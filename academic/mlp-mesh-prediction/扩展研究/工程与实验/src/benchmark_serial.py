"""Measure matched-Q endpoints after training jobs have finished."""
from pathlib import Path
from time import perf_counter
import json
import numpy as np
import torch
import scale_study as study
def main():
    data=study.RUN/"data/gaussian_1200"
    model=study.RUN/"models/gaussian_1200_w64_seed20261023/best_model.pt"
    out=study.ROOT/"runs/matched_benchmark_01";out.mkdir(parents=True,exist_ok=True)
    tx,tq,tdx=study.read_data(data,"train")
    study.TRAIN_MU=tx;study.TRAIN_STD=tx.std(0)
    study.TRAIN_Q=np.repeat(study.topology(12)[0][None],len(tx),axis=0)
    study.TRAIN_Q[:,study.topology(12)[3]]+=tq.reshape(len(tx),-1,2)
    study.cost(data,model,out,cases_per_group=100)
    rows=study.readcsv(out/"baseline_cost.csv")
    assert all(float(r["residual"])<=1e-5 for r in rows)
    assert all(float(r["max_coordinate_difference"])<=1e-6 for r in rows)
    study.dump(out/"config.json",dict(model=str(model),data=str(data),test_cases=400,
        cases_per_group=100,repetitions=3,threads=1,training_jobs_active=False,
        residual_norm="combined interior L2",acceptance_residual=1e-5,cg_atol_per_axis=1e-7,
        coordinate_agreement=1e-6,scope="frozen Q objective only"))
    pkg=torch.load(model,map_location="cpu",weights_only=True)
    net=study.FixedMLP(pkg["output_dim"],pkg["width"]);net.load_state_dict(pkg["state_dict"]);net.eval()
    x0,cells,boundary,inside,*_=study.topology(12)
    trainx=np.repeat(x0[None],len(tx),axis=0);trainx[:,inside]+=tdx.reshape(len(tx),-1,2)
    manifest=json.loads((data/"manifest.json").read_text(encoding="utf-8"))
    approximate=[];times=[]
    for rec in manifest["splits"]["test"]:
        mu=np.asarray(rec["spec"]["mu"]);saved=np.load(data/rec["relative_data_path"])
        first={}
        for repeat in range(3):
            order=["MLP_approx","nearest_approx"] if repeat%2==0 else ["nearest_approx","MLP_approx"]
            for method in order:
                start=perf_counter()
                if method=="MLP_approx":
                    q,x,raw,tau,fallback,_=study.predict(net,pkg,mu)
                else:
                    nearest=int(np.argmin(np.sum(((tx-mu)/study.TRAIN_STD)**2,axis=1)))
                    q=study.TRAIN_Q[nearest].copy();x=trainx[nearest].copy()
                    assert np.all(study.signed_areas(q,cells)>1e-10) and np.all(study.signed_areas(x,cells)>1e-10)
                    assert np.all(np.isfinite(x)) and np.array_equal(x[boundary],x0[boundary])
                elapsed=perf_counter()-start
                times.append(dict(id=rec["id"],group=rec["group"],method=method,repeat=repeat,online_seconds=elapsed))
                if repeat==0:
                    first[method]=dict(id=rec["id"],group=rec["group"],method=method,
                        error_relative=float(np.linalg.norm((x-saved["X"])[inside])/np.linalg.norm((saved["X"]-x0)[inside])),
                        coordinate_rmse=float(np.sqrt(np.mean((x[inside]-saved["X"][inside])**2))),
                        interpolation_rmse=study.interpolation(x,cells,mu))
        for method,row in first.items():
            row["online_seconds"]=float(np.mean([t["online_seconds"] for t in times[-6:] if t["method"]==method]))
            approximate.append(row)
    study.csvout(out/"approximate_per_case.csv",approximate)
    study.csvout(out/"approximate_timings.csv",times)
    print("Serial matched-Q benchmark completed",len(rows))
if __name__=="__main__":main()
