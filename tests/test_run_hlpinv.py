"""scripts/run_hlpinv.py (R454): HLP snapshot pairing, bins, slice rows, book arithmetic and the decision, offline."""
import importlib.util
import re
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_hlpinv", ROOT / "scripts" / "run_hlpinv.py")
hp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hp)
H = hp.H
T0 = hp.fh.ms("2026-11-12")


def frames(run_ms, coins, shares, vlm=50e6, oi=1e6, mark=10.0, pos_lag_ms=3_000):
    ctx = pd.DataFrame({"ts": run_ms, "coin": coins, "mark": mark, "oracle": mark, "mid": mark, "funding": 1e-5,
                        "premium": 0.0, "open_interest": oi, "day_ntl_vlm": vlm})
    # HLP's net size split over two child vaults
    pos = pd.DataFrame({"ts": run_ms + pos_lag_ms, "vault": "0xa", "coin": coins, "szi": [s * oi / 2 for s in shares],
                        "entry_px": mark, "position_value": 0, "unrealized_pnl": 0, "margin_used": 0})
    pos2 = pos.assign(vault="0xb", ts=run_ms + pos_lag_ms + 500)
    return pd.concat([pos, pos2], ignore_index=True), ctx


class Snapshots(unittest.TestCase):
    def test_pairs_runs_shares_and_eligibility(self):
        coins = [f"C{i:02d}" for i in range(20)]
        shares = np.linspace(-0.3, 0.3, 20)
        p1, c1 = frames(T0 + 7 * 60_000, coins, shares)
        p2, c2 = frames(T0 + H + 9 * 60_000, coins, shares[::-1], vlm=[5e6] + [50e6] * 19)
        c3 = c2.assign(ts=T0 + 2 * H + 7 * 60_000)            # a context with no positions: dropped
        late = p1.assign(ts=T0 + 7 * 60_000 + 11 * 60_000)    # positions 11 minutes after a context: not paired
        tab = hp.snapshots(pd.concat([p1, p2, late]), pd.concat([c1, c2, c3]))
        self.assertEqual(sorted(tab.run.unique()), [T0 + 7 * 60_000, T0 + H + 9 * 60_000])
        a = tab[tab.run == T0 + 7 * 60_000].set_index("coin")
        self.assertAlmostEqual(a.loc["C00", "share"], -0.3)
        self.assertEqual(int(a.snap.iloc[0]), T0 + 7 * 60_000 + 3_500)
        b = tab[tab.run == T0 + H + 9 * 60_000].set_index("coin")
        self.assertFalse(b.loc["C00", "elig"])                # $5M volume
        self.assertTrue(b.loc["C01", "elig"])

    def test_coin_without_position_is_zero_and_small_oi_is_out(self):
        coins = ["A", "B"]
        p, c = frames(T0, coins, [0.1, 0.1])
        c.loc[c.coin == "B", "open_interest"] = 100.0         # $1k of open interest
        tab = hp.snapshots(p[p.coin == "A"], c).set_index("coin")
        self.assertTrue(tab.loc["A", "elig"])
        self.assertEqual(tab.loc["B", "net_szi"], 0.0)
        self.assertFalse(tab.loc["B", "elig"])


class Bins(unittest.TestCase):
    def test_eighths_with_sign(self):
        coins = [f"C{i:02d}" for i in range(20)]
        shares = [-0.5, -0.4, -0.3] + [0.0] * 15 + [0.2, 0.6]
        p, c = frames(T0, coins, shares)
        k, lo, hi = hp.bins(hp.snapshots(p, c))[T0]
        self.assertEqual(k, 3)                                # ceil(20 / 8)
        self.assertEqual(lo, ["C00", "C01", "C02"])
        self.assertEqual(hi, ["C19", "C18"])                  # only two coins with share > 0

    def test_too_few_coins(self):
        p, c = frames(T0, [f"C{i}" for i in range(10)], np.linspace(-1, 1, 10) / 10)
        self.assertEqual(hp.bins(hp.snapshots(p, c)), {})


class Rows(unittest.TestCase):
    def test_first_run_of_each_hour_and_entry_row(self):
        coins = [f"C{i:02d}" for i in range(16)]
        sh = np.linspace(-0.2, 0.2, 16)
        # snapshots land 3.5 s after each context; entry at the first close at least 5 minutes later
        parts = [frames(T0 - 2 * H, coins, sh), frames(T0 + 7 * 60_000, coins, sh),
                 frames(T0 + 40 * 60_000, coins, sh), frames(T0 + 2 * H + 50 * 60_000, coins, sh),
                 frames(T0 + 3 * H + 30 * 60_000, coins, sh)]
        tab = hp.snapshots(pd.concat([x[0] for x in parts]), pd.concat([x[1] for x in parts]))
        self.assertEqual(hp.slice_rows(tab, T0), {0: T0 + 7 * 60_000, 2: T0 + 2 * H + 50 * 60_000,
                                                  3: T0 + 3 * H + 30 * 60_000})
        late = hp.snapshots(*frames(T0 + 55 * 60_000, coins, sh))   # 00:55 + 5 min passes 01:00: enters at 02:00
        self.assertEqual(hp.slice_rows(late, T0), {1: T0 + 55 * 60_000})


