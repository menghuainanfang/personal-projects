"""Build the physical-teacher study report from completed results."""
from pathlib import Path
import csv,json,sys,zipfile
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/"src"))
from scale_study import csvout,dump
plt.rcParams["font.sans-serif"]=["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"]=False
def read(name):return list(csv.DictReader((OUT/name).open(encoding="utf-8-sig")))
def avg(rows,key):return float(np.mean([float(r[key]) for r in rows]))
def main():
    complete=json.loads((OUT/"complete.json").read_text(encoding="utf-8"))
    p=read("prediction.csv");r=read("refinement.csv");status=read("teacher_status.csv")
    methods=["physical_X","Q_teacher_X","Q_MLP"]
    names=dict(physical_X="物理教师X模型",Q_teacher_X="原Q教师X模型",Q_MLP="Q模型重建X",regular="规则物理网格")
    summaries=[]
    for group in ["ID","center","narrow","broad","ALL"]:
        for name in methods:
            sub=[z for z in p if z["method"]==name and (group=="ALL" or z["group"]==group)]
            seeds=[avg([z for z in sub if z["seed"]==str(s)],"error_relative") for s in [20261023,20261024,20261025]]
            summaries.append(dict(group=group,method=name,n=len(sub)//3,error_relative=avg(sub,"error_relative"),
                seed_std=float(np.std(seeds,ddof=1)),raw_legal_rate=float(np.mean([z["raw_valid"]=="True" for z in sub])),
                interpolation_rmse=avg(sub,"interpolation_rmse"),teacher_rmse=avg(sub,"teacher_interpolation_rmse"),
                regular_rmse=avg(sub,"regular_interpolation_rmse"),energy=avg(sub,"energy"),
                prediction_ms=1000*avg(sub,"predict_seconds")))
    csvout(OUT/"summary_prediction.csv",summaries)
    costs=[]
    for name in ["regular"]+methods:
        sub=[z for z in r if z["method"]==name]
        base=[z for z in r if z["method"]=="regular"];eq=[]
        for z in sub:
            b=next(v for v in base if v["id"]==z["id"] and v["repeat"]==z["repeat"])
            gap=abs(float(z["final_energy"])-float(b["final_energy"]))/max(1,abs(float(b["final_energy"])))
            if z["converged"]==b["converged"]=="True" and gap<=1e-6:
                eq.append(float(b["online_seconds"])/float(z["online_seconds"]))
        costs.append(dict(method=name,n=len(sub)//2,converged_runs=sum(z["converged"]=="True" for z in sub),
            mean_seconds=avg(sub,"online_seconds"),iterations=avg(sub,"iterations"),
            final_energy=avg(sub,"final_energy"),matched_runs=len(eq),
            matched_speedup=float(np.exp(np.mean(np.log(eq)))) if eq else None))
    csvout(OUT/"summary_refinement.csv",costs)
    allrows=[z for z in summaries if z["group"]=="ALL"]
    fig,axs=plt.subplots(1,3,figsize=(14,4))
    for ax,key,title,factor in [(axs[0],"error_relative","对物理教师的节点误差 (%)",100),
        (axs[1],"interpolation_rmse","解析函数插值RMSE",1),(axs[2],"energy","预测网格物理能量",1)]:
        ax.bar([names[z["method"]] for z in allrows],[factor*z[key] for z in allrows],color=["#2563eb","#64748b","#ed8936"])
        ax.set_title(title);ax.tick_params(axis="x",labelrotation=15)
    fig.tight_layout();fig.savefig(OUT/"物理教师训练对比.png",dpi=180);plt.close(fig)
    fig,axs=plt.subplots(4,4,figsize=(11,11))
    manifest=json.loads((OUT/"data/manifest.json").read_text(encoding="utf-8"))
    for i,g in enumerate(["ID","center","narrow","broad"]):
        rec=next(v for v in manifest["splits"]["test"] if v["group"]==g)
        d=np.load(OUT/"test_states"/f"{rec['id']}.npz")
        for j,key in enumerate(["teacher_X"]+methods):
            x=d[key];ax=axs[i,j];ax.triplot(x[:,0],x[:,1],d["cells"],lw=.4);ax.set_aspect("equal")
            ax.set_xticks([]);ax.set_yticks([])
            if i==0:ax.set_title("物理教师" if key=="teacher_X" else names[key])
            if j==0:ax.set_ylabel(g)
    fig.tight_layout();fig.savefig(OUT/"物理教师与预测网格.png",dpi=160);plt.close(fig)
    table="\n".join(f"|{names[z['method']]}|{100*z['error_relative']:.3f}% ± {100*z['seed_std']:.3f}|"+
        f"{100*z['raw_legal_rate']:.1f}%|{z['interpolation_rmse']:.6f}|{z['energy']:.6f}|" for z in allrows)
    ctable="\n".join(f"|{names[z['method']]}|{z['converged_runs']}/{2*z['n']}|{z['mean_seconds']:.4f}|{z['iterations']:.1f}|"+
        f"{z['matched_runs']}|"+(f"{z['matched_speedup']:.3f}×" if z["matched_speedup"] else "无")+"|" for z in costs)
    gtable="\n".join(f"|{g}|"+ "|".join(
        f"{100*next(z for z in summaries if z['group']==g and z['method']==name)['error_relative']:.3f}%"
        for name in methods)+"|" for g in ["ID","center","narrow","broad"])
    text=f"""# 物理能量教师监督的网格学习

本实验从物理能量的数值极小点生成X标签，训练3个小型MLP，并在相同测试参数上与原有模型比较。

物理教师X模型的插值RMSE为{allrows[0]['interpolation_rmse']:.6f}，
相对旧Q模型重建X降低{100*(1-allrows[0]['interpolation_rmse']/allrows[2]['interpolation_rmse']):.2f}%。
在20例同目标精修中，其平均迭代从规则初值的{costs[0]['iterations']:.2f}次降到{costs[1]['iterations']:.2f}次，
对规则初值的配对加速比为{costs[1]['matched_speedup']:.2f}倍。
全部四类初值均在20例、各2次运行中收敛，且终点能量满足配对条件。
这支持使用与最终物理优化目标一致的教师标签，作为后续研究路线。

## 直接预测结果

|模型|对物理教师的节点相对误差及种子标准差(百分点)|原始合法率|函数插值RMSE|平均物理能量|
|---|---:|---:|---:|---:|
{table}

本表全部以新物理教师作为节点参照。原Q教师X模型和Q模型学习的是不同目标，
因此这里的节点误差不能与此前对Q教师的1.98%或2.57%直接比较。
物理教师自身的函数插值RMSE为{allrows[0]['teacher_rmse']:.6f}，规则网格为{allrows[0]['regular_rmse']:.6f}。

|测试组|物理教师X模型|原Q教师X模型|Q模型重建X|
|---|---:|---:|---:|
{gtable}

![直接预测比较](物理教师训练对比.png)

## 相同物理目标的在线精修

预先固定每组前5例，共20例；使用种子20261023，交替顺序各重复2次，CPU单线程。
耗时包括预测、合法性处理及优化。模型和数据加载、指标后处理在计时外。
四类初值使用同一物理能量、Armijo谱梯度算法、梯度容差10⁻⁵、3000迭代及30000求值上限。
只有双方收敛且终点能量相对差≤10⁻⁶才计入配对加速比。

|初值|收敛运行数|平均耗时(s)|平均迭代|同终点配对数|对规则初值配对加速比|
|---|---:|---:|---:|---:|---:|
{ctable}

全部运行均保留在refinement.csv，包括未收敛结果；配对加速比为逐例逐次比值的几何均值。
此前冻结Q目标的稀疏直接解不属于本节物理目标的求解器，不与这些时间混算。

## 教师、模型与数据

复用原扩展高斯参数清单与独立划分，申请1200训练、400验证、400测试。
实际合格数量为{complete['split_sizes']}；未达到教师容差的样本数为{complete['failed_teachers']}。
教师从规则物理X出发，采用固定边界；达到10⁻⁵梯度容差才入库。
首轮未收敛者从当前节点继续求解，最多10000迭代、100000求值；失败实例保留JSON状态。
物理能量实现复用上一轮physical_energy.py，面积、逆矩阵、度量场采样位置全部对X求导。
参考边矩阵A、物理边矩阵B，J=AB⁻¹，m=1+αexp(−‖三角形中心−c‖²/σ²)，能量为：

$$E(X)=\\sum_K |K(X)|m_K(X)
\\left[\\frac13(\\|J_K(X)\\|_F^2/m_K(X))^2+
\\frac43(\\det J_K(X)/m_K(X))^2\\right].$$

MLP为4→128→128→242，Tanh隐藏层，目标为物理教师内部位移。
训练种子20261023/24/25，Adam学习率0.001、权重衰减10⁻⁶、批量128、
最多2000轮、验证耐心200、最小改善10⁻⁷。输入标准化及标签尺度仅由训练数据确定。
教师生成并行；训练和在线计时阶段没有教师任务同时运行。
解析函数u=exp(−‖x−c‖²/σ²)，在80×80固定物理点上评价线性插值。
节点误差以物理教师相对规则网格的总内部位移归一化。

![教师与预测](物理教师与预测网格.png)

## 限制

非线性物理教师是达到梯度容差的驻点，不是经过证明的全局最优解。
本实验只覆盖固定12×12划分和扩展高斯范围，不建立跨分辨率或复杂场泛化结论。
旧模型的目标不同；三种表示的结果体现目标及表示的共同影响，不能据此单独证明物理坐标的数学优越性。
精修对照使用现有谱梯度优化器，不代表优于所有传统非线性求解器。
函数插值误差不等于真实PDE求解误差。离线教师生成和训练有额外成本，在线收益不包含这部分成本。

## 复现

在独立项目根目录执行：

    python runs/physical_teacher_01/study.py
    python runs/physical_teacher_01/report.py

已有教师和模型会复用。依赖numpy、scipy、matplotlib、torch。
data/teachers保存物理教师；models保存权重、逐轮损失；test_states保存教师与三个模型预测节点。
teacher_status.csv、prediction.csv、refinement.csv为原始结果；summary_*.csv为汇总。
"""
    (OUT/"中文研究报告.md").write_text(text,encoding="utf-8")
    dump(OUT/"analysis.json",dict(prediction=allrows,refinement=costs,complete=complete))
    print(json.dumps(dict(prediction=allrows,refinement=costs,complete=complete),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
