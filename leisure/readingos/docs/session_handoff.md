# ReadingOS 会话交接

## 项目位置与启动

- 仓库：`D:\桌面\ReadingOS`，分支 `main`，远程 `https://github.com/menghuainanfang/personal-projects.git`。
- 应用目录：`D:\桌面\ReadingOS\leisure\readingos`。
- 安装包：`D:\桌面\ReadingOS\leisure\readingos\release\ReadingOS-0.1.0-win-x64-setup.exe`。
- 本机安装测试位置：`D:\桌面\ReadingOS\leisure\readingos\test-results\installed\ReadingOS.exe`。
- 开发启动：`npm run build` 后 `npm run desktop`。不需要 Vite 开发服务器。
- 用户资料位置由 `app.getPath('userData')` 决定；设置页显示实际路径。测试通过 `READINGOS_TEST_DATA` 指定隔离目录。

## 当前实现

Electron 44.7.0 / React 19 / TypeScript / Vite；Node 内置 SQLite，schema v1。PDF.js 5.4.624、epub.js 0.3.93（xmldom 固定到 0.8.15）、Tiptap 开源组件。Rust 和 C++ Build Tools 未安装；技术选择见环境审计。

完整阅读流程已实现：管理副本导入、纸质书、元数据/封面、书库检索与布局、PDF/EPUB reader、批注/目录/书签、主读后感/历史、日志、洞见/多书来源、实践行动/反馈、计划/统计、备份/恢复、Markdown 导出、NSIS 安装。

源文件职责：

- `electron/store.cjs`：建表、实体写入、事务、导入、恢复和导出。
- `electron/main.cjs` / `preload.cjs`：桌面生命周期与固定 IPC。
- `src/domain.ts` / `locales/zh-CN.ts`：接口、状态词条。
- `src/App.tsx`：页面编排与阅读流程。
- `src/RecordDialog.tsx`：实体编辑表单与键盘焦点。
- `src/Editor.tsx`：Tiptap 正文与即时保存。
- `src/reader/`：统一工具、PDF 和 EPUB adapter。
- `tests/store.test.cjs` / `desktop.cjs`：持久化和真实桌面自动验收。

## 验证与发布

TypeScript / 生产构建通过，8 项持久化测试通过。12 项桌面流程测试通过，覆盖图书导入、正文保存、绘图/高亮、缩放、EPUB 重排与重启、备份恢复。完整证据与验证边界见 `docs/testing.md`；测试产物在 Git 忽略的 `test-results/`。

安装包已在本机隔离目录安装，退出码 0。安装后的 12 项验收全部通过，无意外 renderer 错误，记录位于 `test-results/desktop-packaged/results.json`。测试时文件选择器返回原创样本路径；资料库、reader、文件副本和备份执行生产代码。

GitHub 项目目录为 `menghuainanfang/personal-projects/leisure/readingos`，发布标签为 `readingos-v0.1.0`。仓库根目录提供 ReadingOS 专用 CI 和 issue 模板，中文指南与发布步骤已准备。远程 CI 状态以 GitHub Actions 页面为准；本机测试证据见 `docs/testing.md`。安装包未签名。

## 继续开发

先阅读用户给出的 scope limits 和 `docs/known_issues.md`，以具体 beta 反馈推进。用户资料不在源码目录；不要将数据库、原书、备份和测试目录加入 Git。后续 schema 升级在事务内逐版本处理，并用已有 v1 资料测试迁移。

本版未包括 AI、云同步、其他生活模块、OCR、额外格式、EPUB 绘图或跨版本锚点同步。未来路线见 `docs/roadmap.md`。
