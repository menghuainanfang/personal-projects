# 设计变量

唯一样式来源为 `src/style.css`，领域行为不依赖主题。

| 变量 | 浅色 | 深色 | 用途 |
| --- | --- | --- | --- |
| bg | #f5f2ec | #20251f | 应用背景 |
| panel | #fffdf7 | #282e27 | 编辑器、工具与对话框 |
| side | #e9e3d8 | #252b24 | 导航及辅助区域 |
| ink | #242925 | #e9e6dd | 普通正文 |
| muted | #5f655c | #b2b8ac | 日期、标签、辅助文字 |
| line | #d5d1c7 | #495144 | 内容分组边线 |
| accent | #526554 | #b5c9ae | 主要动作与链接 |
| accent-soft | #e2e8dd | #374532 | 选中状态 |
| danger | #944735 | #efac99 | 删除与错误 |

高亮默认 #dcc776，另有绿/蓝/粉，允许自定义；铜棕未用于小字动作，因为辅助文字需要明确对比度。每书独立保存阅读配色；PDF 背景仅改变页外区域。

字体：界面 Segoe UI → Microsoft YaHei UI → Microsoft YaHei → sans-serif；书名/大标题 Noto Serif CJK SC → Source Han Serif SC → SimSun → Georgia → serif。没有附带字体文件。普通 UI 14px、正文 16px/1.9、辅助 12px、书名大标题 28–30px。真实 EPUB 字号由读者设置，PDF 不改原文。

间距 4/8/12/16/24/32px；主区横向 40px，窄窗口 24px。按钮/表单圆角 6px，面板/弹窗 8px；边线 1px。阴影仅限浮层和原书纸张。背景切换 120ms，减少动态效果时移除过渡。焦点使用 2px 主色轮廓，外扩 3px。

书架单封面 176×224px 上限；缩略图 88×124px。书名保留完整可访问名称，视觉多行截断；原图保持自然宽高比。导航在 CSS 宽度 850px 以下收为 72px 图标栏，名称保留在 aria-label/title。
