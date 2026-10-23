"""Physical-coordinate equidistribution/alignment energy and Armijo descent."""
from time import perf_counter
import numpy as np
import torch
torch.set_num_threads(1)

OPTIONS=dict(theta=1/3,p=2.,gradient_tolerance=1e-5,max_iterations=3000,
             max_energy_evaluations=30000,armijo_c1=1e-4,beta=.5,
             max_backtracks=40,initial_step=.1)

class PhysicalEnergy:
    """Centroid quadrature of the Huang functional, differentiated in X."""
    def __init__(self,problem):
        self.problem=problem
        self.cells=torch.tensor(problem.cells,dtype=torch.long)
        ref=torch.tensor(problem.reference,dtype=torch.float64)[self.cells]
        self.edges=torch.stack((ref[:,1]-ref[:,0],ref[:,2]-ref[:,0]),dim=-1)
        self.det_ref=torch.linalg.det(self.edges)

    def metric_value(self,points):
        mu=torch.as_tensor(self.problem.mu,dtype=torch.float64)
        return 1+mu[2]*torch.exp(-((points-mu[:2])**2).sum(dim=1)/mu[3]**2)

    def tensor_value(self,x):
        tri=x[self.cells]
        b=torch.stack((tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),dim=-1)
        det=b[:,0,0]*b[:,1,1]-b[:,0,1]*b[:,1,0]
        inv=torch.stack((b[:,1,1],-b[:,0,1],-b[:,1,0],b[:,0,0]),dim=1).reshape(-1,2,2)/det[:,None,None]
        j=self.edges@inv
        centers=tri.mean(dim=1)
        m=self.metric_value(centers)
        trace=(j*j).sum(dim=(1,2))/m
        detj=self.det_ref/det
        theta,p=OPTIONS['theta'],OPTIONS['p']
        return (.5*det*m*(theta*trace**p+(1-2*theta)*2**p*(detj/m)**p)).sum()

    def value(self,x):
        with torch.no_grad():
            return float(self.tensor_value(torch.as_tensor(x,dtype=torch.float64)))

    def value_gradient(self,x):
        t=torch.tensor(x,dtype=torch.float64,requires_grad=True)
        value=self.tensor_value(t)
        g=torch.autograd.grad(value,t)[0].detach().numpy()
        g[self.problem.boundary]=0.
        return float(value.detach()),g

def solve(problem,initial,options=None):
    settings=OPTIONS if options is None else options
    started=perf_counter();energy=PhysicalEnergy(problem);x=initial.copy()
    if not problem.valid(x)['valid']:raise ValueError('Initial physical mesh is invalid')
    value,g=energy.value_gradient(x);evaluations=1
    history=[];backtracks=0;illegal=0;alpha=settings['initial_step'];stop='iteration_limit'
    # The same spectral proposal and Armijo rule are used for both initializations.
    for k in range(settings['max_iterations']+1):
        norm=float(np.linalg.norm(g))
        history.append(dict(iteration=k,energy=value,gradient_norm=norm,energy_evaluations=evaluations,
                            backtracks=backtracks,min_area=problem.valid(x)['min_area'],alpha=alpha))
        if norm<=settings['gradient_tolerance']:stop='converged';break
        if k==settings['max_iterations']:break
        accepted=False;alpha=float(np.clip(alpha,1e-8,1.))
        for trial in range(settings['max_backtracks']):
            if evaluations+2>settings['max_energy_evaluations']:stop='energy_budget';break
            candidate=x-alpha*g
            if problem.valid(candidate)['valid']:
                cv=energy.value(candidate);evaluations+=1
                if np.isfinite(cv) and cv<=value-settings['armijo_c1']*alpha*norm**2:
                    cv,cg=energy.value_gradient(candidate);evaluations+=1
                    if np.all(np.isfinite(cg)):accepted=True;break
            else:illegal+=1
            alpha*=settings['beta'];backtracks+=1
        if not accepted:
            if stop!='energy_budget':stop='line_search_stalled'
            break
        displacement=(candidate-x).ravel();change=(cg-g).ravel()
        curvature=float(np.dot(displacement,change))
        proposal=float(np.dot(displacement,displacement)/curvature) if curvature>0 else settings['initial_step']
        x,value,g=candidate,cv,cg
        alpha=proposal
    return dict(X=x,history=history,summary=dict(converged=stop=='converged',stop_reason=stop,
        iterations=history[-1]['iteration'],energy_evaluations=evaluations,backtracks=backtracks,
        illegal_candidates=illegal,initial_energy=history[0]['energy'],final_energy=value,
        final_gradient_norm=float(np.linalg.norm(g)),seconds=perf_counter()-started))
