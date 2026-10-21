import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import forward_xbook as xb

MS_DAY = 86_400_000


def ms(day, hour=0):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6) + hour * 3_600_000


def write(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(p, index=False)


def build(root, days, carry=1e-3, flow=2e-2, replay_value=9.0, noise=0.0):
    """Synthetic journals: every carry and flow sleeve has one live row per day, plus a replay row that must be
    ignored. With noise, each row's net gets that much Gaussian noise times its mean."""
    rng = np.random.default_rng(7)
    jit = lambda m: m * (1 + noise * rng.normal())
    for lane, books in (("xfund_fwd", "AB"), ("xfund_kc_fwd", "AB")):
        rows = [{"day": "2026-10-01", "book": b, "kind": "replay", "net": replay_value, "net_2x": replay_value}
                for b in books]
        rows += [{"day": d, "book": b, "kind": "ontime" if i % 2 else "late", "net": jit(carry), "net_2x": carry / 2}
                 for i, d in enumerate(days) for b in books]
        write(root / lane / "journal" / "days.csv", rows)
    for lane, books in (("mexc_fwd", ["A", "B"]), ("mexc_fwd_sq", ["X2"])):
        rows = [{"day": d, "book": b, "kind": "ontime", "net": jit(flow), "net_2x": flow / 2} for d in days for b in books]
        write(root / lane / "journal" / "tickets.csv", rows)


class XbookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.days = [d.strftime("%Y-%m-%d") for d in pd.date_range(xb.START, periods=20)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_families_drop_replay_and_book_is_risk_balanced(self):
        build(self.root, self.days)
        b = xb.book_days(self.root, "2026-11-30")
        live = b.loc[self.days]
        self.assertTrue(np.allclose(live.carry, 1e-3))                  # the replay row's 9.0 never enters
        self.assertTrue(np.allclose(live.flow, 2e-2))
        self.assertTrue((live.n_carry == 4).all() and (live.n_flow == 3).all())
        want = (1e-3 / xb.SD["carry"] + 2e-2 / xb.SD["flow"] + 0.0) / 3
        self.assertTrue(np.allclose(live.book, want))
        self.assertTrue(np.allclose(live.equal_capital, (1e-3 + 2e-2) / 3))

    def test_event_tickets_booked_on_exit_day_over_slots(self):
        build(self.root, self.days)
        d0 = self.days[3]
        write(self.root / "unlocks_fwd" / "journal" / "tickets.csv",
              [{"ticket": "u1", "exit_ms": ms(d0, 23)}, {"ticket": "u2", "exit_ms": ms(d0, 5)}])
        write(self.root / "unlocks_fwd" / "journal" / "scores.csv", [{"ticket": "u1", "net": 0.05, "net_2x": 0.04}])
        write(self.root / "announce_fwd" / "journal" / "tickets.csv", [{"ticket": "a1", "exit_ms": ms(d0, 1)}])
        write(self.root / "announce_fwd" / "journal" / "scores.csv", [{"ticket": "a1", "net": -0.02, "net_2x": -0.03}])
        b = xb.book_days(self.root, "2026-11-30")
        self.assertAlmostEqual(b.loc[d0, "events"], (0.05 - 0.02) / xb.SLOTS)
        self.assertAlmostEqual(b.loc[d0, "events_2x"], (0.04 - 0.03) / xb.SLOTS)
        self.assertEqual(b.loc[d0, "event_tickets"], 3)
        self.assertEqual(b.loc[d0, "unscored"], 1)                       # u2 counts 0 until scored
        self.assertEqual(b.loc[self.days[4], "events"], 0.0)

    def test_final_needs_carry_flow_and_the_lag(self):
        build(self.root, self.days[:10])
        today = (pd.Timestamp(self.days[-1]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        b = xb.book_days(self.root, today)
        cutoff = (pd.Timestamp(today) - pd.Timedelta(days=xb.FINAL_LAG)).strftime("%Y-%m-%d")
        self.assertEqual(set(b.index[b.final]), {d for d in self.days[:10] if d <= cutoff})
        self.assertFalse(b.loc[self.days[15], "final"])                  # no carry or flow row that day

    def test_looks_pass_continue_fail(self):
        n = xb.LOOKS[0]
        idx = pd.Index([d.strftime("%Y-%m-%d") for d in pd.date_range(xb.START, periods=n)], name="day")
        rng = np.random.default_rng(1)

        def frame(mu):
            f = pd.DataFrame(index=idx)
            for k in xb.FAMILIES:
                f[k] = rng.normal(mu, 1.0, n)
                f[f"{k}_2x"] = f[k] - 0.01
            f["book"] = f[list(xb.FAMILIES)].mean(axis=1)
            f["book_2x"] = f[[f"{k}_2x" for k in xb.FAMILIES]].mean(axis=1)
            f["final"] = True
            return f

        self.assertEqual(xb.look(frame(0.5), n)["verdict"], "PASS")
        self.assertEqual(xb.look(frame(-0.3), n)["verdict"], "FAIL")
        weak = frame(0.0)
        weak["book"] = weak["book"] - weak["book"].mean() + 0.01
        self.assertEqual(xb.look(weak, n)["verdict"], "CONTINUE")
        self.assertIsNone(xb.look(frame(0.5).iloc[:-1], n))

    def test_main_writes_status_and_appends_a_decision_once(self):
        days = [d.strftime("%Y-%m-%d") for d in pd.date_range(xb.START, periods=xb.LOOKS[0] + xb.FINAL_LAG + 1)]
        build(self.root, days, noise=0.5)
        today = (pd.Timestamp(days[-1]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        (self.root / "xbook_fwd").mkdir()
        s = xb.main(exp=self.root, today=today, verify=False)
        self.assertGreaterEqual(s["final_days"], xb.LOOKS[0])
        xb.main(exp=self.root, today=today, verify=False)
        dec = pd.read_csv(self.root / "xbook_fwd" / "journal" / "decisions.csv")
        self.assertEqual(len(dec), 1)                                    # clearly positive nets: one PASS, kept once
        self.assertEqual(dec.verdict.iloc[0], "PASS")


if __name__ == "__main__":
    unittest.main()
