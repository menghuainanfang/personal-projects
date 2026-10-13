# 验证环境

| 项目 | 实测配置 |
|---|---|
| 系统 | Windows、PowerShell |
| 内存 / GPU | 32 GB / RTX 4060 Laptop 8 GB |
| Python | Python 3.13；可选解析使用独立虚拟环境 |
| TeX | 既有 TeX Live 2024、XeLaTeX、latexmk、Biber、ctex/Fandol |
| PDF 翻译 | PDFMathTranslate-next 2.9.0 / BabelDOC 0.6.4 官方便携包 |
| 本地模型 | Ollama 0.40.3、Qwen3 4B Instruct，约 2.5 GB |
| 扫描辅助 | MinerU 4.0.12，ONNX basic |
| 源码辅助 | LaTeXTrans 0.1.0，本地输入已验证 |

工具、模型与主要缓存保存在项目部署目录。用户技能位于 `.agents/skills/mathtranslations`；译文数据库沿用 `.cache/pdf2zh_next/cache.v1.db`。不修改全局 PATH 或既有 TeX 安装。第三方运行时与模型不随公开仓库分发。
