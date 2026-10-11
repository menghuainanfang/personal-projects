# ReadingOS v0.1

面向 Windows 的本地阅读应用。把 PDF、EPUB 和纸质书放进同一个书库，以自己的主读后感为中心，连接日志、洞见和实践行动。

## 使用

安装包：`release/ReadingOS-0.1.0-win-x64-setup.exe`。支持 Windows x64，为当前用户安装。应用自带运行环境，使用时无需 Node、Rust 或网络。

1. 导入无 DRM PDF / EPUB，或添加纸质书。
2. 在阅读器中高亮、评论、绘图和记录书签。
3. 在书籍主页写主读后感和日志，提炼洞见，记录实践反馈。
4. 在「阅读计划」设置目标和月度书单，在「资料与设置」备份资料。

[中文使用指南](docs/user_guide_zh.md) · [测试结果](docs/testing.md) · [已知限制](docs/known_issues.md)

## 开发

需要 Windows x64、Node.js 24 和 npm、Git。项目采用 Electron、React、TypeScript、Vite、SQLite、PDF.js、epub.js 和 Tiptap。

```powershell
cd D:\ReadingOS
npm ci --registry=https://registry.npmjs.org
node node_modules/electron/install.js
node node_modules/esbuild/install.js
npm run notices
npm run build
npm test
npm run test:desktop
npm run desktop
```

桌面应用始终载入本地 `dist`，不会依赖开发服务器。修改前端后重新构建，再运行 desktop；也可以执行 `npm run dev` 做前端调试，但浏览器不具备本机资料接口。

构建 Windows NSIS 安装包并测试实际发布程序：

```powershell
npm run package
$env:READINGOS_EXECUTABLE = "$pwd\release\win-unpacked\ReadingOS.exe"
npm run test:desktop
Remove-Item Env:READINGOS_EXECUTABLE
```

测试使用项目原创样本和隔离的数据目录，不读取个人书库。`tests/fixtures.cjs` 的原创样本按 CC0 提供。`READINGOS_TEST_DATA` 仅供测试指定隔离目录。

## 资料归属

SQLite 数据库和导入文件副本位于 Electron userData（实际路径在应用设置显示）。卸载不删除资料。完整备份为 `.readingos`；书籍主页可导出主读后感与日志的 Markdown。没有云账号、同步或遥测。

## 项目说明

- [环境审计与技术选择](docs/environment_audit.md)
- [开源组件研究](docs/open_source_research.md)
- [架构和数据库](docs/architecture.md)
- [发布准备](docs/publishing.md)
- [v0.1 发布说明](docs/release_notes_v0.1.md)
- [后续路线](docs/roadmap.md)
- [会话交接](docs/session_handoff.md)

原创代码 MIT；运行时依赖许可见 `THIRD_PARTY_NOTICES.txt`，Electron 和 Chromium notices 随运行时分发。
