"""Render physical mesh comparisons and measured learning/optimization curves."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.common import ROOT,load_config,read_csv,metric_value

COLORS=dict(initial='#8b97a3',teacher='#1968a7',prediction='#d28a21',refined='#078579')
NAMES=dict(initial='Initial mesh',teacher='Variational teacher',
           prediction='MLP + safety/transfer',refined='MLP + refinement')

def save(fig,name):
    fig.savefig(ROOT/f'results/{name}.png',dpi=210,bbox_inches='tight')
    fig.savefig(ROOT/f'results/{name}.svg',bbox_inches='tight')
    plt.close(fig)

def main():
    cfg=load_config()
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    xx,yy=np.meshgrid(np.linspace(0,1,100),np.linspace(0,1,100))
    points=np.stack((xx,yy),axis=-1)
    for case in cfg['display_cases']:
        d=np.load(ROOT/f'results/meshes/case_{case}.npz')
        mu=d['mu']
        fig,axes=plt.subplots(1,4,figsize=(13.6,3.5),layout='constrained')
        field=metric_value(points,mu)
        for ax,key,stage in zip(axes,['X0','X_teacher','X_prediction','X_refined'],NAMES):
            nodes=d[key]
            ax.contourf(xx,yy,field,levels=np.linspace(1,1+mu[2],12),cmap='YlOrBr',alpha=.30,vmin=1,vmax=1+mu[2])
            ax.triplot(nodes[:,0],nodes[:,1],d['cells'],lw=.48,color='#154f63')
            ax.plot(mu[0],mu[1],'+',color='#b4391e',ms=6)
            ax.set(aspect='equal',xlim=(0,1),ylim=(0,1),xlabel='x',ylabel='y',title=NAMES[stage])
            ax.set_xticks([0,.5,1]);ax.set_yticks([0,.5,1])
        save(fig,f'case_{case}')
    h=read_csv(ROOT/'results/train_history.csv')
    summary=json.loads((ROOT/'models/training_summary.json').read_text(encoding='utf-8'))
    fig,axes=plt.subplots(1,2,figsize=(10.4,3.3),layout='constrained')
    for ax,key,label in [(axes[0],'normalized_mse','Normalized displacement MSE'),
                         (axes[1],'coordinate_mse','Coordinate RMSE')]:
        for subset,name,color in [('train','Training','#1968a7'),('validation','Validation','#d28a21')]:
            values=np.array([float(r[f'{subset}_{key}']) for r in h])
            if key=='coordinate_mse':values=np.sqrt(values)
            ax.semilogy([int(r['epoch']) for r in h],values,label=name,color=color)
        ax.axvline(summary['best_epoch'],color='#666666',ls=':',lw=.8)
        ax.set(xlabel='Epoch',ylabel=label);ax.grid(alpha=.2);ax.legend()
    save(fig,'train_curve')
    metrics=read_csv(ROOT/'results/metrics.csv')
    fig,axes=plt.subplots(1,2,figsize=(10.5,3.6),layout='constrained')
    for ax,key,label in [(axes[0],'energy_evaluations','Energy evaluations'),
                         (axes[1],'seconds','Online time (s)')]:
        for offset,stage in [(-.2,'teacher'),(.2,'refined')]:
            values=[];std=[]
            for case in cfg['display_cases']:
                r=next(v for v in metrics if v['instance_id']==f'case_{case}' and v['stage']==stage)
                values.append(float(r[key]))
                std.append(float(r['teacher_seconds_std' if stage=='teacher' else 'hybrid_seconds_std']) if key=='seconds' else 0)
            ax.bar(np.arange(3)+offset,values,width=.38,yerr=std,capsize=3,
                   color=COLORS[stage],label=NAMES[stage])
        ax.set_xticks(np.arange(3),['Centered','Shifted','Strength/width'])
        ax.set_ylabel(label);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    save(fig,'cost_comparison')
    fig,axes=plt.subplots(1,3,figsize=(11.7,3.3),layout='constrained')
    for ax,case in zip(axes,cfg['display_cases']):
        for stage in ['teacher','refined']:
            history=read_csv(ROOT/f'results/histories/case_{case}_{stage}.csv')
            ax.semilogy([int(r['iteration']) for r in history],
                [float(r['gradient_norm']) for r in history],label=NAMES[stage],color=COLORS[stage])
        ax.axhline(cfg['teacher']['gradient_tolerance'],color='#777777',ls=':',lw=.8)
        ax.set(title=case.capitalize(),xlabel='Accepted iteration',ylabel='Projected gradient norm')
        ax.grid(alpha=.2)
    axes[-1].legend(fontsize=7)
    save(fig,'convergence')
    # A compact training/online diagram is a method schematic, not an experiment image.
    fig,ax=plt.subplots(figsize=(10.4,2.1),layout='constrained')
    ax.axis('off')
    labels=['Metric parameters','Variational teacher','Physical mesh labels','Train MLP']
    for j,label in enumerate(labels):
        x=.13+j*.245
        ax.text(x,.72,label,ha='center',va='center',bbox=dict(boxstyle='round,pad=.5',fc='#e8eff6',ec='#adc2d2'),fontsize=10)
        if j<3:ax.annotate('',xy=(x+.15,.72),xytext=(x+.085,.72),arrowprops=dict(arrowstyle='->',color='#465e6b'))
    labels=['Unseen parameters','MLP displacement','Safety + state transfer','Same-objective refine']
    for j,label in enumerate(labels):
        x=.13+j*.245
        ax.text(x,.25,label,ha='center',va='center',bbox=dict(boxstyle='round,pad=.5',fc='#e4f1ed',ec='#98c2b6'),fontsize=10)
        if j<3:ax.annotate('',xy=(x+.15,.25),xytext=(x+.085,.25),arrowprops=dict(arrowstyle='->',color='#465e6b'))
    save(fig,'workflow')
    print('Saved mesh plots, training curve, timing comparison, convergence and workflow.')

if __name__=='__main__':main()
