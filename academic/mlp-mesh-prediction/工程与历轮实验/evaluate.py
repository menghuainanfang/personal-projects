"""Paired unseen-instance tests of initial, teacher, prediction and refinement meshes."""
from time import perf_counter
import json
import numpy as np
from src.common import ROOT,load_config,write_json,write_csv
from src.teacher import Problem,solve_reference,solve_state
from src.network import Predictor
from safe_prediction import safe_prediction

def hybrid(mu,cfg,predictor):
    start=perf_counter()
    problem=Problem(mu,cfg)
    setup_seconds=perf_counter()-start
    t=perf_counter()
    displacement=predictor.predict(mu)
    inference_seconds=perf_counter()-t
    safe=safe_prediction(problem,displacement)
    prediction_seconds=perf_counter()-start
    refined=solve_state(problem,safe['Q'])
    total=perf_counter()-start
    timing=dict(setup_seconds=setup_seconds,inference_seconds=inference_seconds,
                safety_seconds=safe['metadata']['seconds'],prediction_seconds=prediction_seconds,
                refinement_seconds=refined['summary']['seconds'],hybrid_seconds=total)
    return problem,safe,refined,timing

def main():
    cfg=load_config();predictor=Predictor()
    split=json.loads((ROOT/'data/split.json').read_text(encoding='utf-8'))
    evaluation=[(iid,'test') for iid in split['test']]+[(iid,'demonstration') for iid in split['demonstration']]
    output=ROOT/'results/meshes';output.mkdir(exist_ok=True)
    (ROOT/'results/histories').mkdir(exist_ok=True)
    metrics=[];timings=[];safety=[]
    for index,(iid,subset) in enumerate(evaluation):
        stored=np.load(ROOT/f'data/teacher/{iid}.npz')
        mu=stored['mu']
        meta=json.loads((ROOT/f'data/teacher/{iid}.json').read_text(encoding='utf-8'))
        if not (meta['converged'] and meta['valid']):
            safety.append(dict(instance_id=iid,split=subset,skipped_failed_teacher=True))
            continue
        repeats=[]
        first=None
        for repeat in range(cfg['timing']['online_repetitions']):
            if (index+repeat)%2==0:
                _,teacher=solve_reference(mu,cfg)
                problem,safe,refined,timing=hybrid(mu,cfg,predictor)
            else:
                problem,safe,refined,timing=hybrid(mu,cfg,predictor)
                _,teacher=solve_reference(mu,cfg)
            np.testing.assert_allclose(teacher['X'],stored['X_teacher'],rtol=0,atol=1e-12)
            row=dict(instance_id=iid,split=subset,repeat=repeat,
                     teacher_seconds=teacher['summary']['seconds'],**timing)
            repeats.append(row);timings.append(row)
            if first is None:first=(problem,safe,refined,teacher)
        problem,safe,refined,teacher=first
        mean_times={key:float(np.mean([r[key] for r in repeats]))
                    for key in ['teacher_seconds','setup_seconds','inference_seconds',
                                'safety_seconds','prediction_seconds','refinement_seconds','hybrid_seconds']}
        mean_times['teacher_seconds_std']=float(np.std([r['teacher_seconds'] for r in repeats],ddof=1))
        mean_times['hybrid_seconds_std']=float(np.std([r['hybrid_seconds'] for r in repeats],ddof=1))
        denominator=max(float(np.linalg.norm((teacher['X']-problem.X0)[~problem.boundary])),1e-14)
        def relative(x):
            return float(np.linalg.norm((x-teacher['X'])[~problem.boundary])/denominator)
        initial_value=teacher['history'][0]['energy']
        teacher_value=teacher['summary']['final_energy']
        raw_error=relative(safe['raw']) if np.all(np.isfinite(safe['raw'])) else None
        safety.append(dict(instance_id=iid,split=subset,skipped_failed_teacher=False,
            raw_relative_error=raw_error,damped_relative_error=relative(safe['damped']),
            aligned_relative_error=relative(safe['X']),**safe['metadata']))
        for stage,x,q,summary,seconds in [
                ('initial',problem.X0,problem.reference,None,0.0),
                ('teacher',teacher['X'],teacher['Q'],teacher['summary'],mean_times['teacher_seconds']),
                ('prediction',safe['X'],safe['Q'],None,mean_times['prediction_seconds']),
                ('refined',refined['X'],refined['Q'],refined['summary'],mean_times['hybrid_seconds'])]:
            status=problem.valid(x)
            energy,_=problem.energy.value_gradient(q)
            metrics.append(dict(instance_id=iid,split=subset,stage=stage,
                cx=float(mu[0]),cy=float(mu[1]),A=float(mu[2]),sigma=float(mu[3]),
                relative_displacement_error=relative(x),energy=energy,
                relative_energy_gap=(energy-teacher_value)/abs(teacher_value),
                excess_energy_fraction=(energy-teacher_value)/max(initial_value-teacher_value,1e-14),
                min_area=status['min_area'],legal=status['valid'],flipped_cells=status['flipped_cells'],
                iterations=summary['iterations'] if summary else 0,
                energy_evaluations=summary['energy_evaluations'] if summary else 0,
                converged=summary['converged'] if summary else None,
                final_gradient_norm=summary['final_gradient_norm'] if summary else None,
                seconds=seconds,raw_valid=safe['metadata']['raw_valid'],
                displacement_tau=safe['metadata']['tau'],safety_backtracks=safe['metadata']['backtracks'],
                fallback=safe['metadata']['fallback'],
                transfer_relative_change=safe['metadata']['transfer_relative_change'],
                **mean_times))
        np.savez_compressed(output/f'{iid}.npz',mu=mu,X0=problem.X0,cells=problem.cells,
            boundary=problem.boundary,X_teacher=teacher['X'],Q_teacher=teacher['Q'],
            X_raw=safe['raw'],X_damped=safe['damped'],X_prediction=safe['X'],Q_prediction=safe['Q'],
            X_refined=refined['X'],Q_refined=refined['Q'])
        write_csv(ROOT/f'results/histories/{iid}_teacher.csv',teacher['history'])
        write_csv(ROOT/f'results/histories/{iid}_refined.csv',refined['history'])
        write_csv(ROOT/'results/metrics.csv',metrics)
        write_csv(ROOT/'results/timings.csv',timings)
        write_json(ROOT/'results/safety.json',safety)
        print(f'{iid}: error={relative(safe["X"]):.4f}, tau={safe["metadata"]["tau"]}, '
              f'teacher {mean_times["teacher_seconds"]:.3f}s/{teacher["summary"]["iterations"]} steps, '
              f'hybrid {mean_times["hybrid_seconds"]:.3f}s/{refined["summary"]["iterations"]} steps, '
              f'{refined["summary"]["stop_reason"]}',flush=True)
    test=[r for r in metrics if r['split']=='test']
    aggregate=[]
    for stage in ['initial','teacher','prediction','refined']:
        rows=[r for r in test if r['stage']==stage]
        a=dict(stage=stage,instances=len(rows),legal=sum(r['legal'] for r in rows),
               converged=sum(r['converged'] is True for r in rows))
        for key in ['relative_displacement_error','energy','relative_energy_gap','excess_energy_fraction',
                    'min_area','iterations','energy_evaluations','seconds','transfer_relative_change']:
            values=np.array([r[key] for r in rows],dtype=float)
            a[key+'_mean']=float(values.mean());a[key+'_std']=float(values.std(ddof=1))
        aggregate.append(a)
    write_csv(ROOT/'results/aggregate.csv',aggregate)
    valid_safety=[r for r in safety if not r['skipped_failed_teacher']]
    test_safety=[r for r in valid_safety if r['split']=='test']
    def stats(rows):
        return dict(instances=len(rows),raw_legal_rate=float(np.mean([r['raw_valid'] for r in rows])),
            safe_legal_rate=float(np.mean([r['safe_valid'] for r in rows])),
            fallback_rate=float(np.mean([r['fallback'] for r in rows])),
            mean_backtracks=float(np.mean([r['backtracks'] for r in rows])),
            max_transfer_relative_change=float(np.max([r['transfer_relative_change'] for r in rows])),
            mean_raw_relative_error=float(np.mean([r['raw_relative_error'] for r in rows])),
            mean_damped_relative_error=float(np.mean([r['damped_relative_error'] for r in rows])),
            mean_aligned_relative_error=float(np.mean([r['aligned_relative_error'] for r in rows])))
    time_pairs=[r for r in test if r['stage']=='refined']
    summary=dict(test=stats(test_safety),all_evaluated=stats(valid_safety),
        teacher_mean_seconds=float(np.mean([r['teacher_seconds'] for r in time_pairs])),
        hybrid_mean_seconds=float(np.mean([r['hybrid_seconds'] for r in time_pairs])),
        ratio_of_mean_times=float(np.mean([r['teacher_seconds'] for r in time_pairs])/
                                  np.mean([r['hybrid_seconds'] for r in time_pairs])),
        prediction_mean_seconds=float(np.mean([r['prediction_seconds'] for r in time_pairs])),
        skipped_teachers=[r['instance_id'] for r in safety if r['skipped_failed_teacher']],
        timing_repeats=cfg['timing']['online_repetitions'],
        timing_scope='CPU model preloaded; includes problem setup, input scaling, inference, damping, '
                     'state transfer and refinement; excludes model loading, training, diagnostics and file IO',
        paired_order='alternated within instance and repeat',energy_variable='computational Q')
    write_json(ROOT/'results/evaluation_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
