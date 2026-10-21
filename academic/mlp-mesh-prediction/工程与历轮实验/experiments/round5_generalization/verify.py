"""Verify saved states and matched-objective timing comparisons."""
import csv,json
import numpy as np
from study import *

def read(name):
    return list(csv.DictReader((ROOT/'results'/name).open(encoding='utf-8-sig')))

def main():
    cases=json.loads((ROOT/'results/cases.json').read_text(encoding='utf-8'))
    metrics=read('metrics.csv');timings=read('timings.csv')
    assert len(metrics)==180 and len(timings)==540
    comparisons=[];references=[];max_energy_rise=0.
    points=np.load(ROOT/'results/sampling.npz')['points']
    for case in cases:
        cfg=copy.deepcopy(CFG);cfg['mesh']['n']=case['n'];p=Problem(case['mu'],cfg)
        energy=MonitorEnergy(p,case)
        reference=np.load(ROOT/f'results/meshes/{case["iid"]}_reference.npz')
        reference_status=json.loads((ROOT/f'results/meshes/{case["iid"]}_reference.json').read_text(encoding='utf-8'))
        references.append(dict(iid=case['iid'],group=case['group'],n=case['n'],
            converged=reference_status['converged'],
            interpolation_rmse=interpolate_error(reference['X'],p.cells,case,points),
            regular_rmse=interpolate_error(p.X0,p.cells,case,points),
            min_angle=geometry(reference['X'],p.cells)['min_angle']))
        regular=next(r for r in metrics if r['iid']==case['iid'] and r['method']=='regular')
        for method in METHODS:
            row=next(r for r in metrics if r['iid']==case['iid'] and r['method']==method)
            d=np.load(ROOT/f'results/meshes/{case["iid"]}_{method}.npz')
            assert p.valid(d['X_initial'])['valid'] and p.valid(d['X_final'])['valid']
            value,g=energy.value_gradient(d['X_final'])
            assert abs(value-float(row['final_energy']))<1e-12
            assert abs(np.linalg.norm(g)-float(row['final_gradient_norm']))<1e-12
            if row['converged']=='True':assert np.linalg.norm(g)<=1e-5
            h=read(f'histories/{case["iid"]}_{method}.csv')
            rise=max(np.diff([float(r['energy']) for r in h]),default=0.)
            max_energy_rise=max(max_energy_rise,rise)
            assert rise<=1e-12
            observed=min(float(r['min_area']) for r in h)
            assert observed+1e-13>=float(row['area_lower_bound'])
            gap=(float(row['final_energy'])-float(regular['final_energy']))/abs(float(regular['final_energy']))
            comparable=row['converged']=='True' and regular['converged']=='True' and abs(gap)<=1e-7
            comparisons.append(dict(iid=case['iid'],group=case['group'],method=method,
                converged_pair=row['converged']=='True' and regular['converged']=='True',
                relative_energy_gap=gap,comparable=comparable,
                paired_speedup=float(regular['online_seconds'])/float(row['online_seconds']) if comparable else None))
            ts=[r for r in timings if r['iid']==case['iid'] and r['method']==method]
            assert len(ts)==3
            assert all(r['converged']==row['converged'] for r in ts)
            assert abs(np.mean([float(t['online_seconds']) for t in ts])-float(row['online_seconds']))<1e-12
    write_csv(ROOT/'results/paired_comparisons.csv',comparisons)
    write_csv(ROOT/'results/reference_metrics.csv',references)
    write_json(ROOT/'results/verification.json',dict(cases=len(cases),states=len(metrics),timed_runs=len(timings),
        saved_state_metrics_checked=True,area_bound_verified=True,energy_monotone=True,
        failures=[{k:r[k] for k in ['iid','method','stop_reason']} for r in metrics if r['converged']!='True'],
        comparable_energy_relative_tolerance=1e-7))
    print('Verified 180 states, 540 timings, energy descent and area lower bounds.')

if __name__=='__main__':main()
