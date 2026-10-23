"""Summarize completed X and Q comparisons from persisted numeric results."""
from pathlib import Path
import csv,json,sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[1]/"src"))
from scale_study import csvout,dump
plt.rcParams["font.sans-serif"]=["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"]=False
GROUPS=["ID","center","narrow","broad"]
NAMES=dict(ID="原分布",center="中心偏移",narrow="窄而强",broad="宽而弱",ALL="全部")
def read(name):return list(csv.DictReader((OUT/name).open(encoding="utf-8-sig")))
def mean(rows,key):return float(np.mean([float(r[key]) for r in rows]))
def main():
    a=read("prediction_aggregate.csv");p=read("prediction_per_case.csv")
    metrics=[]
    for group in GROUPS+["ALL"]:
        for target in ["X","Q"]:
            s=[r for r in a if r["target"]==target and r["group"]==group]
            vals=np.array([float(r["error_relative"]) for r in s])
            metrics.append(dict(group=group,target=target,node_relative_error=float(vals.mean()),
                seed_std=float(vals.std(ddof=1)),raw_legal_rate=mean(s,"raw_legal_rate"),
                interpolation_rmse=mean(s,"interpolation_rmse"),
                teacher_interpolation_rmse=mean(s,"teacher_interpolation_rmse"),
                regular_interpolation_rmse=mean(s,"regular_interpolation_rmse"),
                prediction_ms=1000*mean(s,"predict_seconds"),
                minimum_angle_mean=mean(s,"min_angle"),minimum_quality_mean=mean(s,"min_quality")))
    csvout(OUT/"summary_prediction.csv",metrics)
    r=read("physical_per_case.csv");base=[z for z in r if z["method"]=="regular"]
    paired=[]
    for z in r:
        b=next(v for v in base if v["id"]==z["id"] and v["repeat"]==z["repeat"])
        gap=abs(float(z["final_energy"])-float(b["final_energy"]))/max(1,abs(float(b["final_energy"])))
        comparable=z["converged"]=="True" and b["converged"]=="True" and gap<=1e-6
        paired.append(dict(**z,relative_energy_gap_to_regular=gap,matched_endpoint=comparable,
            paired_speedup=float(b["online_seconds"])/float(z["online_seconds"])))
    csvout(OUT/"physical_paired.csv",paired)
    phys=[]
    for method in ["regular","X_MLP","Q_MLP","nearest_X"]:
        sub=[z for z in paired if z["method"]==method];eq=[z for z in sub if z["matched_endpoint"]]
        ids=sorted(set(z["id"] for z in sub))
        times=[np.median([float(z["online_seconds"]) for z in sub if z["id"]==i]) for i in ids]
        phys.append(dict(method=method,cases=len(ids),converged_cases=sum(
            all(z["converged"]=="True" for z in sub if z["id"]==i) for i in ids),
            mean_case_median_seconds=float(np.mean(times)),mean_iterations=mean(sub,"iterations"),
            mean_final_gradient=mean(sub,"final_gradient_norm"),mean_final_energy=mean(sub,"final_energy"),
            mean_interpolation_rmse=mean(sub,"interpolation_rmse"),
            matched_case_count=len(set(z["id"] for z in eq)),
            matched_speedup=float(np.exp(np.mean(np.log([float(z["paired_speedup"]) for z in eq])))) if eq else None))
    csvout(OUT/"summary_physical.csv",phys)
    fig,axs=plt.subplots(1,3,figsize=(14,4));gx=np.arange(4)
    for t,offset,color in [("X",-.18,"#2563eb"),("Q",.18,"#ed8936")]:
        sub=[next(z for z in metrics if z["group"]==g and z["target"]==t) for g in GROUPS]
        axs[0].bar(gx+offset,[100*z["node_relative_error"] for z in sub],.36,
            yerr=[100*z["seed_std"] for z in sub],label=t+"-MLP",color=color)
        axs[1].bar(gx+offset,[z["interpolation_rmse"] for z in sub],.36,label=t+"-MLP",color=color)
        vals=[1000*float(z["predict_seconds"]) for z in p if z["target"]==t]
        axs[2].bar(t,np.median(vals),color=color)
    for ax in axs[:2]:ax.set_xticks(gx,[NAMES[g] for g in GROUPS]);ax.legend()
    axs[0].set_title("物理节点相对误差（3种子均值±标准差）");axs[0].set_ylabel("%")
    axs[1].set_title("解析函数插值RMSE");axs[2].set_title("在线预测耗时中位数");axs[2].set_ylabel("ms")
    fig.tight_layout();fig.savefig(OUT/"直接预测对比.png",dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4));labels=["规则网格","X-MLP","Q-MLP","最近邻X"]
    axs[0].bar(labels,[z["mean_case_median_seconds"] for z in phys],color=["#64748b","#2563eb","#ed8936","#8b5cf6"])
    axs[0].set_ylabel("秒");axs[0].set_title("同一物理能量精修（含未收敛算例）")
    axs[1].bar(labels,[z["converged_cases"] for z in phys]);axs[1].set_ylim(0,21);axs[1].set_title("达到梯度容差的算例数 / 20")
    fig.tight_layout();fig.savefig(OUT/"物理精修对比.png",dpi=180);plt.close(fig)
    subset=json.loads((OUT/"physical_subset.json").read_text(encoding="utf-8"))
    fig,axs=plt.subplots(4,5,figsize=(14,11))
    for i,g in enumerate(GROUPS):
        rec=next(z for z in subset if z["group"]==g)
        d=np.load(OUT/"prediction_states"/f"{rec['id']}.npz")
        sol=np.load(OUT/"refinement_states"/f"{rec['id']}_X_MLP.npz")
        arrays=[d["X0"],d["teacher_X"],d["Q_20261023"],d["X_20261023"],sol["X"]]
        for j,(x,title) in enumerate(zip(arrays,["规则物理网格","Q教师重建X","Q-MLP重建X","X-MLP直接预测","X-MLP物理精修"])):
            ax=axs[i,j];ax.triplot(x[:,0],x[:,1],d["cells"],lw=.45,color="#334155")
            ax.set_aspect("equal");ax.set_xticks([]);ax.set_yticks([])
            if i==0:ax.set_title(title)
            if j==0:ax.set_ylabel(NAMES[g])
    fig.tight_layout();fig.savefig(OUT/"代表性物理网格.png",dpi=170);plt.close(fig)
    x=next(z for z in metrics if z["target"]=="X" and z["group"]=="ALL")
    q=next(z for z in metrics if z["target"]=="Q" and z["group"]=="ALL")
    table="\n".join(f"|{NAMES[g]}|"+ "|".join(
        f"{100*next(z for z in metrics if z['group']==g and z['target']==t)['node_relative_error']:.3f}%"
        for t in ["X","Q"])+"|" for g in GROUPS+["ALL"])
    ftable="\n".join(f"|{NAMES[g]}|"+ "|".join(
        f"{next(z for z in metrics if z['group']==g and z['target']==t)['interpolation_rmse']:.6f}"
        for t in ["X","Q"])+f"|{next(z for z in metrics if z['group']==g and z['target']=='X')['teacher_interpolation_rmse']:.6f}|"+
        f"{next(z for z in metrics if z['group']==g and z['target']=='X')['regular_interpolation_rmse']:.6f}|" for g in GROUPS+["ALL"])
    ptable="\n".join(f"|{labels[i]}|{z['converged_cases']}/20|{z['mean_case_median_seconds']:.4f}|{z['mean_iterations']:.1f}|"+
        f"{z['mean_final_gradient']:.2e}|{z['mean_interpolation_rmse']:.6f}|" for i,z in enumerate(phys))
    etable="\n".join(f"|{labels[i]}|{z['matched_case_count']}|"+
        (f"{z['matched_speedup']:.3f}×" if z["matched_speedup"] is not None else "无可比算例")+"|" for i,z in enumerate(phys))
    direction="低于" if x["node_relative_error"]<q["node_relative_error"] else "高于"
    pairmap={(z["id"],z["seed"],z["target"]):z for z in p}
    nodewin=np.mean([float(z["error_relative"])<float(pairmap[z["id"],z["seed"],"Q"]["error_relative"]) for z in p if z["target"]=="X"])
    interpwin=np.mean([float(z["interpolation_rmse"])<float(pairmap[z["id"],z["seed"],"Q"]["interpolation_rmse"]) for z in p if z["target"]=="X"])
    text=f"""# 直接物理网格预测与精修补充实验

直接学习X的平均物理节点误差为 **{100*x['node_relative_error']:.3f}% ± {100*x['seed_std']:.3f}个百分点**，
{direction}相同训练预算下Q-MLP重建X的 **{100*q['node_relative_error']:.3f}% ± {100*q['seed_std']:.3f}个百分点**。
逐测试样本、逐种子配对时，X模型的节点误差更小比例为{100*nodewin:.1f}%，插值误差更小比例为{100*interpwin:.1f}%。

直接X预测在线耗时约{ x['prediction_ms']:.3f}毫秒，Q预测并重建约{q['prediction_ms']:.3f}毫秒。
在20例相同物理能量精修中，规则初值平均{phys[0]['mean_case_median_seconds']:.3f}秒，
X初值{phys[1]['mean_case_median_seconds']:.3f}秒，Q初值{phys[2]['mean_case_median_seconds']:.3f}秒，
最近邻X初值{phys[3]['mean_case_median_seconds']:.3f}秒，四种方法全部收敛到能量相近的终点。
这些结果支持将预测网格用作非线性物理优化初值，但没有显示直接学习X比学习Q具有精度或精修成本上的明显优势。
最近邻也能降低精修成本，神经网络在本测试中的额外收益有限。

## 数据和公平比较

复用1200组真实高斯教师训练数据、400组验证数据、400组独立测试数据。原分布、中心偏移、窄而强、宽而弱各占测试集100组。
这些组均包含在扩展训练范围内。网格12×12划分、169节点、121内部节点、288三角形。
两种网络均为4→128→128→242，Tanh隐藏层，Adam学习率0.001、权重衰减10⁻⁶、批量128、最多2000轮、
验证早停耐心200、最小改善10⁻⁷，种子20261023/24/25，CPU单线程；标准化仅使用训练数据。
Q模型直接复用已经训练好的对应权重，X模型从头训练。误差分母为教师内部节点相对于规则网格的总位移范数。
X标签是冻结Q教师重建出的物理网格，不是下文物理能量的极小点。

## 直接预测的物理节点结果

|测试组|X-MLP直接预测|Q-MLP重建X|
|---|---:|---:|
{table}

每类3个模型各1200次、共2400次预测的原始几何/重建成功率：X为{100*x['raw_legal_rate']:.2f}%，Q管线为{100*q['raw_legal_rate']:.2f}%。
原始预测和最终使用的节点均保存在prediction_states；非法X预测按位移逐次减半直到几何合法，边界始终固定。
合法性条件为节点有限、位于单位正方形、边界不动、所有三角形有向面积大于10⁻¹⁰。

### 解析函数插值误差

目标函数为u(x)=exp(−‖x−c‖²/σ²)，在相同80×80物理采样点上计算分片线性插值RMSE。
节点误差与此函数误差是不同指标。

|测试组|X-MLP|Q-MLP|Q教师X|规则网格|
|---|---:|---:|---:|---:|
{ftable}

![直接预测比较](直接预测对比.png)

## 以X为变量的物理变分优化

沿用第四轮已经实现的物理能量与Armijo谱梯度法，原项目保留不变。
参考三角形边矩阵记为A，物理三角形为B(X)，J=A B(X)⁻¹，m(X)=1+α exp(−‖中心(X)−c‖²/σ²)。
取θ=1/3、p=2，使用三角形中心求积：

$$E_{{phys}}(X)=\\sum_K |K(X)|m_K(X)
\\left[\\frac13\\left(\\frac{{\\|J_K(X)\\|_F^2}}{{m_K(X)}}\\right)^2
+\\frac43\\left(\\frac{{\\det J_K(X)}}{{m_K(X)}}\\right)^2\\right].$$

面积、矩阵逆及度量场对X的依赖全部纳入64位自动微分。方向差分核对见physical_gradient_check.json。
该能量与冻结Q的二次Winslow能量不同，二者能量数值及求解耗时不构成同目标加速比。
本节只比较相同物理能量、相同算法、相同固定边界、相同梯度容差10⁻⁵、
相同3000次迭代及30000次能量求值上限下的四类初值。
每组预先选测试清单前5例，共20例；模型固定使用种子20261023。各方法交替顺序重复2次。
最近邻在训练参数标准化距离下检索缓存的教师X。耗时包含在线初值构造与精修，不含模型/数据加载及结果后处理。

|物理优化初值|收敛算例|每例两次耗时中位数的均值(s)|平均迭代数|平均最终梯度范数|插值RMSE|
|---|---:|---:|---:|---:|---:|
{ptable}

全部20例均保留在上表，未收敛的结果也计入耗时及误差。
仅当同一例两种初值都达到梯度容差、终点物理能量相对差不超过10⁻⁶时，才计入相同终点的速度比较：

|初值|与规则初值可比算例数|配对加速比几何均值|
|---|---:|---:|
{etable}

加速比按同一算例、同一次重复的规则初值耗时除以对应方法耗时计算。它描述当前物理优化器的初值效果。
精修后的几何及每步能量/梯度/回溯记录保存在refinement_states；失败停止原因保留在physical_per_case.csv。

## 结果解释与研究判断

直接输出X消除了Q→X的三角形插值，因此在线成本显著降低；但省去数值重建不等于神经网络误差必然更小。
本实验中X标签包含重建映射的非线性，固定网络和训练预算下，X映射的实际拟合结果更差，窄而强一组尤其明显。
这是一项实测判断，不能由此推导所有网络都应学习Q，或给出X表示优越性的普遍定理。

物理精修把两类预测带到能量相近的终点，最终插值误差几乎一致。
X-MLP与Q-MLP平均精修成本接近，微小时间差不能解释为坐标表示优势。
精修能否受益应看初始物理网格与该物理目标的匹配程度；Q教师的高精度拟合不保证就是物理能量的最佳初值。
如果继续发展物理网格路线，值得验证的是以同一物理能量生成教师标签后再学习X，
并与该目标下更强的传统优化器比较，而不仅把现有标签的输出坐标替换成X。

![物理精修结果](物理精修对比.png)

![四类代表网格](代表性物理网格.png)

## 适用范围和限制

这些实验检验固定分辨率、扩展高斯范围内的预测及小样本物理精修，不证明复杂场或任意分辨率泛化。
物理能量非线性，不保证不同初值到同一极小点。当前比较复用同一传统物理优化器，不能推出优于所有传统算法。
精修模型只学习Q教师的重建X；若要学习物理能量的最优解，需要另建对应的物理教师数据。
插值实验是解析函数的有限元插值误差，没有运行PDE求解，也不表示实际PDE误差。

## 复现与数据

在独立研究项目根目录执行：

    python runs/physical_X_01/run.py
    python runs/physical_X_01/analyze.py

依赖numpy、scipy、matplotlib、torch。已有X权重会被复用；重新训练时使用新的输出目录保留本次结果。
run.py引用本项目src、gaussian_1200真实教师库和既有3份Q权重，均保留在父项目。
prediction_per_case.csv有2400行，physical_per_case.csv有160行，summary_prediction.csv和summary_physical.csv给出汇总。
"""
    (OUT/"中文结果分析.md").write_text(text,encoding="utf-8")
    dump(OUT/"analysis_complete.json",dict(prediction_rows=len(p),physical_rows=len(r),
        x_node_error=x["node_relative_error"],q_node_error=q["node_relative_error"],
        x_wins_paired_node=float(nodewin),x_wins_paired_interpolation=float(interpwin),physical=phys))
    print(json.dumps(dict(X=x,Q=q,physical=phys),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
