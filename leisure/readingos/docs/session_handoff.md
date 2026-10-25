# ReadingOS 维护交接

## 当前版本与位置

- 桌面仓库：`D:\桌面\ReadingOS`，当前功能分支 `readingos-micro-002`。
- 应用：`D:\桌面\ReadingOS\projects\readingos`。
- 远程：`https://github.com/menghuainanfang/personal-projects.git`；公开版本为 v0.2.0，远程目录 `leisure/readingos`。
- 本机候选安装包：`release/ReadingOS-0.2.1-win-x64-setup.exe`。
- 已验证安装程序：`test-results/installed-micro002/ReadingOS.exe`。
- 启动：`npm run build` 后 `npm run desktop`，或使用安装后的快捷方式。

v0.2 完成统一书房视觉、主读后感优先、批注引用日志、精确来源跳转、按书保存阅读偏好及键盘对话框。安装版 12 项原有流程、6 项新版专项通过；数据测试 10 项通过。完整证据和边界见 `V02_ACCEPTANCE.md`。

v0.2.1 本机候选版增加阅读计划中的批量书单导入与排期，保留 schema v2。PapaParse 5.7.0 精确固定；研究在工程外 `D:\ReadingOS-research\PapaParse`。私人数据库一致性快照在 `D:\ReadingOS-private-backups`，未参与功能测试。新增 `shared/booklist.mjs`、`BooklistDialog.tsx` 和固定 `batchPlans` IPC；全部业务写入由 Store 一个事务完成。

本轮 21 项数据/算法测试、新功能源码及安装版各 9 项通过；最终安装版原有 12+6 项回归通过。`npm run test:micro002` 使用新建隔离目录与原创 CSV/TSV File，不碰个人书库。详细研究、算法规则、截图和验收见 `micro-iterations/002-papaparse.md` 与 `002-acceptance.md`。v0.2.1 尚未公开发布；下一步可由用户本机试用，再确认源码同步或 Release。

## 关键代码

Electron 44.7 / React 19 / TypeScript / Vite / Node SQLite，schema v2。PDF.js 5.4.624、epub.js 0.3.93 与 Tiptap 保留；新增 Radix Dialog 1.2.0，许可见 THIRD_PARTY_NOTICES。

| 文件 | 职责 |
| --- | --- |
| electron/store.cjs | SQLite、v1 升级、原书管理、部分偏好合并、备份/恢复/导出 |
| electron/main.cjs、preload.cjs | 本机生命周期、文件选择和固定业务 IPC |
| src/domain.ts | 实体与偏好接口、版本对应的批注位置解析 |
| src/App.tsx | 页面、继续阅读、引用日志、来源跳转 |
| src/reader/Reader.tsx | 保存队列、工具、侧栏、阅读设置与来源请求 |
| src/reader/PdfReader.tsx | PDF 文字层、归一化 SVG、固定页与滚动 |
| src/reader/EpubReader.tsx | CFI、高亮、重排、正文配色 |
| src/Editor.tsx、RecordDialog.tsx、Modal.tsx | 正文编辑、记录表单、Radix 键盘焦点 |
| src/style.css | 深浅色、字体、版式、视口与减少动态效果 |

阅读进度按 asset 保存；排版按逻辑书保存。同书来源请求每次传入新的位置对象，阅读器接收请求后跳转。

## 测试与资料

`npm test` 检查数据与迁移；`npm run test:desktop` 检查完整基础流程；`npm run test:v02` 检查引用、独立偏好、重启、离线模拟、36 组视口、键盘、主题与来源删除。安装程序通过 `READINGOS_EXECUTABLE` 指定，数据通过 `READINGOS_TEST_DATA` 隔离。`npm run screenshots` 保存新版图；`node tests/v02-desktop.cjs --layout-only` 仅复测新版布局与主题。

真实基线位于 `screenshots/before/` 与本机 `test-results/v02-visual-before/`；新版截图保存在 after。新克隆的测试由 legacy-fixture 自动生成原创 v1 结构资料。本机实际 v1 全流程备份为 `test-results/v02-v1-workflow.readingos`，可通过 verify-v1-backup 检查全部旧表与文件。

用户资料目录在应用「资料与设置」显示，源码中没有个人书库。依赖、构建、安装包、测试数据库、原书和备份都在 Git 忽略路径。仓库的其他项目独立维护。

## 升级与回退

v1 打开时先保存 `before-v2.sqlite`，再新增阅读设置。升级前仍应保存完整 `.readingos` 备份。回退到 v0.1 要先退出应用，再恢复升级前数据库及对应原书目录；旧版不能直接读取 v2。用 v0.2 恢复旧备份会再次升级到 v2，不能作为直接降级操作。回退会舍弃备份之后的新记录，操作前保存当前完整备份。

本地提交：`1c8865a`（基线和选择）、`5954c81`（界面和主要工作流）、`808ae1f`（阅读器内来源请求）；最终交付文档提交见本地 Git 历史。v0.2 已于 2026-10-20 发布，main 提交 `fe3f82a`，标签 `readingos-v0.2.0`。后续阅读能力见 `roadmap.md`，实际限制见 `known_issues.md`。
