"""Shared instances, projected gradient descent and guarded step proposals."""
from time import perf_counter
import numpy as np
from src.geometry import signed_triangle_areas
from src.variational_mesh import WinslowEnergy, reconstruct_physical

FEATURES = ['log1p_gradient_norm', 'log_previous_alpha', 'log_scaled_min_area', 'previous_backtracks']
METHODS = ['fixed', 'armijo', 'warm', 'rf']
DEFAULT = dict(alpha0=1.0, fixed_alpha=0.05, beta=0.5, c1=1e-4,
               alpha_min=1e-12, max_backtracks=40, max_iterations=1800,
               max_energy_evals=30000, relative_gradient_tolerance=1e-4,
               absolute_gradient_tolerance=1e-7, area_floor=1e-12)

def instance(case, seed, n=12):
    rng = np.random.default_rng(seed)
    x, y = np.meshgrid(np.linspace(0, 1, n+1), np.linspace(0, 1, n+1))
    reference = np.column_stack((x.ravel(), y.ravel()))
    cells = []
    for j in range(n):
        for i in range(n):
            a = j*(n+1)+i
            cells.extend([[a, a+1, a+n+2], [a, a+n+2, a+n+1]])
    cells = np.array(cells, dtype=np.int64)
    boundary = np.any((reference == 0) | (reference == 1), axis=1)
    physical = reference.copy()
    physical[~boundary] += rng.uniform(-0.12/n, 0.12/n, (sum(~boundary), 2))
    centers = physical[cells].mean(axis=1)
    strength = float(rng.uniform(3, 7))
    center = rng.uniform(0.43, 0.57, 2)
    radius2 = ((centers-center)**2).sum(axis=1)
    w = strength*np.exp(-radius2/(2*0.17**2))
    eye = np.broadcast_to(np.eye(2), (len(cells), 2, 2)).copy()
    if case == 'uniform':
        metric = eye
    elif case == 'gaussian':
        metric = (1+w[:, None, None])*eye
    elif case == 'anisotropic':
        angle = np.pi/6
        v = np.array([np.cos(angle), np.sin(angle)])
        metric = eye + w[:, None, None]*np.outer(v, v)
    else:
        raise ValueError(case)
    assert np.min(signed_triangle_areas(physical, cells)) > 0
    assert np.min(np.linalg.eigvalsh(metric)) > 0
    config = dict(case=case, seed=seed, n=n, strength=strength, center=center.tolist(), sigma=0.17,
                  perturbation_fraction=0.12)
    return reference, physical, cells, boundary, metric, config

