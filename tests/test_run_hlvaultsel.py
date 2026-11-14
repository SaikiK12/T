"""scripts/run_hlvaultsel.py (R450): vault selection by past record on a synthetic vault layout, offline."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_hlvaultsel", ROOT / "scripts" / "run_hlvaultsel.py")
hs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hs)
D = hs.DAY
T0 = hs.ms("2023-06-01")


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def layout(root, vaults):
    """vaults: {address: (created_ms, av, daily_ret fn(k) -> float, fee, rel)}; weekly points from creation."""
    idx, meta = [], []
    for a, (created, av, ret, fee, rel) in vaults.items():
        idx.append({"address": a, "name": a, "leader": "0x1", "created_ms": created, "is_closed": 0,
                    "relationship": rel, "first_seen_ms": 0})
        meta.append({"address": a, "fetched_ms": 0, "is_closed": 0, "allow_deposits": 1, "leader_commission": fee,
                     "leader_fraction": 0.1, "points": 0, "peak_av": av})
        rows, pnl = [], 0.0
        for k in range(0, 1300, 7):
            t = created + k * D
            rows.append({"ts": t, "account_value": av, "pnl": pnl})
            pnl += sum(ret(k + j) for j in range(7)) * av
        write_csv(root / "hist" / a[2:6] / f"{a}.csv", ["ts", "account_value", "pnl"], rows)
    write_csv(root / "index.csv", ["address", "name", "leader", "created_ms", "is_closed", "relationship",
                                   "first_seen_ms"], idx)
    write_csv(root / "meta.csv", ["address", "fetched_ms", "is_closed", "allow_deposits", "leader_commission",
                                  "leader_fraction", "points", "peak_av"], meta)


def addr(k):
    return "0x" + f"{k:040x}"


class Book(unittest.TestCase):
    def test_picks_the_steady_vaults_and_charges_the_fee(self):
        rng = np.random.default_rng(0)
        noise = {k: rng.normal(0, 0.02, 2000) for k in range(12)}
        vaults = {}
        for k in range(12):                       # 0-9 steady +0.05%/day; 10-11 noisy; 12 small; 13 young; 14 child
            vaults[addr(k)] = (T0, 1e6, (lambda j: 0.0005) if k < 10 else (lambda j, k=k: noise[k][j]), 0.1,
                               "normal")
        vaults[addr(12)] = (T0, 1e5, lambda j: 0.001, 0.1, "normal")
        vaults[addr(13)] = (hs.ms("2024-05-01"), 1e6, lambda j: 0.001, 0.1, "normal")
        vaults[addr(14)] = (T0, 1e6, lambda j: 0.001, 0.1, "child")
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), vaults)
            hist, info = hs.load(d)
            self.assertNotIn(addr(14), hist)                                  # children dropped
            book = hs.run(hist, info, "2024-03-31", "2024-05-31")
            first = book.iloc[0]
            self.assertEqual(first.eligible, 12)                              # small and young vaults excluded
            self.assertEqual(set(first.addresses.split()), {addr(k) for k in range(10)})
            gross = 0.0005 * 30                                               # weekly points: 4 or 5 weeks
            self.assertAlmostEqual(first.gross, gross, delta=0.0005 * 7)
            self.assertAlmostEqual(first.net_fee, first.gross * 0.9)
            self.assertAlmostEqual(first.cost_1x, hs.SWITCH_COST)              # 10 of 10 slots new
            self.assertAlmostEqual(book.iloc[1].cost_1x, 0.0)                   # same picks, no switch

    def test_dormant_vaults_are_not_picked(self):
        # a vault whose pnl moves in one week of ten (always up) has a tiny sd; it must not be scored
        vaults = {addr(1): (T0, 1e6, lambda j: 0.002 if (j // 7) % 10 == 0 else 0.0, 0.1, "normal"),
                  addr(2): (T0, 1e6, lambda j: 0.0005 + 0.0001 * (-1) ** (j // 7), 0.1, "normal")}
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), vaults)
            hist, info = hs.load(d)
            t = hs.ms("2024-03-31") + D - 1
            self.assertIsNone(hs.score(hist[addr(1)], t))
            self.assertIsNotNone(hs.score(hist[addr(2)], t))
            self.assertEqual(hs.run(hist, info, "2024-03-31", "2024-03-31").iloc[0].addresses, addr(2))

    def test_empty_slots_earn_the_hurdle(self):
        vaults = {addr(k): (T0, 1e6, lambda j: 0.0005, 0.0, "normal") for k in range(4)}
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), vaults)
            hist, info = hs.load(d)
            row = hs.run(hist, info, "2024-03-31", "2024-03-31").iloc[0]
            self.assertEqual(row.picks, 4)
            picked = np.mean([hs.held_return(hist[a], hs.ms("2024-03-31") + D - 1, hs.ms("2024-04-30") + D - 1)
                              for a in vaults])
            idle = hs.HURDLE_ANN * row.days / 365
            self.assertAlmostEqual(row.net_fee, 0.4 * picked + 0.6 * idle)

    def test_held_return_after_closure_stays_flat(self):
        h = (np.array([0, 10, 20], dtype=np.int64), np.array([100.0, 110.0, 0.0]), np.array([0.0, 10.0, 10.0]))
        self.assertAlmostEqual(hs.held_return(h, 10, 25), 0.0)
        self.assertAlmostEqual(hs.held_return(h, 0, 25), 0.10)
        self.assertEqual(hs.held_return(h, -5, 25), 0.0)                      # no point before t0

    def test_flows_do_not_inflate_returns(self):
        # 100 -> a 900 deposit and 10 of pnl -> 1010; then a withdrawal of 500 and 20 of pnl -> 530
        h = (np.array([0, 10, 20], dtype=np.int64), np.array([100.0, 1010.0, 530.0]), np.array([0.0, 10.0, 30.0]))
        r = hs.period_returns(h, 0, 2)
        self.assertAlmostEqual(r[0], 10 / 1000)                              # start value plus the inflow
        self.assertAlmostEqual(r[1], 20 / 1010)                              # an outflow leaves the start value
        self.assertAlmostEqual(hs.held_return(h, 0, 20), (1 + 10 / 1000) * (1 + 20 / 1010) - 1)
        empty = (np.array([0, 10], dtype=np.int64), np.array([0.0, 0.0]), np.array([0.0, 0.0]))
        self.assertEqual(list(hs.period_returns(empty, 0, 1)), [0.0])

    def test_summary_and_decisions(self):
        import pandas as pd
        book = pd.DataFrame({"formation": [f"m{k}" for k in range(24)], "days": [30.4] * 24,
                             "net_1x": [0.01 + 0.002 * (-1) ** k for k in range(24)],
                             "net_2x": [0.009] * 24, "net_3x": [0.008] * 24, "gross": [0.012] * 24,
                             "net_fee": [0.0108] * 24, "picks": [10] * 24, "new": [2] * 24})
        s = hs.summary(book)
        self.assertAlmostEqual(s["1x"]["net_ann"], 0.24 / (24 * 30.4 / 365), places=6)
        self.assertEqual(hs.decide_gate0(s), "EARNED (forward continues)")
        s["2x"]["excess_ann"] = -0.01
        self.assertEqual(hs.decide_gate0(s), "NULL (stop)")
        self.assertEqual(hs.decide_forward({"months": 3}), "no look reached (3 held months)")

    def test_last_formation(self):
        import pandas as pd
        self.assertEqual(hs.last_formation("2026-11-30", pd.Timestamp("2027-01-05")), "2026-11-30")
        self.assertEqual(hs.last_formation("2026-11-30", pd.Timestamp("2026-12-20")), "2026-10-31")


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "hlvaultsel_v1" / "PREREG.md").read_text()
        self.assertEqual((hs.MIN_AGE_DAYS, hs.MIN_AV, hs.LOOKBACK_DAYS, hs.MIN_PERIODS, hs.TOP_N, hs.MIN_ACTIVE),
                         (180, 500_000.0, 180, 6, 10, 0.8))
        self.assertEqual((hs.DEFAULT_COMMISSION, hs.SWITCH_COST, hs.HURDLE_ANN, hs.NW_LAG), (0.10, 0.0010, 0.04, 3))
        for s in ("at least 180 days old", "at least $500k", "past 180 days", "at least 6 periods", "the 10 vaults",
                  "10 bp", "4.0%/yr on capital", "lag 3", "2024-01-31", "2026-09-30", "12 held months",
                  "net inflow", "earns the hurdle", "least 80% of them"):
            self.assertIn(s, text)
        self.assertEqual(hs.WINDOWS["gate0"], ("2024-01-31", "2026-09-30"))


if __name__ == "__main__":
    unittest.main()
