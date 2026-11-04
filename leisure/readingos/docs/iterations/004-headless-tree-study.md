# Headless Tree 源码与集成

2026-11-04。上游 [lukasbach/headless-tree](https://github.com/lukasbach/headless-tree)，工程外浅克隆 `D:\ReadingOS-research\headless-tree`，检出 release 提交 `8a96358a139c4793f8e572201fd714d1a2d26e83`，与 npm gitHead 和 core/react 1.8.0 标签一致。精确依赖 `@headless-tree/core@1.8.0`、`@headless-tree/react@1.8.0`，React peer 为 `*`，在本项目 React 19 实际运行。MIT，Copyright (c) 2023 Lukas Bach；版权及许可全文进入 THIRD_PARTY_NOTICES。

阅读 readme、[官方入门](https://headless-tree.lukasbach.com/getstarted/)、React `src/use-tree.tsx`，core 的 sync-data-loader、selection、hotkeys-core、search、renaming feature/types，以及 general/basic-styling 示例。

`useTree` 保持 createTree 实例并更新 config/state；sync loader 从当前 SQLite snapshot 读取节点与子 ID；实例输出可见项的平面列表，层级/ARIA/展开由库负责。selection 将选中 ID 传回书架，hotkeys-core 处理方向键与选择，search 使用真实匹配函数按完整学科路径查找。ReadingOS 调用 `getContainerProps`、`getItems`、`item.getProps`、`getItemMeta`、`isExpanded`、`isSelected`，没有递归假树。修改目录后 rebuildTree，保持 UUID。

调用链：SubjectTree → useTree / syncDataLoaderFeature / selectionFeature / hotkeysCoreFeature / searchFeature → 当前 subject_categories；选择 → LibraryBrowser → subjectBooks 后代集合 → book_subjects 去重 → 原有 Book 卡片。树不直接写 SQL。

自主业务：目录防环/深度/同名校验、分类 CRUD 与排序、批量归属及主分类、父类计数、搜索 AND 规则、时间语义、迁移与事务；样式继续用暖纸与松绿。官方 renaming 已研究，本轮使用统一编辑对话框，同时修改名称、父级和排序；拖拽不启用。后续升级先核对同版本 tag/gitHead/许可，再复测键盘、search、rebuild 与所有业务约束。

同步迁移完整归档使用 fflate 0.8.3 的 zipSync，避免同步 Store 构造期间在完整恢复材料生成前开始迁移；备份读取仍保留 JSZip。MIT 许可随清单分发。
