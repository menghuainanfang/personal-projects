# 仓库比较

核查日期：2026-10-12。核查内容为当前 README、许可证、依赖清单、代表性配置与 CLI/翻译源码、最新发布及最多 8 条开放 issue/PR。`evidence/` 保存 API 元数据、源码与说明快照；不是完整问题审计。更新时间是仓库推送时间，不代表稳定版本发布时间。

| 项目 | 近期状态与许可 | 功能、Windows 与资源 | API / Codex / 决策 |
|---|---|---|---|
| [MathTranslations Skill](https://github.com/libinyam/mathtranslations-skill) | 10-02 推送；MIT；NOTICE 明确随附 legacy TeX 和 logo 的授权 | 数学译稿与审校；标准库审计；不自带 OCR 模型；含 12 个专项技能；未含 mathtranslation.cls | Codex 主入口；无额外翻译 API 适配器；主技能已安装，专项技能保留但不全部注册 |
| [LaTeXTrans](https://github.com/NiuTrans/LaTeXTrans) | 09-21 推送；MIT；CLI 支持本地目录、zip/tar 和 arXiv | 保持结构进行 LLM 翻译；Python、Streamlit、现有 TeX；模型计算在配置的服务侧；独立环境避免固定依赖影响已有环境 | 需要 LLM endpoint、模型、密钥；成本随服务与文本长度；已部署独立选项，避免替代 Codex 主流程 |
| [MinerU](https://github.com/opendatalab/MinerU) | 10-11 推送；4.0.12；Apache 2.0 加商业门槛和在线服务标识条款 | 4.x 分级解析，含 Windows wheel；基础 ONNX 模型约 0.8 GB，CPU 可运行；standard 模型约 2 GB；full 增加约 5 GB 依赖，不默认安装 | 本地解析可不上传；remote 明确上传；主流程采用基础本地解析；扫描公式仍需核对 |
| [PDFMathTranslate-next 原链接](https://github.com/PDFMathTranslate/PDFMathTranslate-next) / [当前仓库](https://github.com/PDFMathTranslate-next/PDFMathTranslate-next) | 原链接源码 2.8.2，04-08 推送；文档发布链接指向 2.9.0；AGPL-3.0 | BabelDOC 译读和双语 PDF；当前包含资源便携包约 592 MB；Python 包需要隔离 3.12 环境；不输出可编辑 TeX | 支持多个远端引擎及 Ollama；API 成本另计；采用当前 2.9.0，GUI 限定本机 |
| [数学教材视觉翻译技能](https://github.com/JiayanJohnnyChu/math-textbook-visual-translator) | 08-20 推送；树中未发现明确 LICENSE，API license=null | 每页视觉转写、章节审校；大量页面渲染与模型上下文；默认禁用文字层/OCR，与高效抽取主路径不同 | 理念参考；不注册、不复制其实现到交付代码；保持出处 |
| [Marker](https://github.com/datalab-to/marker) | 10-02 推送；当前代码 Apache-2.0；权重为修改的 AI Pubs Open Rail-M | PDF 到 Markdown/JSON；新版 Surya VLM 需服务，NVIDIA 路线依赖 Docker/vLLM，CPU 需 llama.cpp；下载权重另计 | LLM 增强可调用远端服务；与 MinerU 重叠，Windows 初次部署不安装 |
| [Codex RWD Math Skills](https://github.com/Euler2023/codex_rwd_math_skills) | 07-17 推送；树中未发现明确 LICENSE，API license=null | OCR Markdown 校对分块、PDF/Markdown 到 TeX；依赖因技能而异；与已有主技能重叠 | 仅参考公开说明，不注册或复用实现 |
| [AI & Math Translations Skill](https://github.com/DBQDSS/aimath-translations-skill) | 确实存在；独立仓库/衍生项目；MIT；创建于 10-08；本地评估固定提交 | 扩展 AI/ML、代码及术语规则；与 MathTranslations 同源，但规则和资源并不相同 | 评估副本留在 vendor，不同时启用；人名保留策略可与教材既有中文译名冲突 |

MinerU 4.x 的安装与命令不能沿用 magic-pdf 或 2.x 的说明。当前使用基础环境 ONNX 路线，机器有 32 GB 内存和 8 GB 显存，但本次不为吞吐率增加 PyTorch/vLLM。

## 兼容性与已知问题

- 主技能专项编译技能记录了 `其他机器的 TeX 路径` 和另一用户的 Python；当前电脑实际是 TeX Live 2024。使用本地配置中的实测工具。
- MathTranslations 的说明将 400 DPI 位图裁图描述为没有栅格模糊；这仍是栅格图。保留原有矢量资源优先，确需裁图时按页面核实清晰度。
- PDFMathTranslate GUI 源码默认 `0.0.0.0`，失败回退可能打开共享；本机部署修改为 loopback，关闭共享回退。
- PDFMathTranslate 的旧 uv 文档仍写 Python 3.10-3.12，而当前 pyproject 宣称 <3.14。默认部署采用官方便携包的固定依赖与内置运行时。普通 Python 包的最新 bitstring 5.0 已移除 BabelDOC 需要的 BitStream 接口，需版本约束；便携包内置 4.4.0。
- LaTeXTrans 编译器以“目录里存在 PDF”为成功依据，且未保证 Biber 完整构建；对已有旧 PDF 或 biblatex 项目不足。最终输出由本工作区独立构建命令验证。
- MinerU 开放问题包含公式识别错误、表格合并信息遗漏与图像片段来源信息问题；Marker 包含行中插图与链接转义问题。它们是候选的质量风险，不能据此断言本机样例必定失败。

可复核来源：[MathTranslations 官方指南](https://mathtranslations.org/guide/)、[PDFMathTranslate Windows 文档](https://pdf2zh-next.com/getting-started/INSTALLATION_winexe.html)、[MinerU README](https://github.com/opendatalab/MinerU)、[Marker README](https://github.com/datalab-to/marker)。
