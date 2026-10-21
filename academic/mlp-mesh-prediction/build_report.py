"""Rewrite the inherited report and classroom narrative from new measured results."""
import json
import numpy as np
from src.common import ROOT,load_config,read_csv,write_json
from src.paper_template import to_tex

STAGE=dict(initial='初始网格',teacher='传统参考',prediction='MLP安全预测',refined='MLP后精修')
CASE=dict(center='中心加密',shifted='偏心加密',strength='强度与宽度变化')

REFERENCES='''[1] Huang W., Kamenski L., Russell R. D. A comparative numerical study of meshing functionals for variational mesh adaptation. Journal of Mathematics Study, 2015, 48(2):168–186. DOI:10.4208/jms.v48n2.15.04. [原文入口](https://arxiv.org/abs/1503.04709)。

[2] Song W., Zhang M., Wallwork J. G., et al. M2N: Mesh Movement Networks for PDE Solvers. Advances in Neural Information Processing Systems, 35, 2022. DOI:10.52202/068431-0522. [会议原文](https://proceedings.neurips.cc/paper_files/paper/2022/hash/2f88d8061f12abae9d14d376fd69c933-Abstract-Conference.html)。

[3] Wang Z., Chen X., Wang Q., et al. UGM2N: An Unsupervised and Generalizable Mesh Movement Network via M-Uniform Loss. Advances in Neural Information Processing Systems, 38, 2025. DOI:10.52202/085713-1885. [会议原文](https://proceedings.neurips.cc/paper_files/paper/2025/hash/5170d42c38539462236b23e03808068c-Abstract-Conference.html)。'''

