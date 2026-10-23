"""Evaluate n=12 single-Gaussian Q predictor against held-out teacher geometry.

Reports direct sparse reference runtime separately from prediction runtime. A
sparse reference is not an equivalent task to approximate inference unless
same-quality output is required, so do not call timing ratio a speedup without
quality constraints.
"""
import argparse, csv, json, pathlib
from time import perf_counter
import numpy as np
import torch
from matplotlib.tri import Triangulation, LinearTriInterpolator
from teacher_general import topology, signed_areas, make_teacher
from train_fixed_q import FixedMLP, read_data


def reconstruct(q,x0,cells,boundary):
    if signed_areas(q,cells).min()<=1e-10:return None
    tr=Triangulation(q[:,0],q[:,1],cells)
    coords=[]
    for axis in (0,1):
        values=LinearTriInterpolator(tr,x0[:,axis])(x0[:,0],x0[:,1])
        if np.ma.getmaskarray(values).any():return None
        coords.append(np.asarray(values))
    x=np.column_stack(coords);x[boundary]=x0[boundary]
    return x if signed_areas(x,cells).min()>1e-10 and np.all((x>=-1e-12)&(x<=1+1e-12)) else None


def run(args):
    root=args.data.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    ckpt=torch.load(args.model.resolve(),map_location='cpu',weights_only=True)
    model=FixedMLP(ckpt['output_dim'],ckpt['width'])
    model.load_state_dict(ckpt['state_dict']);model.eval()
    mu,qref,xref=read_data(root,'test')
    x0,cells,boundary,inside,*_=topology(12)
    rows=[]
    for j,p in enumerate(mu):
        start=perf_counter()
        vec=(p-np.array(ckpt['input_mean']))/np.array(ckpt['input_std'])
        with torch.inference_mode():
            disp=model(torch.tensor(vec,dtype=torch.float32).reshape(1,4)).numpy().reshape(-1,2)*ckpt['label_scale']
        q=x0.copy();q[inside]+=disp
        raw_valid=reconstruct(q,x0,cells,boundary) is not None
        t=1.;safe=reconstruct(q,x0,cells,boundary)
        for attempt in range(22):
            if safe is not None:break
            t*=.5;q=x0.copy();q[inside]+=t*disp;safe=reconstruct(q,x0,cells,boundary)
        if safe is None:safe=x0.copy();t=0
        predict_seconds=perf_counter()-start
        teacher=x0.copy();teacher[inside]+=xref[j].reshape(-1,2)
        denom=max(float(np.linalg.norm((teacher-x0)[inside])),1e-14)
        e=float(np.linalg.norm((safe-teacher)[inside])/denom)
        rmse=float(np.sqrt(np.mean((safe[inside]-teacher[inside])**2)))
        sparse_start=perf_counter();teacher_exact=make_teacher(12,{'kind':'single','mu':p.tolist()});sparse_seconds=perf_counter()-sparse_start
        if np.linalg.norm(teacher_exact['Q'][inside]-x0[inside]-qref[j].reshape(-1,2))>1e-10:
            raise RuntimeError('saved teacher mismatch')
        rows.append(dict(instance=j,error_relative=e,coord_rmse=rmse,raw_valid=raw_valid,
                         fallback=t==0,damping_tau=t,predict_seconds=predict_seconds,
                         sparse_reference_seconds=sparse_seconds,min_area=signed_areas(safe,cells).min()))
    with (out/'metrics_per_case.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    summary={'n_test':len(rows),'mean_relative_error':float(np.mean([r['error_relative'] for r in rows])),
             'median_relative_error':float(np.median([r['error_relative'] for r in rows])),
             'mean_absolute_coord_rmse':float(np.mean([r['coord_rmse'] for r in rows])),
             'raw_legal_rate':float(np.mean([r['raw_valid'] for r in rows])),
             'safe_legal_rate':1.,'fallback_count':sum(r['fallback'] for r in rows),
             'mean_predict_seconds':float(np.mean([r['predict_seconds'] for r in rows])),
             'mean_sparse_reference_seconds':float(np.mean([r['sparse_reference_seconds'] for r in rows])),
             'warning':'Wall-clock noisy; not a same-precision speedup; no physical refinement performed.'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=pathlib.Path,required=True)
    p.add_argument('--model',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    run(p.parse_args())
