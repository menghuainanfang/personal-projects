"""Train one physical-displacement MLP using complete parameter-instance splits."""
from time import perf_counter
import json,random
import numpy as np
import torch
from src.common import ROOT,load_config,write_json,write_csv
from src.network import MeshMLP

def samples(ids):
    features=[];labels=[]
    for iid in ids:
        status=json.loads((ROOT/f'data/teacher/{iid}.json').read_text(encoding='utf-8'))
        if not (status['converged'] and status['valid']):
            continue
        d=np.load(ROOT/f'data/teacher/{iid}.npz')
        features.append(d['mu'])
        labels.append((d['X_teacher']-d['X0'])[~d['boundary_mask']].ravel())
    return np.array(features),np.array(labels)

def main():
    cfg=load_config();options=cfg['model'];seed=cfg['seed']
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    torch.set_num_threads(options['threads'])
    torch.use_deterministic_algorithms(True)
    split=json.loads((ROOT/'data/split.json').read_text(encoding='utf-8'))
    assert not set(split['train'])&set(split['validation'])
    assert not set(split['train'])&set(split['test'])
    assert not set(split['validation'])&set(split['test'])
    train_x,train_y=samples(split['train'])
    val_x,val_y=samples(split['validation'])
    mean,std=train_x.mean(axis=0),train_x.std(axis=0)
    scale=float(np.sqrt(np.mean(train_y**2)))
    assert np.all(std>0) and scale>0
    x=torch.tensor((train_x-mean)/std,dtype=torch.float32)
    y=torch.tensor(train_y/scale,dtype=torch.float32)
    vx=torch.tensor((val_x-mean)/std,dtype=torch.float32)
    vy=torch.tensor(val_y/scale,dtype=torch.float32)
    model=MeshMLP(train_y.shape[1],options['hidden'])
    optimizer=torch.optim.Adam(model.parameters(),lr=options['learning_rate'],weight_decay=options['weight_decay'])
    best=float('inf');wait=0;best_epoch=0;history=[];best_state=None
    start=perf_counter()
    for epoch in range(1,options['max_epochs']+1):
        model.train()
        order=torch.randperm(len(x))
        for begin in range(0,len(x),options['batch_size']):
            indices=order[begin:begin+options['batch_size']]
            optimizer.zero_grad()
            loss=torch.mean((model(x[indices])-y[indices])**2)
            loss.backward();optimizer.step()
        model.eval()
        with torch.inference_mode():
            train_loss=float(torch.mean((model(x)-y)**2))
            val_loss=float(torch.mean((model(vx)-vy)**2))
        history.append(dict(epoch=epoch,train_normalized_mse=train_loss,
            validation_normalized_mse=val_loss,train_coordinate_mse=train_loss*scale**2,
            validation_coordinate_mse=val_loss*scale**2))
        if val_loss<best-options['min_delta']:
            best=val_loss;wait=0;best_epoch=epoch
            best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else:
            wait+=1
        if epoch%200==0:
            print(f'epoch={epoch} train={train_loss:.6f}, val={val_loss:.6f}, best={best:.6f}',flush=True)
        if wait>=options['early_stopping_patience']:
            break
    duration=perf_counter()-start
    package=dict(state_dict=best_state,input_mean=mean.tolist(),input_std=std.tolist(),
        displacement_scale=scale,output_size=train_y.shape[1],hidden=options['hidden'],
        threads=options['threads'],best_epoch=best_epoch,seed=seed,
        train_ids=split['train'],validation_ids=split['validation'])
    torch.save(package,ROOT/'models/mlp.pt')
    write_csv(ROOT/'results/train_history.csv',history)
    result=dict(training_instances=len(x),validation_instances=len(vx),best_epoch=best_epoch,
        epochs=len(history),best_validation_normalized_mse=best,
        best_validation_coordinate_mse=best*scale**2,
        no_move_validation_coordinate_mse=float(np.mean(val_y**2)),
        parameters=sum(p.numel() for p in model.parameters()),training_seconds=duration,
        torch_version=torch.__version__,device='cpu',threads=options['threads'],
        input_mean=mean.tolist(),input_std=std.tolist(),displacement_scale=scale,
        normalization_fit='training instances only',test_used_for_model_selection=False)
    write_json(ROOT/'models/training_summary.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
