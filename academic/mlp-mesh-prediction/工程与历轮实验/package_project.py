"""Archive the complete mesh-prediction project and verify its extracted contents."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import zipfile
from src.common import ROOT

def main():
    target=ROOT.parent/'mesh_prediction_course_project.zip'
    excluded={'__pycache__','.venv','node_modules','.git','.pytest_cache','build_logs'}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(ROOT.rglob('*')):
            rel=path.relative_to(ROOT)
            if not path.is_file() or excluded.intersection(rel.parts) or path.suffix in {'.pyc','.aux','.log','.out'}:
                continue
            z.write(path,Path('mesh_prediction')/rel)
    with tempfile.TemporaryDirectory(prefix='mesh-prediction-archive-') as td:
        with zipfile.ZipFile(target) as z:z.extractall(td)
        unpacked=Path(td)/'mesh_prediction'
        env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
        subprocess.run([sys.executable,'verify_results.py'],cwd=unpacked,env=env,check=True)
        assert (unpacked/'models/mlp.pt').is_file()
        assert (unpacked/'tools/reporting/notes_to_report.py').is_file()
    print(f'{target} ({target.stat().st_size/1024/1024:.2f} MiB); extracted validation passed.')

if __name__=='__main__':main()
