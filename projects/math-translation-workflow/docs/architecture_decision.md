# 架构决定

采用三个独立入口：PDF 快速译读、PDF 按章节重建中文 LaTeX、原生 LaTeX 直接翻译。共用术语表与审校记录，保持工具环境隔离。

| 场景 | 组件及路径 | 处理方式 |
|---|---|---|
| 快速 PDF | PDFMathTranslate-next 2.9.0，官方 Windows 便携包内置 Python 运行时 | BabelDOC 保留布局，输出中文及双语 PDF；外部翻译引擎由用户选择 |
| 教材精译 | MathTranslations 主技能 + MinerU 4 基础解析 + 现有 TeX Live | 分页抽取辅助、逐节回源翻译、中文 LaTeX、Biber、PDF 审校 |
| 原生 TeX | MathTranslations；LaTeXTrans 为独立批处理选项 | 直接保持宏、标签、文献及图资源，翻译自然语言，不先转 Markdown |

`scripts/workflow.py` 只负责准备项目、按物理页提取文本、独立构建及调用上游审计，不重写翻译器或 OCR。每次构建复制可编辑项目到新的构建目录；失败日志保留，旧 PDF 不被覆盖。

原始输入保存在各项目 `source/`；译稿在 `translation/`；页面抽取在 `extracted/`；术语表在 `glossary.tsv`；进度在 `chapters.json`；问题在 `review/issues.md`。已审校章节由进度文件标识，继续任务先读该文件，不重复翻译。

现有 LaTeX 项目保留文档类与构建惯例。新教材样例使用 ctexart、Fandol、amsmath、amsthm、graphicx、hyperref、biblatex；主仓库自带 legacy 模板另做完整编译测试。仓库未提供 mathtranslation.cls，不假设它存在。

Marker 与 MinerU 功能重叠，当前 Marker 的 VLM 服务部署增加复杂度，不安装。两个无明确许可证的参考技能不注册。aimath 为 MIT 的独立衍生项目，保留评估副本，暂不与主技能同时启用以避免术语政策冲突。

PDFMathTranslate 的上游 GUI 启动代码使用 `0.0.0.0`，且有 `share=True` 的回退分支。已修改便携包内的 GUI 启动函数为 `127.0.0.1` 并关闭共享回退；配置和 BabelDOC 资源缓存也定向到 D 盘工作区。修改脚本可复现，保留上游许可证，官方便携 EXE 为默认 GUI 入口。

本地解析和编译无需上传文档。Codex 翻译使用当前服务；LaTeXTrans 与 PDFMathTranslate 的远端引擎会发送文本并可能计费。本次不配置密钥、不自动发送个人文件。模型下载授权不等于文档上传或付费 API 授权。
