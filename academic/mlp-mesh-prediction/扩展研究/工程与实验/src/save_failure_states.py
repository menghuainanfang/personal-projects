"""Store invalid raw Q predictions together with their safe physical outputs."""
from scale_study import *
def save(data,modelpath,out):
    failed=json.loads((out/"failures.json").read_text(encoding="utf-8"))
    if not failed:return 0
    pkg=torch.load(modelpath,map_location="cpu",weights_only=True)
    net=FixedMLP(pkg["output_dim"],pkg["width"]);net.load_state_dict(pkg["state_dict"]);net.eval()
    torch.set_num_threads(1)
    records=json.loads((data/"manifest.json").read_text(encoding="utf-8"))["splits"]["test"]
    byid={r["id"]:r for r in records};x0,cells,boundary,inside,*_=topology(12)
    target=out/"failure_states";target.mkdir(exist_ok=True)
    for row in failed:
        rec=byid[row["id"]];mu=np.asarray(rec["spec"]["mu"])
        vec=(mu-np.asarray(pkg["input_mean"]))/np.asarray(pkg["input_std"])
        with torch.inference_mode():
            disp=net(torch.tensor(vec,dtype=torch.float32)[None]).numpy().reshape(-1,2)*pkg["label_scale"]
        raw=x0.copy();raw[inside]+=disp
        q,x,*_=predict(net,pkg,mu);d=np.load(data/rec["relative_data_path"])
        np.savez_compressed(target/(row["id"]+".npz"),mu=mu,raw_Q=raw,safe_Q=q,
            safe_X=x,teacher_X=d["X"],X0=x0,cells=cells,boundary=boundary)
    return len(failed)
if __name__=="__main__":
    model=RUN/"models/gaussian_1200_w64_seed20261023/best_model.pt"
    total=save(RUN/"extreme_test",model,RUN/"extreme_test/evaluation")
    for folder in (RUN/"models").iterdir():
        cfg=json.loads((folder/"run_config.json").read_text(encoding="utf-8"))
        total+=save(RUN/"data"/cfg["dataset"],folder/"best_model.pt",folder/"evaluation")
    print("Saved raw/safe failure states:",total)
