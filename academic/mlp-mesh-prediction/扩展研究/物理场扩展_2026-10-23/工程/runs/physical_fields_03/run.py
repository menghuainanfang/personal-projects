"""Physical mesh teachers and manufactured Poisson tests on four field families."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:
    os.environ[key]='1'
import sys
import json
import csv
import numpy as np
import torch
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'runs/physical_X_01'))
sys.path.insert(0,str(ROOT/'runs/physical_hybrid_02'))
from teacher_general import topology,signed_areas
from physical_energy import PhysicalEnergy
from solvers import physical_lbfgs
torch.set_num_threads(1)


def field(points,spec):
    """Exact scalar u and isotropic monitor m, both differentiable in position."""
    kind=spec['kind']
    if kind in ('single','double'):
        u=torch.zeros(points.shape[:-1],dtype=points.dtype)
        m=torch.ones_like(u)
        for cx,cy,strength,width in spec['peaks']:
            g=torch.exp(-((points-torch.tensor([cx,cy],dtype=points.dtype))**2).sum(-1)/width**2)
            u=u+g
            m=m+strength*g
        return u,m
    if kind=='ring':
        d=((points-torch.tensor(spec['center'],dtype=points.dtype))**2).sum(-1)-spec['radius']**2
        return torch.tanh(30*d),1+spec['strength']*torch.exp(-(30*d)**2)
    if kind=='wave':
        d=points[...,1]-.5-.25*torch.sin(2*torch.pi*points[...,0]+spec['phase'])
        return torch.tanh(-30*d),1+spec['strength']*torch.exp(-(d/.1)**2)
    raise ValueError(kind)


class Problem:
    def __init__(self,n,spec):
        self.reference,self.cells,self.boundary,*_=topology(n)
        self.spec=spec
    def valid(self,x):
        area=float(signed_areas(x,self.cells).min())
        valid=bool(np.isfinite(x).all() and area>1e-10 and x.min()>=-1e-12
                   and x.max()<=1+1e-12 and
                   np.max(abs(x[self.boundary]-self.reference[self.boundary]))<=1e-12)
        return dict(valid=valid,min_area=area)


class FieldEnergy(PhysicalEnergy):
    def metric_value(self,points):
        return field(points,self.problem.spec)[1]


def quadrature(order):
    a,w=np.polynomial.legendre.leggauss(order)
    a=(a+1)/2
    w=w/2
    r,s=np.meshgrid(a,a,indexing='ij')
    wr,ws=np.meshgrid(w,w,indexing='ij')
    bary=np.stack((1-r-(1-r)*s,r,(1-r)*s),axis=-1).reshape(-1,3)
    weights=(2*wr*ws*(1-r)).ravel()
    return bary,weights


def exact(points,spec,forcing=False):
    x=torch.tensor(points,dtype=torch.float64,requires_grad=forcing)
    u,_=field(x,spec)
    if not forcing:
        return u.detach().numpy()
    grad=torch.autograd.grad(u.sum(),x,create_graph=True)[0]
    laplace=sum(torch.autograd.grad(grad[:,axis].sum(),x,retain_graph=True)[0][:,axis]
                for axis in range(2))
    return -laplace.detach().numpy()


def poisson(x,cells,boundary,spec,order=8):
    """P1 FEM for -Δu=f with exact Dirichlet data on all four sides."""
    tri=x[cells]
    edges=np.stack((tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=-1)
    areas=np.linalg.det(edges)/2
    gradients=np.array([[-1.,-1.],[1.,0.],[0.,1.]])@np.linalg.inv(edges)
    local=areas[:,None,None]*(gradients@gradients.transpose(0,2,1))
    rows=np.broadcast_to(cells[:,:,None],local.shape).ravel()
    cols=np.broadcast_to(cells[:,None,:],local.shape).ravel()
    stiffness=coo_matrix((local.ravel(),(rows,cols)),shape=(len(x),len(x))).tocsr()
    bary,weights=quadrature(order)
    points=np.einsum('qv,kvd->kqd',bary,tri)
    forcing=exact(points.reshape(-1,2),spec,True).reshape(len(cells),-1)
    load_local=areas[:,None]*np.einsum('q,kq,qv->kv',weights,forcing,bary)
    load=np.zeros(len(x))
    np.add.at(load,cells.ravel(),load_local.ravel())
    uh=exact(x,spec)
    inside=np.flatnonzero(~boundary)
    fixed=np.flatnonzero(boundary)
    rhs=load[inside]-stiffness[inside][:,fixed]@uh[fixed]
    uh[inside]=spsolve(stiffness[inside][:,inside],rhs)
    residual=float(np.max(abs(stiffness[inside]@uh-load[inside])))
    return uh,residual


def l2_error(x,cells,uh,spec,order=8):
    bary,weights=quadrature(order)
    points=np.einsum('qv,kvd->kqd',bary,x[cells])
    reference=exact(points.reshape(-1,2),spec).reshape(len(cells),-1)
    numerical=uh[cells]@bary.T
    return float(np.sqrt(np.sum(signed_areas(x,cells)*((numerical-reference)**2@weights))))


def cases():
    for variant in range(2):
        yield dict(kind='single',variant=variant,peaks=[[.4+.15*variant,.5,6.,.16]])
        yield dict(kind='double',variant=variant,peaks=[[.3,.35+.1*variant,5.,.14],[.7,.65-.1*variant,7.,.12]])
        yield dict(kind='ring',variant=variant,center=[.5,.5],radius=.22+.04*variant,strength=8.)
        yield dict(kind='wave',variant=variant,phase=.4*variant,strength=8.)


def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    specs=list(cases())
    (OUT/'config.json').write_text(json.dumps(dict(specs=specs,n=[12,24],
        objective='Huang theta=1/3 p=2 with position-dependent scalar M=mI',
        solver='L-BFGS, gradient tolerance 1e-5, fixed full boundary',
        pde='-Laplace(u)=f, manufactured exact u, exact Dirichlet boundary',
        quadrature_order=8,training='no new neural training'),indent=2),encoding='utf8')
    rows=[]
    figures={}
    for spec in specs:
        for n in [12,24]:
            name=f"{spec['kind']}_{spec['variant']}_n{n}"
            problem=Problem(n,spec)
            x0=problem.reference
            energy=FieldEnergy(problem)
            rng=np.random.default_rng(20261023)
            direction=rng.normal(size=x0.shape)
            direction[problem.boundary]=0
            direction/=np.linalg.norm(direction)
            h=1e-6
            _,gradient=energy.value_gradient(x0)
            fd=(energy.value(x0+h*direction)-energy.value(x0-h*direction))/(2*h)
            ad=float(np.sum(gradient*direction))
            gradient_error=abs(fd-ad)/max(1.,abs(fd),abs(ad))
            if gradient_error>1e-6:
                raise RuntimeError(f'{name}: field energy derivative mismatch')
            # Match the original Gaussian energy before relying on the extension.
            if spec['kind']=='single':
                problem.mu=np.array(spec['peaks'][0])
                legacy=PhysicalEnergy(problem)
                lv,lg=legacy.value_gradient(x0)
                if abs(lv-energy.value(x0))>1e-12 or np.max(abs(lg-gradient))>1e-12:
                    raise RuntimeError('Single Gaussian objective changed')
            result=physical_lbfgs(problem,x0,FieldEnergy)
            x=result['X']
            if not problem.valid(x)['valid']:
                raise RuntimeError(f'{name}: invalid physical mesh')
            energies=np.array([r['energy'] for r in result['history']])
            if np.any(np.diff(energies)>1e-12*np.maximum(1.,abs(energies[:-1]))):
                raise RuntimeError(f'{name}: energy increased')
            uniform,res0=poisson(x0,problem.cells,problem.boundary,spec)
            adapted,res1=poisson(x,problem.cells,problem.boundary,spec)
            if max(res0,res1)>1e-9:
                raise RuntimeError(f'{name}: Poisson linear solve residual')
            e0=l2_error(x0,problem.cells,uniform,spec)
            e1=l2_error(x,problem.cells,adapted,spec)
            high0=l2_error(x0,problem.cells,uniform,spec,12)
            high1=l2_error(x,problem.cells,adapted,spec,12)
            quadrature_change=max(abs(high0-e0)/high0,abs(high1-e1)/high1)
            if quadrature_change>.01:
                raise RuntimeError(f'{name}: L2 quadrature changed by more than one percent')
            row=dict(id=name,kind=spec['kind'],variant=spec['variant'],n=n,
                nodes=len(x),**result['summary'],min_area=problem.valid(x)['min_area'],
                gradient_check=gradient_error,poisson_residual=max(res0,res1),
                uniform_l2=e0,adapted_l2=e1,error_ratio=e1/e0,quadrature_change=quadrature_change,
                uniform_interpolation_l2=l2_error(x0,problem.cells,exact(x0,spec),spec),
                adapted_interpolation_l2=l2_error(x,problem.cells,exact(x,spec),spec))
            rows.append(row)
            np.savez_compressed(OUT/f'{name}.npz',X0=x0,X=x,cells=problem.cells,
                boundary=problem.boundary,u_uniform=uniform,u_adapted=adapted,
                field_log_m=np.log(field(torch.tensor(np.stack(np.meshgrid(
                    np.linspace(0,1,32),np.linspace(0,1,32)),axis=-1),dtype=torch.float64),spec)[1].numpy()))
            write_csv(OUT/f'{name}_history.csv',result['history'])
            write_csv(OUT/'results.csv',rows)
            if spec['variant']==0 and n==24:
                figures[spec['kind']]=(problem,x,uniform,adapted,row)
            print(name,'converged',row['converged'],'PDE ratio',round(e1/e0,4),flush=True)
    fig,axes=plt.subplots(4,3,figsize=(12,14),constrained_layout=True)
    for axrow,(kind,(p,x,u0,u1,row)) in zip(axes,figures.items()):
        for ax,nodes,title in [(axrow[0],p.reference,'Regular'),(axrow[1],x,'Physical teacher')]:
            ax.triplot(nodes[:,0],nodes[:,1],p.cells,lw=.35)
            ax.set_title(f'{kind}: {title}')
            ax.set_aspect('equal')
        axrow[2].bar(['Regular','Adapted'],[row['uniform_l2'],row['adapted_l2']])
        axrow[2].set_title(f"Poisson L2 ratio {row['error_ratio']:.3f}")
    fig.savefig(OUT/'meshes_and_pde.png',dpi=140)
    plt.close(fig)
    summaries=[]
    for kind in ['single','double','ring','wave']:
        for n in [12,24]:
            group=[r for r in rows if r['kind']==kind and r['n']==n]
            summaries.append(dict(kind=kind,n=n,cases=len(group),
                converged=sum(r['converged'] for r in group),
                mean_error_ratio=float(np.mean([r['error_ratio'] for r in group])),
                worst_error_ratio=max(r['error_ratio'] for r in group)))
    write_csv(OUT/'summary.csv',summaries)
    (OUT/'completion.json').write_text(json.dumps(dict(cases=len(rows),
        converged=sum(r['converged'] for r in rows),
        improved=sum(r['error_ratio']<1 for r in rows),
        max_gradient_error=max(r['gradient_check'] for r in rows),
        max_quadrature_change=max(r['quadrature_change'] for r in rows),
        summary=summaries),indent=2),encoding='utf8')


if __name__=='__main__':
    main()
