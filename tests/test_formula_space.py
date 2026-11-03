"""Algebra, missingness, units and invented-world discovery; no market reads."""
from fractions import Fraction as F
import math
import random
import unittest

from lab import formula_space as f


class FormulaTests(unittest.TestCase):
    def setUp(self):
        self.x=f.variable("x",f.PRICE)
        self.y=f.variable("y",f.PRICE)
        self.z=f.variable("z")

    def values(self,**values):
        atoms={a.name:a for e in (self.x,self.y,self.z) for a in e.inputs}
        return {atoms[k]:v for k,v in values.items()}

    def test_expansion_commutation_and_distribution_are_proved(self):
        self.assertTrue(f.equivalent(self.x+self.y,self.y+self.x))
        self.assertTrue(f.equivalent(2*(self.x+self.y),2*self.x+2*self.y))
        self.assertTrue(f.equivalent((self.x-self.y)/self.y,self.x/self.y-1))

    def test_close_location_and_wick_formulas_share_exact_value(self):
        h,l,c=(f.variable(n,f.PRICE) for n in ("high","low","close"))
        location=(c-l)/(h-l)
        wick=((c-l)-(h-c))/(h-l)
        self.assertTrue(f.equivalent(wick,2*location-1))
        self.assertFalse(f.equivalent(wick,location))
        self.assertTrue(f.predicate_equivalent(location,F(4,5),wick,F(3,5)))

    def test_threshold_alias_boundary_and_direction_are_preserved(self):
        a,b=self.x/self.y,2*(self.x/self.y)-1
        self.assertTrue(f.predicate_equivalent(a,F(4,5),b,F(3,5)))
        self.assertFalse(f.predicate_equivalent(a,F(4,5),b,F(2,5)))
        self.assertFalse(f.predicate_equivalent(a,F(4,5),-a,-F(4,5)))
        v=self.values(x=4,y=5)
        self.assertEqual(a.evaluate(v),F(4,5))
        self.assertEqual(b.evaluate(v),F(3,5))
        self.assertFalse(a.evaluate(v)>F(4,5))
        self.assertTrue(a.evaluate(v)>=F(4,5))
        with self.assertRaises(ValueError):
            f.predicate_equivalent(a,0,b,0,comparison="approx")

    def test_zero_divisor_is_not_erased_by_cancellation(self):
        ratio=self.x/self.x
        self.assertFalse(f.equivalent(ratio,f.constant(1)))
        self.assertIsNone(ratio.evaluate(self.values(x=0)))
        self.assertEqual(ratio.evaluate(self.values(x=9)),F(1))
        with self.assertRaisesRegex(ValueError,"zero divisor"):
            self.x/(self.y-self.y)

    def test_zero_numerator_still_requires_divisor_and_input(self):
        a=f.constant(0,f.PRICE)/self.x
        self.assertIsNone(a.evaluate({}))
        self.assertIsNone(a.evaluate(self.values(x=0)))
        self.assertEqual(a.evaluate(self.values(x=8)),0)
        self.assertFalse(f.equivalent(a,f.constant(0)))

    def test_cancelled_missing_inputs_do_not_become_observed_zeros(self):
        a=self.x-self.x
        self.assertIsNone(a.evaluate({}))
        self.assertFalse(f.equivalent(a,f.constant(0,f.PRICE)))
        self.assertEqual(a.evaluate(self.values(x=7)),0)
        b=(self.x/self.y)*self.y
        self.assertFalse(f.equivalent(b,self.x))
        self.assertIsNone(b.evaluate(self.values(x=7,y=0)))

    def test_guards_are_scalar_normalized_without_changing_sign(self):
        self.assertTrue(f.equivalent(self.x/(2*self.y),(self.x/self.y)/2))
        self.assertTrue(f.equivalent(self.x/(-self.y),-(self.x/self.y)))

    def test_incomplete_domain_proofs_are_conservative(self):
        # These zero sets coincide, but this small engine does not factor them.
        a=(self.x/self.y)/self.y
        b=self.x/(self.y*self.y)
        self.assertFalse(f.equivalent(a,b))
        self.assertEqual(a.evaluate(self.values(x=7,y=2)),b.evaluate(self.values(x=7,y=2)))

    def test_nonfinite_and_bool_measurements_remain_unknown(self):
        for value in (float("nan"),float("inf"),True,None,"7"):
            with self.subTest(value=value):
                self.assertIsNone(self.x.evaluate(self.values(x=value)))
        self.assertEqual(self.x.evaluate(self.values(x=.1)),F(1,10))
        with self.assertRaises(ValueError):
            f.constant(float("inf"))

    def test_units_reject_incoherent_sums_and_track_products(self):
        volume=f.variable("volume",f.VOLUME)
        with self.assertRaisesRegex(ValueError,"unlike units"):
            self.x+volume
        self.assertEqual((self.x*volume).unit,f.PRICE.combine(f.VOLUME))
        self.assertEqual((self.x/self.y).unit,f.ONE)
        with self.assertRaises(ValueError):
            f.Unit(price=True)
        with self.assertRaises(ValueError):
            f.constant(1,"usd")

    def test_same_input_name_with_conflicting_units_is_rejected(self):
        other=f.variable("x",f.VOLUME)
        with self.assertRaisesRegex(ValueError,"conflicting units"):
            self.x*other

    def test_future_lags_and_implicit_clock_joins_are_rejected(self):
        for lag in (-1,True,1.5):
            with self.assertRaises(ValueError):
                f.variable("x",lag=lag)
        other=f.variable("y",f.PRICE,clock="exchange")
        with self.assertRaisesRegex(ValueError,"different clocks"):
            self.x-other
        lagged=f.variable("x",f.PRICE,lag=1)
        self.assertFalse(f.equivalent(self.x,lagged))

    def test_price_scale_invariance_of_dimensionless_bar_geometry(self):
        ratio=(self.x-self.y)/self.y
        for scale in (F(1,100),F(1),F(1000)):
            self.assertEqual(ratio.evaluate(self.values(x=12*scale,y=10*scale)),F(1,5))

    def test_equivalence_agrees_with_independent_scalar_arithmetic(self):
        a=(self.x-self.y)/self.y
        b=self.x/self.y-1
        rng=random.Random(3)
        for _ in range(100):
            x,y=rng.randint(-100,100),rng.choice([i for i in range(-100,101) if i])
            values=self.values(x=x,y=y)
            self.assertEqual(a.evaluate(values),F(x-y,y))
            self.assertEqual(a.evaluate(values),b.evaluate(values))

    def test_accidental_sample_correlation_does_not_prove_identity(self):
        self.assertFalse(f.equivalent(self.x,self.y))
        values=self.values(x=7,y=7)
        self.assertEqual(self.x.evaluate(values),self.y.evaluate(values))

    def test_expression_and_polynomial_budgets_stop_growth(self):
        x=self.x
        with self.assertRaises(f.BudgetError):
            for _ in range(10):
                x=x*x
        with self.assertRaises(f.BudgetError):
            product=f.constant(1)
            for n in range(7):
                product=product*(f.variable("a"+str(n))+f.variable("b"+str(n)))


