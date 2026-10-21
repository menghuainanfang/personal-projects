"""Package all required code, teachers, models, figures and documents."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]
OUTPUT=SOURCE.parent/'mesh_prediction_round4_course_project.zip'

def main():
    excluded={'__pycache__','node_modules','.venv','.git','build_logs','pdf_preview','provenance'}
    count=0
    with zipfile.ZipFile(OUTPUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(SOURCE.rglob('*')):
            if not p.is_file() or any(part in excluded for part in p.relative_to(SOURCE).parts):continue
            if p.suffix in {'.pyc','.aux','.log','.out','.zip'}:continue
            z.write(p,Path(SOURCE.name)/p.relative_to(SOURCE));count+=1
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        prefix=f'{SOURCE.name}/experiments/round4_direct_physical/'
        for name in ['physical.py','experiment.py','results/A_metrics.csv','results/B_metrics.csv',
                     'paper/report.pdf','presentation/index.html','README.md']:
            assert prefix+name in z.namelist()
        assert f'{SOURCE.name}/experiments/round3/models/q_mlp_20261021.pt' in z.namelist()
        assert f'{SOURCE.name}/data/teacher/mu_000.npz' in z.namelist()
        assert f'{SOURCE.name}/models/mlp.pt' in z.namelist()
    print(f'{OUTPUT} ({OUTPUT.stat().st_size/1024**2:.2f} MiB, {count} files)')

if __name__=='__main__':main()
