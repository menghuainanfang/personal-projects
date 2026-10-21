"""Checks for the coordinate interfaces used in this experiment."""
import unittest
import numpy as np
import experiment as e

class CoordinateTests(unittest.TestCase):
    def setUp(self):
        self.d=e.data(e.SPLIT['test'][0]);self.p=e.Problem(self.d['mu'],e.CFG)

    def test_teacher_cycle_is_not_identity(self):
        q=self.p.physical_to_state(self.d['X_teacher']);x=self.p.physical(q)
        self.assertTrue(self.p.valid(q)['valid'])
        self.assertTrue(self.p.valid(x)['valid'])
        self.assertGreater(np.linalg.norm(x-self.d['X_teacher']),1e-4)
        np.testing.assert_allclose(self.p.physical(self.d['Q_teacher']),self.d['X_teacher'],atol=1e-14)

    def test_computational_safety(self):
        raw=self.p.reference+12*(self.d['Q_teacher']-self.p.reference)
        s=e.q_safe(self.p,raw)
        self.assertLess(s['tau'],1.)
        self.assertTrue(self.p.valid(s['Q'])['valid'])
        self.assertTrue(self.p.valid(s['X'])['valid'])
        np.testing.assert_array_equal(s['Q'][self.p.boundary],self.p.reference[self.p.boundary])
        np.testing.assert_allclose(self.p.physical(s['Q']),s['X'],atol=1e-14)

    def test_nonfinite_displacement_falls_back(self):
        raw=self.p.reference.copy();raw[~self.p.boundary]=np.nan
        s=e.q_safe(self.p,raw)
        self.assertTrue(s['fallback'])
        np.testing.assert_array_equal(s['Q'],self.p.reference)

if __name__=='__main__':unittest.main()
