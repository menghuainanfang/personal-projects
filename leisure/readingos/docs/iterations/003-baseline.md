# v0.3 基线

2026-10-25。本机实际工程为 `D:\桌面\ReadingOS\projects\readingos`，版本 0.2.1；保留批量书单、PapaParse 与已有阅读工作流。开发分支 `readingos-v03-workspace-calendar` 从本机干净的 `fb48596` 创建。GitHub 应用目录为 `leisure/readingos`。

真实用户资料已通过只读 SQLite 一致快照与原书副本压缩为完整 `.readingos` 备份，保存在仓库外 `D:\ReadingOS-private-backups\before-v03-*`。备份大小 6,021,886 字节。全部开发测试使用 `READINGOS_TEST_DATA` 隔离目录。

修改前执行生产构建、21 项数据/算法测试、12 项桌面回归、6 项 v0.2 专项、9 项批量书单验收，全部通过。相同原创资料与 1366×768 窗口截图保存在 `screenshots/iterations/003/before/`，包括书库、书籍主页、PDF 阅读器、洞见、计划和日期编辑表单。原版日期使用浏览器原生控件，日期截图记录实际表单，不声称捕获了独立原生弹层。

原工作台固定 200px 左导航；没有全局上下文工具栏、可调整的书籍上下文区或统一日期网格。书籍主心得、PDF/EPUB 引擎、来源引用、偏好、完整备份与 schema v2 已正确工作，作为本次回归基础。
