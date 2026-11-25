"""Tests for scripts/run_xyzbal_fwd.py (R530): sides, the balanced weekend net, costs, the decision, the frozen text."""
import re
import sys
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_xyzbal_fwd as bal  # noqa: E402
import xyzwknd_rule as rule  # noqa: E402

W = dict(rule.weekend(date(2026, 12, 4)), friday="2026-12-04")
U = {"coin": "X", "growth": "enabled", "fee_scale": "1.0", "ipo_424b4": ""}


def priced(coin, w_bp, move_bp, funding_raw=0.0):
    """A market row as market_row makes it: raw fade side s = -sign(W); c, f, g are the raw side's returns."""
    s = -1 if w_bp > 0 else 1
    return {"friday": "2026-12-04", "coin": coin, "status": "priced", "w_bp": w_bp, "raw_side": s,
            "c_x1": s * move_bp, "f_x1": funding_raw, "g_x1": s * move_bp + funding_raw}


class Rule(unittest.TestCase):
    def test_market_row_from_candles(self):
        hrs = np.arange(W["R"] - 10 * bal.base.DAY, W["X1"] + rule.HOUR_MS, rule.HOUR_MS)
        close = np.full(len(hrs), 100.0)
        close[hrs >= W["E"] - 2 * rule.HOUR_MS] = 101.0            # +~100 bp by E
        close[hrs >= W["X1"] - 2 * rule.HOUR_MS] = 100.5           # gives back half by X1
        k = pd.DataFrame({"t": hrs, "c": close})
        f = pd.DataFrame(columns=["time", "rate"]).astype({"time": "int64", "rate": float})
        r = bal.market_row(U, W, k, f)
        self.assertEqual(r["status"], "priced")
        self.assertAlmostEqual(r["w_bp"], 1e4 * np.log(1.01), 6)
        self.assertEqual(r["raw_side"], -1)
        self.assertGreater(r["g_x1"], 0)

    def test_market_row_not_listed(self):
        k = pd.DataFrame({"t": [W["R"] - 2 * bal.base.DAY], "c": [1.0]})
        f = pd.DataFrame(columns=["time", "rate"])
        self.assertEqual(bal.market_row(U, W, k, f)["status"], "not_listed")

    def test_sides_are_relative_to_the_median(self):
        rows = [priced(c, w, 0.0) for c, w in zip("ABCDEF", (200, 150, 100, 100, 40, -20))]
        med = bal.assign_sides(rows)
        self.assertEqual(med, 100.0)
        self.assertEqual([r["side"] for r in rows], [-1, -1, 0, 0, 1, 1])

    def test_too_few_markets(self):
        rows = [priced(c, w, 0.0) for c, w in zip("ABCD", (200, 150, -100, -120))]
        trades, wk = bal.weekend_rows(rows, W, None, None, None, {c: U for c in "ABCD"})
        self.assertEqual(wk["status"], "too_few_markets")
        self.assertEqual(trades, [])

    def test_balanced_net_cancels_the_common_move_and_charges_costs(self):
        # Relative movers: +-100 bp; every market moves +40 bp after E (common), relative risers give back 20,
        # relative fallers recover 20. Long side earns 60, short side earns -20: gross 20.
        w = (100, 120, 0, 0, -100, -120)
        mv = (20, 20, 40, 40, 60, 60)
        rows = [priced(c, a, b) for c, a, b in zip("ABCDEF", w, mv)]
        trades, wk = bal.weekend_rows(rows, W, None, None, None, {c: U for c in "ABCDEF"})
        self.assertEqual(wk["status"], "ok")
        self.assertEqual((wk["n_long"], wk["n_short"]), (2, 2))
        self.assertAlmostEqual(wk["gross_bp"], 20.0, 9)
        # no books: 10 bp fallback per fill (2 fills) + growth fee 2 x 0.9 bp = 21.8 bp per trade
        self.assertAlmostEqual(wk["cost_bp"], 21.8, 6)
        self.assertAlmostEqual(wk["net_1x"], 20.0 - 21.8, 6)
        self.assertAlmostEqual(wk["net_2x"], 20.0 - 43.6, 6)
        self.assertIsNone(wk["net5k_1x"])
        self.assertEqual(sum(t["fallback_fills"] for t in trades), 8)
        self.assertAlmostEqual(wk["common_move_bp"], 40.0, 9)

    def test_one_sided_weekend_does_not_trade(self):
        rows = [priced(c, w, 0.0) for c, w in zip("ABCDEF", (300, 0, 0, 0, 0, 0))]
        _, wk = bal.weekend_rows(rows, W, None, None, None, {c: U for c in "ABCDEF"})
        self.assertEqual(wk["status"], "one_sided")


class Decide(unittest.TestCase):
    def frame(self, v):
        fr = pd.date_range("2026-12-04", periods=len(v), freq="7D").strftime("%Y-%m-%d")
        return pd.DataFrame({"friday": fr, "status": "ok", "net_1x": v, "net_2x": np.asarray(v) - 10})

    def test_futility(self):
        self.assertEqual(bal.decision(self.frame([-1.0] * 15))["state"], "NULL")

    def test_pending_before_a_look(self):
        self.assertEqual(bal.decision(self.frame([30.0] * 19))["state"], "PENDING")

    def test_pass_at_20(self):
        v = [30.0] * 17 + [12.0, 14.0, 16.0]
        st = bal.decision(self.frame(v))
        self.assertEqual(st["state"], "PASS")
        self.assertIn("20", st["reason"])

    def test_no_pass_by_30_is_null(self):
        v = [40.0, -38.0] * 15
        self.assertEqual(bal.decision(self.frame(v))["state"], "NULL")


class Frozen(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "xyzbal_fwd" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        text = re.sub(r"\s+", " ", p.read_text())
        for phrase in ("2026-12-04", "50 bp", "Sunday 19:00", "Sunday 22:00", "Friday 20:00", "$1k", "90 minutes",
                       "10 bp", "at least 5", "15 traded weekends", "20 traded weekends", "30 traded weekends",
                       "p < 0.01", "p < 0.04", "best 3", "seed 530", "Trials:** 1", "R462", "7 days",
                       "equal notional"):
            self.assertIn(phrase, text, phrase)
        self.assertEqual((bal.THETA_BP, bal.MIN_MARKETS, bal.FUTILITY_N, bal.INTERIM_N, bal.FINAL_N, bal.SEED,
                          bal.TOP_K), (50.0, 5, 15, 20, 30, 530, 3))
        self.assertEqual((bal.ALPHA_INTERIM, bal.ALPHA_FINAL, bal.FIRST_FRIDAY), (0.01, 0.04, date(2026, 12, 4)))


if __name__ == "__main__":
    unittest.main()
