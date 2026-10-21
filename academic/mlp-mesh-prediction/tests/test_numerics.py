import unittest
import numpy as np
from src.common import fixed_mesh,load_config
from src.teacher import Problem
from src.variational_mesh import WinslowEnergy
from src.geometry import signed_triangle_areas
from safe_prediction import safe_prediction

class NumericalChecks(unittest.TestCase):
    def setUp(self):
        self.cfg=load_config()
        self.problem=Problem([.5,.5,5.,.24],self.cfg)

    def test_triangle_energy_and_derivative(self):
        physical=np.array([[0.,0.],[2.,0.],[0.,1.]])
        cells=np.array([[0,1,2]])
        obj=WinslowEnergy(physical,cells,np.eye(2)[None])
        q=np.array([[0.,0.],[1.3,0.],[0.,1.]])
        value,g=obj.value_gradient(q)
        self.assertAlmostEqual(value,1+1.3**2/4,places=13)
        self.assertAlmostEqual(g[1,0],1.3/2,places=13)

    def test_topology_identity_and_state_mapping(self):
        p=self.problem
        self.assertEqual(p.reference.shape,(169,2))
        self.assertEqual(p.cells.shape,(288,3))
        self.assertEqual(np.sum(~p.boundary),121)
        self.assertAlmostEqual(signed_triangle_areas(p.X0,p.cells).sum(),1.,places=13)
        np.testing.assert_allclose(p.physical(p.reference),p.X0,atol=1e-14)
        np.testing.assert_allclose(p.physical_to_state(p.X0),p.reference,atol=1e-14)

    def test_directional_gradient_for_supported_metrics(self):
        rng=np.random.default_rng(23)
        for mu in [[.5,.5,5,.24],[.36,.64,5,.24],[.58,.43,7.5,.19]]:
            p=Problem(mu,self.cfg)
            q=p.reference.copy()
            q[~p.boundary]+=rng.uniform(-.002,.002,(sum(~p.boundary),2))
            d=rng.normal(size=q.shape);d[p.boundary]=0;d/=np.linalg.norm(d)
            value,g=p.energy.value_gradient(q)
            h=1e-5
            difference=(p.energy.value_gradient(q+h*d)[0]-p.energy.value_gradient(q-h*d)[0])/(2*h)
            self.assertAlmostEqual(difference,float(np.sum(g*d)),delta=1e-8)
            g[p.boundary]=0
            self.assertLess(p.energy.value_gradient(q-1e-3*g)[0],value)

    def test_invalid_displacement_is_damped_without_teacher(self):
        p=self.problem
        d=np.zeros((sum(~p.boundary),2))
        d[len(d)//2,0]=.7
        out=safe_prediction(p,d)
        self.assertFalse(out['metadata']['raw_valid'])
        self.assertGreater(out['metadata']['backtracks'],0)
        self.assertTrue(p.valid(out['X'])['valid'])
        self.assertTrue(p.valid(out['Q'])['valid'])
        np.testing.assert_array_equal(out['X'][p.boundary],p.X0[p.boundary])

    def test_nonfinite_prediction_falls_back_to_initial(self):
        p=self.problem
        d=np.zeros((sum(~p.boundary),2));d[0,0]=np.nan
        out=safe_prediction(p,d)
        self.assertTrue(out['metadata']['fallback'])
        np.testing.assert_array_equal(out['X'],p.X0)

if __name__=='__main__':unittest.main()
