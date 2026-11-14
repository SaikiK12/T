"""scripts/run_litbuyback.py (R486): circular-shift null finds a leading signal and not noise, the share signal, the
7-day target, non-overlapping blocks with a signal and median built from data up to the block start only, the long's
funding sign, cost scaling 20/40/60 bp, the 2026-11-10 sample-end cut, gates and verdict."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_litbuyback as rb  # noqa: E402

DAY = rb.DAY


def series(first, vals):
    return pd.Series(list(vals), index=rb.days(first, rb.day_label(rb.ms(first) + (len(vals) - 1) * DAY)), dtype=float)


def no_funding():
    return pd.DataFrame(columns=["rate", "hours"], dtype=float)


class TestNull(unittest.TestCase):
    def test_leading_signal_found(self):
        rng = np.random.default_rng(1)
        x = rng.normal(size=300)
        y = 0.8 * x + 0.6 * rng.normal(size=300)
        c = rb.circular_null(x, y)
        self.assertGreater(c["rho"], 0.5)
        self.assertLess(c["p_one"], 0.05)
        self.assertLess(c["p_two"], 0.05)
        self.assertEqual(c["shifts"], 300 - 2 * 14 + 1)

    def test_noise_not_found(self):
        rng = np.random.default_rng(2)
        ps = [rb.circular_null(rng.normal(size=300), rng.normal(size=300))["p_two"] for _ in range(20)]
        self.assertGreater(np.median(ps), 0.2)

    def test_spearman_is_rank_based(self):
        x = np.arange(50.0)
        self.assertAlmostEqual(rb.spearman(x, np.exp(x / 5)), 1.0)
        self.assertAlmostEqual(rb.spearman(x, -x ** 3), -1.0)

    def test_paired_series_through_the_pipeline(self):
        """s leads r: a share built from buyback and volume, against the 7-day forward return."""
        n = 200
        rng = np.random.default_rng(3)
        close = series("2026-01-01", 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n))))
        r7 = rb.fwd_return(close, 7)
        s = (r7.fillna(0) + rng.normal(0, 0.01, n)) * 0.01 + 0.01
        x, y, used = rb.paired(s, r7, "2026-01-01", "2026-12-31")
        self.assertEqual(len(x), n - 7)                            # the last 7 days have no target
        self.assertEqual(used[-1], rb.day_label(rb.ms("2026-01-01") + (n - 8) * DAY))
        self.assertLess(rb.circular_null(x, y)["p_one"], 0.05)


class TestSignalTarget(unittest.TestCase):
    def test_share(self):
        bb = series("2026-01-01", [10, 20, 30])
        pq = series("2026-01-02", [100, 300])
        sq = series("2026-01-02", [100, 100])
        s = rb.share(bb, pq, sq)
        self.assertTrue(np.isnan(s["2026-01-01"]))                # no volume that day
        self.assertAlmostEqual(s["2026-01-02"], 20 / 200)
        self.assertAlmostEqual(s["2026-01-03"], 30 / 400)

    def test_fwd_return(self):
        c = series("2026-01-01", np.arange(1.0, 21.0))
        r = rb.fwd_return(c, 7)
        self.assertAlmostEqual(r["2026-01-01"], 8 / 1 - 1)
        self.assertTrue(np.isnan(r["2026-01-14"]))


class TestBook(unittest.TestCase):
    def setUp(self):
        self.close = series("2026-01-01", 100 * 1.001 ** np.arange(200))
        self.s = series("2026-01-01", np.linspace(1, 2, 200))   # rising: sbar above its prior median

    def test_blocks_non_overlapping_and_skipped_without_history(self):
        b = rb.book(self.s, self.close, no_funding(), "2026-01-01", "2026-06-01")
        st = [rb.ms(x) for x in b.start]
        self.assertTrue(all(np.diff(st) == 7 * DAY))
        self.assertTrue(all(rb.ms(e) - rb.ms(s) == 7 * DAY for s, e in zip(b.start, b.end)))
        # sbar needs 7 days and the median 60 prior sbar values: first block at day 66 or later
        self.assertGreaterEqual(rb.ms(b.start.iloc[0]), rb.ms("2026-01-01") + 66 * DAY)
        self.assertTrue(b.long.all())

    def test_median_uses_prior_data_only(self):
        sbar, med = rb.smoothed(self.s, "2026-01-01", "2026-07-01")
        t = "2026-04-01"
        i = rb.days("2026-01-01", "2026-07-01").index(t)
        prior = sbar.iloc[i - 60:i]
        self.assertAlmostEqual(med[t], prior.median())
        self.assertAlmostEqual(sbar[t], self.s.iloc[i - 6:i + 1].mean())
        spiked = self.s.copy()
        nxt = rb.day_label(rb.ms(t) + DAY)
        spiked[nxt] = 1e6                                          # a huge value on t+1
        sbar2, med2 = rb.smoothed(spiked, "2026-01-01", "2026-07-01")
        self.assertEqual(med2[t], med[t])
        self.assertEqual(sbar2[t], sbar[t])
        self.assertNotEqual(sbar2[nxt], sbar[nxt])
        b1 = rb.book(self.s, self.close, no_funding(), "2026-01-01", "2026-06-01")
        b2 = rb.book(spiked, self.close, no_funding(), "2026-01-01", "2026-06-01")
        before = b1.start <= t
        pd.testing.assert_frame_equal(b1[before], b2[before])

    def test_flat_when_below_median(self):
        s = series("2026-01-01", np.linspace(2, 1, 200))           # falling: always below the prior median
        b = rb.book(s, self.close, no_funding(), "2026-01-01", "2026-06-01")
        self.assertFalse(b.long.any())
        self.assertTrue((b.book_1x == 0).all())
        self.assertTrue((b.bench_1x != 0).all())

    def test_funding_sign_for_the_long_and_costs(self):
        days = rb.days("2026-01-01", "2026-07-19")
        fund = pd.DataFrame({"rate": 24 * 0.0001, "hours": 24}, index=days)   # + : longs pay 1 bp an hour
        b = rb.book(self.s, self.close, fund, "2026-01-01", "2026-06-01")
        r = b.iloc[0]
        self.assertAlmostEqual(r.funding_paid, 7 * 24 * 0.0001)
        self.assertEqual(r.funding_hours, 168)
        self.assertAlmostEqual(r.price, 1.001 ** 7 - 1)
        self.assertAlmostEqual(r.gross_long, r.price - r.funding_paid)     # the long pays
        for m, c in ((1, 0.002), (2, 0.004), (3, 0.006)):
            self.assertAlmostEqual(r[f"book_{m}x"], r.price - r.funding_paid - c)
            self.assertAlmostEqual(r[f"bench_{m}x"], r.price - r.funding_paid - c)
        self.assertEqual(rb.COST, {1: 0.002, 2: 0.004, 3: 0.006})
        neg = fund.assign(rate=-24 * 0.0001)                                      # shorts pay: the long receives
        self.assertGreater(rb.book(self.s, self.close, neg, "2026-01-01", "2026-06-01").iloc[0].gross_long, r.price)

    def test_funding_window(self):
        fund = pd.DataFrame({"rate": [1.0, 2.0, 4.0], "hours": [24, 24, 24]},
                            index=["2026-03-01", "2026-03-02", "2026-03-08"])
        self.assertEqual(rb.funding_paid(fund, "2026-03-01"), (6.0, 48))   # day b excluded, b+7 included


class FakeReader:
    def __init__(self, files):
        self.files, self.asked = files, []

    def list(self, folder):
        return sorted(p.split("/")[-1] for p in self.files if p.rsplit("/", 1)[0] == folder)

    def read(self, paths):
        self.asked += paths
        return {p: self.files[p] for p in paths}


def lit_files(last="2026-11-12", bad_row=False):
    files = {}
    for d in rb.days("2026-11-01", last):
        t = rb.ms(d)
        files[f"lit/perp_candles_1d/{d}.csv"] = f"ts,open,high,low,close,volume,quote_volume\n{t},1,1,1,1,1,10\n"
        files[f"lit/spot_candles_1d/{d}.csv"] = f"ts,open,high,low,close,volume,quote_volume\n{t},1,1,1,1,1,5\n"
        rows = "".join(f"{t + h * 3_600_000},0.001,0,long,0.00001\n" for h in range(24))
        files[f"lit/perp_funding/{d}.csv"] = "ts,rate_pct,value,direction,rate\n" + rows
    if bad_row:
        t = rb.ms("2026-11-11")
        files["lit/perp_funding/2026-11-10.csv"] += f"{t},0.001,0,long,0.00001\n"
    return files


class TestSampleEnd(unittest.TestCase):
    def test_files_after_end_never_read(self):
        r = FakeReader(lit_files())
        perp, spot, fund = rb.load_lit(r)
        self.assertEqual(perp.index[-1], "2026-11-10")
        self.assertEqual(spot.index[-1], "2026-11-10")
        self.assertEqual(fund.index[-1], "2026-11-10")
        self.assertFalse([p for p in r.asked if p.endswith(("2026-11-11.csv", "2026-11-12.csv"))])
        self.assertEqual(rb.SAMPLE_END, "2026-11-10")
        self.assertEqual(rb.LAST_T, rb.day_label(rb.ms(rb.SAMPLE_END) - rb.H * DAY))

    def test_row_after_end_refused(self):
        with self.assertRaises(ValueError):
            rb.load_lit(FakeReader(lit_files(bad_row=True)))
        with self.assertRaises(ValueError):
            rb.enforce_cut(pd.DataFrame({"ts": [rb.ms("2026-11-11")]}))
        rb.enforce_cut(pd.DataFrame({"ts": [rb.ms("2026-11-11") - 1]}))

    def test_dated_names(self):
        self.assertEqual(rb.dated_names(["2026-11-11.csv", "2026-11-10.csv", "2026-01-02.csv"]),
                         ["2026-01-02.csv", "2026-11-10.csv"])
        with self.assertRaises(ValueError):
            rb.dated_names(["meta.json"])

    def test_buyback_cut(self):
        path = ROOT / "research" / "intake" / "hlp_llp_lit_20261113" / "em_buyback_usdc_all.json"
        s = rb.load_buyback(path)
        self.assertEqual(s.index[-1], "2026-11-10")
        self.assertEqual(s.index[0], "2025-12-30")


class TestGates(unittest.TestCase):
    def blocks(self, book, bench):
        return pd.DataFrame({"book_1x": book, "book_2x": np.asarray(book) - 0.002, "bench_1x": bench})

    def test_signal_needs_all_three(self):
        corr = {"rho": 0.3, "p_one": 0.01}
        b = self.blocks([0.05, 0.06, 0.04, 0.05, 0.07], [0.0] * 5)
        g, _ = rb.gates(corr, b)
        self.assertTrue(all(g.values()))
        self.assertEqual(rb.verdict(g), "SIGNAL")
        g, _ = rb.gates({"rho": -0.3, "p_one": 0.01}, b)
        self.assertEqual(rb.verdict(g), "NULL")
        g, _ = rb.gates(corr, self.blocks([0.05, 0.06, 0.04, 0.05, 0.07], [0.1] * 5))
        self.assertFalse(g["G3_book_1x_beats_always_long"])
        g, _ = rb.gates(corr, self.blocks([0.05, -0.06, 0.04, -0.05, 0.03], [0.0] * 5))
        self.assertFalse(g["G2_book_2x_mean_gt_0_t_ge_2"])


if __name__ == "__main__":
    unittest.main()
