import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_optflow as of

H = of.HOUR
DAY = 86_400_000


def rows(**kw):
    """One flow row per keyword set: a 30-day option on an index at 100 with 50% IV, traded in the hour at T0."""
    base = {"t": of.T0, "expiry_ms": of.T0 + 30 * DAY, "strike": 100.0, "cp": "C", "buy": 0.0, "sell": 0.0,
            "block_buy": 0.0, "block_sell": 0.0, "iv": 50.0, "premium": 0.05, "index_price": 100.0}
    return pd.DataFrame([{**base, **kw}])


class SignalTest(unittest.TestCase):
    def one(self, **kw):
        return of.hourly_signals(rows(**kw)).iloc[0]

    def test_signs_of_calls_puts_and_blocks(self):
        c = self.one(buy=1.0)                                    # a taker buys an at-the-money call on the screen
        self.assertGreater(c.screen_delta, 0)
        self.assertEqual(c.block_delta, 0)
        self.assertAlmostEqual(c.drift, 0.05 * 100)               # premium (coins) x index, all of it signed bullish
        self.assertAlmostEqual(c.drift_screen, c.drift)
        self.assertEqual(c.drift_otm, 0)                          # at the money is not out of the money
        p = self.one(cp="P", buy=1.0)                             # a taker buys a put: bearish
        self.assertLess(p.screen_delta, 0)
        self.assertAlmostEqual(p.drift, -5.0)
        ps = self.one(cp="P", sell=1.0, strike=80.0)              # a taker sells an out-of-the-money put: bullish
        self.assertGreater(ps.drift, 0)
        self.assertAlmostEqual(ps.drift_otm, ps.drift)
        b = self.one(buy=1.0, block_buy=1.0, strike=120.0)        # a block call buy, out of the money
        self.assertGreater(b.block_delta, 0)
        self.assertAlmostEqual(b.screen_delta, 0)
        self.assertAlmostEqual(b.drift_screen, 0)
        self.assertGreater(b.drift_otm, 0)
        half = self.one(buy=1.0, sell=1.0)                        # two-way flow nets to nothing
        self.assertAlmostEqual(half.drift, 0)
        self.assertAlmostEqual(half.screen_delta, 0)

    def test_no_iv_gives_no_delta_but_keeps_the_drift(self):
        s = self.one(buy=2.0, iv=np.nan)
        self.assertEqual((s.screen_delta, s.amount_no_delta), (0.0, 2.0))
        self.assertGreater(s.drift, 0)


class TimingTest(unittest.TestCase):
    def test_a_row_is_known_only_after_its_hour(self):
        h = pd.DataFrame({"drift": [1.0]}, index=pd.Index([of.T0 + 10 * H], name="t"))
        s = of.hour_array(h, "drift", nh=40)
        S = of.window_sum(s, 4)
        self.assertEqual(np.flatnonzero(np.nan_to_num(S)).tolist(), [11, 12, 13, 14])   # instants T0 + 11 h .. 14 h
        self.assertTrue(np.isnan(S[:4]).all())

    def test_zscore_reads_only_the_past(self):
        rng = np.random.default_rng(0)
        S = rng.normal(size=900)
        x = of.zscore(S)
        self.assertTrue(np.isnan(x[:500]).all() and np.isfinite(x[500:]).all())
        S2 = S.copy()
        S2[700:] += 100
        x2 = of.zscore(S2)
        np.testing.assert_array_equal(x[:700], x2[:700])
        self.assertEqual(x2[700], of.WINSOR)                      # a jump is capped

    def test_forward_return(self):
        PH = np.array([100.0, 110.0, np.nan, 121.0])
        r = of.fwd_return(PH, 1)
        self.assertAlmostEqual(r[0], np.log(1.1))
        self.assertTrue(np.isnan(r[1]) and np.isnan(r[2]) and np.isnan(r[3]))


class RuleTest(unittest.TestCase):
    def test_trades_do_not_overlap(self):
        x = np.array([2.0, 2.0, 2.0, 0.0, -2.0, 0.5])
        r = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.06])
        g = of.rule(x, r, 2, np.ones(6, bool))
        np.testing.assert_allclose(g, [0.01, 0.03, -0.05])
        s = of.rule_stats(g)
        self.assertAlmostEqual(s["net1_bp"], (np.mean(g) - 2 * of.COST) * 1e4)
        self.assertAlmostEqual(s["net3_bp"], (np.mean(g) - 6 * of.COST) * 1e4)


class PlantedTest(unittest.TestCase):
    def test_a_planted_lead_is_found_and_noise_is_not(self):
        rng = np.random.default_rng(1)
        n = of.NH + 1
        x, r = {}, {}
        for c in of.COINS:
            for h in of.HORIZONS:
                r[(c, h)] = rng.normal(0, 0.01, n)
                for s in of.SIGNALS:
                    x[(c, s, h)] = rng.normal(size=n)
            r[(c, 4)] = 0.002 * x[(c, "drift_otm", 4)] + rng.normal(0, 0.01, n)
        res = of.analyze(x, r)
        self.assertEqual(res["passes"], ["drift_otm h4"])
        self.assertEqual(res["verdict"], "PARTIAL")
        t = next(z for z in res["tests"] if z["signal"] == "drift_otm" and z["h"] == 4)
        self.assertGreater(t["valid_rule"]["gross_bp"], 0)
        x[("BTC", "drift", 1)] = -x[("BTC", "drift", 1)]
        r[("BTC", 1)] = 0.002 * x[("BTC", "drift", 1)] + rng.normal(0, 0.01, n)
        r[("BTC", 1)] = -r[("BTC", 1)]                            # a lead with the wrong sign is not a pass
        res = of.analyze(x, r)
        self.assertNotIn("drift h1", res["passes"])


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        d = self.tmp / "BTC" / "flow"
        d.mkdir(parents=True)
        for ym, t in (("2020-12", of.T0 - DAY), ("2021-01", of.T0 + H)):
            rows(t=t).to_parquet(d / f"{ym}.parquet", index=False)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_reads_only_the_window_and_checks_hashes(self):
        good = {f"BTC/flow/{p.name}": prereg.sha256_file(p) for p in (self.tmp / "BTC" / "flow").glob("*.parquet")}
        f = of.load_rows("BTC", root=self.tmp, hashes=good)
        self.assertEqual(f.t.tolist(), [of.T0 + H])
        bad = {**good, "BTC/flow/2021-01.parquet": "0" * 64}
        with self.assertRaises(prereg.PreregError):
            of.load_rows("BTC", root=self.tmp, hashes=bad)
        of.load_rows("BTC", root=self.tmp, hashes={"BTC/flow/2021-01.parquet": good["BTC/flow/2021-01.parquet"]})


if __name__ == "__main__":
    unittest.main()
