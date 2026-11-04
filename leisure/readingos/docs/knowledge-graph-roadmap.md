# 知识网络基础

实体 UUID 不随分类/时间改变。`shared/library.mjs::knowledgeGraph` 从真实 snapshot 输出节点和边，类型在 library.d.mts：book / subject / insight；categorized_as 来自 book_subjects，parent_subject 来自父级，derived_from 来自 insight_links 并携带原 link ID。时间只作为日期事实，不转成语义连线。related_to 是预留类型，只有未来用户明确建立关联后才能输出；本轮没有空的跨书关系表、手工跨书关联界面或随机图谱。

例：图书 B、学科 S、洞见 I 形成 B → S（categorized_as）与 I → B（derived_from，evidence 为 insight_links UUID）。后续图谱渲染器接受投影，不能改变领域 ID、分类计数或阅读完成统计。

[Obsidian 官方说明](https://github.com/obsidianmd/obsidian-help/blob/master/en/Plugins/Graph%20view.md) 将笔记作为节点，内部链接作为边，提供筛选、分组和当前笔记的局部图。ReadingOS 后续优先复用这种局部浏览思路，先让每条连线能回到来源，再考虑全局图。

[react-force-graph](https://github.com/vasturiano/react-force-graph) 为 MIT（Copyright 2018 Vasco Asturiano），提供相同数据接口的 2D Canvas、3D ThreeJS/WebGL 等独立包，graphData 使用 nodes/links，支持节点点击、缩放和平移。它进行迭代力模拟；CPU、动画及 3D 依赖增加运行负担。本轮没有安装。建议未来只评估独立 2D 包、按需加载、限制局部节点与停止闲置模拟；用实际书库测首屏和交互时间，不能推断为本轮已验证性能。

下一步先增加可解释、可编辑、可删除的“相关/对比/延伸”书籍关联及事务测试，届时建立 book_relations，禁止自关联和重复关系；然后增加真实局部图与来源跳转。结构关系、语义关联、日期事实分别标记。
