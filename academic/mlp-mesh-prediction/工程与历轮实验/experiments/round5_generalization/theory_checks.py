"""Numerical illustrations of the explicitly stated mathematical results."""
import numpy as np
from study import *

def main():
    p=Problem([.5,.5,5.,.24],CFG)
    inside=np.flatnonzero(~p.boundary);base=p.reference.copy()
    value,g0=p.energy.value_gradient(base)
    columns=[]
    for node in inside:
        for axis in range(2):
            q=base.copy();q[node,axis]+=1
            _,g=p.energy.value_gradient(q)
            columns.append((g-g0)[inside].ravel())
    h=np.column_stack(columns);eig=np.linalg.eigvalsh(h)
    assert eig[0]>0 and np.max(abs(h-h.T))<1e-10
    write_json(ROOT/'results/theory_checks.json',dict(
        frozen_Q_hessian_dofs=len(h),symmetry_residual=float(np.max(abs(h-h.T))),
        minimum_eigenvalue=float(eig[0]),maximum_eigenvalue=float(eig[-1]),
        condition_number=float(eig[-1]/eig[0]),
        smaller_error_counterexample=dict(hessian=[1.,100.],alpha=.01,
            A_initial=[0.,1.],A_after_one_step=[0.,0.],
            B_initial=[.1,0.],B_after_one_step=[.099,0.]),
        theorem_scope='A proof is in 文档/数学结论与证明.md; this computation illustrates one instance only.'))
    print('Frozen Q Hessian SPD:',eig[0],eig[-1])

if __name__=='__main__':main()
