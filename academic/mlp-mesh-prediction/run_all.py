"""Reproduce teachers, training, paired tests, plots, PDF and offline report."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
from src.common import ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--documents-only',action='store_true')
    parser.add_argument('--dependencies',type=Path,help='Matching reporting template with installed node_modules')
    parser.add_argument('--node',type=Path)
    args=parser.parse_args()
    logs=ROOT/'results/build_logs';logs.mkdir(exist_ok=True)
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    jobs=[] if args.documents_only else [
        ['-m','unittest','discover','-s','tests','-v'],
        ['generate_dataset.py','--smoke'],['generate_dataset.py'],['train.py'],['evaluate.py']]
    jobs += [['make_figures.py'],['build_report.py']]
    for index,job in enumerate(jobs):
        print('Running '+' '.join(job),flush=True)
        with (logs/f'{index:02d}_{Path(job[0]).stem}.log').open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,*job],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    compiler=shutil.which('xelatex')
    if not compiler:
        raise RuntimeError('XeLaTeX is required to rebuild the PDF; delivered PDF/HTML can be read without it.')
    for iteration in range(1,4):
        with (logs/f'xelatex_{iteration}.log').open('w',encoding='utf-8') as log:
            subprocess.run([compiler,'-interaction=nonstopmode','-halt-on-error','-file-line-error','report.tex'],
                           cwd=ROOT/'paper',stdout=log,stderr=subprocess.STDOUT,check=True)
    generator=ROOT/'tools/reporting'
    sys.path.insert(0,str(generator))
    from notes_to_report import make_snapshot,prepare_dependencies
    from build_report_app import find_node
    from report_contract import atomic_json
    node=find_node(args.node)
    deps=args.dependencies.resolve() if args.dependencies else prepare_dependencies(node)
    for note,output in [(ROOT/'presentation/talk.md',ROOT/'presentation/index.html'),
                        (ROOT/'paper/report.md',ROOT/'paper/report.html')]:
        snapshot=make_snapshot(note,node,deps)
        for block in snapshot['report']['layout']['blocks']:
            block['markdown']=block['markdown'].replace('<!-- pagebreak -->','')
        snapshot_path=logs/(note.stem+'_input.snapshot.json')
        atomic_json(snapshot_path,snapshot)
        command=[sys.executable,str(generator/'build_report_app.py'),'--snapshot',str(snapshot_path),
            '--output',str(output),'--node',str(node),'--dependencies',str(deps),'--allow-revision']
        with (logs/(note.stem+'_html.log')).open('w',encoding='utf-8') as log:
            subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run([sys.executable,str(generator/'verify_report.py'),str(output)],cwd=ROOT,env=env,check=True)
        snapshot_path.unlink()
    subprocess.run([sys.executable,'verify_results.py'],cwd=ROOT,env=env,check=True)
    print('Full project outputs are ready.',flush=True)

if __name__=='__main__':main()
