"""Validated quadrature and isolated timing for the completed experiment."""
from pathlib import Path
import csv,json,time
import numpy as np
import torch
import benchmark as b
OUT=b.OUT
def read(name):return list(csv.DictReader((OUT/name).open(encoding="utf-8-sig")))
def main():
    pde=read("pde.csv")
    for row in pde:
        n=int(row["n"]);kind=row["kind"]
        order=32 if kind=="five_ring" and n==12 else 12 if kind=="five_ring" and n==24 else 8
        row["quadrature_order"]=order
        if order==8:continue
        d=np.load(OUT/"states"/f"{kind}_{n}.npz");x=d[row["method"]]
        problem=b.physics.Problem(n,dict(kind=kind))
        st=time.perf_counter();uh,res=b.physics.poisson(x,problem.cells,problem.boundary,problem.spec,order=order)
        elapsed=time.perf_counter()-st
        row.update(poisson_seconds=elapsed,poisson_l2=b.physics.l2_error(x,problem.cells,uh,problem.spec,order=order),
                   linear_residual=res)
    b.csvout("pde.csv",pde)
    ck=torch.load(b.ROOT/"runs/physical_field_training_04/model.pt",map_location="cpu",weights_only=True)
    net=b.learner.FieldNet();net.load_state_dict(ck["state_dict"]);net.eval()
    rows=read("timings.csv")
    for n in [48,96]:
        p=b.physics.Problem(n,dict(kind="five_ring"));rec=dict(n=n,spec=p.spec)
        nc=n//2;coarse=np.load(OUT/"states"/f"five_ring_{nc}.npz")["regular"]
        saved=np.load(OUT/"states"/f"five_ring_{n}.npz")
        arrays={k:saved[k] for k in saved.files}
        b.learner.predict(net,ck,rec);b.physics.FieldEnergy(p).value_gradient(p.reference)
        fresh=[]
        for repeat in range(2):
            methods=["regular","network","coarse_to_fine"]
            if repeat:methods.reverse()
            for method in methods:
                start=time.perf_counter()
                if method=="regular":initial=p.reference.copy()
                elif method=="network":initial=b.learner.predict(net,ck,rec)[1]
                else:initial=b.prolong(coarse,nc,p)
                sol=b.physics.physical_lbfgs(p,initial,b.physics.FieldEnergy)
                elapsed=time.perf_counter()-start
                row=dict(kind="five_ring",n=n,nodes=len(initial),repeat=repeat,method=method,
                    online_seconds=elapsed,total_with_coarse_seconds=elapsed,**sol["summary"])
                fresh.append(row)
                if repeat==0:
                    arrays[method]=sol["X"]
                    b.csvout(f"states/five_ring_{n}_{method}_history.csv",sol["history"])
                print("TIMED",n,repeat,method,round(elapsed,3),flush=True)
        rows=[r for r in rows if not(r["kind"]=="five_ring" and int(r["n"])==n)]+fresh
        b.csvout("timings.csv",rows)
        np.savez_compressed(OUT/"states"/f"five_ring_{n}.npz",**arrays)
    print("FINALIZED",flush=True)
if __name__=="__main__":main()
