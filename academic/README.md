# 学科与学习项目

这里整理课程实践、教材案例、数学学习工具和方法复现。重点是理解问题、独立实现方法、核对结果，并形成可以继续学习或扩展的成果。

## 项目索引

| 项目 | 主要内容 | 当前状态 | 入口 |
| --- | --- | --- | --- |
| Data Science Bookcamp 独立学习专题 | 概率模拟、统计推断、异常检测、文本分析与社交网络预测 | 计划中 | [专题介绍](data-science-bookcamp/) |
| 本地数学翻译工作流 | 数学 PDF 与 LaTeX 材料的中文翻译、编译和审校 | 本地整书翻译与精译流程已验证 | [使用与验证](math-translation-workflow/) |
| 机器学习辅助二维变分网格课程设计 | X/Q预测、物理精修、60个新问题泛化测试、条件数学证明；含历史步长练手 | 数据、图表、中文论文与统一导读已归档；适用边界明确 | [中文总览与全部成果](mlp-mesh-prediction/) |

## Data Science Bookcamp 独立学习专题

以 Leonard Apeltsin 的 *Data Science Bookcamp* 为学习起点，通过独立实现、结果复现和方法扩展理解数据科学案例。学习路径为：理解方法、独立实现、复现结果、修改与扩展，再发展原创项目。

五个案例目前均为计划中：

| 案例 | 学习内容 |
| --- | --- |
| [概率模拟](data-science-bookcamp/01-probability-simulations/) | 概率、蒙特卡洛模拟、NumPy |
| [广告点击统计](data-science-bookcamp/02-ad-click-statistics/) | 统计推断、假设检验、A/B 测试 |
| [疫情异常检测](data-science-bookcamp/03-outbreak-detection/) | 聚类、地理空间分析、可视化 |
| [就业市场 NLP](data-science-bookcamp/04-job-market-nlp/) | 文本处理、TF-IDF、降维、聚类 |
| [社交网络预测](data-science-bookcamp/05-social-network-prediction/) | 图分析、特征工程、机器学习 |

各案例开始后，在对应目录记录环境、数据来源、运行方式、实验结果与方法解释。[专题 README](data-science-bookcamp/README.md) 汇总整体学习路线。

## 本地数学翻译工作流

将英文数学论文和教材整理为中文 PDF 与可编辑 LaTeX 项目，支持本地 PDF 解析、原生 TeX 翻译、术语维护、分章节继续和编译审校。

| 任务 | 工具与流程 |
| --- | --- |
| 普通或扫描 PDF 精译 | MathTranslations、MinerU 本地解析、XeLaTeX / Biber |
| arXiv 或现有 LaTeX 源码 | 直接处理源码，LaTeXTrans 为可选批处理入口 |
| 快速中文或双语 PDF | PDFMathTranslate-next Windows 便携包 |
| 长教材整理 | 章节进度、物理页映射、术语表与审校记录 |

本地精译流程通过四页原创样例的 21 项验收；本机 Ollama + Qwen3 完成 ISLP 613 页机器初稿，中文与双语版本各 309 条书签。默认自动翻译不调用付费 API。环境面向 Windows PowerShell，精译另需 Python 与 TeX Live / MiKTeX。

- [原创讲义](math-translation-workflow/output/pdf/original.pdf)与[中文译本](math-translation-workflow/output/pdf/translated-zh.pdf)。
- [可编辑样例](math-translation-workflow/samples/Linear%20algebra%20sample/)与[审校记录](math-translation-workflow/samples/Linear%20algebra%20sample/review.md)。
- [中文用户指南](math-translation-workflow/docs/user_guide_zh.md)、[安装说明](math-translation-workflow/docs/installation_report.md)与[验收结果](math-translation-workflow/evidence/acceptance.json)。
- [论文与全书任务报告](math-translation-workflow/reports/completed-tasks.md)。

从仓库根目录进入 `academic/math-translation-workflow`，按[项目 README](math-translation-workflow/README.md) 初始化本机工具并运行样例。

## 限制

Data Science Bookcamp 案例尚未开始实现，当前目录提供学习计划。数学翻译工作流的整书成果为机器初稿，没有逐页精校；LaTeXTrans 独立模型翻译尚未完成端到端验证。解析、编译和样例验收不能代替数学内容的回源审校。

## 数据与许可

学科项目记录资料来源、实验环境和随机种子。数据集仅在许可允许时分发；数学翻译样例为原创内容，使用 CC0 1.0，第三方工具和模型保留原有许可。原创代码与说明采用仓库的 [MIT License](../LICENSE)。

[返回仓库首页](../README.md) · [兴趣与休闲项目](../leisure/)
