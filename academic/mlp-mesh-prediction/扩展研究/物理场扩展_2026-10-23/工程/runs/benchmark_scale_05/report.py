"""Summarize completed size scaling without assuming a network advantage."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
plt.rcParams["font.sans-serif"]=["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"]=False
def read(name):return list(csv.DictReader((OUT/name).open(encoding="utf-8-sig")))
def write(name,rows):
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
def main():
    raw=read("timings.csv");pde=read("pde.csv");pred=read("predictions.csv")
    config=json.loads((OUT/"config.json").read_text(encoding="utf-8"))
    summary=[];paired=[]
    for kind in ["wave","five_ring"]:
        for i,n in enumerate(config["n"]):
            base=[r for r in raw if r["kind"]==kind and int(r["n"])==n and r["method"]=="regular"]
            coarse_cost=0.
            if i:
                nc=config["n"][i-1]
                coarse_cost=float(np.median([float(r["online_seconds"]) for r in raw if r["kind"]==kind and int(r["n"])==nc and r["method"]=="regular"]))
            for method in ["regular","network","coarse_to_fine"]:
                sub=[r for r in raw if r["kind"]==kind and int(r["n"])==n and r["method"]==method]
                for row in sub:
                    row["total_with_coarse_seconds"]=float(row["online_seconds"])+(coarse_cost if method=="coarse_to_fine" else 0.)
                    b=next(z for z in base if z["repeat"]==row["repeat"])
                    gap=abs(float(b["final_energy"])-float(row["final_energy"]))/max(1,abs(float(b["final_energy"])))
                    accepted=row["converged"]==b["converged"]=="True" and gap<=1e-6
                    paired.append(dict(kind=kind,n=n,method=method,repeat=row["repeat"],
                        accepted=accepted,energy_gap=gap,
                        speedup=float(b["online_seconds"])/row["total_with_coarse_seconds"]))
                pairs=[r for r in paired if r["kind"]==kind and r["n"]==n and r["method"]==method and r["accepted"]]
                pd=next(r for r in pde if r["kind"]==kind and int(r["n"])==n and r["method"]==method)
                uniform=next(r for r in pde if r["kind"]==kind and int(r["n"])==n and r["method"]=="X0")
                seconds=float(np.mean([float(r["total_with_coarse_seconds"]) for r in sub]))
                summary.append(dict(kind=kind,n=n,nodes=(n+1)**2,method=method,
                    converged=sum(r["converged"]=="True" for r in sub),repeats=len(sub),
                    mean_seconds=seconds,mean_fine_seconds=float(np.mean([float(r["online_seconds"]) for r in sub])),
                    mean_iterations=float(np.mean([float(r["iterations"]) for r in sub])),
                    matched_pairs=len(pairs),paired_speedup=float(np.exp(np.mean(np.log([r["speedup"] for r in pairs])))) if pairs else None,
                    pde_error_ratio=float(pd["poisson_l2"])/float(uniform["poisson_l2"]),
                    poisson_seconds=float(pd["poisson_seconds"]),
                    mesh_and_poisson_seconds=seconds+float(pd["poisson_seconds"])))
    write("timings.csv",raw);write("summary.csv",summary);write("paired.csv",paired)
    fig,axs=plt.subplots(2,3,figsize=(14,8))
    for i,kind in enumerate(["wave","five_ring"]):
        nodes=[(n+1)**2 for n in config["n"]]
        for method,label in [("regular","规则初值 L-BFGS"),("network","网络初值 L-BFGS"),("coarse_to_fine","两层传统法（含粗求解）")]:
            sub=[next(r for r in summary if r["kind"]==kind and r["n"]==n and r["method"]==method) for n in config["n"]]
            axs[i,0].loglog(nodes,[r["mean_seconds"] for r in sub],"-o",label=label)
            axs[i,1].semilogx(nodes,[r["mean_iterations"] for r in sub],"-o",label=label)
        for method,label in [("X0","规则网格"),("direct","网络直接输出"),("regular","传统优化"),("network","网络后精修")]:
            vals=[next(r for r in pde if r["kind"]==kind and int(r["n"])==n and r["method"]==method) for n in config["n"]]
            baseline=[next(r for r in pde if r["kind"]==kind and int(r["n"])==n and r["method"]=="X0") for n in config["n"]]
            axs[i,2].semilogx(nodes,[float(r["poisson_l2"])/float(b["poisson_l2"]) for r,b in zip(vals,baseline)],"-o",label=label)
        for j,title in enumerate(["网格在线时间（秒，含未收敛）","细网格迭代数","Poisson误差 / 规则误差"]):
            axs[i,j].set_title(("正弦波前" if kind=="wave" else "五圆环")+"："+title)
            axs[i,j].set_xlabel("节点数");axs[i,j].legend(fontsize=8)
    fig.tight_layout();fig.savefig(OUT/"规模与收益.png",dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,4,figsize=(12,6))
    for i,kind in enumerate(["wave","five_ring"]):
        d=np.load(OUT/"states"/f"{kind}_96.npz")
        for j,key in enumerate(["X0","direct","regular","network"]):
            x=d[key];ax=axs[i,j];ax.triplot(x[:,0],x[:,1],d["cells"],lw=.1)
            ax.set_aspect("equal");ax.set_xticks([]);ax.set_yticks([])
            if i==0:ax.set_title(dict(X0="规则网格",direct="网络直接输出",regular="传统L-BFGS",network="网络＋L-BFGS")[key])
            if j==0:ax.set_ylabel(kind)
    fig.tight_layout();fig.savefig(OUT/"9409节点网格.png",dpi=170);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5))
    for ax,kind in zip(axs,["wave","five_ring"]):
        for method,label in [("X0","规则网格直接求PDE"),("direct","网络直接＋PDE"),("regular","传统优化＋PDE"),("network","网络精修＋PDE")]:
            costs=[];errors=[]
            for n in config["n"]:
                pd=next(r for r in pde if r["kind"]==kind and int(r["n"])==n and r["method"]==method)
                if method=="X0":mesh=0.
                elif method=="direct":mesh=float(next(r for r in pred if r["kind"]==kind and int(r["n"])==n)["predict_seconds"])
                else:mesh=next(r["mean_seconds"] for r in summary if r["kind"]==kind and r["n"]==n and r["method"]==method)
                costs.append(mesh+float(pd["poisson_seconds"]));errors.append(float(pd["poisson_l2"]))
            ax.loglog(costs,errors,"-o",label=label)
            for x,y,n in zip(costs,errors,config["n"]):ax.annotate(str((n+1)**2),(x,y),fontsize=7)
        ax.set_xlabel("网格生成＋一次PDE求解（秒）");ax.set_ylabel("Poisson L2误差")
        ax.set_title(kind+"：误差与成本（标注节点数）");ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(OUT/"误差与成本.png",dpi=180);plt.close(fig)
    names=dict(regular="规则",network="网络",coarse_to_fine="两层")
    table="\n".join(f"|{r['kind']}|{r['nodes']}|{names[r['method']]}|{r['converged']}/{r['repeats']}|"+
        f"{r['mean_seconds']:.3f}|{r['mean_iterations']:.1f}|{r['matched_pairs']}/{r['repeats']}|"+
        (f"{r['paired_speedup']:.3f}" if r["paired_speedup"] is not None else "—")+"|" for r in summary)
    ftable=[]
    for kind in ["wave","five_ring"]:
        for n in config["n"]:
            vals={r["method"]:float(r["poisson_l2"]) for r in pde if r["kind"]==kind and int(r["n"])==n}
            ftable.append(f"|{kind}|{(n+1)**2}|{vals['direct']/vals['X0']:.3f}|{vals['regular']/vals['X0']:.3f}|{vals['network']/vals['X0']:.3f}|")
    legal=sum(r["raw_valid"]=="True" for r in pred)
    largest={kind:{m:next(r for r in summary if r["kind"]==kind and r["n"]==96 and r["method"]==m)
        for m in ["regular","network","coarse_to_fine"]} for kind in ["wave","five_ring"]}
    report=f"""# 公开解析算例与规模测试

