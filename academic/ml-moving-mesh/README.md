# 二维变分网格与随机森林步长预测

**状态：练手实验已完成。** 本项目检验机器学习初始步长预测是否能降低二维网格优化的实际成本，保存了完整数据、代码和一份实验报告。

随机森林减少了能量评价次数，但总耗时高于标准 Armijo；独立验证集的预测误差也高于沿用上一步步长的策略。现阶段作为数值优化与机器学习的练手项目归档，后续课程设计方向另行评估。

## 成果入口

- [七页中文实验报告 PDF](paper/paper.pdf)，包含公式、真实网格图、对照表与参考文献。
- [报告 Markdown](paper/paper.md)与[LaTeX 源码](paper/paper.tex)。
- [课堂汇报 HTML](presentation/report.html)：下载后双击，公式、图片和脚本均内嵌，可离线使用。
- [论文 HTML](paper/paper.html)：下载后离线阅读。
- [实测结果](results_summary.md)、[逐次结果 CSV](data/results.csv)与[汇总表](data/aggregate.csv)。

GitHub 文件页不直接运行 HTML；查看汇报时下载该文件，或下载仓库后打开本目录的 START_HERE.html。

## 实验和结论

复用 Winslow 离散能量、解析梯度及分片线性逆映射，比较固定步长、标准 Armijo、历史步长热启动和随机森林预测初值。所有方法共用下降方向、固定边界、Armijo 条件与计算/物理网格正面积检查。

三类度量分别为单位阵、局部高斯标量场和光滑各向异性场。训练24个、验证6个、测试9个完整实例，同一轨迹不跨集合。测试网格均为169个节点、288个三角形；36次测试全部达到共同梯度阈值，最终网格无翻转。

|算例|Armijo 评价次数|森林评价次数|Armijo 时间/s|森林时间/s|
|---|---:|---:|---:|---:|
|均匀度量|382.0|153.0|0.301|1.016|
|高斯度量|972.7|298.0|0.969|2.517|
|各向异性度量|891.0|240.0|0.736|1.710|

表中为三个独立测试实例的均值。森林的特征与预测约占其求解耗时的64.8%；本次小网格的能量评价很便宜，评价次数节省不足以抵消预测开销。验证集对数步长MAE为0.1848，上一步预测为0.1638，森林R²为−0.5623。

![三种度量下的评价次数与实际耗时](figures/cost.png)

![高斯度量下的初始、Armijo及随机森林物理网格](figures/mesh_gaussian.png)

## 复现

需要 Python 3.13；完整文档重建另需 Node.js 22.12+（建议24）及 XeLaTeX/ctex。已提供的PDF和HTML可直接阅读，无须安装开发依赖。

~~~powershell
cd academic/ml-moving-mesh
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/reproduce.py
~~~

网页沿用现有汇报生成器，其必要源码和锁定依赖清单位于 tools/reporting/。首次重建网页需要联网安装前端依赖；已有匹配的依赖目录可传 --dependencies。--documents-only 可复用保存的数值结果，仅重建图表与文档。运行日志写入 data/build_logs/。

只复现数值实验与图表：

~~~powershell
.\.venv\Scripts\python.exe scripts/run_experiments.py
.\.venv\Scripts\python.exe scripts/make_figures.py
~~~

## 代码和数据

|目录|内容|
|---|---|
|src/|复用的几何、Winslow能量、逆映射与共同实验驱动|
|scripts/|数据生成、训练、评估、绘图、文档生成、校验与打包|
|data/|种子配置、实例划分、教师轨迹、验证预测、全部测试结果和网格坐标|
|models/|固定随机种子的32棵树随机森林|
|figures/|由数值结果生成的PNG及SVG|
|paper/|报告、排版源码与离线网页|
|presentation/|课堂讲稿及原生成器输出|
|tools/reporting/|现有汇报生成器的必要源码，未包含node_modules|

src/geometry.py 和 src/variational_mesh.py 来自作者已有移动网格研究项目，原样复用；相关五项数学性质测试通过。新增六次随机合法网格方向差分的最大相对误差为6.45e−9。完整流水线已实际运行，ZIP解压后的轨迹、统计和资源校验通过。检查记录见 data/verification.json。

## 局限与后续方向

实验为三类小型度量、同分布测试和一次批量计时；误差棒为实例间样本标准差。采用冻结度量下的显式梯度优化，不代表原论文ode15s求解器加速，也没有PDE误差比较。网页通过生成和归档校验，浏览器实际渲染与键盘验收尚未确认。

后续更值得评估的是“学习辅助的网格参数选择”：在相同节点预算下，以插值误差或PDE误差为目标，学习选择度量强度与作用范围，并与均匀网格、固定经验参数及相同预算的简单搜索比较。该方向尚未实现，是否有收益取决于新实验。

[返回学科与学习项目](../README.md) · [参考文献与用途](references.md)
