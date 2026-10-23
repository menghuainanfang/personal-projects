"""Controlled Gaussian coverage, capacity and sparse-solver comparisons."""
from pathlib import Path
from time import perf_counter
import argparse,csv,json,os,subprocess,sys,copy
import numpy as np
import torch
from scipy import sparse
from scipy.sparse.linalg import cg
from matplotlib.tri import Triangulation,LinearTriInterpolator
from dataset_factory import specs,kind_group,shared_old_140,sample_gaussian
from teacher_general import topology,make_teacher,signed_areas
from train_fixed_q import FixedMLP,read_data,train
from eval_fixed_q import reconstruct
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/"runs/scale_study_01"
SEEDS=[20261023,20261024,20261025]
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
def csvout(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def field(x,mu):return np.exp(-((x-np.asarray(mu[:2]))**2).sum(-1)/mu[3]**2)
def interpolation(x,cells,mu):
    t=(np.arange(80)+.5)/80;xx,yy=np.meshgrid(t,t)
    z=np.column_stack([xx.ravel(),yy.ravel()])
    v=LinearTriInterpolator(Triangulation(x[:,0],x[:,1],cells),field(x,mu))(z[:,0],z[:,1])
    if np.ma.getmaskarray(v).any():raise ValueError("Interpolation outside domain")
    return float(np.sqrt(np.mean((np.asarray(v)-field(z,mu))**2)))
def quality(x,cells):
    t=x[cells];length=np.stack([np.linalg.norm(t[:,i]-t[:,(i+1)%3],axis=1) for i in range(3)],1)
    angles=[]
    for i in range(3):
        a,b,c=length[:,i],length[:,(i+1)%3],length[:,(i+2)%3]
        angles.append(np.degrees(np.arccos(np.clip((b*b+c*c-a*a)/(2*b*c),-1,1))))
    area=signed_areas(x,cells)
    return dict(min_area=float(area.min()),min_angle=float(np.min(angles)),
        min_quality=float(np.min(4*np.sqrt(3)*area/(length*length).sum(1))))
def matrix(mu):
    x0,cells,boundary,inside,bnodes,areas,local,row,col=topology(12)
    m=1+mu[2]*field(x0[cells].mean(1),mu)
    return sparse.coo_matrix(((local/m[:,None,None]).ravel(),(row,col)),shape=(len(x0),len(x0))).tocsr()
def predict(model,pkg,mu):
    x0,cells,boundary,inside,*_=topology(12)
    with torch.inference_mode():
        vec=(mu-np.asarray(pkg["input_mean"]))/np.asarray(pkg["input_std"])
        disp=model(torch.tensor(vec,dtype=torch.float32)[None]).numpy().reshape(-1,2)*pkg["label_scale"]
    q=x0.copy();q[inside]+=disp
    raw_area=float(signed_areas(q,cells).min())
    rawx=reconstruct(q,x0,cells,boundary);raw_valid=rawx is not None
    if raw_valid:return q,rawx,True,1.,False,raw_area
    for k in range(1,21):
        q=x0.copy();q[inside]+=2.**(-k)*disp
        x=reconstruct(q,x0,cells,boundary)
        if x is not None:return q,x,raw_valid,2.**(-k),False,raw_area
    return x0.copy(),x0.copy(),raw_valid,0.,True,raw_area
def evaluate(data,modelpath,out):
    torch.set_num_threads(1)
    pkg=torch.load(modelpath,map_location="cpu",weights_only=True)
    model=FixedMLP(pkg["output_dim"],pkg["width"]);model.load_state_dict(pkg["state_dict"]);model.eval()
    manifest=json.loads((data/"manifest.json").read_text(encoding="utf-8"))
    x0,cells,boundary,inside,*_=topology(12);rows=[];failures=[]
    for i,rec in enumerate(manifest["splits"]["test"]):
        d=np.load(data/rec["relative_data_path"]);mu=np.asarray(rec["spec"]["mu"])
        start=perf_counter();q,x,raw,tau,fallback,raw_area=predict(model,pkg,mu);duration=perf_counter()-start
        k=matrix(mu);qref=d["Q"];xref=d["X"]
        err=float(np.linalg.norm((x-xref)[inside])/max(np.linalg.norm((xref-x0)[inside]),1e-14))
        row=dict(id=rec["id"],group=rec["group"],error_relative=err,
            coordinate_rmse=float(np.sqrt(np.mean((x[inside]-xref[inside])**2))),
            raw_valid=raw,safe_valid=True,raw_q_min_area=raw_area,tau=tau,fallback=fallback,
            interpolation_rmse=interpolation(x,cells,mu),teacher_interpolation_rmse=interpolation(xref,cells,mu),
            regular_interpolation_rmse=interpolation(x0,cells,mu),
            initial_energy=float(.5*np.sum(q*(k@q))),teacher_energy=float(.5*np.sum(qref*(k@qref))),
            initial_gradient_norm=float(np.linalg.norm((k@q)[inside])),predict_seconds=duration,**quality(x,cells))
        rows.append(row)
        if not raw or fallback:failures.append(dict(id=rec["id"],group=rec["group"],raw_valid=raw,tau=tau))
    csvout(out/"metrics_per_case.csv",rows);dump(out/"failures.json",failures)
    agg=[]
    for group in list(dict.fromkeys(r["group"] for r in rows))+["ALL"]:
        sub=[r for r in rows if group=="ALL" or r["group"]==group]
        row=dict(group=group,n=len(sub),raw_legal_rate=np.mean([r["raw_valid"] for r in sub]),
            fallback_rate=np.mean([r["fallback"] for r in sub]))
        for key in ["error_relative","coordinate_rmse","interpolation_rmse","teacher_interpolation_rmse",
            "regular_interpolation_rmse","predict_seconds","min_angle","min_quality","tau"]:
            vals=np.array([r[key] for r in sub]);row[key]=float(vals.mean())
            if key=="error_relative":
                row.update(error_std=float(vals.std(ddof=1)),error_median=float(np.median(vals)),
                    error_worst10=float(np.sort(vals)[-max(1,int(np.ceil(.1*len(vals)))):].mean()))
        agg.append(row)
    csvout(out/"aggregate.csv",agg)
    worst=sorted(rows,key=lambda r:r["error_relative"],reverse=True)[:5]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,5,figsize=(15,6))
    for j,row in enumerate(worst):
        rec=next(r for r in manifest["splits"]["test"] if r["id"]==row["id"])
        d=np.load(data/rec["relative_data_path"]);_,x,*_=predict(model,pkg,np.asarray(rec["spec"]["mu"]))
        for ax,coords,title in [(axs[0,j],d["X"],row["group"]+" teacher"),(axs[1,j],x,f"pred {100*row['error_relative']:.1f}%")]:
            ax.triplot(coords[:,0],coords[:,1],cells,lw=.4);ax.set_aspect("equal");ax.set_title(title);ax.set_xlim(0,1);ax.set_ylim(0,1)
    fig.tight_layout();fig.savefig(out/"worst5.png",dpi=150);plt.close(fig)
    return rows
