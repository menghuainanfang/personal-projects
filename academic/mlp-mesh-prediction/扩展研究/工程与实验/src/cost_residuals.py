"""Apply the common combined-L2 endpoint criterion to saved timing records."""
from scale_study import *
def main():
    data=RUN/"data/gaussian_1200"
    records=json.loads((data/"manifest.json").read_text(encoding="utf-8"))["splits"]["test"]
    byid={r["id"]:r for r in records}
    path=RUN/"models/gaussian_1200_w64_seed20261023/evaluation/baseline_cost.csv"
    rows=readcsv(path);inside=topology(12)[3]
    for row in rows:
        if row["method"]=="sparse_direct":
            rec=byid[row["id"]];d=np.load(data/rec["relative_data_path"])
            k=matrix(np.asarray(rec["spec"]["mu"]))
            row["residual"]=float(np.linalg.norm((k@d["Q"])[inside]))
        assert float(row["residual"])<=1e-5
        assert float(row["max_coordinate_difference"])<=1e-6
    csvout(path,rows)
    dump(path.parent/"matched_precision.json",dict(rows=len(rows),all_passed=True,
        residual_norm="combined interior L2",acceptance_tolerance=1e-5,
        cg_atol_per_axis=1e-7,max_coordinate_difference=1e-6,
        endpoint_verification="Endpoint checks outside repeated timing; measured online times retained"))
if __name__=="__main__":main()
