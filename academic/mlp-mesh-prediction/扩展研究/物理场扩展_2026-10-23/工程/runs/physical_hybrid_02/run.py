"""Compare learned physical initializations with two matched physical solvers."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS']:
    os.environ[key] = '1'
import sys
import json
import time
import numpy as np
import torch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
OLD = ROOT/'runs/physical_X_01'
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(OLD))
# The existing experiment also has a run.py; load it under a distinct name.
import importlib.util
spec = importlib.util.spec_from_file_location('physical_experiment', OLD/'run.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
from physical_energy import PhysicalEnergy, solve
from teacher_general import make_teacher
from train_fixed_q import FixedMLP
from scale_study import csvout, interpolation
from solvers import weak_winslow, physical_lbfgs


def main():
    torch.set_num_threads(1)
    records = json.loads((OLD/'physical_subset.json').read_text(encoding='utf8'))
    checkpoint = ROOT/'runs/physical_teacher_01/models/physical_X_seed20261023/best_model.pt'
    package = torch.load(checkpoint, map_location='cpu', weights_only=True)
    model = FixedMLP(package['output_dim'], package['width'])
    model.load_state_dict(package['state_dict'])
    model.eval()
    # Detect a missing spatial-metric derivative before comparing physical solves.
    problem = old.Problem(np.array(records[0]['spec']['mu']))
    energy = PhysicalEnergy(problem)
    direction = np.random.default_rng(2015).normal(size=old.X0.shape)
    direction[old.BOUNDARY] = 0
    direction /= np.linalg.norm(direction)
    _, gradient = energy.value_gradient(old.X0)
    h = 1e-6
    finite_difference = (energy.value(old.X0+h*direction)-energy.value(old.X0-h*direction))/(2*h)
    analytical = float(np.sum(gradient*direction))
    error = abs(finite_difference-analytical)/max(1., abs(finite_difference), abs(analytical))
    if error > 1e-6:
        raise RuntimeError('Physical energy derivative does not match directional difference')
    checks = dict(physical_gradient_error=error, weak_teachers=[])
    rows = []
    for index, record in enumerate(records):
        mu = np.array(record['spec']['mu'])
        problem = old.Problem(mu)
        teacher = make_teacher(12, record['spec'])
        weak_q, residual = weak_winslow(old.X0, old.CELLS, old.BOUNDARY, teacher['monitor_cells'])
        difference = float(np.max(np.abs(weak_q-teacher['Q'])))
        checks['weak_teachers'].append(dict(id=record['id'], max_coordinate_difference=difference,
                                            residual=residual))
        # Same weak form and quadrature must produce the same frozen-Q teacher.
        if difference > 1e-10 or residual > 1e-9:
            raise RuntimeError('Weak Winslow assembly disagrees with the direct-energy teacher')
        methods = [('regular_spectral', False, False), ('physical_MLP_spectral', True, False),
                   ('regular_lbfgs', False, True), ('physical_MLP_lbfgs', True, True)]
        for repeat in range(2):
            ordered = methods if (index+repeat)%2 == 0 else list(reversed(methods))
            for name, learned, lbfgs in ordered:
                started = time.perf_counter()
                if learned:
                    raw, initial, raw_valid, tau, fallback = old.direct_x(model, package, mu)
                else:
                    initial = old.X0.copy()
                    raw_valid, tau, fallback = True, 1., False
                result = (physical_lbfgs(problem, initial, PhysicalEnergy) if lbfgs
                          else solve(problem, initial))
                elapsed = time.perf_counter()-started
                if not problem.valid(result['X'])['valid']:
                    raise RuntimeError('Physical solver returned invalid geometry')
                energies = np.array([r['energy'] for r in result['history']])
                if np.any(np.diff(energies) > 1e-12*np.maximum(1., abs(energies[:-1]))):
                    raise RuntimeError('Accepted physical steps increased the objective')
                rows.append(dict(id=record['id'], group=record['group'], repeat=repeat,
                    method=name, online_seconds=elapsed, raw_valid=raw_valid, tau=tau,
                    fallback=fallback, **result['summary'],
                    interpolation_rmse=interpolation(result['X'], old.CELLS, mu)))
                if repeat == 0:
                    np.savez_compressed(OUT/f"{record['id']}_{name}.npz",
                                        initial_X=initial, X=result['X'], mu=mu,
                                        cells=old.CELLS, X0=old.X0)
                    csvout(OUT/f"{record['id']}_{name}_history.csv", result['history'])
            csvout(OUT/'results.csv', rows)
        print('COMPLETED', index+1, record['group'], flush=True)
    (OUT/'checks.json').write_text(json.dumps(checks, indent=2), encoding='utf8')
    summaries = []
    for name, _, _ in methods:
        subset = [r for r in rows if r['method']==name]
        summaries.append(dict(method=name, runs=len(subset),
            converged=sum(r['converged'] for r in subset),
            seconds=float(np.mean([r['online_seconds'] for r in subset])),
            iterations=float(np.mean([r['iterations'] for r in subset])),
            interpolation_rmse=float(np.mean([r['interpolation_rmse'] for r in subset]))))
    csvout(OUT/'summary.csv', summaries)
    pairs = []
    for baseline, learned in [('regular_spectral','physical_MLP_spectral'),
                              ('regular_lbfgs','physical_MLP_lbfgs'),
                              ('regular_lbfgs','physical_MLP_spectral')]:
        ratios = []
        for r in rows:
            if r['method'] != baseline:
                continue
            candidate = next(s for s in rows if s['id']==r['id'] and s['repeat']==r['repeat']
                             and s['method']==learned)
            relative = abs(r['final_energy']-candidate['final_energy'])/max(1.,abs(r['final_energy']))
            if r['converged'] and candidate['converged'] and relative <= 1e-6:
                ratios.append(r['online_seconds']/candidate['online_seconds'])
        pairs.append(dict(baseline=baseline, learned=learned, matched=len(ratios), total=40,
            geometric_speedup=float(np.exp(np.mean(np.log(ratios)))) if ratios else None))
    config = dict(checkpoint=str(checkpoint), training='reuse completed physical teacher supervised model',
                  cases=20, repeats=2, seed=20261023, tolerance=1e-5,
                  max_iterations=3000, max_energy_evaluations=30000,
                  pairing_relative_energy_tolerance=1e-6, paired_results=pairs,
                  weak_max_difference=max(r['max_coordinate_difference'] for r in checks['weak_teachers']))
    (OUT/'completion.json').write_text(json.dumps(config, indent=2), encoding='utf8')
    print(json.dumps(dict(summary=summaries, paired=pairs), indent=2), flush=True)


if __name__ == '__main__':
    main()
