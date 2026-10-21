"""Untrained-distribution, resolution and external-field evaluation."""
from pathlib import Path
import sys,copy,json
from time import perf_counter
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parents[1]
sys.path.insert(0,str(SOURCE))
sys.path.insert(0,str(SOURCE/'experiments/round4_direct_physical'))
import numpy as np
import torch
from scipy.interpolate import RegularGridInterpolator
from matplotlib.tri import Triangulation,LinearTriInterpolator
from src.common import load_config,write_json,write_csv
from src.network import Predictor
from src.teacher import Problem,solve_state
from src.variational_mesh import WinslowEnergy,edge_matrices
from metrics import geometry,sample_points
from physical import PhysicalEnergy,OPTIONS
CFG=load_config()
for name in ['results','results/meshes','results/histories','文档','图表']:
    (ROOT/name).mkdir(parents=True,exist_ok=True)
torch.set_num_threads(1)
METHODS=['regular','X_mlp','Q_mlp']

def field(points,case,backend=np):
    z=points
    if case['kind']=='gaussian':
        mu=case['mu']
        return backend.exp(-((z[...,0]-mu[0])**2+(z[...,1]-mu[1])**2)/mu[3]**2)
    if case['kind']=='wave':
        d=z[...,1]-.5-.25*backend.sin(2*np.pi*z[...,0]+case['phase'])
        return backend.tanh(-30*d)
    value=0.
    for center,width,amplitude in zip(case['centers'],[.12,.10],[1.,.8]):
        value=value+amplitude*backend.exp(-((z[...,0]-center[0])**2+(z[...,1]-center[1])**2)/width**2)
    return value

def monitor(points,case,backend=np):
    if case['kind']=='constant':return points[...,0]*0+1
    if case['kind']=='gaussian':return 1+case['mu'][2]*field(points,case,backend)
    if case['kind']=='wave':
        d=points[...,1]-.5-.25*backend.sin(2*np.pi*points[...,0]+case['phase'])
        return 1+8*backend.exp(-(d/.10)**2)
    value=1.
    for center,width,strength in zip(case['centers'],[.12,.10],[6.,4.]):
        value=value+strength*backend.exp(-((points[...,0]-center[0])**2+(points[...,1]-center[1])**2)/width**2)
    return value

def monitor_bound(case):
    return 1+case['mu'][2] if case['kind']=='gaussian' else (9 if case['kind']=='wave' else 11)

class MonitorEnergy(PhysicalEnergy):
    def __init__(self,problem,case):
        super().__init__(problem);self.case=case

    def tensor_value(self,x):
        tri=x[self.cells]
        b=torch.stack((tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),dim=-1)
        det=b[:,0,0]*b[:,1,1]-b[:,0,1]*b[:,1,0]
        inv=torch.stack((b[:,1,1],-b[:,0,1],-b[:,1,0],b[:,0,0]),dim=1).reshape(-1,2,2)/det[:,None,None]
        j=self.edges@inv
        m=monitor(tri.mean(1),self.case,torch)
        trace=(j*j).sum(dim=(1,2))/m
        detj=self.det_ref/det
        return (.5*det*m*(trace**2/3+4*(detj/m)**2/3)).sum()

def optimize(problem,initial,energy):
    """Reuse the physical BB/Armijo iteration with an explicit energy object."""
    opt={**OPTIONS,'max_iterations':4000,'max_energy_evaluations':40000}
    start=perf_counter();x=initial.copy();value,g=energy.value_gradient(x)
    evaluations=1;backtracks=0;alpha=.1;history=[];stop='iteration_limit'
    for k in range(opt['max_iterations']+1):
        norm=float(np.linalg.norm(g))
        history.append(dict(iteration=k,energy=value,gradient_norm=norm,
            min_area=problem.valid(x)['min_area'],energy_evaluations=evaluations,backtracks=backtracks))
        if norm<=opt['gradient_tolerance']:stop='converged';break
        if k==opt['max_iterations']:break
        alpha=float(np.clip(alpha,1e-8,1.));accepted=False
        for _ in range(opt['max_backtracks']):
            if evaluations+2>opt['max_energy_evaluations']:stop='energy_budget';break
            candidate=x-alpha*g
            if problem.valid(candidate)['valid']:
                cv=energy.value(candidate);evaluations+=1
                if np.isfinite(cv) and cv<=value-opt['armijo_c1']*alpha*norm**2:
                    cv,cg=energy.value_gradient(candidate);evaluations+=1
                    if np.all(np.isfinite(cg)):accepted=True;break
            alpha*=.5;backtracks+=1
        if not accepted:
            if stop!='energy_budget':stop='line_search_stalled'
            break
        step=(candidate-x).ravel();change=(cg-g).ravel();curvature=float(step@change)
        proposal=float(step@step/curvature) if curvature>0 else .1
        x,value,g=candidate,cv,cg;alpha=proposal
    return dict(X=x,history=history,converged=stop=='converged',stop_reason=stop,
        iterations=history[-1]['iteration'],energy_evaluations=evaluations,backtracks=backtracks,
        initial_energy=history[0]['energy'],final_energy=value,
        final_gradient_norm=float(np.linalg.norm(g)),seconds=perf_counter()-start)

