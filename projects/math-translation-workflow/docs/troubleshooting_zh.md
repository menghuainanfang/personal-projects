# 故障排查

| 现象 | 处理 |
|---|---|
| Codex 未显示主技能 | 检查用户目录下的 `.agents/skills/mathtranslations/SKILL.md`；重启 Codex；可运行 `python scripts/check_discovery.py` 查看 enabled 状态 |
| 编译错误 | 查输出目录 `compile.log` 和 `project/build/main.log`；修复译稿再运行 build；新构建独立保存 |
| 中文字体缺失 | 样例用 Fandol；用已有 TeX Live XeLaTeX；不要套用专项技能中另一机器路径 |
| 引用显示问号 | 使用完整 latexmk 构建，检查 `.bib` 中的引用键与 Biber 日志；单次 XeLaTeX 不足 |
| 插图缺失 | 保持源项目相对路径、扩展名和资源目录；审计会报告缺失资源；不要用猜测图替代 |
| PDF 解析公式不准 | 打开源页面核对符号、下标、范围和编号；OCR/文字层只作草稿 |
| MinerU 服务不可用 | 运行 `.\MinerU.ps1 server status --json`；查看 `state/mineru` 下日志；确认基础模型下载和验证通过，再启动服务 |
| MinerU 基础档未就绪 | 执行 `. .\本地环境.ps1`，再用 `.venvs/mineru/Scripts/mineru-kit.exe models verify --tier basic --small-backend onnx`；不自动切到 remote |
| 免费翻译接口错误 | 可能为网络失败或限流；保留原文，稍后仅重跑失败页，或选择已获授权的服务；不要自动换付费 API |
| 快速 PDF GUI 端口占用 | 关闭自己上次启动的服务，或传 `--server-port 7861`；打开对应 localhost 地址 |
| 更新后 GUI 暴露网络 | 先运行 `python scripts/patch_pdf_gui.py`；保持 `127.0.0.1`、share=false；不要直接用未修改的上游 GUI |
| 下载不完整 | 运行 `python scripts/install_portable.py`；脚本对已有部分尝试 HTTP Range 继续，完成后验证 ZIP；不把半成品标记为安装成功 |
| LaTeXTrans 有 PDF 但引用不对 | 最终译稿用 `.\翻译工具.ps1 build '实际译稿目录'` 重建并查看日志与 PDF |

## 限制

网络翻译服务、模型下载站点和 arXiv 的可用性不由本机控制。远端文档发送与付费调用需要明确授权。当前数学样例验证结果不代表任意教材可以自动达到同等质量。全文处理应从一个章节开始，建立术语表和审校记录后再继续。
