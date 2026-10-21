"""Damp physical displacement, then align it with the inherited solver state."""
from time import perf_counter
import numpy as np

def safe_prediction(problem,displacement):
    started=perf_counter()
    raw=problem.X0.copy()
    raw[~problem.boundary]+=np.asarray(displacement).reshape(-1,2)
    raw_status=problem.valid(raw)
    transfer_failures=0
    for backtracks in range(problem.config['prediction']['max_displacement_backtracks']+1):
        tau=2.0**(-backtracks)
        physical=problem.X0.copy()
        physical[~problem.boundary]+=tau*np.asarray(displacement).reshape(-1,2)
        if not problem.valid(physical)['valid']:
            continue
        q=problem.physical_to_state(physical)
        if not problem.valid(q)['valid']:
            transfer_failures+=1;continue
        aligned=problem.physical(q)
        if not problem.valid(aligned)['valid']:
            transfer_failures+=1;continue
        norm=max(float(np.linalg.norm((physical-problem.X0)[~problem.boundary])),1e-14)
        return dict(raw=raw,damped=physical,X=aligned,Q=q,
            metadata=dict(raw_valid=raw_status['valid'],raw_min_area=raw_status['min_area'],
                tau=tau,backtracks=backtracks,fallback=False,transfer_failures=transfer_failures,
                transfer_relative_change=float(np.linalg.norm((aligned-physical)[~problem.boundary])/norm),
                safe_valid=True,seconds=perf_counter()-started))
    return dict(raw=raw,damped=problem.X0.copy(),X=problem.X0.copy(),Q=problem.reference.copy(),
        metadata=dict(raw_valid=raw_status['valid'],raw_min_area=raw_status['min_area'],
            tau=0.0,backtracks=problem.config['prediction']['max_displacement_backtracks']+1,
            fallback=True,transfer_failures=transfer_failures,transfer_relative_change=0.0,
            safe_valid=True,seconds=perf_counter()-started))
