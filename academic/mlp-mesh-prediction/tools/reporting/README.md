# 笔记与实验汇报网页

将 Markdown、纯文本或 Word 笔记转换成可离线打开的汇报网页，也可通过结构化 JSON 制作带交互图表的实验报告。

## 在这台电脑上使用

1. 将 `.md`、`.markdown`、`.txt` 或 `.docx` 文件放入 `inbox`。
2. 双击 `生成汇报.cmd`。
3. 网页会自动打开，并保存在 `reports/<笔记文件名>/report.html`。

也可以把一个或多个笔记文件拖到 `生成汇报.cmd` 上。每个笔记生成一份网页；笔记中的本地图片应保留原来的相对位置。`inbox` 只处理当前层的笔记，图片可以放在子目录中。

成品 HTML 内嵌脚本、样式、数学字体和本地图片，可以单独发送给他人。需要保留构建记录时，一起保存同目录的 `.snapshot.json` 和 `.manifest.json`。

本机已经安装前端依赖和 Word 转换工具。首次迁移到其他电脑时，安装 Python 3.10+、Node 22.12+（建议 Node 24），再运行：

```powershell
python prepare_report_environment.py
python -m pip install -r notes-requirements.txt
```

第二条仅供 Word 导入使用。笔记转换发现缺少前端依赖时，会自动运行第一次依赖安装；常规实验报告构建不自动安装依赖。

## 命令行

在 reporting 文件夹中运行：

```powershell
# 单个文件
python notes_to_report.py "D:\笔记\本周进展.md" --open

# 指定输出位置和标题
python notes_to_report.py "D:\笔记\本周进展.md" --output "D:\汇报\进展.html" --title "本周研究进展"

# 批量处理文件夹，或默认处理 inbox
python notes_to_report.py "D:\笔记\本周"
python notes_to_report.py

# 随包示例
python notes_to_report.py examples/notes/示例笔记.md --open
```

同名文件会使用相同的默认输出位置；批量输入存在同名笔记时会提示分别指定输出，避免相互覆盖。重复生成同一份输出会更新交付文件并保留报告身份。

## 笔记格式

Markdown 的第一个一级标题作为网页标题；没有一级标题时使用文件名。原文的段落、标题、列表、表格、代码和链接保持其结构。

行内公式使用 `$...$`：

```markdown
扩散系数 $\nu>0$，梯度为 $\nabla u$。
```

独立公式使用 `$$...$$`：

```latex
$$
\begin{aligned}
\partial_t u-\nu\Delta u &= f,\\
u|_{\partial\Omega} &= 0.
\end{aligned}
$$
```

也支持 `\(...\)` 和 `\[...\]`，会在导入时规范为美元符号分隔。代码块中的示例不会被转换。公式由 KaTeX 排版，不需要电脑安装 TeX，也不访问 CDN。

本地图片使用普通 Markdown 图片语法：

```markdown
![误差曲线](images/error.png)
```

支持 PNG、JPEG、SVG、GIF、WebP、AVIF 和 BMP，也支持引用式图片。图片会嵌入网页，缺失图片会提示具体路径。远程图片需先保存为本地文件。含空格的路径可写成 `![图](<images/my plot.png>)`。

Word 文档通过 Pandoc 转换，保留标准标题、表格、内嵌图片和可转换的 Word 数学公式。纯文本使用 UTF-8 编码，可以包含上述公式和 Markdown 语法。

## 样式与网页编辑

沿用模板的单栏布局、原有浅蓝配色、深浅主题、顶部工具栏和打印功能。正文使用适合中文的系统无衬线字体，字号 16px；章节标题 20px；报告标题桌面 48px、窄屏 36px。公式、宽表和代码在各自容器内横向滚动。

网页顶部切到 Edit 后，可通过“编辑 Markdown / LaTeX”修改笔记正文，点击“保存正文”返回排版视图。笔记正文使用源码编辑，保留公式、图片、表格和代码。

