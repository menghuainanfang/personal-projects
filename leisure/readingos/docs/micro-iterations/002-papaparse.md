# 002 · PapaParse 与批量书单排期

日期：2026-10-20。版本：ReadingOS 0.2.1 本地候选版。目标是阅读计划中的一个完整动作：输入书单、检查匹配、分配月份、确认整批保存。

## 现有工程与资料

本机维护工程为 `D:\桌面\ReadingOS\projects\readingos`，GitHub 分类目录为 `leisure/readingos`。功能分支 `readingos-micro-002` 从本机 v0.2 工作副本创建；开始时工作区无未提交修改。README、architecture、known_issues、session_handoff 和原有数据/桌面测试已核对。

SQLite 继续使用 schema v2，复用 books 和 plans，不新增表、不迁移数据。修改前在工程外 `D:\ReadingOS-private-backups` 保存个人数据库的一致性快照；原书目录未参与测试。隔离书库还保存修改前 `.readingos` 完整备份，验证原有目标、月份计划、状态和完成日期。私有快照、数据库、书籍及导入文件均不进入 Git。

## 源码研究

研究目录：`D:\ReadingOS-research\PapaParse`，使用 `git clone --depth 1`，并浅取 `5.7.0` 标签；没有将上游仓库或其测试依赖纳入 ReadingOS。

