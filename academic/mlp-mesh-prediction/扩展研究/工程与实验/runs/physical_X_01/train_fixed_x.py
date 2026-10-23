"""Train direct physical-X displacement on existing n=12 Gaussian teachers.

The architecture and training protocol match the fixed-Q comparison.
Model selection uses validation data.
"""
import argparse, csv, json, os, pathlib, random
import numpy as np
import torch
from torch import nn


class FixedMLP(nn.Module):
    def __init__(self, d_out, width=64):
        super().__init__()
        self.layers=nn.Sequential(nn.Linear(4,width),nn.Tanh(),nn.Linear(width,width),nn.Tanh(),nn.Linear(width,d_out))
    def forward(self, x):return self.layers(x)


def read_data(root:pathlib.Path, split:str):
    m=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    items=m['splits'][split]
    assert items, f'no {split} data'
    if any(r['n']!=12 or r['spec']['kind']!='single' for r in items):
        raise ValueError('FixedMLP training only supports n=12 and single Gaussian; use new variable field model for other kinds')
    f=[];q=[];x=[]
    for rec in items:
        d=np.load(root/rec['relative_data_path'])
        nodes=d['X0'];mask=~d['boundary']
        f.append(rec['spec']['mu']);q.append((d['Q']-nodes)[mask].ravel());x.append((d['X']-nodes)[mask].ravel())
    return np.asarray(f,dtype=np.float64),np.asarray(q),np.asarray(x)


def train(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    if args.device=='cpu':torch.set_num_threads(1)
    if args.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA not available; choose --device cpu')
    root=args.data.resolve();a,_,b=read_data(root,'train');c,_,d=read_data(root,'validation')
    mean=a.mean(0);std=np.maximum(a.std(0),1e-12);scale=float(np.sqrt(np.mean(b**2)))
    if scale<=0:raise ValueError('zero X displacement labels')
    device=torch.device(args.device)
    x=torch.tensor((a-mean)/std,dtype=torch.float32,device=device)
    y=torch.tensor(b/scale,dtype=torch.float32,device=device)
    vx=torch.tensor((c-mean)/std,dtype=torch.float32,device=device)
    vy=torch.tensor(d/scale,dtype=torch.float32,device=device)
    model=FixedMLP(y.shape[1],args.width).to(device)
    opt=torch.optim.Adam(model.parameters(),lr=args.lr,weight_decay=1e-6)
    best=float('inf');wait=0;state=None;history=[];best_epoch=0
    for e in range(args.epochs):
        model.train();ind=torch.randperm(len(x),device=device)
        for j in range(0,len(x),args.batch):
            ix=ind[j:j+args.batch];opt.zero_grad(set_to_none=True)
            loss=((model(x[ix])-y[ix])**2).mean()
            loss.backward();opt.step()
        model.eval()
        with torch.inference_mode():
            tl=float(((model(x)-y)**2).mean().item());vl=float(((model(vx)-vy)**2).mean().item())
        history.append({'epoch':e+1,'train_mse':tl,'validation_mse':vl})
        if vl<best-args.min_delta:
            best=vl;wait=0;best_epoch=e+1
            state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else:wait+=1
        if (e+1)%100==0:print('epoch',e+1,'train',tl,'val',vl,flush=True)
        if wait>=args.patience:break
    ckpt={'state_dict':state,'input_mean':mean.tolist(),'input_std':std.tolist(),
          'label_scale':scale,'width':args.width,'output_dim':b.shape[1],
          'seed':args.seed,'train_samples':len(a),'validation_samples':len(c),
          'target':'physical_X_displacement','best_epoch':best_epoch,'best_val_normalized_mse':best}
    torch.save(ckpt,out/'best_model.pt')
    with (out/'loss_history.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=history[0].keys());w.writeheader();w.writerows(history)
    (out/'training_summary.json').write_text(json.dumps({k:v for k,v in ckpt.items() if k!='state_dict'},indent=2),encoding='utf-8')
    print('TRAINED',out,'best epoch',best_epoch,'val',best,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--epochs',type=int,default=2000)
    p.add_argument('--patience',type=int,default=200)
    p.add_argument('--min-delta',type=float,default=1e-7)
    p.add_argument('--seed',type=int,default=20261023)
    p.add_argument('--batch',type=int,default=32)
    p.add_argument('--width',type=int,choices=[64,128,256],default=64)
    p.add_argument('--lr',type=float,default=0.001)
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    train(p.parse_args())

