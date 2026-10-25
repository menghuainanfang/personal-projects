# Mantine：工作台结构

研究日期：2026-10-25。上游 [mantinedev/mantine](https://github.com/mantinedev/mantine)，工程外浅克隆 `D:\ReadingOS-research\mantine`，研究提交 `194d652452ee060aad3796c121f9b6a9f74cb453`。实际安装精确版本 `@mantine/core@9.7.3`、`@mantine/hooks@9.7.3`。MIT，Copyright (c) 2021 Vitaly Rtishchev；完整声明随 THIRD_PARTY_NOTICES 分发。

阅读官方 [AppShell 文档](https://mantine.dev/core/app-shell/)、源码 `packages/@mantine/core/src/components/AppShell/` 中 AppShell、Navbar、Aside、Section、样式、`use-app-shell-resize` 和 `AppShellResizeHandle`。

- AppShell 通过 section 配置与 CSS 变量协调固定 Header/Navbar/Aside 和 Main 的留白。ReadingOS 直接运行这些组件，移除原来的固定左栏与手算左边距。
- Navbar/Aside 的 mobile、desktop collapsed 状态独立；断点决定固定栏是否占用正文空间。ReadingOS 在窄窗默认收起导航，上下文区作为可关闭浮层；正文继续保持一个滚动区。
- Section 的 grow 与 ScrollArea 组合，让标识、底部离线说明保持位置，中间导航和长书籍上下文独立滚动。
- `useAppShellResize` 通过 CSS 变量预览宽度，结束后报告 sizes；官方 handle 提供 pointer 和键盘交互。ReadingOS 限制 aside 为 240–380px，并保存最终宽度，没有重新编写拖动算法。
- MantineProvider 提供主题变量，官方样式负责布局与组件状态。项目使用真正的 NavLink、ActionIcon、Group、Tooltip、ScrollArea、Popover；不复制组件外观冒充复用。

自主实现的是阅读场景：四类页面路由、书籍标题、全局查找、继续阅读、上下文中日志/批注/洞见/行动的数据关联及来源跳转。Quiet Reading 的字体、暖纸色、松绿强调色来自现有项目；`ReadingThemeProvider` 与 `workspace.css` 将其接入 Mantine。旧按钮规则限定在非 Mantine/DayPicker 控件，body 显式使用原主题颜色，防止库的全局默认颜色改变原有阅读页。

PDF/EPUB 阅读器保留自己的工具与专注模式，打开时不渲染工作台外壳。实际源码通过 npm 使用；研究仓库不进入应用或公开仓库。
