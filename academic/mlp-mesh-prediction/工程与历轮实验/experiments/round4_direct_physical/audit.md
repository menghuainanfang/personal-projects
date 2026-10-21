# 坐标接口与目标审计

## 已有Q目标

src/teacher.py中的Problem在规则物理网格X0上冻结面积、边矩阵及度量。src/variational_mesh.py的WinslowEnergy接收计算节点Q，使用J=B(Q)E(X0)^{-1}，计算I_h(Q)=sum |K(X0)| tr(J M_K^{-1} J^T)。梯度仅对Q求导。最终物理网格是原分片线性逆映射X=R(Q)。

src/network.py中的旧模型输出内部物理位移。P=X0+位移是原始物理预测；仅物理退缩得到P_safe；safe_prediction.py还会执行Q=C(P_safe)及X=R(Q)。后者改变物理预测，是进入Q求解器前的状态转换。第四轮直接物理预测分支仅执行物理合法性检查与必要退缩，不调用C或R。

实验A使用200个已保存教师的140/30/30拆分与三个展示实例，重新运行模型和指标。旧实验CSV仅作历史记录，不作为新结果来源。Q模型使用第三轮预先固定的20261021权重，教师、两个模型与求解器均不修改。

## 独立物理目标

采用Huang、Kamenski、Russell（2015）式(11)的均匀分布/对齐泛函，在物理三角形重心做单点求积，以物理内部节点X为变量。固定参考边矩阵为Ehat，物理边矩阵为E(X)，逆Jacobian为J=Ehat E(X)^{-1}。

令m=1+A exp(-|x_K(X)-c|²/sigma²)、rho=m、d=2、p=2、theta=1/3，定义

$$
E_{\rm phys}(X)=\sum_K |K(X)|m_K(X)
\left[\frac13\left(\frac{\|J_K(X)\|_F^2}{m_K(X)}\right)^2+
\frac43\left(\frac{\det J_K(X)}{m_K(X)}\right)^2\right].
$$

面积、Jacobian、重心和度量均随X变化；PyTorch float64自动微分计算整个离散表达式的导数，再将边界梯度置零。这里没有将物理X送入旧WinslowEnergy，也没有复用其冻结Q梯度。

选择p=2的目标包含密度控制项。对给定m和单元形状，贡献随面积倒数增长；对退化单元，正定有界的m不能抵消逆Jacobian的增长。坐标及度量在单位方形上无量纲，两个括号项量纲一致，正面积时能量为正。连续泛函的存在性结果不自动证明这份重心求积、固定边界离散问题的唯一极小点；这里只检验梯度、合法性、下降与停止条件。

四个方向差分检查覆盖规则及变形物理网格，步长1e-6。两种初值采用完全相同的物理目标、投影梯度、BB谱步长提议和单调Armijo回溯。BB提议为(s·s)/(s·y)，曲率非正则使用0.1，提议限制[1e-8,1]。只接受保持固定边界、区域范围、正面积且满足真实能量充分下降的节点。

本轮候选式中只含一次trace的物理Winslow目标，在二维标量度量下局部均匀缩放会抵消面积与逆Jacobian尺度，缺少同等明确的等分布项。因此采用上式作独立物理优化实验，不把它视为原Q目标的等价改写。

## 比较与计时

实验A跨网格仅比较节点误差、几何质量与同一解析场的插值RMSE。实验B仅在同一E_phys下比较规则物理初值与旧X模型物理初值的成本。I_h和E_phys的值、梯度阈值及耗时不跨目标排序。

模型和固定拓扑接口在计时前加载。实验A分别计时输入归一化/推理与安全/重建；实验B包含推理、安全、物理能量对象建立及优化。每个实例交替顺序重复三次。指标、采样插值、文件读写不计入生成/优化时间。存储教师是参考标签，其读盘耗时不作为传统在线求解时间；既有教师和训练成本单列。

固定拓扑为单位方形三角剖分，边界逐节点保持不变，所有状态检查全部三角形有向面积。没有对本项目以外的任意拓扑声称全局合法性。

## 核实的文献

Huang W., Kamenski L., Russell R. D. A comparative numerical study of meshing functionals for variational mesh adaptation. 2015. https://arxiv.org/abs/1503.04709 ，正文式(11)及其参数说明已核对。

Barzilai J., Borwein J. M. Two-Point Step Size Gradient Methods. IMA Journal of Numerical Analysis, 1988, 8(1):141–148. https://doi.org/10.1093/imanum/8.1.141 ，期刊题名、作者、年份和页码已核对。

Song W., Zhang M., Wallwork J. G., et al. M2N: Mesh Movement Networks for PDE Solvers. NeurIPS 35, 2022. https://proceedings.neurips.cc/paper_files/paper/2022/hash/2f88d8061f12abae9d14d376fd69c933-Abstract-Conference.html ，会议页面已核对。