检查的版本为 npm **papaparse 5.7.0**，与官方标签 [5.7.0](https://github.com/mholt/PapaParse/tree/5.7.0) 对照，标签提交 `555c1c1b6175e7a043adf8694983776a1e6fdeeb`。实际 [LICENSE](https://github.com/mholt/PapaParse/blob/5.7.0/LICENSE) 为 MIT，版权为 Matthew Holt，2015；运行时包使用精确版本，版权与完整许可进入 THIRD_PARTY_NOTICES，随安装包分发。

### 真正学到的解析机制

1. [papaparse.js](https://github.com/mholt/PapaParse/blob/5.7.0/papaparse.js) 的 Parser 扫描游标区分普通字段和引号字段。进入引号后，逗号与换行属于字段内容，连续双引号还原为一个引号；缺少闭引号会生成 MissingQuotes。CSV 不能用逗号和换行的两次 split 代替。
2. ParserHandle 负责分隔符猜测、空行、表头与结果转换，和底层字符扫描分开。guessDelimiter 评估候选列数及稳定性，单列文件可能返回 UndetectableDelimiter；这不等于书目无效，界面允许明确选择分隔符。
3. `header: true` 可产生字段名与 FieldMismatch，并会给重复表头改名，通过 meta.renamedHeaders 说明。ReadingOS 使用 `header: false` 保留原始列数组，以列序号映射，避免同名表头在映射时变得含糊；业务层另行报告列数不一致。
4. stripBom 处理开头 BOM；`skipEmptyLines: 'greedy'` 跳过空白及全空字段行。`dynamicTyping: false` 保留 `001` 等原始字符串。书名标点和作者不应被自动转换。
5. `step` 按逻辑记录返回数据及错误，`parser.abort()` 可在超过记录上限时停止。逻辑记录可能跨物理行；错误显示针对记录，不把引号内换行当成另一条书目。
6. FileStreamer 使用 FileReader 异步读浏览器 File，并支持分块。FileReader 的默认文本解码不能在这里满足严格编码拒绝，因此 ReadingOS 先检查 File.size，用 arrayBuffer 和 `TextDecoder('utf-8', {fatal:true})` 解码，再交 Papa.parse。读取局限于用户明确选择的文件。

实际阅读了 [README](https://github.com/mholt/PapaParse/blob/5.7.0/README.md)、[官方文档](https://www.papaparse.com/docs) 和 [tests/test-cases.js](https://github.com/mholt/PapaParse/blob/5.7.0/tests/test-cases.js) 中的引号内分隔符、引号内换行、转义双引号、缺失引号、空行、UTF-8 BOM、重复表头与 step 案例。项目新增自己的输入与事务测试，并未宣称运行了上游完整浏览器测试套件。

## 直接复用与自主业务

| 责任 | 实现 |
| --- | --- |
| CSV/TSV 字符语法 | PapaParse：引号、转义、换行、分隔符检测、BOM、空白记录、解析错误和逐条回调 |
| 本地 File 的许可与编码 | 浏览器文件选择器、2 MiB 限制、严格 UTF-8 解码；不增加任意本机文件读取 IPC |
| 纯文本 | ReadingOS：每行完整书名，仅 Tab 分作者，不按逗号、冒号、括号或破折号拆分 |
| 列映射 | ReadingOS：中文/英文别名建议，用户确认书名、作者、月份列；支持无表头、分号和竖线分隔 |
| 书目匹配 | ReadingOS：NFKC、空白及大小写规范化后比较书名/作者；同名不确定情况由用户确认，元数据不覆盖 |
| 计划安排 | ReadingOS：按已有负载计算月份新增配额，再依输入顺序填入；保留既有计划、手动与文件月份 |
| 保存 | ReadingOS：固定 batchPlans IPC、主进程再次校验/匹配、一个 SQLite 事务保存整批 |

PapaParse 不负责识别“是否同一本书”、安排阅读月份或更新 SQLite。

## 使用与业务规则

阅读计划标题旁选择「导入与安排书单」。支持粘贴文本、CSV/TSV 文件、从书库多选。写入前必须生成预览；修改输入或列映射会使旧预览失效。生成后收起输入区域，预览列表显示状态、作者与可修改月份；输入区可重新展开。

- 精确书名与作者匹配唯一条目时关联原 book ID。仅同名、作者缺失/不同、或书库已有多条精确候选时，要求选择关联书目或确认新建。
- 同批完全重复条目默认排除，标明与第几条相同；明确勾选后，自动排期共用首次出现条目的月份，主进程再次去重。同名但不同作者的新条目需要确认独立新建。
- 新书状态为想读，无电子文件；旧书状态、作者、完成日期及其他记录保持原值。
- 自动范围包含开始与结束月份；一次最多 120 个月。已有书在范围内已有计划时默认沿用最早月份，重复导入不会增加另一月份。
- 先把文件/手动月份计入新增负载，再给剩余书目计算均衡配额；相同负载优先较早月份，最后依输入顺序按月份填入。全部选择可复现，无随机数。
- 「每月最多新安排」限制本次新增关系，已有关系只参与负载权重；不是年度或月度目标。手动/文件月份可以在自动范围之外，仍受该月新增上限约束。
- 月份不足时显示待安排数量，确认按钮停用；用户可扩大范围、调整上限或明确排除条目。原计划不删除、不移动，目标数量不改变。
- 同一书的同月份关系只保留一份。新建、关联、成功安排、跳过、其中重复、无效失败分别反馈；数据库错误使整批回滚，显示失败条数及写入 0 条。

## 代码位置

- `shared/booklist.mjs`：PapaParse 适配、解析限制、匹配和排期纯函数，前后端使用同一身份规则。
- `shared/booklist.d.mts`：供 TypeScript 使用的明确接口。
- `src/BooklistDialog.tsx`：输入、列映射、预览、确认、手动月份及结果；复用 Modal/Radix。
- `src/App.tsx`：阅读计划入口与成功后的全量刷新。
- `electron/store.cjs`：batchPlans 校验、唯一 book ID 选择与事务；现有 books/plans 操作复用。
- `electron/main.cjs`、`preload.cjs`、`src/domain.ts`：只增加一项固定批量业务调用。

## 测试与界面

`tests/booklist.test.cjs` 验证解析、长度/条数、保守匹配、顺序均匀安排、已有负载、容量、重复条目共用月份、重开幂等、资料保留和真实 SQLite 触发器导致的回滚。`tests/micro002-desktop.cjs` 在隔离资料与离线模拟下操作实际 Electron，包括文件选择、列映射、手动月份、临时排除、重启和真实 IPC 回滚。原阅读功能继续使用 desktop 与 v02 两套回归。

截图在 `screenshots/micro-002/`：before 来自 v0.2.0 安装程序，after/preview 来自候选程序；均为 1380×920 窗口及原创书目。150% Chromium 缩放截图滚动到预览，长表单内部可滚动，保存入口保留。安装与最终测试结果见同目录 `002-acceptance.md`。

## 限制与后续

仅支持 UTF-8（含 BOM），最大 2 MiB、500 条、书名 500 字符、作者 200 字符。不会将未经专门验证的平台导出标成兼容。无原生 XLSX、在线图书检索或封面获取。CSV 解析在有限大小内同步完成，没有使用 worker 或流式超大文件导入。

匹配不推断版本、ISBN、别名或译名；不确定时人工确认。书库多选按书库顺序安排，单个条目可手动改月。对话框沿用原有暖纸/深色变量，125%/150% 使用 Chromium 缩放；Windows 全局 DPI、屏幕阅读器及其他设备仍需验证。

下一轮可继续完善列映射预设和大量书目预览的操作效率。若增加 CSV 导出，应单独验证 Papa.unparse 的 escapeFormulae 与目标电子表格软件的公式注入防护；本轮没有 CSV 导出入口。
