import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_lighter_flow as lf

MS = 1000          # us per ms


def ts(s):
    return pd.Timestamp(s).value // 1000      # us


class Synth:
    """A recorded tape in lf's layout: one 2 h session a day, quotes every 500 ms, an informed account (7) whose
    trades precede a +/-10 bp step 2 s later, a noise account (8) and an anti-informed account (9)."""

    def __init__(self, root, days=("2026-10-29", "2026-10-30", "2026-11-02"), seed=1):
        self.root = Path(root)
        rng = np.random.default_rng(seed)
        ses = []
        for mk in lf.MARKETS:
            tid = 0
            for day in days:
                t0 = ts(f"{day}T02:00:00Z")
                t1 = t0 + 7_200 * 1_000_000
                if mk == lf.MARKETS[0]:
                    ses.append((pd.Timestamp(t0, unit="us").strftime("%Y-%m-%dT%H:%M:%SZ"),
                                pd.Timestamp(t1, unit="us").strftime("%Y-%m-%dT%H:%M:%SZ")))
                grid = np.arange(t0 + 10_000_000, t1 - 10_000_000, 500 * MS)       # quote update times, us
                steps = np.zeros(len(grid))
                trades = []
                for k, T_us in enumerate(np.arange(t0 + 60_000_000, t1 - 400_000_000, 120_000_000)):
                    acct = (7, 8, 9)[k % 3]
                    side = int(rng.choice([1, -1]))
                    if acct == 7:
                        steps[grid >= T_us + 2_000_000] += side * 10e-4
                    elif acct == 9:
                        steps[grid >= T_us + 2_000_000] -= side * 10e-4
                    tid += 1
                    trades.append((T_us + 80 * MS, tid, T_us // MS, T_us + 30 * MS, 1, 0, 100.0 * np.exp(steps[
                        np.searchsorted(grid, T_us) - 1]) * (1 + side * 1e-5), 1.0,
                        acct if side < 0 else 555, acct if side > 0 else 555, int(side > 0), 0, 0, 0.0, 0.0, 0, 0,
                        0.0, 0.0, 0))
                mid = 100.0 * np.exp(steps)
                q = pd.DataFrame(dict(t=grid + 60 * MS, upd=grid, nonce=np.arange(len(grid)), bid=mid * (1 - 1e-5),
                                      bq=np.full(len(grid), 50.0), ask=mid * (1 + 1e-5), aq=np.full(len(grid), 50.0)))
                tr = pd.DataFrame(trades, columns=["t", "trade_id", "T", "tx_us", "block", "liq", "px", "sz",
                                                   "ask_acct", "bid_acct", "maker_ask", "tfee", "mfee", "tpos",
                                                   "tentry", "timf", "tsign", "mpos", "mentry", "mimf"])
                for kind, df in (("quote", q), ("trade", tr)):
                    d = self.root / kind / mk / day
                    d.mkdir(parents=True, exist_ok=True)
                    df.to_parquet(d / "000000-1.parquet", index=False)
        pd.DataFrame(ses, columns=["start_utc", "end_utc"]).assign(seconds=7200, messages=1, ended_by="x").to_csv(
            self.root / "sessions.csv", index=False)


