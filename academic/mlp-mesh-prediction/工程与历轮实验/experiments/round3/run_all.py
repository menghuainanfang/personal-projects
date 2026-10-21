"""Reproduce round-three experiments using the existing teacher data."""
from pathlib import Path
import argparse,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--documents-only',action='store_true')
    parser.add_argument('--node',type=Path)
    parser.add_argument('--dependencies',type=Path)
    args=parser.parse_args()
    env=os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    logs=ROOT/'results/build_logs';logs.mkdir(parents=True,exist_ok=True)
    jobs=[] if args.documents_only else [['-m','unittest','test_round3','-v'],['experiment.py','all'],['verify.py']]
    jobs+=[['build_documents.py']]
    for i,job in enumerate(jobs):
        print('Running '+' '.join(job),flush=True)
        with (logs/f'{i}_{Path(job[0]).stem}.log').open('w',encoding='utf-8') as f:
            subprocess.run([sys.executable,*job],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    compiler=shutil.which('xelatex')
    if not compiler:raise RuntimeError('Document rebuild requires XeLaTeX; delivered PDF is ready to read.')
    for i in range(3):
        with (logs/f'xelatex_{i+1}.log').open('w',encoding='utf-8') as f:
            subprocess.run([compiler,'-interaction=nonstopmode','-halt-on-error','-file-line-error','report.tex'],
                           cwd=ROOT/'paper',stdout=f,stderr=subprocess.STDOUT,check=True)
    generator=SOURCE/'tools/reporting';sys.path.insert(0,str(generator))
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
        path=logs/(note.stem+'_input.snapshot.json');atomic_json(path,snapshot)
        with (logs/(note.stem+'_html.log')).open('w',encoding='utf-8') as f:
            subprocess.run([sys.executable,str(generator/'build_report_app.py'),'--snapshot',str(path),
                '--output',str(output),'--node',str(node),'--dependencies',str(deps),'--allow-revision'],
                cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run([sys.executable,str(generator/'verify_report.py'),str(output)],cwd=ROOT,env=env,check=True)
        path.unlink()
    print('Round-three documents ready.',flush=True)

if __name__=='__main__':main()
