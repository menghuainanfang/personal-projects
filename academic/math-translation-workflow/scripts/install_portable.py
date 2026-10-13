import json, urllib.request, zipfile, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'evidence'/'pdf2zh-current-release.json').read_text())
asset=next(a for a in data['assets'] if 'v0.6.4-with-assets-win64' in a['name'])
downloads=root/'downloads';downloads.mkdir(exist_ok=True)
archive=downloads/asset['name']
if not archive.exists() or archive.stat().st_size!=asset['size']:
    pending=archive.with_suffix('.pending')
    offset=pending.stat().st_size if pending.exists() else 0
    headers={'User-Agent':'local-workflow'}
    if offset: headers['Range']=f'bytes={offset}-'
    req=urllib.request.Request(asset['browser_download_url'],headers=headers)
    with urllib.request.urlopen(req,timeout=90) as stream:
        append=stream.status==206 and stream.headers.get('Content-Range','').startswith(f'bytes {offset}-')
        with pending.open('ab' if append else 'wb') as out:
            while chunk:=stream.read(1024*1024): out.write(chunk)
    if pending.stat().st_size!=asset['size']: raise RuntimeError('下载不完整')
    pending.replace(archive)
dest=root/'tools'/'pdf2zh';dest.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(archive) as z:z.extractall(dest)
print('便携版已解压：',dest)
for patch in ('patch_pdf_gui.py', 'patch_formula_placeholders.py', 'patch_pdf_runtime_encoding.py'):
    subprocess.run([sys.executable, str(root/'scripts'/patch)], check=True)
