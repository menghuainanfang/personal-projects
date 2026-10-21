"""Create Chinese reports and figures from the independent evaluation."""
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from study import ROOT,SOURCE,METHODS,write_json,write_csv

GROUPS={'fresh_ID':'新同分布参数','OOD_center':'中心外推','OOD_narrow':'窄峰强加密',
        'OOD_broad':'宽峰弱加密','scale_8':'8×8规模迁移','scale_16':'16×16规模迁移',
        'scale_24':'24×24规模迁移','paper_wave':'论文波前代理','double_peak':'双峰代理'}

def read(name):
    return list(csv.DictReader((ROOT/'results'/name).open(encoding='utf-8-sig')))

def table(headers,rows):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+
                     ['|'+'|'.join(map(str,r))+'|' for r in rows])

def figure(name,fig):
    fig.savefig(ROOT/f'图表/{name}.png',dpi=190,bbox_inches='tight')
    fig.savefig(ROOT/f'图表/{name}.svg',bbox_inches='tight');plt.close(fig)

def main():
    s=json.loads((ROOT/'results/summary.json').read_text(encoding='utf-8'))
    groups=s['groups'];metrics=read('metrics.csv');paired=read('paired_comparisons.csv')
    cases=json.loads((ROOT/'results/cases.json').read_text(encoding='utf-8'))
    absolute=[]
    for c in cases:
        teacher=np.load(ROOT/f'results/meshes/{c["iid"]}_reference.npz')
        mask=np.all((teacher['X0']>0)&(teacher['X0']<1),axis=1)
        for method in METHODS:
            mesh=np.load(ROOT/f'results/meshes/{c["iid"]}_{method}.npz')
            absolute.append(dict(iid=c['iid'],group=c['group'],method=method,n=c['n'],
                coordinate_component_rmse=float(np.sqrt(np.mean((mesh['X_initial'][mask]-teacher['X'][mask])**2)))))
    write_csv(ROOT/'results/absolute_errors.csv',absolute)
    def get(g,m):return next(r for r in groups if r['group']==g and r['method']==m)
    speed={}
    rows=[]
    for group in GROUPS:
        for method in ['X_mlp','Q_mlp']:
            ids=[r['iid'] for r in paired if r['group']==group and r['method']==method and r['comparable']=='True']
            base=[float(r['online_seconds']) for r in metrics if r['iid'] in ids and r['method']=='regular']
            learned=[float(r['online_seconds']) for r in metrics if r['iid'] in ids and r['method']==method]
            speed[group,method]=float(np.mean(base)/np.mean(learned)) if ids else None
        x,q=get(group,'X_mlp'),get(group,'Q_mlp')
        rows.append([GROUPS[group],x['n_cases'],f"{100*x['initial_node_error']:.2f}",
            f"{100*q['initial_node_error']:.2f}",f"{speed[group,'X_mlp']:.2f}",f"{speed[group,'Q_mlp']:.2f}"])
    overview=table(['测试组','例数','X初始化误差/%','Q初始化误差/%','X同目标加速','Q同目标加速'],rows)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    names=list(GROUPS);pos=np.arange(len(names))
    fig,axes=plt.subplots(1,2,figsize=(12,3.7))
    for offset,method,label,color in [(-.18,'X_mlp','X-MLP','#388f83'),(.18,'Q_mlp','Q-MLP','#587ca5')]:
        axes[0].bar(pos+offset,[100*get(g,method)['initial_node_error'] for g in names],width=.36,color=color,label=label)
        axes[1].bar(pos+offset,[speed[g,method] for g in names],width=.36,color=color,label=label)
    for ax in axes:ax.set_xticks(pos,names,rotation=55,ha='right');ax.legend(fontsize=8)
    axes[0].set_ylabel('Safe physical displacement error (%)')
    axes[1].set_ylabel('Matched physical objective speedup');axes[1].axhline(1,ls='--',color='grey',linewidth=.8)
    fig.tight_layout();figure('01_泛化误差与初始化收益',fig)
    parent_ids=[f'fresh_ID_{i:02d}' for i in range(4)]
    fig,axes=plt.subplots(1,2,figsize=(9,3))
    for method,label in [('X_mlp','X-MLP'),('Q_mlp','Q-MLP')]:
        err=[];time=[]
        for n in [8,12,16,24]:
            sub=[r for r in metrics if r['method']==method and (r['iid'] in parent_ids if n==12 else r['group']==f'scale_{n}')]
            err.append(100*np.mean([float(r['initial_node_error']) for r in sub]))
            reg=[next(z for z in metrics if z['iid']==r['iid'] and z['method']=='regular') for r in sub]
            time.append(np.mean([float(z['online_seconds']) for z in reg])/np.mean([float(z['online_seconds']) for z in sub]))
        axes[0].plot([8,12,16,24],err,'o-',label=label);axes[1].plot([8,12,16,24],time,'o-',label=label)
    for ax in axes:ax.set_xlabel('Squares per axis n');ax.legend();ax.set_xticks([8,12,16,24])
    axes[0].set_ylabel('Initialization node error (%)');axes[1].set_ylabel('Online speedup');axes[1].axhline(1,color='grey',ls='--')
    fig.tight_layout();figure('02_规模迁移与误差',fig)
    fig,axes=plt.subplots(2,4,figsize=(11,5.4))
    for row,iid in enumerate(['paper_wave_00','double_peak_00']):
        regular=np.load(ROOT/f'results/meshes/{iid}_regular.npz')
        xp=np.load(ROOT/f'results/meshes/{iid}_X_mlp.npz');qp=np.load(ROOT/f'results/meshes/{iid}_Q_mlp.npz')
        meshes=[regular['X_initial'],xp['X_initial'],xp['X_final'],qp['X_final']]
        for ax,nodes,title in zip(axes[row],meshes,['Regular','Gaussian proxy X','Physical refine X','Physical refine Q']):
            ax.triplot(nodes[:,0],nodes[:,1],regular['cells'],color='#294d66',linewidth=.5)
            ax.set(aspect='equal',title=title,xlim=(0,1),ylim=(0,1));ax.set_xticks([0,1]);ax.set_yticks([0,1])
    fig.tight_layout();figure('03_论文波前与双峰迁移',fig)
    smooth=read('paper_smoothing.csv');d=np.load(ROOT/'results/meshes/smoothing_20_17.npz')
    fig,axes=plt.subplots(1,3,figsize=(9,3))
    for ax,key,title in zip(axes,['X_initial','X_final','reference'],['Perturbed','Smoothed Q method','Regular reference']):
        x=d[key];ax.triplot(x[:,0],x[:,1],d['cells'],linewidth=.4,color='#294d66')
        ax.set(aspect='equal',title=title);ax.set_xticks([0,1]);ax.set_yticks([0,1])
    fig.tight_layout();figure('04_原论文平滑核验',fig)
    fig,ax=plt.subplots(figsize=(5,3.6))
    for method,label in [('regular','Regular'),('X_mlp','X-MLP'),('Q_mlp','Q-MLP')]:
        sub=[r for r in metrics if r['method']==method]
        ax.loglog([float(r['area_lower_bound']) for r in sub],[float(r['minimum_observed_area']) for r in sub],'.',label=label)
    ax.set(xlabel='Proved area lower bound',ylabel='Smallest observed physical area')
    ax.legend();fig.tight_layout();figure('05_理论面积下界核验',fig)
    narrow=get('OOD_narrow','X_mlp')
    narrow_rise=100*(narrow['final_rmse']/narrow['initial_rmse']-1)
    smooth_table=table(['每轴方格','种子','收敛','剩余扰动比例','最小终点面积'],[
        [r['n'],r['seed'],r['converged'],f"{float(r['relative_remaining_perturbation']):.2e}",
         f"{float(r['final_min_area']):.3e}"] for r in smooth])
    functional=table(['组别','规则RMSE','X初值RMSE','X精修RMSE'],[
        [GROUPS[g],f"{get(g,'regular')['regular_rmse']:.6f}",
         f"{get(g,'X_mlp')['initial_rmse']:.6f}",f"{get(g,'X_mlp')['final_rmse']:.6f}"] for g in GROUPS])
    conclusions=[
        f"新同分布样本上X/Q物理初始化误差为{100*get('fresh_ID','X_mlp')['initial_node_error']:.2f}%/"
        f"{100*get('fresh_ID','Q_mlp')['initial_node_error']:.2f}%，对应同目标平均加速{speed['fresh_ID','X_mlp']:.2f}/"
        f"{speed['fresh_ID','Q_mlp']:.2f}倍。",
        f"分布外窄强峰的X误差升至{100*narrow['initial_node_error']:.1f}%，"
        f"宽弱峰为{100*get('OOD_broad','X_mlp')['initial_node_error']:.1f}%；不能把同分布精度推广为外推保证。",
        "网络原生输出固定242维；8/16/24规模的结果使用显式双线性位移场插值，没有重新训练，属于带适配器的迁移。",
        f"波前和双峰没有原生输入接口。固定高斯代理初始化在双峰组X加速为{speed['double_peak','X_mlp']:.2f}倍，"
        "没有稳定优势；不能称为网络学会这些外部场。",
        f"窄强峰组物理能量下降后，X初始化的插值RMSE反而增加{narrow_rise:.1f}%。能量最小化与插值最小化不是同一目标。"
    ]
    report=f"""# 泛化、规模迁移与原论文核验

## 核心结论

"""+'\n\n'.join(conclusions)+f"""

## 数据与实验协议

新增60个评估问题，没有重新训练模型。40个新高斯参数包括16个新同分布、8个中心外推、8个窄强峰和8个宽弱峰；另有12个规模迁移问题、4个正弦波前和4个双峰代理问题。具体参数见results/cases.json，种子20261025。

三种初值都最小化相同物理能量，固定拓扑、边界、梯度阈值1e-5、4000次迭代和40000次能量预算。模型预加载，每问题交替顺序重复三次，保存540次计时。旧冻结Q目标仅生成参考物理坐标，不将其求解时间与新物理目标作同精度比较。

只有两种方法都收敛且终点相对能量差不超过1e-7时才计算成对加速；原始状态、终止原因与完整耗时保留。节点误差分母是当前参考教师的内部移动量；弱加密时分母较小，应同时看results/absolute_errors.csv中的坐标分量RMSE。Q的原始合法率检查其计算输出，进入精修的物理状态另经合法性检查。

## 泛化结果

{overview}

![不同问题组的初始化误差与同目标收益](../图表/01_泛化误差与初始化收益.png)

表中外部场的代理输入固定为(0.5,0.5,5,0.24)。这保留原模型接口，测试高斯形状初始化的迁移，而不是用四参数伪装任意函数的完整编码。不同场可以有完全相同的网络输出。

## 规模测试

网络在12×12方格上训练。规模测试选用四个相同高斯参数，在参考坐标中将13×13节点上的位移做双线性插值，再检查边界、面积与必要退缩。没有直接改变网络输出层，也没有按新规模重新训练。

![相同四组参数的规模对照](../图表/02_规模迁移与误差.png)

本次8—24方格范围内可运行，但更细网格上的预测误差没有随有限元分辨率自动收敛到零。结果不能推广到不同拓扑、不同区域或任意分辨率。

## 原论文对应关系

原文为Huang和Kamenski，J. Comput. Phys. 301 (2015):322–337，arXiv:1410.7872v2。已检查用户本地PDF第1、12、13、14页，页脚编号与PDF页码在这些页一致。

Example 4.1的M=I平滑测试采用Huang泛函theta=1/3、p=2，在固定物理网格上优化Q，再重建物理网格。使用自己的正扰动网格、对角三角剖分和Armijo极小化，替代原文的ode15s积分到t=1。

{smooth_table}

![原论文平滑机制核验](../图表/04_原论文平滑核验.png)

四个实例都恢复到接近参考规则网格，支持平滑机制的定性复现；不声称复现原论文轨迹、全部网格连接、计时或所有例题。

Example 4.2原函数为u=tanh(-30[y-1/2-(1/4)sin(2pi x)])。本轮相位零实例使用这一函数，其他三例改变相位；度量改为有界各向同性波带监测函数，而非原文引用的Hessian度量构造。马蹄形区域及三维九球案例未实施，不把本轮算例迁移称为完整论文复现。

![原论文波前与双峰的代理迁移](../图表/03_论文波前与双峰迁移.png)

## 功能指标与能量目标

{functional}

所有RMSE使用相同160×160物理采样点与解析节点真值。窄强峰中的RMSE反升是实际结果，不能因优化能量下降而删去。初值是否接近旧教师、物理能量是否更低、具体函数插值是否更准，是三个不同问题。

## 数学结论

[数学结论与证明](数学结论与证明.md)给出物理能量的正面积下界、条件Armijo驻点结果、原冻结Q目标的强凸性、误差传递条件和不可普遍排序的反例。

![面积下界与实测值](../图表/05_理论面积下界核验.png)

面积界由独立物理目标本身保证，不是MLP独有优势。更小的初值误差也可能位于收敛慢的特征模态，因此不能单靠误差大小证明实际加速。

## 适用范围

当前模型适合固定高斯参数族的快速近似与优化初值；对外推、跨规模和任意外部场的效果要分别验证。课程设计宜定位为学习初值的条件收益和评价指标对照，不定位为通用网格预测算法。没有新模型训练、PDE解误差或原论文全部算例复现。

## 数据入口

- results/metrics.csv：180个状态的误差、质量、能量、收敛和平均耗时。
- results/timings.csv：540次原始计时。
- results/paired_comparisons.csv：同终点能量条件与成对加速。
- results/reference_metrics.csv：旧Q教师的功能误差。
- results/absolute_errors.csv：绝对坐标分量RMSE。
- results/meshes/及histories/：全部保存节点与求解过程。

参考原文：[Huang与Kamenski 2015](https://arxiv.org/abs/1410.7872)。
"""
    (ROOT/'文档/泛化测试报告.md').write_text(report,encoding='utf-8')
    overview_text="# 本轮实验入口\n\n"+'\n\n'.join(conclusions)+"""

- [完整测试报告](文档/泛化测试报告.md)
- [数学结论与证明](文档/数学结论与证明.md)
- [运行和代码入口](运行说明.md)
- 数据位于results，图位于图表；原论文PDF留在本地，不随项目分发。
"""
    (ROOT/'README.md').write_text(overview_text,encoding='utf-8')
    write_json(ROOT/'results/reading_values.json',dict(conclusions=conclusions,speedups=[
        dict(group=g,method=m,speedup=speed[g,m]) for g in GROUPS for m in ['X_mlp','Q_mlp']],
        overview_table=overview,narrow_interpolation_error_increase_percent=narrow_rise,
        total_cases=60,total_timing_runs=540))
    print('Chinese reports and figures ready.')

if __name__=='__main__':main()
