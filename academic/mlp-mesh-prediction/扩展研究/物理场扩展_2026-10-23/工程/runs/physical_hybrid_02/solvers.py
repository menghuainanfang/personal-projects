"""Physical-coordinate L-BFGS descent and P1 weak Winslow assembly."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from time import perf_counter


def weak_winslow(nodes, cells, boundary, monitor_cells):
    """Solve ∫(1/m)∇q·∇v=0 with q=x on the boundary.

    Piecewise constant m uses the same centroid values as the direct energy.
    The factor two matches the derivative of ∫|∇q|²/m.
    """
    triangles = nodes[cells]
    edges = np.stack((triangles[:, 1]-triangles[:, 0],
                      triangles[:, 2]-triangles[:, 0]), axis=-1)
    gradients = np.array([[-1., -1.], [1., 0.], [0., 1.]]) @ np.linalg.inv(edges)
    area = np.linalg.det(edges)/2
    local = (2*area/monitor_cells)[:, None, None] * (gradients @ gradients.transpose(0, 2, 1))
    rows = np.broadcast_to(cells[:, :, None], local.shape).ravel()
    cols = np.broadcast_to(cells[:, None, :], local.shape).ravel()
    matrix = coo_matrix((local.ravel(), (rows, cols)), shape=(len(nodes), len(nodes))).tocsr()
    interior = np.flatnonzero(~boundary)
    fixed = np.flatnonzero(boundary)
    q = nodes.copy()
    q[interior] = spsolve(matrix[interior][:, interior], -matrix[interior][:, fixed] @ q[fixed])
    return q, float(np.max(np.abs((matrix @ q)[interior])))


def physical_lbfgs(problem, initial, energy_class, tolerance=1e-5,
                   max_iterations=3000, max_evaluations=30000, memory=10):
    """L-BFGS direction with feasible Armijo steps and fixed boundary nodes."""
    started = perf_counter()
    if not problem.valid(initial)['valid']:
        raise ValueError('Initial physical mesh is invalid')
    energy = energy_class(problem)
    x = initial.copy()
    value, g = energy.value_gradient(x)
    evaluations = 1
    pairs = []
    history = []
    stop = 'iteration_limit'
    backtracks = illegal = 0
    for iteration in range(max_iterations+1):
        norm = float(np.linalg.norm(g))
        history.append(dict(iteration=iteration, energy=value, gradient_norm=norm,
                            min_area=problem.valid(x)['min_area']))
        if norm <= tolerance:
            stop = 'converged'
            break
        if iteration == max_iterations:
            break
        z = g.ravel().copy()
        coefficients = []
        for s, y, rho in reversed(pairs):
            a = rho*np.dot(s, z)
            coefficients.append(a)
            z -= a*y
        if pairs:
            s, y, _ = pairs[-1]
            z *= np.dot(s, y)/np.dot(y, y)
        for (s, y, rho), a in zip(pairs, reversed(coefficients)):
            z += s*(a-rho*np.dot(y, z))
        direction = -z.reshape(x.shape)
        direction[problem.boundary] = 0.
        slope = float(np.sum(g*direction))
        if slope >= 0:
            pairs.clear()
            direction = -g
            slope = -norm**2
        alpha = 1.
        accepted = False
        for _ in range(40):
            if evaluations+2 > max_evaluations:
                stop = 'energy_budget'
                break
            candidate = x+alpha*direction
            if problem.valid(candidate)['valid']:
                candidate_value = energy.value(candidate)
                evaluations += 1
                if np.isfinite(candidate_value) and candidate_value <= value+1e-4*alpha*slope:
                    candidate_value, candidate_gradient = energy.value_gradient(candidate)
                    evaluations += 1
                    accepted = True
                    break
            else:
                illegal += 1
            alpha *= .5
            backtracks += 1
        if not accepted:
            if stop != 'energy_budget':
                stop = 'line_search_stalled'
            break
        s = (candidate-x).ravel()
        y = (candidate_gradient-g).ravel()
        curvature = float(np.dot(s, y))
        if curvature > 1e-10*np.linalg.norm(s)*np.linalg.norm(y):
            pairs.append((s, y, 1/curvature))
            pairs = pairs[-memory:]
        x, value, g = candidate, candidate_value, candidate_gradient
    return dict(X=x, history=history, summary=dict(converged=stop=='converged',
        stop_reason=stop, iterations=history[-1]['iteration'], final_energy=value,
        initial_energy=history[0]['energy'], final_gradient_norm=float(np.linalg.norm(g)),
        seconds=perf_counter()-started, energy_evaluations=evaluations,
        backtracks=backtracks, illegal_candidates=illegal))
