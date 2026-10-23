"""Summarize the completed physical field training experiment."""
from pathlib import Path
import json,csv
import numpy as np

OUT=Path(__file__).resolve().parent


def main():
    done=json.loads((OUT/'completion.json').read_text(encoding='utf8'))
    training=json.loads((OUT/'training_summary.json').read_text(encoding='utf8'))
    preparation=json.loads((OUT/'preparation.json').read_text(encoding='utf8'))
    with (OUT/'test_results.csv').open(encoding='utf-8-sig') as f:
        results=list(csv.DictReader(f))
    with (OUT/'refinements.csv').open(encoding='utf-8-sig') as f:
        refinement=list(csv.DictReader(f))
    text=['# 跨场物理网格网络：首轮训练', '',
        f"网络已完成四类场监督训练，在{done['test_cases']}个未参与训练的场—网格组合上评测，原始预测合法{done['raw_valid']}/{done['test_cases']}。",
        '网络直接预测物理位移，教师由直接物理Huang能量优化生成。结果同时报告教师拟合和Poisson误差。','',
        '## 数据与模型','',
        f"教师生成{preparation['converged']}/{preparation['requested']}收敛。训练{training['train_fields']}场、验证{training['validation_fields']}场、测试48场；每类分别48/12/12场。按场实例划分，测试场的12×12和24×24网格共享同一测试归属。所有四类场均在训练中出现，因此测试新参数和新分辨率，不是未见类别泛化。",'',
        '输入是32×32 log(m)场及待查询节点的参考坐标；场编码器1024→128→64，坐标解码器66→128→128→2，Tanh隐藏层。输出乘16x(1−x)y(1−y)，使位移在边界连续趋零。训练仅使用12×12网格的内部位移，归一化参数及标签尺度只取训练集。','',
        f"参数量{training['parameters']}，CPU单线程训练{training['epochs']}轮，用时{training['seconds']:.1f}秒；依据验证集选择第{done['selected_epoch']}轮，单个训练种子20261026。损失为归一化监督位移MSE，没有把Poisson误差或网格能量加入训练损失。",'',
        '## 独立测试','',
        '相对教师误差按物理教师相对规则网格的位移范数归一化。PDE列为优化/预测网格上Poisson L2误差与同节点数规则网格误差之比，小于1表示改善。PDE评价使用几何合法性处理后的网络输出；原始合法率另外报告。','',
        '|场|网格n|原始合法数|相对教师误差|教师PDE误差比|网络PDE误差比|',
        '|---|---:|---:|---:|---:|---:|']
    names=dict(single='单峰',double='双峰',ring='圆环',wave='波前')
    for r in done['summary']:
        text.append(f"|{names[r['kind']]}|{r['n']}|{r['raw_valid']}/{r['cases']}|{100*r['relative_teacher_error']:.1f}%|{r['teacher_ratio']:.3f}|{r['prediction_ratio']:.3f}|")
    text+=['','![各场与分辨率下的Poisson误差](pde_comparison.png)','',
           '![训练与验证损失](training_curve.png)','',
           '网络对教师的拟合误差与PDE误差是不同指标。预测网格若比教师PDE误差更低，也不能据此认定学习方法已超过传统优化：教师最小化的是网格能量，网络可能因欠拟合而保留更多规则网格特征。','',
           '## 传统精修','',
           '测试清单中每类前两个场、两个分辨率，共16个固定场—网格组合，分别从规则网格和网络初值启动相同L-BFGS。容差10⁻⁵，最多3000迭代和30000能量求值。在线时间包含网络预测及几何处理，PDE后处理与模型加载不计入。','',
           '|初值|收敛数|平均迭代|平均在线秒数|平均PDE误差比|',
           '|---|---:|---:|---:|---:|']
    for method,label in [('regular','规则网格'),('network','网络预测')]:
        group=[r for r in refinement if r['method']==method]
        text.append(f"|{label}|{sum(r['converged']=='True' for r in group)}/{len(group)}|{np.mean([float(r['iterations']) for r in group]):.1f}|{np.mean([float(r['online_seconds']) for r in group]):.4f}|{np.mean([float(r['pde_ratio']) for r in group]):.3f}|")
    speed='无满足条件的配对' if done['paired_speedup'] is None else f"{done['paired_speedup']:.3f}倍"
    text+=['',f"双方均收敛且终点相对能量差≤10⁻⁶的配对为{done['matched_pairs']}/{done['total_pairs']}，其耗时比几何均值为{speed}。未匹配实例全部保留在refinement_pairs.csv，不纳入这个加速数字；它可能意味着落入不同驻点，不能仅按耗时排名。每个组合运行一次，本轮时间结果为探索性测量。",'',
           '## 验证与复现','',
           '准备阶段检查三种数据划分没有重复场实例；每个教师达到梯度容差且网格合法后保存。预测分别保存raw/safe/teacher节点及原始最小面积、退缩系数。Poisson求解沿用已通过仿射检验、正弦制造解收敛检验和右端导数核对的P1实现，并检查每次线性求解残差。','',
           '```powershell',
           'D:/MLMeshCourseTask/.venv/Scripts/python.exe D:/MeshLearningResearch_20261023/mesh-learning-lab/runs/physical_field_training_04/study.py all',
           'D:/MLMeshCourseTask/.venv/Scripts/python.exe D:/MeshLearningResearch_20261023/mesh-learning-lab/runs/physical_field_training_04/report.py',
           '```','',
           'config.json、manifest.json记录配置和所有场；teachers保存336组物理教师及状态；model.pt保存验证集选出的模型；training_log.csv记录训练过程；test_results.csv保存全部96个测试组合；refinements.csv和refinement_pairs.csv保存传统精修对照。','',
           '## 限制','',
           '当前仅一个种子、192个训练场、方形区域、标量度量与固定拓扑；坐标查询能输出不同数量节点，不构成跨尺度精度或正面积保证。教师达到数值驻点，不保证全局最优或更小PDE误差；没有执行UM2N或MMPDElab官方完整基准。几何修复会改变网络预测，原始与修复后的表现需分别解释。','',
           '下一步首先根据本轮原始合法率和各场误差判断主要限制：教师拟合不足时扩大样本或调整表示；预测非法时改进几何约束；教师PDE误差本身较差时改进度量。不能把三类问题都归因于训练轮数不足。']
    (OUT/'README.md').write_text('\n'.join(text)+'\n',encoding='utf8')


if __name__=='__main__':
    main()
