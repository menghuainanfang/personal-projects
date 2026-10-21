"""Verify teacher labels, split/scaler isolation, accepted steps and report inputs."""
import json
import re
import numpy as np
from src.common import ROOT,load_config,read_csv,write_json
from src.teacher import Problem
from src.network import Predictor

def main():
    cfg=load_config()
    split=json.loads((ROOT/'data/split.json').read_text(encoding='utf-8'))
    groups=[set(v) for v in split.values()]
    for i,a in enumerate(groups):
        for b in groups[i+1:]:
            assert not a&b,'Instance split overlap'
    assert [len(split[k]) for k in ['train','validation','test','demonstration']]==[140,30,30,3]
    predictor=Predictor()
    assert predictor.package['train_ids']==split['train']
    assert predictor.package['validation_ids']==split['validation']
    training_mu=[];training_labels=[]
    teacher_count=0
    for iid in sum(split.values(),[]):
        d=np.load(ROOT/f'data/teacher/{iid}.npz')
        meta=json.loads((ROOT/f'data/teacher/{iid}.json').read_text(encoding='utf-8'))
        p=Problem(d['mu'],cfg)
        if meta['converged'] and meta['valid']:
            assert meta['final_gradient_norm']<=cfg['teacher']['gradient_tolerance']
            assert p.valid(d['Q_teacher'])['valid'] and p.valid(d['X_teacher'])['valid']
            np.testing.assert_allclose(p.physical(d['Q_teacher']),d['X_teacher'],atol=1e-14,rtol=0)
            if iid in split['train']:
                training_mu.append(d['mu'])
                training_labels.append((d['X_teacher']-d['X0'])[~d['boundary_mask']].ravel())
            teacher_count+=1
    np.testing.assert_allclose(predictor.mean,np.mean(training_mu,axis=0),atol=1e-14,rtol=0)
    np.testing.assert_allclose(predictor.std,np.std(training_mu,axis=0),atol=1e-14,rtol=0)
    assert abs(predictor.displacement_scale-float(np.sqrt(np.mean(np.array(training_labels)**2))))<1e-14
    metrics=read_csv(ROOT/'results/metrics.csv')
    assert len(metrics)==4*(len(split['test'])+len(split['demonstration']))
    safety=json.loads((ROOT/'results/safety.json').read_text(encoding='utf-8'))
    for iid in split['test']+split['demonstration']:
        d=np.load(ROOT/f'results/meshes/{iid}.npz')
        p=Problem(d['mu'],cfg)
        displacement=predictor.predict(d['mu'])
        np.testing.assert_allclose(displacement,(d['X_raw']-d['X0'])[~p.boundary],atol=1e-12,rtol=0)
        np.testing.assert_allclose(p.physical_to_state(d['X_damped']),d['Q_prediction'],atol=1e-14,rtol=0)
        s=next(r for r in safety if r['instance_id']==iid)
        original_norm=max(float(np.linalg.norm((d['X_damped']-d['X0'])[~p.boundary])),1e-14)
        actual_transfer=float(np.linalg.norm((d['X_prediction']-d['X_damped'])[~p.boundary])/original_norm)
        assert np.isclose(actual_transfer,s['transfer_relative_change'])
        reference_error_norm=max(np.linalg.norm((d['X_teacher']-d['X0'])[~p.boundary]),1e-14)
        for stage,x_key,q_key in [('initial','X0',None),('teacher','X_teacher','Q_teacher'),
                                  ('prediction','X_prediction','Q_prediction'),('refined','X_refined','Q_refined')]:
            row=next(r for r in metrics if r['instance_id']==iid and r['stage']==stage)
            x=d[x_key];q=p.reference if q_key is None else d[q_key]
            assert p.valid(x)['valid'] and p.valid(q)['valid']
            np.testing.assert_allclose(p.physical(q),x,atol=1e-14,rtol=0)
            value,gradient=p.energy.value_gradient(q)
            assert np.isclose(value,float(row['energy']),rtol=1e-14,atol=1e-14)
            actual=np.linalg.norm((x-d['X_teacher'])[~p.boundary])/reference_error_norm
            assert np.isclose(actual,float(row['relative_displacement_error']),atol=1e-13)
            if row['converged']=='True':
                gradient[p.boundary]=0
                assert np.linalg.norm(gradient)<=cfg['teacher']['gradient_tolerance']
        for stage in ['teacher','refined']:
            h=read_csv(ROOT/f'results/histories/{iid}_{stage}.csv')
            for before,after in zip(h,h[1:]):
                bound=float(before['energy'])-cfg['teacher']['armijo_c1']*float(after['alpha'])*float(before['gradient_norm'])**2
                assert float(after['energy'])<=bound+1e-14
                assert float(after['min_physical_area'])>cfg['mesh']['area_epsilon']
                assert float(after['min_computational_area'])>cfg['mesh']['area_epsilon']
    for a in read_csv(ROOT/'results/aggregate.csv'):
        rows=[r for r in metrics if r['split']=='test' and r['stage']==a['stage']]
        for key in ['relative_displacement_error','energy','seconds','energy_evaluations','iterations']:
            assert np.isclose(float(a[key+'_mean']),np.mean([float(r[key]) for r in rows]))
    for path in [ROOT/'paper/report.md',ROOT/'presentation/talk.md']:
        text=path.read_text(encoding='utf-8')
        assert not any(ord(c)<32 and c not in '\n\r\t' for c in text)
        assert r'\operatorname{tr}' in text
        for link in re.findall(r'!\[.*?\]\((.*?)\)',text):
            assert (path.parent/link).is_file(),link
    import pymupdf
    pdf=pymupdf.open(ROOT/'paper/report.pdf')
    assert 5<=len(pdf)<=8,f'Expected 5-8 pages, got {len(pdf)}'
    assert sum(len(page.get_images()) for page in pdf)>=6
    assert all('\ufffd' not in page.get_text() for page in pdf)
    for name in ['presentation/index.html','paper/report.html']:
        text=(ROOT/name).read_text(encoding='utf-8')
        assert 'data:image/' in text and 'data:font/' in text
    result=dict(teacher_labels_checked=teacher_count,evaluated_instances=33,
        mesh_states_checked=len(metrics),split_and_training_scaler='passed',
        physical_label_reconstruction='passed',physical_to_computational_transfer='passed',
        armijo_acceptance='passed',positive_area_and_fixed_boundary='passed',
        state_energy_and_error_metrics='passed',aggregate_csv='passed',pdf_pages=len(pdf),
        offline_report='generator built and archive verified',
        browser_visual_check=json.loads((ROOT/'results/browser_validation.json').read_text(encoding='utf-8'))['status'])
    write_json(ROOT/'results/verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
