"""Recompute physical metrics and verify matched optimization records."""
import numpy as np
from common import *
from physical import PhysicalEnergy
from metrics import measure,sample_points
from experiment import A_METHODS,B_METHODS

def main():
    a=read_rows('A_metrics.csv');b=read_rows('B_metrics.csv')
    at=read_rows('A_timings.csv');bt=read_rows('B_timings.csv')
    assert len(a)==165 and len(b)==66 and len(at)==297 and len(bt)==198
    points=np.load(ROOT/'results/interpolation_points.npz')['points']
    np.testing.assert_array_equal(points,sample_points(160))
    endpoint_rows=[]
    for iid in IDS:
        d=data(iid);p=Problem(d['mu'],CFG)
        with np.load(ROOT/f'results/meshes/{iid}_A.npz') as saved:
            for method in A_METHODS:
                row=next(r for r in a if r['iid']==iid and r['method']==method)
                stats=measure(p,saved[method],d['X_teacher'],points)
                for key,val in stats.items():
                    if isinstance(val,bool):assert row[key]==str(val)
                    else:assert abs(float(row[key])-val)<1e-12
        energy=PhysicalEnergy(p)
        for method in B_METHODS:
            row=next(r for r in b if r['iid']==iid and r['method']==method)
            with np.load(ROOT/f'results/meshes/{iid}_{method}.npz') as saved:
                value,g=energy.value_gradient(saved['X_final'])
                assert p.valid(saved['X_initial'])['valid'] and p.valid(saved['X_final'])['valid']
                assert abs(value-float(row['final_energy']))<1e-12
                assert abs(np.linalg.norm(g)-float(row['final_gradient_norm']))<1e-12
                if row['converged']=='True':assert np.linalg.norm(g)<=1e-5
                stats=measure(p,saved['X_final'],d['X_teacher'],points)
                for key in ['interpolation_rmse','node_error','min_area','min_angle','min_quality']:
                    assert abs(stats[key]-float(row[key]))<1e-12
            h=read_rows(f'histories/{iid}_{method}.csv')
            assert np.all(np.diff([float(r['energy']) for r in h])<=1e-13)
            times=[r for r in bt if r['iid']==iid and r['method']==method]
            assert len(times)==3 and all(r['converged']==row['converged'] for r in times)
            assert abs(np.mean([float(r['online_seconds']) for r in times])-float(row['online_seconds']))<1e-12
        with np.load(ROOT/f'results/meshes/{iid}_physical_regular.npz') as regular, np.load(ROOT/f'results/meshes/{iid}_physical_mlp.npz') as learned:
            xr,xm=regular['X_final'],learned['X_final']
            er,em=energy.value(xr),energy.value(xm)
            endpoint_rows.append(dict(iid=iid,split='test' if iid in SPLIT['test'] else 'display',
                relative_energy_difference=(em-er)/abs(er),
                relative_endpoint_distance=float(np.linalg.norm((xm-xr)[~p.boundary])/np.linalg.norm((xr-p.X0)[~p.boundary]))))
    for name,metrics in [('A_aggregate.csv',a),('B_aggregate.csv',b)]:
        for row in read_rows(name):
            group=[r for r in metrics if r['split']=='test' and r['method']==row['method']]
            for key in ['node_error','interpolation_rmse','min_angle','min_quality']:
                assert abs(np.mean([float(r[key]) for r in group])-float(row[key]))<1e-12
    failures=[dict(iid=r['iid'],method=r['method'],reason=r['stop_reason']) for r in b if r['converged']!='True']
    write_json(ROOT/'results/verification.json',dict(A_states=len(a),B_states=len(b),
        A_timed_runs=len(at),B_timed_runs=len(bt),physical_metrics_recomputed=True,
        full_X_gradient_checked=True,monotone_physical_energy=True,aggregate_consistent=True,failures=failures))
    write_csv(ROOT/'results/B_endpoint_comparison.csv',endpoint_rows)
    print('Verified 231 physical states and 495 timed runs; failures:',failures)

if __name__=='__main__':main()
