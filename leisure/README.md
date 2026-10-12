# 兴趣与休闲项目

这里整理从个人兴趣和日常生活中发展出来的工具：探索生活记录中的数据，也让阅读、思考和实践更容易衔接。

## 项目索引

| 项目 | 主要用途 | 当前状态 | 入口 |
| --- | --- | --- | --- |
| 空间研究室 · Qzone Lab | 探索 QQ 空间题材、配图和发布时间与点赞浏览的关系 | 初版已交付 | [介绍与运行](qzone-lab/) |
| ReadingOS | 本地阅读、批注、读后记录、洞见与实践管理 | v0.1 已发布，v0.2 更新中 | [介绍与下载](readingos/) |

## 空间研究室 · Qzone Lab

一个本地运行的个人动态分析工具。围绕“哪些日常更容易被回应”，分别观察浏览数、点赞数和每百次浏览获得的赞数，再按题材、配图、年份和发布时间比较。

### 功能与体验

- 在独立 Edge 窗口扫码登录，采集本人说说及明确的互动总数。
- 导入 CSV、说说 JSON、QZoneExport 备份或包含说说列表的 HAR。
- 文字关键词初分主主题，支持人工修改与自定义主题。
- 按日期、主题和关键词筛选，查看配图、小时、星期、生日与节日差异。
- 比较同一年中的题材差异，显示重抽样区间，导出 CSV、JSON 和 Markdown 报告。

![空间研究室虚构数据演示](qzone-lab/assets/demo.jpg)

分析和文件导入需要 Python 3.10+；扫码采集另需 Windows Edge 和 Playwright。进入 `leisure/qzone-lab` 后运行 `python app.py`，Windows 也可以双击启动脚本。

项目已用于一次个人动态分析。公开演示包含 300 条模拟动态，日期、生日和纪念日由使用者自行设置。完整方法、测试与操作步骤见[项目 README](qzone-lab/README.md)。

## ReadingOS

面向 Windows 的本地阅读应用，将 PDF、EPUB 和纸质书放进同一个书库，以主读后感为中心，连接阅读日志、洞见和实践行动。

### 功能与体验

- 导入无 DRM PDF / EPUB，或添加纸质书。
- 阅读时高亮、评论、绘图并记录书签。
- 在书籍主页写主读后感和日志，整理洞见与实践反馈。
- 设置阅读目标和月度书单，备份本机资料，导出读后记录。

v0.1 已在 Windows 11 x64 完成安装验证；项目文档记录了 8 项持久化测试，以及源码版和安装版各 12 项桌面验收。v0.2 更新中。

- [下载 v0.1 安装包](https://github.com/menghuainanfang/personal-projects/releases/tag/readingos-v0.1.0)：Windows x64，应用自带运行环境。
- [中文用户指南](readingos/docs/user_guide_zh.md)、[测试结果](readingos/docs/testing.md)与[后续路线](readingos/docs/roadmap.md)。
- [开发与构建说明](readingos/README.md)：源码位于 `leisure/readingos`，使用 Electron、React、TypeScript、Vite、SQLite、PDF.js、epub.js 和 Tiptap。

## 数据与隐私

空间研究室把动态与设置保存在本机 `data/workspace.json`；公开演示使用虚构数据。ReadingOS 的书库与记录保存在本机 Electron userData，可通过 `.readingos` 文件备份。个人数据、本机配置、依赖与构建产物保留在各自使用环境。

## 限制

QQ 空间接口可能因登录状态、权限或限流而不可用；累计浏览数可能包含重复浏览，题材比较说明关联，不能作为因果结论。ReadingOS 安装包面向 Windows x64，具体功能边界见[已知限制](readingos/docs/known_issues.md)。

## 许可

原创代码与文档采用 [MIT License](../LICENSE)，各项目使用的第三方组件和数据保留原有许可。

[返回仓库首页](../README.md) · [学科与学习项目](../academic/)
