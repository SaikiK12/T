"""scripts/run_levels_v2.py (R333) on invented series: barriers and classes, one open event per coin, dropped paths,
causal features, the walk-forward purge, the policies and the books."""
import unittest

import numpy as np
import pandas as pd

from scripts import run_levels_v2 as lv

H = lv.H


def path(closes):
    lr = np.log(np.asarray(closes, float))
    return lr, np.append(np.exp(np.diff(lr)) - 1, np.nan)


def label(closes, cand, side, horizon=4, delay=0, sig=0.05):
    lr, ret = path(closes)
    return lv._label(np.asarray(cand, np.int64), np.asarray(side, np.int8), lr, ret, np.full(len(lr), sig),
                     horizon, delay), ret


class LabelTest(unittest.TestCase):
    def test_resistance_through_on_the_upper_barrier(self):
        # sigma 0.05 around log(100): the upper barrier is 105.13, first crossed by the close of row 3
        (ent, ext, cls, g, st), ret = label([100, 101, 103, 106, 104, 100], [0], [1])
        self.assertEqual((st[0], ent[0], ext[0], cls[0]), (1, 0, 3, 1))
        self.assertAlmostEqual(g[0], ret[0] + ret[1] + ret[2])

    def test_support_away_on_the_upper_barrier_and_through_on_the_lower(self):
        (_, ext, cls, g, st), ret = label([100, 101, 103, 106, 104, 100], [0], [-1])
        self.assertEqual((st[0], ext[0], cls[0]), (1, 3, -1))
        self.assertAlmostEqual(g[0], -(ret[0] + ret[1] + ret[2]))     # through for support is down
        (_, ext, cls, g, st), ret = label([100, 99, 94, 97, 98, 99], [0], [-1])
        self.assertEqual((ext[0], cls[0]), (2, 1))
        self.assertAlmostEqual(g[0], -(ret[0] + ret[1]))

    def test_resistance_away_and_timeout(self):
        (_, ext, cls, _, _), _ = label([100, 99, 94, 97, 98, 99], [0], [1])
        self.assertEqual((ext[0], cls[0]), (2, -1))
        (_, ext, cls, g, st), ret = label([100, 101, 102, 101, 100, 99], [0], [1])
        self.assertEqual((st[0], ext[0], cls[0]), (1, 4, 0))
        self.assertAlmostEqual(g[0], ret[:4].sum())

    def test_one_open_event_per_coin(self):
        # the event at row 0 exits at row 3, so candidates 2 and 3 are skipped and row 4 starts the next one
        (ent, _, _, _, st), _ = label([100, 101, 103, 106, 104, 100, 101, 102, 103, 104], [0, 2, 3, 4], [1] * 4)
        self.assertEqual(st.tolist(), [1, 0, 0, 1])
        self.assertEqual(ent[3], 4)

    def test_a_missing_close_drops_the_event_and_frees_the_coin(self):
        (_, _, _, _, st), _ = label([100, 101, np.nan, 102, 101, 100, 101, 102, 101], [0, 3], [1, 1])
        self.assertEqual(st.tolist(), [2, 1])

    def test_delay_enters_one_close_later_with_barriers_around_the_entry(self):
        closes = [100, 110, 112, 116, 113, 112, 111]
        (ent, ext, _, _, _), _ = label(closes, [0], [1], delay=0)
        self.assertEqual((ent[0], ext[0]), (0, 1))
        (ent, ext, cls, g, _), ret = label(closes, [0], [1], delay=1)
        self.assertEqual((ent[0], ext[0], cls[0]), (1, 3, 1))           # 110 x e^0.05 = 115.6, crossed at row 3
        self.assertAlmostEqual(g[0], ret[1] + ret[2])

    def test_no_event_without_a_full_horizon(self):
        (_, _, _, _, st), _ = label([100, 101, 102, 101, 100, 99], [0, 2], [1, 1])
        self.assertEqual(st.tolist(), [1, 0])


