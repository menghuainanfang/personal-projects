# 架构与数据库

## 应用边界

`electron/main.cjs` 管理桌面窗口、权限、native 文件对话框和固定 IPC 入口。`electron/preload.cjs` 只向主 renderer 暴露 ReadingOS 业务操作。renderer 不持有 Node、SQLite 或任意本机文件访问权。

`electron/store.cjs` 是阅读模块的资料库与管理文件服务；`src/domain.ts` 定义前后端边界。`src/App.tsx` 提供书库、书籍主页、洞见/行动与目标。`src/Editor.tsx` 使用 Tiptap 保存用户正文。`src/reader/Reader.tsx` 管理工具模式、批注历史和侧栏；PDF / EPUB adapter 各自负责渲染与位置转换。

未来模块可以增加自己的领域实体和页面，复用窗口与 persistence 边界。本版没有云服务、账户、插件框架或后台遥测。

## SQLite v1

数据库在 Electron userData 目录的 `library.sqlite`，原书在 `assets/<UUID>.pdf|epub`。foreign_keys 开启，WAL 日志和 FULL 同步用于可靠提交。`PRAGMA user_version=1` 标识本版结构；首次建表和版本写入在同一事务中。再次打开 v1 不重建表；数据库版本高于支持范围时拒绝打开。后续升级应在 `Store.open()` 添加逐版本事务迁移，不删除已建数据库。

| 表                 | 作用和关系                                                                       |
| ------------------ | -------------------------------------------------------------------------------- |
| books              | 逻辑书；标题、作者、封面 data URL、标签、分类、状态、开始/完成日期               |
| assets             | book_id 外键；具体 PDF/EPUB 版本；唯一导入内容 hash 和管理文件名                 |
| progress           | asset_id 主键；PDF page/scroll JSON 或 EPUB CFI                                  |
| annotations        | asset_id 外键；kind、anchor JSON、color、width、选文、评论；不保存渲染器私有结构 |
| summaries          | 每书唯一置顶主读后感；Tiptap HTML                                                |
| summary_revisions  | 每次内容变化的完整版本；相同内容不重复写入                                       |
| journals           | 多篇日志；书、日期、标题、HTML、来源批注 ID / 章节说明                           |
| insights           | 独立洞见；标题、内容、创建/更新时间                                              |
| insight_links      | 洞见与多书、批注、日志的关系；source 被删除时保留洞见                            |
| actions / feedback | 源洞见和可选书籍、计划日期、状态、多条实践反馈                                   |
| goals              | period 主键；年或年月与目标本数                                                  |
| plans              | book_id + month 联合主键；计划与完成日期分离                                     |
| bookmarks          | asset_id、位置、标签                                                             |

实体 ID 是 UUID；数据库中的原书路径由程序创建，不使用用户书名拼接。哈希只在导入时用于查重，匹配后跳过解析与复制。不同电子版本作为不同 asset，可以关联同一 book，但不共享位置和批注。

## 阅读坐标

PDF 渲染保持页面原始方向。高亮保存 `{page,rects:[[x,y,w,h],...]}`，绘图保存 `{page,points:[[x,y],...]}`。坐标以页面左上角为原点、页面宽高为单位，均为 0–1 的相对值；显示时乘当前 viewport 尺寸。原文和 SVG 批注同属于一个页面容器，一起滚动。更改 zoom 会重新渲染 canvas / TextLayer 并重新投影 SVG。

EPUB 保存 `{cfi}` 与完整选文；selected 事件中的 DOM Range 先将元素边界转为文字节点边界，再通过 contents.cfiFromRange 生成锚点。位置来自 relocated。高亮由 rendition.annotations 恢复，点击批注通过 display(CFI) 跳转。重排影响显示页面，不改变当前版本内容树的锚点。未实现跨版本锚点迁移。

默认工具是选文，SVG 不接收 pointer。显式选择手绘/形状/文本工具后才接收主鼠标按键；中键、滚轮和右键不创建绘图。橡皮擦删除完整笔画或批注。撤销/重做历史针对当前阅读器会话，记录写入数据库。

## 保存与备份

正文每次修改都立即提交，保存状态以 IPC 完成为准；主读后感版本和当前正文在一个事务内提交。数据库 WAL 支持异常退出后的已提交资料恢复。尚未显示「已保存」的输入仍可能在异常退出时丢失。

备份通过 SQLite `VACUUM INTO` 创建一致快照，将数据库及引用的 assets 压缩为 `.readingos`。恢复先解压到应用目录下的 staging，检查版本、数据库完整性、外键、必须表和原书是否完整；验证失败不替换当前数据库。验证通过后先备份当前资料，再交换文件并重开资料库。恢复前备份留在数据目录。用户可选择 Markdown 导出一本书的主读后感和日志。

资料库升级与卸载不删除 userData。源码 Git 忽略数据文件、运行时目录、书籍样本输出和备份；安装包只包含应用资源。
