"""R367 hftlead_v1: the rule's grid, signal, fills and statistics on hand-made cases, and the runner end to end on a
synthetic recorder directory (a planted lead and a world without one)."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import hftlead_rule as rule  # noqa: E402
import record_hft as rh  # noqa: E402
import run_hftlead as run  # noqa: E402

NAN = math.nan


def arr(n, **at):
    a = np.full(n, NAN)
    for k, v in at.items():
        a[int(k[1:])] = v
    return a


class GridTests(unittest.TestCase):
    def test_to_index_lays_whole_days_end_to_end(self):
        t0 = 1_793_145_600_000                                      # a UTC midnight
        t = np.array([t0, t0 + 100, t0 + 86_400_000 - 100, t0 + 86_400_000, t0 + 86_400_000 + 5_000, t0 - 100])
        self.assertEqual(rule.to_index(t, t0).tolist(), [0, 1, 863_999, 864_000, 864_050, -1])
        with mock.patch.object(rule, "DAY_BUCKETS", 100):
            self.assertEqual(rule.to_index(t, t0).tolist(), [0, 1, -1, 100, 150, -1])

    def test_ffill_mid_carries_a_quote_for_one_second_only(self):
        idx = np.array([2, 20])
        mid, bid, ask = rule.ffill_mid(idx, [10.0, 20.0], [12.0, 22.0], 40)
        self.assertTrue(np.isnan(mid[:2]).all())
        self.assertEqual(mid[2], 11.0)
        self.assertEqual(mid[2 + rule.MAX_AGE], 11.0)
        self.assertTrue(np.isnan(mid[3 + rule.MAX_AGE:20]).all())
        self.assertEqual((bid[20], ask[25]), (20.0, 22.0))

    def test_trade_extremes_leave_empty_buckets_nan(self):
        ls, hb = rule.trade_extremes(np.array([3, 3, 7]), [9.0, 8.0, NAN], [NAN, 11.0, 12.0], 10)
        self.assertEqual((ls[3], hb[7]), (8.0, 12.0))                # the later row of a bucket replaces the earlier
        self.assertEqual(int(np.isfinite(ls).sum()), 1)
        self.assertEqual(int(np.isfinite(hb).sum()), 2)


class SignalTests(unittest.TestCase):
    def test_a_constant_basis_is_removed_and_a_jump_decays_after_the_median_catches_up(self):
        n = 2000
        basis = 3.0                                                  # bp the lead sits above the USDC mid
        usdc = np.full(n, 100.0)
        lead = usdc * np.exp(basis / 1e4)
        lead[1000:] *= np.exp(2.0 / 1e4)                             # the lead jumps 2 bp, USDC has not followed
        x = rule.signal(lead, usdc)
        self.assertAlmostEqual(x[900], 0.0, places=9)
        self.assertAlmostEqual(x[1000], 2.0, places=6)
        self.assertGreater(x[1100], 1.9)
        self.assertAlmostEqual(x[1000 + rule.MED_WIN], 0.0, places=6)     # the median has fully absorbed it

    def test_thresholds_use_only_the_hours_before(self):
        with mock.patch.object(rule, "HOUR_BUCKETS", 100), mock.patch.object(rule, "MIN_HIST", 250):
            x = np.tile(np.concatenate([np.full(50, 1.0), np.full(50, -3.0)]), 10)      # 10 hours, |x| 1 then 3
            x[800:900] = 50.0                                                        # a burst in hour 8
            th = rule.thresholds(x, 95)
            self.assertTrue(np.isnan(th[:300]).all())                                # fewer than 250 points before
            self.assertEqual(th[300], 3.0)                                           # hours 0-2: |x| in {1, 3}
            self.assertEqual(th[800], 3.0)                                           # hour 8 does not see itself
            self.assertGreater(th[900], 40.0)                                        # hour 9 sees the burst
            x2 = x.copy()
            x2[800:900] = -7.0
            self.assertEqual(rule.thresholds(x2, 95)[800], th[800])


class FillTests(unittest.TestCase):
    def world(self, n=60):
        bid, ask = np.full(n, 100.0), np.full(n, 100.1)
        mid = np.full(n, 100.05)
        return bid, ask, mid, np.full(n, NAN), np.full(n, NAN)

    def test_strict_fills_need_a_print_through_the_quote_and_touch_fills_accept_it_at_the_quote(self):
        bid, ask, mid, ls, hb = self.world()
        ls[3] = 100.0                                    # a sell at our bid: touch only
        ls[8] = 99.9                                     # a sell through it: both
        mid[8 + rule.MARK] = 100.2                       # the mid a second after that fill
        out = rule.outcomes(bid, ask, mid, ls, hb, lag=1)
        self.assertEqual((out["bid_strict_j"][0], out["bid_touch_j"][0]), (8, 3))      # live from bucket 2
        self.assertAlmostEqual(out["bid_strict_m"][0], 1e4 * (100.2 - 100.0) / 100.0)
        self.assertAlmostEqual(out["bid_touch_m"][0], 1e4 * (mid[3 + rule.MARK] - 100.0) / 100.0)
        self.assertEqual((out["bid_strict_j"][5], out["bid_touch_j"][5]), (8, 8))
        self.assertEqual((out["bid_strict_j"][20], out["bid_touch_j"][20]), (-1, -1))
        self.assertTrue(np.isnan(out["bid_strict_m"][20]))

    def test_asks_mirror_bids(self):
        bid, ask, mid, ls, hb = self.world()
        hb[10] = 100.1                                   # a buy at our ask: touch
        hb[12] = 100.3                                   # a buy through it: strict
        mid[12 + rule.MARK] = 99.9
        out = rule.outcomes(bid, ask, mid, ls, hb, lag=2)
        self.assertEqual((out["ask_touch_j"][5], out["ask_strict_j"][5]), (10, 12))
        self.assertAlmostEqual(out["ask_strict_m"][5], 1e4 * (100.1 - 99.9) / 100.1)     # short: gains as the mid falls

    def test_the_quote_is_live_from_k_plus_1_plus_lag_for_qlife_buckets(self):
        bid, ask, mid, ls, hb = self.world(80)
        lag = 3
        ls[20] = 99.0
        out = rule.outcomes(bid, ask, mid, ls, hb, lag)
        first_live = lambda k: k + 1 + lag
        last_live = lambda k: k + lag + rule.QLIFE
        self.assertEqual(out["bid_strict_j"][20 - lag - 1], 20)         # bucket 20 is the first live bucket
        self.assertEqual(out["bid_strict_j"][20 - lag], -1)             # one decision later it was before arrival
        self.assertEqual(out["bid_strict_j"][20 - lag - rule.QLIFE], 20)    # the last live bucket
        self.assertEqual(out["bid_strict_j"][20 - lag - rule.QLIFE - 1], -1)    # one more and it had expired
        self.assertEqual((first_live(16), last_live(7)), (20, 20))

    def test_a_stale_mark_drops_the_markout_but_not_the_fill(self):
        bid, ask, mid, ls, hb = self.world()
        ls[8] = 99.9
        mid[8 + rule.MARK] = NAN
        out = rule.outcomes(bid, ask, mid, ls, hb, lag=1)
        self.assertEqual(out["bid_strict_j"][5], 8)
        self.assertTrue(np.isnan(out["bid_strict_m"][5]))

    def test_no_quote_no_fill(self):
        bid, ask, mid, ls, hb = self.world()
        ls[8] = 99.9
        bid[5] = NAN
        out = rule.outcomes(bid, ask, mid, ls, hb, lag=1)
        self.assertEqual(out["bid_strict_j"][5], -1)

    def test_one_quote_at_a_time(self):
        j = np.full(100, -1)
        j[10] = 14                                       # a fill: the next decision waits for 14 + MARK
        cand = np.array([10, 11, 14, 24, 25, 30, 40, 41])
        keep = rule.serialize(cand, j, lag=1)
        # 10 fills at 14 (free after 24); 25 is not filled and expires at 25 + 1 + QLIFE = 36; 40 is free again
        self.assertEqual(cand[keep].tolist(), [10, 25, 40])

    def test_rule_fills_choose_the_side_from_the_sign_and_drop_stale_marks(self):
        n = 36                                           # the ask fills at 28; its markout bucket 38 is off the grid
        bid, ask, mid, ls, hb = np.full(n, 100.0), np.full(n, 100.1), np.full(n, 100.05), arr(n), arr(n)
        ls[8] = 99.9
        hb[28] = 100.3
        mid[8 + rule.MARK] = 100.2
        out = rule.outcomes(bid, ask, mid, ls, hb, lag=1)
        x = np.zeros(n)
        x[5] = 1.0                                       # up: a bid
        x[25] = -1.0                                     # down: an ask
        ks, kf, jf, m = rule.rule_fills(np.array([5, 25]), x, out, 1, "strict")
        self.assertEqual(ks.tolist(), [5, 25])
        self.assertEqual((kf.tolist(), jf.tolist()), ([5], [8]))      # the ask's mark is past the series: stale
        self.assertAlmostEqual(m[0], 20.0)


class StatTests(unittest.TestCase):
    def test_block_stat_matches_the_ratio_estimator(self):
        blocks = np.array([0, 0, 0, 1, 1, 2])
        vals = np.array([1.0, 2.0, 3.0, 5.0, 7.0, 4.0])
        mean, se, t, n, h = rule.block_stat(blocks, vals)
        tot, cnt = np.array([6.0, 12.0, 4.0]), np.array([3.0, 2.0, 1.0])
        mu = tot.sum() / cnt.sum()
        want = math.sqrt(3 / 2 * ((tot - mu * cnt) ** 2).sum()) / cnt.sum()
        self.assertAlmostEqual(mean, 22 / 6)
        self.assertAlmostEqual(se, want)
        self.assertAlmostEqual(t, mean / want)
        self.assertEqual((n, h), (6, 3))
        self.assertTrue(math.isnan(rule.block_stat([0, 0], [1.0, 2.0])[1]))
        self.assertTrue(math.isnan(rule.block_stat([], [])[0]))

    def test_holm(self):
        adj = rule.holm(np.array([0.01, 0.04, 0.03, NAN]))
        self.assertTrue(np.allclose(adj, [0.04, 0.09, 0.09, 1.0]))
        self.assertTrue(np.allclose(rule.holm(np.array([0.5])), [0.5]))

    def test_verdict(self):
        good = {"rule": "a", "n_strict": 400, "mean_strict": 0.5, "mean_touch": 0.2, "p_holm": 0.01}
        weak = dict(good, rule="b", mean_strict=0.15)                    # positive but under two cost units
        thin = dict(good, rule="c", n_strict=10)
        self.assertEqual(rule.verdict([good, weak], 4)[0], "PASS")
        self.assertEqual(rule.verdict([weak, weak], 4)[0], "NULL")
        self.assertEqual(rule.verdict([dict(good, p_holm=0.2), weak], 4)[0], "NULL")
        self.assertEqual(rule.verdict([dict(good, mean_touch=-0.1), weak], 4)[0], "NULL")
        self.assertEqual(rule.verdict([good, thin, thin, thin], 4)[0], "INCONCLUSIVE")
        self.assertEqual(rule.verdict([good], 2)[0], "INCONCLUSIVE")
        self.assertEqual(len(rule.RULES), rule.TRIALS)


# ------------------------------------------------------------------------------------------------- end to end
HOUR, DAY = 100, 2400


def write_world(root, days, lead, seed):
    """Daily recorder files for BTC and ETH on a shrunken grid (DAY buckets a day): the Binance USDT and Bybit mids
    walk; the USDC mid copies the walk `delay` buckets later when `lead`, else walks on its own. Sell and buy prints
    appear at random around the USDC quote, through it half the time."""
    rng = np.random.default_rng(seed)
    for day in days:
        t0 = run.day_ms(day)
        book, trades = [], []
        for coin, px, tick in (("BTC", 80_000.0, 0.1), ("ETH", 2_350.0, 0.01)):
            walk = lambda: px * np.exp(np.cumsum(rng.normal(0, 0.4e-4, DAY)))
            u = walk()
            c = np.roll(u, 3) if lead else walk()
            b = u * np.exp(rng.normal(0, 0.05e-4, DAY))
            k = np.arange(DAY)
            t = t0 + 100 * k
            series = (("binance", coin + "USDT", u), ("binance", coin + "USDC", c), ("bybit", coin + "USDT", b))
            for v, s, mid in series:
                m = np.round(mid / tick) * tick
                book.append(pd.DataFrame({"t": t, "v": v, "s": s, "bid": m - tick / 2, "bq": 1.0, "ask": m + tick / 2,
                                          "aq": 1.0, "n": 1, "lag": 40, "ro": 10}))
            cm = np.round(c / tick) * tick
            through = rng.random(DAY) < 0.5
            sell = rng.random(DAY) < 0.4
            buy = rng.random(DAY) < 0.4
            trades.append(pd.DataFrame({
                "t": t, "v": "binance", "s": coin + "USDC", "nb": buy.astype(int), "qb": buy * 1.0,
                "hb": np.where(buy, cm + tick / 2 + tick * through, NAN), "ns": sell.astype(int), "qs": sell * 1.0,
                "ls": np.where(sell, cm - tick / 2 - tick * through, NAN), "lag": 40}))
        for kind, frames in (("book", book), ("trades", trades)):
            df = pd.concat(frames, ignore_index=True)
            df = df.sort_values(["t", "v", "s"], kind="stable", ignore_index=True)[rh.KINDS[kind][0]]
            (root / kind).mkdir(parents=True, exist_ok=True)
            rh.save(rh.pack(df, kind), root / kind / f"{day}.parquet")


def patched():
    return [mock.patch.object(rule, "DAY_BUCKETS", DAY), mock.patch.object(rule, "HOUR_BUCKETS", HOUR),
            mock.patch.object(rule, "MIN_HIST", 300), mock.patch.object(rule, "MED_WIN", 20),
            mock.patch.object(rule, "MED_MIN", 10), mock.patch.object(rule, "MIN_FILLS", 5),
            mock.patch.object(run, "PLACEBO_SHIFT", (150, 2000)), mock.patch.object(run, "PLACEBOS", 3)]


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for p in patched():
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, lead, days=("2026-10-28", "2026-10-29", "2026-10-30", "2026-10-31", "2026-11-01"), seed=1, **kw):
        data, lane = self.root / "data", self.root / "lane"
        write_world(data, days, lead, seed)
        state = run.run(data=data, lane=lane, check=False, today="2026-11-05", **kw)
        return state, lane / "results"

    def test_finished_days_exclude_today_and_unmerged_days(self):
        data = self.root / "data"
        write_world(data, ["2026-10-29", "2026-10-30"], True, 1)
        (data / "trades" / "2026-10-30.parquet").unlink()
        self.assertEqual(run.finished_days(data, today="2026-11-05"), ["2026-10-29"])
        self.assertEqual(run.finished_days(data, today="2026-10-29"), [])

    def test_a_planted_lead_shows_in_the_gross_diagnostic_and_a_world_without_one_does_not(self):
        state, res = self.go(lead=True)
        self.assertIn(state, {"PASS", "NULL", "INCONCLUSIVE"})
        gross = pd.read_csv(res / "lead_gross.csv")
        self.assertEqual(len(gross), rule.TRIALS)
        fast = gross[gross.rule.str.contains("|L200|", regex=False)]
        slow = gross[gross.rule.str.contains("|L500|", regex=False)]
        self.assertTrue((fast["mean"] > 0).all(), fast[["rule", "mean", "t"]])        # a 300 ms lead, a 200 ms order
        self.assertGreater(fast["t"].min(), 3)
        self.assertLess(slow["t"].abs().max(), 3)                                    # ... and none for a 500 ms order
        state0, res0 = self.go(lead=False, seed=2)
        gross0 = pd.read_csv(res0 / "lead_gross.csv")
        self.assertLess(gross0["t"].abs().max(), 4)

    def test_outputs_and_determinism(self):
        state, res = self.go(lead=True)
        rules = pd.read_csv(res / "rules.csv")
        self.assertEqual(len(rules), rule.TRIALS)
        self.assertEqual(sorted(rules.rule.str.split("|").str[0].unique()), ["BTC", "ETH"])
        self.assertTrue((rules.p_holm >= rules.strict_p - 1e-12).all())
        self.assertTrue(np.allclose(rules.strict_net_2x, rules.strict_mean - 2 * rule.UNIT_COST_BP))
        self.assertTrue((rules.touch_n >= rules.strict_n).all())            # touch fills include strict fills
        self.assertEqual(len(pd.read_csv(res / "controls.csv")), 16)
        self.assertEqual(len(pd.read_csv(res / "placebos.csv")), rule.TRIALS)
        self.assertEqual(len(pd.read_csv(res / "data_files.csv")), 10)       # 5 days of book and trades
        summary = json.loads((res / "summary.json").read_text())
        self.assertEqual(summary["usable_days"], ["2026-10-29", "2026-10-30", "2026-10-31", "2026-11-01"])
        first = (res / "rules.csv").read_bytes()
        run.run(data=self.root / "data", lane=self.root / "lane", check=False, today="2026-11-05")
        self.assertEqual((res / "rules.csv").read_bytes(), first)

    def test_too_few_usable_days_is_inconclusive_and_scores_nothing(self):
        state, res = self.go(lead=True, days=("2026-10-29", "2026-10-30"))
        self.assertEqual(state, "INCONCLUSIVE")
        self.assertFalse((res / "rules.csv").exists())
        self.assertEqual(json.loads((res / "summary.json").read_text())["state"], "INCONCLUSIVE")

    def test_plumbing_computes_no_outcome(self):
        state, res = self.go(lead=True, days=("2026-10-29", "2026-10-30", "2026-10-31"))
        self.assertTrue((res / "rules.csv").exists())                       # three usable days score the rules
        (res / "rules.csv").unlink()
        self.assertEqual(run.run(plumbing=True, data=self.root / "data", lane=self.root / "lane", check=False,
                                 today="2026-11-05"), "PLUMBING")
        self.assertFalse((res / "rules.csv").exists())
        cov = pd.read_csv(res / "coverage.csv")
        self.assertTrue((cov[cov.day >= "2026-10-29"].coverage > 0.9).all())
        self.assertTrue((cov[cov.day == "2026-10-28"].coverage == 0).all())          # the history day has no files

    def test_a_day_with_a_recorder_outage_is_not_usable(self):
        data, lane = self.root / "data", self.root / "lane"
        days = ["2026-10-28", "2026-10-29", "2026-10-30", "2026-10-31", "2026-11-01"]
        write_world(data, days, True, 1)
        p = data / "book" / "2026-10-30.parquet"
        df = pd.read_parquet(p)
        df = df[df.t < run.day_ms("2026-10-30") + 100 * (DAY // 2)]          # the second half of the day is missing
        rh.save(df, p)
        run.run(data=data, lane=lane, check=False, today="2026-11-05")
        cov = pd.read_csv(lane / "results" / "coverage.csv")
        self.assertFalse(cov[cov.day == "2026-10-30"].usable.any())
        self.assertEqual(json.loads((lane / "results" / "summary.json").read_text())["usable_days"],
                         ["2026-10-29", "2026-10-31", "2026-11-01"])


class FrozenInputsTests(unittest.TestCase):
    def test_a_changed_input_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("x = 1\n")
            sha = run.prereg.sha256_file(root / "a.py")
            (root / "PREREG.md").write_text(f"```inputs\n{sha}  a.py\n```\n")
            self.assertEqual(run.frozen_inputs(root / "PREREG.md", root), {"a.py": sha})
            (root / "a.py").write_text("x = 2\n")
            with self.assertRaises(run.prereg.PreregError):
                run.frozen_inputs(root / "PREREG.md", root)


if __name__ == "__main__":
    unittest.main()
