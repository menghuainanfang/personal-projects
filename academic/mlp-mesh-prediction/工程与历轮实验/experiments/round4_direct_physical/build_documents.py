"""Create the article and classroom report from round-four result files."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
from src.paper_template import to_tex

NAMES={'X0':'规则网格','XT':'旧Q教师物理网格','X_raw':'X模型直接输出',
       'X_transferred':'X模型经坐标往返','Q_physical':'Q模型一次重建',
       'physical_regular':'物理优化：规则初值','physical_mlp':'物理优化：X模型初值'}
LABELS=['Regular','Q teacher','Raw X-MLP','Transferred X','Rebuilt Q-MLP']

def text(path,value):
    (ROOT/path).write_text(value,encoding='utf-8')

def table(headers,body):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+
                     ['|'+'|'.join(map(str,r))+'|' for r in body])

def save_figure(name,fig):
    fig.savefig(ROOT/f'results/{name}.png',dpi=200,bbox_inches='tight')
    fig.savefig(ROOT/f'results/{name}.svg',bbox_inches='tight');plt.close(fig)

def main():
    s=json.loads((ROOT/'results/summary.json').read_text(encoding='utf-8'))
    a={r['method']:r for r in s['A']};b={r['method']:r for r in s['B']}
    times={r['method']:r for r in s['A_timing']}
    bm=read_rows('B_metrics.csv');end=read_rows('B_endpoint_comparison.csv')
    r,m=b['physical_regular'],b['physical_mlp']
    speed=r['online_seconds']/m['online_seconds']
    faster=sum(float(next(z for z in bm if z['iid']==iid and z['method']=='physical_mlp')['online_seconds'])<
               float(next(z for z in bm if z['iid']==iid and z['method']=='physical_regular')['online_seconds']) for iid in SPLIT['test'])
    maxend=max(float(z['relative_endpoint_distance']) for z in end if z['split']=='test')
    maxegap=max(abs(float(z['relative_energy_difference'])) for z in end if z['split']=='test')
    raw,qq,base=a['X_raw'],a['Q_physical'],a['X0']
    raw_change=100*(raw['interpolation_rmse']/base['interpolation_rmse']-1)
    refined_gain=100*(1-m['interpolation_rmse']/base['interpolation_rmse'])
    conclusion=(f"直接X预测在33个未见实例上均合法且无需退缩，测试节点误差为{100*raw['node_error']:.2f}%，"
        f"与Q模型的{100*qq['node_error']:.2f}%接近。两者插值RMSE分别为"
        f"{raw['interpolation_rmse']:.6f}和{qq['interpolation_rmse']:.6f}；"
        f"直接X相对规则网格的平均RMSE增加{raw_change:.2f}%。")
    bconclusion=(f"独立物理目标下，规则初值与X模型初值均达到共同梯度阈值。"
        f"平均接受迭代由{r['iterations']:.1f}降至{m['iterations']:.1f}，"
        f"完整在线时间由{r['online_seconds']:.3f}秒降至{m['online_seconds']:.3f}秒，均值比加速{speed:.2f}倍。"
        f"物理精修后RMSE为{m['interpolation_rmse']:.6f}，较规则网格降低{refined_gain:.2f}%。")
    recommendation=("课程设计可保留“直接物理预测作为廉价近似与物理优化初值”的方案，"
        "以独立插值评测和同目标精修为核心。单独的原始X预测适合快速逼近教师，"
        "本次插值指标不支持把它作为无需后处理的最终优胜网格；物理精修的收益温和，需计入离线成本。")
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(10,2.9))
    for ax,key,mult,ylabel in zip(axes,['node_error','interpolation_rmse','min_angle'],
        [100,1000,1],['Node displacement error (%)','Interpolation RMSE (x 0.001)','Minimum angle (degrees)']):
        vals=[a[k][key]*mult for k in a]
        std=[a[k][key+'_std']*mult for k in a]
        ax.bar(LABELS,vals,yerr=std,capsize=2,color=['#979fa7','#60778d','#388e82','#c8934e','#507fa4'])
        ax.set_ylabel(ylabel);ax.tick_params(axis='x',rotation=48)
    fig.tight_layout();save_figure('A_comparison',fig)
    for iid in ['case_center','case_shifted','case_strength']:
        d=np.load(ROOT/f'results/meshes/{iid}_A.npz')
        fig,axes=plt.subplots(1,5,figsize=(10,2.25))
        for ax,key,title in zip(axes,a.keys(),LABELS):
            x=d[key];ax.triplot(x[:,0],x[:,1],d['cells'],linewidth=.45,color='#294d66')
            ax.set(aspect='equal',xlim=(0,1),ylim=(0,1),title=title);ax.set_xticks([0,1]);ax.set_yticks([0,1])
        fig.tight_layout();save_figure(iid,fig);d.close()
    fig,axes=plt.subplots(1,3,figsize=(10,2.6))
    for ax,iid in zip(axes,['case_center','case_shifted','case_strength']):
        for method,label in [('physical_regular','Regular initial'),('physical_mlp','X-MLP initial')]:
            h=read_rows(f'histories/{iid}_{method}.csv')
            ax.semilogy([int(z['iteration']) for z in h],[float(z['gradient_norm']) for z in h],label=label)
        ax.axhline(1e-5,color='grey',ls='--',linewidth=.7);ax.set(title=iid.replace('case_',''),xlabel='Accepted iteration')
    axes[0].set_ylabel('Physical projected gradient norm');axes[0].legend(fontsize=8)
    fig.tight_layout();save_figure('B_convergence',fig)
    fig,axes=plt.subplots(1,2,figsize=(8,2.4))
    for ax,key,ylabel in zip(axes,['online_seconds','iterations'],['Mean online time (s)','Mean accepted iterations']):
        ax.bar(['Regular initial','X-MLP initial'],[r[key],m[key]],color=['#8193a0','#388e82'])
        ax.set_ylabel(ylabel)
    fig.tight_layout();save_figure('B_cost',fig)
    iid='case_strength';old=np.load(ROOT/f'results/meshes/{iid}_A.npz')
    reg=np.load(ROOT/f'results/meshes/{iid}_physical_regular.npz')
    mlp=np.load(ROOT/f'results/meshes/{iid}_physical_mlp.npz')
    fig,axes=plt.subplots(1,4,figsize=(9,2.4))
    for ax,x,label in zip(axes,[old['X0'],old['X_raw'],reg['X_final'],mlp['X_final']],
        ['Regular','Raw X-MLP','Physical: regular','Physical: MLP']):
        ax.triplot(x[:,0],x[:,1],old['cells'],color='#294d66',linewidth=.45)
        ax.set(title=label,aspect='equal',xlim=(0,1),ylim=(0,1));ax.set_xticks([0,1]);ax.set_yticks([0,1])
    fig.tight_layout();save_figure('B_mesh',fig)
    old.close();reg.close();mlp.close()
    a_table=table(['物理网格','节点误差/%','最小角/度','最差质量q','RMSE×1000'],[
        [NAMES[k],f"{100*a[k]['node_error']:.3f}",
         f"{a[k]['min_angle']:.2f} ± {a[k]['min_angle_std']:.2f}",
         f"{a[k]['min_quality']:.3f}",
         f"{1000*a[k]['interpolation_rmse']:.3f} ± {1000*a[k]['interpolation_rmse_std']:.3f}"] for k in a])
    b_table=table(['物理目标的初值','接受迭代','能量评价','在线时间/s','收敛数'],[
        ['规则网格',f"{r['iterations']:.1f}",f"{r['energy_evaluations']:.1f}",
         f"{r['online_seconds']:.3f} ± {r['online_seconds_std']:.3f}",f"{r['converged']}/30"],
        ['X模型输出',f"{m['iterations']:.1f}",f"{m['energy_evaluations']:.1f}",
         f"{m['online_seconds']:.3f} ± {m['online_seconds_std']:.3f}",f"{m['converged']}/30"]])
    energy_table=table(['初值','初始E_phys','终点E_phys','终点梯度范数','终点插值RMSE'],[
        [label,f"{z['initial_energy']:.8f}",f"{z['final_energy']:.8f}",
         f"{z['final_gradient_norm']:.2e}",f"{z['interpolation_rmse']:.6f}"]
         for label,z in [('规则网格',r),('X模型输出',m)]])
    time_table=table(['预测分支','推理/ms','检查或转换/ms','完整生成/ms'],[
        [NAMES[k],*[f"{1000*times[k][key]:.3f}" for key in ['inference_seconds','processing_seconds','generation_seconds']]]
        for k in ['X_raw','X_transferred','Q_physical']])
    case_rows=[]
    am=read_rows('A_metrics.csv')
    for iid in ['case_center','case_shifted','case_strength']:
        group={z['method']:z for z in am if z['iid']==iid}
        br=next(z for z in bm if z['iid']==iid and z['method']=='physical_regular')
        bl=next(z for z in bm if z['iid']==iid and z['method']=='physical_mlp')
        case_rows.append([iid.replace('case_',''),f"{float(group['X0']['interpolation_rmse']):.5f}",
            f"{float(group['X_raw']['interpolation_rmse']):.5f}",f"{float(group['Q_physical']['interpolation_rmse']):.5f}",
            f"{float(bl['interpolation_rmse']):.5f}",f"{float(br['online_seconds'])/float(bl['online_seconds']):.2f}"])
    case_table=table(['算例','规则RMSE','原始X RMSE','Q重建RMSE','物理精修RMSE','同目标加速'],case_rows)
    old_train=json.loads((SOURCE/'models/training_summary.json').read_text(encoding='utf-8'))
    teacher_seconds=sum(json.loads(f.read_text(encoding='utf-8'))['seconds'] for f in (SOURCE/'data/teacher').glob('*.json'))
    offline=teacher_seconds+old_train['training_seconds']
    amort=int(np.ceil(offline/(r['online_seconds']-m['online_seconds']))) if r['online_seconds']>m['online_seconds'] else None
    pages=[]
    pages.append(rf"""# 直接物理网格预测与变分精修的数值实验

