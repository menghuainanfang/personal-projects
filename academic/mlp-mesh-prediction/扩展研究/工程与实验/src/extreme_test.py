"""Held-out combined parameter extrapolation, evaluated without model selection."""
from pathlib import Path
import json
import numpy as np
from teacher_general import make_teacher
from scale_study import RUN,dump,evaluate

def main():
    rng=np.random.default_rng(84991);root=RUN/"extreme_test"
    cases=[]
    for group in ["edge_narrow","near_boundary","outside_envelope"]:
        for _ in range(24):
            mu=[float(rng.uniform(.2,.8)),float(rng.uniform(.2,.8)),5.,.24]
            axis=int(rng.integers(2))
            mu[axis]=float(rng.uniform(.035,.10) if rng.random()<.5 else rng.uniform(.90,.965))
            if group=="edge_narrow":mu[2:]=[float(rng.uniform(10,14)),float(rng.uniform(.08,.12))]
            if group=="outside_envelope":mu[2:]=[float(rng.uniform(15,20)),float(rng.uniform(.035,.07))]
            cases.append((group,dict(kind="single",mu=mu)))
    manifest=dict(preset="extreme_72_preregistered_84991",splits={"test":[]});failures=[]
    for i,(group,spec) in enumerate(cases):
        uid=f"extreme_{i:03d}"
        try:
            t=make_teacher(12,spec);(root/"teachers").mkdir(parents=True,exist_ok=True)
            path=root/f"teachers/{uid}.npz"
            np.savez_compressed(path,**{k:t[k] for k in ["X0","X","Q","cells","boundary","monitor_cells"]})
            manifest["splits"]["test"].append(dict(id=uid,n=12,group=group,spec=spec,relative_data_path=f"teachers/{uid}.npz"))
        except Exception as e:failures.append(dict(id=uid,group=group,spec=spec,error=repr(e)))
    manifest.update(requested=72,valid=len(manifest["splits"]["test"]),failed=len(failures))
    dump(root/"manifest.json",manifest);dump(root/"failures.json",failures)
    # The checkpoint is fixed in advance; this test does not choose a seed or width.
    model=RUN/"models/gaussian_1200_w64_seed20261023/best_model.pt"
    evaluate(root,model,root/"evaluation")
if __name__=="__main__":main()
