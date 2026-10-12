"""数学翻译项目的本地准备、分页提取与独立构建。"""
import argparse, datetime, json, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config.json'

def run(argv, cwd, log):
    with log.open('w', encoding='utf-8') as f:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, stdout=f, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(f'执行失败，日志：{log}')

def config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))

def build(project, main='main.tex'):
    project = project.resolve()
    if not (project/main).is_file():
        raise FileNotFoundError(project/main)
    cfg = config()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    dest = ROOT/'output'/'builds'/project.name/stamp
    stage = dest/'project'
    shutil.copytree(project, stage, ignore=shutil.ignore_patterns('.git','__pycache__','*.aux','*.log','*.out','*.toc','*.bcf','*.bbl','*.blg','*.run.xml','*.fls','*.fdb_latexmk','*.synctex.gz'))
    dest.mkdir(exist_ok=True)
    # Relative output directory avoids TeX's non-ASCII absolute-output-path failure.
    argv=[cfg['latexmk'], '-xelatex', '-interaction=nonstopmode', '-halt-on-error', '-file-line-error', '-outdir=build', main]
    run(argv,stage,dest/'compile.log')
    pdf=stage/'build'/Path(main).with_suffix('.pdf')
    if not pdf.exists(): raise RuntimeError('编译器未生成 PDF')
    shutil.copy2(pdf,dest/'result.pdf')
    logs='\n'.join(p.read_text(encoding='utf-8',errors='replace') for p in (stage/'build').glob('*.log'))
    problems=[line for line in logs.splitlines() if any(t in line for t in ['undefined references','undefined citations','multiply defined','Missing character:','Overfull \\hbox'])]
    (dest/'build_review.json').write_text(json.dumps({'pdf':str(dest/'result.pdf'),'log_findings':problems},ensure_ascii=False,indent=2),encoding='utf-8')
    print(dest/'result.pdf')
    if problems: print('需复核日志：',*problems,sep='\n')
    return dest

def init(source, target):
    if target.exists(): raise FileExistsError(f'项目已存在：{target}；使用 status 继续已有项目')
    if not source.exists(): raise FileNotFoundError(source)
    (target/'source').mkdir(parents=True)
    if source.is_dir(): shutil.copytree(source,target/'source'/'tex')
    else: shutil.copy2(source,target/'source'/source.name)
    for d in ['translation','extracted','review']: (target/d).mkdir()
    (target/'glossary.tsv').write_text('English\t中文首选\t备选\t语境\t审校状态\n',encoding='utf8')
    (target/'review'/'issues.md').write_text('# 待审问题\n\n记录页码、原文、观察与译者建议。\n',encoding='utf8')
    (target/'chapters.json').write_text(json.dumps({'source_original':str(source.resolve()),'page_numbering':'PDF 物理页从 1 起；印刷页需人工对应','chapters':[]},ensure_ascii=False,indent=2),encoding='utf8')
    print(target)

def extract(pdf, out, first, last):
    if first < 1 or last < first: raise ValueError('页范围须从 1 开始且连续')
    cfg=config()
    out.mkdir(parents=True,exist_ok=True)
    for page in range(first,last+1):
        path=out/f'page-{page:04d}.txt'
        if path.exists(): continue
        temp=path.with_suffix('.pending.txt')
        run([cfg['pdftotext'],'-f',page,'-l',page,'-layout',pdf.resolve(),temp.resolve()],ROOT,out/f'page-{page:04d}.log')
        temp.replace(path)
    print(f'已提取 PDF 物理页 {first}-{last}：{out}。公式须对照页面。')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('project',type=Path);b.add_argument('--main',default='main.tex')
    i=sub.add_parser('init');i.add_argument('source',type=Path);i.add_argument('target',type=Path)
    e=sub.add_parser('extract');e.add_argument('pdf',type=Path);e.add_argument('out',type=Path);e.add_argument('--first',type=int,required=True);e.add_argument('--last',type=int,required=True)
    s=sub.add_parser('status');s.add_argument('project',type=Path)
    a=sub.add_parser('audit');a.add_argument('project',type=Path)
    args=p.parse_args()
    if args.command=='build': build(args.project,args.main)
    elif args.command=='init': init(args.source,args.target)
    elif args.command=='extract': extract(args.pdf,args.out,args.first,args.last)
    elif args.command=='status': print((args.project/'chapters.json').read_text(encoding='utf8'))
    elif args.command=='audit':
        return subprocess.call([sys.executable,str(Path(config()['skill'])/'scripts'/'audit_latex.py'),str(args.project),'--strict'])
    return 0
if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,ValueError,FileNotFoundError,FileExistsError) as error:
        print(str(error),file=sys.stderr);sys.exit(1)
