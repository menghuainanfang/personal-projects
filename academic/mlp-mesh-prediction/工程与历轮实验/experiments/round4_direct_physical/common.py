"""Shared paths, saved datasets and model interfaces."""
from pathlib import Path
import sys,json,csv
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]
sys.path.insert(0,str(SOURCE))
import numpy as np
from src.common import load_config,write_json,write_csv
from src.teacher import Problem
from src.network import Predictor
from src.geometry import signed_triangle_areas
from safe_prediction import safe_prediction
CFG=load_config()
SPLIT=json.loads((SOURCE/'data/split.json').read_text(encoding='utf-8'))
IDS=SPLIT['test']+['case_center','case_shifted','case_strength']
for folder in ['results','results/meshes','results/histories','paper','presentation']:
    (ROOT/folder).mkdir(parents=True,exist_ok=True)

def data(iid):
    with np.load(SOURCE/f'data/teacher/{iid}.npz') as d:
        return {k:d[k].copy() for k in d.files}

def read_rows(name):
    return list(csv.DictReader((ROOT/'results'/name).open(encoding='utf-8-sig')))

def physical_safe(problem,raw):
    """Restrict physical displacement without any coordinate conversion."""
    for k in range(21):
        tau=2.**(-k);x=problem.X0+tau*(raw-problem.X0)
        x[problem.boundary]=problem.X0[problem.boundary]
        if problem.valid(x)['valid']:
            return x,dict(tau=tau,backtracks=k,fallback=False)
    return problem.X0.copy(),dict(tau=0.,backtracks=21,fallback=True)

