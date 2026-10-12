# 安装说明与验证状态

## 已验证状态

| 组件 | 验证范围 |
| --- | --- |
| MathTranslations | 新 Codex 进程发现启用技能；样例审计零错误、零警告；8 项上游审计测试通过 |
| LaTeX | 四页中英文样例与上游 legacy 模板编译；Biber、交叉引用、图和中文字体通过 |
| MinerU 4.0.12 | ONNX basic 模型验证、本机服务就绪、四页解析与重复解析通过 |
| PDFMathTranslate 2.9.0 / BabelDOC 0.6.4 | 官方便携包版本、资源、WebUI 与 127.0.0.1 监听通过 |
| LaTeXTrans 0.1.0 | 独立环境 CLI、本地 tar.gz 导入和带版本 arXiv ID 识别通过 |

样例验收摘要随仓库提供。个人环境、模型和完整运行日志不随仓库分发。

## 安装主技能与本机工具

依照项目 README 克隆完整主技能，运行 `scripts/setup_local.py`。已有 TeX Live 或 MiKTeX 时复用现有安装。缺少工具时在配置中填写实际路径；勿将其他机器的绝对路径复制过来。

## MinerU 基础解析

下载模型约 0.8 GB。先确认存储空间和用途，再运行：

```powershell
. .\本地环境.ps1
python -m venv .venvs/mineru
.\.venvs\mineru\Scripts\python.exe -m pip install mineru==4.0.12
.\.venvs\mineru\Scripts\mineru-kit.exe models download --tier basic --small-backend onnx --source modelscope
.\.venvs\mineru\Scripts\mineru-kit.exe models verify --tier basic --small-backend onnx
.\MinerU.ps1 server start
.\MinerU.ps1 config set parse_server.local.managed_tier basic
.\MinerU.ps1 config set parse_server.local.mode managed
.\MinerU.ps1 server status --json
```

等待本地 `healthy=true` 再解析。模型与状态都在项目目录；不加 `--remote`。按需要使用本地基本解析，不默认安装 GPU full。

## 快速 PDF 便携版

固定发布资产信息在 `evidence/pdf2zh-current-release.json`，包含资源下载约 592 MB：

```powershell
python scripts/install_portable.py
python scripts/patch_pdf_gui.py
.\快速PDF.ps1
```

本地修改将 GUI 的全接口监听改为 `127.0.0.1`、关闭共享回退，并把配置和资源缓存定位到项目目录。更新或重新解压后再运行 patch 脚本。保留全部上游许可；不直接启动未经修改的 GUI。

## LaTeXTrans 可选部署

```powershell
. .\本地环境.ps1
git clone https://github.com/NiuTrans/LaTeXTrans.git vendor/LaTeXTrans
git -C vendor/LaTeXTrans checkout a4f8c214e525aa000413fde167bae23fb16e1b4a
python -m venv .venvs/latextrans
.\.venvs\latextrans\Scripts\python.exe -m pip install -e vendor/LaTeXTrans
.\.venvs\latextrans\Scripts\latextrans.exe --help
```

复制上游 `config/default.toml` 为自己的 `config/latextrans.local.toml`，配置英文到中文、模型、endpoint、实际源项目和输出路径。密钥只放在被 Git 忽略的本地配置中，勿放命令行或日志。

## 验收与停止

需要复跑验收时，在另一个环境安装 `requirements-qa.txt`，先编译 README 样例，再运行 `python scripts/acceptance.py`。主技能源码需位于 README 指定的 vendor 目录。该测试会创建独立测试成果并故意测试编译失败和缺图。

WebUI 用终端中断停止；MinerU 使用 `.\MinerU.ps1 server stop`。卸载时保留个人项目及输出，再移走相应环境与工具目录。

## 限制

Google 免费接口实测 HTTP 429，无有效翻译 PDF；其退出码不能作成功依据。LaTeXTrans 实际 LLM 翻译、在线 arXiv 下载和其自动编译未通过完整链路测试。远端服务需要文档发送授权，付费调用需费用授权。源作品与模型授权不由工具代码许可证替代。
