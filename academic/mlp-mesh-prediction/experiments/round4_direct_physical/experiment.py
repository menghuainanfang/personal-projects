"""Direct physical prediction and matched physical-energy optimization."""
import sys
from time import perf_counter
import numpy as np
from common import *
from physical import solve,OPTIONS
from metrics import measure,sample_points,interpolation_rmse

A_METHODS=['X0','XT','X_raw','X_transferred','Q_physical']
B_METHODS=['physical_regular','physical_mlp']

def generate(p,predictor,q_predictor,method,mu):
    start=perf_counter();t=perf_counter()
    if method=='X_raw':
        x=p.X0.copy();x[~p.boundary]+=predictor.predict(mu)
        inference=perf_counter()-t;t=perf_counter()
        safe,meta=physical_safe(p,x)
        meta['raw_valid']=p.valid(x)['valid']
        return x,safe,dict(inference_seconds=inference,processing_seconds=perf_counter()-t,
                           generation_seconds=perf_counter()-start,**meta)
    if method=='X_transferred':
        displacement=predictor.predict(mu);inference=perf_counter()-t;t=perf_counter()
        s=safe_prediction(p,displacement)
        return s['X'],s['X'],dict(inference_seconds=inference,processing_seconds=perf_counter()-t,
            generation_seconds=perf_counter()-start,tau=s['metadata']['tau'],
            backtracks=s['metadata']['backtracks'],fallback=s['metadata']['fallback'],
            raw_valid=s['metadata']['raw_valid'])
    # Time normalization/forward separately from computational checks and R.
    q=p.reference.copy();q[~p.boundary]+=q_predictor.predict(mu)
    inference=perf_counter()-t;t=perf_counter()
    for k in range(21):
        candidate=p.reference+2.**(-k)*(q-p.reference)
        if p.valid(candidate)['valid']:
            x=p.physical(candidate)
            if p.valid(x)['valid']:break
    else:
        k=21;x=p.X0.copy()
    return x,x,dict(inference_seconds=inference,processing_seconds=perf_counter()-t,
        generation_seconds=perf_counter()-start,tau=2.**(-k) if k<=20 else 0.,
        backtracks=k,fallback=k==21,raw_valid=p.valid(q)['valid'])

def aggregate(rows,group):
    result=[]
    for method in group:
        subset=[r for r in rows if r['split']=='test' and r['method']==method]
        keys=[k for k,v in subset[0].items() if isinstance(v,(float,int)) and not isinstance(v,bool)]
        row=dict(method=method,n=len(subset),valid=sum(r['valid'] for r in subset))
        for k in keys:
            row[k]=float(np.mean([r[k] for r in subset]))
            row[k+'_std']=float(np.std([r[k] for r in subset],ddof=1))
        if 'converged' in subset[0]:row['converged']=sum(r['converged'] for r in subset)
        result.append(row)
    return result

