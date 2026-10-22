import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_charmexpiry as ce

MIN, HOUR, DAY = ce.MIN, ce.HOUR, ce.DAY
E = ce.T0 + 8 * HOUR                         # 2021-01-01 is a Friday: its 08:00 UTC expiry


def flow(*rows):
    """Flow rows (t, instrument, strike, cp, buy, sell) of options expiring at E."""
    return pd.DataFrame([{"t": t, "instrument": f"BTC-{k:g}-{cp}", "expiry_ms": E, "strike": float(k), "cp": cp,
                          "buy": b, "sell": s} for t, k, cp, b, s in rows])


class ExposureTest(unittest.TestCase):
    def test_expiry_delta_and_the_dealer_sign(self):
        K, call = np.array([100.0, 100.0]), np.array([True, False])
        np.testing.assert_array_equal(ce.step_delta(101.0, K, call), [1.0, 0.0])
        np.testing.assert_array_equal(ce.step_delta(99.0, K, call), [0.0, -1.0])
        np.testing.assert_array_equal(ce.step_delta(100.0, K, call), [0.5, -0.5])
        # takers bought 2 calls that finish in the money: dealers are short them, delta -2 coins, hedged long 2 coins,
        # and sell that hedge once the calls settle, so D < 0 predicts a fall
        self.assertAlmostEqual(ce.dealer_delta(101.0, np.array([100.0]), np.array([True]), np.array([2.0])), -202.0)
        # takers bought puts that finish in the money: dealers are long delta and buy back their short hedge
        self.assertGreater(ce.dealer_delta(99.0, np.array([100.0]), np.array([False]), np.array([3.0])), 0)

    def test_positions_use_only_rows_known_by_the_cut(self):
        f = flow((E - 3 * HOUR, 100, "C", 2.0, 0.0), (E - HOUR, 100, "C", 0.0, 1.5), (E - 2 * HOUR, 99, "P", 0.0, 1.0))
        K, call, pos = ce.positions(f, E - 2 * HOUR)
        self.assertEqual(dict(zip(K, pos)), {99.0: -1.0, 100.0: 2.0})
        K, call, pos = ce.positions(f, E - HOUR)
        self.assertEqual(dict(zip(K, pos)), {99.0: -1.0, 100.0: 0.5})
        self.assertEqual(len(ce.positions(f, E - 4 * HOUR)[0]), 0)

    def test_near_money_band(self):
        K = np.array([100.0, 103.0, 98.0, 101.0])
        pos = np.array([1.0, 5.0, -2.0, -0.5])
        self.assertAlmostEqual(ce.near_money(100.0, K, pos), (1 + 2 + 0.5) * 100)   # 103 is 3% away, 98 is 2%


