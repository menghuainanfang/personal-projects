"""将便携运行时的标准输出与错误日志设为 UTF-8。"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / 'tools/pdf2zh/pdf2zh/_pystand_static.int'
text = path.read_text(encoding='utf-8')
encoding_setup = "import sys\nsys.stdout.reconfigure(encoding='utf-8', errors='replace')\nsys.stderr.reconfigure(encoding='utf-8', errors='replace')\n"
if "sys.stdout.reconfigure(encoding='utf-8'" not in text:
    text = text.replace('import sys\n', encoding_setup, 1)
    path.write_text(text, encoding='utf-8')
print('运行时日志编码：UTF-8。')