def main():
    cfg=load_config()
    metrics=read_csv(ROOT/'results/metrics.csv')
    aggregate=read_csv(ROOT/'results/aggregate.csv')
    evaluation=json.loads((ROOT/'results/evaluation_summary.json').read_text(encoding='utf-8'))
    training=json.loads((ROOT/'models/training_summary.json').read_text(encoding='utf-8'))
    dataset=json.loads((ROOT/'data/dataset_summary.json').read_text(encoding='utf-8'))
    smoke=json.loads((ROOT/'data/smoke_report.json').read_text(encoding='utf-8'))
    pred=next(r for r in aggregate if r['stage']=='prediction')
    refined=next(r for r in aggregate if r['stage']=='refined')
    teacher=next(r for r in aggregate if r['stage']=='teacher')
    def m(case,stage):
        return next(r for r in metrics if r['instance_id']==f'case_{case}' and r['stage']==stage)
    summary_table='|状态|位移相对误差|能量相对差|最小面积均值|评价次数|在线时间/s|\n|---|---:|---:|---:|---:|---:|\n'
    for row in aggregate:
        summary_table+=f"|{STAGE[row['stage']]}|{float(row['relative_displacement_error_mean']):.5f}|{float(row['relative_energy_gap_mean']):.2e}|{float(row['min_area_mean']):.3e}|{float(row['energy_evaluations_mean']):.1f}|{float(row['seconds_mean']):.5f}|\n"
    case_table='|算例|预测误差|精修误差|传统迭代|精修迭代|传统时间/s|混合时间/s|\n|---|---:|---:|---:|---:|---:|---:|\n'
    energy_table='|算例|初始状态|传统状态|预测状态|精修状态|\n|---|---:|---:|---:|---:|\n'
    for case in CASE:
        p,t,r=m(case,'prediction'),m(case,'teacher'),m(case,'refined')
        case_table+=f"|{CASE[case]}|{float(p['relative_displacement_error']):.4f}|{float(r['relative_displacement_error']):.2e}|{t['iterations']}|{r['iterations']}|{float(t['seconds']):.4f}|{float(r['seconds']):.4f}|\n"
        energy_table+='|'+CASE[case]+'|'+'|'.join(f"{float(m(case,s)['energy']):.8f}" for s in STAGE)+'|\n'
    test_error=float(pred['relative_displacement_error_mean'])
    refined_error=float(refined['relative_displacement_error_mean'])
    ratio=evaluation['ratio_of_mean_times']
    speed_text=(f"混合方法的平均在线耗时为传统方法的{1/ratio:.3f}倍，按均值比计算的加速比为{ratio:.2f}。"
                if ratio>1 else f"混合方法的平均在线耗时为传统方法的{1/ratio:.3f}倍，本批次未获得在线加速。")
    conclusion=(f"独立测试集原始物理预测平均相对位移误差为{evaluation['test']['mean_raw_relative_error']:.2%}，"
                f"安全/状态转换后为{test_error:.2%}，精修后为{refined_error:.2e}；"
                f"安全预测合法率为{evaluation['test']['safe_legal_rate']:.1%}。"+speed_text)
    refined_runs=[r for r in metrics if r['stage']=='refined']
    n_refined_converged=sum(r['converged']=='True' for r in refined_runs)
    raw_legal=evaluation['test']['raw_legal_rate']
    transfer=evaluation['test']['max_transfer_relative_change']
    offline=dataset['teacher_solve_seconds']+training['training_seconds']
    saving=evaluation['teacher_mean_seconds']-evaluation['hybrid_mean_seconds']
    amortization=(f"以本次均值差作粗略估算，需要约{int(np.ceil(offline/saving))}次同分布在线调用才能摊平这批教师求解和拟合成本。"
                  if saving>0 else "本次在线阶段没有时间收益，因此不能给出可摊平离线成本的正调用次数。")
    paper=rf'''# 基于多层感知机的二维变分自适应网格预测与数值实验

作者：________　学号：________　课程：机器学习课程设计

**摘要：** 本文以传统变分网格为教师，研究固定拓扑二维网格的快速预测。小型MLP以四个高斯度量参数为输入，直接预测内部物理节点位移，并结合合法性检查、坐标状态转换及同目标精修。200个独立实例按140/30/30划分，另设三个展示算例。测试原始预测平均相对误差为{evaluation['test']['mean_raw_relative_error']:.2%}，状态转换后为{test_error:.2%}，网格全部合法。精修后误差降至{refined_error:.2e}，包含预测与预处理的在线流程平均耗时为传统方法的{1/ratio:.3f}倍。结果显示该问题族内存在预测与初值收益，同时需计入插值误差和离线成本。

**关键词：** 自适应网格；多层感知机；变分方法；位移预测；监督学习

## 1 引言

移动网格在不增加节点数量、不改变连接关系的条件下调整节点位置，使网格向指定区域集中。变分方法通过最小化网格泛函确定坐标映射，数值结果取决于度量、边界和离散方式[1]。对于需要反复处理相近参数场的问题，传统优化每次都从规则网格出发，可能重复执行相似的坐标调整。本课程设计考察能否学习参数与优化后物理节点之间的关系，并将预测用于直接近似或优化初值。

M2N研究了基于传统参考网格的监督网格移动[2]；UGM2N从无监督几何目标研究网格生成与泛化[3]。本文采用固定方形区域、固定顶点编号和一个小型全连接网络，教师为本地已有的Winslow变分网格实现。目标是验证小规模参数族内的可行性、误差和成本，而非复现上述完整网络或求解系统。

## 2 数学与学习方法

### 2.1 冻结物理网格上的变分教师

初始物理节点为 $X_0$，规则参考节点为 $\widehat Q$，计算节点为 $Q$。三者共享连接数组。单元边矩阵 $E_K=E_K(X_0)$、$B_K=B_K(Q)$，Jacobian 为 $J_K=B_KE_K^{{-1}}$。本实现采用

$$
I_h(Q;\mu)=\sum_K |K(X_0)|\,\operatorname{{tr}}(J_K M_K(\mu)^{{-1}}J_K^T).
$$

这是[1]式(6)的几何离散形式，省略常数因子 $1/2$。物理面积和度量在内迭代中冻结，梯度对计算节点求导。设 $C_K=E_K^{{-1}}M_K^{{-1}}E_K^{{-T}}$，对边矩阵的导数为 $2|K|B_KC_K$，再按顶点装配并将边界梯度投影为零。教师最终物理网格为 $X_T=R(Q_T)$，其中 $R$ 是原有分片线性逆映射在参考节点处的求值；训练标签取 $X_T-X_0$ 的内部节点部分。

<!-- pagebreak -->

### 2.2 参数族、网络及损失

区域为 $[0,1]^2$，每轴12个方格，固定剖分为288个三角形，共169个节点，其中内部121个。所有样本使用相同的规则初始网格，输入仅为 $\mu=(c_x,c_y,A,\sigma)$。度量在初始物理单元中心评价：

$$
M_\mu(x,y)=\left[1+A\exp\left(-\frac{{(x-c_x)^2+(y-c_y)^2}}{{\sigma^2}}\right)\right]I_2.
$$

两特征值均大于等于1。采样范围为 $c_x,c_y\in[0.30,0.70]$、$A\in[2,8]$、$\sigma\in[0.18,0.30]$。MLP结构为 $4\to64\to64\to242$，两隐层使用Tanh，共{training['parameters']}个参数。输入按训练集均值和标准差标准化，位移除以训练集位移分量的全局均方根。训练损失为

$$
L=\frac{{1}}{{2N_{{\rm int}}}}\sum_{{i\in\mathcal I}}\|\Delta X_i^{{\rm pred}}-\Delta X_i^T\|_2^2.
$$

实际训练对归一化位移计算上述MSE，曲线同时还原原坐标尺度。使用Adam、学习率0.001、批量32、权重衰减 $10^{{-6}}$，最多2600个epoch；连续200个epoch验证误差未改善即早停，保留最佳验证权重。边界位移不由网络预测，直接复制初始边界。训练与模型选择均不读取测试标签。

### 2.3 安全预测与一致状态精修

网络输出物理位移。先从 $X_0$ 沿该位移取 $\tau=1,1/2,\ldots$ 的候选，逐一检查有限值、固定边界、区域范围和全部三角形面积大于 $10^{{-10}}$。若不能通过则回退到 $X_0$，原始非法率、退缩次数和回退率均保留。

精修需要计算坐标初值。对合法物理候选 $P$，用其三角剖分上的“物理节点到参考节点”线性映射在固定 $X_0$ 上插值，定义 $Q_P=C(P)$；再计算 $X_P=R(Q_P)$。对 $Q_P$、$X_P$ 均检查合法性，不满足则继续位移退缩。四状态比较中的“MLP安全预测”指这个与计算状态一致的 $X_P$，同时保存转换前 $P$ 并报告转换误差。该插值往返不是精确求逆，也没有使用教师坐标修正预测。

传统与精修均最小化同一 $I_h(Q;\mu)$，使用固定初值1的Armijo回溯，退缩因子1/2、充分下降系数 $10^{{-4}}$。接受计算候选后还检查重建物理网格。两者共同采用绝对停止条件 $\|g\|_2\le10^{{-5}}$，最多2200次接受迭代、30000次能量评价。精修从 $Q_P$ 出发，不把物理节点直接放入计算节点接口。

<!-- pagebreak -->

## 3 数据与数值实验

### 3.1 教师核验与实例划分

沿用的能量、梯度和逆映射具有单元手算、方向差分、恒等映射及网格合法性测试。本次新增五项检查覆盖高斯问题族的梯度、固定拓扑、初值转换、非法位移退缩和非有限预测回退。先运行24个随机教师实例，{smoke['converged']}/24收敛、{smoke['valid']}/24合法，物理位移非零且标签随参数变化，再扩充正式数据。

正式数据含200个随机参数实例及三个固定展示实例，共{dataset['instances']}次独立教师求解，其中{dataset['successful']}次通过收敛和几何检查，失败数{len(dataset['failed'])}，全部结果均保存。随机实例按140/30/30划分训练、验证和测试；同一参数实例整体进入一个集合。展示参数在训练前写入配置，不用于早停或模型选择。随机种子20261021，配置及划分随数据归档。

### 3.2 训练与非平凡移动基线

![图1　训练与验证误差曲线。左为归一化位移MSE，右为原坐标分量RMSE；竖线为最佳验证epoch。](../results/train_curve.png)

本次实际训练{training['epochs']}个epoch，最佳验证epoch为{training['best_epoch']}。验证坐标分量MSE为{training['best_validation_coordinate_mse']:.3e}，不移动网格的对应MSE为{training['no_move_validation_coordinate_mse']:.3e}。教师标签是终点物理位移，迭代中间步骤没有被当作额外独立样本。神经网络只学习固定分辨率、固定拓扑下的参数映射。

运行环境为Windows、Intel Core Ultra 7 155H、Python 3.13.2、NumPy 2.3.4、PyTorch {training['torch_version']}。训练及评测统一CPU单线程。训练时间{training['training_seconds']:.2f}秒，全部教师求解累计{dataset['teacher_solve_seconds']:.2f}秒；二者作为离线成本单列。

<!-- pagebreak -->

### 3.3 算例一：中心局部加密

![图2　中心加密：初始、传统参考、MLP安全预测及预测后精修的物理网格。底色为同一度量标量，十字为峰值中心。](../results/case_center.png)

参数为 $\mu=(0.50,0.50,5.0,0.24)$。安全预测相对位移误差为{float(m('center','prediction')['relative_displacement_error']):.2%}，精修后为{float(m('center','refined')['relative_displacement_error']):.2e}。四张图使用相同坐标范围、节点编号及连通关系，直接比较中心聚集的形状。

### 3.4 算例二：加密区域移动

![图3　偏心加密：峰值中心移至左上方，比较四种状态的局部集中位置与形状。](../results/case_shifted.png)

参数为 $\mu=(0.36,0.64,5.0,0.24)$。安全预测相对位移误差为{float(m('shifted','prediction')['relative_displacement_error']):.2%}，精修后为{float(m('shifted','refined')['relative_displacement_error']):.2e}。该例只改变输入参数，未为偏心位置另行训练网络或调整安全阈值。预测是否贴近教师由全部内部节点误差评价，不以图形相似代替数值误差。

<!-- pagebreak -->

### 3.5 算例三：强度与作用范围变化

![图4　较强、较窄的局部度量下，初始网格与三个生成结果的对照。](../results/case_strength.png)

参数为 $\mu=(0.58,0.43,7.5,0.19)$，仍位于训练参数区间内。安全预测相对误差为{float(m('strength','prediction')['relative_displacement_error']):.2%}，精修后为{float(m('strength','refined')['relative_displacement_error']):.2e}；这检验区间内部响应，不作为分布外泛化证据。

### 3.6 独立测试与能量

相对位移误差定义为 $e_X=\|X-X_T\|_{{\mathcal I}}/\max(\|X_T-X_0\|_{{\mathcal I}},10^{{-14}})$，不移动基线为1。下表为30个独立测试实例的算术均值，能量相对差为 $(I_h-I_h(Q_T))/|I_h(Q_T)|$；能量均评价对应计算状态 $Q$，不是把物理数组直接代入梯度接口。

表1　测试集四状态比较；预测行仅包含生成开销，精修行包含全部在线流程

{summary_table}

表2　三个展示实例的同一冻结状态能量 $I_h(Q)$

{energy_table}

原始MLP物理输出的平均相对位移误差为{evaluation['test']['mean_raw_relative_error']:.2%}，仅几何退缩后为{evaluation['test']['mean_damped_relative_error']:.2%}，再经状态转换后为{test_error:.2%}。原始预测合法率为{raw_legal:.1%}，安全处理后合法率为{evaluation['test']['safe_legal_rate']:.1%}，回退率为{evaluation['test']['fallback_rate']:.1%}。物理候选经状态转换后的相对变化量在测试集中最大为{transfer:.2%}；这部分离散插值误差与网络误差分开记录，转换前后数据均可复核。

<!-- pagebreak -->

## 4 精修成本与结果讨论

![图5　三个展示算例的传统求解与混合流程评价次数及在线耗时；时间误差棒为三次配对运行的样本标准差。](../results/cost_comparison.png)

表3　三个展示实例的精度与成本；时间为三次配对运行均值

{case_table}

![图6　传统与精修的投影梯度范数；虚线是共同的绝对停止阈值。](../results/convergence.png)

独立测试集传统求解平均{evaluation['teacher_mean_seconds']:.4f}秒，直接预测加安全/状态处理平均{evaluation['prediction_mean_seconds']:.4f}秒，完整混合流程平均{evaluation['hybrid_mean_seconds']:.4f}秒。{speed_text} 评估含30个随机测试和三个展示实例，精修中{n_refined_converged}/{len(refined_runs)}次达到共同阈值。单步与累计能量评价计数、回溯次数及梯度范数均保存于逐步记录。

<!-- pagebreak -->

### 4.1 计时与离线摊销

模型预加载后，每次在线计时包含度量及能量对象建立、输入归一化、MLP推理、位移安全退缩、两次插值状态转换和传统精修，不含模型加载、文件读写、指标汇总和离线训练。传统基线包含同样的问题对象建立与优化。每实例重复三次并交替先后顺序。表1的标准差描述测试实例差异，图5误差棒描述同一实例重复计时差异；二者用途不同。

教师与训练离线成本合计约{offline:.2f}秒。{amortization} 该估算依赖本机负载、固定问题族和持续使用场景，不包含未来重新训练或数据整理成本。

### 4.2 局限

本实验仅对固定拓扑、固定分辨率的单高斯正定度量进行同区间预测，不能推断跨网格规模、复杂几何、多峰度量或分布外泛化。MLP监督的是所选传统离散教师的终点，预测误差小不自动意味着PDE误差更小。状态转换为分片线性插值，存在已测量的往返差异；每次候选的正面积和边界检查也不等同于任意网格上的通用非退化定理。

本实现为冻结度量内迭代和显式梯度优化，不包含完整PDE求解或外层度量更新。它没有复现M2N的Monge–Ampère教师或完整网络[2]，也没有实现UGM2N的无监督损失与跨拓扑系统[3]。所有速度、误差和合法率只取自本项目实际运行，不引用文献性能替代实验数据。

## 5 结论

本文以已有变分网格算法产生真实物理网格标签，完成了四参数到242维内部节点位移的小型MLP训练、独立测试及三个四状态可视化算例。{conclusion}

课程实验表明，直接物理位移预测可以作为具有明确误差的近似输出，而同目标精修提供恢复教师精度的途径。实际选择应同时考虑预测偏差、几何合法性、状态转换和训练摊销；在本实验范围之外，需要重新检验上述结论。

## 参考文献

{REFERENCES}
'''
    (ROOT/'paper/report.md').write_text(paper,encoding='utf-8')
    (ROOT/'paper/report.tex').write_text(to_tex(paper),encoding='utf-8')
    write_json(ROOT/'results/report_values.json',dict(test_prediction_error=test_error,
        test_refined_error=refined_error,online_speedup=ratio,offline_seconds=offline,
        amortization_calls=int(np.ceil(offline/saving)) if saving>0 else None))
    write_presentation(cfg,conclusion,summary_table,case_table,training,evaluation,REFERENCES)
    (ROOT/'references.md').write_text('# 核心文献\n\n'+REFERENCES+'''

核查日期：2026-10-21。[1] arXiv核对作者、正式期刊Journal of Mathematics Study、卷期页码及DOI；[2][3] NeurIPS正式会议页面核对题名、作者、年份、卷号和会议页面提供的DOI。正文只引用方法背景，不引用其性能数值作为本实验结果。

[1]提供Winslow泛函及计算/物理映射背景；[2]用于监督网格预测的概念参考；[3]用于无监督几何约束与泛化的背景。本项目的物理标签来自已有Winslow教师，并非Monge–Ampère教师。
''',encoding='utf-8')
    (ROOT/'results_summary.md').write_text('# 实测结果\n\n'+conclusion+'\n\n'+summary_table+
        '\n\n'+case_table+f'\n\n教师实例{dataset["successful"]}/{dataset["instances"]}通过；测试原始合法率{raw_legal:.1%}，安全合法率{evaluation["test"]["safe_legal_rate"]:.1%}，回退率{evaluation["test"]["fallback_rate"]:.1%}。测试转换相对变化最大{transfer:.2%}。'+
        '\n\n局限：固定拓扑、单高斯度量、同区间参数；物理/计算状态转换存在插值误差；无PDE误差或跨拓扑结论。',encoding='utf-8')

