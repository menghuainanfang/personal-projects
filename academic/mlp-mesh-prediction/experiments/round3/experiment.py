"""Coordinate diagnostics and paired comparisons on the saved teacher dataset."""
from pathlib import Path
import sys, json, csv, random, copy
from time import perf_counter
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]
sys.path.insert(0,str(SOURCE))
import numpy as np
import torch
from src.common import load_config
from src.teacher import Problem,solve_state
from src.network import Predictor,MeshMLP
from safe_prediction import safe_prediction

CFG=load_config()
SPLIT=json.loads((SOURCE/'data/split.json').read_text(encoding='utf-8'))
IDS=SPLIT['test']+['case_center','case_shifted','case_strength']
for folder in ['results','models','paper','presentation']:
    (ROOT/folder).mkdir(parents=True,exist_ok=True)

def save_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def save_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def data(iid):
    with np.load(SOURCE/f'data/teacher/{iid}.npz') as d:
        return {k:d[k].copy() for k in d.files}

def err(a,b,den,inside):
    return float(np.linalg.norm((a-b)[inside])/den)

def diagnose():
    predictor=Predictor()
    rows=[]
    for iid in IDS:
        d=data(iid);p=Problem(d['mu'],CFG);inside=~p.boundary
        den=float(np.linalg.norm((d['X_teacher']-p.X0)[inside]))
        qden=float(np.linalg.norm((d['Q_teacher']-p.reference)[inside]))
        cycleq=p.physical_to_state(d['X_teacher']);cycle=p.physical(cycleq)
        s=safe_prediction(p,predictor.predict(d['mu']))
        raw=s['raw'];damped=s['damped'];aligned=s['X']
        a=(damped-d['X_teacher'])[inside].ravel()/den
        b=(aligned-damped)[inside].ravel()/den
        rows.append(dict(iid=iid,split='test' if iid in SPLIT['test'] else 'display',
            teacher_cycle_error=err(cycle,d['X_teacher'],den,inside),
            teacher_q_cycle_error=err(cycleq,d['Q_teacher'],qden,inside),
            teacher_energy=p.energy.value_gradient(d['Q_teacher'])[0],
            cycle_energy=p.energy.value_gradient(cycleq)[0],
            teacher_cycle_valid=p.valid(cycle)['valid'] and p.valid(cycleq)['valid'],
            raw_error=err(raw,d['X_teacher'],den,inside),
            damped_error=err(damped,d['X_teacher'],den,inside),
            aligned_error=err(aligned,d['X_teacher'],den,inside),
            damping_change=err(damped,raw,den,inside),
            transfer_change=err(aligned,damped,den,inside),
            old_transfer_denominator=s['metadata']['transfer_relative_change'],
            cross_term=float(2*np.dot(a,b)),tau=s['metadata']['tau'],
            decomposition_residual=float(abs(np.dot(a+b,a+b)-np.dot(a,a)-np.dot(b,b)-2*np.dot(a,b)))))
    save_csv(ROOT/'results/diagnosis.csv',rows)
    test=[r for r in rows if r['split']=='test']
    summary={k:float(np.mean([r[k] for r in test])) for k in rows[0] if isinstance(rows[0][k],(float,int))}
    save_json(ROOT/'results/diagnosis_summary.json',summary)
    print('Diagnosis:',summary,flush=True)