class TableTest(unittest.TestCase):
    def test_prices_returns_and_inputs_at_each_decision(self):
        P = np.full(2 * 1440 + 1, 100.0)
        i = lambda tau: (tau - ce.T0) // MIN
        P[i(E - 29 * MIN)] = 100.2                     # 07:31, the C entry
        P[i(E - MIN)] = 100.6                          # 07:59, the C exit
        P[i(E)] = 101.0                                # 08:00: the window moved +1%
        P[i(E + MIN)] = 101.0                          # 08:01, the A and B entry
        P[i(E + 61 * MIN)] = 100.5                     # the h60 exit
        P[i(E + 121 * MIN)] = 102.0                    # the h120 exit
        rows = flow((E - 3 * HOUR, 100.5, "C", 2.0, 0.0),        # in the money at 08:00, not at 07:30
                    (E - HOUR, 99.0, "P", 0.0, 1.0),             # traded 07:00-08:00: unknown at 07:30
                    (E - 3 * HOUR, 110.0, "C", 4.0, 0.0))        # far out of the money
        adv = pd.Series({E // DAY: 1e6})
        t = ce.friday_table(rows, P, adv, [E], "BTC")
        r = t.iloc[0]
        self.assertAlmostEqual(r.m, 0.01)
        self.assertAlmostEqual(r.y60, -(100.5 / 101 - 1))        # fade an up move: short at 08:01
        self.assertAlmostEqual(r.y120, -(102 / 101 - 1))
        self.assertAlmostEqual(r.r60, np.log(100.5 / 101))
        self.assertAlmostEqual(r.rC, np.log(100.6 / 100.2))
        self.assertAlmostEqual(r.N, (2 + 1) * 100)                # 100.5 and 99 are within 2% of 100; 110 is not
        self.assertAlmostEqual(r.Db, -2 * 101.0)                  # at 08:00 the 100.5 call is in, the 99 put out
        self.assertAlmostEqual(r.Dc, 0.0)                         # at 07:30 the call is out; the put is not known
        self.assertEqual((r.n_opt, r.adv), (3, 1e6))


class TrailingTest(unittest.TestCase):
    def test_scaling_reads_only_the_past(self):
        rng = np.random.default_rng(0)
        v = rng.normal(size=80)
        x = ce.trailing(v, center=True)
        self.assertTrue(np.isnan(x[:ce.NEED]).all() and np.isfinite(x[ce.NEED:]).all())
        v2 = v.copy()
        v2[50:] += 100
        np.testing.assert_array_equal(x[:50], ce.trailing(v2, center=True)[:50])
        self.assertEqual(ce.trailing(v2, center=True)[50], ce.WINSOR)
        w = v[40 - ce.LOOK if 40 > ce.LOOK else 0:40]
        self.assertAlmostEqual(ce.trailing(v, center=False)[40], v[40] / np.sqrt(np.mean(w ** 2)))


class PlantedTest(unittest.TestCase):
    def table(self, rng, n=1000):
        exp = ce.T0 + 8 * HOUR + np.arange(2 * n, dtype=np.int64) * 7 * DAY
        parts = []
        for c in ce.COINS:
            t = pd.DataFrame({"expiry": exp, "coin": c, "win": np.repeat(["disc", "valid"], n)})
            for x in ("xA", "xB", "xC"):
                t[x] = rng.normal(0.5, 1.0, 2 * n)                  # xA has a mean: the fade's own mean must not count
            for y in ("y60", "r60", "r120", "rC"):
                t[y] = rng.normal(0, 0.01, 2 * n)
            t["y120"] = 0.003 + rng.normal(0, 0.01, 2 * n)            # a fade that wins on average, at every dose
            t["y60"] = 0.002 * t.xA + rng.normal(0, 0.01, 2 * n)       # a planted dose effect
            t["r60"] = -0.002 * t.xB + rng.normal(0, 0.01, 2 * n)      # an unwind with the wrong sign
            t["p0801"], t["X60"], t["X120"], t["p0731"] = 100.0, 100.0 * np.exp(t.r60), 100.0 * np.exp(t.r120), 100.0
            t["p0759"] = 100.0 * np.exp(t.rC)
            parts.append(t)
        return pd.concat(parts, ignore_index=True), exp

    def test_a_planted_dose_passes_and_the_rest_do_not(self):
        tab, exp = self.table(np.random.default_rng(3))
        res = ce.analyze(tab, exp)
        self.assertEqual(res["passes"], ["A h60"])
        self.assertEqual(res["significant_against"], ["B h60"])
        self.assertEqual(res["verdict"], "PARTIAL")
        a120 = next(t for t in res["tests"] if t["trial"] == "A h120")
        self.assertLess(abs(a120["valid"]["t"]), ce.T_MIN)           # demeaned: the fade's mean is not a dose slope
        self.assertGreater(a120["valid_rule"]["gross_bp"], 20)
        a60 = next(t for t in res["tests"] if t["trial"] == "A h60")
        self.assertGreater(a60["valid_rule"]["gross_bp"], a60["valid_rule_low_dose"]["gross_bp"])

    def test_rules(self):
        t = pd.DataFrame({"xA": [0.5, -0.5, np.nan], "y60": [0.01, 0.02, 0.03], "xB": [2.0, -1.5, 0.5],
                          "p0801": 100.0, "X60": [101.0, 101.0, 101.0], "xC": [-1.0, 0.2, 3.0], "p0731": 100.0,
                          "p0759": [99.0, 99.0, 102.0]})
        np.testing.assert_allclose(ce.rule_trades(t, "A", 60).g, [0.01])
        np.testing.assert_allclose(ce.rule_trades(t, "B", 60).g, [0.01, -0.01])
        np.testing.assert_allclose(ce.rule_trades(t, "C", None).g, [0.01, 0.02])
        s = ce.rule_stats(np.array([0.01, -0.002]), 1.0)
        self.assertAlmostEqual(s["net1_bp"], 40 - 6)
        self.assertAlmostEqual(s["api_bp"], 40 - 17)


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        d = self.tmp / "BTC" / "flow"
        d.mkdir(parents=True)
        f = flow((E - 40 * DAY, 100, "C", 1.0, 0.0))
        f.to_parquet(d / "2020-11.parquet", index=False)
        pd.concat([f.assign(t=E - 3 * HOUR), f.assign(expiry_ms=E + DAY)]).to_parquet(d / "2021-01.parquet",
                                                                                      index=False)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_reads_every_file_keeps_only_the_expiries_and_checks_hashes(self):
        good = {f"BTC/flow/{p.name}": prereg.sha256_file(p) for p in (self.tmp / "BTC" / "flow").glob("*.parquet")}
        f = ce.load_expiring("BTC", [E], root=self.tmp, hashes=good)
        self.assertEqual(sorted(f.t.tolist()), [E - 40 * DAY, E - 3 * HOUR])   # 2020 rows count toward positions
        with self.assertRaises(prereg.PreregError):
            ce.load_expiring("BTC", [E], root=self.tmp, hashes={**good, "BTC/flow/2020-11.parquet": "0" * 64})


class ClockTest(unittest.TestCase):
    def test_fridays_at_eight(self):
        f = pd.to_datetime(ce.fridays(), unit="ms")
        self.assertTrue((f.dayofweek == 4).all() and (f.hour == 8).all() and (f.minute == 0).all())
        self.assertEqual((f[0], f[-1]), (pd.Timestamp("2021-01-01 08:00"), pd.Timestamp("2026-09-25 08:00")))
        self.assertTrue((np.diff(ce.fridays()) == 7 * DAY).all())


if __name__ == "__main__":
    unittest.main()