class LevelTest(unittest.TestCase):
    def test_levels_exclude_the_decision_close(self):
        x = np.array([1.0, 5.0, 2.0, 3.0, 0.5])
        np.testing.assert_array_equal(lv.prev_max(x, 2), [np.nan, np.nan, 5.0, 5.0, 3.0])
        np.testing.assert_array_equal(lv.prev_min(x, 2), [np.nan, np.nan, 1.0, 2.0, 2.0])

    def test_age_and_touches(self):
        lr = np.array([1.0, 1.10, 1.05, 1.10, 1.02, 1.0])
        age, touch = lv._age_touches(lr, np.array([1.10]), np.full(6, 0.3), np.array([5]), 5)
        # the level was last printed at row 3; rows 1 (same price) and 2 (0.05 away) sit within 0.075
        self.assertEqual((age[0], touch[0]), (2.0, 2.0))


def coin(n=900, seed=1):
    rng = np.random.default_rng(seed)
    lr = np.log(100) + np.cumsum(rng.normal(0, 0.01, n))
    qv = rng.uniform(1e6, 2e6, n)
    return {"lr": lr, "qv": qv, "tbq": qv * rng.uniform(0.3, 0.7, n), "fund": rng.normal(0, 1e-4, n),
            "prem": rng.normal(0, 1e-4, n), "elig": np.ones(n, bool), "rank": np.full(n, 10.0),
            "cost": np.full(n, 6e-4), "ret": np.append(np.exp(np.diff(lr)) - 1, np.nan)}


