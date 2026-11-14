"""scripts/run_invcost.py (R456): measured costs on R454's and R455's books, offline, on synthetic parents."""
import contextlib
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_invcost", ROOT / "scripts" / "run_invcost.py")
ic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ic)
lv, hi = ic.lv, ic.hi
H = ic.H
T0 = hi.fh.ms("2026-11-12")
SYMS = [f"S{i:02d}" for i in range(20)]
NOW = (T0 + (24 * 3 + 1) * H + 30 * 60_000) / 1000    # three complete days


def walk(seed):
    rng = np.random.default_rng(seed)
    return {s: 10 * np.exp(np.cumsum(rng.normal(0, 0.005, 24 * 6))) for s in SYMS}


def write(root, sub, df, day_of="ts"):
    d = Path(root) / sub
    d.mkdir(parents=True, exist_ok=True)
    df = df.assign(_d=[hi.fh.day_label(int(x)) for x in df[day_of]])
    for day, g in df.groupby("_d"):
        g.drop(columns="_d").to_csv(d / f"{day}.csv", index=False)


def llp_files(root, seed=0):
    rng = np.random.default_rng(seed)
    pos, mk, acc = [], [], []
    for h in range(-2, 24 * 3 + 2):
        run = T0 + h * H + 7 * 60_000
        sh = rng.normal(0, 0.1, len(SYMS))
        for j, s in enumerate(SYMS):
            mk.append({"ts": run, "market_id": j, "symbol": s, "status": "active", "mark_price": 10.0,
                       "open_interest_usd": 1e7, "daily_quote_token_volume": 5e7})
            pos.append({"ts": run, "market_id": j, "symbol": s, "sign": 1 if sh[j] > 0 else -1,
                        "position_value": abs(sh[j]) * 1e7})
        acc.append({"ts": run, "total_asset_value": 1.0})
    write(root, "llp/positions", pd.DataFrame(pos))
    write(root, "llp/markets", pd.DataFrame(mk))
    write(root, "llp/accounts", pd.DataFrame(acc))


def hlp_files(root, seed=1):
    rng = np.random.default_rng(seed)
    pos, ctx = [], []
    for h in range(-2, 24 * 3 + 2):
        run = T0 + h * H + 7 * 60_000
        sh = rng.normal(0, 0.1, len(SYMS))
        for j, s in enumerate(SYMS):
            ctx.append({"ts": run, "coin": s, "mark": 10.0, "oracle": 10.0, "mid": 10.0, "funding": 0.0,
                        "premium": 0.0, "open_interest": 1e6, "day_ntl_vlm": 5e7})
            pos.append({"ts": run + 3_000, "vault": "0xa", "coin": s, "szi": sh[j] * 1e6, "entry_px": 10.0,
                        "position_value": 0, "unrealized_pnl": 0, "margin_used": 0})
    write(root, "hlp/positions", pd.DataFrame(pos))
    write(root, "hlp/ctx", pd.DataFrame(ctx))


def books(root, sub, coin_col, k1, k10, bp):
    rows = [{"ts": T0 + h * H + 50 * 60_000, coin_col: s, f"buy_{k1}_bp": bp, f"sell_{k1}_bp": bp,
             f"buy_{k10}_bp": 2 * bp, f"sell_{k10}_bp": 2 * bp} for h in range(0, 24 * 3 + 2) for s in SYMS]
    write(root, sub, pd.DataFrame(rows))


