import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cmelead_rule as r  # noqa: E402

US = r.US
T = 1_800_000_000 * US


def lead_world(jump_bp=30.0, jump_at=0.2, revert_at=None, base=100.0):
    """One CME trade a second from T-310 s to T+90 s; the price jumps at T+jump_at (and falls back at revert_at)."""
    ts = np.arange(-310, 91) * US + int(0.05 * US)
    ts = np.sort(np.concatenate([ts, [int(jump_at * US)]]))
    price = np.full(len(ts), base)
    price[ts >= T * 0 + int(jump_at * US)] = base * math.exp(jump_bp / 1e4)
    if revert_at is not None:
        price[ts >= int(revert_at * US)] = base
    return {"t": ts + T, "price": price}


def fol_world(jump_at=3.0, jump_bp=30.0, base=100.0, every=0.2, only_side=None):
    """Binance prints every `every` s with alternating taker side; the price jumps at T+jump_at."""
    ts = np.arange(int(-310 / every), int(90 / every) + 1) * int(every * US)
    price = np.where(ts >= int(jump_at * US), base * math.exp(jump_bp / 1e4), base)
    bm = (np.arange(len(ts)) % 2).astype(bool)
    if only_side == "buy":
        bm = np.zeros(len(ts), dtype=bool)
    if only_side == "sell":
        bm = np.ones(len(ts), dtype=bool)
    return {"t": ts + T, "price": price, "buyer_maker": bm}


class RuleTests(unittest.TestCase):
    def test_a_lagging_follower_is_caught(self):
        out = r.evaluate(lead_world(), fol_world(jump_at=3.0), T, "ngs", 1.0)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["s"], 1)
        self.assertAlmostEqual(out["t_star_s"], 0.2, places=3)
        self.assertAlmostEqual(out["D"], 30.0, places=1)
        self.assertAlmostEqual(out["c"], 0.0, places=6)
        self.assertTrue(out["lag_ok"])
        self.assertAlmostEqual(out["entry"], 100.0)
        self.assertAlmostEqual(out["gross"], 30.0, places=1)

    def test_a_follower_that_already_moved_is_filtered(self):
        out = r.evaluate(lead_world(), fol_world(jump_at=0.3), T, "ngs", 1.0)
        self.assertEqual(out["status"], "ok")
        self.assertGreater(out["c"], 0.9)
        self.assertFalse(out["lag_ok"])
        self.assertAlmostEqual(out["gross"], 0.0, places=6)

    def test_down_jump_sells_and_gains(self):
        out = r.evaluate(lead_world(jump_bp=-30.0), fol_world(jump_at=3.0, jump_bp=-30.0), T, "ngs", 1.0)
        self.assertEqual((out["status"], out["s"]), ("ok", -1))
        self.assertAlmostEqual(out["gross"], 30.0, places=1)

    def test_threshold_decides_the_event_type(self):
        lead, fol = lead_world(jump_bp=12.0), fol_world(jump_at=3.0, jump_bp=12.0)
        self.assertEqual(r.evaluate(lead, fol, T, "ngs", 1.0)["status"], "no_cross")
        self.assertEqual(r.evaluate(lead, fol, T, "wpsr", 1.0)["status"], "ok")

    def test_a_move_that_reverts_before_the_decision_is_skipped(self):
        out = r.evaluate(lead_world(revert_at=0.7), fol_world(), T, "ngs", 1.0)
        self.assertEqual(out["status"], "reverted")
        self.assertEqual(r.evaluate(lead_world(revert_at=0.7), fol_world(), T, "ngs", 0.4)["status"], "ok")

    def test_entry_must_be_a_taker_print_on_the_right_side_within_the_wait(self):
        out = r.evaluate(lead_world(), fol_world(only_side="sell"), T, "ngs", 1.0)
        self.assertEqual(out["status"], "no_fill")
        out = r.evaluate(lead_world(), fol_world(every=3.0), T, "ngs", 1.0)
        self.assertEqual(out["status"], "no_fill")

    def test_exit_needs_a_fresh_opposite_print(self):
        out = r.evaluate(lead_world(), fol_world(every=0.2, only_side="buy"), T, "ngs", 1.0)
        self.assertEqual(out["status"], "no_exit")

    def test_exit_never_precedes_entry(self):
        lead = lead_world(jump_at=59.5)
        out = r.evaluate(lead, fol_world(jump_at=90.0), T, "ngs", 5.0)
        self.assertEqual(out["status"], "no_exit")

    def test_missing_reference_makes_the_event_invalid(self):
        lead = lead_world()
        keep = lead["t"] >= T - 5 * US
        thin = {"t": lead["t"][keep], "price": lead["price"][keep]}
        self.assertEqual(r.evaluate(thin, fol_world(), T, "ngs", 1.0)["status"], "no_ref")
        empty = {"t": np.array([], dtype=np.int64), "price": np.array([])}
        self.assertTrue(math.isnan(r.reference(empty, T)))

    def test_old_trades_do_not_count_as_a_reference(self):
        lead = lead_world()
        keep = lead["t"] < T - 400 * US
        self.assertEqual(keep.sum(), 0)
        old = {"t": np.array([T - 500 * US]), "price": np.array([100.0])}
        self.assertTrue(math.isnan(r.reference(old, T)))

    def test_the_decision_sees_nothing_after_it(self):
        base = r.evaluate(lead_world(), fol_world(jump_at=3.0), T, "ngs", 1.0)
        lead, fol = lead_world(), fol_world(jump_at=3.0)
        late = lead["t"] > T + int(1.3 * US)
        lead["price"][late] = 50.0
        again = r.evaluate(lead, fol, T, "ngs", 1.0)
        self.assertEqual((again["D"], again["c"], again["entry"]), (base["D"], base["c"], base["entry"]))

    def test_net_and_cost_units(self):
        self.assertEqual(r.net(30.0, 1), 20.0)
        self.assertEqual(r.net(30.0, 2), 10.0)
        self.assertEqual(r.net(30.0, 3), 0.0)

    def test_sign_flip_and_holm(self):
        rng = np.random.default_rng(0)
        self.assertAlmostEqual(r.sign_flip_p([2, 1, -1], rng), 3 / 8)
        self.assertAlmostEqual(r.sign_flip_p([5.0] * 6, rng), 1 / 64)
        self.assertTrue(math.isnan(r.sign_flip_p([], rng)))
        self.assertTrue(np.allclose(r.holm([0.01, 0.04]), [0.02, 0.04]))

    def test_verdict_levels(self):
        unit = 2 * r.FEE_SIDE_BP
        cell = lambda mean, p, n=8, valid=20: {"n": n, "valid": valid, "mean": mean, "p_holm": p}  # noqa: E731
        self.assertEqual(r.verdict([cell(2.5 * unit, 0.01)])[0], "PASS")
        self.assertEqual(r.verdict([cell(1.5 * unit, 0.01)])[0], "PARTIAL")
        self.assertEqual(r.verdict([cell(3 * unit, 0.20)])[0], "NULL")
        self.assertEqual(r.verdict([cell(3 * unit, 0.01, n=5)])[0], "INCONCLUSIVE")
        self.assertEqual(r.verdict([cell(3 * unit, 0.01, valid=9)])[0], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
