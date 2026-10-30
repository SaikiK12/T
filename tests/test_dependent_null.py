import math
import unittest
import numpy as np
from lab.dependent_null import sample,obm,binomial_tail,tolerance_order,calibrate,calibrated_intervals,iid_intervals,binomial_interval,N


class DependentNullTests(unittest.TestCase):
    def test_literal_impulse_obm_and_shift_scale_preserve_entire_sample(self):
        x=np.zeros((N,3));x[N//2]=[1,2,-1];days=np.arange(N)
        for b in (14,28):
            r=obm(x,days,block=b);m=N-b+1
            expected=b*(b*(1/b-1/N)**2+(m-b)*(1/N)**2)/((N-b)*m)
            np.testing.assert_allclose(np.square(r['se']),[expected,4*expected,expected],rtol=1e-13)
            np.testing.assert_allclose(r['mean'],[1/N,2/N,-1/N])
            shifted=obm(x+10,days,block=b)
            np.testing.assert_allclose(shifted['se'],r['se'],rtol=1e-12)
            scaled=obm(x*100,days,block=b)
            np.testing.assert_allclose(scaled['se'],np.array(r['se'])*100,rtol=1e-13)

    def test_missing_gap_overflow_and_constant_variance_do_not_pass(self):
        x=np.ones((N,3));days=np.arange(N)
        self.assertEqual(obm(x,days,block=14)['state'],'DEGENERATE')
        self.assertEqual(obm(np.full((N,3),.1),days,block=14)['state'],'DEGENERATE')
        self.assertEqual(iid_intervals(np.full((N,3),.1),days)['state'],'DEGENERATE')
        x[5,0]=np.nan
        with self.assertRaises(ValueError):sample(x,days)
        x[5,0]=1;days[5]+=1
        with self.assertRaises(ValueError):sample(x,days)
        days=np.arange(N,dtype=np.uint64)+np.uint64(2**64-100)
        with self.assertRaises(ValueError):sample(x,days)
        with self.assertRaises(ValueError):sample(x[:-1],np.arange(N-1))

    def test_finite_but_unrepresentable_moments_and_intervals_are_not_assessed(self):
        x=np.full((N,3),1e308);x[0]=5e307;days=np.arange(N)
        self.assertEqual(iid_intervals(x,days)['state'],'DEGENERATE')
        self.assertEqual(obm(x,days,block=14)['state'],'DEGENERATE')
        x=np.zeros((N,3));x[100]=[1000,2000,3000]
        c={'n':N,'family':3,'market_validated':False,'cutoffs':{'14':1e308}}
        r=calibrated_intervals(x,days,block=14,calibration=c)
        self.assertEqual(r['state'],'DEGENERATE');self.assertIsNone(r['lower']);self.assertIsNone(r['upper'])

    def test_finite_binomial_tolerance_order_has_literal_probability(self):
        expected=sum(math.comb(20,j) for j in range(14,21))/2**20
        self.assertAlmostEqual(binomial_tail(20,14,.5),expected,places=14)
        r=tolerance_order(20,alpha=.499,confidence=.90,calibration_cells=1)
        self.assertEqual(r['order'],14)
        self.assertLessEqual(r['tail_probability'],r['cell_error_budget'])
        with self.assertRaises(ValueError):tolerance_order(20,alpha=.05,confidence=.99,calibration_cells=16)

    def test_all_declared_profiles_needed_and_worst_profile_controls_cutoff(self):
        profiles=[f'case{i}' for i in range(8)];a=np.arange(500)/100+1
        stats={f'{p}|{b}':a+i for i,p in enumerate(profiles) for b in (14,28)}
        c=calibrate(stats,profiles);k=c['tolerance']['order']
        self.assertEqual(c['cutoffs']['14'],float(a[k-1]+7))
        self.assertFalse(c['market_validated']);self.assertFalse(c['actual_order_allowed'])
        x=np.zeros((N,3));x[100]=[1,2,3]
        r=calibrated_intervals(x,np.arange(N),block=14,calibration=c)
        self.assertFalse(r['market_evidence_eligible'])
        self.assertTrue(all(l<=m<=u for l,m,u in zip(r['lower'],r['mean'],r['upper'])))
        stats.pop(next(iter(stats)))
        with self.assertRaises(ValueError):calibrate(stats,profiles)

    def test_multiplicity_adjusted_monte_carlo_interval_is_wider(self):
        a=binomial_interval(10,500,comparisons=1);b=binomial_interval(10,500,comparisons=40)
        self.assertLess(b[0],a[0]);self.assertGreater(b[1],a[1])
        a=binomial_interval(0,500,comparisons=40)
        self.assertEqual(a[0],0)
        self.assertAlmostEqual(a[1],-math.expm1(math.log(.05/(2*40))/500),places=13)
