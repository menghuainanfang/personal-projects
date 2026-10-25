# 微迭代 002 验收

日期：2026-10-20。版本：**0.2.1 本机候选版**。功能分支：`readingos-micro-002`。构建、Windows 安装及安装后验收完成；源码以独立 Pull Request 提交审查，GitHub Release 尚未发布。

## 交付物

- 本机源码：`D:\桌面\ReadingOS\projects\readingos`；远程对应 `leisure/readingos`。
- 安装包：`release/ReadingOS-0.2.1-win-x64-setup.exe`，131,729,260 字节（约 125.63 MiB）。
- 实际安装：`test-results/installed-micro002/ReadingOS.exe`，安装退出码 0；应用报告 version 0.2.1、packaged true。
- 研究：[PapaParse 源码学习记录](002-papaparse.md)。
- 截图：`screenshots/micro-002/before.png`、`after.png`、`preview.png`、`csv-mapping.png`、`preview-125.png`、`preview-150.png` 和 `installed-plan.png`。

## 执行结果

| 验证 | 结果 | 检测的具体问题 |
| --- | --- | --- |
| v0.2 阅读计划基线 | 1 项通过 | 改计划不能改状态、完成日期、目标或覆盖旧月份 |
| 生产构建 | 通过 | TypeScript 接口、PapaParse 打包、共享模块和 PDF 静态资源是否完整 |
| 数据/算法测试 | 21/21 | 原有 10 项、书单新增 11 项；包括引号、BOM、空行、限制、匹配、均衡、容量、幂等和真实 SQL 回滚 |
| 新功能源码 Electron | 9/9 | 实际表单与 CSV/TSV File、预览、排期、保存、重启 |
| 新功能安装版 Electron | 9/9 | 相同功能在 app.asar 和实际安装后可运行，无 pageerror |
| 基础阅读回归（源码/安装版） | 各 12/12 | PDF/EPUB、批注绘图、富文本/日志/实践、计划、重启、备份恢复 |
| v0.2 专项回归（源码/安装版） | 各 6/6 | 阅读偏好、引用日志/来源定位、资料升级、主题、36 组视口与键盘 |
| 运行时依赖审计 | 0 项已知漏洞 | 新增 npm 依赖没有引入已报告的运行时漏洞 |

数据结构仍为 `PRAGMA user_version=2`，没有数据库迁移。主进程批量事务只插入缺失 books/plans，已有 book 行不更新；原有数据测试和快照比较验证读后感、日志、偏好、目标等保持原值。

## 用户验收对应

| 要求 | 实际验证 |
| --- | --- |
| 1. 粘贴 10 本书生成预览 | 10 条显示，预览前后数据库快照相同 |
| 2. 带表头 CSV 提取书名、作者 | 自动别名及手工映射两条路径，实际浏览器 File 选择 |
| 3. 逗号、引号、长中文标题 | 标题/作者与原始值相等；另测引号内换行、BOM 与保留 001 |
| 4. 4 本已有书不重复创建 | 10 条首次导入只创建 6 本，4 个原 book ID 和元数据保留 |
| 5. 三个月顺序安排 | 2026-11 至 2027-01；算法测试按月份配额再按输入顺序填入 |
| 6. 旧月份不覆盖 | 比较原计划集合全部保留，年度/月度目标与完成状态保持原值 |
| 7. 手动改月与排除 | 第 5 条改为 2027-01 并保存；临时排除条目后待安排数相应减少 |
| 8. 重复导入不重复计划 | 第二次新增 0、安排 0、重复 10；同批完全相同条目只产生一书一月关系 |
| 9. 数据库出错整批回滚 | 在隔离数据库安装真实 SQLite 触发器，让第二条插入报错；整批所有行与操作前相同 |
| 10. 关闭重启仍保留 | 安装程序关闭重开，全部书目/计划/目标快照相同 |
| 11. 原阅读功能保留 | 最终安装版 12 项基础与 6 项 v0.2 回归通过，包括备份→恢复和原书副本 |

新增验收还覆盖书库多选、无作者人工确认、同名不同作者确认新建、容量不足提示与保存阻止、无效记录排除、超过 2 MiB/500 条、非 UTF-8 拒绝、Tab 约束/Esc/焦点返回、错误焦点，以及 HTML 样式书名只作为文字显示。

## 证据与复现

本机证据：

- 安装：`test-results/micro002-installation.json`。
- 新功能安装版：`test-results/micro002-installed-vOF9FQ/results.json`。
- 基础安装版：`test-results/desktop-packaged/results.json`。
- v0.2 安装版：`test-results/v02-installed/results.json`。
- 每次新功能测试创建独立 `micro002-*` 目录，并在执行前保存 `before.readingos`。样本由测试脚本内的原创书名生成，不使用私人书单。

```powershell
npm test
npm run build
npm run test:micro002
npm run test:desktop
npm run test:v02
$env:ELECTRON_BUILDER_COMPRESSION_LEVEL = '5'
npm run package
Remove-Item Env:ELECTRON_BUILDER_COMPRESSION_LEVEL
# 安装到测试目录后，指定实际安装程序运行同样三套桌面测试
$env:READINGOS_EXECUTABLE = "$pwd\test-results\installed-micro002\ReadingOS.exe"
npm run test:micro002
npm run test:desktop
npm run test:v02
Remove-Item Env:READINGOS_EXECUTABLE
```

原始 v0.2.0 安装程序可通过 `READINGOS_EXECUTABLE` 配合 `node tests/micro002-desktop.cjs --baseline` 验证。默认测试使用 node_modules 内 Electron 加载实际生产 dist；安装版加载打包资源，两者都使用隔离的数据目录并模拟网络离线。

## 界面与验证边界

Before 来自 v0.2.0 安装版，after 是相同初始四书测试书库完成导入后的页面；均为 1380×920 窗口。原有年度目标、月度目标与年度统计布局保留，仅标题附近新增入口。输入区域生成后收起，预览使用紧凑分隔行；长中文标题换行，不增加新的 UI 框架。

新对话框在 1280×720 窗口、125%/150% Chromium 缩放下检查外框和弹窗横向溢出，滚动到预览后仍能修改月份和确认。实际 CSS 视口分别为 1013×527、844×439，DPR 2.5/3。Windows 全局 DPI 没有更改；超出视口的长表单通过内部滚动访问。原有 36 组视口回归另外通过。

安装包未签名，其他 Windows 设备、屏幕阅读器和平台专用导出仍未验证。支持范围和后续建议集中见学习记录的「限制与后续」及 `../known_issues.md`。发布 GitHub Release 需要用户确认本轮结果和授权。