class Book(unittest.TestCase):
    def test_short_slice_earns_minus_return_and_hedge_the_basket(self):
        coins = [f"C{i:02d}" for i in range(16)]
        sh = [-0.5, -0.4] + [0.01] * 13 + [0.5]
        p, c = frames(T0 + 7 * 60_000, coins, sh)
        tab = hp.snapshots(p, c)
        T = 48
        close = np.ones((T + 1, 16))
        ind, basket, opened = hp.build(tab, coins, T0, T, close)
        self.assertTrue(opened[0] and not opened[1:].any())
        self.assertAlmostEqual(ind["F"][0].sum(), 1.0)       # two coins at 1/k, k = 2
        self.assertEqual(list(np.flatnonzero(ind["R"][0])), [2, 15])   # 0.5, then the 0.01 tie broken by name
        self.assertTrue(basket[1:].all())                     # eligibility carried forward
        ret = np.zeros((T, 16))
        ret[5, 0] = 0.01                                      # the shorted coin rises 1% on row 5
        r = hp.book_days(ind["F"], ret, basket, 2, cost=0.0)
        expect = -0.01 * 0.5 / hp.HOLD + (1.0 / hp.HOLD) * 0.01 / 16
        self.assertAlmostEqual(r["net"][0], expect)
        self.assertAlmostEqual(r["net"][1], 0.0)
        c1 = hp.book_days(ind["F"], np.zeros((T, 16)), basket, 2, cost=9e-4)
        self.assertAlmostEqual(c1["cost"][0], 2 * 9e-4 / hp.HOLD)   # short leg and hedge each traded 1/HOLD

    def test_placebo_is_seeded_and_picks_the_bin_size(self):
        rng = np.random.default_rng(1)
        T, S, D = 96, 20, 4
        ind = np.zeros((T, S))
        ind[::3, :3] = 1 / 3
        basket = np.ones((T, S), bool)
        ret = rng.normal(0, 0.01, (T, S))
        a = hp.placebo_means(ind, ret, basket, D, np.arange(D), n_placebo=5, seed=7)
        b = hp.placebo_means(ind, ret, basket, D, np.arange(D), n_placebo=5, seed=7)
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(len(a), 5)


class Decision(unittest.TestCase):
    def tickets(self, n, mean):
        days = pd.date_range("2026-11-15", periods=n, freq="D").strftime("%Y-%m-%d")
        x = mean + np.random.default_rng(0).normal(0, 1e-4, n)
        return pd.DataFrame({"day": days, "book": "F", "net": x, "net_2x": x - 1e-5, "net_3x": x - 2e-5,
                             "kind": "counted"})

    def test_looks(self):
        empty = pd.DataFrame(columns=["day", "book", "coin", "gross"])
        self.assertTrue(hp.read_decision(self.tickets(30, 1e-3), empty, "F")["decision"].startswith("pending"))
        self.assertTrue(hp.read_decision(self.tickets(90, 1e-3), empty, "F")["decision"].startswith("SURVIVES"))
        self.assertTrue(hp.read_decision(self.tickets(90, -1e-3), empty, "F")["decision"].startswith("NULL"))
        s = hp.read_decision(self.tickets(365, 1e-3), empty, "F", lambda n: 5e-4)
        self.assertTrue(s["decision"].startswith("PASS"))
        s = hp.read_decision(self.tickets(365, 1e-3), empty, "F", lambda n: 2e-3)
        self.assertTrue(s["decision"].startswith("NULL"))

    def test_day_kind(self):
        self.assertEqual(hp.day_kind("2026-11-14", 24), "ramp")
        self.assertEqual(hp.day_kind("2026-11-15", 20), "counted")
        self.assertEqual(hp.day_kind("2026-11-15", 19), "thin")


class Frozen(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "hlpinv_v1" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        text = re.sub(r"\s+", " ", p.read_text())
        for phrase in (f"from {hp.FWD_START}", f"counted from {hp.COUNT_START}", f"{hp.HOLD} hours",
                       "one eighth", f"at least {hp.MIN_ELIG} eligible coins", "$10M", "$2M",
                       f"{hp.MATCH_MIN} minutes", f"at least {hp.ENTRY_GAP_MIN} minutes after",
                       f"at least {hp.MIN_HOURS} of its 24 hours", "9 bp",
                       f"{hp.SCREEN_DAYS} counted days", f"{hp.FINAL_DAYS} counted days", "one-sided 2.5%",
                       f"{hp.N_PLACEBO:,} placebo books", f"seed {hp.SEED}", "50%"):
            self.assertIn(phrase, text, phrase)


if __name__ == "__main__":
    unittest.main()
