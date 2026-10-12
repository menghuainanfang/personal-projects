"""限定已部署 PDFMathTranslate GUI 为本机访问。"""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
packages=root/'tools/pdf2zh/pdf2zh/site-packages'
path=packages/'pdf2zh_next/gui.py'
text=path.read_text(encoding='utf8')
start=text.index('def setup_gui(')
end=text.index('# For auto-reloading',start)
before=text[start:end]
after=before.replace('server_name="0.0.0.0"','server_name="127.0.0.1"').replace('share=True,','share=False,')
path.write_text(text[:start]+after+text[end:],encoding='utf8')
for file,old,new in [
    ('babeldoc/const.py','Path.home() / ".cache" / "babeldoc"',f'Path({str(root/"cache"/"babeldoc")!r})'),
    ('pdf2zh_next/const.py','Path("~/.config/pdf2zh").expanduser()',f'Path({str(root/"state"/"pdf2zh")!r})')]:
    target=packages/file
    text=target.read_text(encoding='utf8').replace(old,new)
    target.write_text(text,encoding='utf8')
print('便携 GUI 仅本机，配置与资源缓存位于 D 盘：',path)
