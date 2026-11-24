"""Thorp's growth-optimal sizing with venue failure: the formulas against their closed forms."""
import math
import unittest

from scripts import stake_kelly as sk


class Kelly(unittest.TestCase):
    def test_no_jump_matches_thorp(self):
        # Thorp's S&P example: m .11, s .15, r .06 -> f* = 2.22, g(f*) = .1156; capped at 1 here, so check g directly
        m, s, r = 0.11, 0.15, 0.06
        f = (m - r) / s ** 2
        self.assertAlmostEqual(f, 2.2222, places=3)
        self.assertAlmostEqual(sk.growth(f, 1.0, m, s, 0.0, {}, r=r), (m - r) ** 2 / (2 * s ** 2) + r, places=12)

    def test_half_kelly_keeps_three_quarters(self):
        m, s, r = 0.11, 0.15, 0.06
        f = (m - r) / s ** 2
        g = lambda x: sk.growth(x, 1.0, m, s, 0.0, {}, r=r) - r
        self.assertAlmostEqual(g(f / 2) / g(f), 0.75, places=12)

    def test_break_even_failure_rate(self):
        L, m, s = 2.0, 0.04, 0.0
        lam = sk.break_even_lam(L, m)
        self.assertAlmostEqual(lam, 2 * 0.04 - sk.R_CASH)
        eps = 1e-6                                   # the growth slope at phi = 0 changes sign at lam*
        up = (sk.growth(eps, L, m, s, lam * 0.9, {"a": 1.0}) - sk.growth(0, L, m, s, lam * 0.9, {"a": 1.0})) / eps
        dn = (sk.growth(eps, L, m, s, lam * 1.1, {"a": 1.0}) - sk.growth(0, L, m, s, lam * 1.1, {"a": 1.0})) / eps
        self.assertGreater(up, 0)
        self.assertLess(dn, 0)

    def test_spreading_venues_raises_the_optimum(self):
        args = dict(L=2.0, m=0.06, s=0.0, lam=0.05)
        one, _ = sk.best(shares={"a": 1.0}, **args)
        five, _ = sk.best(shares={k: 0.2 for k in "abcde"}, **args)
        self.assertGreater(five, one)

    def test_a_venue_holding_everything_can_ruin(self):
        self.assertEqual(sk.growth(1.0, 2.0, 0.05, 0.01, 0.01, {"a": 1.0}), -math.inf)

    def test_table_runs(self):
        for base in sk.BASES:
            rows = sk.table(base)
            self.assertEqual(len(rows), 3 * 2 * 3 * 2)
            self.assertTrue(all(0 <= r["phi_star"] <= 1 for r in rows))

    def test_one_scenario(self):
        out = sk.main(["--m", "0.04", "--s", "0.02", "--L", "2", "--lam", "0.02"])
        self.assertAlmostEqual(out["break_even_lam_pct"], 100 * (0.08 - sk.R_CASH))
        self.assertGreater(out["phi_star"], 0)


if __name__ == "__main__":
    unittest.main()
