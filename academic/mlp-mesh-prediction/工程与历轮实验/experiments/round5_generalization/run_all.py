"""Run the independent evaluation, paper checks and Chinese report."""
from pathlib import Path
import argparse,os,subprocess,sys
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports-only',action='store_true')
    args=parser.parse_args()
    env=os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    jobs=[] if args.reports_only else [
        ['-m','unittest','test_study','-v'],['study.py'],['paper_checks.py'],['theory_checks.py'],['verify.py']]
    jobs.append(['build_report.py'])
    for job in jobs:
        print('Running '+' '.join(job),flush=True)
        subprocess.run([sys.executable,*job],cwd=ROOT,env=env,check=True)

if __name__=='__main__':main()
