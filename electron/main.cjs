const { app, BrowserWindow, ipcMain, dialog, session } = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const { Store } = require("./store.cjs");
const isolated = process.env.READINGOS_TEST_DATA;
if (isolated) app.setPath("userData", path.resolve(isolated));
let store, win;
app.whenReady().then(() => {
  store = new Store(app.getPath("userData"));
  const on = (name, fn) =>
    ipcMain.handle("readingos:" + name, (event, ...args) => {
      if (event.senderFrame !== win.webContents.mainFrame)
        throw new Error("仅应用主窗口可操作资料");
      return fn(...args);
    });
  for (const name of [
    "snapshot",
    "save",
    "remove",
    "summary",
    "progress",
    "goal",
    "plan",
    "readAsset",
    "annotations",
  ])
    on(name, (...args) => store[name](...args));
  on("info", () => ({
    version: app.getVersion(),
    dataPath: app.getPath("userData"),
    packaged: app.isPackaged,
  }));
  on("import", async (bookId) => {
    const result = await dialog.showOpenDialog(win, {
      title: "导入图书",
      properties: ["openFile", "multiSelections"],
      filters: [{ name: "电子书", extensions: ["pdf", "epub"] }],
    });
    if (result.canceled) return [];
    const imported = [];
    for (const file of result.filePaths) {
      try {
        imported.push(await store.importFile(file, bookId));
      } catch (e) {
        imported.push({ error: path.basename(file) + "：" + e.message });
      }
    }
    return imported;
  });
  on("cover", async () => {
    const r = await dialog.showOpenDialog(win, {
      properties: ["openFile"],
      filters: [
        { name: "封面图片", extensions: ["png", "jpg", "jpeg", "webp"] },
      ],
    });
    if (r.canceled) return null;
    const p = r.filePaths[0];
    const ext = path.extname(p).slice(1).toLowerCase();
    return (
      "data:image/" +
      (ext === "jpg" ? "jpeg" : ext) +
      ";base64," +
      fs.readFileSync(p).toString("base64")
    );
  });
  on("backup", async () => {
    const r = await dialog.showSaveDialog(win, {
      title: "备份全部资料",
      defaultPath:
        "ReadingOS-" + new Date().toLocaleDateString("sv-SE") + ".readingos",
      filters: [{ name: "ReadingOS 备份", extensions: ["readingos"] }],
    });
    if (r.canceled) return null;
    await store.backup(r.filePath);
    return r.filePath;
  });
  on("restore", async () => {
    const r = await dialog.showOpenDialog(win, {
      properties: ["openFile"],
      filters: [{ name: "ReadingOS 备份", extensions: ["readingos"] }],
    });
    if (r.canceled) return null;
    const confirm = await dialog.showMessageBox(win, {
      type: "warning",
      buttons: ["取消", "恢复备份"],
      defaultId: 0,
      cancelId: 0,
      message: "恢复将替换当前书库。",
      detail: "当前资料会先保存为恢复前备份，保留在应用数据目录。",
    });
    if (confirm.response !== 1) return null;
    return store.restore(r.filePaths[0]);
  });
  on("exportMarkdown", async (id) => {
    const r = await dialog.showSaveDialog(win, {
      defaultPath: "读书笔记.md",
      filters: [{ name: "Markdown", extensions: ["md"] }],
    });
    if (r.canceled) return null;
    fs.writeFileSync(r.filePath, store.markdown(id), "utf8");
    return r.filePath;
  });
  session.defaultSession.webRequest.onBeforeRequest((details, cb) => {
    const allowed =
      details.url.startsWith("file:") ||
      details.url.startsWith("blob:") ||
      details.url.startsWith("data:") ||
      details.url.startsWith("devtools:") ||
      (!app.isPackaged && /^https?:\/\/127\.0\.0\.1:5173\//.test(details.url));
    cb({ cancel: !allowed });
  });
  session.defaultSession.webRequest.onHeadersReceived((details, cb) => {
    cb({
      responseHeaders: {
        ...details.responseHeaders,
        "Content-Security-Policy": [
          "default-src 'self' blob: data:; script-src 'self'; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self' blob: data:; connect-src 'self' blob: data:; frame-src 'self' blob:; object-src 'none'; base-uri 'self'",
        ],
      },
    });
  });
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, cb) =>
    cb(false),
  );
  win = new BrowserWindow({
    width: 1380,
    height: 920,
    minWidth: 900,
    minHeight: 640,
    title: "ReadingOS",
    backgroundColor: "#f6f5f0",
    show: !process.env.READINGOS_TEST_HEADLESS,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event, url) => {
    if (url !== win.webContents.getURL()) event.preventDefault();
  });
  win.loadFile(path.join(__dirname, "../dist/index.html"));
});
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => store?.close());
