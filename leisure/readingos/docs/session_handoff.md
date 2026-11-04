# ReadingOS 维护交接

2026-11-04。当前本机候选版 v0.4.0，开发分支 `readingos-v04-library-knowledge`。实际仓库 `D:\桌面\ReadingOS`，应用 `projects/readingos`；远程 `menghuainanfang/personal-projects` 的应用目录为 `leisure/readingos`。实施基线 cf202b5 / 远程 main 90c292a（v0.3）；本轮不合并 main、不发布 Release，正式 Release 仍为 v0.2.0。

## 当前能力

时间书架区分加入/开始/完成/计划，保留未记录区域；Headless Tree 1.8.0 提供真实多层目录、展开、路径查找和键盘；同书多学科、主分类、父类去重、批量添加/移除/替换。目录事务防环/同名/超六层，只删除空类。搜索与状态和目录是 AND，空格词全部匹配。书籍主页路径可跳转，主心得仍置顶。

SQLite 当前为 schema v3：subject_categories / book_subjects。旧 category 不拆分，迁入“旧分类/待整理”；旧书、UUID、资产、日期和阅读表不改写。升级前同步生成 before-v3-时间戳.sqlite 与完整 .readingos。v1/v2 staging restore 顺序升级，v3 恢复保留分类 ID。容器 format 仍为 1。降级不能删表，执行 `iterations/004-data-migration.md` 的旧完整备份恢复步骤。

## 资料与运行

真实完整备份和一致快照位于仓库外 `D:\ReadingOS-private-backups\before-v04-2026-11-04T03-05-59-251Z`，归档 6,022,313 字节；已核对数据库、外键及全部原书引用。个人资料没有被测试升级。全部测试使用隔离 READINGOS_TEST_DATA。

候选安装包 `release/ReadingOS-0.4.0-win-x64-setup.exe`，133,616,566 字节；实际隔离安装位置 `test-results/installed-v04/ReadingOS.exe`，NSIS 退出码 0。设置 ELECTRON_BUILDER_COMPRESSION_LEVEL=5 后 `npm run package` 可重新构建。

34 项数据/算法、安装版 12 项基础、6 项 v0.2、9 项导入、8 项日期/工作台、7 项新书架均通过；实际结果数组见 `iterations/004-evidence.json`。`npm run test:v04` 使用全新原创 20 本资料；`tests/legacy-fixture.cjs` 生成真正的 v1 表集合，不能把新表写入旧快照定义。截图对照见 `iterations/004-visual-review.md`。

## 关键代码

- electron/store.cjs / library.cjs：迁移、完整归档、分类事务、备份恢复。
- electron/main.cjs / preload.cjs：固定 library IPC，沿用主窗口 sender 检查。
- src/domain.ts：SubjectCategory、BookSubject、LibraryRequest 与 snapshot。
- components/library：时间/学科书架、官方 useTree 节点、目录编辑及批量归属。
- shared/library.mjs / .d.mts：本地月份、后代并集、路径和 typed 知识投影。
- 原 PDF/EPUB、主心得、来源、DayPicker、PapaParse 工作流保留；原有文档及验收资料继续可用。

## 依赖与后续

Headless Tree core/react 1.8.0 对应 release commit 8a96358a139c4793f8e572201fd714d1a2d26e83，研究仓库在 `D:\ReadingOS-research\headless-tree`；MIT 声明随 THIRD_PARTY_NOTICES 分发。fflate 0.8.3 用于同步完整迁移归档。 npm 生产依赖审计 0，全依赖审计 18 项，详情见 known_issues。

未实现拖拽分类、手工跨书语义关系和力导向图谱；知识投影只输出真实分类/洞见关系，related_to 预留。未充分验证屏幕阅读器、多设备系统 DPI、大规模书库和多 GB 归档性能。下一步先采集真实书库反馈，再决定局部知识网络或渲染性能优化。未来发布前重新核对分支、数据库版本和现有个人完整备份。