class CausalTest(unittest.TestCase):
    def test_features_at_a_decision_ignore_everything_after_it(self):
        x = coin()
        t = np.arange(len(x["lr"]), dtype=np.int64) * H
        btc = np.log(30000) + np.cumsum(np.random.default_rng(9).normal(0, 0.005, len(t)))
        ev, cand, drop = lv.coin_events(t, x, btc, lv.sigma12(btc), 72, 12, 0)
        self.assertGreater(len(ev), 10)
        self.assertEqual(drop, 0)
        rng = np.random.default_rng(5)
        for i in ev["row"].values[[2, len(ev) // 2, -3]]:
            y = {k: v.copy() for k, v in x.items()}
            for k in ("lr", "qv", "tbq", "fund", "prem"):
                y[k][i + 1:] = y[k][i + 1:] * rng.uniform(0.5, 1.5, len(t) - i - 1)
            y["ret"] = np.append(np.exp(np.diff(y["lr"])) - 1, np.nan)
            b = btc.copy()
            b[i + 1:] += rng.normal(0, 0.05, len(t) - i - 1)
            ev2, _, _ = lv.coin_events(t, y, b, lv.sigma12(b), 72, 12, 0)
            a, z = ev[ev.row == i], ev2[ev2.row == i]
            self.assertEqual(len(z), 1, f"the event at row {i} must survive a change of the future")
            for f in lv.FEATURES:
                np.testing.assert_allclose(a[f].values, z[f].values, equal_nan=True, err_msg=f)

    def test_events_sit_near_a_level_on_their_side(self):
        x = coin(seed=3)
        t = np.arange(len(x["lr"]), dtype=np.int64) * H
        ev, _, _ = lv.coin_events(t, x, x["lr"], lv.sigma12(x["lr"]), 72, 12, 0)
        self.assertTrue((np.abs(ev["dist"]) <= lv.PROX + 1e-12).all())
        self.assertTrue(set(ev["side"].unique()) <= {-1.0, 1.0})
        self.assertTrue((ev["exit"] > ev["row"]).all() and (ev["exit"] - ev["entry"] <= 12).all())
        self.assertTrue((ev["row"].values[1:] > ev["exit"].values[:-1]).all())


class WalkForwardTest(unittest.TestCase):
    def test_purge(self):
        a = 100 * H
        self.assertTrue(lv.train_mask(np.array([a - 25 * H]), a)[0])       # closed 24 h before the block
        self.assertFalse(lv.train_mask(np.array([a - 24 * H]), a)[0])

    def test_blocks_cover_the_archive_by_quarter(self):
        b = lv.blocks(int(pd.Timestamp("2026-09-30 23:00", tz="UTC").timestamp() * 1000))
        self.assertEqual(len(b), 19)
        self.assertEqual(pd.Timestamp(b[0][0], unit="ms", tz="UTC"), pd.Timestamp("2022-01-01", tz="UTC"))
        self.assertEqual(pd.Timestamp(b[-1][0], unit="ms", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC"))

    def test_predictions_only_inside_test_blocks_and_from_earlier_events(self):
        rng = np.random.default_rng(0)
        n = 6000
        t = np.sort(rng.integers(pd.Timestamp("2021-07-01", tz="UTC").value // 10**6,
                                 pd.Timestamp("2022-07-01", tz="UTC").value // 10**6, n))
        ev = pd.DataFrame({f: rng.normal(size=n) for f in lv.FEATURES})
        ev["t"] = t
        ev["exit_t"] = t + 6 * H
        ev["cls"] = np.where(ev["dist"] > 0, 1, -1)
        ev["sig"] = 0.03
        ev["g"] = ev["cls"] * 0.03
        bl = lv.blocks(int(pd.Timestamp("2022-06-30", tz="UTC").value // 10**6))
        self.assertEqual(len(bl), 2)
        P, C, E, EC, Q90, fits = lv.fit_predict(ev, bl, dict(lv.HGB, max_iter=20, min_samples_leaf=20))
        inside = t >= bl[0][0]
        self.assertTrue(np.isfinite(E[inside]).all() and np.isnan(E[~inside]).all())
        self.assertEqual([f["train"] for f in fits], [int(lv.train_mask(ev["exit_t"].values, a).sum()) for a, _ in bl])
        d = ev["dist"].values                       # it learns the planted rule (20 small steps: not converged)
        self.assertGreater(P[inside & (d > 0.5), 0].mean(), 0.75)
        self.assertLess(P[inside & (d < -0.5), 0].mean(), 0.25)
        np.testing.assert_allclose(P[inside].sum(1), 1)


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.ev = pd.DataFrame({"sig": [0.02] * 3, "cost": [0.001] * 3, "g": [0.01, -0.02, 0.005],
                                "t": [0, DAYMS, 2 * DAYMS]})

    def test_rules(self):
        E = np.array([0.3, -0.5, np.nan])
        np.testing.assert_array_equal(lv.decide(self.ev, E, "P1"), [1, -1, 0])     # |edge| 0.006, 0.010 > 0.004
        np.testing.assert_array_equal(lv.decide(self.ev, E, "P2"), [0, -1, 0])     # needs > 0.009
        np.testing.assert_array_equal(lv.decide(self.ev, E, "P3", np.full(3, 0.4)), [0, -1, 0])

    def test_zero_fee_policy_and_measures(self):
        E = np.array([0.03, -0.5, np.nan])                          # |edge| 0.0006 > 4 x 1 bp
        np.testing.assert_array_equal(lv.decide(self.ev, E, "P0"), [1, -1, 0])
        net, _ = lv.book(self.ev, np.array([1, -1, 0]), 1, lv.ZERO_FEE)
        np.testing.assert_allclose(net, [0.01 - 2e-4, 0.02 - 2e-4])
        m = lv.measures(self.ev, np.array([1, -1, 0]), 0, 3)
        self.assertEqual((m["gross"]["bp_per_trade"], m["zero_fee"]["bp_per_trade"]), (150.0, 148.0))
        self.assertEqual(m["break_even_bp_one_way"], 75.0)          # a 150 bp gross trade pays 75 bp a side

    def test_book_charges_both_sides_at_the_multiple(self):
        net, day = lv.book(self.ev, np.array([1, -1, 0]), 2)
        np.testing.assert_allclose(net, [0.01 - 0.004, 0.02 - 0.004])
        np.testing.assert_array_equal(day, [0, 1])
        s = lv.summarize(net, day, 0, 3)
        self.assertEqual((s["trades"], s["days"], s["bp_per_trade"], s["hit"]), (2, 2, 110.0, 1.0))


DAYMS = lv.DAY


class IdentityTest(unittest.TestCase):
    def test_digest_and_its_frozen_line(self):
        D = {"syms": ["A"], "t": np.arange(3, dtype=np.int64)}
        D.update({k: np.zeros((3, 1)) for k in lv.FIELDS})
        d = lv.digest(D)
        D["ret"][1, 0] = 1e-9
        self.assertNotEqual(d, lv.digest(D))
        self.assertEqual(lv.frozen_digest(f"- **Data digest:** `{d}` (plumbing)"), d)


if __name__ == "__main__":
    unittest.main()
