"""No-training baseline for existing n12 field-supervision test cases."""
from pathlib import Path
import json,csv
import numpy as np
import torch
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
RUN=ROOT/"runs/physical_field_training_04"
def write(name,rows):
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
def main():
    manifest=json.loads((RUN/"manifest.json").read_text(encoding="utf-8"))
    ck=torch.load(RUN/"model.pt",map_location="cpu",weights_only=True)
    std=ck["std"].numpy()
    train=[r for r in manifest if r["split"]=="train" and r["n"]==12]
    test=[r for r in manifest if r["split"]=="test" and r["n"]==12]
    fields=np.stack([np.load(RUN/r["path"])["log_m"] for r in train])
    targets=np.stack([np.load(RUN/r["path"])["X"] for r in train])
    original=list(csv.DictReader((RUN/"test_results.csv").open(encoding="utf-8-sig")))
    rows=[]
    for r in test:
        data=np.load(RUN/r["path"])
        distance=np.mean(((fields-data["log_m"])/std)**2,axis=1)
        i=int(np.argmin(distance))
        reference=data["X"];initial=data["X0"]
        error=float(np.linalg.norm(targets[i]-reference)/np.linalg.norm(reference-initial))
        net=next(z for z in original if z["id"]==r["id"] and int(z["n"])==12)
        rows.append(dict(id=r["id"],kind=r["spec"]["kind"],neighbor=train[i]["id"],
            neighbor_kind=train[i]["spec"]["kind"],nearest_error=error,
            neural_error=float(net["relative_teacher_error"])))
    write("nearest_per_case.csv",rows)
    summary=[]
    for kind in ["single","double","ring","wave","ALL"]:
        sub=[r for r in rows if kind=="ALL" or r["kind"]==kind]
        summary.append(dict(kind=kind,n=len(sub),nearest_error=float(np.mean([r["nearest_error"] for r in sub])),
            neural_error=float(np.mean([r["neural_error"] for r in sub])),
            neural_wins=sum(r["neural_error"]<r["nearest_error"] for r in sub)))
    write("nearest_summary.csv",summary)
    history=list(csv.DictReader((RUN/"training_log.csv").open(encoding="utf-8-sig")))
    best=min(history,key=lambda r:float(r["validation_mse"]))
    (OUT/"loss_diagnosis.json").write_text(json.dumps(dict(best=best,last=history[-1]),indent=2),encoding="utf-8")
    print(json.dumps(dict(nearest_control=summary,loss_best=best,loss_last=history[-1]),indent=2))
if __name__=="__main__":main()
