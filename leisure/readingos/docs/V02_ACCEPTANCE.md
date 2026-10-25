# ReadingOS v0.2 验收

2026-10-11，Windows 11 x64。生产构建、安装包生成、实际安装及安装后的验收均通过。本机源码保存在 `readingos-v0.2` 分支；2026-10-20 已同步到远程 main 的 `leisure/readingos`，标签 `readingos-v0.2.0`。

## 交付

- 安装包：`D:\桌面\ReadingOS\projects\readingos\release\ReadingOS-0.2.0-win-x64-setup.exe`，131,693,717 字节（125.59 MiB）。NSIS 当前用户安装，压缩等级 5，自带运行时。
- 实际安装：`D:\桌面\ReadingOS\projects\readingos\test-results\installed-v02\ReadingOS.exe`；退出码 0，应用报告 `version=0.2.0`、`packaged=true`。
- 核心实现提交：`5954c81`；阅读器内来源定位：`808ae1f`；基线与开源选择：`1c8865a`。
- Before/after 六个场景、两个候选、五个深色场景位于 `screenshots/`，内容均为原创样本。

## 实测结果

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| TypeScript 和生产资源构建 | 通过 | `npm run build`，包含 PDF worker、CMap 与字体资源 |
| 持久化、导入、关系、迁移、备份、导出 | 10/10 | `tests/store.test.cjs` |
| 原有源码桌面流程 | 12/12 | `tests/desktop.cjs`，源码版实际 Electron |
| 最终安装版原有流程 | 12/12 | `test-results/desktop-packaged/results.json`，无意外 renderer 错误 |
| 最终安装版新版专项 | 6/6 | `test-results/v02-installed/results.json`，无 pageerror |
| 实际 v0.1 完整流程备份升级 | 原有 14 表逐行相等、2 份原书逐字节相等 | `test-results/v02-v1-workflow-validation/results.json` |
| 新克隆环境测试资料生成 | 通过 | `tests/legacy-fixture.cjs` 生成 v1 结构，恢复后完整关系和原书可用 |
| 运行时依赖审计 | 0 项已知漏洞 | `npm audit --omit=dev --registry=https://registry.npmjs.org` |

安装版原有流程覆盖空书库、纸质书、元数据、长文/富文本自动保存及重开、日志→洞见→行动→反馈、PDF/EPUB 导入与查重、损坏输入、PDF 选字/高亮/鼠标手绘/形状/文本框/橡皮擦/撤销重做、缩放与调整窗口后归一化坐标、EPUB CFI 重排与重启、计划和完成日期分离、原书副本、Markdown 导出、完整备份恢复。EPUB 中脚本被沙箱阻止的预期提示单独记录，不当作正常页面错误。

新版专项六项：

1. 实际 v1 截图书库备份进入 v2，所有已有行与原书副本不变。
2. 书架一键阅读 → 选文写评论 → 引用到日志 → 保存；从主页返回原页，以及已打开同一本书时从日志弹窗重新定位。
3. PDF 缩放/线宽/自定义颜色与背景保存，EPUB 字号/行距/颜色独立保存；应用重启后恢复且 CFI 高亮仍存在。
4. 书库、主页、日志弹窗和 PDF 阅读器各 9 组视口检查，共 36 组；应用外框无横向溢出、主要工具在视口内；Tab 留在对话框，Esc 后焦点回到入口。
5. 实际主题开关切换深浅色，书库/主页/编辑器/PDF/EPUB 截图；EPUB 正文实际背景验证；普通正文、辅助文字、选中导航和主要按钮配色达到 AA，减少动态效果时过渡为 0。
6. 删除来源批注后日志仍保留，明确显示来源已删除，不出现错误的原文跳转入口。

新版验收在 Chromium 网络离线模拟下执行，阅读与所有资料操作继续可用；没有断开 Windows 的全局网络。文件选择器由自动测试提供原创文件路径，文件读取、SQLite、渲染器、保存与备份均执行实际程序。

## 旧资料保留

实际 v0.1 流程备份的记录数量：books 3、assets 2、progress 2、annotations 6、summaries 1、summary_revisions 4、journals 1、insights 1、insight_links 1、actions 1、feedback 1、goals 1、plans 1、bookmarks 0。所有原始列、UUID、来源关系与内容逐行相等。含非空书签的完整旧结构另由迁移测试验证。

`Store.open()` 对原生 v1 数据库先保存 `before-v2.sqlite` 再事务新增阅读设置；v1 备份在恢复 staging 内迁移。读后感、版本历史、日志、观点、实践和原书不改格式。新版完整备份包含阅读设置，已验证恢复与重开。

## 视觉和视口

Before/after 均为浅色、1366×768 桌面窗口、同一六书原创书库；capturePage 保存原生像素截图，包含批注与编辑器，不是手绘界面。深色截图来自最终安装版，独立保存在 `screenshots/after/*-dark.png`。

视口矩阵为窗口 1280×720、1366×768、1920×1080 × Chromium 缩放 100%/125%/150%。实际 CSS 内容尺寸、devicePixelRatio 与缩放逐组写入结果 JSON；本机基础 DPR 为 1.25，150% Chromium 缩放时为 1.875，最窄 CSS 内容约 845px。测试等待实际尺寸到位后再检查边界。PDF 固定页内保留局部横向滚动；窄视口可通过专注模式或侧栏开关扩大阅读区，长弹窗内部滚动且保存入口保留。

## 验证边界与未实现项

Windows 全局 DPI 未更改，其他机器/显示器、屏幕阅读器、朋友实际 beta、出版商复杂 EPUB、超大文档仍未验证。自定义阅读色由读者选择，AA 检查针对内置主题。连续 PDF、OCR、带批注 PDF 导出、跨版本锚点迁移仍未实现。安装包未签名，具体限制见 `known_issues.md`。

v0.2 源码和 Windows 安装包已于 2026-10-20 按用户授权发布。不存在阻塞本机使用的已知问题。

## 复现

```powershell
npm test
npm run build
npm run test:desktop
npm run test:v02
node tests/verify-v1-backup.cjs test-results/v02-v1-workflow.readingos
$env:ELECTRON_BUILDER_COMPRESSION_LEVEL = "5"
npm run package
Remove-Item Env:ELECTRON_BUILDER_COMPRESSION_LEVEL
$env:READINGOS_EXECUTABLE = "$pwd\test-results\installed-v02\ReadingOS.exe"
npm run test:desktop
npm run test:v02
Remove-Item Env:READINGOS_EXECUTABLE
```

安装版命令需先把新安装包安装到给出的测试目录；也可将 READINGOS_EXECUTABLE 指向自己的实际安装位置。原始本机 v1 流程备份是审计产物，不进入 Git；验证脚本接受其他明确的 v1 `.readingos` 路径。新克隆运行 `test:v02` 会自动生成原创旧结构样本，无需私人数据库。