def train(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    def samples(ids):
        ds=[data(i) for i in ids]
        return np.array([d['mu'] for d in ds]),np.array([(d['Q_teacher']-d['X0'])[~d['boundary_mask']].ravel() for d in ds])
    tx,ty=samples(SPLIT['train']);vx,vy=samples(SPLIT['validation'])
    mean,std=tx.mean(0),tx.std(0);scale=float(np.sqrt(np.mean(ty**2)))
    x=torch.tensor((tx-mean)/std,dtype=torch.float32);y=torch.tensor(ty/scale,dtype=torch.float32)
    v=torch.tensor((vx-mean)/std,dtype=torch.float32);target=torch.tensor(vy/scale,dtype=torch.float32)
    opt=CFG['model'];model=MeshMLP(y.shape[1],opt['hidden'])
    optimizer=torch.optim.Adam(model.parameters(),lr=opt['learning_rate'],weight_decay=opt['weight_decay'])
    best=float('inf');wait=0;history=[];start=perf_counter()
    for epoch in range(1,opt['max_epochs']+1):
        model.train();order=torch.randperm(len(x))
        for begin in range(0,len(x),opt['batch_size']):
            ix=order[begin:begin+opt['batch_size']]
            optimizer.zero_grad();loss=((model(x[ix])-y[ix])**2).mean();loss.backward();optimizer.step()
        model.eval()
        with torch.inference_mode():
            tl=float(((model(x)-y)**2).mean());vl=float(((model(v)-target)**2).mean())
        history.append(dict(epoch=epoch,train_mse=tl,validation_mse=vl))
        if vl<best-opt['min_delta']:
            best=vl;wait=0;best_epoch=epoch;state=copy.deepcopy(model.state_dict())
        else:wait+=1
        if wait>=opt['early_stopping_patience']:break
    package=dict(state_dict=state,input_mean=mean.tolist(),input_std=std.tolist(),displacement_scale=scale,
        output_size=ty.shape[1],hidden=opt['hidden'],threads=1,best_epoch=best_epoch,seed=seed,
        train_ids=SPLIT['train'],validation_ids=SPLIT['validation'],target='Q_teacher - Q0')
    torch.save(package,ROOT/f'models/q_mlp_{seed}.pt')
    summary=dict(seed=seed,epochs=epoch,best_epoch=best_epoch,validation_normalized_mse=best,
        validation_coordinate_mse=best*scale**2,training_seconds=perf_counter()-start,
        training_instances=len(tx),validation_instances=len(vx),parameters=sum(p.numel() for p in model.parameters()))
    save_json(ROOT/f'models/training_{seed}.json',summary)
    save_csv(ROOT/f'results/train_{seed}.csv',history)
    print('Trained:',summary,flush=True)

def q_safe(p,raw):
    inside=~p.boundary
    raw=raw.copy();raw[p.boundary]=p.reference[p.boundary]
    for k in range(CFG['prediction']['max_displacement_backtracks']+1):
        tau=2.**(-k);q=p.reference.copy();q[inside]+=tau*(raw-p.reference)[inside]
        if not p.valid(q)['valid']:continue
        x=p.physical(q)
        if p.valid(x)['valid']:
            return dict(Q=q,X=x,tau=tau,fallback=False,raw_valid=p.valid(raw)['valid'])
    return dict(Q=p.reference.copy(),X=p.X0.copy(),tau=0.,fallback=True,raw_valid=p.valid(raw)['valid'])

def warm_solve(p):
    """Armijo with the previous accepted step, bounded by the original step."""
    from src.geometry import signed_triangle_areas
    settings=p.config['teacher'];q=p.reference.copy();x=p.physical(q)
    value,g=p.energy.value_gradient(q);g[p.boundary]=0
    evaluations=1;backtracks=0;illegal=0;alpha_previous=settings['alpha0'];history=[]
    start=perf_counter();stop='iteration_limit'
    for k in range(settings['max_iterations']+1):
        norm=float(np.linalg.norm(g))
        history.append(dict(iteration=k,energy=value,gradient_norm=norm,energy_evaluations=evaluations,
                            backtracks=backtracks,alpha=alpha_previous))
        if norm<=settings['gradient_tolerance']:stop='converged';break
        if k==settings['max_iterations']:break
        alpha=min(settings['alpha0'],max(1e-12,alpha_previous));accepted=False
        for attempt in range(settings['max_backtracks']):
            if evaluations>=settings['max_energy_evaluations']:stop='energy_budget';break
            candidate=q-alpha*g
            if np.all(signed_triangle_areas(candidate,p.cells)>p.epsilon):
                cv,cg=p.energy.value_gradient(candidate);evaluations+=1
                if np.isfinite(cv) and np.all(np.isfinite(cg)) and cv<=value-settings['armijo_c1']*alpha*norm**2:
                    cx=p.physical(candidate)
                    if p.valid(cx)['valid']:accepted=True;break
                    illegal+=1
            else:illegal+=1
            backtracks+=1;alpha*=settings['beta']
            if alpha<1e-12:alpha=float(settings['alpha0'])
        if not accepted:
            if stop!='energy_budget':stop='line_search_stalled'
            break
        q,x,value,g=candidate,cx,cv,cg;g[p.boundary]=0;alpha_previous=alpha
    return dict(Q=q,X=x,history=history,summary=dict(converged=stop=='converged',stop_reason=stop,
        iterations=history[-1]['iteration'],energy_evaluations=evaluations,backtracks=backtracks,
        illegal_candidates=illegal,initial_energy=history[0]['energy'],final_energy=value,
        final_gradient_norm=float(np.linalg.norm(g)),seconds=perf_counter()-start))

METHODS=['B0','B1','B2','B3','B4']

def evaluate():
    xp=Predictor();qp=Predictor(ROOT/f"models/q_mlp_{CFG['seed']}.pt")
    qp2=Predictor(ROOT/f"models/q_mlp_{CFG['seed']+1}.pt")
    train=[data(i) for i in SPLIT['train']]
    mu=np.array([d['mu'] for d in train]);mean=mu.mean(0);std=mu.std(0)
    rows=[];timings=[];seed_rows=[]
    (ROOT/'results/meshes').mkdir(exist_ok=True);(ROOT/'results/histories').mkdir(exist_ok=True)
    for ii,iid in enumerate(IDS):
        d=data(iid);inside=~d['boundary_mask'];den=float(np.linalg.norm((d['X_teacher']-d['X0'])[inside]))
        first={};seconds={m:[] for m in METHODS}
        nearest=int(np.argmin(np.sum(((mu-d['mu'])/std)**2,axis=1)))
        neighbor=SPLIT['train'][nearest]
        for repeat in range(3):
            order=METHODS if (ii+repeat)%2==0 else METHODS[::-1]
            for method in order:
                start=perf_counter();p=Problem(d['mu'],CFG)
                inference=0.;safety=0.;tau=1.;fallback=False;rawvalid=True
                if method in ['B0','B4']:
                    initialq=p.reference.copy();initialx=p.X0.copy()
                elif method=='B1':
                    t=perf_counter();disp=xp.predict(d['mu']);inference=perf_counter()-t
                    t=perf_counter();s=safe_prediction(p,disp);safety=perf_counter()-t
                    initialq,initialx=s['Q'],s['X'];tau=s['metadata']['tau'];fallback=s['metadata']['fallback'];rawvalid=s['metadata']['raw_valid']
                else:
                    t=perf_counter()
                    if method=='B2':
                        raw=p.reference.copy();raw[inside]+=qp.predict(d['mu'])
                    else:
                        j=int(np.argmin(np.sum(((mu-d['mu'])/std)**2,axis=1)))
                        raw=train[j]['Q_teacher'].copy()
                    inference=perf_counter()-t;t=perf_counter();s=q_safe(p,raw);safety=perf_counter()-t
                    initialq,initialx=s['Q'],s['X'];tau=s['tau'];fallback=s['fallback'];rawvalid=s['raw_valid']
                generation=perf_counter()-start
                result=warm_solve(p) if method=='B4' else solve_state(p,initialq)
                elapsed=perf_counter()-start;seconds[method].append(elapsed)
                timings.append(dict(iid=iid,split='test' if iid in SPLIT['test'] else 'display',repeat=repeat,
                    method=method,order=order.index(method),online_seconds=elapsed,
                    generation_seconds=generation,inference_seconds=inference,safety_seconds=safety,
                    solve_seconds=result['summary']['seconds'],converged=result['summary']['converged']))
                if repeat==0:
                    energy=p.energy.value_gradient(initialq)[0];et=p.energy.value_gradient(d['Q_teacher'])[0]
                    first[method]=dict(iid=iid,split='test' if iid in SPLIT['test'] else 'display',method=method,
                        initial_error=err(initialx,d['X_teacher'],den,inside),
                        final_error=err(result['X'],d['X_teacher'],den,inside),
                        initial_energy_gap=(energy-et)/abs(et),final_energy_gap=(result['summary']['final_energy']-et)/abs(et),
                        initial_min_area=p.valid(initialx)['min_area'],final_min_area=p.valid(result['X'])['min_area'],
                        initial_valid=p.valid(initialq)['valid'] and p.valid(initialx)['valid'],
                        final_valid=p.valid(result['Q'])['valid'] and p.valid(result['X'])['valid'],
                        tau=tau,fallback=fallback,raw_valid=rawvalid,neighbor=neighbor if method=='B3' else '',
                        **{k:result['summary'][k] for k in ['converged','stop_reason','iterations','energy_evaluations','backtracks','final_gradient_norm']})
                    np.savez_compressed(ROOT/f'results/meshes/{iid}_{method}.npz',mu=d['mu'],X0=p.X0,
                        X_teacher=d['X_teacher'],Q_teacher=d['Q_teacher'],Q_initial=initialq,X_initial=initialx,
                        Q_final=result['Q'],X_final=result['X'],cells=p.cells,boundary=p.boundary)
                    save_csv(ROOT/f'results/histories/{iid}_{method}.csv',result['history'])
                    if method=='B0':assert np.allclose(result['Q'],d['Q_teacher'],atol=1e-12,rtol=0)
        for m in METHODS:
            first[m].update(online_seconds=float(np.mean(seconds[m])),repeat_std=float(np.std(seconds[m],ddof=1)))
            rows.append(first[m])
        p=Problem(d['mu'],CFG)
        for seed,predictor in [(CFG['seed'],qp),(CFG['seed']+1,qp2)]:
            raw=p.reference.copy();raw[inside]+=predictor.predict(d['mu']);s=q_safe(p,raw)
            seed_rows.append(dict(iid=iid,split='test' if iid in SPLIT['test'] else 'display',seed=seed,
                physical_error=err(s['X'],d['X_teacher'],den,inside),q_error=err(s['Q'],d['Q_teacher'],
                float(np.linalg.norm((d['Q_teacher']-p.reference)[inside])),inside),tau=s['tau']))
        save_csv(ROOT/'results/metrics.csv',rows);save_csv(ROOT/'results/timings.csv',timings)
        save_csv(ROOT/'results/seeds.csv',seed_rows)
        print(f"Evaluated {ii+1}/{len(IDS)} {iid} "+str({m:round(first[m]['online_seconds'],3) for m in METHODS}),flush=True)
    aggregate=[]
    for m in METHODS:
        group=[r for r in rows if r['split']=='test' and r['method']==m]
        a=dict(method=m,n=len(group),converged=sum(r['converged'] for r in group))
        for k in ['initial_error','final_error','initial_energy_gap','final_energy_gap','online_seconds','iterations',
                  'energy_evaluations','backtracks','final_gradient_norm','initial_min_area']:
            a[k]=float(np.mean([r[k] for r in group]))
            a[k+'_std']=float(np.std([r[k] for r in group],ddof=1))
        a['speedup']=1. if m=='B0' else aggregate[0]['online_seconds']/a['online_seconds']
        aggregate.append(a)
    save_csv(ROOT/'results/aggregate.csv',aggregate)
    save_json(ROOT/'results/aggregate.json',aggregate)
    print(json.dumps(aggregate,indent=2),flush=True)

if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'all'
    if action in ['diagnose','all']:diagnose()
    if action in ['train','all']:
        for seed in [CFG['seed'],CFG['seed']+1]:train(seed)
    if action in ['evaluate','all']:evaluate()
