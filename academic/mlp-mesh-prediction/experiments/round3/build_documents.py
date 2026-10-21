"""Build figures, Chinese article and classroom report from saved results."""
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import experiment as e
from src.paper_template import to_tex

R=e.ROOT
NAMES={'B0':'规则初值+固定步长提议','B1':'X-MLP+坐标转换+精修',
       'B2':'Q-MLP+精修','B3':'训练集1NN+精修','B4':'规则初值+沿用已接受步长'}
LABELS=['Fixed Armijo','X-MLP','Q-MLP','1NN','Warm Armijo']

def rows(name):
    return list(csv.DictReader((R/'results'/name).open(encoding='utf-8-sig')))

def write(path,text):
    (R/path).write_text(text,encoding='utf-8')

def figure(name,fig):
    fig.savefig(R/f'results/{name}.png',dpi=190,bbox_inches='tight')
    fig.savefig(R/f'results/{name}.svg',bbox_inches='tight');plt.close(fig)

def table(headers,body):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+
                     ['|'+'|'.join(map(str,r))+'|' for r in body])

def main():
    a=json.loads((R/'results/aggregate.json').read_text(encoding='utf-8'))
    diag=json.loads((R/'results/diagnosis_summary.json').read_text(encoding='utf-8'))
    met=rows('metrics.csv');seeds=rows('seeds.csv');dr=rows('diagnosis.csv')
    train=[json.loads((R/f"models/training_{s}.json").read_text(encoding='utf-8')) for s in [e.CFG['seed'],e.CFG['seed']+1]]
    oldtrain=json.loads((e.SOURCE/'models/training_summary.json').read_text(encoding='utf-8'))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(8,2.65))
    values=[diag[k]*100 for k in ['raw_error','damped_error','aligned_error','teacher_cycle_error','transfer_change']]
    bars=ax.bar(['Raw X-MLP','Damped X-MLP','Roundtrip X-MLP','Teacher roundtrip','Transfer change'],values,
                color=['#4581b0','#4581b0','#dc8546','#a2608c','#6e9b74'])
    ax.set_ylabel('Relative displacement (%)')
    ax.bar_label(bars,fmt='%.2f',padding=3);ax.set_ylim(0,max(values)*1.22)
    figure('diagnosis',fig)
    fig,axes=plt.subplots(1,2,figsize=(8,2.65))
    for seed in [e.CFG['seed'],e.CFG['seed']+1]:
        h=rows(f'train_{seed}.csv')
        axes[0].semilogy([int(r['epoch']) for r in h],[float(r['validation_mse']) for r in h],label=str(seed))
    axes[0].set(xlabel='Epoch',ylabel='Q validation normalized MSE');axes[0].legend(fontsize=8)
    for seed in [e.CFG['seed'],e.CFG['seed']+1]:
        vals=[float(r['physical_error'])*100 for r in seeds if r['split']=='test' and int(r['seed'])==seed]
        axes[1].plot(range(1,31),vals,'.-',label=str(seed))
    axes[1].set(xlabel='Unseen instance',ylabel='Physical prediction error (%)');axes[1].legend(fontsize=8)
    figure('training',fig)
    fig,axes=plt.subplots(1,2,figsize=(8,2.65))
    axes[0].bar(LABELS,[r['online_seconds'] for r in a],color=['#8b939c','#4581b0','#40978d','#b9914b','#946fa0'])
    axes[0].set_ylabel('Mean online time (s)')
    axes[1].bar(LABELS,[r['energy_evaluations'] for r in a],color=['#8b939c','#4581b0','#40978d','#b9914b','#946fa0'])
    axes[1].set_ylabel('Mean energy evaluations')
    for ax in axes:ax.tick_params(axis='x',rotation=20)
    figure('cost',fig)
    for iid in ['case_center','case_shifted','case_strength']:
        files={m:np.load(R/f'results/meshes/{iid}_{m}.npz') for m in e.METHODS}
        d=files['B2'];fig,axes=plt.subplots(2,3,figsize=(8,5.1))
        grids=[d['X0'],d['X_teacher'],files['B1']['X_initial'],d['X_initial'],files['B3']['X_initial'],d['X_final']]
        titles=['Initial','Teacher','X-MLP + transfer','Q-MLP','1NN','Q-MLP + refinement']
        for ax,x,title in zip(axes.flat,grids,titles):
            ax.triplot(x[:,0],x[:,1],d['cells'],color='#274a64',linewidth=.45)
            ax.set(xlim=(0,1),ylim=(0,1),title=title,aspect='equal');ax.set_xticks([0,.5,1]);ax.set_yticks([0,.5,1])
        fig.tight_layout();figure(iid,fig)
        for f in files.values():f.close()
    init_table=table(['方法','初始化误差/%','最终误差','初始能量相对差','收敛数'],[
        [r['method'],f"{100*r['initial_error']:.3f}",f"{r['final_error']:.2e}",
         f"{r['initial_energy_gap']:.2e}",f"{r['converged']}/30"] for r in a])
    cost_table=table(['方法','接受迭代','能量评价','回溯次数','在线时间/s','相对B0加速'],[
        [r['method'],f"{r['iterations']:.1f}",f"{r['energy_evaluations']:.1f}",f"{r['backtracks']:.1f}",
         f"{r['online_seconds']:.4f}",f"{r['speedup']:.2f}"] for r in a])
    diagnosis_table=table(['量','测试均值/%'],[
        ['原始物理预测误差',f"{100*diag['raw_error']:.3f}"],
        ['仅几何退缩后的误差',f"{100*diag['damped_error']:.3f}"],
        ['往返后的预测误差',f"{100*diag['aligned_error']:.3f}"],
        ['精确教师物理网格的往返误差',f"{100*diag['teacher_cycle_error']:.3f}"],
        ['教师计算坐标的往返误差',f"{100*diag['teacher_q_cycle_error']:.3f}"],
        ['预测往返引入的变化量',f"{100*diag['transfer_change']:.3f}"]])
    seed_table=table(['Q训练种子','最佳轮次','验证坐标MSE','测试物理误差/%','训练时间/s'],[
        [r['seed'],r['best_epoch'],f"{r['validation_coordinate_mse']:.3e}",
         f"{100*np.mean([float(z['physical_error']) for z in seeds if z['split']=='test' and int(z['seed'])==r['seed']]):.3f}",
         f"{r['training_seconds']:.2f}"] for r in train])
    success=[r for r in a if r['converged']==30]
    best=min(success,key=lambda r:r['online_seconds'])
    q=a[2];x=a[1];nn=a[3];warm=a[4]
    conclusion=(f"直接计算坐标监督使初始化物理误差由{100*x['initial_error']:.2f}%降至{100*q['initial_error']:.2f}%，"
        f"完整在线流程相对B0加速{q['speedup']:.2f}倍。达到共同阈值的方法中，{NAMES[best['method']]}平均耗时最短。"
        f"Q-MLP耗时为1NN的{q['online_seconds']/nn['online_seconds']:.3f}倍、为传统沿用步长方法的"
        f"{q['online_seconds']/warm['online_seconds']:.3f}倍。")
    recommendation=("课程设计宜以直接计算坐标预测为主线，并保留最近邻和沿用步长对照。"
                    "其价值由预测精度、达到同一停止阈值的在线成本与离线摊销共同界定。")
    comparison=(f"Q模型相对原X流程的在线均值缩短{100*(1-q['online_seconds']/x['online_seconds']):.2f}%，"
        "属于小幅改善，三次重复不能据此宣称稳定显著领先。"
        f"Q重建误差{100*q['initial_error']:.2f}%与原始X预测{100*diag['raw_error']:.2f}%接近，"
        "主要改进是避免坐标往返，不是网络拟合精度数量级提升。"
        f"沿用步长仅需{warm['energy_evaluations']:.1f}次能量评价，"
        f"但接受迭代为{warm['iterations']:.1f}次，Q精修为{q['iterations']:.1f}次；"
        "每次接受还需要物理重建，因此评价数更少没有转化为最短在线时间。")
    failures=[r for r in met if r['converged']!='True']
    total_valid=sum(r['final_valid']=='True' for r in met)
    all_tau=[float(r['tau']) for r in met if r['method'] in ['B1','B2','B3']]
    offline_teacher=float(sum(json.loads(p.read_text(encoding='utf-8'))['seconds'] for p in (e.SOURCE/'data/teacher').glob('*.json')))
    offline_train=train[0]['training_seconds']
    saving=a[0]['online_seconds']-q['online_seconds']
    amort=f"{int(np.ceil((offline_teacher+offline_train)/saving))}次" if saving>0 else '本次测量无法摊平'
    case_table=table(['算例','X初始化/%','Q初始化/%','1NN初始化/%','Q精修误差'],[
        [iid.replace('case_',''),*[
            f"{100*float(next(r for r in met if r['iid']==iid and r['method']==m)['initial_error']):.3f}" for m in ['B1','B2','B3']],
         f"{float(next(r for r in met if r['iid']==iid and r['method']=='B2')['final_error']):.2e}"]
        for iid in ['case_center','case_shifted','case_strength']])
    write('diagnosis.md',rf"""# 物理与计算坐标往返诊断

30个固定测试实例及3个展示实例使用已保存教师标签；下表只汇总30个测试实例。
设内部节点集合为 $\mathcal I$，共同分母为 $D_T=\|X_T-X_0\|_\mathcal I$。教师物理网格是 $X_T=R(Q_T)$。
对分片线性映射定义 $C(P)$ 为在物理网格P上插值“物理节点到参考节点”的映射至固定节点X0，
而R在计算网格Q上插值“计算节点到固定物理节点”的映射至参考节点。

{diagnosis_table}

![误差及往返变化量](results/diagnosis.png)

## 原因

教师自身经过 $Q_{{cycle}}=C(X_T)$、$X_{{cycle}}=R(Q_{{cycle}})$ 后，平均物理误差为{100*diag['teacher_cycle_error']:.3f}%；
即使物理输入完全精确，这次离散往返也不能恢复教师计算状态。两次插值使用不同的三角剖分及采样位置，
重采样后的分片线性函数通常不等于原函数。这里不存在将R与C当作精确逆映射的依据。

33个实例均未发生X位移退缩，tau均为1，几何退缩变化量为零。第二轮2.19%到6.28%的增加主要来自状态插值往返，
不是网络在安全阶段退化，也不是退缩过强。教师状态平均能量为{diag['teacher_energy']:.9f}，
往返状态为{diag['cycle_energy']:.9f}；能量只在对应Q上评价。

## 向量误差分解

令 $a=(P_{{safe}}-X_T)/D_T$，$b=(R(C(P_{{safe}}))-P_{{safe}})/D_T$，则

$$
\|a+b\|^2=\|a\|^2+\|b\|^2+2a^Tb.
$$

标量相对误差不能直接相加。测试集交叉项均值为{diag['cross_term']:.6e}；
逐实例等式残差均值为{diag['decomposition_residual']:.3e}。diagnosis.csv保存每个实例，
包括原始、退缩、对齐误差与教师往返误差、合法性和能量。
旧转移指标的分母是预测移动量，而这里统一使用D_T；旧口径另列old_transfer_denominator，不能与本表直接混用。

## 接口结论

X模型可用于直接给出物理网格近似，但转换为优化初值时引入额外插值误差。
Q模型直接监督已经存储的Q_teacher，推理后仅需一次R重建物理网格；
安全检查在Q与R(Q)上执行，不再走X到Q到X的往返。
该改变不修改能量、教师、拓扑或停止条件。
""")
    pages=[]
    pages.append(rf"""# 基于多层感知机的二维变分自适应网格预测与数值实验

作者：________　学号：________　课程：机器学习课程设计

**摘要：** 本文研究固定拓扑二维变分网格的参数化预测。针对物理节点预测转为优化初值时的误差，分离网络输出、几何退缩和离散坐标往返。精确教师物理网格的往返误差均值为{100*diag['teacher_cycle_error']:.2f}%，解释了物理预测误差由2.19%增至6.28%的现象。复用200个真实教师实例，以相同小型MLP改为监督计算节点位移，并与物理预测、训练集最近邻、两种传统Armijo策略比较。30个测试实例中，Q模型初始化物理误差为{100*q['initial_error']:.2f}%，精修后为{q['final_error']:.2e}，相对规则初值基线加速{q['speedup']:.2f}倍。{conclusion.split('。',1)[1]}

**关键词：** 变分网格；多层感知机；计算坐标；插值误差；初值预测

## 1 引言

变分自适应网格通过优化节点坐标，使固定数量的节点响应给定度量。传统方法每次从规则网格开始时，重复相近参数场的优化可能产生可利用的冗余。监督学习可近似参数到参考终点的映射，但网络输出必须与数值求解器的状态语义一致。若仅比较物理图形而不检查状态转换，误差与效率可能被误判。

本文选择固定方形区域和四参数高斯度量，以已有变分求解器产生教师。已有网格学习研究表明学习网格移动是可行方向[2]，本课程实验采用可复现的小型全连接网络，考察坐标表示、插值和简单对照对结果的影响。研究问题是：物理预测误差为何在接入求解器后增大；直接计算坐标监督能否改善；相对于简单传统方法是否仍有实际收益。

## 2 变分问题与坐标接口

区域为 $[0,1]^2$，每轴12个方格，共169个节点、121个内部节点及288个三角形。初始物理网格 $X_0$ 与规则参考网格 $Q_0$ 数值相同，计算状态Q与重建物理网格X含义不同。度量在初始单元中心冻结：

$$
M_\mu(x,y)=\left[1+A\exp\left(-\frac{{(x-c_x)^2+(y-c_y)^2}}{{\sigma^2}}\right)\right]I_2.
$$

设 $J_K=B_K(Q)E_K(X_0)^{{-1}}$，采用冻结物理网格上的离散Winslow能量[1]：

$$
I_h(Q;\mu)=\sum_K |K(X_0)|\,\operatorname{{tr}}\left(J_KM_K^{{-1}}J_K^T\right).
$$

本实现省略常数因子1/2。梯度对Q求导，边界梯度为零。传统教师求得 $Q_T$ 后，以分片线性逆映射在参考节点处求值得到 $X_T=R(Q_T)$。所有能量比较均使用相应计算状态，物理节点不能直接送入能量接口。
""")
    pages.append(rf"""## 3 离散坐标往返的误差诊断

对物理预测P，原流程先沿 $P-X_0$ 作几何退缩得到 $P_{{safe}}$，再插值得到计算初值 $C(P_{{safe}})$，最后重建为 $R(C(P_{{safe}}))$。R与C在不同三角剖分上重新采样，其离散组合一般不是恒等算子。通过精确教师输入可将此误差与网络拟合能力分离。

统一使用内部节点移动量 $D_T=\|X_T-X_0\|_\mathcal I$ 作分母，定义 $e_X=\|X-X_T\|_\mathcal I/D_T$。计算坐标往返误差另以 $\|Q_T-Q_0\|_\mathcal I$ 归一化。

{diagnosis_table}

![图1　测试集误差分解。最后一栏为往返引入的变化量，不能与原始误差直接相加。](../results/diagnosis.png)

测试及展示共33个实例均未触发物理位移退缩，原始与仅退缩误差完全相同。教师自身也出现约6.06%的往返误差，表明额外误差主要来自离散插值。原始2.19%的物理预测仍是网络拟合精度的有效量；6.28%评价的是接入求解器后的物理初值。

令 $a=(P_{{safe}}-X_T)/D_T$、$b=(R(C(P_{{safe}}))-P_{{safe}})/D_T$，有

$$
\|a+b\|^2=\|a\|^2+\|b\|^2+2a^Tb.
$$

逐实例等式残差均值为{diag['decomposition_residual']:.2e}，交叉项均值为{diag['cross_term']:.3e}。该向量关系解释为何不能以两种平均误差之差代替插值变化量。教师状态与往返状态的能量均值分别为{diag['teacher_energy']:.8f}和{diag['cycle_energy']:.8f}；往返状态仍合法，但不再等于教师终点。
""")
    pages.append(rf"""## 4 数据、学习与比较方法

复用200个随机参数教师及3个预先固定展示实例，不增加教师求解。参数范围为 $c_x,c_y\in[0.30,0.70]$、$A\in[2,8]$、$\sigma\in[0.18,0.30]$。随机实例整体划分为140个训练、30个验证、30个测试；展示参数不参与训练和模型选择。

X模型学习内部 $\Delta X=X_T-X_0$；Q模型学习内部 $\Delta Q=Q_T-Q_0$。两者均采用 $4\to64\to64\to242$、Tanh、20210个参数，输入按训练集均值及标准差归一化，标签除以各自训练集位移分量全局RMS。损失为归一化分量MSE：

$$
L(\theta)=\frac{{1}}{{242N}}\sum_{{j=1}}^N
\left\|f_\theta(\widetilde\mu_j)-\frac{{(\Delta Q_T)_j}}{{s_Q}}\right\|_2^2.
$$

Adam学习率0.001、权重衰减 $10^{{-6}}$、批量32，最多2600轮；验证连续200轮无改善即停止，取最佳验证权重。主种子固定20261021，辅助种子20261022只用于波动检查。输入统计与输出缩放均不读取测试标签。Q预测沿 $Q_0$ 到预测状态退缩，检查Q及R(Q)有限、边界固定、位于区域内、面积大于 $10^{{-10}}$，失败则回退Q0。

{seed_table}

![图2　两个固定种子的验证曲线与测试误差。主种子预先固定，不按测试结果选择。](../results/training.png)

比较方法为：B0规则初值、每轮从1提议Armijo；B1原X模型经坐标转换后精修；B2直接Q模型后精修；B3标准化参数空间中训练集1近邻的Q教师初值后精修；B4规则初值、下一轮沿用上次接受步长。B3只检索140个训练教师，不接触验证或测试教师。B4步长限定在 $[10^{{-12}},1]$，过小则恢复默认提议。

所有方法使用相同冻结度量、边界、Armijo系数 $10^{{-4}}$、退缩因子1/2、绝对梯度阈值 $10^{{-5}}$、2200接受迭代与30000能量评价上限。B0至B3共用原求解器，B4仅改变步长提议策略。物理预测原模型和最佳权重保持不变。
""")
    def casepara(iid,cn):
        rs={m:next(r for r in met if r['iid']==iid and r['method']==m) for m in e.METHODS}
        mu=e.data(iid)['mu']
        return (rf"参数为 $\mu=({mu[0]:.2f},{mu[1]:.2f},{mu[2]:.1f},{mu[3]:.2f})$。"
            f"X模型转换后误差为{100*float(rs['B1']['initial_error']):.3f}%，"
            f"Q模型重建误差为{100*float(rs['B2']['initial_error']):.3f}%，"
            f"最近邻误差为{100*float(rs['B3']['initial_error']):.3f}%。"
            f"Q模型精修后误差为{float(rs['B2']['final_error']):.2e}，"
            f"接受迭代{rs['B2']['iterations']}次，在线平均{float(rs['B2']['online_seconds']):.4f}秒。")
    pages.append(rf"""## 5 三个代表性数值算例

### 5.1 中心局部加密

![图3　中心加密六状态比较。所有网格使用相同节点编号、连接和坐标范围。](../results/case_center.png)

{casepara('case_center','中心')}

图中比较初始、教师、X模型转换后、Q模型、最近邻与Q模型精修后的物理网格。直接Q监督保留计算状态的含义；物理输出仍由原重建函数产生，因此图形与精修初值对应同一状态。局部节点聚集只是可视化依据，精度取全部内部节点的归一化误差。

{case_table}

三个算例分别检验局部峰值位于中心、峰值偏移、强度及宽度改变，均位于给定参数区间内。展示实例不单独训练网络或改变阈值。各方法完整节点数组、初始及最终Q、最小面积、能量和逐迭代历史随实验保存。
""")
    pages.append(rf"""### 5.2 偏心与较强局部加密

![图4　偏心局部加密的初始、教师、Q预测与精修网格。](../results/case_shifted.png)

{casepara('case_shifted','偏心')}

![图5　较强、较窄高斯度量的初始、教师、Q预测与精修网格。](../results/case_strength.png)

{casepara('case_strength','强度')}
""")
    # Two wide figures on one page retain readable six-panel labels.
    pages[-1]=pages[-1].replace('](../results/case_shifted.png)','](../results/case_shifted_compact.png)').replace(
        '](../results/case_strength.png)','](../results/case_strength_compact.png)')
    for iid in ['case_shifted','case_strength']:
        d=np.load(R/f'results/meshes/{iid}_B2.npz')
        fig,axes=plt.subplots(1,4,figsize=(8,2.05))
        for ax,key,title in zip(axes,['X0','X_teacher','X_initial','X_final'],['Initial','Teacher','Q-MLP','Refined']):
            nodes=d[key];ax.triplot(nodes[:,0],nodes[:,1],d['cells'],linewidth=.45,color='#274a64')
            ax.set(aspect='equal',xlim=(0,1),ylim=(0,1),title=title);ax.set_xticks([0,1]);ax.set_yticks([0,1])
        fig.tight_layout();figure(iid+'_compact',fig);d.close()
    pages.append(rf"""## 6 独立测试的精度与计算成本

以下为30个测试实例均值。初始能量相对差为 $(I_h(Q)-I_h(Q_T))/|I_h(Q_T)|$。
所有预测误差均评价实际进入精修的物理网格R(Q)，B1原始物理预测误差另列于诊断。B4从规则网格出发，因而初始化误差为1。

{init_table}

{cost_table}

![图6　五种方法完整在线时间与能量评价次数。](../results/cost.png)

模型和最近邻字典在计时前预加载，CPU单线程，每实例每方法重复三次，按实例与重复次数交替正反执行顺序。计时从问题对象建立开始，包含参数归一化、推理或近邻检索、几何检查、重建及精修；不含磁盘读写、加载、指标计算和训练。timings.csv保存495次运行，metrics.csv保存165组状态与同一实例三次耗时的样本标准差。表中均值基于全部30个测试参数，不选择速度较快的个例。

{conclusion}

本次共165组最终状态中{total_valid}组几何合法，未收敛组数{len(failures)}。B1至B3初始化最小退缩系数为{min(all_tau):.3f}。成功率与最终梯度均保存，不用未达精度的终止时间证明加速。能量评价数反映算法工作量，在线时间还包含重建等实际开销，二者不能互相替代。
""")
    pages.append(rf"""## 7 讨论与结论

### 7.1 坐标表示与使用价值

精确教师输入的往返误差直接证明：物理坐标到计算坐标的离散转换会改变已经正确的终点，第二轮增加的误差主要由此产生。直接监督Q使用现有教师中已保存的状态，避免了多余的C/R组合，也使网络输出与能量梯度变量一致。X模型原始误差仍应独立报告，不能将其转换后误差解释为训练失败。

{conclusion}

{comparison}

{recommendation}

最近邻不需要拟合网络，因此是衡量小数据参数回归必要性的直接对照。沿用上次接受步长不需要教师数据，其收益来自减少回溯，不能归为初值预测收益。两类对照分别回答“学习是否优于简单查找”和“收益是否也可由廉价求解策略获得”。本实验据实比较完整在线流程，不将模型推理时间单独作为最终加速。

### 7.2 离线成本与限制

已有203个教师求解累计{offline_teacher:.2f}秒，主Q模型训练{offline_train:.2f}秒。若这些教师为新任务专门产生，以B0与B2本次在线均值差粗算，摊平教师与主训练成本约需{amort}同分布调用。若教师已供其他任务使用，只需计入新增训练成本。辅助种子的训练不属于主模型部署所需成本。

实验限于固定拓扑、分辨率、单高斯冻结度量和参数区间；未测跨分辨率、复杂边界、分布外或PDE解误差。几何合法率和达到教师精度不能直接等同于PDE精度改善。计时依赖本机负载，三次重复用于记录同一实例的波动；测试实例间的标准差另保存在aggregate.csv。网页构建与资源一致性检查不替代浏览器视觉与键盘验收，实际状态见README。

### 7.3 结论

本文通过教师往返实验解释物理预测接入求解器后的误差，使用同规模Q-MLP完成了无需坐标往返的状态预测，并在未见参数与三个代表算例上比较五种方法。核心结论是选择与优化变量一致的监督表示，并以最近邻及传统步长策略界定机器学习收益。该结果支持在当前参数族内进行可复现的课程比较实验。

## 参考文献

[1] Huang W., Kamenski L., Russell R. D. A comparative numerical study of meshing functionals for variational mesh adaptation. Journal of Mathematics Study, 2015, 48(2):168–186. DOI:10.4208/jms.v48n2.15.04.

[2] Song W., Zhang M., Wallwork J. G., et al. M2N: Mesh Movement Networks for PDE Solvers. Advances in Neural Information Processing Systems, 35, 2022.
""")
    paper='\n\n<!-- pagebreak -->\n\n'.join(pages)
    write('paper/report.md',paper)
    tex=to_tex(paper)
    tex=tex.replace(r'\resizebox{\linewidth}{!}{',r'\begin{adjustbox}{max width=\linewidth}')
    tex=tex.replace(r'\bottomrule\end{tabular}}\end{center}',
                    r'\bottomrule\end{tabular}\end{adjustbox}\end{center}')
    # Compact only the two four-panel illustrations.
    tex=tex.replace(r'\includegraphics[width=\linewidth]{../results/case_shifted_compact.png}',
                    r'\includegraphics[width=.96\linewidth]{../results/case_shifted_compact.png}')
    tex=tex.replace(r'\includegraphics[width=\linewidth]{../results/case_strength_compact.png}',
                    r'\includegraphics[width=.96\linewidth]{../results/case_strength_compact.png}')
    write('paper/report.tex',tex)
    talk=rf"""# 二维变分网格：坐标表示与学习初值

## 研究结论

{conclusion}

## 问题与教师

固定169节点、288三角形；四参数高斯度量；优化变量为计算节点Q，物理网格为X=R(Q)。200个教师按140/30/30划分，另有三个展示实例。

## 为什么误差从2.19%变成6.28%

精确教师网格往返也产生{100*diag['teacher_cycle_error']:.2f}%误差。33个实例均未发生几何退缩，原因是两次不同三角剖分上的离散重采样不能精确互逆。

![误差分解](../results/diagnosis.png)

{diagnosis_table}

## 直接预测计算坐标

保持4→64→64→242的Tanh网络、训练划分、优化器和预算一致。监督Q_teacher-Q0，只重建一次物理网格，不走物理到计算再到物理的往返。两个固定种子，不用测试结果挑选模型。

![训练曲线与误差波动](../results/training.png)

{seed_table}

## 公平对照

B0：规则初值+每轮从1提议Armijo。B1：X-MLP+转换+精修。B2：Q-MLP+精修。B3：140个训练教师中的1近邻+精修。B4：规则初值+沿用上次接受步长。相同梯度阈值1e-5、能量、边界、合法性和预算。

## 算例一：中心加密

![中心加密](../results/case_center.png)

{casepara('case_center','中心')}

## 算例二：加密位置移动

![偏心加密](../results/case_shifted.png)

{casepara('case_shifted','偏心')}

## 算例三：强度与宽度变化

![较强局部加密](../results/case_strength.png)

{casepara('case_strength','强度')}

## 全部测试精度

{init_table}

{case_table}

## 在线成本

{cost_table}

![完整在线成本](../results/cost.png)

30个测试+3个展示，每方法三次配对计时，共495次运行。包含问题建立、预测/查找、检查、重建与精修，不含预加载和离线成本。

## 使用价值与限制

{conclusion}

{comparison}

{recommendation}

专门生成教师并训练主模型约需{offline_teacher+offline_train:.2f}秒，按本次B0与B2均值差约{amort}调用摊平。固定拓扑、单高斯、区间内结论；没有PDE误差或跨分辨率结论。

## 参考文献

Huang, Kamenski, Russell. A comparative numerical study of meshing functionals for variational mesh adaptation. 2015.

Song et al. M2N: Mesh Movement Networks for PDE Solvers. NeurIPS 2022.
"""
    write('presentation/talk.md',talk)
    write('summary.md',f"""# 第三轮结果

教师物理网格自身往返误差为{100*diag['teacher_cycle_error']:.3f}%。X模型原始误差{100*diag['raw_error']:.3f}%，往返后{100*diag['aligned_error']:.3f}%；几何退缩变化为零。误差增大主要来自不同三角剖分上的离散插值往返。

{conclusion}

{comparison}

{init_table}

{cost_table}

{recommendation}

30测试与3展示均运行三次配对计时，共495次。最终状态合法{total_valid}/165，未收敛{len(failures)}/165。详细限制、复现和产物位置见README.md。
""")
    e.save_json(R/'results/report_values.json',dict(diagnosis=diag,aggregate=a,conclusion=conclusion,
        recommendation=recommendation,teacher_seconds=offline_teacher,main_training_seconds=offline_train))
    print('Figures and report sources ready.')

if __name__=='__main__':main()
