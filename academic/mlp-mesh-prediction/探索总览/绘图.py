from pathlib import Path
import csv,re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
REPO=Path(__file__).resolve().parents[3]
BASE=REPO/"academic/mlp-mesh-prediction"
OUT=BASE/"探索总览"
OUT.mkdir(exist_ok=True)
NEW=BASE/"扩展研究/工程与实验/runs/physical_teacher_01"
def read(name):return list(csv.DictReader((NEW/name).open(encoding="utf-8-sig")))
p=read("summary_prediction.csv");c=read("summary_refinement.csv")
plt.rcParams["font.sans-serif"]=["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"]=False
fig,axs=plt.subplots(1,3,figsize=(15,4.8))
groups=["ID","center","narrow","broad"];gx=np.arange(4)
for method,delta,color,title in [("Q_MLP",-.18,"#94a3b8","原Q模型重建X"),("physical_X",.18,"#2563eb","新物理教师X模型")]:
    vals=[float(next(z for z in p if z["method"]==method and z["group"]==g)["interpolation_rmse"]) for g in groups]
    axs[0].bar(gx+delta,vals,.36,label=title,color=color)
axs[0].set_xticks(gx,["原分布","中心偏移","窄而强","宽而弱"]);axs[0].legend(fontsize=9)
axs[0].set_ylabel("插值RMSE，越低越好");axs[0].set_title("400个测试例：各组均值\n每组100例，新旧模型各3个种子")
names=["规则初值","原Q教师X","Q重建X","新物理教师X"]
order=["regular","Q_teacher_X","Q_MLP","physical_X"]
for ax,key,title in [(axs[1],"iterations","同物理目标：平均迭代数"),(axs[2],"mean_seconds","同批运行：平均在线耗时（秒）")]:
    vals=[float(next(z for z in c if z["method"]==m)[key]) for m in order]
    bars=ax.bar(np.arange(4),vals,color=["#cbd5e1","#94a3b8","#ed8936","#2563eb"])
    ax.set_xticks(np.arange(4),names,rotation=20);ax.set_title(title+"\n20例，每种初值各重复2次")
    ax.set_ylim(0,max(vals)*1.18)
    for bar,v in zip(bars,vals):ax.text(bar.get_x()+bar.get_width()/2,v+max(vals)*.025,f"{v:.2f}",ha="center",fontsize=10)
fig.tight_layout();fig.savefig(OUT/"最新结果直观对比.png",dpi=180);plt.close(fig)
