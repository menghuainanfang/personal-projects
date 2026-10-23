"""Non-destructive launcher for archived 2026-10-23 baseline experiment.

Usage:
 python workbench.py verify
 python workbench.py prepare --output ../runs/replay_01
This intentionally does not start the long training by itself.
"""
import argparse, hashlib, json, pathlib, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'baseline_archive'/'原始补训练实验.zip'
SHA='8caa114cf5b3e1c050b6a15b71214fe79b58da89e5f0162f7a683bf975bd2a1d'
NEEDED={'pilot.py','validate_and_plot.py','interpolation_check.py','paired_control.py',
        'create_report.py','round5_test_cases.json','fresh_holdout_cases.json',
        'Q_ID140.pt','Q_MIX320_shared.pt','Q_double8.pt','补训练泛化实验报告.md'}

def verify():
    h=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if h!=SHA:raise RuntimeError('Baseline archive digest changed; do not overwrite the signed original')
    with zipfile.ZipFile(ARCHIVE) as z:
        names=set(z.namelist());missing=NEEDED-names
        if missing:raise RuntimeError('Missing archive members: '+str(missing))
        bad=z.testzip()
        if bad:raise RuntimeError('Zip CRC failed: '+bad)
    print('PASS baseline SHA256 '+h)
    print('PASS required files and CRC; baseline artifact is immutable')
    print('Bundle path:',ROOT)

def prepare(output:pathlib.Path):
    verify()
    out=output.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError('Refusing to overwrite nonempty output directory: '+str(out))
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as z:
        for member in z.infolist():
            name=pathlib.PurePosixPath(member.filename)
            if name.is_absolute() or '..' in name.parts:
                raise RuntimeError('unsafe archive member '+member.filename)
        z.extractall(out)
    print('Prepared isolated copy at:',out)
    print('Run in this directory, in order:')
    for line in ('python pilot.py','python validate_and_plot.py',
                 'python interpolation_check.py','python paired_control.py',
                 'python create_report.py'):
        print('  '+line)
    print('Important: running pilot.py overwrites only results inside THIS isolated copy.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['verify','prepare'])
    parser.add_argument('--output',type=pathlib.Path)
    args=parser.parse_args()
    if args.command=='verify':verify()
    elif args.output:prepare(args.output)
    else:parser.error('--output required for prepare')

