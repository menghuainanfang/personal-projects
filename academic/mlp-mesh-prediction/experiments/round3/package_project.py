"""Package the complete project, preserving round-two dependencies and outputs."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]
OUTPUT=SOURCE.parent/'mesh_prediction_round3_course_project.zip'

def main():
    excluded={'__pycache__','node_modules','.venv','.git','build_logs','pdf_preview','provenance'}
    excluded_suffix={'.pyc','.aux','.log','.out','.synctex.gz'}
    count=0
    with zipfile.ZipFile(OUTPUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(SOURCE.rglob('*')):
            if not p.is_file() or any(part in excluded for part in p.relative_to(SOURCE).parts):continue
            if p.suffix in excluded_suffix or p.name=='results_run.log':continue
            z.write(p,Path(SOURCE.name)/p.relative_to(SOURCE));count+=1
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        prefix='mesh_prediction/experiments/round3/'
        for path in ['experiment.py','results/metrics.csv','paper/report.pdf','presentation/index.html','README.md']:
            assert prefix+path in z.namelist()
        assert 'mesh_prediction/data/teacher/mu_000.npz' in z.namelist()
        assert 'mesh_prediction/models/mlp.pt' in z.namelist()
    print(f'{OUTPUT} ({OUTPUT.stat().st_size/1024**2:.2f} MiB, {count} files)')

if __name__=='__main__':main()