def write_presentation(cfg,conclusion,table,cases,training,evaluation,references):
    talk=rf'''# 多层感知机能否直接预测二维自适应网格？

机器学习课程设计 · 四参数输入 · 物理节点位移预测

## 1 问题：重复优化，能否学习一次后直接预测？

固定169个顶点、288个三角形，改变高斯度量的中心、强度和宽度。我们希望从四个参数预测121个内部物理节点的位移，再检验是否需要精修。{conclusion}

## 2 学习框架：教师、预测与精修

![训练与在线流程示意；流程图不是实验网格](../results/workflow.png)

教师优化计算节点 $Q$，最终通过原有逆映射重建物理节点 $X_T$。神经网络标签是物理位移，预测物理数组经过独立状态转换后才能交给原优化器。

$$
\mu=(c_x,c_y,A,\sigma)\ \longrightarrow\ \Delta X_{{\mathcal I}},
\qquad X_T=R(Q_T).
$$

## 3 方法：小型MLP与共同安全检查

网络 $4\to64\to64\to242$，两个Tanh隐层、Adam、验证集早停，边界直接复制初始网格。用训练集拟合归一化。原始预测不合法时，从规则网格沿位移按 $1,1/2,\ldots$ 退缩，实际检查正面积与区域约束。

$$
I_h(Q)=\sum_K |K(X_0)|\,\operatorname{{tr}}(B_KE_K^{{-1}}M_K^{{-1}}E_K^{{-T}}B_K^T).
$$

精修使用同一冻结能量与绝对梯度阈值 $10^{{-5}}$。插值状态转换存在往返误差，相关数值另存，不能把预测物理坐标直接当计算坐标。

## 4 数据：实例隔离，验证非平凡移动

24个教师小样本检查通过后，生成200个独立参数实例，按140/30/30划分；另设三个未见展示实例。教师标签由真实收敛求解产生，完整参数、迭代和失败记录保留。MLP实际训练{training['epochs']}个epoch，最佳验证epoch为{training['best_epoch']}。

![训练与验证误差曲线](../results/train_curve.png)

## 5 三个算例：初始、传统、预测、精修

### 中心加密

![中心加密的四状态物理网格](../results/case_center.png)

### 加密区域移动

![偏心加密的四状态物理网格](../results/case_shifted.png)

### 强度与宽度变化

![强度/宽度变化的四状态物理网格](../results/case_strength.png)

三图参数均在训练区间内，展示组合事先写入配置，未用于调参。底色表示度量标量，红十字是峰值中心；所有图节点、边界、拓扑一致。

## 6 指标：精度、几何和总成本一起看

{table}

{cases}

![评价次数与在线总耗时](../results/cost_comparison.png)

原始MLP物理输出平均相对位移误差{evaluation['test']['mean_raw_relative_error']:.2%}，经安全/状态处理后{evaluation['test']['mean_aligned_relative_error']:.2%}。原始测试预测合法率{evaluation['test']['raw_legal_rate']:.1%}，安全处理后{evaluation['test']['safe_legal_rate']:.1%}，回退率{evaluation['test']['fallback_rate']:.1%}。计时包含推理、安全处理、状态转换和精修；模型加载、教师数据生成与训练为离线成本。

## 7 结论与局限

{conclusion}

固定拓扑、单高斯场、同区间测试；没有跨拓扑、分布外或PDE误差结论。预测是可测误差的近似，精修才与传统终止精度比较。教师来自Winslow能量，未复现M2N或UGM2N的完整系统。

本地打开当前 index.html 可离线汇报；完整论文在 paper/report.pdf，源码和数据均随项目提供。从项目根目录运行 python run_all.py 可完整复现。

## 8 参考文献

{references}
'''
    (ROOT/'presentation/talk.md').write_text(talk,encoding='utf-8')

if __name__=='__main__':main()
