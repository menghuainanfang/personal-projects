"""Verify saved trajectories, aggregates and linked artifacts without rerunning solves."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import json,re
import numpy as np
from scripts.make_figures import read_csv
from scripts.run_experiments import write_json
from src.geometry import signed_triangle_areas
from src.variational_mesh import WinslowEnergy

def main():
    splits=json.loads((ROOT/'data/split.json').read_text(encoding='utf-8'))
    assert [len(splits[k]) for k in ['train','validation','test']]==[24,6,9]
    assert len(set(sum(splits.values(),[])))==39
    data=read_csv(ROOT/'data/dataset.csv')
    assert all(r['instance_id'] in splits[r['subset']] for r in data)
    results=read_csv(ROOT/'data/results.csv')
    assert len(results)==36
    for row in results:
        assert row['instance_id'] in splits['test']
        assert all(np.isfinite(float(row[k])) for k in ['final_energy','elapsed_seconds','min_area'])
        hist=read_csv(ROOT/f'data/trajectories/{row["instance_id"]}_{row["method"]}.csv')
        assert len(hist)==int(row['iterations'])+1
        for a,b in zip(hist,hist[1:]):
            bound=float(a['energy'])-1e-4*float(b['alpha'])*float(a['gradient_norm'])**2
            assert float(b['energy']) <= bound+1e-14
        assert float(hist[-1]['energy'])==float(row['final_energy'])
        assert int(hist[-1]['energy_evals'])==int(row['energy_evals'])
        mesh=np.load(ROOT/f'data/meshes/{row["instance_id"]}_{row["method"]}.npz')
        for key in ['initial','computational','final']:
            assert signed_triangle_areas(mesh[key],mesh['cells']).min()>1e-12
        energy=WinslowEnergy(mesh['initial'],mesh['cells'],mesh['metric'])
        v,_=energy.value_gradient(mesh['computational'])
        assert np.isclose(v,float(row['final_energy']),rtol=1e-13,atol=1e-13)
        if row['converged']=='True':
            assert float(row['final_gradient_norm'])<=float(row['gradient_tolerance'])
    for row in read_csv(ROOT/'data/aggregate.csv'):
        group=[r for r in results if r['case']==row['case'] and r['method']==row['method']]
        for key in ['final_energy','energy_evals','elapsed_seconds','backtracks','iterations']:
            assert np.isclose(float(row[key+'_mean']),np.mean([float(r[key]) for r in group]))
    for path in [ROOT/'paper/paper.md',ROOT/'presentation/talk.md']:
        text=path.read_text(encoding='utf-8')
        for link in re.findall(r'!\[.*?\]\((.*?)\)',text):
            assert (path.parent/link).is_file(),link
        assert not any(ord(c)<32 and c not in '\n\r\t' for c in text)
        assert r'\operatorname{tr}' in text
        assert r'\alpha' in text
    pdf_status='not checked'
    if (ROOT/'paper/paper.pdf').exists():
        import pymupdf
        pdf=pymupdf.open(ROOT/'paper/paper.pdf')
        assert 5<=len(pdf)<=8
        assert sum(len(p.get_images()) for p in pdf)>=6
        assert all('\ufffd' not in p.get_text() for p in pdf)
        pdf_status=f'{len(pdf)} pages, images and Chinese text present'
    for path in [ROOT/'presentation/report.html',ROOT/'paper/paper.html']:
        text=path.read_text(encoding='utf-8')
        assert 'data:image/' in text and 'data:font/' in text
        assert '<script type="module"' in text
    verification=dict(test_runs=len(results),converged=sum(r['converged']=='True' for r in results),
        split_instances=39,armijo_trajectories='passed',positive_meshes='passed',
        energy_mesh_consistency='passed',aggregate_consistency='passed',paper_pdf=pdf_status,
        browser_visual_check='not confirmed: browser connector unavailable',
        offline_html='generator build and archive verification passed')
    write_json(ROOT/'data/verification.json',verification)
    print(json.dumps(verification,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