作者：________　学号：________　课程：机器学习课程设计

**摘要：** 本文复用已有二维变分网格教师和小型MLP，检验直接使用物理节点预测的实际价值。对30个测试实例及3个展示实例，比较规则网格、教师物理网格、原始X预测、坐标往返后的X预测和Q模型一次重建网格，并测量同一解析函数的分片线性插值误差。原始X预测与Q重建均合法，测试节点误差分别为{100*raw['node_error']:.2f}%与{100*qq['node_error']:.2f}%，插值精度接近，但均未优于规则网格。随后定义独立的物理坐标均匀分布/对齐能量，使用完整自动微分和单调Armijo求解。在同一物理目标下，X模型初值将平均在线时间由{r['online_seconds']:.3f}秒降至{m['online_seconds']:.3f}秒，终点插值RMSE较规则网格降低{refined_gain:.2f}%。实验表明，教师拟合精度与功能精度需要分开评价，直接物理预测可作为低成本近似和优化初值。

**关键词：** 物理网格；多层感知机；变分方法；自动微分；插值误差

## 1 引言

固定节点预算下的网格移动旨在将节点重新分配到需要解析的区域。变分方法以度量控制坐标分布[1]，学习方法则近似参数到网格终点的映射[2]。两者结合时，需要区分“拟合教师坐标”与“改善具体数值任务”。