class LighterFlowTest(unittest.TestCase):
    def test_trials(self):
        self.assertEqual(lf.TRIALS, 2 * 3 * 3 + 3 + 3)

    def test_session_of_and_units(self):
        with tempfile.TemporaryDirectory() as d:
            Synth(d)
            st, en = lf.sessions(Path(d) / "sessions.csv")
            self.assertEqual(st[0], ts("2026-10-29T02:00:00Z"))
            i = lf.session_of(np.array([st[0] - 1, st[0] + 5, en[0] + 1]), st, en)
            self.assertEqual(i.tolist(), [-1, 0, -1])

    def test_taker_side_replay_and_queue(self):
        st, en = np.array([1_000_000_000]), np.array([9_000_000_000])
        tr = pd.DataFrame(dict(trade_id=[1, 2, 3, 3], maker_ask=[1, 0, 1, 1], bid_acct=[11, 12, 13, 13],
                               ask_acct=[21, 22, 23, 23], T=[1_001_000, 3_000_000, 4_000_000, 4_000_000],
                               t=[1_001_100_000, 3_000_100_000, 4_006_000_000, 4_006_000_000],
                               liq=[0, 0, 0, 0], px=[1.0, 1.0, 1.0, 1.0]))
        out = lf.make_trades(tr, st, en, "WTI")
        self.assertEqual(len(out), 3)                              # duplicate trade id dropped
        self.assertEqual(out.taker.tolist(), [11, 22, 13])         # ask maker -> bid account is the taker
        self.assertEqual(out.side.tolist(), [1, -1, 1])
        self.assertEqual(out.replay.tolist(), [True, False, False])  # T within 2 s of the session start
        self.assertEqual(out.queued.tolist(), [False, False, True])  # received 6 s after T

    def test_asof_needs_same_session_and_edge_margin(self):
        st, en = np.array([0, 100_000_000]), np.array([50_000_000, 200_000_000])
        Q = dict(u=np.array([10_000_000, 20_000_000, 120_000_000]), s=np.array([0, 0, 1]),
                 bid=np.array([1.0, 2.0, 3.0]), ask=np.array([1.1, 2.1, 3.1]), bq=np.ones(3), aq=np.ones(3))
        b, a, _, _ = lf.asof(Q, [25_000, 49_000, 110_000, 130_000], [0, 0, 1, 1], st, en)
        self.assertEqual(b[0], 2.0)
        self.assertTrue(np.isnan(b[1]))          # within 2 s of the session end
        self.assertTrue(np.isnan(b[2]))          # no session-1 quote before 110 s
        self.assertEqual(b[3], 3.0)

    def test_scores_shrink_and_pick(self):
        m = np.r_[np.full(30, 5.0), np.full(20, -4.0), np.full(5, 50.0)]
        a = np.r_[np.full(30, 1), np.full(20, 2), np.full(5, 3)]
        sc, n = lf.scores(m, a)
        self.assertNotIn(3, sc.index)                       # under N_MIN
        self.assertAlmostEqual(sc[1], 150 / 50)
        self.assertAlmostEqual(sc[2], -80 / 40)
        inf, un = lf.pick(sc)
        self.assertEqual(inf.tolist(), [1])
        self.assertEqual(un.tolist(), [2])

    def test_simulate_costs_cooldown_and_fade(self):
        st, en = np.array([0]), np.array([10_000_000_000])
        u = np.arange(0, 600_000_000, 500_000)
        mid = np.where(u >= 30_000_000, 101.0, 100.0)
        Q = {"WTI": dict(u=u, s=np.zeros(len(u), int), bid=mid - 0.01, ask=mid + 0.01, bq=np.full(len(u), 5.0),
                         aq=np.full(len(u), 5.0))}
        sig = pd.DataFrame(dict(mkt="WTI", T=[20_000, 25_000, 200_000], trade_id=[1, 2, 3], side=[1, 1, 1],
                                sess=[0, 0, 0], day="2026-10-30", taker=7))
        df = lf.simulate(sig, Q, 1_300, 60_000, 1, st, en)
        self.assertEqual(len(df), 2)                        # the 25 s signal falls inside the first position
        self.assertAlmostEqual(df.gross.iloc[0], 1e4 * np.log(101 / 100), places=6)
        self.assertAlmostEqual(df.cost.iloc[0], 1e4 * (np.log(100.01 / 100) + np.log(101 / 100.99)), places=6)
        self.assertTrue(df.thin.iloc[0])                    # 5 units x 100 = 500 < 1,000
        self.assertAlmostEqual(df.net2.iloc[0], df.gross.iloc[0] - 2 * df.cost.iloc[0])
        fade = lf.simulate(sig, Q, 1_300, 60_000, -1, st, en)
        self.assertAlmostEqual(fade.gross.iloc[0], -df.gross.iloc[0])

    def test_block_boot_and_verdict(self):
        rng = np.random.default_rng(0)
        ci = lf.block_boot(np.ones(200), np.repeat(np.arange(20), 10), rng)
        self.assertEqual((ci["mean"], ci["lo"], ci["hi"]), (1.0, 1.0, 1.0))
        df = pd.DataFrame(dict(net1=np.ones(200), net2=np.ones(200)))
        self.assertEqual(lf.verdict(df, ci, 0.99), "PASS")
        self.assertEqual(lf.verdict(df, ci, 0.50), "NULL")
        self.assertEqual(lf.verdict(df.head(50), ci, 0.99), "INCONCLUSIVE")
        d = lf.block_boot_diff(np.r_[np.full(50, 2.0), np.zeros(150)], np.r_[np.ones(50), np.zeros(150)],
                               np.repeat(np.arange(20), 10), rng)
        self.assertAlmostEqual(d["diff"], 2.0)

    def test_end_to_end_synthetic_run(self):
        with tempfile.TemporaryDirectory() as d:
            Synth(d)
            real_pq, real_csv = pd.read_parquet, pd.read_csv

            def guard(fn):
                def g(path, *a, **k):          # the dry run must never open a real data file
                    if not str(Path(path).resolve()).startswith(str(Path(d).resolve())):
                        raise AssertionError(f"synthetic run opened {path}")
                    return fn(path, *a, **k)
                return g

            lf.pd.read_parquet, lf.pd.read_csv = guard(real_pq), guard(real_csv)
            try:
                res, df = lf.run(data=Path(d), verify=False)
            finally:
                lf.pd.read_parquet, lf.pd.read_csv = real_pq, real_csv
            self.assertIn(7, res["informed_accounts"]["h60s"])
            self.assertIn(9, res["uninformed_accounts"]["h60s"])
            self.assertGreater(res["primary"]["n"], 0)
            self.assertGreater(df.gross.mean(), 0)             # following the informed account pays here
            self.assertEqual(len(res["cells"]), 21)
            self.assertEqual(len(res["partA"]), 3)
            fade = [c for c in res["cells"] if c["direction"] == "fade" and c["h_s"] == 60 and c["delay_ms"] == 1300]
            self.assertGreater(fade[0]["gross"], 0)             # fading the anti-informed account pays too


if __name__ == "__main__":
    unittest.main()
