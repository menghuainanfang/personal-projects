"""Verify Poisson assembly and manufactured forcing against exact solutions."""
from pathlib import Path
import importlib.util
import json
import numpy as np

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('physical_fields',OUT/'run.py')
experiment=importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


def main():
    original=experiment.exact
    def affine(points,spec,forcing=False):
        return np.zeros(len(points)) if forcing else points[:,0]+2*points[:,1]
    experiment.exact=affine
    problem=experiment.Problem(12,{})
    solution,residual=experiment.poisson(problem.reference,problem.cells,problem.boundary,{})
    patch_error=float(np.max(abs(solution-affine(problem.reference,{}))))
    if patch_error>1e-11:
        raise RuntimeError('Affine patch test failed')
    def sine(points,spec,forcing=False):
        u=np.sin(2*np.pi*points[:,0])*np.sin(3*np.pi*points[:,1])
        return 13*np.pi**2*u if forcing else u
    experiment.exact=sine
    errors=[]
    for n in [8,16,32]:
        problem=experiment.Problem(n,{})
        solution,_=experiment.poisson(problem.reference,problem.cells,problem.boundary,{})
        errors.append(experiment.l2_error(problem.reference,problem.cells,solution,{}))
    rates=np.log2(np.array(errors[:-1])/np.array(errors[1:]))
    if np.min(rates)<1.8:
        raise RuntimeError('Smooth Poisson solution does not show P1 L2 convergence')
    experiment.exact=original
    points=np.random.default_rng(20261023).uniform(0,1,size=(100,2))
    cx,cy,strength,width=.4,.5,6.,.16
    field_spec=dict(kind='single',peaks=[[cx,cy,strength,width]])
    radius2=np.sum((points-[cx,cy])**2,axis=1)
    analytic=(4/width**2-4*radius2/width**4)*np.exp(-radius2/width**2)
    forcing_error=float(np.max(abs(original(points,field_spec,True)-analytic)))
    if forcing_error>1e-10:
        raise RuntimeError('Autodifferentiated Gaussian forcing disagrees with exact formula')
    result=dict(affine_max_error=patch_error,affine_residual=residual,
        sine_n=[8,16,32],sine_l2=errors,sine_rates=rates.tolist(),
        gaussian_forcing_max_error=forcing_error)
    (OUT/'pde_verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