def solve(case, seed, n=12, method='armijo', model=None, options=None):
    reference, physical, cells, boundary, metric, config = instance(case, seed, n)
    opt = DEFAULT | (options or {})
    started = perf_counter()
    energy = WinslowEnergy(physical, cells, metric)
    q = reference.copy()
    moved = reconstruct_physical(q, physical, cells, reference)
    value, gradient = energy.value_gradient(q)
    gradient[boundary] = 0
    initial = value
    initial_norm = float(np.linalg.norm(gradient))
    tolerance = max(opt['absolute_gradient_tolerance'], opt['relative_gradient_tolerance']*initial_norm)
    previous_alpha, previous_backtracks = opt['alpha0'], 0
    evals, backtracks, illegal, fallbacks = 1, 0, 0, 0
    proposal_seconds = search_seconds = 0.0
    rows, training = [], []
    stop = 'iteration_limit'
    for k in range(opt['max_iterations']+1):
        norm = float(np.linalg.norm(gradient))
        min_area = float(signed_triangle_areas(q, cells).min())
        rows.append(dict(iteration=k, energy=value, gradient_norm=norm,
                         energy_evals=evals, backtracks=backtracks,
                         min_area=min_area, alpha=previous_alpha,
                         physical_min_area=float(signed_triangle_areas(moved, cells).min()),
                         elapsed_seconds=perf_counter()-started))
        if norm <= tolerance:
            stop = 'converged'
            break
        if k == opt['max_iterations']:
            break
        if evals >= opt['max_energy_evals']:
            stop = 'energy_budget'
            break
        proposal_start = perf_counter()
        features = [np.log1p(norm), np.log(previous_alpha),
                    np.log(min_area*2*n*n), float(previous_backtracks)]
        if method == 'rf':
            alpha = float(np.clip(np.exp(model.predict(np.array([features]))[0]),
                                  opt['alpha_min'], opt['alpha0']))
        elif method == 'warm':
            alpha = previous_alpha
        elif method == 'fixed':
            alpha = opt['fixed_alpha']
        else:
            alpha = opt['alpha0']
        proposal_seconds += perf_counter()-proposal_start
        search_start = perf_counter()
        accepted = False
        local_backtracks = 0
        # RF may fall back to the same default proposal if its search stalls.
        for attempt in range(2 if method == 'rf' else 1):
            for trial in range(1 if method == 'fixed' else opt['max_backtracks']):
                if evals >= opt['max_energy_evals']:
                    break
                candidate = q-alpha*gradient
                legal = np.all(signed_triangle_areas(candidate, cells) > opt['area_floor'])
                if legal:
                    candidate_value, candidate_gradient = energy.value_gradient(candidate)
                    evals += 1
                    assert np.isfinite(candidate_value) and np.all(np.isfinite(candidate_gradient))
                    if candidate_value <= value-opt['c1']*alpha*norm**2:
                        candidate_physical = reconstruct_physical(candidate, physical, cells, reference)
                        legal = np.all(signed_triangle_areas(candidate_physical, cells) > opt['area_floor'])
                        if legal:
                            accepted = True
                            break
                if not legal:
                    illegal += 1
                local_backtracks += 1
                backtracks += 1
                alpha *= opt['beta']
                if alpha < opt['alpha_min']:
                    break
            if accepted:
                break
            if method == 'rf' and attempt == 0:
                alpha = opt['alpha0']
                fallbacks += 1
        search_seconds += perf_counter()-search_start
        if not accepted:
            stop = 'fixed_step_rejected' if method == 'fixed' else 'line_search_stalled'
            break
        assert candidate_value <= value-opt['c1']*alpha*norm**2
        assert np.array_equal(candidate[boundary], reference[boundary])
        assert np.allclose(candidate_physical[boundary], physical[boundary], atol=1e-13)
        training.append(dict(zip(FEATURES, map(float, features))) |
                        dict(iteration=k, log_alpha=float(np.log(alpha)), accepted_alpha=alpha,
                             step_backtracks=local_backtracks))
        q, moved, value, gradient = candidate, candidate_physical, candidate_value, candidate_gradient
        gradient[boundary] = 0
        previous_alpha, previous_backtracks = alpha, local_backtracks
    elapsed = perf_counter()-started
    summary = dict(instance_id=f'{case}_{seed}_n{n}', case=case, seed=seed, n=n, method=method,
                   initial_energy=initial, final_energy=value,
                   relative_energy_reduction=(initial-value)/initial,
                   initial_gradient_norm=initial_norm, final_gradient_norm=float(np.linalg.norm(gradient)),
                   gradient_tolerance=tolerance, iterations=rows[-1]['iteration'],
                   energy_evals=evals, backtracks=backtracks, illegal_candidates=illegal,
                   fallbacks=fallbacks, elapsed_seconds=elapsed,
                   proposal_seconds=proposal_seconds, search_seconds=search_seconds,
                   min_area=float(signed_triangle_areas(q, cells).min()),
                   physical_min_area=float(signed_triangle_areas(moved, cells).min()),
                   flipped_cells=int(np.count_nonzero(signed_triangle_areas(moved, cells) <= 0)),
                   converged=(stop == 'converged'), stop_reason=stop)
    return summary, rows, training, dict(reference=reference, initial=physical, computational=q,
                                        final=moved, cells=cells, metric=metric), config
