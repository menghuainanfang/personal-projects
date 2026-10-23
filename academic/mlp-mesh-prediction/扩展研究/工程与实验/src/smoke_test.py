"""Quick independent numerical smoke, ~seconds, not a model training run."""
import json
from pathlib import Path
import numpy as np
from teacher_general import topology, make_teacher


def main():
    # Central example reproduces the archived pilot Q energy of 1.2638196185065.
    central = make_teacher(12, {'kind':'single','mu':[.5,.5,5.,.24]})
    assert abs(central['energy'] - 1.2638196185065) < 1e-7, central['energy']
    assert central['residual'] < 1e-8
    assert central['q_min_area'] > 0 and central['x_min_area'] > 0
    checks=[('single',{'kind':'single','mu':[.37,.62,6.,.19]}),
            ('double',{'kind':'double','peaks':[[.3,.3,5.,.18],[.7,.7,3.,.18]]}),
            ('wave',{'kind':'wave','phase':0.,'strength':8.,'width':.1})]
    records=[]
    for n in [8,12,16]:
        x0,cells,*_=topology(n)
        for name,spec in checks:
            try:
                out=make_teacher(n,spec)
                records.append(dict(n=n,kind=name,ok=True,energy=out['energy'],
                                    q_area=out['q_min_area'],x_area=out['x_min_area'],
                                    residual=out['residual'],seconds=out['seconds']))
            except Exception as exc:
                records.append(dict(n=n,kind=name,ok=False,error=str(exc)))
    output=Path('smoke_output.json');output.write_text(json.dumps(records,indent=2),encoding='utf-8')
    print('Center reference energy:',central['energy'])
    print(json.dumps(records,indent=2))
    if not all(r['ok'] for r in records):
        raise SystemExit('Some smoke cases failed: inspect smoke_output.json; do not hide failures.')

if __name__=='__main__':main()
