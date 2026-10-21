"""Rebuild experiments, figures, paper and the existing generator's offline report."""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--documents-only', action='store_true',
                        help='Reuse saved numerical results; rebuild figures, paper and HTML.')
    parser.add_argument('--generator-root', type=Path, default=ROOT/'tools/reporting')
    parser.add_argument('--dependencies', type=Path,
                        help='Existing matching reporting template with node_modules.')
    parser.add_argument('--node', type=Path)
    args = parser.parse_args()
    logs = ROOT/'data/build_logs'
    logs.mkdir(exist_ok=True)
    scripts = ([] if args.documents_only else ['run_experiments.py'])
    scripts += ['make_figures.py', 'build_deliverables.py']
    for script in scripts:
        print(f'Running {script}', flush=True)
        with (logs/(Path(script).stem+'.log')).open('w', encoding='utf-8') as log:
            subprocess.run([sys.executable, str(ROOT/'scripts'/script)],cwd=ROOT,
                           stdout=log,stderr=subprocess.STDOUT,check=True)
    compiler=shutil.which('xelatex')
    if compiler:
        for n in range(1,4):
            with (logs/f'xelatex_{n}.log').open('w',encoding='utf-8') as log:
                subprocess.run([compiler,'-interaction=nonstopmode','-halt-on-error',
                                '-file-line-error','paper.tex'],cwd=ROOT/'paper',
                               stdout=log,stderr=subprocess.STDOUT,check=True)
        print('PDF compiled.',flush=True)
    else:
        print('XeLaTeX unavailable: kept editable paper.md and paper.tex; existing PDF is not rebuilt.',flush=True)
    generator=args.generator_root.resolve()
    node=args.node or shutil.which('node')
    if node is None:
        raise RuntimeError('Node.js >=22.12 is required to rebuild HTML; delivered HTML opens offline.')
    sys.path.insert(0,str(generator))
    from notes_to_report import make_snapshot, prepare_dependencies
    from build_report_app import find_node
    from report_contract import atomic_json
    resolved_node=find_node(Path(node))
    # Reuse an installed locked dependency tree when supplied; otherwise let
    # the generator use or prepare its documented local dependency cache.
    deps=(args.dependencies.resolve() if args.dependencies else prepare_dependencies(resolved_node))
    for note,output in [(ROOT/'presentation/talk.md',ROOT/'presentation/report.html'),
                        (ROOT/'paper/paper.md',ROOT/'paper/paper.html')]:
        snapshot=make_snapshot(note,resolved_node,deps)
        if note.name=='paper.md':
            for b in snapshot['report']['layout']['blocks']:
                b['markdown']=b['markdown'].replace('<!-- pagebreak -->','')
        snapshot_path=logs/(note.stem+'_source.snapshot.json')
        atomic_json(snapshot_path,snapshot)
        command=[sys.executable,str(generator/'build_report_app.py'),'--snapshot',str(snapshot_path),
                 '--output',str(output),'--node',str(resolved_node),'--dependencies',str(deps),
                 '--allow-revision']
        with (logs/(note.stem+'_html.log')).open('w',encoding='utf-8') as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run([sys.executable,str(generator/'verify_report.py'),str(output)],check=True)
        snapshot_path.unlink()
        print(f'Built {output.relative_to(ROOT)}',flush=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/validate_delivery.py')],check=True,cwd=ROOT)
    print('Reproduction finished.',flush=True)

if __name__=='__main__':
    main()
