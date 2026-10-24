"""Frozen field model: size scaling on MMPDElab analytic examples."""
from pathlib import Path
import os
for k in ["OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"]:os.environ[k]="1"
import sys,time,json,csv
import numpy as np
import torch
from scipy.interpolate import RegularGridInterpolator
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/"runs/physical_field_training_04"))
import study as learner
physics=learner.physics
torch.set_num_threads(1)
original_field=physics.field
def field(points,spec):
    if spec["kind"]!="five_ring":return original_field(points,spec)
    x=-2+4*points[...,0];y=-2+4*points[...,1]
    ds=[x*x+y*y-1/8]+[(x-a)**2+(y-b)**2-1/8 for a,b in [(.5,.5),(.5,-.5),(-.5,.5),(-.5,-.5)]]
    return sum(torch.tanh(30*d) for d in ds),1+8*sum(torch.exp(-(30*d)**2) for d in ds)
physics.field=field
original_exact=physics.exact
def exact(points,spec,forcing=False):
    if not forcing:return original_exact(points,spec,False)
    return np.concatenate([original_exact(points[i:i+32768],spec,True) for i in range(0,len(points),32768)])
physics.exact=exact
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
def csvout(name,rows):
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
def prolong(coarse,nc,problem):
    t=np.linspace(0,1,nc+1);displacement=(coarse-physics.Problem(nc,problem.spec).reference).reshape(nc+1,nc+1,2)
    interpolator=RegularGridInterpolator((t,t),displacement)
    x=problem.reference+interpolator(problem.reference[:,[1,0]])
    x[problem.boundary]=problem.reference[problem.boundary]
    tau=1.
    while not problem.valid(x)["valid"]:
        tau*=.5;x=problem.reference+tau*(x-problem.reference)
    return x
def main():
    (OUT/"states").mkdir(exist_ok=True)
    config=dict(n=[12,24,48,96],repeats=2,seed=None,training="none; frozen physical_field_training_04 model",
        cases=[dict(kind="wave",phase=0.,strength=8.),dict(kind="five_ring")],
        source="MMPDElab examples/ex2d_1.m cases 3 and 5",
        changes="custom scalar M=mI; fixed whole boundary; L-BFGS, not ode15s; manufactured Dirichlet Poisson",
        tolerance=1e-5,max_iterations=3000,max_evaluations=30000,threads=1)
    dump("config.json",config)
    ck=torch.load(ROOT/"runs/physical_field_training_04/model.pt",map_location="cpu",weights_only=True)
    net=learner.FieldNet();net.load_state_dict(ck["state_dict"]);net.eval()
    results=[];predictions=[];pdes=[]
    for spec in config["cases"]:
        coarse=None;coarse_n=None;coarse_cost=[]
        for n in config["n"]:
            problem=physics.Problem(n,spec);rec=dict(n=n,spec=spec)
            learner.predict(net,ck,rec)
            predictions_times=[]
            for _ in range(3):
                st=time.perf_counter();raw,safe,valid,tau=learner.predict(net,ck,rec)
                predictions_times.append(time.perf_counter()-st)
            predictions.append(dict(kind=spec["kind"],n=n,nodes=len(safe),raw_valid=valid,tau=tau,
                predict_seconds=float(np.median(predictions_times)),raw_min_area=problem.valid(raw)["min_area"]))
            arrays=dict(X0=problem.reference,raw=raw,direct=safe,cells=problem.cells)
            # Use the same reference grid and model warm-up for all online methods.
            physics.FieldEnergy(problem).value_gradient(problem.reference)
            regular_times=[]
            for repeat in range(2):
                methods=["regular","network","coarse_to_fine"]
                if repeat:methods.reverse()
                for method in methods:
                    st=time.perf_counter()
                    if method=="regular":initial=problem.reference.copy()
                    elif method=="network":initial=learner.predict(net,ck,rec)[1]
                    elif coarse is None:initial=problem.reference.copy()
                    else:initial=prolong(coarse,coarse_n,problem)
                    sol=physics.physical_lbfgs(problem,initial,physics.FieldEnergy)
                    elapsed=time.perf_counter()-st
                    added=float(coarse_cost[-1]) if method=="coarse_to_fine" and coarse_cost else 0.
                    row=dict(kind=spec["kind"],n=n,nodes=len(initial),repeat=repeat,method=method,
                        online_seconds=elapsed,total_with_coarse_seconds=elapsed+added,**sol["summary"])
                    results.append(row);csvout("timings.csv",results)
                    if method=="regular":regular_times.append(elapsed)
                    if repeat==0:
                        arrays[method]=sol["X"]
                        csvout(f"states/{spec['kind']}_{n}_{method}_history.csv",sol["history"])
                    print("SOLVED",spec["kind"],n,repeat,method,round(elapsed,3),sol["summary"]["stop_reason"],flush=True)
            coarse=arrays["regular"];coarse_n=n
            np.savez_compressed(OUT/"states"/f"{spec['kind']}_{n}.npz",**arrays)
            for method in ["X0","direct","regular","network","coarse_to_fine"]:
                x=arrays[method]
                order=32 if spec["kind"]=="five_ring" and n==12 else 12 if spec["kind"]=="five_ring" and n==24 else 8
                st=time.perf_counter();uh,residual=physics.poisson(x,problem.cells,problem.boundary,spec,order=order)
                duration=time.perf_counter()-st
                if residual>1e-9:raise RuntimeError(("PDE residual",residual))
                error=physics.l2_error(x,problem.cells,uh,spec,order=order)
                pdes.append(dict(kind=spec["kind"],n=n,method=method,nodes=len(x),poisson_seconds=duration,
                    poisson_l2=error,linear_residual=residual,min_area=problem.valid(x)["min_area"],quadrature_order=order))
                csvout("pde.csv",pdes)
            coarse_cost.append(float(np.median(regular_times)))
            csvout("predictions.csv",predictions)
            print("CASE COMPLETE",spec["kind"],n,flush=True)
    dump("complete.json",dict(solves=len(results),pde_cases=len(pdes),predictions=len(predictions)))
if __name__=="__main__":main()