def interpolate_error(x,cells,case,points):
    values=LinearTriInterpolator(Triangulation(x[:,0],x[:,1],cells),field(x,case))(points[:,0],points[:,1])
    assert not np.any(np.ma.getmaskarray(values))
    return float(np.sqrt(np.mean((np.asarray(values)-field(points,case))**2)))

def catalog():
    rng=np.random.default_rng(20261025);cases=[]
    def add(group,mu,n=12,**extra):
        cases.append(dict(iid=f'{group}_{sum(c["group"]==group for c in cases):02d}',
            group=group,kind='gaussian',mu=list(map(float,mu)),n=n,**extra))
    for _ in range(16):
        add('fresh_ID',[rng.uniform(.3,.7),rng.uniform(.3,.7),rng.uniform(2,8),rng.uniform(.18,.30)])
    for _ in range(8):
        mu=[rng.uniform(.3,.7),rng.uniform(.3,.7),rng.uniform(2,8),rng.uniform(.18,.30)]
        axis=int(rng.integers(0,2));mu[axis]=rng.uniform(.12,.27) if rng.random()<.5 else rng.uniform(.73,.88)
        add('OOD_center',mu)
    for _ in range(8):
        add('OOD_narrow',[rng.uniform(.25,.75),rng.uniform(.25,.75),rng.uniform(10,14),rng.uniform(.08,.14)])
    for _ in range(8):
        add('OOD_broad',[rng.uniform(.25,.75),rng.uniform(.25,.75),rng.uniform(.5,1.5),rng.uniform(.34,.42)])
    base=copy.deepcopy(cases[:4])
    for n in [8,16,24]:
        for c in base:add(f'scale_{n}',c['mu'],n=n,parent=c['iid'])
    for phase in [0.,np.pi/4,np.pi/2,3*np.pi/4]:
        cases.append(dict(iid=f'paper_wave_{len([c for c in cases if c["kind"]=="wave"]):02d}',
            group='paper_wave',kind='wave',n=12,mu=[.5,.5,5.,.24],phase=phase,
            input_semantics='fixed Gaussian proxy; network does not encode this field'))
    for centers in [[ [.28,.28],[.72,.72] ],[[.28,.72],[.72,.28]],[[.3,.5],[.7,.5]],[[.5,.3],[.5,.7]]]:
        cases.append(dict(iid=f'double_peak_{len([c for c in cases if c["kind"]=="double"]):02d}',
            group='double_peak',kind='double',n=12,mu=[.5,.5,5.,.24],centers=centers,
            input_semantics='fixed Gaussian proxy; network does not encode this field'))
    return cases

def prediction(p,predictor,case,is_q):
    start=perf_counter();disp=predictor.predict(case['mu'])
    if case['n']!=12:
        base=np.zeros((13,13,2));mask=np.ones((13,13),dtype=bool)
        mask[[0,-1],:]=False;mask[:,[0,-1]]=False;base[mask]=disp
        axis=np.linspace(0,1,13)
        # Stored arrays use row=y, column=x. Query in that order.
        interp=RegularGridInterpolator((axis,axis),base)
        disp=interp(p.reference[:,[1,0]])[~p.boundary]
    raw=p.reference.copy();raw[~p.boundary]+=disp
    valid=p.valid(raw)['valid']
    for k in range(21):
        candidate=p.reference+2.**(-k)*(raw-p.reference)
        if p.valid(candidate)['valid']:
            x=p.physical(candidate) if is_q else candidate
            if p.valid(x)['valid']:break
    else:k=21;x=p.X0.copy()
    return dict(X=x,raw=raw,raw_valid=valid,tau=2.**(-k) if k<=20 else 0.,
                fallback=k==21,generation_seconds=perf_counter()-start,
                adapter='native' if case['n']==12 else 'bilinear reference-displacement interpolation')

