"""Create the research entry points and a complete local snapshot."""
from pathlib import Path
import csv,json,shutil,zipfile
from report_study import main as report
from scale_study import ROOT,RUN,dump,csvout,readcsv

def main():
    report()
    env=ROOT/"runs/teacher_audit_01/environment.json"
    for directory in [ROOT,RUN,ROOT/"runs/matched_benchmark_01"]:
        if directory.exists():shutil.copy2(env,directory/"environment.json")
    (RUN/"RUNBOOK.md").write_text("# 高斯扩展复现\n\n从项目根运行python src/scale_study.py。该脚本生成两个严格嵌套的数据档、共享400验证/400测试，训练12个预定模型并评测。全部具体超参数见config.json和models各目录run_config.json。\n\n每个模型保存best_model.pt、training_summary.json、loss_history.csv、training.log以及evaluation/metrics_per_case.csv、aggregate.csv、failures.json和worst5.png。\n\n训练、验证只使用对应split；测试不参与模型选择。不同规模同epoch上限不等于相同优化步数。最终串行成本见../matched_benchmark_01，组合外推见extreme_test。",encoding="utf-8")
    bench=ROOT/"runs/matched_benchmark_01"
    if bench.exists():(bench/"RUNBOOK.md").write_text("# 串行强基线计时\n\n在全部训练停止后，从项目根运行python src/benchmark_serial.py。预加载1200档首个预定种子模型与训练最近邻库。400个共享测试实例×3次×4方法，计入实际在线处理，终点以合并内部梯度L2范数≤1e-5及物理坐标最大差≤1e-6验收；CG每轴atol1e-7。\n\n只比较冻结Q能量，不包括独立物理E_phys。4800条计时在baseline_cost.csv；config.json记录完整口径。模型加载及终点与保存参考的交叉验证不计入在线时间。",encoding="utf-8")
    audit="""# 独立扩展研究审计

课程设计路径为C:/Users/10251/CodexWorkspace/personal-projects-publish/academic/mlp-mesh-prediction，旧工程提交SHA及环境详见environment.json。本研究仅写当前mesh-learning-lab与独立解压工作包目录，没有修改旧课程文件。

阶段0补训练的原始ZIP来自工作包，SHA验证及重放在runs/replay_baseline_01完成；它与课程设计预训练权重不同，当前新训练不是原权重微调。仅隔离副本的报告脚本适配Windows路径，其数值代码不改。数值列容差比较、运行日志与失败清单都保留。

稀疏教师核查由runs/teacher_audit_01给出：中心＋10例，与pilot Q/X和旧工程冻结Q目标能量及梯度交叉核对；9例多场/多尺度与22例数据烟雾均通过。没有把旧非线性物理目标与稀疏Q教师混作同一算法。

工作包主任务书对1200/3000嵌套有疑虑，Windows说明则认为存在包含关系。本地直接比较场spec后确认当前预设天然满足包含关系；没有虚构采样器错误或重写采样分布，新增自动验证见runs/scale_study_01/nested_split_check.json。两个档的400验证/400测试一致，训练实例包含且split互斥。

新固定Q模型batch128与CPU单线程配置为本次预先固定协议，区别于原基线重放batch32等设置；因此原重放结果与新受控覆盖/规模对照分开解释。1200/3000虽然共享样本与epoch上限，但优化更新预算不等，不能只归因数据数量。

场模型对原测试集的边界失败做了探索性连续包络对照。原144测试不再冒称新模型结构的独立最终验证；随后另按固定新种子生成24场、96个网格组合，两已冻结模型各评一次。包络并非所有组都胜出，全部raw/safe结果保留。

完整数据来源、配置、权重和逐实例指标见results_index.csv；未执行CNN、2400场正式训练、独立E_phys精修、能量正则与PDE求解。没有引用这些项目的未运行数字。
"""
    (ROOT/"docs/audit.md").write_text(audit,encoding="utf-8")
    readme="""# 机器学习辅助变分网格：独立扩展研究

**扩展数据覆盖能改善限定参数族预测，但小规模冻结Q目标的强稀疏基线仍很有竞争力；可变节点查询不自动保证细网格几何合法与精度。**

这是一项独立数值研究，课程设计、旧论文和原2015年复现主线均保留。

## 阅读入口

1. [阶段性研究报告](reports/阶段性研究报告.md)：1200/3000、三种子、覆盖与容量对照，以及强传统基线。
2. [真实场输入研究报告](runs/field_operator_01/研究报告.md)：单峰/双峰/波前、可变节点数、原始翻转与连续边界包络。
3. [复现实验说明](docs/复现实验说明.md)与[学习和代码导读](docs/学习与代码导读.md)。
4. [审计记录](docs/audit.md)、[环境](environment.json)、[结果索引](results_index.csv)。

## 已完成

- 原始补训练完整隔离重放；中心＋10例稀疏教师及旧冻结Q能量/梯度交叉检查。
- 1200训练/400验证/400测试和3000训练/同400验证/同400测试，嵌套与实例互斥验证。
- 两档宽64各3训练种子；1200宽128的3种子容量对照；140原范围、320原范围、320混合单种子覆盖对照，共12个新固定Q模型。
- 完整400例的串行强基线：直接稀疏Q解、规则/MLP/最近邻初值CG；另有固定72个真正组合外推问题。
- 180训练场的真实32×32 log(m)编码与节点查询，训练n=8/12/16，测试n=12/20/24/32；规范8维双峰基线、连续边界包络及独立新增24场最终检查。
- 原始非法网格、退缩、尾部误差、最坏5例与功能插值均保留。各阶段实际数据量、教师失败分母与采样协议见分支报告。

## 文件组织

- baseline_archive/：原始补训练ZIP。
- src/：受控高斯实验、教师、训练/评估、串行计时与报告构建。
- runs/replay_baseline_01/：完整旧实验重放。
- runs/teacher_audit_01/：环境、烟雾、教师一致性与起步计时。
- runs/scale_study_01/：全部新高斯标签、12模型、原始日志与400例评测、72例极端外推。
- runs/matched_benchmark_01/：训练结束后的400例强基线串行计时。
- runs/field_operator_01/：真实场、坐标查询、双峰与包络对照；脚本与数据独立保存。
- runs/analysis_01/：同实例配对、离线成本与旧/新测试重合核查。
- figures/、reports/、docs/：真实统计图、中文报告和复现入口。

## 尚未实施

正式mixed_2400训练、CNN与图网络、等优化步数的数据量对照、Q能量/软几何训练损失、独立E_phys精修及真实PDE误差。这些没有写作本次结果。

固定Q学习的近似预测时间与精确解不是同精度任务；各耗时表均标明目标与计时范围。详细资源与成本见研究报告。
"""
    (ROOT/"README_从这里开始.md").write_text(readme,encoding="utf-8")
    registry=[]
    for p in sorted(ROOT.glob("runs/**/*.pt")):
        folder=p.parent
        configs=[folder/"run_config.json",folder/"config.json",folder.parent/"config.json"]
        cfg=next((q for q in configs if q.exists()),None)
        metrics=[folder/"evaluation/metrics_per_case.csv",folder/"metrics_per_case.csv",folder/"aggregate.csv"]
        metric=next((q for q in metrics if q.exists()),None)
        if p.name=="double8_model.pt":
            cfg=folder/"double8_summary.json"
            metric=folder/"double8_comparison.csv"
        registry.append(dict(run=str(folder.relative_to(ROOT)),weights=str(p.relative_to(ROOT)),
            configuration=str(cfg.relative_to(ROOT)) if cfg else "see run RUNBOOK.md",
            metrics=str(metric.relative_to(ROOT)) if metric else "see run aggregate.csv"))
    csvout(ROOT/"results_index.csv",registry)
    dump(ROOT/"artifact_manifest.json",dict(project="mesh-learning-lab",date="2026-10-23",weight_file_count=len(registry),
        new_fixed_model_trainings=12,new_field_model_trainings=3,
        weights=registry,code="src and branch-local scripts",environment="environment.json",
        reports=["reports/阶段性研究报告.md","runs/field_operator_01/研究报告.md"],
        scope="Frozen Q teacher; separate direct-X field labels; no E_phys timing mixture"))
    failures=[]
    for f in (RUN/"data").glob("gaussian_*/failures_*.json"):
        for r in json.loads(f.read_text(encoding="utf-8")):failures.append(dict(file=str(f.relative_to(ROOT)),**r))
    with (RUN/"failures.jsonl").open("w",encoding="utf-8") as f:
        for r in failures:f.write(json.dumps(r,ensure_ascii=False)+"\n")
    dump(ROOT/"completion.json",dict(phase0=True,fixed_models=12,field_models=3,
        field_final_holdout=True,formal_mixed2400=False,CNN=False,PDE=False,
        physical_energy_refinement=False,phase1_sampling="nested exact shared split",
        matched_benchmark_cases=400))
    archive=ROOT.parent/"mesh-learning-lab_研究结果快照.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in ROOT.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts:
                z.write(p,str(Path(ROOT.name)/p.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        print("Snapshot",archive,"MiB",round(archive.stat().st_size/2**20,2),"files",len(z.namelist()))
if __name__=="__main__":main()
