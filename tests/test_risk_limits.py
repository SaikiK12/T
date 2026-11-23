"""R526's risk limits on a synthetic two-venue universe built from hourly bars."""
import math
import unittest

import numpy as np

from lab import xfund as v1
from lab import xfund_v2 as v2
from scripts import run_risk_limits as rl

DAY, H = v1.DAY, v1.H
T0 = 1_600_000_000_000 - 1_600_000_000_000 % DAY
ND = 90


def universe(shift=None, gap_gate=None, scale_gate=1.0, n_coins=2, seed=3):
    """Two venues ("bitfinex" floorless, "gate" pays more funding), hourly bars from one random walk per coin.
    shift = (coin, hour index from T0, factor): multiply gate's closes from that hour on.
    gap_gate = (coin, first hour, last hour): gate prints nothing in those hours."""
    rng = np.random.default_rng(seed)
    hours = ND * 24
    t_open = T0 + H * np.arange(hours, dtype=np.int64) - H         # bar ending at T0 + k H
    series, bars = [], {}
    for c in range(n_coins):
        px = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, hours)))
        row = []
        for name in ("bitfinex", "gate"):
            close = px.copy() * (scale_gate if name == "gate" else 1.0)
            vol = np.ones(hours)
            if name == "gate" and shift and shift[0] == c:
                close[shift[1]:] *= shift[2]
            if name == "gate" and gap_gate and gap_gate[0] == c:
                vol[gap_gate[1]:gap_gate[2] + 1] = 0.0
            cd, fresh = v2.daily_prices(t_open, close, vol, H, T0, ND)
            ft = T0 + 8 * H * np.arange(1, ND * 3, dtype=np.int64)
            rate = np.full(len(ft), 0.0001 if name == "gate" else 0.0)
            f, n = v1.daily_funding(ft, rate, T0, ND)
            row.append(v2.Daily.build(cd, fresh, f, n))
            ok = vol > 0
            bars[(c, name)] = ((t_open + H)[ok], close[ok])
        series.append(row)
    u = v1.Universe([f"C{c}" for c in range(n_coins)], ["bitfinex", "gate"], series, T0, ND, 30, 0.9, 20)
    return u, rl.Hourly(bars)


def replay(u, hourly, **kw):
    bk = rl.Limits([0, 1], 14, 0.05, 20, hourly=hourly, **kw)
    rows, trades = v2.replay(u, bk, v2.window_start(u, [0, 1], 14) + kw.get("delay", 0))
    return rows, trades, bk


