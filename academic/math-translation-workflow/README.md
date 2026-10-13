# 本地数学翻译工作流

英文数学论文与教材的中文译读工具，支持整本 PDF 自动翻译、中文与双语 PDF，以及保留公式、引用和图资源的 LaTeX 精译。

**本地整书翻译已完成实测：ISLP 613 页，中文和双语版本各 613 页、各 309 条书签。** 默认使用本机 Ollama + Qwen3 4B，不调用付费翻译 API，不需要 API 密钥。整书成果是机器初稿，质量范围见[任务报告](reports/completed-tasks.md)。

## 使用方式

| 目标 | 入口 | 交付 |
|---|---|---|
| 整篇论文或整本教材自动译读 | `本地翻译PDF.ps1` | 中文 PDF、双语 PDF |
| 本机网页操作 | `快速PDF.ps1` | 默认本地 Qwen 引擎 |
| 数学内容精译、可编辑排版 | MathTranslations + `翻译工具.ps1` | 中文 LaTeX、PDF、术语与审校记录 |
| 扫描 PDF 辅助解析 | `MinerU.ps1` | 本机 basic 解析稿 |
| arXiv 有 LaTeX 源码 | 优先取得对应版本源码，使用精译路线 | 保留宏、标签、文献和原图 |

整本书可以一次提交。自动入口内部按最多 50 页拆分，控制内存和排版规模，再合并成完整 PDF；不需要操作者逐段翻译。相同引擎和参数下的文本译文可复用已有缓存。

## 开始运行

面向 Windows PowerShell。首次部署见[安装说明](docs/installation_report.md)，依赖与模型不会随 Git 仓库下载。

```powershell
git clone https://github.com/menghuainanfang/personal-projects.git
Set-Location personal-projects/academic/math-translation-workflow
# 完成安装说明中的 PDFMathTranslate 和 Ollama 部署后：
.\本地翻译PDF.ps1 -Pdf 'D:\资料\book.pdf' -Output 'D:\译稿\book'
# 页码是从 1 开始的 PDF 物理页码。
.\本地翻译PDF.ps1 -Pdf 'D:\资料\book.pdf' -Pages '25-26,50-52' -Output 'D:\译稿\sample'
.\本地模型.ps1 stop
```

输出中文 mono 与双语 dual PDF；单批文件名称可能包含 `.no_watermark`。入口同时检查退出码与本次实际生成文件。翻译期间模型占用显存，结束后可停止服务。

精译样例的构建方式：

```powershell
python scripts/setup_local.py
.\翻译工具.ps1 build 'samples\Linear algebra sample\translation'
.\翻译工具.ps1 audit 'samples\Linear algebra sample\translation'
```

精译需要已有 XeLaTeX、latexmk、Biber 和完整 MathTranslations 技能。`翻译工具.ps1` 负责准备、提取、构建、审计和状态读取；自然语言精译由独立翻译与审校步骤完成。

## 公开交付

- [四页原创英文讲义](output/pdf/original.pdf)与[中文译本](output/pdf/translated-zh.pdf)。
- [可编辑中英文项目](samples/Linear%20algebra%20sample/)及[审校记录](samples/Linear%20algebra%20sample/review.md)，使用 CC0 1.0。
- [21 项样例验收](evidence/acceptance.json)。
- [论文与全书任务报告](reports/completed-tasks.md)、[结果数据](reports/task-results.json)。
- [中文操作指南](docs/user_guide_zh.md)、[质量说明](docs/quality_assurance.md)、[故障处理](docs/troubleshooting_zh.md)。

公开仓库包含工作流代码、原创样例和任务报告。个人论文、教材原文、整书译稿、提取文本、翻译缓存与运行日志保留在本地。

## 数据保留

`tools/` 保存运行时，`state/ollama/models/` 保存模型，`state/mineru/` 保存解析模型，`cache/babeldoc/` 保存排版资源。PDFMathTranslate 译文数据库位于用户目录 `.cache/pdf2zh_next/cache.v1.db`，应保留以复用已有翻译。

部署成功后的 `downloads/` 安装包、`cache/pip/`、停用的 `.venvs/pdf2zh` 与 `.venvs/pdf2zh312`、编译中间目录和被整书成品替代的分批备份可清理。有效模型、最终 PDF、可编辑源稿和翻译数据库应保留。

## 限制

- 613 页成果是机器初稿，没有逐页精校。部分标题、页边术语、跨行句子和索引排版仍需修订；书签标题保留英文。
- 公式占位符次数检查可触发逐段翻译回退，不能证明所有数学叙述正确。重要结论应对照双语 PDF 和原书。
- 扫描、复杂表格、脚注与多栏排版的质量取决于源文件；扫描教材需先解析并核对图像。
- 免费在线服务可能限流，默认整书路线使用本机模型。
- 本地自动路线不调用付费服务。精译使用的交互工具遵循其自身账户安排；LaTeXTrans 独立模型翻译未完成端到端验证。

## 许可与参考

原创代码和说明遵循仓库根目录 MIT License，原创样例使用 CC0。第三方工具、模型和源作品各自的许可见[第三方许可](docs/third_party_licenses.md)。模型权重、第三方运行时和受版权保护的译本不随仓库分发。

[MathTranslations](https://github.com/libinyam/mathtranslations-skill) · [MinerU](https://github.com/opendatalab/MinerU) · [PDFMathTranslate-next](https://github.com/PDFMathTranslate-next/PDFMathTranslate-next) · [Ollama](https://github.com/ollama/ollama) · [Qwen3](https://ollama.com/library/qwen3:4b-instruct)
