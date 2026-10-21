"""Gradient, interpolation-adapter and theoretical bound checks."""
import unittest
import numpy as np
from study import *

class StudyTests(unittest.TestCase):
    def test_general_monitor_gradient(self):
        rng=np.random.default_rng(31)
        examples=[catalog()[0],next(c for c in catalog() if c['kind']=='wave'),
                  next(c for c in catalog() if c['kind']=='double')]
        for case in examples:
            p=Problem(case['mu'],CFG);energy=MonitorEnergy(p,case)
            value,g=energy.value_gradient(p.X0)
            h=rng.normal(size=p.X0.shape);h[p.boundary]=0;h/=np.linalg.norm(h)
            fd=(energy.value(p.X0+1e-6*h)-energy.value(p.X0-1e-6*h))/(2e-6)
            self.assertLess(abs(fd-np.sum(g*h))/max(1,abs(fd)),2e-7)
            bound=4*(1/288)**2/(3*monitor_bound(case)*value)
            self.assertGreater(p.valid(p.X0)['min_area'],bound)

    def test_gaussian_energy_matches_previous(self):
        case=catalog()[0];p=Problem(case['mu'],CFG)
        a,ag=MonitorEnergy(p,case).value_gradient(p.X0)
        b,bg=PhysicalEnergy(p).value_gradient(p.X0)
        self.assertAlmostEqual(a,b,places=13)
        np.testing.assert_allclose(ag,bg,atol=1e-13)

    def test_resolution_adapter_boundary(self):
        xp=Predictor();case=next(c for c in catalog() if c['n']==24)
        cfg=copy.deepcopy(CFG);cfg['mesh']['n']=24;p=Problem(case['mu'],cfg)
        pred=prediction(p,xp,case,False)
        self.assertTrue(p.valid(pred['X'])['valid'])
        np.testing.assert_array_equal(pred['X'][p.boundary],p.reference[p.boundary])
        self.assertEqual(len(pred['X']),625)
        coarse_case={**case,'n':12}
        coarse=prediction(Problem(case['mu'],CFG),xp,coarse_case,False)
        np.testing.assert_allclose(pred['raw'].reshape(25,25,2)[::2,::2],
                                   coarse['raw'].reshape(13,13,2),atol=1e-14)

if __name__=='__main__':unittest.main()
