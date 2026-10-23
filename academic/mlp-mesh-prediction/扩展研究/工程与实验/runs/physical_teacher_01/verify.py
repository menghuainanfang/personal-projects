"""Verify persisted physical teacher labels against their energy records."""
from study import OUT,Problem,PhysicalEnergy,dump
import json
import numpy as np
def main():
    m=json.loads((OUT/"data/manifest.json").read_text(encoding="utf-8"))
    rows=[]
    for split in ["train","validation","test"]:
        for group in ["ID","center","narrow","broad"]:
            rec=next(r for r in m["splits"][split] if r["group"]==group)
            d=np.load(OUT/"data"/rec["relative_data_path"])
            status=json.loads((OUT/"data/teachers"/f"{rec['id']}.json").read_text(encoding="utf-8"))
            p=Problem(d["mu"] if "mu" in d else np.array(rec["spec"]["mu"]))
            discrepancy=abs(PhysicalEnergy(p).value(d["X"])-status["final_energy"])
            assert p.valid(d["X"])["valid"] and discrepancy<1e-12 and status["converged"]
            rows.append(dict(split=split,group=group,energy_difference=discrepancy))
    dump(OUT/"交付核验.json",dict(teacher_checks=rows))
    print("Verified saved physical labels across all groups and splits")
if __name__=="__main__":main()
