"""Reference-paper mesh smoothing with the frozen Huang Q functional."""
import copy
import numpy as np
import torch
from study import ROOT,CFG,Problem,solve_state,edge_matrices,write_csv,write_json

class FrozenHuang:
    def __init__(self,problem):
        self.cells=torch.tensor(problem.cells)
        self.inv=torch.tensor(np.linalg.inv(edge_matrices(problem.X0,problem.cells)),dtype=torch.float64)
        from src.geometry import signed_triangle_areas
        self.areas=torch.tensor(signed_triangle_areas(problem.X0,problem.cells),dtype=torch.float64)

    def value_gradient(self,q):
        t=torch.tensor(q,dtype=torch.float64,requires_grad=True);tri=t[self.cells]
        b=torch.stack((tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),dim=-1)
        j=b@self.inv;trace=(j*j).sum(dim=(1,2))
        det=j[:,0,0]*j[:,1,1]-j[:,0,1]*j[:,1,0]
        energy=(self.areas*(trace**2/3+4*det**2/3)).sum()
        return float(energy.detach()),torch.autograd.grad(energy,t)[0].detach().numpy()

def main():
    rows=[]
    for n in [12,20]:
        for seed in [17,29]:
            cfg=copy.deepcopy(CFG);cfg['mesh']['n']=n
            cfg['teacher'].update(max_iterations=5000,gradient_tolerance=1e-6)
            p=Problem([.5,.5,0.,.24],cfg)
            rng=np.random.default_rng(seed)
            p.X0[~p.boundary]+=rng.uniform(-.15/n,.15/n,size=(int((~p.boundary).sum()),2))
            assert p.valid(p.X0)['valid']
            p.energy=FrozenHuang(p)
            result=solve_state(p)
            before=float(np.linalg.norm(p.X0-p.reference))
            after=float(np.linalg.norm(result['X']-p.reference))
            row=dict(n=n,nodes=len(p.reference),seed=seed,converged=result['summary']['converged'],
                iterations=result['summary']['iterations'],gradient_norm=result['summary']['final_gradient_norm'],
                relative_remaining_perturbation=after/before,initial_min_area=p.valid(p.X0)['min_area'],
                final_min_area=p.valid(result['X'])['min_area'],final_valid=p.valid(result['X'])['valid'])
            rows.append(row)
            np.savez_compressed(ROOT/f'results/meshes/smoothing_{n}_{seed}.npz',
                X_initial=p.X0,X_final=result['X'],reference=p.reference,cells=p.cells)
            print(row,flush=True)
    write_csv(ROOT/'results/paper_smoothing.csv',rows)
    write_json(ROOT/'results/paper_correspondence.json',dict(
        source='Huang & Kamenski, JCP 301 (2015), 322-337, arXiv:1410.7872v2',
        checked_local_pdf_pages=[1,12,13,14],printed_pages=[1,12,13,14],
        smoothing='Example 4.1: M=I, Huang theta=1/3 p=2, Q optimization and R reconstruction',
        differences=['Armijo minimization instead of ode15s integration to t=1',
                     'fixed own perturbation seeds and diagonal triangulation'],
        wave='Example 4.2 exact phase-zero analytic field, custom bounded isotropic monitor',
        not_reproduced=['paper Hessian-based monitor and recovery choices','horseshoe-domain cases','3D nine-sphere case']))

if __name__=='__main__':main()
