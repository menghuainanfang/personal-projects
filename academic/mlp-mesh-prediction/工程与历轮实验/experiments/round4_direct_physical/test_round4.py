"""Checks for physical geometry, interpolation and the full X derivative."""
import unittest
import numpy as np
from common import *
from physical import PhysicalEnergy,solve,OPTIONS
from metrics import sample_points,interpolation_rmse

class PhysicalTests(unittest.TestCase):
    def setUp(self):
        self.d=data(SPLIT['train'][0]);self.p=Problem(self.d['mu'],CFG)

    def test_gradient_directions(self):
        energy=PhysicalEnergy(self.p)
        rng=np.random.default_rng(20261021)
        for x in [self.p.X0,.5*(self.p.X0+self.d['X_teacher'])]:
            value,g=energy.value_gradient(x)
            for _ in range(2):
                h=rng.normal(size=x.shape);h[self.p.boundary]=0;h/=np.linalg.norm(h)
                fd=(energy.value(x+1e-6*h)-energy.value(x-1e-6*h))/(2e-6)
                self.assertLess(abs(fd-np.sum(g*h))/max(1,abs(fd)),1e-7)
            np.testing.assert_array_equal(g[self.p.boundary],0)

    def test_short_descent_boundary_and_area(self):
        opts={**OPTIONS,'max_iterations':12}
        result=solve(self.p,self.p.X0,opts)
        self.assertTrue(self.p.valid(result['X'])['valid'])
        self.assertLess(result['summary']['final_energy'],result['summary']['initial_energy'])
        self.assertTrue(np.all(np.diff([r['energy'] for r in result['history']])<=0))
        np.testing.assert_array_equal(result['X'][self.p.boundary],self.p.X0[self.p.boundary])

    def test_field_sampling_and_split(self):
        self.assertFalse(set(SPLIT['train'])&set(SPLIT['test']))
        self.assertFalse(set(SPLIT['train'])&set(SPLIT['validation']))
        xp=Predictor();qp=Predictor(SOURCE/'experiments/round3/models/q_mlp_20261021.pt')
        self.assertEqual(xp.package['train_ids'],SPLIT['train'])
        self.assertEqual(qp.package['train_ids'],SPLIT['train'])
        self.assertGreater(interpolation_rmse(self.p.X0,self.p.cells,self.p.mu,sample_points(40)),0)

    def test_physical_retreat(self):
        raw=self.p.X0+20*(self.d['X_teacher']-self.p.X0)
        x,meta=physical_safe(self.p,raw)
        self.assertLess(meta['tau'],1);self.assertTrue(self.p.valid(x)['valid'])

if __name__=='__main__':unittest.main()
