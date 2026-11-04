# schema v3 与回退

新增 subject_categories（稳定 UUID、单父、多根、六层上限、排序）和 book_subjects（Book 与学科多对多、可选主分类）。唯一索引以 COALESCE(parent_id,'') 区分根级，同父名称 NOCASE 防重；业务端额外规范化名称并拒绝同名、环和深度错误。每书最多一个主分类由部分唯一索引保证。

新建库直接建 v3。v1 顺序保留 before-v2.sqlite 并升级偏好表，再升级 v3；v2 升级前以 VACUUM INTO 保存一致快照，并同步生成包含全部原书的 before-v3-时间戳.readingos。归档完成才开始 BEGIN IMMEDIATE，完整性与外键检查通过才提交 user_version=3；错误回滚并关闭失败连接。

旧 category 原文保留，不拆分。非空旧值形成“旧分类/待整理”下的可见节点；相同名称复用，建立原 Book UUID 的主归属。新界面只管理关系表，原文本不作为第二个分类来源。tags、日期和旧业务表不改写，新书默认未分类。

固定 library IPC 只有 save/delete/assign 三项业务动作，main 继续检查主窗口 sender，Store 校验所有 ID 并执行事务。删除仅允许无子类且无归属的学科；批量 add/remove/replace 支持 1–500 本，任何失败全批回滚，不修改 Book 行或资产。

snapshot 和完整备份包含新表，容器格式仍为 1；staging restore 接受 schema 1/2/3，旧版本链式迁移并检查全部表/外键/原书，然后保留恢复前完整备份再交换资料。

## 回退到 v0.3

1. 在新版「资料与设置」保存当前完整备份，退出全部 ReadingOS 窗口。
2. 启动 v0.3 时先指定一个新的空资料目录，例如 PowerShell 设置 `$env:READINGOS_TEST_DATA='D:\ReadingOS-v03-rollback'`，再运行 v0.3 ReadingOS.exe；不能直接打开 v3 数据库。
3. 在旧程序的「资料与设置」恢复升级前的 before-v3-*.readingos（schema v2）或本轮仓库外 before-v04 完整备份。恢复会同时还原数据库和原书副本。
4. 确认旧书、批注与心得可读后保留新旧资料目录，日常启动使用对应目录；清除环境变量前确认默认 userData 仍是新版资料。回退副本不包含升级后新增分类及笔记，当前完整备份应保留。

不通过删表降级。个人库未用于破坏性迁移；20 本原创旧书测试对全部旧表行、UUID、资产既有 hash 字段和原始文件字节做比较，另测真实回滚、v1/v2/v3 备份与重启。
