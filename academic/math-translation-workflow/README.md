# 本地数学翻译工作流

将英文数学论文和教材整理为中文 PDF 与可编辑 LaTeX 项目，支持本地 PDF 解析、原生 TeX 翻译、术语维护、按章节继续和编译审校。

**状态：本地精译流程已验证。** 四页原创样例通过 21 项验收；MinerU 基础解析与 PDF 翻译 WebUI 已实测。免费 Google 接口受到限流，快速 PDF 的真实翻译尚未通过；LaTeXTrans 模型翻译需配置服务。

## 功能

| 输入与目标 | 入口 |
| --- | --- |
| 普通或扫描 PDF，精译为中文 TeX + PDF | MathTranslations 技能、MinerU 本地 basic、XeLaTeX/Biber |
| arXiv 或已有 LaTeX 源码 | 优先直接翻译源码；LaTeXTrans 为可选批处理入口 |
| 快速中文或双语 PDF | PDFMathTranslate-next 官方 Windows 便携包 |
| 长教材 | 章节进度、物理页映射、术语表与独立审校记录 |

这是一套模块化本地工作流。解析、编译可在本机进行；Codex 或远端翻译引擎仍使用各自的模型服务。

## 演示与验证

- [原创测试讲义](output/pdf/original.pdf)：四页，包含公式、定义、定理、证明、习题、图表、脚注和文献。
- [中文译本](output/pdf/translated-zh.pdf)。
- [可编辑项目](samples/Linear%20algebra%20sample/)与[审校记录](samples/Linear%20algebra%20sample/review.md)。
- [验收结果](evidence/acceptance.json)：公式与结构、空格路径、缺失资源、编译失败、成果保留和恢复等 21 项通过。

样例原稿、译文和图示使用 CC0 1.0。这里未收录个人教材或受版权保护的整书。

## 环境与运行

面向 Windows PowerShell、Python 3.10+、Git、Codex 和已有 TeX Live/MiKTeX。精译样例需要 XeLaTeX、latexmk、Biber 与 ctex/Fandol；PDF 辅助提取需要 pdftotext。

```powershell
git clone https://github.com/menghuainanfang/personal-projects.git
Set-Location personal-projects/academic/math-translation-workflow
python scripts/setup_local.py
.\翻译工具.ps1 build 'samples\Linear algebra sample\translation'
```

初始化脚本根据本机工具生成被 Git 忽略的 `config.json`；如果工具未在 PATH，先用其安装路径填写配置。它不修改全局 PATH，也不安装模型。

MathTranslations 主技能保留完整仓库：

```powershell
git clone https://github.com/libinyam/mathtranslations-skill.git vendor/mathtranslations-skill
$skillDir = Join-Path $HOME '.agents/skills/mathtranslations'
if (Test-Path -LiteralPath $skillDir) { throw '技能目录已存在，请先评估更新' }
New-Item -ItemType Directory -Path (Split-Path $skillDir) -Force | Out-Null
Copy-Item -LiteralPath vendor/mathtranslations-skill -Destination $skillDir -Recurse
python scripts/setup_local.py
.\翻译工具.ps1 audit 'samples\Linear algebra sample\translation'
```

然后在 Codex 中使用 `$mathtranslations` 并指定源文件和范围。每次构建输出到独立目录，保留原稿和旧成果。

可选工具的安装步骤见[安装说明](docs/installation_report.md)，具体操作见[中文用户指南](docs/user_guide_zh.md)。模型和便携包下载体积较大，按实际需要部署。

## 项目结构

```text
math-translation-workflow/
├── scripts/          本机初始化、独立构建、分页提取、验收与工具配置
├── docs/             架构、许可、安装、使用与质量说明
├── samples/          原创中英文 LaTeX 样例、术语表和进度记录
├── output/pdf/       已验证原稿与中文译本
├── evidence/         发布资产信息及样例验收结果
├── 本地环境.ps1      将模型和服务状态定位到项目目录
├── 翻译工具.ps1      项目准备、提取、构建与审计入口
├── MinerU.ps1        本地解析入口
└── 快速PDF.ps1       仅本机访问的 WebUI 入口
```

虚拟环境、下载、模型、个人项目、缓存、运行日志和本机配置不提交到 Git。

## 限制

- 免费 Google 翻译接口实测返回 HTTP 429；工具退出码 0 不代表翻译完成，应检查真实输出。
- LaTeXTrans 的本地输入已测，模型翻译与在线 arXiv 全链路尚未验证；需要服务、模型和授权。
- OCR、文字层抽取和编译都不能证明数学翻译正确；公式、量词、证明与编号需要回源检查。
- MinerU Markdown 图像定位符不能直接替代可携带的图资源；最终项目应保留或提取原图。
- 大教材应按章节处理。现有样例结果不能作为所有教材自动通过的保证。

## 许可与参考

原创代码和说明遵循仓库根目录 MIT License；样例使用 CC0。第三方工具和模型保留各自许可，详见[第三方许可](docs/third_party_licenses.md)。

- [MathTranslations Skill](https://github.com/libinyam/mathtranslations-skill)与[官方指南](https://mathtranslations.org/guide/)
- [MinerU](https://github.com/opendatalab/MinerU)
- [PDFMathTranslate-next](https://github.com/PDFMathTranslate-next/PDFMathTranslate-next)
- [LaTeXTrans](https://github.com/NiuTrans/LaTeXTrans)
- [完整候选比较](docs/repository_comparison.md)
