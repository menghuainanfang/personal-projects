# 环境要求与验证环境

2026-10-12 的本机验证环境为 Windows 11 x64、PowerShell 7、Python 3.13、TeX Live 2024、32 GB 内存、RTX 4060 Laptop 8 GB。Git Bash 和 WSL 可用，实际部署使用原生 Windows。

工作流复用 XeLaTeX、latexmk、Biber、Fandol 中文字体和 Poppler。MinerU 4.0.12 采用 ONNX basic CPU 解析，不要求 CUDA Toolkit。PDFMathTranslate 使用官方 Windows 便携包内置运行时；LaTeXTrans 使用独立 Python 环境。

其他电脑运行 `python scripts/setup_local.py` 生成自己的 `config.json`。技能采用用户目录 `.agents/skills/mathtranslations`；该目录在新 Codex 进程中实际验证可发现。初始化脚本不覆盖现有配置、不改变全局 PATH、不安装模型。

原始机器路径、账号配置和运行缓存未包含在公开仓库。模型、环境、下载及个人译稿都定位到各自项目目录。
