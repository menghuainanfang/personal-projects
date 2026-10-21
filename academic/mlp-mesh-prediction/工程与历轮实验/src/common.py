"""Experiment configuration, inherited topology and result serialization."""
from pathlib import Path
import csv
import json
import numpy as np
import yaml

ROOT=Path(__file__).resolve().parents[1]

def load_config():
    return yaml.safe_load((ROOT/'config.yaml').read_text(encoding='utf-8'))

def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def write_csv(path,rows):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def fixed_mesh(n):
    # Node ordering and diagonals are inherited from the previous experiment.
    x,y=np.meshgrid(np.linspace(0,1,n+1),np.linspace(0,1,n+1))
    nodes=np.column_stack((x.ravel(),y.ravel()))
    cells=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i
            cells.extend([[a,a+1,a+n+2],[a,a+n+2,a+n+1]])
    boundary=np.any((nodes==0)|(nodes==1),axis=1)
    return nodes,np.asarray(cells,dtype=np.int64),boundary

def metric_value(points,mu):
    cx,cy,A,sigma=np.asarray(mu,dtype=float)
    w=A*np.exp(-((points[...,0]-cx)**2+(points[...,1]-cy)**2)/sigma**2)
    return 1+w

def metric_tensor(points,mu):
    return metric_value(points,mu)[...,None,None]*np.eye(2)
