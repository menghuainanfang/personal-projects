"""Recompute saved state metrics, convergence and training-set membership."""
import csv,json
import numpy as np
import experiment as e

def main():
    metrics=list(csv.DictReader((e.ROOT/'results/metrics.csv').open(encoding='utf-8-sig')))
    timings=list(csv.DictReader((e.ROOT/'results/timings.csv').open(encoding='utf-8-sig')))
    assert len(metrics)==165 and len(timings)==495
    assert all(len([t for t in timings if t['iid']==r['iid'] and t['method']==r['method']])==3 for r in metrics)
    assert all(t['converged']==next(r['converged'] for r in metrics if r['iid']==t['iid'] and r['method']==t['method']) for t in timings)
    for r in metrics:
        p=e.Problem(e.data(r['iid'])['mu'],e.CFG)
        with np.load(e.ROOT/f"results/meshes/{r['iid']}_{r['method']}.npz") as d:
            den=float(np.linalg.norm((d['X_teacher']-p.X0)[~p.boundary]))
            for state in ['initial','final']:
                q,x=d['Q_'+state],d['X_'+state]
                assert p.valid(q)['valid'] and p.valid(x)['valid']
                np.testing.assert_allclose(p.physical(q),x,atol=1e-13)
                assert abs(e.err(x,d['X_teacher'],den,~p.boundary)-float(r[state+'_error']))<1e-12
            value,g=p.energy.value_gradient(d['Q_final']);g[p.boundary]=0
            assert abs(np.linalg.norm(g)-float(r['final_gradient_norm']))<1e-12
            if r['converged']=='True':assert np.linalg.norm(g)<=1e-5
        history=list(csv.DictReader((e.ROOT/f"results/histories/{r['iid']}_{r['method']}.csv").open(encoding='utf-8-sig')))
        assert np.all(np.diff([float(x['energy']) for x in history])<=1e-13)
        if r['method']=='B3':
            assert r['neighbor'] in e.SPLIT['train']
            mus=np.array([e.data(i)['mu'] for i in e.SPLIT['train']])
            nearest=e.SPLIT['train'][int(np.argmin(np.sum(((mus-p.mu)/mus.std(0))**2,axis=1)))]
            assert r['neighbor']==nearest
    for r in csv.DictReader((e.ROOT/'results/diagnosis.csv').open(encoding='utf-8-sig')):
        assert float(r['decomposition_residual'])<1e-14
    for seed in [e.CFG['seed'],e.CFG['seed']+1]:
        model=e.Predictor(e.ROOT/f'models/q_mlp_{seed}.pt')
        assert model.package['train_ids']==e.SPLIT['train']
        assert model.package['validation_ids']==e.SPLIT['validation']
        ds=[e.data(i) for i in e.SPLIT['train']]
        mu=np.array([d['mu'] for d in ds])
        np.testing.assert_allclose(model.mean,mu.mean(0));np.testing.assert_allclose(model.std,mu.std(0))
        scale=np.sqrt(np.mean(np.array([(d['Q_teacher']-d['X0'])[~d['boundary_mask']].ravel() for d in ds])**2))
        assert abs(scale-model.displacement_scale)<1e-14
    failures=[dict(iid=r['iid'],method=r['method'],reason=r['stop_reason']) for r in metrics if r['converged']!='True']
    e.save_json(e.ROOT/'results/verification.json',dict(states_checked=len(metrics),timed_runs=len(timings),
        consistent_physical_reconstruction=True,correct_energy_coordinate=True,
        monotone_energy=True,nearest_neighbor_train_only=True,normalization_train_only=True,
        failures=failures))
    print('Verified',len(metrics),'states and',len(timings),'timed runs; failures:',failures)

if __name__=='__main__':main()
