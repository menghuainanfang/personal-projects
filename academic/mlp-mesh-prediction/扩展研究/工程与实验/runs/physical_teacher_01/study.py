"""Supervised physical-X learning with nonlinear physical-energy teachers."""
from pathlib import Path
import os
for key in ["OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"]:os.environ[key]="1"
import sys,json,csv,time,copy
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import torch
from argparse import Namespace
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
OLD=ROOT/"runs/physical_X_01"
sys.path.insert(0,str(OLD))
sys.path.insert(0,str(ROOT/"src"))
from run import Problem,direct_x,load
from physical_energy import solve,OPTIONS,PhysicalEnergy
from teacher_general import topology
from scale_study import dump,csvout,interpolation,quality,predict
from train_fixed_q import FixedMLP
import train_fixed_x
DATA=ROOT/"runs/scale_study_01/data/gaussian_1200"
X0,CELLS,BOUNDARY,INSIDE,*_=topology(12)
SEEDS=[20261023,20261024,20261025]
torch.set_num_threads(1)

def teacher(rec):
    path=OUT/"data/teachers"/f"{rec['id']}.npz"
    meta=path.with_suffix(".json")
    if meta.exists():return json.loads(meta.read_text(encoding="utf-8"))
    mu=np.asarray(rec["spec"]["mu"]);problem=Problem(mu)
    sol=solve(problem,X0)
    if not sol["summary"]["converged"]:
        options=dict(OPTIONS,max_iterations=10000,max_energy_evaluations=100000)
        sol=solve(problem,sol["X"],options)
    summary=dict(id=rec["id"],group=rec["group"],**sol["summary"])
    if summary["converged"]:
        source=np.load(DATA/rec["relative_data_path"])
        np.savez_compressed(path,X0=X0,cells=CELLS,boundary=BOUNDARY,Q=source["Q"],X=sol["X"])
    dump(meta,summary)
    return summary

def main():
    (OUT/"data/teachers").mkdir(parents=True,exist_ok=True)
    m=json.loads((DATA/"manifest.json").read_text(encoding="utf-8"))
    dump(OUT/"config.json",dict(train_requested=1200,validation_requested=400,test_requested=400,
        label="nonlinear physical energy minimizer from regular X",options=OPTIONS,
        retry_iterations=10000,retry_evaluations=100000,seeds=SEEDS,width=128,epochs=2000,
        batch=128,lr=.001,patience=200,workers=6,online_threads=1))
    records=sum(m["splits"].values(),[])
    with ProcessPoolExecutor(max_workers=6) as pool:
        for i,res in enumerate(pool.map(teacher,records,chunksize=1)):
            if (i+1)%100==0:print("PHYSICAL TEACHERS",i+1,flush=True)
    summary=[json.loads((OUT/"data/teachers"/f"{r['id']}.json").read_text(encoding="utf-8")) for r in records]
    csvout(OUT/"teacher_status.csv",summary)
    passed={r["id"] for r in summary if r["converged"]}
    for split,items in m["splits"].items():
        m["splits"][split]=[dict(r,relative_data_path=f"teachers/{r['id']}.npz") for r in items if r["id"] in passed]
    dump(OUT/"data/manifest.json",m)
    for seed in SEEDS:
        dest=OUT/"models"/f"physical_X_seed{seed}"
        if not (dest/"best_model.pt").exists():
            start=time.perf_counter()
            train_fixed_x.train(Namespace(data=OUT/"data",output=dest,seed=seed,device="cpu",
                width=128,lr=.001,epochs=2000,batch=128,patience=200,min_delta=1e-7))
            dump(dest/"training_time.json",dict(seconds=time.perf_counter()-start))
        print("TRAINED",seed,flush=True)
    rows=[]
    for seed in SEEDS:
        pkg=torch.load(OUT/"models"/f"physical_X_seed{seed}"/"best_model.pt",map_location="cpu",weights_only=True)
        model=FixedMLP(242,128);model.load_state_dict(pkg["state_dict"]);model.eval()
        oldx,oldxp=load("X",seed);oldq,oldqp=load("Q",seed)
        for rec in m["splits"]["test"]:
            mu=np.asarray(rec["spec"]["mu"]);ref=np.load(OUT/"data"/rec["relative_data_path"])["X"]
            states=dict(teacher_X=ref,X0=X0,cells=CELLS,mu=mu)
            for name,net,cp in [("physical_X",model,pkg),("Q_teacher_X",oldx,oldxp),("Q_MLP",oldq,oldqp)]:
                times=[]
                for _ in range(3):
                    start=time.perf_counter()
                    if name=="Q_MLP":_,x,valid,tau,fallback,_=predict(net,cp,mu)
                    else:raw,x,valid,tau,fallback=direct_x(net,cp,mu)
                    times.append(time.perf_counter()-start)
                rows.append(dict(id=rec["id"],group=rec["group"],seed=seed,method=name,raw_valid=valid,tau=tau,
                    error_relative=float(np.linalg.norm((x-ref)[INSIDE])/np.linalg.norm((ref-X0)[INSIDE])),
                    interpolation_rmse=interpolation(x,CELLS,mu),teacher_interpolation_rmse=interpolation(ref,CELLS,mu),
                    regular_interpolation_rmse=interpolation(X0,CELLS,mu),
                    energy=PhysicalEnergy(Problem(mu)).value(x),predict_seconds=float(np.median(times)),**quality(x,CELLS)))
                states[name]=x
            if seed==SEEDS[0]:
                (OUT/"test_states").mkdir(exist_ok=True)
                np.savez_compressed(OUT/"test_states"/f"{rec['id']}.npz",**states)
        csvout(OUT/"prediction.csv",rows)
    selected=json.loads((OLD/"physical_subset.json").read_text(encoding="utf-8"))
    physical=[]
    pkg=torch.load(OUT/"models"/f"physical_X_seed{SEEDS[0]}"/"best_model.pt",map_location="cpu",weights_only=True)
    model=FixedMLP(242,128);model.load_state_dict(pkg["state_dict"]);model.eval()
    oldx,oldxp=load("X",SEEDS[0]);oldq,oldqp=load("Q",SEEDS[0])
    for i,rec in enumerate(selected):
        mu=np.asarray(rec["spec"]["mu"]);p=Problem(mu)
        for repeat in range(2):
            methods=["regular","physical_X","Q_teacher_X","Q_MLP"]
            if repeat:methods.reverse()
            for name in methods:
                start=time.perf_counter()
                if name=="regular":x=X0.copy()
                elif name=="physical_X":x=direct_x(model,pkg,mu)[1]
                elif name=="Q_teacher_X":x=direct_x(oldx,oldxp,mu)[1]
                else:x=predict(oldq,oldqp,mu)[1]
                result=solve(p,x);elapsed=time.perf_counter()-start
                physical.append(dict(id=rec["id"],group=rec["group"],repeat=repeat,method=name,
                    online_seconds=elapsed,**result["summary"]))
                csvout(OUT/"refinement.csv",physical)
        print("REFINED",i+1,flush=True)
    dump(OUT/"complete.json",dict(split_sizes={k:len(v) for k,v in m["splits"].items()},
        failed_teachers=len(records)-len(passed),prediction_rows=len(rows),refinement_rows=len(physical)))
if __name__=="__main__":main()