class TestLimits(unittest.TestCase):
    def test_no_limits_reproduce_the_engine(self):
        u, hv = universe()
        rows, trades, _ = replay(u, hv)
        r0, t0 = v2.replay(u, v2.Book([0, 1], 14, 0.05, 20), v2.window_start(u, [0, 1], 14))
        self.assertTrue(len(t0) > 0)
        self.assertTrue(rows.equals(r0))

    def test_a_stop_that_never_fires_reproduces_the_engine(self):
        u, hv = universe()
        rows, _, bk = replay(u, hv, stop=1e9)
        r0, _ = v2.replay(u, v2.Book([0, 1], 14, 0.05, 20), v2.window_start(u, [0, 1], 14))
        np.testing.assert_allclose(rows.gross.to_numpy(), r0.gross.to_numpy(), atol=1e-12)
        self.assertEqual(bk.counts["stops"], 0)

    def test_agree_blocks_legs_that_disagree(self):
        u, hv = universe(scale_gate=1.05)
        _, trades, bk = replay(u, hv, agree=0.02)
        self.assertEqual(len(trades), 0)
        self.assertGreater(bk.counts["blocked_agree"], 0)
        _, trades, _ = replay(u, hv, agree=0.10)
        self.assertGreater(len(trades), 0)

    def test_stop_fires_at_the_first_printed_hour_beyond_the_limit(self):
        u, hv = universe()
        _, t0, _ = replay(u, hv)
        first = min(t["entry_day"] for t in t0 if t["coin"] == "C0")
        hour = (first + 2) * 24 + 5                     # 05:00 two days after entry
        u, hv = universe(shift=(0, hour, 1.15))
        rows, trades, bk = replay(u, hv, stop=0.10)
        st = [t for t in trades if t["reason"] == "stop"]
        self.assertEqual(bk.counts["stops"], 1)
        self.assertEqual(st[0]["coin"], "C0")
        self.assertEqual(st[0]["exit_day"], first + 3)
        later = [t for t in trades if t["coin"] == "C0" and t["entry_day"] > first]
        self.assertTrue(all(t["entry_day"] > first + 3 + rl.COOL for t in later))

    def test_stop_waits_for_both_legs_to_print(self):
        u, hv = universe()
        _, t0, _ = replay(u, hv)
        first = min(t["entry_day"] for t in t0 if t["coin"] == "C0")
        hour = (first + 2) * 24 + 5
        u, hv = universe(shift=(0, hour, 1.15), gap_gate=(0, hour - 2, hour + 3))
        _, _, bk = replay(u, hv, stop=0.10)
        p = [x for x in bk.open if x.coin == 0]
        self.assertEqual(bk.counts["stops"], 1)            # fires once gate prints again, at hour + 4
        self.assertFalse(p and p[0].entry_day == first)

    def test_stop_hour_and_price(self):
        u, hv = universe()
        _, t0, _ = replay(u, hv)
        tr = min((t for t in t0 if t["coin"] == "C0"), key=lambda t: t["entry_day"])
        d0, lo, hi = tr["entry_day"], ["bitfinex", "gate"].index(tr["long"]), ["bitfinex", "gate"].index(tr["short"])
        hour = (d0 + 2) * 24 + 5
        for gap, want in ((None, 5), ((0, hour - 2, hour + 3), 9)):
            u, hv = universe(shift=(0, hour, 1.15), gap_gate=gap)
            a, h = u.series[0][lo], u.series[0][hi]
            p = rl.LPos(0, lo, hi, d0, 0.1, pl_e=float(a.val[d0]), ph_e=float(h.val[d0]))
            bk = rl.Limits([0, 1], 14, 0.05, 20, hourly=hv, stop=0.10)
            k, xa, xh = bk._stop_hour(u, p, d0 + 2)
            self.assertEqual(k, want)
            end, close = hv.bars[(0, "gate")]
            at = u.t0 + (d0 + 2) * DAY + k * H
            self.assertAlmostEqual(xh if hi == 1 else xa, float(close[end == at][0]))
            self.assertIsNone(bk._stop_hour(u, p, d0 + 1))

    def test_active_blocks_a_leg_that_did_not_print(self):
        u, hv = universe(n_coins=1)
        _, t0, _ = replay(u, hv)
        first = min(t["entry_day"] for t in t0)
        u, hv = universe(n_coins=1, gap_gate=(0, first * 24 - 10, first * 24 - 1))
        _, trades, bk = replay(u, hv, active=20)
        self.assertGreater(bk.counts["blocked_active"], 0)
        self.assertTrue(all(t["entry_day"] != first for t in trades))

    def test_delay_decides_on_the_previous_day(self):
        u, hv = universe()
        _, t0, _ = replay(u, hv)
        _, t1, _ = replay(u, hv, delay=1)
        self.assertEqual(min(t["entry_day"] for t in t1), min(t["entry_day"] for t in t0) + 1)

    def test_decide(self):
        def leg(a, w):
            return {"ann_pct": a, "worst_day_pct": w}
        rep = {"P12": {"base": {"0": leg(10, -1), "1": leg(-10, -80)}},
               "P4": {"base": {"0": leg(5, -1), "1": leg(-12, -85)}}}
        for k, (kind, _) in rl.VARIANTS.items():
            if k != "base":
                rep["P12" if kind == "all" else "P4"][k] = {"0": leg(9, -1), "1": leg(4, -2)}
        verdict, out = rl.decide(rep)
        self.assertEqual(verdict, "PASS")
        rep["P4"]["all"]["0"] = leg(3, -1)               # keeps 60% of the base at delay 0
        verdict, out = rl.decide(rep)
        self.assertEqual((verdict, out["all"]["verdict"]), ("FAIL", "REJECT"))


if __name__ == "__main__":
    unittest.main()
