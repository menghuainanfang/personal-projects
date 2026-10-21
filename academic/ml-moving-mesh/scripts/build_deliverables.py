"""Write the paper and classroom narrative directly from the experiment tables."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import csv,json,re,platform,subprocess,shutil
import numpy as np
from scripts.make_figures import read_csv,CHINESE
from scripts.run_experiments import write_json

NAMES=dict(fixed='固定步长',armijo='Armijo',warm='热启动',rf='随机森林')
def main():
    agg=read_csv(ROOT/'data/aggregate.csv')
    raw=read_csv(ROOT/'data/results.csv')
    info=json.loads((ROOT/'data/model_metrics.json').read_text(encoding='utf-8'))
    protocol=json.loads((ROOT/'data/protocol.json').read_text(encoding='utf-8'))
    checks=json.loads((ROOT/'data/gradient_checks.json').read_text(encoding='utf-8'))
    geometry={r['case']:r for r in json.loads((ROOT/'data/geometric_diagnostics.json').read_text(encoding='utf-8'))}
    def get(c,m,k): return float(next(r for r in agg if r['case']==c and r['method']==m)[k+'_mean'])
    savings={c:100*(1-get(c,'rf','energy_evals')/get(c,'armijo','energy_evals')) for c in CHINESE}
    slowdown={c:get(c,'rf','elapsed_seconds')/get(c,'armijo','elapsed_seconds') for c in CHINESE}
    rf_fraction=100*sum(float(r['proposal_seconds']) for r in raw if r['method']=='rf')/sum(float(r['elapsed_seconds']) for r in raw if r['method']=='rf')
    all_min=min(float(r['physical_min_area']) for r in raw)
    all_flip=sum(int(r['flipped_cells']) for r in raw)
    err=max(r['relative_error'] for r in checks)
    table='|算例|方法|迭代数|能量评价|回溯数|时间/s|最终能量|\n|---|---|---:|---:|---:|---:|---:|\n'
    for r in agg:
        table+=f"|{CHINESE[r['case']]}|{NAMES[r['method']]}|{float(r['iterations_mean']):.1f}|{float(r['energy_evals_mean']):.1f}|{float(r['backtracks_mean']):.1f}|{float(r['elapsed_seconds_mean']):.3f}|{float(r['final_energy_mean']):.8f}|\n"
    timing_table='|算例|固定步长/s|Armijo/s|热启动/s|随机森林/s|\n|---|---:|---:|---:|---:|\n'
    for c in CHINESE:
        timing_table+='|'+CHINESE[c]+'|'+'|'.join(f"{get(c,m,'elapsed_seconds'):.3f} ± {float(next(r for r in agg if r['case']==c and r['method']==m)['elapsed_seconds_std']):.3f}" for m in NAMES)+'|\n'
    references='''[1] Huang W., Kamenski L., Russell R. D. A comparative numerical study of meshing functionals for variational mesh adaptation. Journal of Mathematics Study, 2015, 48(2): 168–186. DOI: 10.4208/jms.v48n2.15.04. [预印本](https://arxiv.org/abs/1503.04709)。

[2] Kamandi A. Learning the initial step size and backtracking reduction factor for the Armijo line search. Journal of Mathematical Modeling, 2026, Articles in Press, Corrected Proof，2026-08-18 在线发表. DOI: 10.22124/jmm.2026.33801.3107. [期刊页面](https://jmm.guilan.ac.ir/article_9844.html)。

[3] Wu T., Liu X., An W., Huang Z., Lyu H. A mesh optimization method using machine learning technique and variational mesh adaptation. Chinese Journal of Aeronautics, 2022, 35(3): 27–41. DOI: 10.1016/j.cja.2021.05.018. [期刊页面](https://www.sciopen.com/article/10.1016/j.cja.2021.05.018)。'''
    conclusion=(f"随机森林相对固定初值 Armijo 的能量评价次数分别减少 {savings['uniform']:.1f}%、{savings['gaussian']:.1f}% 和 {savings['anisotropic']:.1f}%，"
                f"但总耗时分别为其 {slowdown['uniform']:.2f}、{slowdown['gaussian']:.2f} 和 {slowdown['anisotropic']:.2f} 倍。"
                "在本次小规模网格上，学习初始步长未带来端到端加速。")
    paper=rf'''# 机器学习辅助的二维变分移动网格优化

基于初始步长预测的数值实验

作者：________　学号：________　课程：机器学习课程设计

**摘要：** 针对二维变分网格梯度优化中的步长选择问题，本文复用 Winslow 离散能量、解析梯度与逆映射，构建带合法性和 Armijo 充分下降检查的随机森林步长预测方法。采用完整网格实例划分，利用传统线搜索轨迹训练模型，并在均匀、高斯及各向异性三类度量下，与固定步长、标准 Armijo 和热启动策略比较。九个未见实例的三十六次运行均达到相同相对梯度阈值，最终网格无翻转。学习方法虽减少部分能量评价，推理开销却使总耗时高于传统方法。结果说明评价次数减少并不等于实际加速，小型网格应优先采用低开销步长策略。

**关键词：** 变分网格；随机森林；Armijo 线搜索；步长预测；数值实验

## 1 引言

移动网格在保持节点数量和连接关系的条件下调整节点位置，使计算资源向局部变化较强的区域集中。变分方法通过最小化网格泛函确定坐标映射；不同泛函对网格的集中、形状与边界约束有不同响应[1]。本文关注其中一个有限而明确的问题：在能量和下降方向固定时，能否利用机器学习选择更合适的线搜索初始步长？

学习线搜索已有相关研究。Kamandi 使用循环模型预测步长和退缩因子[2]；Wu 等将回归模型用于变分网格中的流场估计[3]。本文仅使用一个随机森林预测初始步长，通过小规模对照实验检验其必要性和实际成本。实验复用本地已有数值模块，所有图表均由保存的数值轨迹生成。

## 2 方法

### 2.1 离散能量与坐标角色

设固定物理顶点为 $X$，计算顶点为 $Q$，参考顶点为 $\widehat Q$。单元边矩阵分别为 $E_K=[x_1-x_0,x_2-x_0]$ 和 $B_K=[q_1-q_0,q_2-q_0]$，令 $J_K=B_KE_K^{{-1}}$。固定物理单元面积和单元中心度量后，使用

$$
I_h(Q)=\sum_K |K|\,\operatorname{{tr}}(J_K M_K^{{-1}}J_K^T).
$$

该能量对应[1]式(6)的离散形式，省略了常数因子 $1/2$，梯度与步长均按本实现定义。令 $C_K=E_K^{{-1}}M_K^{{-1}}E_K^{{-T}}$，则单元对边矩阵的导数为 $2|K|B_KC_K$；两列分别装配到顶点1和2，负的列和装配到顶点0。固定边界节点的梯度投影为零。计算过程中 $X$、$|K|$ 和 $M_K$ 不变，最终物理网格由分片线性映射 $\Phi_h:Q\mapsto X$ 在 $\widehat Q$ 上求值得到。

<!-- pagebreak -->

### 2.2 共同的下降与合法性条件

记投影梯度为 $g_k$。四种方法均沿 $-g_k$ 更新计算坐标，候选步为 $Q_k-\alpha g_k$。Armijo 条件为

$$
I_h(Q_k-\alpha g_k)\le I_h(Q_k)-c_1\alpha\|g_k\|_2^2,\qquad c_1=10^{{-4}}.
$$

首先检查候选计算网格的定向面积，再计算候选能量和梯度；充分下降满足后重建物理网格，检查所有物理三角形的定向面积。两类面积均须大于 $10^{{-12}}$。线搜索失败时，Armijo、热启动和随机森林方法以 $\beta=1/2$ 退缩；随机森林搜索耗尽可回退到默认初值。固定步长为0.05，不作回溯，若不能满足同样的接受条件则终止并记录失败。

停止条件统一为

$$
\|g_k\|_2\le\max(10^{{-7}},10^{{-4}}\|g_0\|_2).
$$

每次运行最多1800次接受迭代、30000次能量评价；每轮回溯最多40次。计算网格边界始终固定，重建物理网格边界位移仅有插值舍入误差。记录成功和失败运行，比较采用相同网格、相同精度和相同预算。

### 2.3 随机森林和数据划分

以标准 Armijo 接受的 $\log\alpha_k$ 为监督标签。四个可用特征为

$$
z_k=\left[\log(1+\|g_k\|_2),\ \log\alpha_{{k-1}},\ \log(2n^2 A_{{\min,k}}),\ b_{{k-1}}\right].
$$

其中 $A_{{\min,k}}$ 为当前计算网格最小定向面积，$b_{{k-1}}$ 为上一步拒绝候选数，初值为 $\alpha_{{-1}}=1$、$b_{{-1}}=0$。森林含32棵树，最大深度10，叶节点最少5个样本，固定随机种子20261020，单线程预测。预测值经指数和裁剪得到 $\alpha_0=\operatorname{{clip}}(\exp f(z_k),10^{{-12}},1)$。

训练集为每类8个实例，共24条完整轨迹；验证集为每类2个，共6个实例；测试集为每类3个，共9个实例。训练、验证和测试种子分别为0–7、80–81、100–102。训练和验证网格取 $n\in\{{8,10,12\}}$，测试统一 $n=12$。模型使用 {info['train_samples']} 个训练步骤和 {info['validation_samples']} 个验证步骤；同一实例的全部步骤仅属于一个集合。超参数固定，不根据测试结果选择。

算法流程：生成传统轨迹 → 按实例分组 → 训练森林 → 读取当前状态并预测初值 → 检查计算网格 → 检查充分下降 → 重建并检查物理网格 → 接受或回溯 → 记录日志。

### 2.4 基本数学核验

原模块的单元手算能量、解析梯度方向差分、恒等重建及能量与正面积测试共5项通过。本项目再对三类度量各取两个随机合法网格进行中心差分，步幅 $10^{{-5}}$，最大相对误差为 {err:.2e}，并检查负梯度小步下降。每个接受步执行下降、有限值和边界检查；数据划分执行实例集合不相交断言。

<!-- pagebreak -->

## 3 数值实验

### 3.1 环境、参数与计时口径

实验在本地 Windows 环境运行，Python {protocol['python']}、NumPy {protocol['numpy']}、scikit-learn {protocol['sklearn']}，使用CPU。完整依赖版本保存于环境记录。几何与优化为 NumPy 运算，森林使用 scikit-learn，不依赖GPU或完整PDE系统。

区域为单位正方形，先将每个方格剖分成两个正定向三角形，得到 $n=12$ 时169个顶点和288个单元。每个内部物理顶点的两个坐标独立均匀扰动，范围为 $[-0.12/n,0.12/n]$；边界不动。计算初值为规则参考网格。同一实例四种方法使用完全一致的输入。按种子轮换运行顺序，减轻固定顺序影响。

表1　三类算例的共同构造

|算例|单元中心度量|目的|
|---|---|---|
|均匀|$M=I$|扰动平滑与稳定性|
|高斯|$M=(1+w)I$|局部节点集中|
|各向异性|$M=I+wvv^T$|定向变形|

这里 $w=s\exp(-\|x-c\|^2/(2\sigma^2))$，$\sigma=0.17$，$s$ 在[3,7]中采样，中心两个坐标在[0.43,0.57]中采样，$v=(\cos(\pi/6),\sin(\pi/6))^T$。高斯度量特征值均为 $1+w$，各向异性度量特征值为1和 $1+w$，因而所有输入度量均正定。具体参数逐实例保存在配置文件中。

总耗时覆盖能量对象初始化、特征提取、模型推理、候选检查、梯度计算、网格重建及相同的历史记录工作；不包含实例生成、文件写入和训练。能量评价计数包含初始能量，每次调用复用接口同时获得能量与梯度，拒绝候选的梯度也计入成本。面积检查拒绝的候选不计能量评价；回溯数统计被拒绝的候选，因此二者不能简单互换。搜索耗时包含网格重建，不等同于重复能量评价的纯成本。

### 3.2 算例一：均匀度量

![图1　均匀度量的初始及最终物理网格；展示种子固定为100，所有图均由保存的顶点坐标绘制。](../figures/mesh_uniform.png)

规则参考构型对均匀度量接近平衡。四种策略均消除初始随机扰动，最终能量均接近2。森林改变的是到达平衡的路径，而非平衡网格。该例用于检查基本行为，也检验低成本目标函数是否适合增加预测开销。

<!-- pagebreak -->

### 3.3 算例二：局部高斯度量

![图2　高斯度量下的物理网格。相同初值经标准 Armijo 与随机森林策略优化，均在中心附近形成较密网格。](../figures/mesh_gaussian.png)

展示实例的度量中心约为 $({geometry['gaussian']['center'][0]:.4f},{geometry['gaussian']['center'][1]:.4f})$。以该中心为圆心、半径0.2的圆内，初始节点数{geometry['gaussian']['initial_center_node_count']}，随机森林结果为{geometry['gaussian']['final_center_node_count']}。局部集中来自给定度量和能量最小化，不能归因于森林预测本身；标准 Armijo 也获得几乎相同的网格。圆内计数仅作几何描述，不代表PDE误差降低。

### 3.4 算例三：光滑各向异性度量

![图3　各向异性度量下的物理网格。固定方向与局部强度变化共同导致定向变形，四周边界保持固定。](../figures/mesh_anisotropic.png)

本例在平滑权重上增加秩一方向项，观察局部网格的方向响应。中心圆内节点数从{geometry['anisotropic']['initial_center_node_count']}变为{geometry['anisotropic']['final_center_node_count']}。用单元边矩阵的奇异值比作描述时，全域平均由{geometry['anisotropic']['initial_edge_condition_mean']:.3f}变为{geometry['anisotropic']['final_edge_condition_mean']:.3f}：该指标受三角形顶点编号和原始剖分影响，不能将视觉拉伸直接解释为整体质量改善。这里更直接的证据是单元位置、朝向和能量的实际变化。三个展示实例均预先采用测试种子100，完整九个测试实例全部保留。

<!-- pagebreak -->

### 3.5 四种方法的共同精度比较

表2　三次独立测试实例的算术平均；所有行均3/3收敛，固定步长为0.05

{table}

![图4　三个展示实例的离散能量随接受迭代数变化；各面板使用各自能量尺度。](../figures/energy.png)

三十六次运行全部达到共同梯度阈值，最终物理网格的翻转单元总数为 {all_flip}，所有测试运行最终最小物理定向面积的最小值为 {all_min:.3e}。同一实例不同方法的最终能量非常接近，表中小差异来自停止阈值及数值路径。相对能量降幅、最终梯度范数、计算与物理最小面积均在原始结果表中逐次保存。

森林在均匀、高斯和各向异性算例分别平均执行 {get('uniform','rf','backtracks'):.1f}、{get('gaussian','rf','backtracks'):.1f} 和 {get('anisotropic','rf','backtracks'):.1f} 次回溯。热启动仅在必要时缩小历史步长，成本很低，但不能主动增大步长，可能增加迭代数。固定步长虽无回溯，其收敛过程需要较多迭代，因此评价次数最少或回溯最少都不足以单独判断方法优劣。

<!-- pagebreak -->

## 4 结果讨论

### 4.1 评价节省与时间成本

![图5　能量评价次数及总耗时，误差棒为三个独立实例的样本标准差。](../figures/cost.png)

{conclusion} 森林在三个算例上也均慢于热启动。其特征提取与推理占森林求解总耗时的 {rf_fraction:.1f}%。对288个单元，NumPy 的能量计算较便宜，逐步调用森林的固定开销超过节省的候选检查成本。

表3　总耗时的均值与样本标准差，单位：秒

{timing_table}

### 4.2 模仿标签与预测质量

![图6　独立验证实例的对数步长预测及森林的特征重要性；重要性是模型内的杂质下降统计。](../figures/model.png)

验证集对数步长 MAE 为 {info['validation_log_mae']:.4f}，$R^2={info['validation_log_r2']:.4f}$；直接使用前一步对数步长的 MAE 为 {info['validation_previous_log_alpha_mae']:.4f}。负 $R^2$ 表示预测弱于使用验证标签均值的常数预测。训练标签标准差为 {info['train_label_log_std']:.4f}，森林未建立强预测优势。标签来自固定初值及二分回溯，是教师算法的离散选择，既不是最大可行步长，也不是耗时最优标签。

<!-- pagebreak -->

### 4.3 局限

本实验只有三个度量家族，每类三个未见实例；训练与测试来自相同参数区间，不能推断跨家族或大规模泛化。森林在自身优化轨迹上访问的状态可能偏离教师数据，实例隔离并不能消除这种分布变化。当前报告为一次完整批量运行；误差棒表示实例间差异，并非同一实例多次计时的测量置信区间。运行时间还受本机后台负载影响，稳定可复核的指标是配置、轨迹、评价计数和停止条件。

所有比较使用同一个冻结物理网格上的二次能量，没有外层度量更新；固定边界限制了可达到的变形。定向面积检查是每个离散候选的实际验收条件，不是任意输入下的非退化定理。这里比较简化显式梯度法的线搜索，不是对2015年论文中 ode15s 求解器的直接加速，也没有实现[2]的循环模型或[3]的CFD流程。

教师数据生成耗时 {info['data_generation_seconds']:.3f} 秒，模型拟合耗时 {info['training_seconds']:.3f} 秒；二者单列，不并入测试求解时间。由于本次推理阶段本身没有时间收益，当前测量不存在可摊平训练成本的正复用次数。是否能在更大规模或更昂贵的能量上获益，需要另外的对照实验，而不是由评价次数减少推断。

## 5 结论

本课程设计完成了一条可复现的轻量机器学习数值实验流程：复用解析能量与梯度，生成传统轨迹，按完整实例训练与验证随机森林，并在三个二维算例上与三种传统策略比较。全部测试运行达到同一梯度标准且网格保持正定向；高斯度量产生明确的局部集中，说明优化与映射流程在这些实例上工作正常。

实验支持两个结论：第一，安全层允许预测步长参与迭代而保持本批次接受步的充分下降和网格合法性；第二，在本次小网格与实现条件下，节省能量评价不足以补偿随机森林开销。实际使用应优先选择简单 Armijo 或热启动，并根据求解总成本判断学习模块是否值得加入。

## 参考文献

{references}

**数据与复现：** 项目包含完整配置、训练划分、逐步轨迹、测试结果表、网格坐标、模型和绘图代码。运行 `python scripts/reproduce.py` 可重建实验、图表、报告及汇报页；报告数值由结果文件自动读取，全部运行记录均纳入统计。
'''
    (ROOT/'paper/paper.md').write_text(paper,encoding='utf-8')
    presentation=rf'''# 随机森林能让网格优化更快吗？

机器学习课程设计 · 二维变分网格 · 课堂讲解约7分钟

## 1 研究问题：少算几次，是否就更快？

在169个顶点、288个三角形的小网格上，预测一个初始步长能否减少线搜索成本？我们训练了随机森林，在三个度量场、九个未见实例上完成四种方法共36次测试。全部达到共同精度，最终网格无翻转。

**实测结论：评价次数下降，总耗时上升。** {conclusion}

## 2 网格怎样移动：能量与逆映射

物理网格 $X$ 固定，优化计算网格 $Q$，再通过分片线性逆映射在规则参考顶点上求值，获得新的物理网格。

$$
I_h(Q)=\sum_K|K|\,\operatorname{{tr}}(J_KM_K^{{-1}}J_K^T),\qquad J_K=B_KE_K^{{-1}}.
$$

这是已有 Winslow 离散能量的简化梯度优化比较。原模块五项测试通过，六次新增方向差分的最大相对误差 {err:.2e}。

## 3 森林只提议步长，接受条件统一

标准 Armijo 从1开始；热启动从前一步接受步长开始；固定步长0.05；随机森林用4个当前可用特征预测对数步长。所有方法必须通过同样的网格和充分下降检查。

$$
Q_{{k+1}}=Q_k-\alpha_k g_k,\qquad
I_h(Q_{{k+1}})\le I_h(Q_k)-10^{{-4}}\alpha_k\|g_k\|^2.
$$

计算与重建物理三角形的定向面积须大于 $10^{{-12}}$。森林预测不满足条件时按 $1/2$ 退缩，必要时回退默认初值。

## 4 实验设置：按完整实例隔离

训练24个、验证6个、测试9个完整实例，训练步骤 {info['train_samples']} 条。每个实例的所有步骤只进入一个集合；三类度量各有3个测试种子，四种方法从相同初始网格出发。随机森林32棵树、深度10，固定随机种子，未用测试结果调参。

停止条件统一为 $\|g_k\|\le\max(10^{{-7}},10^{{-4}}\|g_0\|)$。推理、特征提取和网格重建都计入求解耗时；教师数据生成与训练成本单列。

## 5 三个算例：实际网格发生了什么？

### 均匀度量：恢复规则

![均匀度量：初始、Armijo、随机森林](../figures/mesh_uniform.png)

### 高斯度量：局部集中

![高斯度量：初始、Armijo、随机森林](../figures/mesh_gaussian.png)

中心圆内节点数{geometry['gaussian']['initial_center_node_count']} → {geometry['gaussian']['final_center_node_count']}。集中由度量和能量驱动，两种方法得到接近的平衡网格。

### 各向异性：局部定向变形

![各向异性度量：初始、Armijo、随机森林](../figures/mesh_anisotropic.png)

固定方向 $v=(\cos(\pi/6),\sin(\pi/6))$，正定度量 $M=I+wvv^T$。图中均为预先固定的展示种子100，完整测试结果全部保留。

## 6 方法比较：评价更少，时间更长

![评价次数与时间；三实例均值，误差棒为样本标准差](../figures/cost.png)

{table}

![展示实例的能量下降曲线](../figures/energy.png)

随机森林总耗时中的 {rf_fraction:.1f}% 用于特征与预测。小型目标函数很便宜，省下的候选评价抵不过预测成本。热启动无需训练，也显著减少回溯。

## 7 机器学习表现：标签与预测都要检查

![验证集步长预测与特征重要性](../figures/model.png)

验证 MAE={info['validation_log_mae']:.4f}，$R^2={info['validation_log_r2']:.4f}$；直接沿用上一步的 MAE={info['validation_previous_log_alpha_mae']:.4f}。负 $R^2$ 说明森林弱于标签均值预测。教师标签是二分回溯的接受步长，不是最优步长。数据生成 {info['data_generation_seconds']:.2f}s，训练 {info['training_seconds']:.2f}s；当前没有时间收益可摊平训练成本。

## 8 结论、局限与复现入口

实际选择：本实验优先简单 Armijo 或热启动；不能只凭少了多少次函数评价判断加速。

局限：每类只有3个未见实例；同分布测试；一次批量计时；冻结度量；没有PDE误差比较。本实验是显式梯度优化的对照，不是原论文 ode15s 的直接加速。

离线查看：同目录 `report.html`；完整论文在项目 `paper/paper.pdf`；数据在 `data/results.csv`；从项目根目录运行 `python scripts/reproduce.py` 复现。浏览时可使用 PageDown/PageUp、Home/End 滚动，顶部 More 菜单提供原生成器的打印功能。

## 9 参考资料

{references}
'''
    (ROOT/'presentation/talk.md').write_text(presentation,encoding='utf-8')
    (ROOT/'references.md').write_text('# 参考文献与核查\n\n'+references+'''

核查日期：2026-10-20。[1] arXiv 书目页与本地PDF第3–6页（PDF页码）核对逆映射和能量，式(6)含1/2，本实现省略该常数并相应使用自身梯度。[2] 直接读取期刊HTML的 citation 元信息和正文：作者 Ahmad Kamandi，在线日期2026-08-18，Articles in Press / Corrected Proof，卷期页码为空。只据此引用相关研究方向，不外推其效果。[3] SciOpen 页面核对全部五位作者、期卷页和 DOI，正式期次2022-03，页面另记2021年在线日期。

用途：[1] 网格泛函与几何离散背景；[2] 学习线搜索的相关工作；[3] 机器学习参与变分网格的相关工作。三者的实验结果均未作为本项目的数值证据。
''',encoding='utf-8')
    (ROOT/'results_summary.md').write_text('# 实测结果\n\n'+conclusion+'\n\n'+table+'\n\n'+timing_table+
        f'\n36/36达到共同精度，最终翻转单元0。验证MAE={info["validation_log_mae"]:.6f}，R²={info["validation_log_r2"]:.6f}，前一步基线MAE={info["validation_previous_log_alpha_mae"]:.6f}。\n\n'+
        '局限：三类小型度量、每类三个未见实例、一次批量计时、同参数分布、冻结度量；不包含PDE求解、跨家族泛化或原论文求解器加速。没有失败测试运行；受保护的预测均经实际合法性和下降检查。',encoding='utf-8')
    # The Markdown is the common source for both editable text and PDF typography.
    (ROOT/'paper/paper.tex').write_text(to_tex(paper),encoding='utf-8')
    write_json(ROOT/'data/report_values.json',dict(savings_percent=savings,slowdown=slowdown,
        rf_proposal_percent=rf_fraction,minimum_final_physical_area=all_min,final_flipped_cells=all_flip,
        gradient_check_max_error=err))

def text_tex(text):
    def escape(s):
        s=s.replace('\\',r'\textbackslash{}')
        for a,b in [('&',r'\&'),('%',r'\%'),('#',r'\#'),('_',r'\_')]: s=s.replace(a,b)
        return s.replace('→',r'$\to$')
    # Inline math is copied unchanged; prose escapes TeX-special characters.
    parts=re.split(r'(\$[^$]+\$)',text)
    out=''.join(p if p.startswith('$') else escape(p) for p in parts)
    out=re.sub(r'\*\*(.+?)\*\*',r'\\textbf{\1}',out)
    out=re.sub(r'`([^`]+)`',lambda m:r'\texttt{'+m[1]+'}',out)
    out=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',lambda m:r'\href{'+m[2]+'}{'+m[1]+'}',out)
    return out

def to_tex(markdown):
    header=r'''\documentclass[UTF8,a4paper,zihao=5,fontset=fandol]{ctexart}
\usepackage[margin=21mm,top=19mm,bottom=19mm]{geometry}
\usepackage{amsmath,amssymb,graphicx,booktabs,array,caption,xcolor,adjustbox}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small 机器学习课程设计}\fancyhead[R]{\small 二维变分网格与步长预测}
\fancyfoot[C]{\thepage}\setlength{\headheight}{15pt}
\setlength{\parskip}{3pt}\linespread{1.12}
\ctexset{section={format=\large\bfseries,beforeskip=8pt,afterskip=4pt},subsection={format=\normalsize\bfseries,beforeskip=6pt,afterskip=3pt}}
\captionsetup{font=small,labelformat=empty,hypcap=false,skip=3pt}
\setlength{\emergencystretch}{1em}
\begin{document}
'''
    lines=markdown.splitlines(); result=[header]; i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line: result.append('\n');i+=1;continue
        if line=='<!-- pagebreak -->': result.append(r'\newpage'+'\n');i+=1;continue
        if line=='$$':
            j=i+1
            while lines[j].strip()!='$$':j+=1
            result.append('\\[\n'+'\n'.join(lines[i+1:j])+'\n\\]\n');i=j+1;continue
        if line.startswith('# '):
            result.append(r'\begin{center}{\LARGE\bfseries '+text_tex(line[2:])+r'}\end{center}'+'\n');i+=1;continue
        if line.startswith('## '):result.append(r'\section*{'+text_tex(line[3:])+'}\n');i+=1;continue
        if line.startswith('### '):result.append(r'\subsection*{'+text_tex(line[4:])+'}\n');i+=1;continue
        if line.startswith('!['):
            m=re.match(r'!\[(.*?)\]\((.*?)\)',line)
            result.append(r'\begin{center}\includegraphics[width=\linewidth]{'+m[2]+r'}\captionof{figure}{'+text_tex(m[1])+r'}\end{center}'+'\n');i+=1;continue
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                if not re.match(r'^\|[\s:|\-]+\|$',lines[i].strip()):
                    block.append([s.strip() for s in lines[i].strip().strip('|').split('|')])
                i+=1
            wide=len(block[0])>=5
            start=(r'\begin{center}\small\resizebox{\linewidth}{!}{' if wide else
                   r'\begin{center}\small\begin{adjustbox}{max width=\linewidth}')
            result.append(start+r'\begin{tabular}{'+'l'*len(block[0])+r'}\toprule'+'\n')
            for j,row in enumerate(block):
                result.append(' & '.join(text_tex(c) for c in row)+r' \\'+'\n')
                if j==0:result.append(r'\midrule'+'\n')
            result.append(r'\bottomrule\end{tabular}'+('}' if wide else r'\end{adjustbox}')+r'\end{center}'+'\n');continue
        result.append(text_tex(line)+'\n\n');i+=1
    result.append(r'\end{document}')
    return ''.join(result)

if __name__=='__main__':main()