def cost(data,modelpath,out,cases_per_group=10):
    pkg=torch.load(modelpath,map_location="cpu",weights_only=True);torch.set_num_threads(1)
    model=FixedMLP(pkg["output_dim"],pkg["width"]);model.load_state_dict(pkg["state_dict"]);model.eval()
    manifest=json.loads((data/"manifest.json").read_text(encoding="utf-8"))
    chosen=sum(([r for r in manifest["splits"]["test"] if r["group"]==g][:cases_per_group] for g in ["ID","center","narrow","broad"]),[])
    x0,cells,boundary,inside,bnodes,*_=topology(12);rows=[]
    for rec in chosen:
        mu=np.asarray(rec["spec"]["mu"]);saved=np.load(data/rec["relative_data_path"])
        for repeat in range(3):
            methods=["sparse_direct","cg_regular","cg_mlp","cg_nearest"]
            if repeat%2:methods.reverse()
            for method in methods:
                start=perf_counter();iterations=0
                if method=="sparse_direct":
                    ref=make_teacher(12,rec["spec"]);q,x=ref["Q"],ref["X"];residual=ref["residual"]
                else:
                    k=matrix(mu);kii=k[inside,:][:,inside];rhs=-k[inside,:][:,bnodes]@x0[bnodes]
                    initial=x0.copy()
                    if method=="cg_mlp":initial=predict(model,pkg,mu)[0]
                    if method=="cg_nearest":
                        nearest=np.argmin(np.sum(((TRAIN_MU-mu)/TRAIN_STD)**2,axis=1))
                        initial=TRAIN_Q[nearest].copy()
                    q=x0.copy()
                    def callback(_):
                        nonlocal iterations
                        iterations+=1
                    for axis in range(2):
                        v,info=cg(kii,rhs[:,axis],x0=initial[inside,axis],rtol=0,atol=1e-7,maxiter=2000,callback=callback)
                        if info!=0:raise RuntimeError(("CG did not converge",info))
                        q[inside,axis]=v
                    x=reconstruct(q,x0,cells,boundary)
                    if x is None:raise RuntimeError("Invalid CG endpoint")
                    residual=float(np.linalg.norm((k@q)[inside]))
                elapsed=perf_counter()-start
                residual=float(np.linalg.norm((matrix(mu)@q)[inside]))
                rows.append(dict(id=rec["id"],group=rec["group"],repeat=repeat,method=method,
                    online_seconds=elapsed,iterations_sum_axes=iterations,residual=residual,
                    max_coordinate_difference=float(np.max(np.abs(x-saved["X"])))))
    csvout(out/"baseline_cost.csv",rows)
