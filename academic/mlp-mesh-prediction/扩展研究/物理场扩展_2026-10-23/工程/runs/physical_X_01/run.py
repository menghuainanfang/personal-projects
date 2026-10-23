"""Matched direct-X prediction and physical-energy refinement."""
from pathlib import Path
import sys,json,random,csv,time
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"src"))
from train_fixed_q import FixedMLP,read_data
from teacher_general import topology,signed_areas
from scale_study import dump,csvout,quality,interpolation,predict
from physical_energy import PhysicalEnergy,solve,OPTIONS
import train_fixed_x
from argparse import Namespace
DATA=ROOT/"runs/scale_study_01/data/gaussian_1200"
SEEDS=[20261023,20261024,20261025]
GROUPS=["ID","center","narrow","broad"]
torch.set_num_threads(1)
X0,CELLS,BOUNDARY,INSIDE,*_=topology(12)

class Problem:
    def __init__(self,mu):
        self.reference=X0;self.cells=CELLS;self.boundary=BOUNDARY;self.mu=mu
    def valid(self,x):
        area=float(signed_areas(x,CELLS).min())
        valid=bool(np.isfinite(x).all() and area>1e-10 and
                   x.min()>=-1e-12 and x.max()<=1+1e-12 and
                   np.max(np.abs(x[BOUNDARY]-X0[BOUNDARY]))<=1e-12)
        return dict(valid=valid,min_area=area)

def load(target,seed):
    path=(OUT/"models"/f"X_w128_seed{seed}"/"best_model.pt" if target=="X"
          else ROOT/"runs/scale_study_01/models"/f"gaussian_1200_w128_seed{seed}"/"best_model.pt")
    pkg=torch.load(path,map_location="cpu",weights_only=True)
    model=FixedMLP(pkg["output_dim"],pkg["width"])
    model.load_state_dict(pkg["state_dict"]);model.eval()
    return model,pkg

def direct_x(model,pkg,mu):
    with torch.inference_mode():
        a=(mu-np.asarray(pkg["input_mean"]))/np.asarray(pkg["input_std"])
        disp=model(torch.tensor(a,dtype=torch.float32)[None]).numpy().reshape(-1,2)*pkg["label_scale"]
    raw=X0.copy();raw[INSIDE]+=disp
    problem=Problem(mu);valid=problem.valid(raw)["valid"]
    if valid:return raw,raw,True,1.,False
    for k in range(1,21):
        safe=X0.copy();safe[INSIDE]+=2.**(-k)*disp
        if problem.valid(safe)["valid"]:return raw,safe,False,2.**(-k),False
    return raw,X0.copy(),False,0.,True

def predicted(target,model,pkg,mu):
    if target=="X":return direct_x(model,pkg,mu)
    q,x,legal,tau,fallback,_=predict(model,pkg,mu)
    return None,x,legal,tau,fallback