现有模型在两种9409节点问题上，未建立“网络初值＋精修”的同目标加速：
波前规则/网络初值平均{largest['wave']['regular']['mean_seconds']:.2f}/{largest['wave']['network']['mean_seconds']:.2f}秒，
五圆环为{largest['five_ring']['regular']['mean_seconds']:.2f}/{largest['five_ring']['network']['mean_seconds']:.2f}秒。
节点增多本身没有使预测初值更有效。直接使用网络网格则有成本与误差的取舍，详见后文。

本轮冻结既有跨场模型，不重新训练，实际完成2个解析场×4档规模×3类优化初值×2次重复。
最大9409节点、18432三角形，节点数为原169节点的55.7倍。
原始网络预测合法{legal}/{len(pred)}例。

## 同目标耗时与迭代

|场|节点|初值|收敛|完整网格时间(s)|细网格迭代|可比配对|配对加速|
|---|---:|---|---:|---:|---:|---:|---:|
{table}

规则与网络使用同一物理能量、L-BFGS、梯度容差10⁻⁵、3000迭代和30000求值上限。
同一例两种初值均收敛且终点能量相对差≤10⁻⁶才计算加速。
所有停止原因、耗时及终点能量均保留。时间包含初值构造、几何处理与优化；不含模型加载和PDE后处理。
两层法先从规则网格求解前一档粗问题，再将位移双线性插值到细网格精修；
时间已加入那次粗网格规则求解的两次耗时中位数，不假设免费拥有粗解。
不同n使用相同离散梯度范数阈值，不能将此视为统一连续误差容差。

