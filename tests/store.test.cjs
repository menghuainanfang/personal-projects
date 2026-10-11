const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const JSZip = require("jszip");
const { Store } = require("../electron/store.cjs");
const { fixtures } = require("./fixtures.cjs");
const root = fs.mkdtempSync(path.join(os.tmpdir(), "readingos-tests-"));
test("PDF/EPUB managed imports, metadata, duplicate rejection and malformed input", async () => {
  const dir = await fixtures(path.join(root, "fixtures"));
  const s = new Store(path.join(root, "imports"));
  try {
    const a = await s.importFile(path.join(dir, "sample.pdf"));
    const b = await s.importFile(path.join(dir, "sample.epub"), a.bookId);
    assert.equal(s.snapshot().books.length, 1);
    assert.equal(s.snapshot().assets.length, 2);
    assert.equal(s.snapshot().books[0].title, "The Art of Slow Reading");
    assert.equal(
      (await s.importFile(path.join(dir, "sample.pdf"))).duplicate,
      true,
    );
    assert.equal(s.snapshot().assets.length, 2);
    assert.ok(
      s
        .readAsset(s.snapshot().assets[0].id)
        .equals(fs.readFileSync(path.join(dir, "sample.pdf"))),
    );
    await assert.rejects(s.importFile(path.join(dir, "malformed.pdf")), /损坏/);
    await assert.rejects(
      s.importFile(path.join(dir, "malformed.epub")),
      /损坏/,
    );
    assert.equal(s.snapshot().books.length, 1);
    assert.equal(b.bookId, a.bookId);
  } finally {
    s.close();
  }
});
test("Long reflection revisions and all workflow records survive reopen", () => {
  const dir = path.join(root, "workflow");
  let s = new Store(dir);
  const b = s.save("books", { title: "纸质书", status: "reading" });
  const long = "<p>" + "中文段落与思考".repeat(10000) + "</p>";
  s.summary(b, long);
  s.summary(b, long + "<p>第二次修改</p>");
  s.summary(b, long + "<p>第二次修改</p>");
  const j = s.save("journals", {
    book_id: b,
    title: "日志",
    date: "2026-10-11",
    content: long,
    source: "第 1 章",
  });
  const i = s.save("insights", { title: "理解", content: "用自己的话表达" });
  s.save("insight_links", {
    insight_id: i,
    book_id: b,
    journal_id: j,
    annotation_id: null,
  });
  const a = s.save("actions", {
    insight_id: i,
    book_id: b,
    description: "今日实践",
    planned: "2026-10-12",
    status: "active",
  });
  s.save("feedback", { action_id: a, content: "有帮助", date: "2026-10-12" });
  s.close();
  s = new Store(dir);
  try {
    assert.equal(s.snapshot().summaries[0].content, long + "<p>第二次修改</p>");
    assert.equal(s.snapshot().summary_revisions.length, 2);
    assert.equal(s.snapshot().journals[0].content, long);
    assert.equal(s.snapshot().feedback[0].content, "有帮助");
    assert.ok(s.markdown(b).includes("第二次修改"));
    assert.ok(s.markdown(b).includes("第 1 章"));
  } finally {
    s.close();
  }
});
test("Annotations use edition-specific anchors and progress persists", async () => {
  const s = new Store(path.join(root, "anchors"));
  const dir = await fixtures(path.join(root, "anchors-fixtures"));
  try {
    await s.importFile(path.join(dir, "sample.pdf"));
    const a = s.snapshot().assets[0];
    const anchor = JSON.stringify({ page: 2, rects: [[0.1, 0.2, 0.3, 0.04]] });
    s.save("annotations", {
      asset_id: a.id,
      kind: "highlight",
      anchor,
      color: "#e6b84e",
      width: 2,
      text: "Reading",
      comment: "重点",
    });
    s.progress(a.id, JSON.stringify({ page: 2, scroll: 0.3 }));
    assert.equal(s.snapshot().annotations[0].anchor, anchor);
    assert.equal(JSON.parse(s.snapshot().progress[0].location).page, 2);
    assert.throws(
      () =>
        s.save("annotations", {
          asset_id: "missing",
          kind: "ink",
          anchor: "{}",
          color: "#000000",
          width: 2,
        }),
      /FOREIGN KEY/,
    );
  } finally {
    s.close();
  }
});
test("Completion dates count books once, independently of reading plans", () => {
  const s = new Store(path.join(root, "goals"));
  try {
    const b = s.save("books", {
      title: "跨月阅读",
      status: "completed",
      started: "2025-12-20",
      completed: "2026-02-03",
    });
    s.plan(b, "2025-12", true);
    s.plan(b, "2026-01", true);
    s.plan(b, "2026-02", true);
    s.goal("2026", 12);
    s.goal("2026-02", 2);
    assert.equal(
      s.snapshot().books.filter((b) => b.completed.startsWith("2026")).length,
      1,
    );
    assert.equal(s.snapshot().plans.length, 3);
    s.save("books", { id: b, status: "reading" });
    assert.equal(s.snapshot().books[0].completed, "");
    assert.equal(s.snapshot().books[0].started, "2025-12-20");
  } finally {
    s.close();
  }
});
test("Backup restores all relational rows and original assets, with recovery backup", async () => {
  const s = new Store(path.join(root, "backup"));
  const dir = await fixtures(path.join(root, "backup-fixtures"));
  try {
    await s.importFile(path.join(dir, "sample.epub"));
    const b = s.snapshot().books[0].id;
    s.summary(b, "<p>保留思考</p>");
    s.save("journals", {
      book_id: b,
      title: "日志",
      date: "2026-10-11",
      content: "<p>保留日志</p>",
    });
    const before = s.snapshot();
    const target = path.join(root, "all.readingos");
    await s.backup(target);
    s.remove("books", b);
    assert.equal(s.snapshot().assets.length, 0);
    const recovery = await s.restore(target);
    assert.ok(fs.existsSync(recovery));
    assert.deepEqual(s.snapshot(), before);
    assert.ok(
      s
        .readAsset(before.assets[0].id)
        .equals(fs.readFileSync(path.join(dir, "sample.epub"))),
    );
  } finally {
    s.close();
  }
});
test("Incomplete backup does not replace the live library", async () => {
  const s = new Store(path.join(root, "bad-restore"));
  try {
    s.save("books", { title: "仍在" });
    const target = path.join(root, "bad.readingos");
    const z = new JSZip();
    z.file("format.json", JSON.stringify({ app: "ReadingOS", version: 1 }));
    z.file("library.sqlite", "invalid");
    fs.writeFileSync(target, await z.generateAsync({ type: "nodebuffer" }));
    await assert.rejects(s.restore(target));
    assert.equal(s.snapshot().books[0].title, "仍在");
  } finally {
    s.close();
  }
});
test("Version 1 reopen preserves data and newer database is rejected", () => {
  const dir = path.join(root, "migration");
  let s = new Store(dir);
  const id = s.save("books", { title: "升级保留" });
  s.close();
  s = new Store(dir);
  assert.equal(s.snapshot().books[0].id, id);
  s.db.exec("PRAGMA user_version=2");
  s.close();
  assert.throws(() => new Store(dir), /较新版本/);
});
test("Transactions roll back dependent writes on foreign-key failure", () => {
  const s = new Store(path.join(root, "transaction"));
  try {
    assert.throws(() =>
      s.transaction(() => {
        s.save("books", { title: "应回滚" });
        s.save("insight_links", { insight_id: "missing", book_id: "missing" });
      }),
    );
    assert.equal(s.snapshot().books.length, 0);
  } finally {
    s.close();
  }
});