编辑记录保存在当前浏览器中，不会写回原笔记，也不会直接修改磁盘上的 HTML。可点击“下载当前 Markdown”保存已提交的正文，再把下载的笔记重新生成网页以交付修订版。下载的 Markdown 包含内嵌图片。重新导入后，如需撤去浏览器中已有的正文修订，点击“还原导入正文”；该操作支持顶部撤销。PDF 使用顶部 More 菜单中的转换入口，由浏览器打印保存。

## 实验数据报告

`report_contract.py` 定义 `schemaVersion: 1` 的数据格式。布局支持 `narrative`、`metrics`、`chart`、`table`；图表支持 line、area、bar、scatter。数据放在 `queries`，区块通过 `queryId` 引用数据。

```powershell
python create_report_app.py my_report --data-json reviewed_snapshot.json
python build_report_app.py my_report --output report.html --source-root "D:\实验项目"

# 或直接从快照构建
python build_report_app.py --snapshot report_snapshot.json --output report.html --source-root "D:\实验项目"

# 草稿或待修订报告
python build_report_app.py my_report --output draft.html --allow-revision

# 归档校验
python verify_report.py report.html
python verify_report.py report.html --source-root "D:\实验项目"
```

`--source-root` 是来源文件相对路径的基准，也是 `--data-builder` 的工作目录；默认是 reporting 文件夹。Node 不在 PATH 时传 `--node`；`--dependencies` 可指定包含匹配 `package-lock.json` 与 `node_modules` 的依赖目录。

实验报告的 `ready` 状态要求必需检查通过、来源文件存在且内容匹配。科学指标和检查结果由数据构建脚本计算，结构校验不代替科学审阅。缺失科学指标用 `null`，不补零；NaN/Infinity 禁止写入快照。

普通笔记输出标记为笔记整理稿，不自动获得实验验证通过状态。

## 开发与验证

主要入口：

- `notes_to_report.py`：笔记导入与网页生成。
- `prepare_report_environment.py`：准备锁定版本的前端依赖。
- `build_report_app.py`：实验报告校验、构建和归档。
- `verify_report.py`：交付文件校验。
- `technical_report_app_template/src/content/report/`：报告内容和样式。
- `technical_report_app_template/src/theme.css`：主题字体和配色。

```powershell
python -m unittest discover -s tests -v
node --test technical_report_app_template/tests/rich-narrative.test.mjs
node technical_report_app_template/scripts/verify-protected-runtime.mjs
```

Python 测试包含公式原文、图片嵌入、Word 转换、UTF-8 归档与数据契约。原项目液滴算例不随包提供，其测试在缺少数据时跳过。模板其他测试包含原产品及商业示例的专属假设，不作为独立包的验收入口。

## 使用边界

- 导入保留笔记内容，不自动总结、筛选重点或撰写科研结论。需要浓缩成汇报稿时，先编辑笔记再生成。
- 数学支持以 KaTeX 的 LaTeX 子集为准；不编译整份 TeX 工程、TikZ 或自定义宏包。Word 扫描图片里的公式不会被自动识别为 LaTeX。
- PDF、旧版 `.doc`、扫描件和 Obsidian 的 `![[...]]` 专用嵌入语法未接入。请先转换为支持的格式；Obsidian 图片改用普通 Markdown 图片语法。
- Word 复杂版式会按网页结构重排。原始 HTML 标签不作为排版接口。
- 浏览器编辑记录是本地显示修订；不同浏览器、不同设备或接收文件的人不会自动获得这些修改。同一浏览器曾保存的正文修订会优先显示；需要显示最新导入的正文时，在 Edit 模式点击“还原导入正文”。
- Word、PPT、发布等菜单保留原模板行为，其中部分依赖 ChatGPT/Codex 及相应插件；本地生成 HTML 和浏览器打印 PDF 可独立使用。
