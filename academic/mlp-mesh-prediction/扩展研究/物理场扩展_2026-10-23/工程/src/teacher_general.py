"""Independent, tested starting point for scalable 2D scalar-monitor Q teachers.

No original experiment files are modified. All optimization is of frozen-X0
quadratic Winslow Q energy, NOT the separate round4 nonlinear X energy.
If the unconstrained stationary solution is nonvalid, raise, log and treat
explicitly; never silently use an invalid mesh as a teacher.
"""
from __future__ import annotations
from functools import lru_cache
from time import perf_counter
import numpy as np
import scipy.sparse as sparse
from scipy.sparse.linalg import spsolve
from matplotlib.tri import Triangulation, LinearTriInterpolator


def signed_areas(nodes: np.ndarray, cells: np.ndarray) -> np.ndarray:
    t = nodes[cells]
    a, b = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
    return 0.5 * (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])


@lru_cache(maxsize=12)
def topology(n: int):
    if not 4 <= int(n) <= 128:
        raise ValueError('n must be an integer between 4 and 128')
    xx, yy = np.meshgrid(np.linspace(0, 1, n + 1), np.linspace(0, 1, n + 1))
    x0 = np.column_stack((xx.ravel(), yy.ravel()))
    cells = []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            cells.extend(((a, a + 1, a + n + 2), (a, a + n + 2, a + n + 1)))
    cells = np.asarray(cells, dtype=np.int64)
    boundary = np.any((x0 == 0) | (x0 == 1), axis=1)
    interior = np.flatnonzero(~boundary)
    bnodes = np.flatnonzero(boundary)
    edges = np.stack((x0[cells[:, 1]] - x0[cells[:, 0]],
                      x0[cells[:, 2]] - x0[cells[:, 0]]), axis=-1)
    areas = signed_areas(x0, cells)
    inv = np.linalg.inv(edges)
    d = np.array([[-1., 1., 0.], [-1., 0., 1.]])
    gram = np.einsum('kij,klj->kil', inv, inv)  # inv @ inv.T
    local = 2 * areas[:, None, None] * np.einsum('ab,kbc,cd->kad', d.T, gram, d)
    row = np.broadcast_to(cells[:, :, None], (len(cells), 3, 3)).ravel().copy()
    col = np.broadcast_to(cells[:, None, :], (len(cells), 3, 3)).ravel().copy()
    return x0, cells, boundary, interior, bnodes, areas, local, row, col


def metric(points: np.ndarray, spec: dict) -> np.ndarray:
    """spec = {'kind': 'single'|'double'|'wave', ...}; m >= 1.

    single: mu=[cx,cy,A,sigma]; double: peaks=[[cx,cy,A,sigma],...];
    wave: phase, strength, width. Note this is a user-defined wave monitor,
    not the Hessian metric in the cited 2015 paper.
    """
    kind = spec['kind']
    if kind in ('single', 'double'):
        params = [spec['mu']] if kind == 'single' else spec['peaks']
        result = np.ones(points.shape[:-1], dtype=np.float64)
        for p in params:
            cx, cy, strength, width = map(float, p)
            if not strength >= 0 or not width > 0:
                raise ValueError('metric strengths must be nonnegative and widths positive')
            result += strength * np.exp(-((points[..., 0] - cx) ** 2 +
                                         (points[..., 1] - cy) ** 2) / width ** 2)
        return result
    if kind == 'wave':
        phase = float(spec.get('phase', 0.0))
        strength = float(spec.get('strength', 8.0))
        width = float(spec.get('width', 0.1))
        if not strength >= 0 or not width > 0:
            raise ValueError('invalid wave strength or width')
        distance = points[..., 1] - 0.5 - .25 * np.sin(2 * np.pi * points[..., 0] + phase)
        return 1 + strength * np.exp(-(distance / width) ** 2)
    raise ValueError(f'unsupported kind: {kind}')


def make_teacher(n: int, spec: dict, *, min_area: float = 1e-10) -> dict:
    t0 = perf_counter()
    x0, cells, boundary, interior, bnodes, areas, local, row, col = topology(n)
    centers = x0[cells].mean(axis=1)
    m = metric(centers, spec)
    if np.any(~np.isfinite(m)) or np.any(m <= 0):
        raise ValueError('invalid metric')
    matrix = sparse.coo_matrix(((local / m[:, None, None]).ravel(), (row, col)),
                               shape=(len(x0), len(x0))).tocsr()
    kii = matrix[interior, :][:, interior]
    kib = matrix[interior, :][:, bnodes]
    q = x0.copy()
    for axis in range(2):
        q[interior, axis] = spsolve(kii, -kib @ x0[bnodes, axis])
    residual = float(np.max(np.abs((matrix @ q)[interior])))
    qmin = float(signed_areas(q, cells).min())
    if not qmin > min_area:
        raise ValueError(f'Q invalid, minimum signed area {qmin}')
    tri = Triangulation(q[:, 0], q[:, 1], cells)
    coords = []
    for axis in range(2):
        vals = LinearTriInterpolator(tri, x0[:, axis])(x0[:, 0], x0[:, 1])
        if np.any(np.ma.getmaskarray(vals)):
            raise ValueError('inverse-map interpolation masked outside Q grid')
        coords.append(np.asarray(vals, dtype=np.float64))
    x = np.column_stack(coords)
    x[boundary] = x0[boundary]
    xmin = float(signed_areas(x, cells).min())
    if not xmin > min_area:
        raise ValueError(f'X invalid, minimum signed area {xmin}')
    energy = float(.5 * (q * (matrix @ q)).sum())  # because K is Hessian of I
    return dict(X0=x0, Q=q, X=x, cells=cells, boundary=boundary,
                monitor_cells=m, energy=energy, residual=residual,
                q_min_area=qmin, x_min_area=xmin, seconds=perf_counter()-t0,
                spec=spec, n=n)
