# 开源组件研究

检查日期：2026-10-11。已读取以下八个仓库的实际 README、许可证，及存在的 package.json / CMakeLists.txt；原文工作副本在被 Git 忽略的 `research/`。安装版本以 `package-lock.json` 为准。

| 项目                                                                                              | 许可证                    | API / 架构 / 兼容性                                                                                                 | 使用决定与风险                                                                                            |
| ------------------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| [PDF.js](https://github.com/mozilla/pdf.js)                                                       | Apache-2.0                | worker、getDocument、getPage、getViewport、render、TextLayer、getOutline；本地 CMaps/字体/WASM                      | 使用 pdfjs-dist 5.4.624。canvas 与文字层交给 PDF.js；批注模型保持独立。每次切换/缩放取消旧 render task    |
| [epub.js](https://github.com/futurepress/epub.js)                                                 | BSD-2-Clause              | 0.3.93；Book → Spine → Rendition；renderTo/display、selected/relocated、themes、annotations.highlight/remove；CFI   | 使用。禁用 scripted content，净化章节 HTML，阻止外网；位置与 asset 绑定，不跨版本复制锚点                 |
| [foliate-js](https://github.com/johnfactotum/foliate-js)                                          | MIT                       | 原生 ESM；book / renderer 接口；view.js、overlayer.js、epubcfi.js；README 明确 API 不稳定且无正式 release           | 保留作为未来格式适配候选，本版不引入                                                                      |
| [react-pdf-highlighter-extended](https://github.com/DanielArnould/react-pdf-highlighter-extended) | MIT                       | 8.1.0；PdfLoader/PdfHighlighter、viewportToScaled、TextHighlight/AreaHighlight；peer React 18.3.1，pdfjs-dist 4.4.x | 不引入：与本版 React 19 / PDF.js 5 不匹配，且不直接提供完整鼠标绘图；直接使用 PDF.js 成熟的页面与文字渲染 |
| [Tiptap](https://github.com/ueberdosis/tiptap)                                                    | MIT（开源 Editor）        | ProseMirror 基础，无头 UI；useEditor/EditorContent、StarterKit、onUpdate、getHTML、setContent                       | 使用开源 React / StarterKit；每次正文更新立即保存，界面显示状态；不依赖商业服务                           |
| [Readest](https://github.com/readest/readest)                                                     | AGPL-3.0                  | README：Next.js 16 + Tauri 2；pnpm monorepo；多格式、批注、并排阅读                                                 | 仅参考目录/阅读/批注布局和模块划分                                                                        |
| [Koodo Reader](https://github.com/koodo-reader/koodo-reader)                                      | AGPL-3.0                  | 2.4.6 工作树 package；Electron main.js、React；书库、笔记、备份、格式适配                                           | 仅参考书库导航、状态筛选和备份入口                                                                        |
| [Xournal++](https://github.com/xournalpp/xournalpp)                                               | GPL-2.0（见仓库 LICENSE） | C++ / GTK3 / CMake；工具模式、PDF 底图、手绘/形状/文本、橡皮擦、自动保存                                            | 仅参考明确工具模式和鼠标绘图 UX，不作为 React 依赖                                                        |

## 核对的 API 与示例

- [PDF.js 官方示例](https://mozilla.github.io/pdf.js/examples/)：viewport 变换、HiDPI canvas、render task 与文本渲染；[viewer 源码](https://github.com/mozilla/pdf.js/tree/master/web)包含 AnnotationEditor 层。编辑器 API 与 PDF.js 内部 annotation storage 紧密相关，无法直接覆盖 EPUB 和本版独立绘图模型，因此原文渲染由其负责，用户记录置于独立 SVG 层。
- [epub.js API](https://github.com/futurepress/epub.js/blob/master/documentation/md/API.md)、[高亮示例](https://github.com/futurepress/epub.js/blob/master/examples/highlights.html)：selected CFI、annotations.highlight、relocated、display。CFI 是当前版本内容树中的位置，不等于跨版本内容 ID。
- [Tiptap React 安装/API 示例](https://tiptap.dev/docs/editor/getting-started/install/react)：useEditor 和 EditorContent 的生命周期。StarterKit 提供标题、强调、列表、引用和历史。
- react-pdf-highlighter-extended README 的 PdfLoader / PdfHighlighter / HighlightContainer 示例：具备 viewport 无关高亮，但自定义 ink 工具仍需实现。
- foliate-js README 提供自定义 `foliate-view`、`open`、`relocate` 及底层 book 接口示例。Readest/Koodo/Xournal++ 是完整应用而非可直接嵌入的阅读器 SDK。

## 分发许可

项目原创代码采用 MIT。`THIRD_PARTY_NOTICES.txt` 包含安装的运行时 JS 依赖许可证和 notices，并随安装包提供。Electron 的 LICENSE 与 LICENSES.chromium.html 随 runtime 一并分发。测试书由本项目原创，CC0，可重新生成；不包含用户书籍或其他受版权限制作品。
