"""Generate physical teacher meshes for independent Gaussian-metric parameters."""
from pathlib import Path
from time import perf_counter
import argparse,json,platform
import numpy as np
from src.common import ROOT,load_config,write_json,write_csv,metric_tensor
from src.teacher import solve_reference

def parameters(config):
    rng=np.random.default_rng(config['seed'])
    low,high=np.array(list(config['parameter_ranges'].values())).T
    return rng.uniform(low,high,(config['dataset']['samples'],4))

def make_split(config):
    n=config['dataset']['samples']
    order=np.random.default_rng(config['seed']+1).permutation(n)
    nt=int(n*config['dataset']['train_fraction'])
    nv=int(n*config['dataset']['validation_fraction'])
    return dict(train=[f'mu_{i:03d}' for i in order[:nt]],
                validation=[f'mu_{i:03d}' for i in order[nt:nt+nv]],
                test=[f'mu_{i:03d}' for i in order[nt+nv:]],
                demonstration=[f'case_{name}' for name in config['display_cases']])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    cfg=load_config()
    output=ROOT/'data/teacher';output.mkdir(parents=True,exist_ok=True)
    meta_path=ROOT/'data/dataset_config.json'
    if meta_path.exists():
        assert json.loads(meta_path.read_text(encoding='utf-8'))==cfg,'Dataset configuration changed; use a separate data directory.'
    else:
        write_json(meta_path,cfg)
    all_mu=parameters(cfg)
    cases=[(f'mu_{i:03d}',mu) for i,mu in enumerate(all_mu)]
    if args.smoke:
        cases=cases[:cfg['dataset']['smoke_samples']]
    else:
        cases += [(f'case_{name}',np.asarray(mu)) for name,mu in cfg['display_cases'].items()]
    summaries=[]
    start=perf_counter()
    generated=0
    for iid,mu in cases:
        record=output/f'{iid}.npz'
        summary_path=output/f'{iid}.json'
        if record.exists() and summary_path.exists():
            saved=np.load(record)
            assert np.array_equal(saved['mu'],mu),'Teacher parameters do not match'
            summary=json.loads(summary_path.read_text(encoding='utf-8'))
        else:
            problem,result=solve_reference(mu,cfg)
            summary=dict(instance_id=iid,seed=cfg['seed'],cx=float(mu[0]),cy=float(mu[1]),
                         A=float(mu[2]),sigma=float(mu[3]),**result['summary'])
            summary['valid']=problem.valid(result['X'])['valid']
            summary['movement_norm']=float(np.linalg.norm((result['X']-problem.X0)[~problem.boundary]))
            np.savez_compressed(record,mu=mu,X0=problem.X0,X_teacher=result['X'],
                Q_teacher=result['Q'],connectivity=problem.cells,boundary_mask=problem.boundary,
                metric=problem.metric)
            write_json(summary_path,summary)
            write_csv(output/f'{iid}_history.csv',result['history'])
            generated+=1
        summaries.append(summary)
        write_csv(ROOT/'data'/('smoke_runs.csv' if args.smoke else 'teacher_runs.csv'),summaries)
        print(f'{iid}: {summary["stop_reason"]}, {summary["iterations"]} steps, '
              f'{summary["seconds"]:.3f}s, |delta X|={summary["movement_norm"]:.4f}',flush=True)
    passed=all(s['converged'] and s['valid'] and s['movement_norm']>0.01 for s in summaries)
    if args.smoke:
        meshes=[np.load(output/f'{iid}.npz')['X_teacher'] for iid,_ in cases]
        variation=float(np.max(np.linalg.norm(np.array(meshes)-meshes[0],axis=(1,2))))
        report=dict(instances=len(summaries),converged=sum(s['converged'] for s in summaries),
            valid=sum(s['valid'] for s in summaries),nontrivial_labels=passed,
            maximum_between_label_distance=variation,
            teacher_physical_not_computational=True,generated_seconds=perf_counter()-start)
        write_json(ROOT/'data/smoke_report.json',report)
        assert passed and variation>.01,'Teacher smoke test did not produce valid varying physical labels.'
        print(json.dumps(report,ensure_ascii=False),flush=True)
    else:
        failed=[s['instance_id'] for s in summaries if not s['converged'] or not s['valid']]
        write_json(ROOT/'data/failures.json',failed)
        write_json(ROOT/'data/split.json',make_split(cfg))
        # Each NPZ retains unconverged outputs too; only successful independent
        # instances may be used as supervised labels.
        write_json(ROOT/'data/dataset_summary.json',dict(instances=len(summaries),
            successful=len(summaries)-len(failed),failed=failed,
            teacher_solve_seconds=sum(s['seconds'] for s in summaries),
            current_generation_wall_seconds=perf_counter()-start,new_instances=generated,
            python=platform.python_version(),numpy=np.__version__))

if __name__=='__main__':main()