class Costs(unittest.TestCase):
    def test_nearest_snapshot_fee_and_fallback(self):
        bk = pd.DataFrame({"ts": [T0 + 50 * 60_000, T0 + 5 * H], "symbol": "A", "buy_1k_bp": [4.0, np.nan],
                           "sell_1k_bp": [2.0, 1.0]})
        c, m = ic.measured_costs(np.full((8, 1), 9e-4), ["A"], T0, bk, "symbol", 1e-4, size=1_000)
        self.assertAlmostEqual(c[0, 0], 1e-4 + 3e-4)        # trade at 01:00, snapshot at 00:50
        self.assertTrue(m[1, 0])                            # 02:00 is 70 minutes from 00:50: within 90
        self.assertFalse(m[2, 0])                           # 03:00 is 130 minutes away
        self.assertEqual(c[4, 0], 9e-4)                     # the 05:00 book was too thin: assumed cost
        self.assertEqual(ic.cost_cols("coin", 1_000), ("buy_1000_bp", "sell_1000_bp"))
        self.assertEqual(ic.cost_cols("symbol", 10_000), ("buy_10k_bp", "sell_10k_bp"))


class Parents(unittest.TestCase):
    @contextlib.contextmanager
    def parents(self, d, bp):
        """Synthetic R454 and R455 parents run forward to three complete days, journals in d; patches stay on."""
        llp_files(d)
        hlp_files(d)
        books(d, "lighter/books", "symbol", "1k", "10k", bp)
        books(d, "main/books", "coin", "1000", "10000", bp)
        w = {"R455": walk(2), "R454": walk(3)}

        def rows(lane):
            def f(s, a, b):
                t = np.arange(a, b, H)
                i = ((t - T0) // H).astype(int)
                if lane == "R455":
                    return pd.DataFrame({"t": t, "close": w[lane][s][i], "volume": 1.0})
                return [(int(x), s, float(w[lane][s][k]), 1e-5) for x, k in zip(t, i)]
            return f
        fund = lambda s, a, b: pd.DataFrame({"t": np.arange(a, b, H), "rate": 1e-5})   # noqa: E731
        with mock.patch.object(lv, "J", Path(d) / "j455"), mock.patch.object(hi, "J", Path(d) / "j454"), \
                mock.patch.object(lv.carrylane, "lighter_prices", rows("R455")), \
                mock.patch.object(lv.carrylane, "lighter_funding", fund), \
                mock.patch.object(hi.fh, "fetch_hl", rows("R454")), mock.patch.object(hi.time, "sleep", lambda s: 0), \
                mock.patch.object(lv.time, "time", lambda: NOW), mock.patch.object(hi.time, "time", lambda: NOW):
            lv.forward(d)
            hi.forward(d)
            yield

    def test_measured_equals_assumed_at_9bp_and_parity_guard(self):
        with tempfile.TemporaryDirectory() as d, self.parents(d, 9.0 - 4.5):   # R454: 4.5 bp fee + 4.5 bp slip
            rep = ic.read(d, Path(d) / "out")
            df = pd.read_csv(Path(d) / "out" / "daily.csv")
            a = df[df.lane == "R454"]
            self.assertEqual(len(a), 6)                       # 3 days x 2 books
            self.assertTrue(np.allclose(a.assumed_1x, a.meas_1000_1x))
            b = df[df.lane == "R455"]                         # Lighter: no fee, 4.5 bp slip: cheaper than assumed
            self.assertEqual(len(b), 6)
            self.assertTrue((b.meas_1000_1x > b.assumed_1x).all())
            self.assertTrue((b.meas_10000_1x < b.meas_1000_1x).all())   # the $10k cost is twice the $1k one
            self.assertGreater(rep["R454"]["F"]["traded_share_measured"], 0.9)
            self.assertTrue(rep["R455"]["R"]["decision"].startswith("pending"))
            tk = pd.read_csv(Path(d) / "j455" / "tickets.csv")
            tk.loc[0, "net"] += 1e-4
            tk.to_csv(Path(d) / "j455" / "tickets.csv", index=False)
            with self.assertRaises(SystemExit):
                ic.read(d, Path(d) / "out")


class Frozen(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "invcost_v1" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        text = re.sub(r"\s+", " ", p.read_text())
        for phrase in ("$1k market order", "90 minutes", "4.5 bp", "Standard account", "9df27190", "ea4f9f26",
                       "zero trials"):
            self.assertIn(phrase, text, phrase)


if __name__ == "__main__":
    unittest.main()