已有X模型直接预测物理内部节点位移，本研究不增加训练或更换网络。新的实验是保留其原始物理输出，测量几何和独立插值指标，再探索将物理节点直接作为优化变量。物理输出无需为展示或插值先转换到计算坐标；只有进入原Q求解器时才需要那一接口。

## 2 数据与既有方法

单位方形每轴12个方格，共169个节点、121个内部节点和288个三角形。固定连接及逐节点边界。复用200个真实教师，按140/30/30完整参数实例拆分，另有三个预先指定展示参数。输入为 $\mu=(c_x,c_y,A,\sigma)$，范围为 $c_x,c_y\in[0.30,0.70]$、$A\in[2,8]$、$\sigma\in[0.18,0.30]$。

原X模型与Q模型均为 $4\to64\to64\to242$ 的Tanh网络，输入和标签缩放仅使用训练集。保留原X权重和第三轮预先固定的Q权重；不重新选择模型，不产生教师样本。X标签为物理位移，Q标签为计算位移，二者数值意义不同。

原求解器在固定物理网格 $X_0$ 上冻结度量，以计算节点Q为变量：

$$
I_h(Q;\mu)=\sum_K |K(X_0)|\operatorname{{tr}}
\left(B_K(Q)E_K(X_0)^{{-1}}M_K^{{-1}}E_K(X_0)^{{-T}}B_K(Q)^T\right).
$$

