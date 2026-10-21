# 实验环境与复用

实验环境为Windows、Intel Core Ultra 7 155H、Python 3.13.2、NumPy 2.3.4、SciPy 1.16.3、Matplotlib 3.10.7、scikit-learn 1.9.1、joblib 1.6.0；PDF检查使用PyMuPDF 1.28.0，排版使用已有TeX Live 2024。依赖固定于requirements.txt。

从作者已有移动网格研究项目原样复用geometry.py和variational_mesh.py，其Winslow能量、解析梯度与逆映射具有五项通过的测试。课设驱动在独立目录实现，未修改原研究项目。后续六次方向差分的结果在data/gradient_checks.json中保存。

汇报页调用作者已有reporting工具，使用其Markdown输入、KaTeX公式排版、本地图片嵌入和单文件HTML构建接口。必要源码保存在tools/reporting。生成与归档检查已通过，浏览器视觉及键盘验收尚未确认。

所有数值由本项目种子和配置生成。参考文献仅提供方法背景，不充当本项目实验结果。详细计时范围和复现方式见README及paper/paper.md。