![规模与收益](规模与收益.png)

## PDE精度

以同一解析函数构造−Δu=f和四边精确Dirichlet条件。
P1有限元沿用既有实现。波前与较细五圆环使用8×8 Duffy求积；
五圆环n12采用32×32、n24采用12×12，以解析窄环层。
最粗五圆环的24×24与32×32求积比较，规则/两种优化网格的L2误差相对变化最大约2.56×10⁻⁶。
右端自动微分按32768点分批，控制大网格内存。在线计时与求积验证分开进行。
下表为同节点数Poisson L2误差与规则网格之比，小于1为改善。

|场|节点|网络直接|传统优化|网络精修|
|---|---:|---:|---:|---:|
{chr(10).join(ftable)}

pde.csv保留PDE线性求解残差、完整组装求解时间、误差及面积。
summary.csv的mesh_and_poisson_seconds为网格生成与该状态一次PDE求解的时间和，
误差评估不计时。每状态PDE只计一次，不能用它声称稳健的端到端加速。

![不同节点数下的实际误差与成本](误差与成本.png)

图中直接网络与精修输出达到的误差不同，不能把纵坐标不同的两点直接相除作为同精度加速。
更低网格成本但更高任务误差属于近似取舍；是否可用需要应用先给出误差阈值。

![最大规模网格](9409节点网格.png)

## 与公开算例的关系

解析函数来自MMPDElab官方examples/ex2d_1.m的case 3及case 5：

- 波前：u=tanh[−30(y−1/2−sin(2πx)/4)]。
- 五圆环：令ξ=4x−2、η=4y−2，中心为(0,0)、(±1/2,±1/2)，
  u为五项tanh[30((ξ−a)²+(η−b)²−1/8)]之和。

官方来源：https://github.com/weizhanghuang/MMPDElab/blob/master/examples/ex2d_1.m

本地与官方的重要差别：官方使用MovMesh_metric构造并平滑度量，默认只固定角点，
采用MovMesh/MovMesh_XM等时间积分；本轮使用固定全部边界、当前自定义标量m、
现有Huang物理能量及L-BFGS。波前m沿用训练定义，五圆环m=1+8Σexp[−(30d)²]。
此外增加了制造解Poisson评价。因此这是公开解析场的本地移植与规模压力测试，不是MMPDElab官方算法复现。

波前的函数族参加过训练；五圆环没有参加训练。模型输入仍是32×32采样，
细网格节点增加不提高输入分辨率，也不表示网络跨尺度误差自动下降。
每类只有一个固定解析实例，重复计时2次，仅作探索性规模测试。

## 可进一步接入的公开基准

|项目|实际提供的内容|当前接入状态|
|---|---|---|
|MMPDElab|解析场、Poisson与移动网格的MATLAB源代码|已读取官方源文件并移植上述解析函数；当前环境未发现matlab/octave命令|
|UM2N|Poisson/Helmholtz/Burgers数据生成、Swirl评测与数据/权重入口|已核对官方README和评测代码；当前Python缺少Firedrake、Movement、torch_geometric，未跑官方评测|
|UGAWG adapt-benchmarks|各向异性自适应基准和度量评价约定|已核对公开入口；含3D和改变拓扑任务，当前二维固定拓扑模型不直接适配|

UM2N：https://github.com/mesh-adaptation/UM2N
Swirl评测：https://mesh-adaptation.github.io/docs/_modules/UM2N/test/bench_swirl.html
UGAWG：https://github.com/UGAWG/adapt-benchmarks

这些不是一个免适配的统一排行榜。当前网络不能原样处理任意多边形、三维体网格或完整各向异性张量。
官方对照应共同报告同自由度预算下的几何合法性、PDE误差和完整在线成本；
UM2N的Monge–Ampère目标与当前Huang目标不同，不能比较终点能量作为精度等价依据。

## 复现

在现有独立研究工程根目录运行：

    python runs/benchmark_scale_05/benchmark.py
    python runs/benchmark_scale_05/report.py

复用runs/physical_field_training_04/model.pt及其输入处理，runs/physical_hybrid_02的L-BFGS、
runs/physical_fields_03的PDE模块。旧源码和模型保持不变。
config.json固定所有解析参数、规模、预算；timings.csv、paired.csv、pde.csv和states保存真实记录。
"""
    (OUT/"中文测试报告.md").write_text(report,encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