其输出物理网格为 $X_T=R(Q_T)$。原始X预测为P，仅物理退缩得到 $P_{{safe}}$；旧转换分支还执行 $R(C(P_{{safe}}))$。本实验分别保存这些对象，不把物理X直接代入旧Q能量。
""")
    pages.append(rf"""## 3 独立的物理坐标变分目标

固定参考三角形的边矩阵记为 $\widehat E_K$，物理边矩阵为 $E_K(X)$。定义物理到参考的逆Jacobian

$$
J_K(X)=\widehat E_KE_K(X)^{{-1}},\qquad
M_K(X)=m_K(X)I_2,\qquad
m_K(X)=1+A\exp\left(-\frac{{|x_K(X)-c|^2}}{{\sigma^2}}\right).
$$

其中 $x_K(X)$ 为当前物理重心。采用文献[1]式(11)的泛函族，取 $d=2,p=2,\theta=1/3$，在每个物理单元做重心求积：

$$
E_{{\rm phys}}(X)=\sum_K |K(X)|m_K(X)\left[
\frac13\left(\frac{{\|J_K(X)\|_F^2}}{{m_K(X)}}\right)^2+
\frac43\left(\frac{{\det J_K(X)}}{{m_K(X)}}\right)^2\right].
$$

面积、Jacobian及度量均依赖X，不能使用原冻结物理网格上的Q梯度。用PyTorch float64对整个离散表达式自动微分，保留面积、逆矩阵和重心度量的全部导数，最后将边界梯度置零。对规则和变形训练实例各取两个固定随机方向，中心差分步长 $10^{{-6}}$，方向导数差异通过 $10^{{-7}}$ 的归一化检查。

正面积下能量为正，且 $1\le m\le9$。局部缩放时逆Jacobian与面积共同作用，p=2的项提供面积分配惩罚；退化单元的逆Jacobian增长不能由有界m抵消。坐标和度量在单位方形上无量纲。连续泛函的性质不自动给出本离散问题的唯一性，本文只验证实现的导数、几何、下降与数值停止条件。

### 3.1 相同物理目标的求解

规则初值与原X模型物理初值共用同一能量与求解程序。采用投影负梯度方向，BB谱步长提议[3]为

$$
\alpha_{{BB}}=\frac{{s^Ts}}{{s^Ty}},\quad
s=X_k-X_{{k-1}},\quad y=g_k-g_{{k-1}}.
$$

曲率非正则取0.1，初始提议0.1，提议限制 $[10^{{-8}},1]$。Armijo系数 $10^{{-4}}$、退缩因子1/2，仅接受有限、区域内、边界固定、全部有向面积大于 $10^{{-10}}$ 且真实充分下降的候选。停止条件为 $\|g\|_2\le10^{{-5}}$，上限3000次接受迭代、30000次能量评价。梯度求值的前向计算也计入能量评价。

### 3.2 几何及独立功能指标

使用最小有向面积、翻转数、最小角，以及 $q_K=4\sqrt3|K|/\sum_{{e\subset K}}|e|^2$ 评价形状；q越接近1越好。所有网格在相同160×160中点采样上插值

$$
u_\mu(x,y)=\exp\left(-\frac{{(x-c_x)^2+(y-c_y)^2}}{{\sigma^2}}\right),\quad
e_{{\rm int}}=\sqrt{{\frac1N\sum_{{j=1}}^N\left(u_h(z_j)-u_\mu(z_j)\right)^2}}.
$$

节点值取解析场真值，使用同一三角连接上的分片线性插值。该采样RMSE独立于教师坐标标签，是插值实验而非PDE解误差。
""")
    pages.append(rf"""## 4 直接使用物理预测的测试结果

表1为30个独立测试实例均值；最小角与RMSE后为实例间样本标准差。节点误差分母为教师内部物理移动量 $\|X_T-X_0\|_\mathcal I$，不移动误差为1。q为每张网格最差单元质量的均值。

{a_table}

![图1　节点误差、采样插值RMSE与最小角。误差棒为30个实例间的样本标准差。](../results/A_comparison.png)

{conclusion}

实验A共165个状态均合法，翻转数为零，原始X预测的33个实例均不需要位移退缩。X与Q预测的最小角和最差单元质量接近。规则网格的形状质量最高，但形状与节点分配共同决定插值表现，单独的几何质量不是充分指标。

旧教师的平均插值RMSE也高于规则网格，说明该教师在这一解析场和节点预算下不是插值最优网格。度量根据高斯函数值设定，并未按插值误差最小化构造；因此更接近教师不必然降低RMSE。经坐标往返的X输出虽然节点误差更大，其RMSE却较低，这是评价目标不同的实际例子。

