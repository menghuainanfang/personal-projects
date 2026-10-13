# 安装与部署

实测组合：Windows、32 GB 内存、RTX 4060 Laptop 8 GB；PDFMathTranslate-next 2.9.0 / BabelDOC 0.6.4 官方便携包，Ollama 0.40.3，Qwen3 `4b-instruct`。精译使用既有 TeX Live 2024；MinerU 4.0.12 basic 和 LaTeXTrans 0.1.0 为可选独立环境。

## 整书本地翻译

整个项目可放到 D 盘。以下路径均相对项目目录。

1. 安装 Python 3.10+，运行 `python scripts/install_portable.py`。脚本读取固定发布资产 `evidence/pdf2zh-current-release.json`，下载约 592 MiB 的官方资源包并解压到 `tools/pdf2zh/`，随后应用本机 GUI、公式占位符和 UTF-8 日志三个补丁。体积匹配的已有安装包会复用。
2. 从 [Ollama 官方发布页](https://github.com/ollama/ollama/releases/tag/v0.40.3)取得 Windows amd64 独立压缩包，解压至 `tools/ollama/`，使可执行文件位于 `tools/ollama/ollama.exe`，保留附带的 `lib/` 与许可证。压缩包约 1.4 GiB。
3. 启动服务并下载模型，已有模型无需重复下载：

```powershell
.\本地模型.ps1 start
.\本地模型.ps1 pull
.\本地模型.ps1 status
.\本地翻译PDF.ps1 -Pdf 'D:\资料\book.pdf' -Output 'D:\译稿\book'
.\本地模型.ps1 stop
```

模型约 2.5 GB，保存在 `state/ollama/models/`。服务地址为 `127.0.0.1:11435`，上下文 8192，单模型、单并发。PDF 翻译使用单 worker，关闭自动术语表和富文本标签，翻译表格文字，内部每批最多 50 页。依赖和模型下载需要联网；源 PDF 翻译使用本机模型，不需要远端翻译账户或 API 密钥。

译文数据库沿用上游默认的用户目录 `.cache/pdf2zh_next/cache.v1.db`，应保留。BabelDOC 排版资源与本机配置保存在项目目录。当前补丁与 BabelDOC 0.6.4 配套，更新便携包后核对补丁入口并重新应用。

## LaTeX 精译

复用已有 TeX Live 或 MiKTeX，确认 XeLaTeX、latexmk、Biber 与 ctex/Fandol 可用。安装完整技能：

```powershell
git clone https://github.com/libinyam/mathtranslations-skill.git vendor/mathtranslations-skill
$skillDir = Join-Path $HOME '.agents/skills/mathtranslations'
if (Test-Path -LiteralPath $skillDir) { throw '技能目录已存在，请先评估更新' }
New-Item -ItemType Directory -Path (Split-Path $skillDir) -Force | Out-Null
Copy-Item -LiteralPath vendor/mathtranslations-skill -Destination $skillDir -Recurse
python scripts/setup_local.py
.\翻译工具.ps1 build 'samples\Linear algebra sample\translation'
```

初始化保留已有 `config.json`。未进入 PATH 的工具在配置中填写实际路径。保持技能的 scripts、references、LICENSE、NOTICE 和模板资源完整。

## 可选扫描解析

```powershell
. .\本地环境.ps1
python -m venv .venvs/mineru
.\.venvs\mineru\Scripts\python.exe -m pip install mineru==4.0.12
.\.venvs\mineru\Scripts\mineru-kit.exe models download --tier basic --small-backend onnx --source modelscope
.\.venvs\mineru\Scripts\mineru-kit.exe models verify --tier basic --small-backend onnx
.\MinerU.ps1 server start
```

已验证 basic 模型解析原创四页讲义；standard、advanced 与 GPU full 没有部署。解析稿中的图像定位符需要转换为图文件，才能用于最终 LaTeX 项目。

LaTeXTrans 可从其官方仓库完整克隆，在 `.venvs/latextrans` 独立安装。本地源码导入已验证；其独立模型翻译尚未完成端到端验证。整书本地 PDF 路线不依赖该环境。
