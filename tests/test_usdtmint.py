"""R460 usdtmint_v1 rule on synthetic bars: timing, fills, funding window, overlap, circle shift, planted drift."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import usdtmint_rule as rule  # noqa: E402

M, H, D = rule.MINUTE_MS, rule.HOUR_MS, rule.DAY_MS


def world(days=400, seed=1, events=150, plant_bp=0.0, hold=24 * H):
    """Random-walk minute opens; `plant_bp` added in a straight ramp over `hold` after each event."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, days * D, M, dtype="int64")
    steps = rng.normal(0, 0.0004, len(t))
    ev = np.sort(rng.choice(np.arange(10 * D, (days - 10) * D, M), size=events, replace=False))
    ev = ev[rule.non_overlapping(ev, hold)]
    if plant_bp:
        per = plant_bp / 1e4 / (hold // M)
        for e in ev:
            i = int(e // M)
            steps[i:i + hold // M] += per
    o = 100 * np.exp(np.cumsum(steps))
    return t, o, ev


class Timing(unittest.TestCase):
    def test_entry_two_minutes_then_next_minute(self):
        self.assertEqual(int(rule.entry_time(1_000)), 3 * M)
        self.assertEqual(int(rule.entry_time(60_000)), 3 * M)
        self.assertEqual(int(rule.entry_time(60_001)), 4 * M)

    def test_price_window_and_missing(self):
        t = np.array([0, M, 7 * M], dtype="int64")
        o = np.array([1.0, 2.0, 3.0])
        p = rule.price_at(t, o, np.array([0, M // 2, 2 * M, 7 * M, 9 * M]))
        self.assertEqual(p[0], 1.0)
        self.assertEqual(p[1], 2.0)          # next bar within 5 minutes
        self.assertTrue(np.isnan(p[2]))     # next bar 5 minutes or more away
        self.assertEqual(p[3], 3.0)
        self.assertTrue(np.isnan(p[4]))

    def test_funding_counts_settlements_after_entry_up_to_exit(self):
        ft = np.array([0, 8 * H, 16 * H, 24 * H], dtype="int64")
        fr = np.array([1e-4, 2e-4, 3e-4, 4e-4])
        self.assertAlmostEqual(float(rule.funding_bp(ft, fr, np.array([0]), 24 * H)[0]), 9.0)
        self.assertAlmostEqual(float(rule.funding_bp(ft, fr, np.array([H]), 4 * H)[0]), 0.0)

    def test_non_overlapping(self):
        e = np.array([0, H, 5 * H, 4 * H], dtype="int64")
        self.assertEqual(rule.non_overlapping(e, 4 * H).tolist(), [0, 3])

    def test_circle_shift_wraps(self):
        s = rule.circle_shift(np.array([90 * M]), 0, 100 * M, 20 * M)
        self.assertEqual(int(s[0]), 10 * M)


class Power(unittest.TestCase):
    def test_planted_drift_is_found(self):
        t, o, ev = world(plant_bp=60.0)
        p, plac, obs = rule.shift_p(t, o, ev, 24 * H, 0, 380 * D, np.random.default_rng(0), draws=300)
        self.assertLess(p, 0.02)
        self.assertGreater(obs - plac, 30)

    def test_no_drift_is_not_found(self):
        ps = []
        for seed in range(6):
            t, o, ev = world(seed=seed + 10)
            ps.append(rule.shift_p(t, o, ev, 24 * H, 0, 380 * D, np.random.default_rng(seed), draws=200)[0])
        self.assertGreater(min(ps), 0.01)
        self.assertGreater(np.median(ps), 0.1)


class Decide(unittest.TestCase):
    def test_holm(self):
        self.assertEqual(rule.holm([0.01, 0.04]).tolist(), [0.02, 0.04])

    def test_verdict(self):
        base = {"n": 100, "p_holm": 0.01, "excess_disc": 5, "excess_val": 5, "excess_hold": 5, "net_1x": 3,
                "net_2x": 1}
        self.assertEqual(rule.verdict([base, dict(base, p_holm=0.5)])[0], "PASS")
        self.assertEqual(rule.verdict([dict(base, excess_hold=-1, net_2x=-1), dict(base, p_holm=0.5)])[0],
                         "PARTIAL")
        self.assertEqual(rule.verdict([dict(base, p_holm=0.2), dict(base, p_holm=0.5)])[0], "NULL")
        self.assertEqual(rule.verdict([dict(base, n=10), dict(base, n=10)])[0], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