表2为模型预加载后的生成时间。固定拓扑接口预建，包含输入归一化与推理、物理合法性检查，Q分支还含一次R重建；旧转移分支含C/R。三分支交替顺序各重复三次，误差评估不计时。

{time_table}

三个展示实例用320×320采样复核，所有五状态RMSE的最大相对变化为{100*s['sampling_max_relative_change']:.4f}%。较密采样支持本次误差量级判断，但不把X与Q之间极小的均值差解释为稳定精度优势。
""")
    pages.append(rf"""## 5 三个代表性算例

### 5.1 中心加密

![图2　中心度量：规则、教师、原始X、转换X和Q重建物理网格。](../results/case_center.png)

参数为 $\mu=(0.50,0.50,5.0,0.24)$。所有分支使用同一节点编号、边界与连接，五张图的范围一致。原始X的物理输出未经计算坐标往返。

### 5.2 加密中心偏移

![图3　偏心度量的五状态比较。](../results/case_shifted.png)

参数为 $\mu=(0.36,0.64,5.0,0.24)$，考察区间内部加密位置移动。模型不为此例单独拟合。

### 5.3 强度及宽度变化

![图4　较强、较窄高斯度量的五状态比较。](../results/case_strength.png)

参数为 $\mu=(0.58,0.43,7.5,0.19)$。下表最后一列仅比较同一物理目标的两种初值。

{case_table}
""")
    pages.append(rf"""## 6 物理坐标直接优化的结果

实验B的66组终点全部合法并达到共同物理梯度阈值，198次重复运行均收敛。下表为测试集均值，时间后的标准差为实例间差异；单实例三次计时的标准差保存在逐实例CSV。

{b_table}

{energy_table}

![图5　三个展示实例的物理能量投影梯度轨迹；虚线为共同停止阈值。](../results/B_convergence.png)

![图6　同一物理目标下的完整在线时间与接受迭代数。](../results/B_cost.png)

{bconclusion}

30个测试实例中，MLP初值在{faster}个实例上耗时较短。两种初值终点的最大相对能量差为{maxegap:.2e}，以规则物理优化终点移动量归一化的最大节点距离为{maxend:.2e}，本次未观察到不同终点导致的明显精度差异。物理目标终点相对旧Q教师约{100*m['node_error']:.2f}%的坐标差是不同目标产生的结果，不能解释为相同教师精修失败。
""")
    pages.append(rf"""## 7 结果解释与课程设计选择

![图7　较强度量下，规则和原始X预测与两个物理优化终点。](../results/B_mesh.png)

### 7.1 直接物理输出的价值

直接X输出以约{1000*times['X_raw']['generation_seconds']:.3f}毫秒完成预测和检查，保留了约2%的教师位移拟合精度，省去离散往返。与Q模型一次重建的插值误差和几何质量基本相同，因而对快速给出教师近似具有价值。其平均插值RMSE略高于规则网格，不能据此宣称直接预测本身改善了插值任务。

独立物理能量在本问题族上可求导、可下降并达到共同阈值。MLP初值减少约{100*(1-m['iterations']/r['iterations']):.1f}%的接受迭代、约{100*(1-m['online_seconds']/r['online_seconds']):.1f}%的在线时间。两种初值都能获得相近终点，因此MLP的主要作用是减少达到终点的成本，而非创造传统方法无法获得的网格。

{recommendation}

### 7.2 离线成本与限制

既有203个教师求解累计{teacher_seconds:.2f}秒，X模型训练{old_train['training_seconds']:.2f}秒，本轮没有新增教师或训练。若这些成本专为部署产生，按本次同目标平均节省估算，约需{amort}次同分布调用摊平；若教师已有其他用途，可单列新增成本，不能将离线阶段视为免费。

本实验固定拓扑、分辨率、区域与单高斯参数范围，未涉及PDE误差或分布外泛化。度量不是针对本插值任务最优设计，物理重心求积目标也不保证全局唯一极小点。I_h与E_phys是不同离散目标，能量大小、梯度阈值和时间不能跨目标作同精度加速比较。时间受本机负载影响，模型及固定拓扑接口预加载，指标与磁盘操作排除；三次重复均保留。网页构建检查与实际浏览器验收状态见README。