def main():
    manifest=json.loads((DATA/"manifest.json").read_text(encoding="utf-8"))
    dump(OUT/"config.json",dict(data=str(DATA),train=1200,validation=400,test=400,n=12,
        width=128,seeds=SEEDS,epochs=2000,batch=128,patience=200,min_delta=1e-7,
        learning_rate=.001,weight_decay=1e-6,device="cpu",threads=1,
        physical_cases_per_group=5,physical_timing_repeats=2,
        physical_model_seed=SEEDS[0],physical_options=OPTIONS,
        physical_subset="First five manifest test records in each of four groups; fixed before evaluation",
        target="X reconstructed from the existing frozen-Q teachers; not physical-energy minimizers"))
    for seed in SEEDS:
        out=OUT/"models"/f"X_w128_seed{seed}"
        if not (out/"best_model.pt").exists():
            start=time.perf_counter()
            args=Namespace(data=DATA,output=out,seed=seed,device="cpu",width=128,
                lr=.001,epochs=2000,batch=128,patience=200,min_delta=1e-7)
            train_fixed_x.train(args)
            dump(out/"timing.json",dict(training_seconds=time.perf_counter()-start))
        print("TRAINED X",seed,flush=True)
    models={(t,s):load(t,s) for t in ["X","Q"] for s in SEEDS}
    rows=[];states=OUT/"prediction_states";states.mkdir(exist_ok=True)
    for i,rec in enumerate(manifest["splits"]["test"]):
        d=np.load(DATA/rec["relative_data_path"]);mu=np.array(rec["spec"]["mu"]);ref=d["X"]
        ref_rmse=interpolation(ref,CELLS,mu);regular_rmse=interpolation(X0,CELLS,mu)
        denom=np.linalg.norm((ref-X0)[INSIDE]);problem=Problem(mu);energy=PhysicalEnergy(problem)
        arrays=dict(teacher_X=ref,X0=X0,cells=CELLS,mu=mu)
        for target in ["X","Q"]:
            for seed in SEEDS:
                model,pkg=models[target,seed]
                times=[]
                for _ in range(3):
                    start=time.perf_counter()
                    raw,x,legal,tau,fallback=predicted(target,model,pkg,mu)
                    times.append(time.perf_counter()-start)
                rows.append(dict(id=rec["id"],group=rec["group"],target=target,seed=seed,
                    error_relative=float(np.linalg.norm((x-ref)[INSIDE])/denom),
                    coordinate_rmse=float(np.sqrt(np.mean((x[INSIDE]-ref[INSIDE])**2))),
                    raw_valid=legal,tau=tau,fallback=fallback,
                    interpolation_rmse=interpolation(x,CELLS,mu),
                    teacher_interpolation_rmse=ref_rmse,regular_interpolation_rmse=regular_rmse,
                    physical_energy=energy.value(x),predict_seconds=float(np.median(times)),**quality(x,CELLS)))
                arrays[f"{target}_{seed}"]=x
                if raw is not None:arrays[f"raw_X_{seed}"]=raw
        np.savez_compressed(states/f"{rec['id']}.npz",**arrays)
        if (i+1)%100==0:print("EVALUATED",i+1,flush=True)
    csvout(OUT/"prediction_per_case.csv",rows)
    aggregate=[]
    for target in ["X","Q"]:
        for seed in SEEDS:
            for group in GROUPS+["ALL"]:
                sub=[r for r in rows if r["target"]==target and r["seed"]==seed and (group=="ALL" or r["group"]==group)]
                a=dict(target=target,seed=seed,group=group,n=len(sub),
                    raw_legal_rate=float(np.mean([r["raw_valid"] for r in sub])))
                for key in ["error_relative","coordinate_rmse","interpolation_rmse","teacher_interpolation_rmse",
                    "regular_interpolation_rmse","physical_energy","predict_seconds","min_angle","min_quality"]:
                    a[key]=float(np.mean([r[key] for r in sub]))
                aggregate.append(a)
    csvout(OUT/"prediction_aggregate.csv",aggregate)
    chosen=sum(([r for r in manifest["splits"]["test"] if r["group"]==g][:5] for g in GROUPS),[])
    dump(OUT/"physical_subset.json",chosen)
    # Detect a derivative/adapter mismatch before using the reused optimizer.
    p=Problem(np.array(chosen[0]["spec"]["mu"]));e=PhysicalEnergy(p)
    rng=np.random.default_rng(2015);v=rng.normal(size=X0.shape);v[BOUNDARY]=0;v/=np.linalg.norm(v)
    value,g=e.value_gradient(X0);h=1e-6
    fd=(e.value(X0+h*v)-e.value(X0-h*v))/(2*h);ad=float(np.sum(g*v))
    discrepancy=abs(fd-ad)/max(1.,abs(fd),abs(ad))
    if discrepancy>1e-6:raise RuntimeError("Physical derivative mismatch")
    dump(OUT/"physical_gradient_check.json",dict(relative_discrepancy=discrepancy,finite_difference=fd,autodiff=ad))
    features,_,labels=read_data(DATA,"train");std=features.std(0)
    train_x=np.repeat(X0[None],len(labels),axis=0);train_x[:,INSIDE]+=labels.reshape(len(labels),-1,2)
    refined=[];save=OUT/"refinement_states";save.mkdir(exist_ok=True)
    for i,rec in enumerate(chosen):
        mu=np.array(rec["spec"]["mu"]);problem=Problem(mu)
        nearest=int(np.argmin(np.sum(((features-mu)/std)**2,axis=1)))
        for repeat in range(2):
            methods=["regular","X_MLP","Q_MLP","nearest_X"]
            if repeat%2:methods.reverse()
            for method in methods:
                start=time.perf_counter()
                if method=="regular":initial=X0.copy()
                elif method=="nearest_X":
                    ix=int(np.argmin(np.sum(((features-mu)/std)**2,axis=1)));initial=train_x[ix].copy()
                else:
                    target=method[0];initial=predicted(target,*models[target,SEEDS[0]],mu)[1]
                sol=solve(problem,initial);elapsed=time.perf_counter()-start
                x=sol["X"];summary=sol["summary"]
                refined.append(dict(id=rec["id"],group=rec["group"],repeat=repeat,method=method,
                    online_seconds=elapsed,**summary,interpolation_rmse=interpolation(x,CELLS,mu),**quality(x,CELLS)))
                if repeat==0:
                    np.savez_compressed(save/f"{rec['id']}_{method}.npz",X=x,initial_X=initial,X0=X0,cells=CELLS,mu=mu)
                    csvout(save/f"{rec['id']}_{method}_history.csv",sol["history"])
                csvout(OUT/"physical_per_case.csv",refined)
        print("PHYSICAL",i+1,rec["group"],flush=True)
    dump(OUT/"complete.json",dict(prediction_records=len(rows),physical_records=len(refined)))
if __name__=="__main__":main()
