"""Package the complete inputs and outputs required by this comparison."""
from pathlib import Path
import csv,json,zipfile
import numpy as np
import torch,sys
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/"src"))
from train_fixed_q import read_data
from teacher_general import signed_areas
from physical_energy import PhysicalEnergy
from run import Problem

def main():
    data=ROOT/"runs/scale_study_01/data/gaussian_1200"
    _,_,labels=read_data(data,"train")
    scale=float(np.sqrt(np.mean(labels**2)))
    for seed in [20261023,20261024,20261025]:
        p=torch.load(OUT/"models"/f"X_w128_seed{seed}"/"best_model.pt",map_location="cpu",weights_only=True)
        assert p["target"]=="physical_X_displacement" and np.isclose(p["label_scale"],scale,rtol=1e-12)
    rows=list(csv.DictReader((OUT/"physical_per_case.csv").open(encoding="utf-8-sig")))
    assert len(rows)==160
    energy_difference=[];minimum_area=float("inf")
    for row in rows:
        if int(row["repeat"]):continue
        d=np.load(OUT/"refinement_states"/f"{row['id']}_{row['method']}.npz")
        problem=Problem(d["mu"]);assert problem.valid(d["X"])["valid"]
        energy_difference.append(abs(PhysicalEnergy(problem).value(d["X"])-float(row["final_energy"])))
        minimum_area=min(minimum_area,float(signed_areas(d["X"],d["cells"]).min()))
    assert max(energy_difference)<1e-12
    records=list(csv.DictReader((OUT/"prediction_per_case.csv").open(encoding="utf-8-sig")))
    assert len(records)==2400
    check=dict(prediction_rows=2400,physical_rows=160,verified_physical_states=80,
        labels_target="physical_X_displacement",maximum_saved_energy_difference=max(energy_difference),
        minimum_refined_signed_area=minimum_area)
    (OUT/"交付核验.json").write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding="utf-8")
    index=ROOT/"results_index.csv"
    rows=list(csv.DictReader(index.open(encoding="utf-8-sig")))
    for seed in [20261023,20261024,20261025]:
        weight=f"runs/physical_X_01/models/X_w128_seed{seed}/best_model.pt"
        if not any(r["weights"]==weight for r in rows):
            rows.append(dict(run="runs/physical_X_01",weights=weight,
                configuration="runs/physical_X_01/config.json",metrics="runs/physical_X_01/prediction_per_case.csv"))
    with index.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["run","weights","configuration","metrics"]);w.writeheader();w.writerows(rows)
    paths=[ROOT/"README_物理网格补充实验.md",ROOT/"environment.json"]
    paths+=list((ROOT/"src").glob("*.py"))
    paths += [p for p in OUT.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [p for p in data.rglob("*") if p.is_file()]
    for seed in [20261023,20261024,20261025]:
        m=ROOT/"runs/scale_study_01/models"/f"gaussian_1200_w128_seed{seed}"
        paths += [m/name for name in ["best_model.pt","training_summary.json","run_config.json","loss_history.csv"]]
    archive=ROOT.parent/"直接物理网格预测与精修_完整复现包.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in paths:z.write(p,p.relative_to(ROOT.parent))
    print(json.dumps(dict(archive=str(archive),files=len(paths),MiB=archive.stat().st_size/2**20,verification=check),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
