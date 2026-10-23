"""Summarize completed runs and their explicit scientific scope."""
from pathlib import Path
import csv,json,sys,zipfile
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scale_study import ROOT,RUN,readcsv,csvout,dump

def main():
    models=[]
    for p in sorted((RUN/"models").glob("*/evaluation/aggregate.csv")):
        cfg=json.loads((p.parents[1]/"run_config.json").read_text(encoding="utf-8"))
        for r in readcsv(p):models.append(dict(dataset=cfg["dataset"],width=cfg["width"],seed=cfg["seed"],**r))
    if models:csvout(RUN/"aggregate.csv",models)
    figroot=ROOT/"figures";figroot.mkdir(exist_ok=True)
    manifest=RUN/"data/gaussian_1200/manifest.json"
    if manifest.exists():
        m=json.loads(manifest.read_text(encoding="utf-8"))
        fig,axs=plt.subplots(1,2,figsize=(10,4))
        for group in ["ID","center","narrow","broad"]:
            mus=np.array([r["spec"]["mu"] for r in m["splits"]["train"] if r["group"]==group])
            axs[0].scatter(mus[:,0],mus[:,1],s=7,alpha=.4,label=group)
            axs[1].scatter(mus[:,2],mus[:,3],s=7,alpha=.4,label=group)
        axs[0].set(xlabel="cx",ylabel="cy");axs[1].set(xlabel="A",ylabel="sigma");axs[1].legend()
        fig.tight_layout();fig.savefig(figroot/"training_coverage.png",dpi=160);plt.close(fig)
    if models:
        fig,ax=plt.subplots(figsize=(9,4))
        for group in ["ID","center","narrow","broad"]:
            xs=[];ys=[];errs=[]
            for ds,n in [("ID140",140),("ID320",320),("MIX320",320),("gaussian_1200",1200),("gaussian_3000",3000)]:
                rs=[r for r in models if r["dataset"]==ds and r["group"]==group and r["width"]==64]
                if rs:xs.append(f"{ds}\nn={n}");ys.append(100*np.mean([float(r["error_relative"]) for r in rs]));errs.append(100*np.std([float(r["error_relative"]) for r in rs],ddof=1) if len(rs)>1 else 0)
            ax.errorbar(xs,ys,yerr=errs,marker="o",label=group)
        ax.set(ylabel="Mean relative X error (%)");ax.legend();fig.tight_layout();fig.savefig(figroot/"coverage_and_size.png",dpi=160);plt.close(fig)
        for ds in ["gaussian_1200","gaussian_3000"]:
            paths=list((RUN/"models").glob(f"{ds}_w64_seed*/loss_history.csv"))
            if paths:
                fig,ax=plt.subplots(figsize=(8,4))
                for p in paths:
                    h=readcsv(p);ax.semilogy([int(r["epoch"]) for r in h],[float(r["validation_mse"]) for r in h],label=p.parent.name.split("seed")[-1])
                ax.set(xlabel="Epoch",ylabel="Validation normalized MSE");ax.legend();fig.tight_layout()
                fig.savefig(figroot/f"{ds}_convergence.png",dpi=160);plt.close(fig)
        path=RUN/"models/gaussian_1200_w64_seed20261023/evaluation"
        costfile=ROOT/"runs/matched_benchmark_01/baseline_cost.csv"
        if not costfile.exists():costfile=path/"baseline_cost.csv"
        if costfile.exists():
            c=readcsv(costfile);fig,ax=plt.subplots(figsize=(8,4))
            methods=["sparse_direct","cg_regular","cg_mlp","cg_nearest"]
            vals=[1000*np.mean([float(r["online_seconds"]) for r in c if r["method"]==s]) for s in methods]
            ax.bar(methods,vals);ax.set_ylabel("Full online time (ms)")
            fig.tight_layout();fig.savefig(figroot/"matched_Q_cost.png",dpi=160);plt.close(fig)
            percase=readcsv(path/"metrics_per_case.csv")
            fig,ax=plt.subplots(figsize=(8,4))
            ax.boxplot([[100*float(r["error_relative"]) for r in percase if r["group"]==g] for g in ["ID","center","narrow","broad"]],
                tick_labels=["ID","center","narrow","broad"],showfliers=True)
            ax.set_ylabel("Relative X error (%)");fig.tight_layout();fig.savefig(figroot/"error_distribution.png",dpi=160);plt.close(fig)
            costs=[]
            for method in methods:
                sub=[r for r in c if r["method"]==method]
                costs.append(dict(method=method,n_timed=len(sub),online_seconds=np.mean([float(r["online_seconds"]) for r in sub]),
                    max_coordinate_difference=max(float(r["max_coordinate_difference"]) for r in sub),
                    max_residual=max(float(r["residual"]) for r in sub)))
            csvout(RUN/"matched_cost_aggregate.csv",costs)
            apath=ROOT/"runs/matched_benchmark_01/approximate_per_case.csv"
            if apath.exists():
                approx=readcsv(apath);fig,ax=plt.subplots(figsize=(7,4))
                direct=next(r for r in costs if r["method"]=="sparse_direct")
                ax.scatter([0],[1000*direct["online_seconds"]],s=70,label="sparse exact")
                for method in ["MLP_approx","nearest_approx"]:
                    sub=[r for r in approx if r["method"]==method]
                    ax.scatter([100*np.mean([float(r["error_relative"]) for r in sub])],
                        [1000*np.mean([float(r["online_seconds"]) for r in sub])],s=70,label=method)
                ax.set(xlabel="Relative physical displacement error (%)",ylabel="Full online time (ms)")
                ax.legend();fig.tight_layout();fig.savefig(figroot/"time_quality.png",dpi=160);plt.close(fig)
        baseline=RUN/"models/ID140_w64_seed20261023/evaluation/metrics_per_case.csv"
        if baseline.exists():
            old={r["id"]:r for r in readcsv(baseline)};paired=[]
            for p in (RUN/"models").glob("*/evaluation/metrics_per_case.csv"):
                for r in readcsv(p):
                    paired.append(dict(model=p.parents[1].name,id=r["id"],group=r["group"],
                        error_difference_vs_ID140=float(r["error_relative"])-float(old[r["id"]]["error_relative"])))
            csvout(RUN/"paired_differences.csv",paired)
    lines=["# 阶段性研究报告\n\n共享400例测试上，1200宽64、3000宽64、1200宽128模型的三种子平均教师相对误差分别为3.095%、2.379%、1.984%。扩大覆盖与容量改善了教师逼近，但MLP＋CG的同目标在线成本仍高于直接稀疏解；功能插值与细网格合法性也没有随教师误差自动改善。\n\n本研究比较冻结物理网格的Winslow计算坐标教师、真实度量场表示与可变节点查询。课程设计原项目独立保留。"]
    audit=ROOT/"runs/teacher_audit_01/summary.json"
    if audit.exists():lines.append("## 阶段0：教师一致性与强传统基线\n\n中心和10个随机问题的稀疏教师与原pilot在浮点精度内一致；另对旧工程的冻结Q能量与梯度交叉验证。9个多场/多尺度与22个数据烟雾实例均通过。详见runs/teacher_audit_01/audit.md。原始补训练重放在runs/replay_baseline_01独立保存，不等同于课程设计旧权重微调。")
    replay=ROOT/"runs/replay_baseline_01"
    comparisons=list(replay.rglob("baseline_replay_comparison.csv"))
    lines.append("重放结果入口："+str(comparisons[0].relative_to(ROOT)) if comparisons else "原始基线重放尚未形成最终比较表，不将其标记为全部完成。")
    lines.append("## 阶段1：数据、训练与误差\n\n1200与3000档使用同一400验证/400测试参数；每组各100例。以实例spec的直接集合比较确认训练包含关系和split互斥。训练标签是稀疏Q教师内部位移，所有新受控变体共享batch=128、Adam、最多2000轮、验证耐心200。三种子预注册为20261023/24/25。140/320小基线各单种子，不能对其宣称多种子稳健性。\n\ncenter/narrow/broad对原范围模型属于范围外，但对混合1200/3000模型已处于训练分布覆盖内。补齐训练后的这些测试只证明扩展包络内的新参数泛化，不能继续称作真正未见包络外OOD。另设的72个组合/超包络问题才承担本轮外推检验。")
    lines.append("|数据|宽度|组别|完成种子数|平均物理位移误差/%|种子间标准差/%|\n|---|---|---|---|---|---|")
    for ds in ["ID140","ID320","MIX320","gaussian_1200","gaussian_3000"]:
        for width in [64,128]:
            for group in ["ID","center","narrow","broad"]:
                rs=[r for r in models if r["dataset"]==ds and r["width"]==width and r["group"]==group]
                if not rs:continue
                vals=np.array([100*float(r["error_relative"]) for r in rs])
                lines.append(f"|{ds}|{width}|{group}|{len(vals)}|{vals.mean():.3f}|{vals.std(ddof=1) if len(vals)>1 else 0:.3f}|")
    lines.append("\n平均、实例标准差、中位数、最坏10%尾均值在各模型evaluation/aggregate.csv中；实例配对差在paired_differences.csv。未以测试选择种子。预测指标分母是当前教师物理移动量，绝对内部坐标RMSE另列。")
    lines.append("![训练参数覆盖](../figures/training_coverage.png)\n\n![覆盖与数据规模对照；误差棒为已有多种子的标准差，单种子处不代表零不确定性](../figures/coverage_and_size.png)\n\n![首个1200模型的逐实例误差分布](../figures/error_distribution.png)")
    analysis=ROOT/"runs/analysis_01/中文分析.md"
    if analysis.exists():
        lines.append("## 数据覆盖与数值功能的配对证据\n\n[完整配对与成本分析](../runs/analysis_01/中文分析.md)给出400个相同实例的差分。320原范围与320混合的平均教师相对误差约34.90%→7.10%，但平均插值RMSE约0.009167→0.009759；窄强峰组插值约0.012645→0.015007。增加覆盖改善教师拟合，却没有同步改善指定功能指标。这里两者优化与训练协议相同，功能差异不能用教师误差代替。\n\n离线教师训练/验证成本、实际更新次数与训练时间在runs/analysis_01/offline_cost.csv；该分析也确认400测试与原课程203个教师、第五轮公开参数无精确重复。")
    costsfile=RUN/"matched_cost_aggregate.csv"
    if costsfile.exists():
        lines.append("## 同Q目标数值成本\n\n最终表优先采用全部训练停止后的runs/matched_benchmark_01串行测量，覆盖全部400个测试实例、每组100例、每例3次；训练期40例初测原样保留在首模型evaluation中。CPU单线程，缓存拓扑与模型；计入度量/矩阵组装、初始化、检查、线性解及物理重建。稀疏直接解作为强基线；CG各方法均以每轴绝对残差1e−7停止，统一以合并内部梯度L2范数≤1e−5验收，并校验与保存直接解坐标差。终点交叉核验在计时外。最近邻搜索时间计入，训练标签库预加载。")
        lines.append("|方法|完整在线均时/ms|最大物理坐标差|最大残差|\n|---|---|---|---|")
        cs=readcsv(costsfile)
        for r in cs:lines.append(f"|{r['method']}|{1000*float(r['online_seconds']):.3f}|{float(r['max_coordinate_difference']):.2e}|{float(r['max_residual']):.2e}|")
        sparse_time=float(next(r for r in cs if r["method"]=="sparse_direct")["online_seconds"])
        learned=float(next(r for r in cs if r["method"]=="cg_mlp")["online_seconds"])
        lines.append("\n"+("MLP＋CG没有超过完整稀疏直接解，本测量条件下不存在用离线训练成本换取该强基线在线加速的盈亏平衡点。" if learned>=sparse_time else "本组MLP＋CG在线均时低于稀疏直接解，但仍需结合实例差、离线成本和并发负载解释，不能推广为所有规模的优势。"))
        lines.append("单独网络预测是近似网格，不能把其时间除以直接解时间称为同精度加速。该表仅比较冻结Q目标，不含独立E_phys物理目标。")
        lines.append("![共同Q目标完整在线成本](../figures/matched_Q_cost.png)\n\n![近似网格与精确稀疏解的时间—质量权衡，非同精度加速比](../figures/time_quality.png)")
    extreme=RUN/"extreme_test/evaluation/aggregate.csv"
    if extreme.exists():
        lines.append("## 预留组合外推\n\n使用固定seed84991生成72个靠边/靠边窄强/包络外问题，只评估预先指定的1200宽64种子20261023；未用其选模型。有效教师数和失败参数见extreme_test/manifest.json与failures.json。")
        for r in readcsv(extreme):
            if r["group"]!="ALL":lines.append(f"- {r['group']}：{r['n']}个有效教师，平均相对误差{100*float(r['error_relative']):.2f}%，原始合法率{float(r['raw_legal_rate']):.3f}。")
    fieldroot=ROOT/"runs/field_operator_01"
    if (fieldroot/"研究报告.md").exists():
        lines.append("## 阶段2：真实度量场输入与坐标查询\n\n详见[真实场研究报告](../runs/field_operator_01/研究报告.md)。180训练场按实例划分后，每场监督8/12/16规模。原模型直接预测物理X位移，输入为真实32×32 log(m)；参数74,274，不是四参数代理。原测试中n32波前全部出现原始翻转，安全退缩后仍有约57.09%相对误差，支持接口可查询而非几何泛化保证。\n\n连续边界包络16x(1−x)y(1−y)用于探索靠边位移约束，保留原始模型；使用24个新场×4分辨率的96组合最终检查。n32新波前误差由51.28%降至43.11%，原始合法率由12.5%升至75%；但新单峰合法率由100%降至87.5%，n12波前误差也增大，不能称包络全面更好。原始144测试的对照仅作为探索性复用，新holdout不再用于调参。\n\n![场查询跨分辨率表现；右图仅为近似预测与稀疏精确参考的时间比](../runs/field_operator_01/cross_resolution.png)")
    else:lines.append("## 阶段2状态\n\n是否完成以runs/field_operator_01中实际模型、CSV及报告为准，尚未纳入本汇总的分支不作为结果。")
    lines.append("## 解释与局限\n\n数据覆盖不足由ID320与MIX320的同样本数对照检验；扩展效果由嵌套1200/3000且共享验证测试检验；表示不足由真实场输入分支检验。两个规模使用相同epoch上限与batch，而非相同梯度更新步数或相同训练时间，因此3000档同时增加数据量与优化计算预算；不能把差异全部归因于样本数量。各模型实际训练轮数和时间单列，严格等优化步数对照尚未执行。插值误差不作为训练目标，教师拟合改善不等同于功能改善。本阶段以80×80固定物理采样评价高斯插值，场分支采用各自明确的采样协议，不混并绝对RMSE。\n\nCPU小型固定MLP训练是明确选择，CUDA硬件可用但本固定网络实验没有宣称GPU训练。多种子差仅反映训练随机性，不涵盖训练数据重抽样不确定性；同参数生成机理的测试不能推广到任意分布。场分支规模较小，同时更换输入表征、标签坐标和网络结构，不能以其与四参数模型的差异单独归因于场编码。\n\n独立E_phys精修、软几何/Q能量正则消融及真实PDE求解留待实施；没有把它们写作已完成成果。")
    (ROOT/"reports/阶段性研究报告.md").write_text("\n\n".join(lines),encoding="utf-8")
    registry=[]
    for p in ROOT.glob("runs/**/best_model.pt"):
        registry.append(dict(run=str(p.parent.relative_to(ROOT)),weights=str(p.relative_to(ROOT)),configuration=str((p.parent/"run_config.json").relative_to(ROOT)),metrics=str((p.parent/"evaluation/metrics_per_case.csv").relative_to(ROOT))))
    if registry:csvout(ROOT/"results_index.csv",registry)
    dump(ROOT/"artifact_manifest.json",dict(project="mesh-learning-lab",created="2026-10-23",results=registry,
        original_course_project="C:/Users/10251/CodexWorkspace/personal-projects-publish/academic/mlp-mesh-prediction",
        code_version="local research source in src; original project SHA recorded in environment.json",
        scope="Frozen Q teacher expansion, no cross-objective timing"))
    print("Updated completed-run report",len(registry),"checkpoints")
if __name__=="__main__":main()
