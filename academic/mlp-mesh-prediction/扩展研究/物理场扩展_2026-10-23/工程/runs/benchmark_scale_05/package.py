"""Package the benchmark, frozen model and required numerical modules."""
from pathlib import Path
import zipfile
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def main():
    dependencies=[
        ROOT/"runs/physical_field_training_04/study.py",
        ROOT/"runs/physical_field_training_04/model.pt",
        ROOT/"runs/physical_fields_03/run.py",
        ROOT/"runs/physical_hybrid_02/solvers.py",
        ROOT/"runs/physical_X_01/physical_energy.py",
        ROOT/"src/teacher_general.py"]
    target=ROOT.parent/"公开解析算例与9409节点规模测试_复现包.zip"
    readme="""# 公开解析算例与网格规模测试

进入解压目录，先阅读runs/benchmark_scale_05/中文测试报告.md。
冻结模型来自此前四类场训练，未为本轮重新训练。

需要numpy、scipy、matplotlib、torch。已有结果与图片可直接阅读。
重新计算：

    python runs/benchmark_scale_05/benchmark.py
    python runs/benchmark_scale_05/report.py

benchmark.py包含解析场定义、完整计时口径与PDE求积阶数。
report.py从真实CSV生成表格与图片。finalize.py用于对已有结果作独立高阶求积评价和串行计时。
sources中的MMPDElab官方MATLAB源码按其AGPL-3.0许可保留；其余文件沿用原项目许可。
这是相同解析函数的本地实现与规模压力测试，不是MMPDElab或UM2N官方完整基准复现。
"""
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr("mesh-learning-benchmark/README.md",readme)
        for p in dependencies+[p for p in OUT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".log"]:
            z.write(p,Path("mesh-learning-benchmark")/p.relative_to(ROOT))
    print(target,target.stat().st_size/2**20)
if __name__=="__main__":main()
