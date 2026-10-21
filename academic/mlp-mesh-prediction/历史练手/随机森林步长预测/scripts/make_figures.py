"""Create all figures and aggregate tables from stored numerical results."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.experiment import METHODS
from scripts.run_experiments import write_csv,write_json,CASES

LABEL = dict(fixed='Fixed 0.05',armijo='Armijo',warm='Warm start',rf='Random forest')
COLORS = dict(fixed='#8996a5',armijo='#1764aa',warm='#d98720',rf='#00897b')
CHINESE = dict(uniform='均匀度量',gaussian='局部高斯度量',anisotropic='各向异性度量')
def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))
def save(fig,name):
    fig.savefig(ROOT/f'figures/{name}.png',dpi=190,bbox_inches='tight')
    fig.savefig(ROOT/f'figures/{name}.svg',bbox_inches='tight')
    plt.close(fig)
def main():
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    rows=read_csv(ROOT/'data/results.csv')
    aggregate=[]
    for case in CASES:
        for method in METHODS:
            group=[r for r in rows if r['case']==case and r['method']==method]
            row=dict(case=case,method=method,runs=len(group),converged=sum(r['converged']=='True' for r in group))
            for key in ['final_energy','relative_energy_reduction','iterations','energy_evals','backtracks',
                        'elapsed_seconds','proposal_seconds','search_seconds','final_gradient_norm','min_area',
                        'physical_min_area','illegal_candidates','fallbacks']:
                values=[float(r[key]) for r in group]
                row[key+'_mean']=float(np.mean(values))
                row[key+'_std']=float(np.std(values,ddof=1))
            row['flipped_cells']=sum(int(r['flipped_cells']) for r in group)
            aggregate.append(row)
    write_csv(ROOT/'data/aggregate.csv',aggregate)
    for case in CASES:
        fig,axes=plt.subplots(1,3,figsize=(10.2,3.5),layout='constrained')
        for ax,method in zip(axes,['initial','armijo','rf']):
            m=np.load(ROOT/f'data/meshes/{case}_100_n12_{"armijo" if method=="initial" else method}.npz')
            nodes=m['initial'] if method=='initial' else m['final']
            ax.triplot(nodes[:,0],nodes[:,1],m['cells'],lw=0.58,color='#18596c')
            ax.set(aspect='equal',xlim=(0,1),ylim=(0,1),xlabel='x',ylabel='y',
                   title=('Initial physical mesh' if method=='initial' else LABEL[method]))
            ax.set_xticks([0,0.5,1]); ax.set_yticks([0,0.5,1])
        save(fig,f'mesh_{case}')
    fig,axes=plt.subplots(1,3,figsize=(11,3.3),layout='constrained')
    for ax,case in zip(axes,CASES):
        for method in METHODS:
            h=read_csv(ROOT/f'data/trajectories/{case}_100_n12_{method}.csv')
            ax.plot([int(r['iteration']) for r in h],[float(r['energy']) for r in h],
                    label=LABEL[method],color=COLORS[method],lw=1.3)
        ax.set(title=case.capitalize(),xlabel='Accepted iteration',ylabel='Energy I_h')
        ax.ticklabel_format(axis='y',useOffset=False); ax.grid(alpha=.2)
    axes[-1].legend(fontsize=8)
    save(fig,'energy')
    fig,axes=plt.subplots(1,2,figsize=(10.5,3.7),layout='constrained')
    for ax,key,label in zip(axes,['energy_evals','elapsed_seconds'],['Energy evaluations','Elapsed time (s)']):
        for i,method in enumerate(METHODS):
            a=[next(r for r in aggregate if r['case']==c and r['method']==method) for c in CASES]
            ax.bar(np.arange(3)+(i-1.5)*.19,[r[key+'_mean'] for r in a],width=.18,
                   yerr=[r[key+'_std'] for r in a],label=LABEL[method],color=COLORS[method],capsize=2)
        ax.set_xticks(range(3),['Uniform','Gaussian','Anisotropic']);ax.set_ylabel(label)
        ax.grid(axis='y',alpha=.2)
    axes[1].legend(fontsize=8)
    save(fig,'cost')
    fig,axes=plt.subplots(1,3,figsize=(11,3.3),layout='constrained')
    for ax,case in zip(axes,CASES):
        for method in METHODS:
            h=read_csv(ROOT/f'data/trajectories/{case}_100_n12_{method}.csv')
            g=np.array([float(r['gradient_norm']) for r in h])
            ax.semilogy([int(r['iteration']) for r in h],g/g[0],color=COLORS[method],label=LABEL[method])
        ax.axhline(1e-4,color='#666666',ls=':',lw=.8)
        ax.set(title=case.capitalize(),xlabel='Accepted iteration',ylabel='Relative gradient norm')
        ax.grid(alpha=.2)
    axes[-1].legend(fontsize=8)
    save(fig,'gradient')
    v=read_csv(ROOT/'data/validation_predictions.csv')
    fig,axes=plt.subplots(1,2,figsize=(9,3.5),layout='constrained')
    truth=np.array([float(r['true_log_alpha']) for r in v]);pred=np.array([float(r['predicted_log_alpha']) for r in v])
    axes[0].scatter(truth,pred,s=7,alpha=.25,color=COLORS['rf'])
    lim=[min(truth.min(),pred.min())-.1,max(truth.max(),pred.max())+.1]
    axes[0].plot(lim,lim,color='#555555',lw=1)
    axes[0].set(xlabel='Teacher log(alpha)',ylabel='Predicted log(alpha)',title='Held-out validation instances')
    info=json.loads((ROOT/'data/model_metrics.json').read_text(encoding='utf-8'))
    axes[1].barh(['Gradient norm','Previous alpha','Minimum area','Previous backtracks'],list(info['importance'].values()),color=COLORS['rf'])
    axes[1].set(xlabel='Impurity importance',title='Forest feature importance')
    save(fig,'model')
    # Geometric diagnostics use the same initial/final physical meshes shown above.
    conf=json.loads((ROOT/'data/configurations.json').read_text(encoding='utf-8'))
    geometry=[]
    for case in CASES:
        cfg=next(r for r in conf if r['subset']=='test' and r['case']==case and r['seed']==100)
        m=np.load(ROOT/f'data/meshes/{case}_100_n12_rf.npz')
        row=dict(case=case,seed=100,center=cfg['center'],radius=.2)
        for stage in ['initial','final']:
            nodes=m[stage]; cells=m['cells']
            edges=np.stack((nodes[cells[:,1]]-nodes[cells[:,0]],nodes[cells[:,2]]-nodes[cells[:,0]]),axis=-1)
            singular=np.linalg.svd(edges,compute_uv=False)
            row[stage+'_edge_condition_mean']=float(np.mean(singular[:,0]/singular[:,1]))
            row[stage+'_center_node_count']=int(np.sum(np.linalg.norm(nodes-cfg['center'],axis=1)<.2))
        geometry.append(row)
    write_json(ROOT/'data/geometric_diagnostics.json',geometry)
    print(json.dumps(aggregate,ensure_ascii=False,indent=2))
if __name__=='__main__':
    main()