class FamilyTests(unittest.TestCase):
    def test_factory_recovers_a_planted_nonlinear_equation(self):
        x,z=f.variable("x",f.PRICE),f.variable("z")
        family=f.enumerate_family((x,z,f.constant(1)))
        planted=x/(1+z)
        exact=[e for e in family.forms if f.equivalent(e,planted)]
        self.assertEqual(len(exact),1)
        self.assertEqual(family.attempts,len(family.forms)+family.duplicates+family.invalid)
        self.assertGreater(family.duplicates,0)
        self.assertFalse(family.budget_exhausted)
        a,b=next(iter(x.inputs)),next(iter(z.inputs))
        for xv,zv in ((F(3),F(1,2)),(F(11),F(5)),(F(-2),F(3))):
            self.assertEqual(exact[0].evaluate({a:xv,b:zv}),xv/(1+zv))

    def test_factory_budget_is_explicit_and_repeatable(self):
        leaves=(f.variable("x"),f.variable("z"),f.constant(1))
        first=f.enumerate_family(leaves,max_attempts=20)
        self.assertTrue(first.budget_exhausted)
        self.assertEqual(first.attempts,20)
        self.assertEqual(first,f.enumerate_family(leaves,max_attempts=20))
        for args in (dict(max_nodes=4),dict(max_nodes=11),dict(max_attempts=2)):
            with self.assertRaises(ValueError):
                f.enumerate_family(leaves,**args)

    def test_no_future_target_or_sample_is_accepted_by_factory(self):
        with self.assertRaises(TypeError):
            f.enumerate_family((f.variable("x"),),target=[1,2,3])


class PathTests(unittest.TestCase):
    def test_same_ohlcv_does_not_identify_the_intrabar_path(self):
        a,b=[100,110,90,105],[100,90,110,105]
        def ohlcv(path):
            return path[0],max(path),min(path),path[-1],4
        self.assertEqual(ohlcv(a),ohlcv(b))
        self.assertNotEqual(sum(abs(y-x) for x,y in zip(a,a[1:])),sum(abs(y-x) for x,y in zip(b,b[1:])))

    def test_flow_first_and_price_first_have_opposite_area(self):
        flow_first=f.signed_area([0,0,1],[0,1,1])
        price_first=f.signed_area([0,1,1],[0,0,1])
        self.assertEqual(flow_first,-F(1,2))
        self.assertEqual(price_first,F(1,2))

    def test_translation_subdivision_and_reversal_geometry(self):
        x,y=[0,0,1],[0,1,1]
        area=f.signed_area(x,y)
        self.assertEqual(f.signed_area([v+100 for v in x],[v-7 for v in y]),area)
        self.assertEqual(f.signed_area([0,0,0,1],[0,F(1,2),1,1]),area)
        self.assertEqual(f.signed_area(x[::-1],y[::-1]),-area)

    def test_missing_paths_remain_unknown_and_alignment_is_checked(self):
        self.assertIsNone(f.signed_area([0,float("nan"),1],[0,1,1]))
        self.assertIsNone(f.signed_area([0,None,1],[0,1,1]))
        with self.assertRaises(ValueError):
            f.signed_area([0,1],[0])
        with self.assertRaises(f.BudgetError):
            f.signed_area([0]*(f.MAX_PATH_POINTS+1),[0]*(f.MAX_PATH_POINTS+1))


if __name__=="__main__":
    unittest.main()