def run():
    cases=catalog();write_json(ROOT/'results/cases.json',cases)
    xp=Predictor();qp=Predictor(SOURCE/'experiments/round3/models/q_mlp_20261021.pt')
    points=sample_points(160);np.savez_compressed(ROOT/'results/sampling.npz',points=points)
    rows=[];timings=[];start_all=perf_counter()
    for index,case in enumerate(cases):
        cfg=copy.deepcopy(CFG);cfg['mesh']['n']=case['n']
        p=Problem(case['mu'],cfg)
        m=monitor(p.X0[p.cells].mean(1),case)
        p.metric=m[:,None,None]*np.eye(2);p.energy=WinslowEnergy(p.X0,p.cells,p.metric)
        teacher=solve_state(p)
        den=max(float(np.linalg.norm((teacher['X']-p.X0)[~p.boundary])),1e-14)
        np.savez_compressed(ROOT/f'results/meshes/{case["iid"]}_reference.npz',
            mu=case['mu'],X=teacher['X'],Q=teacher['Q'],cells=p.cells,X0=p.X0)
        write_json(ROOT/f'results/meshes/{case["iid"]}_reference.json',teacher['summary'])
        initial_cache={};first={}
        for repeat in range(3):
            order=METHODS if (index+repeat)%2==0 else METHODS[::-1]
            for method in order:
                started=perf_counter()
                if method=='regular':
                    pred=dict(X=p.X0.copy(),raw_valid=True,tau=1.,fallback=False,generation_seconds=0.,adapter='regular')
                else:
                    pred=prediction(p,xp if method=='X_mlp' else qp,case,method=='Q_mlp')
                energy=MonitorEnergy(p,case);result=optimize(p,pred['X'],energy)
                elapsed=perf_counter()-started
                timings.append(dict(iid=case['iid'],group=case['group'],n=case['n'],method=method,repeat=repeat,
                    online_seconds=elapsed,generation_seconds=pred['generation_seconds'],
                    solve_seconds=result['seconds'],converged=result['converged']))
                if repeat==0:
                    xi,xf=pred['X'],result['X'];inside=~p.boundary
                    initial_cache[method]=xi
                    area_ref=1/(2*case['n']**2)
                    bound=4*area_ref**2/(3*monitor_bound(case)*result['initial_energy'])
                    first[method]=dict(iid=case['iid'],group=case['group'],kind=case['kind'],n=case['n'],
                        method=method,teacher_converged=teacher['summary']['converged'],
                        raw_valid=pred['raw_valid'],tau=pred['tau'],fallback=pred['fallback'],adapter=pred['adapter'],
                        initial_node_error=float(np.linalg.norm((xi-teacher['X'])[inside])/den) if teacher['summary']['converged'] else None,
                        initial_rmse=interpolate_error(xi,p.cells,case,points),
                        final_rmse=interpolate_error(xf,p.cells,case,points),
                        regular_rmse=interpolate_error(p.X0,p.cells,case,points),
                        initial_min_angle=geometry(xi,p.cells)['min_angle'],
                        final_min_angle=geometry(xf,p.cells)['min_angle'],
                        final_valid=p.valid(xf)['valid'],area_lower_bound=bound,
                        minimum_observed_area=min(h['min_area'] for h in result['history']),
                        **{k:result[k] for k in ['converged','stop_reason','iterations','energy_evaluations',
                            'initial_energy','final_energy','final_gradient_norm']})
                    np.savez_compressed(ROOT/f'results/meshes/{case["iid"]}_{method}.npz',
                        X_initial=xi,X_final=xf,cells=p.cells,X0=p.X0)
                    write_csv(ROOT/f'results/histories/{case["iid"]}_{method}.csv',result['history'])
        for method in METHODS:
            seconds=[r['online_seconds'] for r in timings if r['iid']==case['iid'] and r['method']==method]
            first[method].update(online_seconds=float(np.mean(seconds)),repeat_std=float(np.std(seconds,ddof=1)))
            rows.append(first[method])
        write_csv(ROOT/'results/metrics.csv',rows);write_csv(ROOT/'results/timings.csv',timings)
        print(f'{index+1}/{len(cases)} {case["iid"]} '+str({m:(first[m]['converged'],first[m]['iterations'],
             round(first[m]['online_seconds'],3)) for m in METHODS}),flush=True)
    aggregate=[]
    for group in dict.fromkeys(c['group'] for c in cases):
        for method in METHODS:
            sub=[r for r in rows if r['group']==group and r['method']==method]
            row=dict(group=group,method=method,n_cases=len(sub),
                converged=sum(r['converged'] for r in sub),raw_legal=sum(r['raw_valid'] for r in sub),
                teacher_converged=sum(r['teacher_converged'] for r in sub),fallbacks=sum(r['fallback'] for r in sub))
            for key in ['initial_node_error','initial_rmse','final_rmse','regular_rmse','online_seconds','iterations','initial_min_angle']:
                vals=[r[key] for r in sub if r[key] is not None]
                row[key]=float(np.mean(vals)) if vals else None
                row[key+'_std']=float(np.std(vals,ddof=1)) if len(vals)>1 else 0.
            aggregate.append(row)
    write_csv(ROOT/'results/aggregate.csv',aggregate)
    write_json(ROOT/'results/summary.json',dict(groups=aggregate,case_count=len(cases),timed_runs=len(timings),
        repetitions=3,retrained=False,seed=20261025,seconds=perf_counter()-start_all))

if __name__=='__main__':run()