## 8 结论

直接使用原始物理预测避免多余坐标往返，在本测试集上具有合法、廉价且接近教师的特点，但对指定解析场未优于规则网格。使用独立的物理坐标能量精修可改善本次插值指标，X模型作为同目标优化初值取得{speed:.2f}倍的温和加速。课程设计的可靠结论是同时检验教师拟合、几何与独立功能指标，并将初值收益限定在同一优化目标内。

## 参考文献

[1] Huang W., Kamenski L., Russell R. D. A comparative numerical study of meshing functionals for variational mesh adaptation. Journal of Mathematics Study, 2015, 48(2):168–186. DOI:10.4208/jms.v48n2.15.04. [论文原文](https://arxiv.org/abs/1503.04709)。

[2] Song W., Zhang M., Wallwork J. G., et al. M2N: Mesh Movement Networks for PDE Solvers. Advances in Neural Information Processing Systems, 35, 2022. [会议原文](https://proceedings.neurips.cc/paper_files/paper/2022/hash/2f88d8061f12abae9d14d376fd69c933-Abstract-Conference.html)。

[3] Barzilai J., Borwein J. M. Two-Point Step Size Gradient Methods. IMA Journal of Numerical Analysis, 1988, 8(1):141–148. DOI:10.1093/imanum/8.1.141. [期刊入口](https://doi.org/10.1093/imanum/8.1.141)。
""")
    paper='\n\n<!-- pagebreak -->\n\n'.join(pages)
    text('paper/report.md',paper)
    tex=to_tex(paper).replace(r'\resizebox{\linewidth}{!}{',r'\begin{adjustbox}{max width=\linewidth}')
    tex=tex.replace(r'\bottomrule\end{tabular}}\end{center}',r'\bottomrule\end{tabular}\end{adjustbox}\end{center}')
    text('paper/report.tex',tex)
    talk=rf"""# 直接物理网格预测与优化

## 核心发现（约40秒）

{conclusion}

{bconclusion}

## 为什么直接使用X（约40秒）

旧X模型已经预测物理节点，新的实验直接使用其输出。Q模型预测计算节点后需要一次物理重建；原X模型进入Q求解器还需离散往返。本轮把这些物理网格分开评价，并使用独立的解析函数插值指标。

## 固定数据与评价（约40秒）

已有200个教师按140/30/30拆分，另有三个展示实例；169节点、288三角形。网络与教师均不重训。所有网格在相同160×160物理采样点上插值同一解析高斯函数，RMSE只是插值误差。

## 直接物理预测是否足够好（约60秒）

{a_table}

![物理网格精度与质量](../results/A_comparison.png)

原始X与Q重建的插值精度接近，但都略差于规则网格。度量按高斯函数值设定，并非为插值最优设计；接近教师不等于功能误差更低。

## 三个算例（约60秒）

![中心加密](../results/case_center.png)

![偏心加密](../results/case_shifted.png)

![强度与宽度变化](../results/case_strength.png)

{case_table}

## 能否直接优化X（约60秒）

固定参考边矩阵，令 $J=\widehat E E(X)^{{-1}}$。采用Huang均匀分布/对齐能量族，d=2、p=2、theta=1/3，面积、逆Jacobian和重心度量全部随X变化。

$$
E_{{\rm phys}}(X)=\sum_K |K(X)|m_K(X)\left[
\frac13\left(\frac{{\|J_K(X)\|_F^2}}{{m_K(X)}}\right)^2+
\frac43\left(\frac{{\det J_K(X)}}{{m_K(X)}}\right)^2\right].
$$

完整自动微分通过方向差分；固定边界、正面积、BB步长提议和单调Armijo回溯。该目标与旧Q目标不同。

## 同目标初值比较（约60秒）

{b_table}

{energy_table}

![物理优化成本](../results/B_cost.png)

![物理梯度收敛](../results/B_convergence.png)

MLP初值在{faster}/30个测试实例上更快；两个终点最大相对能量差{maxegap:.2e}。中心展示例可能不加速，全部个例与重复计时保留。

## 最终方案与限制（约50秒）

{recommendation}

专门产生教师并训练需约{offline:.2f}秒，按本轮同目标均值差约{amort}次调用摊平。固定拓扑、单高斯、区间内结论；没有PDE精度结论，不跨目标比较加速。

## 参考文献

Huang, Kamenski, Russell. A comparative numerical study of meshing functionals for variational mesh adaptation. 2015.

Song et al. M2N: Mesh Movement Networks for PDE Solvers. NeurIPS 2022.

Barzilai, Borwein. Two-Point Step Size Gradient Methods. 1988.
"""
    text('presentation/talk.md',talk)
    text('summary.md',f"""# 第四轮结果分析

{conclusion}

{a_table}

{bconclusion}

{b_table}

两种物理初值的测试终点最大相对能量差{maxegap:.2e}，最大相对节点距离{maxend:.2e}；MLP在{faster}/30个测试实例上耗时较短。

{recommendation}

原始X的价值是低成本教师近似及物理优化初值，不能将本次插值精度略差于规则网格写成改进。物理精修的加速仅在相同E_phys下成立；旧Q目标与新X目标不混用能量或成本结论。
""")
    text('README.md',f"""# 直接物理网格预测与优化

{conclusion}

{bconclusion}

{recommendation}

## 成果入口

- paper/report.pdf：中文论文；report.md、report.tex可编辑，report.html可离线阅读。
- presentation/index.html：约5—8分钟课堂汇报网页；talk.md为讲稿。
- summary.md、audit.md：结果分析及数学/接口审计。
- results/A_metrics.csv、A_aggregate.csv：五种物理网格的逐实例指标及测试均值/标准差。
- results/B_metrics.csv、B_aggregate.csv：同一物理目标下两种初值的精度与成本。
- results/A_timings.csv、B_timings.csv：297次生成计时和198次优化计时。
- results/meshes/、histories/：33实例完整节点与物理优化轨迹；interpolation_points.npz为固定采样点。
- results/sampling_check.csv、B_endpoint_comparison.csv、verification.json：密采样、终点差异与指标复核。

## 复现

保留本目录在mesh_prediction/experiments/round4_direct_physical下的位置，教师和模型从上两级读取。依赖与上两级requirements.txt相同，使用CPU、PyTorch单线程；文档重建需要XeLaTeX及Node.js。

~~~powershell
python run_all.py
~~~

已有匹配的网页前端依赖时，可用--dependencies指定目录，Node可用--node指定可执行文件。仅重建文档加--documents-only，首次准备网页依赖可能需要联网。

分步运行 python -m unittest test_round4 -v、python experiment.py、python verify.py。本轮不会调用教师生成或模型训练。物理优化参数在physical.py的OPTIONS，已有网格及参数范围在上两级config.yaml。两种初值共用目标、梯度、预算、停止规则；计时排除采样与磁盘操作，固定拓扑接口和模型预加载。

运行 python package_project.py 生成新的完整ZIP，位置在mesh_prediction目录同级，名称mesh_prediction_round4_course_project.zip。包内包含所需源码、旧教师和模型、前三轮成果及本轮数据、图片、论文和离线网页，不含虚拟环境和前端依赖目录。

## 限制与验收

全部165个直接比较状态、66个物理优化终点均合法，所有198次优化重复达共同阈值；原有五项测试和新增四项测试通过。物理能量完整梯度通过四个方向差分，逐状态指标及汇总已重算复核。160与320密采样在展示实例上的最大RMSE相对变化为{100*s['sampling_max_relative_change']:.4f}%。

固定网格、单高斯参数区间与给定解析场的结论；没有PDE误差、分布外或跨分辨率保证。物理能量与旧Q目标不同，不能比较二者能量或作跨目标同精度加速结论。既有教师与X训练合计约{offline:.2f}秒，同目标优化粗略摊销约{amort}次。

PDF使用已有论文模板并逐页渲染检查；网页沿用原生成器构建及资源校验。当前浏览器工具对本地文件的限制使网页实际视觉与键盘交互验收未完成，可在本机浏览器直接打开HTML评估。
""")
    write_json(ROOT/'results/report_values.json',dict(conclusion=conclusion,physical_result=bconclusion,
        recommendation=recommendation,physical_speedup=speed,physical_faster_cases=faster,
        raw_rmse_increase_percent=raw_change,refined_rmse_reduction_percent=refined_gain,
        max_endpoint_distance=maxend,max_relative_energy_difference=maxegap,
        teacher_seconds=teacher_seconds,X_training_seconds=old_train['training_seconds'],amortization_calls=amort))
    print('Round-four figures and document sources ready.')

if __name__=='__main__':main()
