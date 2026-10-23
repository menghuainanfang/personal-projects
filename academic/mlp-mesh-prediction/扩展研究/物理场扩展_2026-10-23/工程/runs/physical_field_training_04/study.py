"""Field-conditioned physical mesh supervision with held-out field instances."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:
    os.environ[key]='1'
import sys,json,csv,time,argparse
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import torch
from torch import nn
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'runs/physical_fields_03'))
import run as physics
torch.set_num_threads(1)
KINDS=['single','double','ring','wave']
GRID=np.stack(np.meshgrid(np.linspace(0,1,32),np.linspace(0,1,32)),axis=-1).reshape(-1,2)
CONFIG=dict(seed=20261026,train_per_kind=48,validation_per_kind=12,test_per_kind=12,
    train_n=[12],test_n=[12,24],workers=4,epochs=1200,patience=150,
    steps_per_epoch=8,batch_queries=1024,learning_rate=.001,
    input='32x32 log(m) and reference query coordinates',
    labels='X-X0 from direct physical Huang energy optimization',
    boundary='16*x*(1-x)*y*(1-y) envelope',
    training_loss='training-scaled displacement MSE',
    refinement_subset='first two test instances per kind, at n12 and n24',
    teacher_tolerance=1e-5,device='cpu',threads=1)


def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')


def csvout(path,rows):
    if rows:
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)


def sample(kind,rng):
    if kind in ('single','double'):
        peaks=[]
        for j in range(1 if kind=='single' else 2):
            cx=rng.uniform(.25,.75) if kind=='single' else rng.uniform(.22,.42)+.36*j
            peaks.append([float(cx),float(rng.uniform(.3,.7)),float(rng.uniform(3,9)),float(rng.uniform(.12,.23))])
        return dict(kind=kind,peaks=peaks)
    if kind=='ring':
        return dict(kind=kind,center=rng.uniform(.43,.57,2).tolist(),
                    radius=float(rng.uniform(.18,.29)),strength=float(rng.uniform(4,10)))
    return dict(kind=kind,phase=float(rng.uniform(-.7,.7)),strength=float(rng.uniform(4,10)))


def feature(spec):
    return np.log(physics.field(torch.tensor(GRID,dtype=torch.float64),spec)[1].numpy()).astype('float32')


def teacher(record):
    path=OUT/record['path']
    status_path=path.with_suffix('.json')
    if status_path.exists():
        return json.loads(status_path.read_text(encoding='utf8'))
    problem=physics.Problem(record['n'],record['spec'])
    result=physics.physical_lbfgs(problem,problem.reference,physics.FieldEnergy)
    status=dict(id=record['id'],split=record['split'],n=record['n'],kind=record['spec']['kind'],
                **result['summary'])
    if status['converged']:
        if not problem.valid(result['X'])['valid']:
            raise RuntimeError('Teacher has invalid geometry')
        np.savez_compressed(path,X=result['X'],X0=problem.reference,
                            log_m=feature(record['spec']))
    dump(status_path,status)
    return status


def prepare():
    (OUT/'teachers').mkdir(exist_ok=True)
    dump(OUT/'config.json',CONFIG)
    manifest=[]
    for si,split in enumerate(['train','validation','test']):
        for ki,kind in enumerate(KINDS):
            rng=np.random.default_rng(CONFIG['seed']+1000*si+100*ki)
            for index in range(CONFIG[split+'_per_kind']):
                spec=sample(kind,rng)
                uid=f'{split}_{kind}_{index:03d}'
                for n in (CONFIG['test_n'] if split=='test' else CONFIG['train_n']):
                    manifest.append(dict(id=uid,index=index,split=split,n=n,spec=spec,
                                         path=f'teachers/{uid}_n{n}.npz'))
    # Field instances, rather than mesh versions, define the split.
    fields={split:{json.dumps(r['spec'],sort_keys=True) for r in manifest if r['split']==split}
            for split in ['train','validation','test']}
    if fields['train'] & (fields['validation']|fields['test']) or fields['validation'] & fields['test']:
        raise RuntimeError('Field instances overlap between splits')
    dump(OUT/'manifest.json',manifest)
    statuses=[]
    with ProcessPoolExecutor(max_workers=CONFIG['workers']) as pool:
        for i,status in enumerate(pool.map(teacher,manifest,chunksize=1)):
            statuses.append(status)
            if (i+1)%24==0:
                print('TEACHERS',i+1,'/',len(manifest),'failed',sum(not r['converged'] for r in statuses),flush=True)
    csvout(OUT/'teacher_status.csv',statuses)
    dump(OUT/'preparation.json',dict(requested=len(manifest),converged=sum(r['converged'] for r in statuses)))


class FieldNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder=nn.Sequential(nn.Linear(1024,128),nn.Tanh(),nn.Linear(128,64),nn.Tanh())
        self.decoder=nn.Sequential(nn.Linear(66,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh(),nn.Linear(128,2))
    def forward(self,fields,coordinates,owner):
        code=self.encoder(fields)[owner]
        x,y=coordinates[:,0:1],coordinates[:,1:2]
        return self.decoder(torch.cat([code,coordinates],dim=1))*(16*x*(1-x)*y*(1-y))


def data(split):
    records=[r for r in json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
             if r['split']==split and (OUT/r['path']).exists()]
    fields=[];coords=[];labels=[];owners=[]
    for i,r in enumerate(records):
        d=np.load(OUT/r['path'])
        problem=physics.Problem(r['n'],r['spec'])
        interior=~problem.boundary
        fields.append(d['log_m']);coords.append(d['X0'][interior])
        labels.append((d['X']-d['X0'])[interior])
        owners.extend([i]*int(interior.sum()))
    return np.stack(fields),np.vstack(coords).astype('float32'),np.vstack(labels).astype('float32'),np.array(owners)


def train():
    torch.manual_seed(CONFIG['seed'])
    rng=np.random.default_rng(CONFIG['seed'])
    tr,va=data('train'),data('validation')
    mean=tr[0].mean(0);std=np.maximum(tr[0].std(0),.05)
    scale=float(np.sqrt(np.mean(tr[2]**2)))
    def tensors(d):
        return (torch.tensor((d[0]-mean)/std),torch.tensor(d[1]),
                torch.tensor(d[2]/scale),torch.tensor(d[3]))
    f,c,y,o=tensors(tr);vf,vc,vy,vo=tensors(va)
    net=FieldNet()
    optimizer=torch.optim.Adam(net.parameters(),lr=CONFIG['learning_rate'],weight_decay=1e-6)
    best=float('inf');stale=0;history=[];started=time.perf_counter()
    for epoch in range(CONFIG['epochs']):
        net.train();losses=[]
        for _ in range(CONFIG['steps_per_epoch']):
            idx=torch.tensor(rng.integers(0,len(c),CONFIG['batch_queries']))
            optimizer.zero_grad()
            loss=((net(f,c[idx],o[idx])-y[idx])**2).mean()
            loss.backward();optimizer.step();losses.append(float(loss.detach()))
        net.eval()
        with torch.inference_mode():
            validation=float(((net(vf,vc,vo)-vy)**2).mean())
        history.append(dict(epoch=epoch+1,train_mse=float(np.mean(losses)),validation_mse=validation))
        if validation<best-1e-6:
            best=validation;stale=0
            torch.save(dict(state_dict=net.state_dict(),mean=torch.tensor(mean),std=torch.tensor(std),
                scale=scale,epoch=epoch+1,validation_mse=validation),OUT/'model.pt')
        else:
            stale+=1
        if (epoch+1)%100==0:
            print('EPOCH',epoch+1,'validation',validation,flush=True)
        if stale>=CONFIG['patience']:
            break
    csvout(OUT/'training_log.csv',history)
    dump(OUT/'training_summary.json',dict(train_fields=len(tr[0]),validation_fields=len(va[0]),
        epochs=len(history),best_validation=best,seconds=time.perf_counter()-started,
        parameters=sum(p.numel() for p in net.parameters()),seed=CONFIG['seed']))
    plt.figure(figsize=(6,4))
    plt.semilogy([r['train_mse'] for r in history],label='train')
    plt.semilogy([r['validation_mse'] for r in history],label='validation')
    plt.xlabel('Epoch');plt.ylabel('Scaled displacement MSE');plt.legend();plt.tight_layout()
    plt.savefig(OUT/'training_curve.png',dpi=150);plt.close()


def predict(net,ck,record):
    problem=physics.Problem(record['n'],record['spec'])
    sampled=torch.tensor(feature(record['spec']))
    f=((sampled-ck['mean'])/ck['std'])[None]
    with torch.inference_mode():
        disp=net(f,torch.tensor(problem.reference,dtype=torch.float32),
                 torch.zeros(len(problem.reference),dtype=torch.long)).numpy()*ck['scale']
    raw=problem.reference+disp
    raw_valid=problem.valid(raw)['valid']
    safe=raw.copy();tau=1.
    for _ in range(21):
        if problem.valid(safe)['valid']:
            break
        tau*=.5;safe=problem.reference+tau*disp
    if not problem.valid(safe)['valid']:
        safe=problem.reference.copy();tau=0.
    return raw,safe,raw_valid,tau


def pde_error(problem,x):
    uh,residual=physics.poisson(x,problem.cells,problem.boundary,problem.spec)
    if residual>1e-9:
        raise RuntimeError('Poisson residual exceeded tolerance')
    return physics.l2_error(x,problem.cells,uh,problem.spec)


def evaluate():
    ck=torch.load(OUT/'model.pt',map_location='cpu',weights_only=True)
    net=FieldNet();net.load_state_dict(ck['state_dict']);net.eval()
    records=[r for r in json.loads((OUT/'manifest.json').read_text(encoding='utf8')) if r['split']=='test']
    rows=[];refinements=[]
    (OUT/'predictions').mkdir(exist_ok=True)
    for i,r in enumerate(records):
        problem=physics.Problem(r['n'],r['spec'])
        started=time.perf_counter()
        raw,safe,raw_valid,tau=predict(net,ck,r)
        prediction_seconds=time.perf_counter()-started
        regular_error=pde_error(problem,problem.reference)
        prediction_error=pde_error(problem,safe)
        teacher_path=OUT/r['path']
        if teacher_path.exists():
            teacher_x=np.load(teacher_path)['X']
            teacher_error=pde_error(problem,teacher_x)
            relative=float(np.linalg.norm(safe-teacher_x)/np.linalg.norm(teacher_x-problem.reference))
        else:
            teacher_x=np.full_like(safe,np.nan)
            teacher_error=relative=float('nan')
        row=dict(id=r['id'],kind=r['spec']['kind'],n=r['n'],teacher_available=teacher_path.exists(),
            raw_valid=raw_valid,tau=tau,relative_teacher_error=relative,
            raw_min_area=float(physics.signed_areas(raw,problem.cells).min()),
            safe_min_area=problem.valid(safe)['min_area'],prediction_seconds=prediction_seconds,
            uniform_l2=regular_error,prediction_l2=prediction_error,teacher_l2=teacher_error,
            prediction_ratio=prediction_error/regular_error,teacher_ratio=teacher_error/regular_error)
        rows.append(row)
        np.savez_compressed(OUT/'predictions'/f"{r['id']}_n{r['n']}.npz",
                            raw=raw,safe=safe,teacher=teacher_x)
        # Fixed subset selected by manifest index, independent of predictions.
        if r['index']<2:
            for method in ['regular','network']:
                started=time.perf_counter()
                initial=(predict(net,ck,r)[1] if method=='network' else problem.reference.copy())
                result=physics.physical_lbfgs(problem,initial,physics.FieldEnergy)
                elapsed=time.perf_counter()-started
                err=pde_error(problem,result['X'])
                refinements.append(dict(id=r['id'],kind=r['spec']['kind'],n=r['n'],method=method,
                    online_seconds=elapsed,**result['summary'],pde_l2=err,pde_ratio=err/regular_error))
            csvout(OUT/'refinements.csv',refinements)
        csvout(OUT/'test_results.csv',rows)
        if (i+1)%8==0:
            print('TESTED',i+1,'/',len(records),flush=True)
    summary=[]
    for kind in KINDS:
        for n in CONFIG['test_n']:
            group=[r for r in rows if r['kind']==kind and r['n']==n]
            summary.append(dict(kind=kind,n=n,cases=len(group),raw_valid=sum(r['raw_valid'] for r in group),
                repaired=sum(r['tau']<1 for r in group),teacher_failures=sum(not r['teacher_available'] for r in group),
                relative_teacher_error=float(np.nanmean([r['relative_teacher_error'] for r in group])),
                prediction_ratio=float(np.mean([r['prediction_ratio'] for r in group])),
                teacher_ratio=float(np.nanmean([r['teacher_ratio'] for r in group]))))
    csvout(OUT/'summary.csv',summary)
    paired=[]
    for r in [r for r in refinements if r['method']=='regular']:
        match=next(s for s in refinements if s['id']==r['id'] and s['n']==r['n'] and s['method']=='network')
        gap=abs(r['final_energy']-match['final_energy'])/max(1.,abs(r['final_energy']))
        accepted=r['converged'] and match['converged'] and gap<=1e-6
        paired.append(dict(id=r['id'],n=r['n'],kind=r['kind'],matched=accepted,energy_gap=gap,
                           speedup=r['online_seconds']/match['online_seconds']))
    csvout(OUT/'refinement_pairs.csv',paired)
    accepted=[r['speedup'] for r in paired if r['matched']]
    dump(OUT/'completion.json',dict(test_cases=len(rows),raw_valid=sum(r['raw_valid'] for r in rows),
        refined_runs=len(refinements),refined_converged=sum(r['converged'] for r in refinements),
        matched_pairs=len(accepted),total_pairs=len(paired),
        paired_speedup=float(np.exp(np.mean(np.log(accepted)))) if accepted else None,
        selected_epoch=ck['epoch'],summary=summary))
    fig,axes=plt.subplots(2,4,figsize=(14,7),constrained_layout=True)
    for j,kind in enumerate(KINDS):
        for i,n in enumerate(CONFIG['test_n']):
            r=next(r for r in summary if r['kind']==kind and r['n']==n)
            axes[i,j].bar(['Regular','Teacher','Network'],[1,r['teacher_ratio'],r['prediction_ratio']])
            axes[i,j].axhline(1,color='black',lw=.6)
            axes[i,j].set_title(f'{kind} n={n}; legal {r["raw_valid"]}/{r["cases"]}')
            axes[i,j].set_ylabel('Poisson L2 / regular')
    fig.savefig(OUT/'pde_comparison.png',dpi=150);plt.close(fig)
    print('COMPLETED',json.dumps(dict(paired_speedup=float(np.exp(np.mean(np.log(accepted)))) if accepted else None,
                                   summary=summary)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','train','evaluate','all'])
    args=parser.parse_args()
    for stage in (['prepare','train','evaluate'] if args.stage=='all' else [args.stage]):
        globals()[stage]()
