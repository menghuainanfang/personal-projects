# 使用指南

## PDF 或教材精译

在 Codex 中打开本项目，提供 PDF 或本地路径，指定章节/页数和输出要求。示例请求：

> 使用 $mathtranslations，将指定 PDF 的第一章翻译为中文 LaTeX 和 PDF。对照原页面保留公式、变量、量词、定理证明、习题、图表、脚注和文献，先建立术语表，完成后编译并审校。

初始化项目可使用：

```powershell
.\翻译工具.ps1 init 'D:\Materials\book.pdf' 'projects\book-zh'
.\翻译工具.ps1 extract 'projects\book-zh\source\book.pdf' 'projects\book-zh\extracted' --first 1 --last 10
```

提取文字层只作辅助。扫描与复杂公式可使用已部署的 MinerU：

```powershell
.\MinerU.ps1 server start
.\MinerU.ps1 parse 'D:\Materials\book.pdf' --tier basic --pages 1-10 --output 'projects\book-zh\extracted\chapter01.md'
```

页码为从 1 起的 PDF 物理页，印刷页核实后另记。把译稿放入 `translation`，原稿留在 `source`。术语 TSV 包含英文、中文首选、备选、语境和审校状态；问题写入 `review/issues.md`。

## 原生 TeX 与 arXiv

有源码时直接处理源码：

```powershell
.\翻译工具.ps1 init 'D:\Materials\paper-source' 'projects\paper-zh'
```

将项目 `source/tex` 复制为译稿目录，先编译原文基线。翻译时保留类、宏、标签、公式、图资源和文献键，不先转换 Markdown。有发表 PDF 时回源核对；没有时记录页面比较缺口。

LaTeXTrans 支持本地目录、zip/tar.gz 或 `--arxiv 2508.18791v2`。配置服务并取得对应发送与费用授权后使用；自动翻译全链路尚未实测。最终译稿仍运行本项目的完整构建命令。

## 编译与审计

```powershell
.\翻译工具.ps1 audit 'projects\paper-zh\translation'
.\翻译工具.ps1 build 'projects\paper-zh\translation'
```

构建输出位于新的 `output/builds` 子目录，日志和旧 PDF 保留。修复失败项后重跑 build；只编译成功不能证明译文正确，还要检查数学、编号、文献及页面外观。

## 按章节继续

在 `chapters.json` 中记录每章 ID、物理页范围、译稿、审校记录和 `pending` / `translated` / `reviewed` 状态。源页不能遗漏或重复。只有完成回源比较、编译、编号核对及页面检查后才标为 reviewed。

继续任务先读取进度、术语表和问题记录，跳过已核实章节，仅处理待译或失败部分。文字层提取会跳过已经完成的页，失败页可以重跑。疑似原文错误单独写译者建议，不静默改正文。

## 快速中文/双语 PDF

运行 `.\快速PDF.ps1`，浏览器打开 `http://127.0.0.1:7860`。选择 English → Simplified Chinese、输入文件和翻译服务，再启动。先测试少量页面，检查真实输出。

远端引擎会发送待译文本，Ollama 需要额外本地模型服务。免费 Google 接口当前验收遇到 429；不自动切换付费服务或发送个人文件。配置不自动保存密钥。

## 更新与卸载

更新前保留术语、进度与已审译稿。主技能更新完整目录；新版本先用样例测试。便携包更新后重应用 `patch_pdf_gui.py`；MinerU 不沿用旧版命令。停止服务后移走所选工具环境即可停用，个人原稿和成果另行保留。