def datasets():
    for name in ["gaussian_1200","gaussian_3000"]:
        subprocess.run([sys.executable,str(ROOT/"src/dataset_factory.py"),"--preset",name,
            "--output",str(RUN/"data"/name),"--resolutions","12"],check=True)
    small=RUN/"data/gaussian_1200";large=RUN/"data/gaussian_3000"
    sm=json.loads((small/"manifest.json").read_text(encoding="utf-8"));lg=json.loads((large/"manifest.json").read_text(encoding="utf-8"))
    def keys(m,s):return {json.dumps(r["spec"],sort_keys=True) for r in m["splits"][s]}
    assert keys(sm,"train")<=keys(lg,"train")
    assert keys(sm,"validation")==keys(lg,"validation") and keys(sm,"test")==keys(lg,"test")
    for split in ["train","validation","test"]:
        for other in ["train","validation","test"]:
            if split!=other:assert not keys(lg,split)&keys(lg,other)
    dump(RUN/"nested_split_check.json",dict(training_nested=True,validation_identical=True,test_identical=True,
        small_requested=sm["requested"],large_requested=lg["requested"],small_failed=sm["failed"],large_failed=lg["failed"]))
    for name,items in [("ID140",shared_old_140()),("ID320",shared_old_140()+sample_gaussian("ID",180,81001)),
        ("MIX320",shared_old_140()+sum((sample_gaussian(g,60,81002+i) for i,g in enumerate(["center","narrow","broad"])),[]))]:
        wanted={json.dumps(s,sort_keys=True) for s in items};m=copy.deepcopy(lg)
        m["splits"]["train"]=[r for r in lg["splits"]["train"] if json.dumps(r["spec"],sort_keys=True) in wanted]
        assert len(m["splits"]["train"])==len(items)
        # All variants point to the single large library, without copying teacher files.
        for arr in m["splits"].values():
            for r in arr:r["relative_data_path"]="../gaussian_3000/"+r["relative_data_path"]
        m["preset"]=name;m["requested"]["train"]=len(items);m["valid"]["train"]=len(items);m["failed"]["train"]=0
        dump(RUN/"data"/name/"manifest.json",m)
def main():
    RUN.mkdir(parents=True,exist_ok=True)
    config=dict(model_seeds=SEEDS,epochs=2000,patience=200,batch=128,device="cpu",threads=1,
        description="Frozen Q objective; shared validation/test; batch fixed across new controlled variants")
    dump(RUN/"config.json",config);datasets()
    jobs=[("gaussian_1200",64,s) for s in SEEDS]+[("ID140",64,SEEDS[0]),("ID320",64,SEEDS[0]),("MIX320",64,SEEDS[0])]
    jobs += [("gaussian_3000",64,s) for s in SEEDS]+[("gaussian_1200",128,s) for s in SEEDS]
    summaries=[]
    for dataset,width,seed in jobs:
        tag=f"{dataset}_w{width}_seed{seed}";out=RUN/"models"/tag;out.mkdir(parents=True,exist_ok=True)
        args=argparse.Namespace(data=RUN/"data"/dataset,output=out,seed=seed,device="cpu",width=width,
            lr=.001,epochs=2000,batch=128,patience=200,min_delta=1e-7)
        start=perf_counter()
        if not (out/"best_model.pt").exists():
            with (out/"training.log").open("w",encoding="utf-8") as f:
                old=sys.stdout;sys.stdout=f
                try:train(args)
                finally:sys.stdout=old
            dump(out/"run_config.json",dict(**config,dataset=dataset,width=width,seed=seed,training_seconds=perf_counter()-start))
        rows=evaluate(args.data,out/"best_model.pt",out/"evaluation")
        summaries.extend(dict(dataset=dataset,width=width,seed=seed,**r) for r in readcsv(out/"evaluation/aggregate.csv"))
        csvout(RUN/"aggregate.csv",summaries)
        print("FINISHED",tag,perf_counter()-start,flush=True)
        if tag==f"gaussian_1200_w64_seed{SEEDS[0]}":
            global TRAIN_MU,TRAIN_STD,TRAIN_Q
            tx,tq,_=read_data(args.data,"train");TRAIN_MU=tx;TRAIN_STD=tx.std(0)
            TRAIN_Q=np.repeat(topology(12)[0][None],len(tx),axis=0)
            TRAIN_Q[:,topology(12)[3]]+=tq.reshape(len(tx),-1,2)
            cost(args.data,out/"best_model.pt",out/"evaluation")
def readcsv(path):return list(csv.DictReader(path.open(encoding="utf-8-sig")))
if __name__=="__main__":main()
