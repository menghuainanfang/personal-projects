# 直接物理网格预测与优化

直接X预测在33个未见实例上均合法且无需退缩，测试节点误差为2.19%，与Q模型的2.15%接近。两者插值RMSE分别为0.010280和0.010285；直接X相对规则网格的平均RMSE增加2.52%。

独立物理目标下，规则初值与X模型初值均达到共同梯度阈值。平均接受迭代由205.1降至167.1，完整在线时间由0.858秒降至0.702秒，均值比加速1.22倍。物理精修后RMSE为0.009347，较规则网格降低6.78%。

课程设计可保留“直接物理预测作为廉价近似与物理优化初值”的方案，以独立插值评测和同目标精修为核心。单独的原始X预测适合快速逼近教师，本次插值指标不支持把它作为无需后处理的最终优胜网格；物理精修的收益温和，需计入离线成本。

## 成果入口

- paper/report.pdf：中文论文；report.md、report.tex可编辑，report.html可离线阅读。
- presentation/index.html：约5—8分钟课堂汇报网页；talk.md为讲稿。
- summary.md、audit.md：结果分析及数学/接口审计。
- results/A_metrics.csv、A_aggregate.csv：五种物理网格的逐实例指标及测试均值/标准差。
- results/B_metrics.csv、B_aggregate.csv：同一物理目标下两种初值的精度与成本。
- results/A_timings.csv、B_timings.csv：297次生成计时和198次优化计时。
- results/meshes/、histories/：33实例完整节点与物理优化轨迹；interpolation_points.npz为固定采样点。
- results/sampling_check.csv、B_endpoint_comparison.csv、verification.json：密采样、终点差异与指标复核。

## 复现

保留本目录在mesh_prediction/experiments/round4_direct_physical下的位置，教师和模型从上两级读取。依赖与上两级requirements.txt相同，使用CPU、PyTorch单线程；文档重建需要XeLaTeX及Node.js。

~~~powershell
python run_all.py
~~~

已有匹配的网页前端依赖时，可用--dependencies指定目录，Node可用--node指定可执行文件。仅重建文档加--documents-only，首次准备网页依赖可能需要联网。

分步运行 python -m unittest test_round4 -v、python experiment.py、python verify.py。本轮不会调用教师生成或模型训练。物理优化参数在physical.py的OPTIONS，已有网格及参数范围在上两级config.yaml。两种初值共用目标、梯度、预算、停止规则；计时排除采样与磁盘操作，固定拓扑接口和模型预加载。

运行 python package_project.py 生成新的完整ZIP，位置在mesh_prediction目录同级，名称mesh_prediction_round4_course_project.zip。包内包含所需源码、旧教师和模型、前三轮成果及本轮数据、图片、论文和离线网页，不含虚拟环境和前端依赖目录。

## 限制与验收

全部165个直接比较状态、66个物理优化终点均合法，所有198次优化重复达共同阈值；原有五项测试和新增四项测试通过。物理能量完整梯度通过四个方向差分，逐状态指标及汇总已重算复核。160与320密采样在展示实例上的最大RMSE相对变化为0.0268%。

固定网格、单高斯参数区间与给定解析场的结论；没有PDE误差、分布外或跨分辨率保证。物理能量与旧Q目标不同，不能比较二者能量或作跨目标同精度加速结论。既有教师与X训练合计约254.03秒，同目标优化粗略摊销约1634次。

PDF使用已有论文模板并逐页渲染检查；网页沿用原生成器构建及资源校验。当前浏览器工具对本地文件的限制使网页实际视觉与键盘交互验收未完成，可在本机浏览器直接打开HTML评估。


[下载完整课程项目ZIP](../../../../../downloads/mesh_prediction_round4_course_project.zip)
