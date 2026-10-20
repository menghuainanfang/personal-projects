const { DatabaseSync } = require("node:sqlite");
const fs = require("node:fs");
const path = require("node:path");
const { randomUUID, createHash } = require("node:crypto");
const JSZip = require("jszip");
const { PDFDocument } = require("pdf-lib");
const TurndownService = require("turndown");
const { DOMParser } = require("@xmldom/xmldom");

const schema = `
CREATE TABLE books(id TEXT PRIMARY KEY,title TEXT NOT NULL,author TEXT NOT NULL DEFAULT '',tags TEXT NOT NULL DEFAULT '',category TEXT NOT NULL DEFAULT '',cover TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'want',started TEXT NOT NULL DEFAULT '',completed TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE assets(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,name TEXT NOT NULL,format TEXT NOT NULL,hash TEXT NOT NULL UNIQUE,file TEXT NOT NULL UNIQUE,created TEXT NOT NULL);
CREATE TABLE progress(asset_id TEXT PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,location TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE annotations(id TEXT PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,kind TEXT NOT NULL,anchor TEXT NOT NULL,color TEXT NOT NULL,width REAL NOT NULL DEFAULT 2,text TEXT NOT NULL DEFAULT '',comment TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE summaries(book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,content TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE summary_revisions(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,content TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE journals(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,title TEXT NOT NULL,date TEXT NOT NULL,content TEXT NOT NULL,source TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE insights(id TEXT PRIMARY KEY,title TEXT NOT NULL,content TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE insight_links(id TEXT PRIMARY KEY,insight_id TEXT NOT NULL REFERENCES insights(id) ON DELETE CASCADE,book_id TEXT REFERENCES books(id) ON DELETE CASCADE,annotation_id TEXT REFERENCES annotations(id) ON DELETE SET NULL,journal_id TEXT REFERENCES journals(id) ON DELETE SET NULL);
CREATE TABLE actions(id TEXT PRIMARY KEY,insight_id TEXT REFERENCES insights(id) ON DELETE SET NULL,book_id TEXT REFERENCES books(id) ON DELETE SET NULL,description TEXT NOT NULL,planned TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'planned',created TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE feedback(id TEXT PRIMARY KEY,action_id TEXT NOT NULL REFERENCES actions(id) ON DELETE CASCADE,content TEXT NOT NULL,date TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE goals(period TEXT PRIMARY KEY,target INTEGER NOT NULL CHECK(target>=0));
CREATE TABLE plans(book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,month TEXT NOT NULL,PRIMARY KEY(book_id,month));
CREATE TABLE bookmarks(id TEXT PRIMARY KEY,asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,location TEXT NOT NULL,label TEXT NOT NULL,created TEXT NOT NULL);
`;
const fields = {
  books: [
    "title",
    "author",
    "tags",
    "category",
    "cover",
    "status",
    "started",
    "completed",
  ],
  annotations: [
    "asset_id",
    "kind",
    "anchor",
    "color",
    "width",
    "text",
    "comment",
  ],
  journals: ["book_id", "title", "date", "content", "source"],
  insights: ["title", "content"],
  insight_links: ["insight_id", "book_id", "annotation_id", "journal_id"],
  actions: ["insight_id", "book_id", "description", "planned", "status"],
  feedback: ["action_id", "content", "date"],
  bookmarks: ["asset_id", "location", "label"],
};
const preferencesSchema = `CREATE TABLE reader_preferences(book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,settings TEXT NOT NULL,updated TEXT NOT NULL); PRAGMA user_version=2;`;
class Store {
  constructor(root) {
    this.root = root;
    fs.mkdirSync(path.join(root, "assets"), { recursive: true });
    this.open();
  }
  open() {
    this.db = new DatabaseSync(path.join(this.root, "library.sqlite"));
    this.db.exec(
      "PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;",
    );
    const version = this.db.prepare("PRAGMA user_version").get().user_version;
    if (version > 2) {
      this.db.close();
      throw new Error("数据库来自较新版本，请使用相应版本 ReadingOS。");
    }
    if (version === 0) this.transaction(() => this.db.exec(schema + preferencesSchema));
    if (version === 1) {
      const backup = path.join(this.root, 'before-v2.sqlite');
      if (!fs.existsSync(backup)) this.db.exec(`VACUUM INTO '${backup.replace(/'/g, "''")}'`);
      this.transaction(() => this.db.exec(preferencesSchema));
    }
  }
  transaction(fn) {
    this.db.exec("BEGIN IMMEDIATE");
    try {
      const result = fn();
      this.db.exec("COMMIT");
      return result;
    } catch (e) {
      this.db.exec("ROLLBACK");
      throw e;
    }
  }
  snapshot() {
    const result = {};
    for (const table of [
      "books",
      "assets",
      "progress",
      "annotations",
      "summaries",
      "summary_revisions",
      "journals",
      "insights",
      "insight_links",
      "actions",
      "feedback",
      "goals",
      "plans",
      "bookmarks",
      "reader_preferences",
    ])
      result[table] = this.db.prepare(`SELECT * FROM ${table}`).all();
    return result;
  }
  save(table, data) {
    if (!fields[table]) throw new Error("不支持的数据类型");
    const id = data.id || randomUUID();
    const existing = this.db
      .prepare(`SELECT * FROM ${table} WHERE id=?`)
      .get(id);
    const row = { ...existing, ...data, id };
    if (table === "books") {
      if (!String(row.title || "").trim()) throw new Error("请填写书名");
      if (
        !["want", "reading", "completed", "paused", "abandoned"].includes(
          row.status || "want",
        )
      )
        throw new Error("阅读状态无效");
      for (const key of fields.books)
        row[key] ??= key === "status" ? "want" : "";
      if (row.status === "reading" && !row.started)
        row.started = new Date().toLocaleDateString("sv-SE");
      if (row.status === "completed" && !row.completed)
        row.completed = new Date().toLocaleDateString("sv-SE");
      if (row.status !== "completed") row.completed = "";
    }
    if (
      table === "actions" &&
      !["planned", "active", "done", "cancelled"].includes(row.status)
    )
      throw new Error("行动状态无效");
    const keys = fields[table].filter((k) => row[k] !== undefined);
    const now = new Date().toISOString();
    if (existing) {
      const updated = this.db
        .prepare(`PRAGMA table_info(${table})`)
        .all()
        .some((c) => c.name === "updated");
      this.db
        .prepare(
          `UPDATE ${table} SET ${keys.map((k) => k + "=?").join(",")}${updated ? ",updated=?" : ""} WHERE id=?`,
        )
        .run(...keys.map((k) => row[k]), ...(updated ? [now] : []), id);
    } else {
      const updated = this.db
        .prepare(`PRAGMA table_info(${table})`)
        .all()
        .some((c) => c.name === "updated");
      const created = this.db
        .prepare(`PRAGMA table_info(${table})`)
        .all()
        .some((c) => c.name === "created");
      const cols = [
        "id",
        ...keys,
        ...(created ? ["created"] : []),
        ...(updated ? ["updated"] : []),
      ];
      this.db
        .prepare(
          `INSERT INTO ${table}(${cols.join(",")}) VALUES(${cols.map(() => "?")})`,
        )
        .run(
          id,
          ...keys.map((k) => row[k]),
          ...(created ? [now] : []),
          ...(updated ? [now] : []),
        );
    }
    return id;
  }
  remove(table, id) {
    if (!fields[table]) throw new Error("不支持的数据类型");
    const files =
      table === "books"
        ? this.db.prepare("SELECT file FROM assets WHERE book_id=?").all(id)
        : [];
    this.db.prepare(`DELETE FROM ${table} WHERE id=?`).run(id);
    for (const { file } of files)
      fs.rmSync(path.join(this.root, "assets", path.basename(file)), {
        force: true,
      });
  }
  annotations(assetId, rows) {
    this.transaction(() => {
      const existing = this.db
        .prepare("SELECT id FROM annotations WHERE asset_id=?")
        .all(assetId);
      for (const a of existing)
        if (!rows.some((r) => r.id === a.id)) this.remove("annotations", a.id);
      for (const row of rows) {
        if (row.asset_id !== assetId) throw new Error("批注版本不匹配");
        this.save("annotations", row);
      }
    });
  }
  summary(bookId, content) {
    this.transaction(() => {
      const old = this.db
        .prepare("SELECT content FROM summaries WHERE book_id=?")
        .get(bookId);
      if (old?.content === content) return;
      const now = new Date().toISOString();
      this.db
        .prepare("INSERT INTO summary_revisions VALUES(?,?,?,?)")
        .run(randomUUID(), bookId, content, now);
      this.db
        .prepare(
          "INSERT INTO summaries VALUES(?,?,?) ON CONFLICT(book_id) DO UPDATE SET content=excluded.content,updated=excluded.updated",
        )
        .run(bookId, content, now);
    });
  }
  progress(assetId, location) {
    this.db
      .prepare(
        "INSERT INTO progress VALUES(?,?,?) ON CONFLICT(asset_id) DO UPDATE SET location=excluded.location,updated=excluded.updated",
      )
      .run(assetId, location, new Date().toISOString());
  }
  preferences(bookId, settings) {
    const current = this.db.prepare('SELECT settings FROM reader_preferences WHERE book_id=?').get(bookId);
    const allowed = ['fontSize','lineHeight','zoom','color','width','background','foreground','readerTheme'];
    const next = { ...(current ? JSON.parse(current.settings) : {}) };
    for (const key of allowed) if (settings[key] !== undefined) next[key] = settings[key];
    this.db.prepare('INSERT INTO reader_preferences VALUES(?,?,?) ON CONFLICT(book_id) DO UPDATE SET settings=excluded.settings,updated=excluded.updated')
      .run(bookId,JSON.stringify(next),new Date().toISOString());
  }
  goal(period, target) {
    if (
      !/^\d{4}(-\d{2})?$/.test(period) ||
      !Number.isInteger(target) ||
      target < 0
    )
      throw new Error("阅读目标无效");
    this.db
      .prepare(
        "INSERT INTO goals VALUES(?,?) ON CONFLICT(period) DO UPDATE SET target=excluded.target",
      )
      .run(period, target);
  }
  plan(bookId, month, enabled) {
    if (!/^\d{4}-\d{2}$/.test(month)) throw new Error("月份无效");
    this.db
      .prepare(
        enabled
          ? "INSERT OR IGNORE INTO plans VALUES(?,?)"
          : "DELETE FROM plans WHERE book_id=? AND month=?",
      )
      .run(bookId, month);
  }
  async importFile(source, bookId) {
    const format = path.extname(source).slice(1).toLowerCase();
    if (!["pdf", "epub"].includes(format))
      throw new Error("请选择 PDF 或 EPUB 文件");
    const bytes = fs.readFileSync(source);
    const hash = createHash("sha256").update(bytes).digest("hex");
    const duplicate = this.db
      .prepare("SELECT * FROM assets WHERE hash=?")
      .get(hash);
    if (duplicate) return { bookId: duplicate.book_id, duplicate: true };
    let title = path.basename(source, path.extname(source)),
      author = "";
    try {
      if (format === "pdf") {
        const pdf = await PDFDocument.load(bytes, { updateMetadata: false });
        if (pdf.getPageCount() < 1) throw Error();
        title = pdf.getTitle() || title;
        author = pdf.getAuthor() || "";
      } else {
        const zip = await JSZip.loadAsync(bytes);
        const container = await zip
          .file("META-INF/container.xml")
          ?.async("string");
        if (!container) throw Error();
        const parser = new DOMParser({
          errorHandler: {
            warning() {},
            error(message) {
              throw Error(message);
            },
            fatalError(message) {
              throw Error(message);
            },
          },
        });
        const opf = parser
          .parseFromString(container, "application/xml")
          .getElementsByTagNameNS("*", "rootfile")[0]
          ?.getAttribute("full-path");
        const xml = opf && (await zip.file(opf)?.async("string"));
        if (!xml) throw Error();
        const document = parser.parseFromString(xml, "application/xml");
        const manifest = new Map(
          Array.from(document.getElementsByTagNameNS("*", "item")).map(
            (item) => [item.getAttribute("id"), item.getAttribute("href")],
          ),
        );
        const spine = Array.from(
          document.getElementsByTagNameNS("*", "itemref"),
        );
        if (!spine.length) throw Error();
        for (const ref of spine) {
          const href = manifest.get(ref.getAttribute("idref"));
          if (
            !href ||
            !zip.file(
              path.posix.join(
                path.posix.dirname(opf),
                decodeURIComponent(href.split("#")[0]),
              ),
            )
          )
            throw Error();
        }
        title =
          document.getElementsByTagNameNS("*", "title")[0]?.textContent ||
          title;
        author =
          document.getElementsByTagNameNS("*", "creator")[0]?.textContent || "";
      }
    } catch {
      throw new Error(
        "文件损坏、加密或格式不受支持。请尝试可正常打开的无 DRM 文件。",
      );
    }
    const assetId = randomUUID();
    const file = assetId + "." + format;
    fs.writeFileSync(path.join(this.root, "assets", file), bytes, {
      flag: "wx",
    });
    try {
      this.transaction(() => {
        if (!bookId) bookId = this.save("books", { title, author });
        this.db
          .prepare("INSERT INTO assets VALUES(?,?,?,?,?,?,?)")
          .run(
            assetId,
            bookId,
            path.basename(source),
            format,
            hash,
            file,
            new Date().toISOString(),
          );
      });
    } catch (e) {
      fs.rmSync(path.join(this.root, "assets", file), { force: true });
      throw e;
    }
    return { bookId, duplicate: false };
  }
  readAsset(id) {
    const asset = this.db.prepare("SELECT file FROM assets WHERE id=?").get(id);
    if (!asset) throw new Error("找不到图书文件");
    return fs.readFileSync(
      path.join(this.root, "assets", path.basename(asset.file)),
    );
  }
  async backup(destination) {
    const temp = path.join(this.root, "snapshot-" + randomUUID() + ".sqlite");
    try {
      this.db.exec(`VACUUM INTO '${temp.replace(/'/g, "''")}'`);
      const zip = new JSZip();
      zip.file("library.sqlite", fs.readFileSync(temp));
      zip.file("format.json", JSON.stringify({ app: "ReadingOS", version: 1 }));
      for (const asset of this.db.prepare("SELECT file FROM assets").all())
        zip.file(
          "assets/" + asset.file,
          fs.readFileSync(
            path.join(this.root, "assets", path.basename(asset.file)),
          ),
        );
      const bytes = await zip.generateAsync({
        type: "nodebuffer",
        compression: "DEFLATE",
      });
      fs.writeFileSync(destination + ".tmp", bytes);
      fs.renameSync(destination + ".tmp", destination);
    } finally {
      fs.rmSync(temp, { force: true });
    }
  }
  async restore(source) {
    const zip = await JSZip.loadAsync(fs.readFileSync(source));
    const format = JSON.parse(
      (await zip.file("format.json")?.async("string")) || "null",
    );
    if (format?.app !== "ReadingOS" || format.version !== 1)
      throw new Error("不是有效的 ReadingOS 备份");
    const stage = path.join(this.root, "restore-" + randomUUID());
    fs.mkdirSync(path.join(stage, "assets"), { recursive: true });
    let candidate;
    try {
      const data = await zip.file("library.sqlite")?.async("nodebuffer");
      if (!data) throw new Error("备份缺少数据库");
      fs.writeFileSync(path.join(stage, "library.sqlite"), data);
      candidate = new DatabaseSync(path.join(stage, "library.sqlite"));
      const version = candidate.prepare('PRAGMA user_version').get().user_version;
      if (
        ![1,2].includes(version) ||
        candidate.prepare("PRAGMA integrity_check").get().integrity_check !==
          "ok" ||
        candidate.prepare("PRAGMA foreign_key_check").all().length
      )
        throw new Error("备份数据库无效");
      if (version === 1) candidate.exec('BEGIN IMMEDIATE;'+preferencesSchema+'COMMIT;');
      for (const table of Object.keys(this.snapshot()))
        candidate.prepare(`SELECT * FROM ${table} LIMIT 0`).all();
      for (const { id, format, file } of candidate
        .prepare("SELECT * FROM assets")
        .all()) {
        if (
          !["pdf", "epub"].includes(format) ||
          file !== id + "." + format ||
          path.basename(file) !== file
        )
          throw new Error("备份包含无效文件路径");
        const content = await zip.file("assets/" + file)?.async("nodebuffer");
        if (!content) throw new Error("备份缺少图书文件");
        fs.writeFileSync(path.join(stage, "assets", file), content);
      }
      candidate.close();
      candidate = null;
      const recovery = path.join(
        this.root,
        "before-restore-" +
          new Date().toISOString().replace(/[:.]/g, "-") +
          ".readingos",
      );
      await this.backup(recovery);
      this.db.close();
      const old = path.join(this.root, "previous-" + randomUUID());
      fs.mkdirSync(old);
      const moved = [],
        installed = [];
      try {
        for (const name of [
          "library.sqlite",
          "library.sqlite-wal",
          "library.sqlite-shm",
          "assets",
        ])
          if (fs.existsSync(path.join(this.root, name))) {
            fs.renameSync(path.join(this.root, name), path.join(old, name));
            moved.push(name);
          }
        fs.renameSync(
          path.join(stage, "library.sqlite"),
          path.join(this.root, "library.sqlite"),
        );
        installed.push("library.sqlite");
        fs.renameSync(
          path.join(stage, "assets"),
          path.join(this.root, "assets"),
        );
        installed.push("assets");
        this.open();
      } catch (e) {
        for (const name of installed)
          fs.rmSync(path.join(this.root, name), {
            recursive: true,
            force: true,
          });
        for (const name of moved)
          fs.renameSync(path.join(old, name), path.join(this.root, name));
        this.open();
        throw e;
      } finally {
        fs.rmSync(old, { recursive: true, force: true });
      }
      return recovery;
    } finally {
      candidate?.close();
      fs.rmSync(stage, { recursive: true, force: true });
    }
  }
  markdown(bookId) {
    const book = this.db.prepare("SELECT * FROM books WHERE id=?").get(bookId);
    if (!book) throw new Error("图书不存在");
    const md = new TurndownService();
    const reflection = this.db
      .prepare("SELECT * FROM summaries WHERE book_id=?")
      .get(bookId);
    const logs = this.db
      .prepare("SELECT * FROM journals WHERE book_id=? ORDER BY date")
      .all(bookId);
    return (
      `# ${book.title}\n\n${book.author}\n\n## 主读后感\n\n${md.turndown(reflection?.content || "")}\n\n` +
      logs
        .map(
          (j) =>
            `## ${j.date} · ${j.title}\n\n${md.turndown(j.content)}\n\n${j.source ? "来源：" + j.source + "\n" : ""}`,
        )
        .join("\n")
    );
  }
  close() {
    this.db.close();
  }
}
module.exports = { Store, schema };
