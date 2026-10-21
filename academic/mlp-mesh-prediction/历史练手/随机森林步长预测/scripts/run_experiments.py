"""Generate independent trajectories, fit one forest and evaluate four strategies."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import csv
import json
import platform
from time import perf_counter
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from src.experiment import solve, instance, FEATURES, METHODS, DEFAULT
from src.variational_mesh import WinslowEnergy, reconstruct_physical
from src.geometry import signed_triangle_areas

CASES = ['uniform', 'gaussian', 'anisotropic']
def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def verify_gradient():
    checks = []
    for case in CASES:
        for seed in [2026, 2027]:
            ref, phys, cells, boundary, metric, _ = instance(case, seed, 8)
            energy = WinslowEnergy(phys, cells, metric)
            rng = np.random.default_rng(seed)
            q = ref.copy()
            q[~boundary] += rng.uniform(-0.005, 0.005, (sum(~boundary), 2))
            d = rng.normal(size=q.shape); d[boundary] = 0; d /= np.linalg.norm(d)
            assert signed_triangle_areas(q, cells).min() > 0
            v, g = energy.value_gradient(q)
            h = 1e-5
            fd = (energy.value_gradient(q+h*d)[0]-energy.value_gradient(q-h*d)[0])/(2*h)
            exact = float(np.sum(g*d))
            err = abs(fd-exact)/max(1e-8, abs(exact))
            assert err < 1e-6
            gp = g.copy(); gp[boundary] = 0
            assert energy.value_gradient(q-1e-3*gp)[0] < v
            assert np.allclose(reconstruct_physical(ref, phys, cells, ref), phys, atol=1e-13)
            checks.append(dict(case=case, seed=seed, finite_difference=fd, analytic=exact, relative_error=err))
    write_json(ROOT/'data/gradient_checks.json', checks)

def main():
    verify_gradient()
    for name in ['data/trajectories','data/meshes']:
        (ROOT/name).mkdir(exist_ok=True)
    splits = dict(train=[], validation=[], test=[])
    configurations, samples, teacher_summaries = [], [], []
    generation_start = perf_counter()
    for subset, seeds in [('train',range(8)), ('validation',range(80,82))]:
        for case in CASES:
            for seed in seeds:
                n = [8,10,12][seed % 3]
                s, hist, labels, _, conf = solve(case, seed, n)
                splits[subset].append(s['instance_id'])
                configurations.append(dict(subset=subset, **conf))
                teacher_summaries.append(dict(subset=subset, **s))
                samples.extend(dict(subset=subset, instance_id=s['instance_id'], case=case,
                                    seed=seed, n=n, **r) for r in labels)
                write_csv(ROOT/f'data/trajectories/{s["instance_id"]}_teacher.csv', hist)
                print(f'{subset}: {case} seed={seed}, {s["iterations"]} steps, {s["stop_reason"]}', flush=True)
    generation_seconds = perf_counter()-generation_start
    write_csv(ROOT/'data/dataset.csv', samples)
    write_csv(ROOT/'data/teacher_summary.csv', teacher_summaries)
    model = RandomForestRegressor(n_estimators=32, max_depth=10, min_samples_leaf=5,
                                  random_state=20261020, n_jobs=1)
    train = [r for r in samples if r['subset']=='train']
    valid = [r for r in samples if r['subset']=='validation']
    started = perf_counter()
    model.fit([[r[f] for f in FEATURES] for r in train], [r['log_alpha'] for r in train])
    training_seconds = perf_counter()-started
    joblib.dump(model, ROOT/'models/random_forest.joblib', compress=3)
    prediction = model.predict([[r[f] for f in FEATURES] for r in valid])
    truth = np.array([r['log_alpha'] for r in valid])
    write_csv(ROOT/'data/validation_predictions.csv', [dict(instance_id=r['instance_id'],
              iteration=r['iteration'], true_log_alpha=float(t), predicted_log_alpha=float(p))
              for r,t,p in zip(valid, truth, prediction)])
    model_info = dict(features=FEATURES, parameters=model.get_params(), train_samples=len(train),
        validation_samples=len(valid), validation_log_mae=mean_absolute_error(truth,prediction),
        validation_log_r2=r2_score(truth,prediction),
        validation_previous_log_alpha_mae=mean_absolute_error(truth,[r['log_previous_alpha'] for r in valid]),
        train_label_log_std=float(np.std([r['log_alpha'] for r in train])),
        importance=dict(zip(FEATURES, model.feature_importances_.tolist())),
        data_generation_seconds=generation_seconds, training_seconds=training_seconds)
    results=[]
    for case in CASES:
        for seed in range(100,103):
            n=12
            iid=f'{case}_{seed}_n{n}'
            splits['test'].append(iid)
            configurations.append(dict(subset='test', **instance(case,seed,n)[-1]))
            # Rotate order to distribute warm-cache and machine-load effects.
            order=METHODS[seed%4:]+METHODS[:seed%4]
            for method in order:
                s,hist,_,meshes,_=solve(case, seed, n, method, model)
                results.append(s)
                write_csv(ROOT/f'data/trajectories/{iid}_{method}.csv', hist)
                np.savez_compressed(ROOT/f'data/meshes/{iid}_{method}.npz', **meshes)
                print(f'test: {case} seed={seed} {method}, {s["iterations"]} steps, {s["elapsed_seconds"]:.3f}s, {s["stop_reason"]}',flush=True)
    assert not (set(splits['train']) & set(splits['validation']) or
                set(splits['train']) & set(splits['test']) or set(splits['validation']) & set(splits['test']))
    write_csv(ROOT/'data/results.csv', results)
    write_json(ROOT/'data/split.json', splits)
    write_json(ROOT/'data/configurations.json', configurations)
    write_json(ROOT/'data/model_metrics.json', model_info)
    write_json(ROOT/'data/protocol.json',dict(options=DEFAULT,methods=METHODS,
        python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__,
        platform=platform.platform(),processor=platform.processor(),
        seed=20261020, runtime_scope='solve includes energy setup, inference, features, history, reconstruction and acceptance; excludes instance creation, file IO, training'))
    print(json.dumps(model_info, ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
