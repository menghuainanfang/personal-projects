# ReadingOS v0.3.0 本机候选版

面向 Windows 的本地阅读应用。把 PDF、EPUB 和纸质书放进同一个书库，以自己的主读后感为中心，连接日志、洞见和实践行动。

## 使用

本机候选版本：v0.3.0。真实采用 Mantine AppShell、导航与可调书籍上下文，DayPicker 中文日期网格，以及统一月份/范围选择。保留批量书单、预览去重与自动排期。当前正式 Release 为 v0.2.0；远程源码目录 `leisure/readingos/`，本机工作副本 `projects/readingos/`，开发分支 `readingos-v03-workspace-calendar`。本轮 [验收记录](docs/iterations/003-acceptance.md)、[Mantine 源码研究](docs/iterations/003-mantine-source-study.md)、[DayPicker 源码研究](docs/iterations/003-daypicker-source-study.md) 与 [工作台设计](docs/iterations/003-workspace-design.md) 可供维护审查。

[下载 v0.2 安装包](https://github.com/menghuainanfang/personal-projects/releases/tag/readingos-v0.2.0)。

本机候选安装包：`release/ReadingOS-0.3.0-win-x64-setup.exe`。支持 Windows x64，为当前用户安装。应用自带运行环境，使用时无需 Node、Rust 或网络。v0.3 继续使用 SQLite v2，无数据库迁移。

1. 导入无 DRM PDF / EPUB，或添加纸质书。
2. 在阅读器中高亮、评论、绘图和记录书签。
3. 在书籍主页写主读后感和日志，提炼洞见，记录实践反馈。
4. 在「阅读计划」设置目标和月度书单，在「资料与设置」备份资料。

[中文使用指南](docs/user_guide_zh.md) · [新版测试结果](docs/V02_ACCEPTANCE.md) · [已知限制](docs/known_issues.md)

## 开发

需要 Windows x64、Node.js 24 和 npm、Git。项目采用 Electron、React、TypeScript、Vite、SQLite、PDF.js、epub.js 和 Tiptap。

```powershell
cd D:\桌面\ReadingOS\projects\readingos
npm ci --registry=https://registry.npmjs.org
node node_modules/electron/install.js
node node_modules/esbuild/install.js
npm run notices
npm run build
npm test
npm run test:desktop
npm run test:v02
npm run test:micro002
npm run test:v03
npm run desktop
```

桌面应用始终载入本地 `dist`，不会依赖开发服务器。修改前端后重新构建，再运行 desktop；也可以执行 `npm run dev` 做前端调试，但浏览器不具备本机资料接口。

构建 Windows NSIS 安装包并测试实际发布程序：

```powershell
$env:ELECTRON_BUILDER_COMPRESSION_LEVEL = "5"
npm run package
Remove-Item Env:ELECTRON_BUILDER_COMPRESSION_LEVEL
$env:READINGOS_EXECUTABLE = "$pwd\release\win-unpacked\ReadingOS.exe"
npm run test:desktop
npm run test:v02
npm run test:micro002
npm run test:v03
Remove-Item Env:READINGOS_EXECUTABLE
```

测试使用项目原创样本和隔离的数据目录，不读取个人书库。`tests/fixtures.cjs` 的原创样本按 CC0 提供。`READINGOS_TEST_DATA` 仅供测试指定隔离目录。

`npm run screenshots` 保存六个真实场景和两个视觉候选。首次运行新版验收或截图时，`tests/legacy-fixture.cjs` 会生成完整的原创 v1 结构资料，用于旧备份兼容检查；本机已有的实际 v0.1 基线优先保留。`node tests/v02-desktop.cjs --layout-only` 可单独复测窗口、缩放和对比度。

`npm run screenshots:v03` 保存本轮工作台和日历实机截图。前后对照在 `screenshots/iterations/003/before` 与 `after`；安装验证的结果与资源观察汇总在 `docs/iterations/003-evidence.json`。

## 资料归属

SQLite 数据库和导入文件副本位于 Electron userData（实际路径在应用设置显示）。卸载不删除资料。完整备份为 `.readingos`；书籍主页可导出主读后感与日志的 Markdown。没有云账号、同步或遥测。

## 项目说明

- [环境审计与技术选择](docs/environment_audit.md)
- [开源组件研究](docs/open_source_research.md)
- [v0.2 开源决策](docs/V02_OPEN_SOURCE_DECISIONS.md)
- [视觉方向](docs/ART_DIRECTION.md) · [设计变量](docs/DESIGN_TOKENS.md) · [组件规则](docs/COMPONENT_RULES.md)
- [架构和数据库](docs/architecture.md)
- [发布准备](docs/publishing.md)
- [v0.1 发布说明](docs/release_notes_v0.1.md)
- [v0.2 发布说明](docs/release_notes_v0.2.md) · [更新记录](CHANGELOG.md)
- [后续路线](docs/roadmap.md)
- [会话交接](docs/session_handoff.md)

原创代码 MIT；运行时依赖许可见 `THIRD_PARTY_NOTICES.txt`，Electron 和 Chromium notices 随运行时分发。

## 本机维护

桌面仓库位于 `D:\桌面\ReadingOS`，应用源码、构建产物和文档位于 `projects/readingos/`。从公开仓库克隆时进入 `leisure/readingos` 运行开发命令；两处目录不同。

修改后先执行相关测试，在独立分支提交。本机与公开仓库使用不同子目录；同步时将应用文件映射到 `leisure/readingos`，工作流路径也需同步。合并 main 与正式 Release 需要用户确认。

```powershell
cd D:\桌面\ReadingOS
git switch readingos-v03-workspace-calendar
git add projects/readingos .github/workflows/readingos-windows.yml
git commit -m "Update ReadingOS"
```

本地安装包、依赖、测试资料和个人书库不进入 Git。Windows 构建工作流位于仓库根目录 `.github/workflows/readingos-windows.yml`。
