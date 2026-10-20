# v0.2 开源选择

2026-10-11 核对官方仓库 README、实际许可证、package 与依赖信息；桌面候选进一步检查源码。单一推荐：**保留 Electron、SQLite 和现有阅读引擎，局部引入 Radix Dialog**。完整 Fork 没有得到足以抵消数据迁移与同步成本的工程收益。

## 三条路线

| 维度 | Readest 整体 Fork | Koodo 整体 Fork | 现有外壳与局部组件 |
| --- | --- | --- | --- |
| 阅读覆盖 | 多格式、主题、注释；手写仍是 README 规划项 | 多格式、书架、笔记与备份 | 已有 PDF/EPUB、手绘、评论、书签；补充引用与设置 |
| 自有心得/日志/洞见/实践 | 需要增加领域实体与 UI | 需要增加领域实体与 UI | 14 张原有表直接保留 |
| 代码边界 | Next.js 16、Tauri 2、pnpm monorepo | React 18、Electron 34、CRA | React 19、Electron 44、Vite；一个新依赖 |
| 维护证据 | main 最后推送 2026-10-11 | dev 最后推送 2026-10-11 | 依赖固定锁文件，自有流程回归 |
| 数据迁移 | BookConfig/booknotes 与 SQLite 各实体映射；CFI/版本/关系转换 | Book key、md5、location 与 SQLite UUID/asset 映射 | 仅新增 reader_preferences，事务迁移 |
| Windows 打包 | 当前缺 Rust/C++；需补 Tauri 工具链再验收 | Electron 接近，但原工程打包与依赖需重验 | 已有 NSIS 安装路径与运行时 |
| 可访问性 | 有响应式和键盘入口，未本机验证整体应用 | 未本机验证整体应用 | Radix 对话框实际 Tab/Esc/恢复焦点测试 |
| 安全边界 | 引入网络、同步、额外文件协议面，需重新审视 | 引入云服务、多种存储依赖，需重新审视 | 保留受限 preload、离线与原书副本 |
| 许可证 | AGPL-3.0，衍生分发与源码提供义务 | AGPL-3.0，衍生分发与源码提供义务 | 自有 MIT，依赖按实际许可保留声明 |
| 上游同步成本 | 自有领域插入大量 reader 状态/UI，需持续合并 | 相同且栈升级方向不同 | 依赖更新限于组件接口，不同步整套产品 |
| 视觉控制 | 需改既有产品大范围主题和布局 | 需改既有产品大范围主题和布局 | 原有领域布局可以直接调整 |

Readest 实查 [BooknoteItem.tsx](https://github.com/readest/readest/blob/main/apps/readest-app/src/app/reader/components/sidebar/BooknoteItem.tsx)：注释以 bookKey/CFI 为核心、来源链接与 bookConfig 更新。Koodo 实查 [Book.ts](https://github.com/koodo-reader/koodo-reader/blob/dev/src/models/Book.ts)、[databaseService.ts](https://github.com/koodo-reader/koodo-reader/blob/dev/src/utils/storage/databaseService.ts)：模型和存储不能直接读取 ReadingOS 的全套关系。两者没有在本机安装运行，也没有声称完成迁移验证。

## 组件与产品证据

| 官方来源 | 实际许可、维护与决定 |
| --- | --- |
| [PDF.js](https://github.com/mozilla/pdf.js) | Apache-2.0；master 推送 10-10；保留 5.4.624、文字层/归一化 SVG，继续现有实际回归 |
| [epub.js](https://github.com/futurepress/epub.js) | 实际 `license` 为 BSD-2-Clause，API 标识 NOASSERTION 不作为结论；master 推送 03-24；保留 0.3.93 与 CFI |
| [foliate-js](https://github.com/johnfactotum/foliate-js) | MIT；main 推送 05-01；README 明确 API 不稳定。替换需要重验所有 CFI、重排与备份，当前不替换 |
| [react-pdf-highlighter-extended](https://github.com/DanielArnould/react-pdf-highlighter-extended) | MIT；main 推送 2024-11-22；package 8.1.0 使用 React 18.3/PDF.js 4.4，与当前 React 19/PDF.js 5 不吻合。当前已有手绘与坐标流程，不强制安装验证不匹配版本 |
| [Tiptap](https://github.com/ueberdosis/tiptap) | MIT 开源核心及本项目扩展；main 推送 10-09；保留已有 HTML 数据和编辑器 |
| [shadcn/ui](https://github.com/shadcn-ui/ui) | MIT；main 推送 10-10；实查 new-york-v4 `dialog.tsx`，其底层为 Radix。直接使用 headless primitive，独立编写样式 |
| [Radix Dialog](https://www.radix-ui.com/primitives/docs/components/dialog) | MIT；实际安装 1.2.0，peer 支持 React 19；Root/Portal/Overlay/Content/Title 实际集成所有表单，原始 LICENSE 随 notices |
| [Mantine](https://github.com/mantinedev/mantine) | MIT；master 推送 10-11；成熟组件体系，但为一个对话框引入另一套主题和样式没有收益，未安装 |
| [Foliate](https://github.com/johnfactotum/foliate) | 桌面 GPL-3.0，gtk4 推送 04-08；GJS/GTK/libadwaita/WebKitGTK 依赖不适合现有 Windows 栈。参考安静阅读，未复制代码 |
| [Zotero 阅读器](https://www.zotero.org/support/pdf_reader) | 官方交互说明验证批注→来源笔记→原文；参考来源链和密度，未复制代码/资产 |
| [BookLore](https://github.com/booklore-app/booklore) | AGPL-3.0；develop 推送 10-09；README 声明 maintenance mode，活跃后继为 BookOrbit。Docker/Java/MariaDB 与本地桌面目标不同；只参考封面秩序 |

临时研究缓存位于 Git 忽略的 `research/v02/`，包含官方 README/LICENSE/package、查询日期和维护元数据。缓存不是分发代码。新增组件的技术验证使用实际生产程序和 SQLite：`tests/v02-desktop.cjs`；不是独立的静态演示。

## 分发与资产

没有复制 Readest、Koodo、Foliate、BookLore 源码、商标或封面。封面占位为本项目文字与颜色排版；样本为原创 CC0；系统字体只引用名称，不打包字体。图标仍是 lucide 的 ISC 许可资产。原创代码 MIT，所有运行时依赖版权与全文许可由 `npm run notices` 写入 `THIRD_PARTY_NOTICES.txt`，安装包包含该文件。保留 PDF.js Apache 许可及运行时自带声明。
