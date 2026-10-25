# React DayPicker：日期网格与本地日期

研究日期：2026-10-25。上游 [gpbl/react-day-picker](https://github.com/gpbl/react-day-picker)，工程外浅克隆 `D:\ReadingOS-research\react-day-picker`，研究提交 `a3a3cd26fd5e43092ec9fb5839d64f9c07dadd2a`。安装 `@daypicker/react@10.0.2`，此包实际转出 `react-day-picker` 的实现与样式。MIT，Copyright (c) 2014–2026 Giampaolo Bellavite and contributors；完整许可在 THIRD_PARTY_NOTICES。

阅读 README、官方 [文档](https://daypicker.dev/)、`packages/react-day-picker/src/DayPicker.tsx`、`selection/useSingle.tsx`、`selection/useRange.tsx`、`useFocus.ts` 及安装包类型。

- DayPicker 将 calendar、selection、focus 分开管理；ReadingDatePicker 使用真实 `mode="single"`、受控 month/selected 与 onSelect，日期格、月份切换和方向键行为直接来自库。
- single 模式允许再次点击取消选择。ReadingOS 通过显式「清空」入口处理可空字段，必填字段保留选择；不把未选择当成今天。
- range 模式管理两个具体日期和 min/max/disabled 等日期约束。阅读排期存的是月份，不能将月份端点伪装为日范围，因此使用自主 MonthGrid 与确认式月份范围，具体日期仍由 DayPicker 渲染。
- `useFocus` 计算初始目标与方向键移动；caption dropdowns 与 `navLayout="after"` 使年/月、导航顺序一致。实际配置简体中文、周一开始、autoFocus，并用 Mantine Popover 限制弹层内 Tab。
- 本地日期不经 UTC ISO 序列化。`shared/dates.mjs` 用本地年月日生成字符串，严格解析后比较年月日拒绝日期滚动；2028-02-29 有效，2027-02-29 不保存。

ReadingOS 自主负责字符串校验、可空/必填业务、表单错误、月份网格、范围确认和 SQLite 字段映射。用户键入非法内容时保留草稿与错误，不把它发给父层或日志自动保存；选择合法日期后输入与网格同步。Esc 在日历层关闭并回到触发按钮，外层 Radix 表单继续保持打开。日历留在 Radix DOM 内，以 fixed 定位避免滚动表单裁切，没有新增第二套日期框架。
