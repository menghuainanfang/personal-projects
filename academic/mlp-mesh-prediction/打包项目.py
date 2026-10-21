"""将课程代码、数据、模型、图表、论文与汇报归档。"""
from pathlib import Path
import argparse,zipfile
ROOT=Path(__file__).resolve().parent
FILENAME='机器学习网格课程设计_泛化与理论整理版.zip'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/FILENAME)
    output=parser.parse_args().output.resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    ignored={'__pycache__','node_modules','.venv','.git','build_logs','pdf_preview','provenance'}
    files=[]
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file() or p.resolve()==output:continue
            if any(part in ignored for part in p.relative_to(ROOT).parts):continue
            if p.suffix in {'.zip','.pyc','.log','.aux','.out'}:continue
            name=Path('机器学习网格课程设计')/p.relative_to(ROOT)
            z.write(p,name);files.append(str(name).replace('\\','/'))
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        required=['README.md','项目导读/01_结论与适用范围.md',
            '工程与历轮实验/models/mlp.pt',
            '工程与历轮实验/experiments/round3/models/q_mlp_20261021.pt',
            '工程与历轮实验/experiments/round5_generalization/results/metrics.csv',
            '工程与历轮实验/experiments/round4_direct_physical/paper/report.pdf',
            '历史练手/随机森林步长预测/paper/paper.pdf']
        assert all('机器学习网格课程设计/'+r in z.namelist() for r in required)
    print(f'{output} ({output.stat().st_size/1024**2:.2f} MiB, {len(files)} files)')

if __name__=='__main__':main()
