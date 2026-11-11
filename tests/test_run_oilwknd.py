"""scripts/run_oilwknd.py (R459): the oil weekend fade on Lighter, offline, with a stub venue."""
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_oilwknd", ROOT / "scripts" / "run_oilwknd.py")
ow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ow)
MIN, H = ow.MIN, ow.H
W1 = ow.weekend("2026-11-13")
UTC = lambda s: int(pd.Timestamp(s, tz="UTC").value // 10**6)


class Venue:
    """One-minute bars from a price path; like Lighter, a request returns at most the last 500 bars of its range."""

    def __init__(self, paths, fail=False, rate=1e-5, gap=None):
        self.paths, self.fail, self.rate, self.gap = paths, fail, rate, gap

    def minutes(self, sym, start, end):
        if self.fail:
            raise RuntimeError("down")
        t = np.arange(start - start % MIN, end + 1, MIN)
        if self.gap:
            t = t[(t < self.gap[0]) | (t >= self.gap[1])]
        t = t[-500:]
        px = np.array([self.paths[sym](x) for x in t], float)
        return pd.DataFrame({"t": t.astype(np.int64), "open": px, "close": px})

    def funding(self, sym, start, end):
        t = np.arange(start - start % H, end, H)
        return pd.DataFrame({"t": t, "rate": self.rate})


def path(w, move, reanchor, cash):
    """70 before Sunday S - 30 min; 70 (1 + move) to the reopen; then 70 (1 + reanchor); 70 (1 + cash) from C."""
    def f(t):
        if t < w["S"] - 30 * MIN:
            return 70.0
        if t < w["S"]:
            return 70.0 * (1 + move)
        if t < w["C"]:
            return 70.0 * (1 + reanchor)
        return 70.0 * (1 + cash)
    return f


def books(asset, bp, times):
    return pd.DataFrame([{"ts": t, "symbol": asset, "buy_1k_bp": bp, "sell_1k_bp": bp} for t in times])


class Clocks(unittest.TestCase):
    def test_anchors_dst_and_holidays(self):
        self.assertEqual((W1["F"], W1["S"], W1["C"]), (UTC("2026-11-13 22:00"), UTC("2026-11-15 23:00"),
                                                       UTC("2026-11-16 14:30")))
        self.assertEqual(W1["E"], W1["S"] - 5 * MIN)
        self.assertFalse(W1["holiday"])
        self.assertTrue(ow.weekend("2026-12-25")["holiday"])          # Christmas Friday
        self.assertTrue(ow.weekend("2027-01-15")["holiday"])          # Martin Luther King Monday
        self.assertFalse(ow.weekend("2026-11-27")["holiday"])         # day after Thanksgiving: open
        d = ow.weekend("2027-03-12")                                  # clocks change on Sunday 2027-03-14
        self.assertEqual((d["F"], d["S"], d["C"]), (UTC("2027-03-12 22:00"), UTC("2027-03-14 22:00"),
                                                    UTC("2027-03-15 13:30")))
        self.assertEqual(ow.fridays("2026-11-13", W1["C"] + 3 * H - 1), [])
        self.assertEqual([w["friday"] for w in ow.fridays("2026-11-13", W1["C"] + 3 * H)], ["2026-11-13"])


class Score(unittest.TestCase):
    def test_fade_price_funding_cost_and_x60(self):
        v = Venue({"WTI": path(W1, 0.02, 0.01, 0.005)}, rate=1e-5)
        bars = ow.weekend_bars(v, "WTI", W1)
        self.assertTrue((bars.t <= W1["F"]).any() and (bars.t >= W1["C"]).any())   # the 500-bar cap is avoided
        bk = books("WTI", 2.0, [W1["S"] - 20 * MIN, W1["C"] + 40 * MIN])
        r = ow.score_asset("WTI", W1, bars, v.funding("WTI", W1["S"] - 2 * H, W1["C"] + 2 * H), bk)
        self.assertEqual(r["status"], "ok")
        self.assertAlmostEqual(r["w_bp"], 1e4 * np.log(1.02))
        self.assertEqual(r["side"], -1)                                # a rise is faded: short
        self.assertEqual(r["entry_t"], W1["S"] - 4 * MIN)
        self.assertEqual(r["exit_t"], W1["C"])
        self.assertAlmostEqual(r["price"], -(1.005 / 1.02 - 1))
        n_settle = len(range(W1["S"] - 4 * MIN - (W1["S"] - 4 * MIN) % H + H, W1["C"] + 1, H))
        self.assertAlmostEqual(r["funding"], n_settle * 1e-5)          # a short receives positive funding
        self.assertAlmostEqual(r["cost_1x"], 2 * 2e-4)
        self.assertEqual(r["fallback_fills"], 0)
        self.assertAlmostEqual(r["net_3x"], r["gross"] - 3 * r["cost_1x"])
        self.assertAlmostEqual(r["gross_x60"], -(1.01 / 1.02 - 1))
        self.assertAlmostEqual(r["net_x60_1x"], r["gross_x60"] - 2e-4 - 2e-4)
        r = ow.score_asset("WTI", W1, bars, None, books("WTI", 2.0, []))
        self.assertEqual(r["fallback_fills"], 2)
        self.assertAlmostEqual(r["cost_1x"], 2 * 10e-4)

    def test_fall_is_bought_small_move_skipped_and_missing_prices(self):
        v = Venue({"WTI": path(W1, -0.03, -0.01, -0.02), "BRENTOIL": path(W1, 0.005, 0.0, 0.0)})
        r = ow.score_asset("WTI", W1, ow.weekend_bars(v, "WTI", W1), None, None)
        self.assertEqual((r["status"], r["side"]), ("ok", 1))
        self.assertAlmostEqual(r["price"], 0.98 / 0.97 - 1)
        r = ow.score_asset("BRENTOIL", W1, ow.weekend_bars(v, "BRENTOIL", W1), None, None)
        self.assertEqual(r["status"], "no_trade")                      # |W| about 50 bp
        g = Venue({"WTI": path(W1, 0.02, 0.0, 0.0)}, gap=(W1["S"] - 6 * MIN, W1["S"]))
        self.assertEqual(ow.score_asset("WTI", W1, ow.weekend_bars(g, "WTI", W1), None, None)["status"], "unpriced")


class Forward(unittest.TestCase):
    def test_due_retry_once_holiday_and_status(self):
        with tempfile.TemporaryDirectory() as d:
            j = Path(d) / "j"
            paths = {"WTI": path(W1, 0.02, 0.0, 0.0), "BRENTOIL": path(W1, 0.0, 0.0, 0.0)}
            with mock.patch.object(ow, "J", j):
                st = ow.forward(d, now_ms=W1["C"] + 2 * H, venue=Venue(paths))
                self.assertEqual(st["rows"], 0)
                ow.forward(d, now_ms=W1["C"] + 3 * H, venue=Venue(paths, fail=True))
                self.assertFalse((j / "trades.csv").exists())           # fetch failed: retried next run
                st = ow.forward(d, now_ms=W1["C"] + 3 * H, venue=Venue(paths))
                tr = pd.read_csv(j / "trades.csv")
                self.assertEqual(sorted(tr.status), ["no_trade", "ok"])
                ow.forward(d, now_ms=W1["C"] + 3 * H + 1, venue=Venue(paths))
                self.assertEqual(len(pd.read_csv(j / "trades.csv")), 2)  # not scored twice
                self.assertTrue(st["decision"].startswith("pending (1 traded weekends"))
                xmas = ow.weekend("2026-12-25")
                ow.forward(d, now_ms=xmas["C"] + 3 * H, venue=Venue(paths))
                tr = pd.read_csv(j / "trades.csv")
                self.assertEqual(int((tr.status == "holiday").sum()), 2)


class Decision(unittest.TestCase):
    def frame(self, nets):
        rows = []
        for i, x in enumerate(nets):
            f = str((pd.Timestamp("2026-11-13") + pd.Timedelta(weeks=i)).date())
            rows.append({"friday": f, "asset": "WTI", "status": "ok", "net_1x": x, "net_2x": x - 1e-4,
                         "net_3x": x - 2e-4})
        return pd.DataFrame(rows)

    def test_reads(self):
        self.assertTrue(ow.decision(self.frame([1e-3] * 14))["decision"].startswith("pending (14"))
        x = [-1e-3] * 15 + [5e-2] * 30
        self.assertTrue(ow.decision(self.frame(x))["decision"].startswith("NULL (futility"))
        rng = np.random.default_rng(0)
        good = list(5e-3 + rng.normal(0, 5e-3, 40))
        self.assertTrue(ow.decision(self.frame(good))["decision"].startswith("PASS at 40"))
        noisy = [1e-3] * 15 + [4e-2, -4e-2] * 12 + [1e-3]        # mean > 0, far from significant
        self.assertTrue(ow.decision(self.frame(noisy))["decision"].startswith("NULL at 40"))


class Frozen(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "oilwknd_fwd" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        text = re.sub(r"\s+", " ", p.read_text())
        for phrase in ("2026-11-13", "WTI and BRENTOIL", "100 bp", "Friday 17:00", "Sunday 18:00", "Monday 09:30",
                       "S − 4 min", "within 5 minutes", "90 minutes", "10 bp", "3 hours", "15 traded weekends",
                       "40 traded weekends", "p < 0.05", "best 3", "seed 459", "Trials:** 2", "R432"):
            self.assertIn(phrase, text, phrase)
        self.assertEqual((ow.THETA_BP, ow.FUTILITY_N, ow.FINAL_N, ow.SEED, ow.TOP_K), (100.0, 15, 40, 459, 3))


if __name__ == "__main__":
    unittest.main()
