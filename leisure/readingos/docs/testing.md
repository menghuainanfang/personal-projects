# 测试结果

测试日期：2026-10-11；环境为当前 Windows 11 x64。所有样本为原创测试 PDF / EPUB，测试目录与个人资料隔离。

## 已执行并通过

`npm run build`：TypeScript 检查与 Vite 生产构建通过，本地字体/CMap/WASM 资源复制成功。

`npm test`：8 项持久化测试通过：

1. PDF/EPUB 导入、元数据、同一书多版本、重复识别、损坏文件拒绝和管理副本保留。
2. 约七万字主读后感反复编辑、版本去重、日志、洞见、行动及反馈在重开后完整保留；Markdown 包含用户正文。
3. PDF 页面相对锚点、进度和具体电子版本外键。
4. 跨月/跨年阅读按实际完成日期单次统计，计划与事实分开。
5. 完整备份恢复所有关系记录和原书；自动保存恢复前备份。
6. 无效备份不会替换当前书库。
7. SQLite v1 重开保留资料，拒绝无法支持的较新数据库版本。
8. 外键失败后事务完整回滚。

`npm run test:desktop`：实际 Electron 窗口中的 12 项验收通过：

1. 首次启动空书库；renderer 不可使用 Node require。
2. 纸质书、资料编辑、富文本主读后感自动保存及历史版本恢复。
3. 阅读日志自动保存/格式化、洞见提炼、行动状态与实践反馈。
4. native dialog 对接的 PDF/EPUB 导入、重复和损坏文件处理，包括缺失正文的 EPUB。
5. PDF canvas、实际 TextLayer 选文、高亮、鼠标笔迹和撤销/重做。
6. PDF 直线、圆圈、文本框、整体橡皮擦、撤销恢复和评论。
7. PDF 缩放后高亮宽度与 viewport 比例一致，窗口尺寸变化不改锚点。
8. EPUB 整段选文、CFI 高亮、字号/窗口重排后覆盖多行；iframe 无本机 API。
9. 年度目标与月度计划保存。
10. 退出并重启后，所有资料快照一致，PDF 页码和全部批注恢复。
11. EPUB 退出并重启后高亮恢复。
12. native backup / restore 对接保存完整书库。

测试脚本通过 Playwright 操作实际桌面 renderer 和主进程。为自动化，系统文件对话框在测试中返回固定样本路径，恢复确认返回测试批准；文件导入、SQLite、reader 和备份代码均为生产实现。没有把浏览器演示当作桌面验收。

测试截图和完整结果在 `test-results/desktop-development/`，该目录被 Git 忽略。测试记录中没有意外 renderer 错误；EPUB 的脚本禁止信息单独记录为 sandbox 拦截，不视为应用错误。

`npm audit --omit=dev`：0 项已知运行时漏洞。开发工具剩余提示见已知限制。

## Windows 安装

已构建 `release/ReadingOS-0.1.0-win-x64-setup.exe`，119,492,635 字节，约 114 MiB。静默安装验收退出码为 0，实际生成 `ReadingOS.exe`；安装测试产物随项目保存在 `test-results/installed`。最终用户不需要开发运行时。

安装后的应用通过同一套 12 项完整桌面验收，无意外 renderer 错误，`info.packaged` 为 `true`；结果记录为 `test-results/desktop-packaged/results.json`。截图在捕获时显示实际窗口，核对了 PDF 绘图位置与 EPUB 重排后的整段高亮。

## 验证范围

初次 v0 → v1 建表和已有 v1 保留已测试；不存在历史产品数据库，尚无 v1 → v2 的真实升级迁移。本机安装及运行不等于不同 Windows 设备的 beta 反馈。系统文件选择器的人工交互、辅助技术、超大书库、不同 EPUB 出版商的复杂排版仍需要 beta 实测。
