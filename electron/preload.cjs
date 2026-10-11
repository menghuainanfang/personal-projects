const { contextBridge, ipcRenderer } = require("electron");
const call = (name, ...args) =>
  ipcRenderer.invoke("readingos:" + name, ...args);
contextBridge.exposeInMainWorld("readingos", {
  snapshot: () => call("snapshot"),
  save: (table, data) => call("save", table, data),
  remove: (table, id) => call("remove", table, id),
  summary: (bookId, content) => call("summary", bookId, content),
  progress: (id, location) => call("progress", id, location),
  annotations: (assetId, rows) => call("annotations", assetId, rows),
  goal: (period, target) => call("goal", period, target),
  plan: (bookId, month, enabled) => call("plan", bookId, month, enabled),
  importBook: (bookId) => call("import", bookId),
  readAsset: (id) => call("readAsset", id),
  cover: () => call("cover"),
  backup: () => call("backup"),
  restore: () => call("restore"),
  exportMarkdown: (id) => call("exportMarkdown", id),
  info: () => call("info"),
});
