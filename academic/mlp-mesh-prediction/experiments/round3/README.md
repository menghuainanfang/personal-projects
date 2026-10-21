# 二维变分网格：坐标诊断与直接计算坐标预测

## 阅读入口

- paper/report.pdf：中文课程论文；report.md与report.tex可编辑，report.html为离线论文网页。
- presentation/index.html：课堂汇报网页；talk.md为可编辑内容。
- diagnosis.md：插值往返诊断；summary.md：简洁结果。
- results/aggregate.csv：30测试汇总；metrics.csv：33实例×5方法；timings.csv：495次配对运行。
- results/meshes/和histories/：各方法初始化、终点节点与求解轨迹。
- models/：两个固定种子的Q模型及训练记录。
- audit.md：复用代码、坐标接口、划分及比较约定。

本目录位于第二轮项目的experiments/round3内。第二轮源代码、教师和X模型从上两级读取，不修改或重新生成；压缩包包含所需整个mesh_prediction项目和第二轮成果。2015年论文复现项目不作为运行依赖。

## 运行

按上两级requirements.txt安装依赖后，在本目录运行 python run_all.py。需要重建文档时准备XeLaTeX与Node.js；仅重建文档可加--documents-only。

分步运行：

~~~powershell
python -m unittest test_round3 -v
python experiment.py diagnose
python experiment.py train
python experiment.py evaluate
python verify.py
python package_project.py
~~~

数字计算使用CPU单线程；主种子20261021，辅助种子20261022，主模型不按测试结果选择。运行配置复用上两级config.yaml。Q安全处理、五方法和精修的实现见experiment.py。原X模型使用第二轮已保存权重，不重新拟合。

## 迁移复现

解压后保留mesh_prediction目录结构，在其根目录按requirements.txt安装Python依赖；建议Python 3.13、已有CPU可运行的PyTorch。再进入experiments/round3运行python run_all.py。文档重建需XeLaTeX/ctex与Node.js 22.12+；网页生成器首次准备依赖可能需要联网，已有匹配依赖可用--dependencies指定。交付PDF和内嵌资源HTML可直接离线阅读，无需安装开发环境。

最终压缩包位于mesh_prediction目录的同级，名为mesh_prediction_round3_course_project.zip。调用package_project.py重建，包含旧数据、旧X模型、新Q模型、源码、所有数值结果、图、论文及网页；排除虚拟环境、前端依赖、缓存和排版临时文件。

## 数据与比较口径

不改变140/30/30划分。三展示实例不参与拟合或模型选择。1NN仅在140个训练教师中按训练集标准差缩放的参数距离选取Q初值。Q模型和X模型结构、主种子、预算、优化器一致，各自标签缩放仅由训练集计算。

B0规则初值固定Armijo提议；B1物理MLP转换后精修；B2计算MLP精修；B3最近邻精修；B4规则初值沿用已接受步长。B0至B3共用原求解器，B4仅改变提议步长。所有方法共同使用绝对梯度阈值1e-5和相同能量、面积阈值及预算。计时包含问题建立、推理或查找、检查、重建及优化，模型和训练字典预加载，交替顺序三次配对。所有能量在Q上评价。

## 限制与验收状态

仅限固定网格、单高斯度量和参数区间内，没有PDE解误差、分布外或跨分辨率结论。第二个种子只检查初始化误差波动，完整精修计时使用预先固定的主种子。成功率和终止原因在metrics.csv；未收敛终止不能解释为同精度加速。

PDF经过编译和逐页渲染检查；数值状态由verify.py复核，网页由现有生成器执行构建和资源一致性校验。当前浏览器工具不允许file协议，本地离线网页的浏览器视觉、窄屏和键盘交互验收未完成；这项限制不影响交付HTML文件。可在本机浏览器直接打开presentation/index.html评估课堂展示。


[下载完整课程项目ZIP](../../../../downloads/mesh_prediction_round3_course_project.zip)
