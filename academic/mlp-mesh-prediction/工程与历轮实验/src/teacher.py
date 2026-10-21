"""Frozen-metric Winslow optimization and explicit physical/state transfer."""
from time import perf_counter
import numpy as np
from src.common import fixed_mesh,metric_tensor
from src.variational_mesh import WinslowEnergy,reconstruct_physical
from src.geometry import signed_triangle_areas
from validate_mesh import mesh_status

class Problem:
    def __init__(self,mu,config):
        self.config=config
        self.mu=np.asarray(mu,dtype=float)
        self.reference,self.cells,self.boundary=fixed_mesh(config['mesh']['n'])
        self.X0=self.reference.copy()
        self.metric=metric_tensor(self.X0[self.cells].mean(axis=1),self.mu)
        self.energy=WinslowEnergy(self.X0,self.cells,self.metric)
        self.epsilon=float(config['mesh']['area_epsilon'])

    def physical(self,q):
        x=reconstruct_physical(q,self.X0,self.cells,self.reference)
        x[self.boundary]=self.X0[self.boundary]
        return x

    def physical_to_state(self,x):
        """Interpolate the physical-to-reference map at the frozen physical nodes."""
        q=reconstruct_physical(x,self.reference,self.cells,self.X0)
        q[self.boundary]=self.reference[self.boundary]
        return q

    def valid(self,nodes):
        return mesh_status(nodes,self.reference,self.cells,self.boundary,self.epsilon)

def solve_state(problem,q_initial=None):
    started=perf_counter()
    settings=problem.config['teacher']
    q=(problem.reference if q_initial is None else q_initial).copy()
    if not problem.valid(q)['valid']:
        raise ValueError('Invalid initial computational mesh')
    x=problem.physical(q)
    if not problem.valid(x)['valid']:
        raise ValueError('Invalid reconstructed initial physical mesh')
    value,gradient=problem.energy.value_gradient(q)
    gradient[problem.boundary]=0
    evaluations,backtracks,illegal=1,0,0
    history=[]
    stop='iteration_limit'
    accepted_alpha=0.0
    for k in range(settings['max_iterations']+1):
        norm=float(np.linalg.norm(gradient))
        history.append(dict(iteration=k,energy=value,gradient_norm=norm,
            energy_evaluations=evaluations,backtracks=backtracks,alpha=accepted_alpha,
            min_computational_area=float(signed_triangle_areas(q,problem.cells).min()),
            min_physical_area=float(signed_triangle_areas(x,problem.cells).min())))
        if norm<=settings['gradient_tolerance']:
            stop='converged';break
        if k==settings['max_iterations']:
            break
        alpha=float(settings['alpha0'])
        accepted=False
        for _ in range(settings['max_backtracks']):
            if evaluations>=settings['max_energy_evaluations']:
                stop='energy_budget';break
            candidate=q-alpha*gradient
            if np.all(signed_triangle_areas(candidate,problem.cells)>problem.epsilon):
                cv,cg=problem.energy.value_gradient(candidate)
                evaluations+=1
                if not (np.isfinite(cv) and np.all(np.isfinite(cg))):
                    raise FloatingPointError('Nonfinite candidate energy or gradient')
                if cv<=value-settings['armijo_c1']*alpha*norm**2:
                    cx=problem.physical(candidate)
                    if problem.valid(cx)['valid']:
                        accepted=True;break
                    illegal+=1
            else:
                illegal+=1
            backtracks+=1
            alpha*=settings['beta']
        if not accepted:
            if stop!='energy_budget':stop='line_search_stalled'
            break
        assert cv<=value-settings['armijo_c1']*alpha*norm**2
        assert np.array_equal(candidate[problem.boundary],problem.reference[problem.boundary])
        q,x,value,gradient=candidate,cx,cv,cg
        gradient[problem.boundary]=0
        accepted_alpha=alpha
    summary=dict(converged=stop=='converged',stop_reason=stop,iterations=history[-1]['iteration'],
        energy_evaluations=evaluations,backtracks=backtracks,illegal_candidates=illegal,
        initial_energy=history[0]['energy'],final_energy=value,
        final_gradient_norm=float(np.linalg.norm(gradient)),
        gradient_tolerance=float(settings['gradient_tolerance']),
        seconds=perf_counter()-started,min_area=problem.valid(x)['min_area'])
    return dict(Q=q,X=x,summary=summary,history=history)

def solve_reference(mu,config):
    start=perf_counter()
    problem=Problem(mu,config)
    result=solve_state(problem)
    result['summary']['seconds']=perf_counter()-start
    return problem,result