def main():
    xp=Predictor();qp=Predictor(SOURCE/'experiments/round3/models/q_mlp_20261021.pt')
    points=sample_points(160);np.savez_compressed(ROOT/'results/interpolation_points.npz',points=points)
    a_rows=[];b_rows=[];a_times=[];b_times=[];sampling=[]
    for ii,iid in enumerate(IDS):
        d=data(iid);p=Problem(d['mu'],CFG);split='test' if iid in SPLIT['test'] else 'display'
        nodes={'X0':p.X0.copy(),'XT':d['X_teacher'].copy()}
        generated={}
        for repeat in range(3):
            order=['X_raw','X_transferred','Q_physical']
            if (ii+repeat)%2:order=order[::-1]
            for method in order:
                x,safe,meta=generate(p,xp,qp,method,d['mu'])
                a_times.append(dict(iid=iid,split=split,repeat=repeat,method=method,**meta))
                if repeat==0:
                    nodes[method]=x;generated[method]=meta
                    if method=='X_raw' and not meta['raw_valid']:nodes['X_safe']=safe
        for method,x in nodes.items():
            if not p.valid(x)['valid']:
                raise ValueError(f'{iid} {method} invalid raw prediction; inspect saved physical safety metadata')
            stats=measure(p,x,d['X_teacher'],points)
            a_rows.append(dict(iid=iid,split=split,method=method,**stats))
        np.savez_compressed(ROOT/f'results/meshes/{iid}_A.npz',mu=d['mu'],cells=p.cells,boundary=p.boundary,**nodes)
        first={}
        for repeat in range(3):
            order=B_METHODS if (ii+repeat)%2==0 else B_METHODS[::-1]
            for method in order:
                start=perf_counter()
                inference=safety=0.
                if method=='physical_mlp':
                    t=perf_counter();raw=p.X0.copy();raw[~p.boundary]+=xp.predict(d['mu'])
                    inference=perf_counter()-t;t=perf_counter()
                    initial,meta=physical_safe(p,raw);safety=perf_counter()-t
                else:
                    initial=p.X0.copy();meta=dict(tau=1.,backtracks=0,fallback=False)
                result=solve(p,initial)
                elapsed=perf_counter()-start
                b_times.append(dict(iid=iid,split=split,repeat=repeat,method=method,online_seconds=elapsed,
                    inference_seconds=inference,safety_seconds=safety,solve_seconds=result['summary']['seconds'],
                    converged=result['summary']['converged']))
                if repeat==0:
                    first[method]=dict(iid=iid,split=split,method=method,**result['summary'],
                        **measure(p,result['X'],d['X_teacher'],points),tau=meta['tau'],fallback=meta['fallback'])
                    save=dict(mu=d['mu'],cells=p.cells,boundary=p.boundary,X_initial=initial,X_final=result['X'])
                    np.savez_compressed(ROOT/f'results/meshes/{iid}_{method}.npz',**save)
                    write_csv(ROOT/f'results/histories/{iid}_{method}.csv',result['history'])
        for method in B_METHODS:
            times=[r['online_seconds'] for r in b_times if r['iid']==iid and r['method']==method]
            first[method].update(online_seconds=float(np.mean(times)),repeat_std=float(np.std(times,ddof=1)))
            b_rows.append(first[method])
        if split=='display':
            for method,x in nodes.items():
                low=interpolation_rmse(x,p.cells,p.mu,points)
                high=interpolation_rmse(x,p.cells,p.mu,sample_points(320))
                sampling.append(dict(iid=iid,method=method,rmse_160=low,rmse_320=high,
                                     relative_change=abs(high-low)/high))
        write_csv(ROOT/'results/A_metrics.csv',a_rows);write_csv(ROOT/'results/A_timings.csv',a_times)
        write_csv(ROOT/'results/B_metrics.csv',b_rows);write_csv(ROOT/'results/B_timings.csv',b_times)
        print(f'{ii+1}/{len(IDS)} {iid}: '+str({m:(first[m]['iterations'],round(first[m]['online_seconds'],4),first[m]['converged']) for m in B_METHODS}),flush=True)
    aa=aggregate(a_rows,A_METHODS);bb=aggregate(b_rows,B_METHODS)
    timing_summary=[]
    for method in ['X_raw','X_transferred','Q_physical']:
        subset=[r for r in a_times if r['split']=='test' and r['method']==method]
        timing_summary.append(dict(method=method,**{k:float(np.mean([r[k] for r in subset]))
            for k in ['inference_seconds','processing_seconds','generation_seconds']}))
    summary=dict(A=aa,B=bb,A_timing=timing_summary,physical_options=OPTIONS,
                 sampling_max_relative_change=max(r['relative_change'] for r in sampling),
                 test_instances=len(SPLIT['test']),display_instances=3)
    write_json(ROOT/'results/summary.json',summary)
    write_csv(ROOT/'results/A_aggregate.csv',aa);write_csv(ROOT/'results/B_aggregate.csv',bb)
    write_csv(ROOT/'results/sampling_check.csv',sampling)
    write_json(ROOT/'results/run_config.json',dict(source_config=CFG,physical_options=OPTIONS,
        test_ids=IDS,models=['models/mlp.pt','experiments/round3/models/q_mlp_20261021.pt'],
        sampling='160x160 identical midpoint points, 320x320 check on display cases',
        timing='preloaded models and fixed-topology problem context; no disk IO or error evaluation'))
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
