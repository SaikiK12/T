import unittest

import numpy as np

from lab import features, research, search
from lab.engine import Rule
from tests.test_features import synthetic


def small_setup(T=24 * 400, S=16):
    p = synthetic(T=T, S=S)
    u = research.make_universe(p, elig_top=10, col_top=14, window=24 * 10)
    specs = [s for s in features.default_specs() if s.k == 1 and s.family in ("ret", "rsi", "hour", "ema_ratio", "tbi")][:14]
    bins, names = features.views(u.bank, specs, u.elig)
    return u, bins, names


class ScoringTests(unittest.TestCase):
    def test_era_nw_matches_the_reference_engine(self):
        from lab import engine
        rng = np.random.default_rng(0)
        d = rng.normal(0.001, 0.01, (5, 400)).astype(np.float32)
        edges = np.array([0, 120, 250, 400])
        mean, t = search.era_nw(d, edges, 3)
        for r in range(5):
            for e in range(3):
                seg = d[r, edges[e]:edges[e + 1]].astype(np.float64)
                self.assertAlmostEqual(float(t[r, e]), engine.nw_t(seg, 3), places=6)
                self.assertAlmostEqual(float(mean[r, e]), float(seg.mean()), places=7)

    def test_half_year_edges_split_on_calendar_halves(self):
        u, _, _ = small_setup(T=24 * 400, S=8)
        e = search.half_year_edges(u.p, 0, 24 * 396)
        self.assertEqual(e[0], 0)
        self.assertEqual(int(e[1]), 181)                 # 2021-01-01 .. 2021-06-30
        self.assertEqual(int(e[2]), 181 + 184)           # second half of 2021
        self.assertEqual(int(e[-1]), 396)


class CatalogAndSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.u, cls.bins, cls.names = small_setup()
        cls.t0, cls.t1 = 0, 24 * 300

    def test_catalog_respects_support_limits(self):
        v, lo, hi, sup = search.condition_catalog(self.bins, self.u.elig, self.t0, self.t1)
        self.assertGreater(len(v), 20)
        self.assertTrue((sup >= 0.005).all() and (sup <= 0.40).all())
        self.assertTrue((lo <= hi).all())

    def test_a_planted_signal_is_found_and_a_placebo_does_not_find_it(self):
        u, bins, t0, t1 = self.u, self.bins, self.t0, self.t1
        # plant a market-neutral effect: where view 0 sits in its top buckets, the next bar beats the cross-section.
        # (A net drift would also score in the placebo, since a time shift keeps drift, and long-biased rules ride it.)
        ret = u.ret.copy()
        hot = ((bins[0] >= 6) & u.elig).astype(np.float32)
        n_el = np.maximum(u.elig.sum(axis=1, keepdims=True), 1)
        ret += 0.004 * (hot - hot.sum(axis=1, keepdims=True) / n_el * u.elig)
        planted = type(u)(u.p, u.elig, u.cmat, ret, u.rank, u.bank)
        cat = search.condition_catalog(bins, planted.elig, t0, t1)
        rules = search.singles(cat, directions=(1,), holds=(1,))
        edges = np.array([0, 100, 200, 300])
        real = search.score_rules(planted, bins, rules, t0, t1, edges)
        best = rules[int(np.argmax(real.peak))]
        self.assertEqual(best.view, (0,))
        self.assertGreater(float(real.peak.max()), 6.0)
        null = search.score_rules(planted, bins, rules, t0, t1, edges, ret_override=search.shifted_returns(planted, 24 * 137 + 5, limit=t1))
        self.assertLess(float(null.peak.max()), 4.0)
        grid, fdr, counts = search.empirical_fdr(real.peak, [null.peak])
        self.assertTrue(fdr[np.searchsorted(grid, 6.0)] < 0.05)

    def test_placebo_shift_stays_inside_its_window(self):
        u, limit = self.u, 24 * 300
        out = search.shifted_returns(u, 24 * 50 + 3, limit)
        self.assertTrue(np.isnan(out[limit:]).all())                         # nothing from later periods
        np.testing.assert_array_equal(out[0], u.ret[24 * 50 + 3])           # row 0 holds the return from `shift` rows later
        np.testing.assert_array_equal(out[limit - 1], u.ret[(24 * 50 + 3) - 1])   # wraps around inside the window

    def test_placebo_requires_an_explicit_window_limit(self):
        with self.assertRaises(ValueError):
            search.shifted_returns(self.u, 5)

    def test_pairs_and_triples_are_built_from_distinct_features(self):
        conds = [(0, 5, 7), (1, 0, 2), (2, 3, 3), (0, 0, 1)]
        rs = search.pairs(conds, directions=(1,), holds=(24,))
        self.assertTrue(all(len(set(r.view)) == 2 for r in rs))
        self.assertEqual(len(rs), 5)                     # C(4,2)=6 minus the pair that shares view 0

    def test_dedupe_drops_near_copies(self):
        rng = np.random.default_rng(1)
        base = rng.normal(0, 1, (3, 300))
        ret = np.vstack([base[0], base[0] + rng.normal(0, 0.1, 300), base[1], -base[1] + rng.normal(0, 0.1, 300), base[2]])
        kept = search.dedupe(ret, np.arange(5), rho=0.7)
        self.assertEqual(kept, [0, 2, 4])


if __name__ == "__main__":
    unittest.main()
