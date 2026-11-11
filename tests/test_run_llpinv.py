"""scripts/run_llpinv.py (R455): LLP snapshot table, Lighter price rows and R454's rule reused, offline."""
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_llpinv", ROOT / "scripts" / "run_llpinv.py")
lv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lv)
H = lv.H
T0 = lv.fh.ms("2026-11-12")


def files(run, symbols, shares, vlm=50e6, oi_usd=20e6, status="active"):
    mk = pd.DataFrame({"ts": run, "market_id": range(len(symbols)), "symbol": symbols, "status": status,
                       "mark_price": 10.0, "index_price": 10.0, "last_trade_price": 10.0, "open_interest": 1.0,
                       "open_interest_usd": oi_usd, "daily_quote_token_volume": vlm, "taker_fee": 0, "maker_fee": 0})
    pos = pd.DataFrame({"ts": run, "market_id": range(len(symbols)), "symbol": symbols,
                        "sign": [1 if s > 0 else -1 for s in shares], "position": 1.0,
                        "position_value": [abs(s) * oi_usd for s in shares]})
    pos = pos[np.array(shares) != 0]
    acc = pd.DataFrame({"ts": [run], "total_asset_value": 1.0, "collateral": 1.0, "available_balance": 1.0,
                        "total_shares": 1, "positions": len(pos)})
    return pos, mk, acc


class Snapshots(unittest.TestCase):
    def test_share_sign_and_eligibility(self):
        syms = [f"S{i:02d}" for i in range(20)]
        sh = list(np.linspace(-0.3, 0.3, 19)) + [0.0]
        pos, mk, acc = files(T0 + 7 * 60_000, syms, sh)
        mk.loc[0, "status"] = "inactive"
        mk.loc[1, "daily_quote_token_volume"] = 5e6
        tab = lv.snapshots(pos, mk, acc).set_index("coin")
        self.assertAlmostEqual(tab.loc["S02", "share"], sh[2])
        self.assertEqual(tab.loc["S19", "share"], 0.0)                    # no position: share 0
        self.assertFalse(tab.loc["S00", "elig"])                          # inactive market
        self.assertFalse(tab.loc["S01", "elig"])                          # $5M volume
        self.assertTrue(tab.loc["S02", "elig"])
        self.assertEqual(int(tab.snap.iloc[0]), T0 + 7 * 60_000)

    def test_runs_need_an_accounts_row(self):
        pos, mk, acc = files(T0, ["A", "B"], [0.1, -0.1])
        self.assertTrue(lv.snapshots(pos, mk, acc.assign(ts=T0 + H)).empty)

    def test_r454_rule_applies(self):
        syms = [f"S{i:02d}" for i in range(16)]
        sh = [-0.5, -0.4] + [0.01] * 13 + [0.5]
        tab = lv.snapshots(*files(T0 + 7 * 60_000, syms, sh))
        ind, basket, opened = lv.hi.build(tab, syms, T0, 48, np.ones((49, 16)))
        self.assertEqual(list(np.flatnonzero(ind["F"][0])), [0, 1])
        self.assertTrue(opened[0])


class Prices(unittest.TestCase):
    def test_closed_candles_with_their_funding(self):
        c = pd.DataFrame({"t": [T0, T0 + H, T0 + 2 * H], "close": [1.0, 2.0, 3.0], "volume": 0.0})
        f = pd.DataFrame({"t": [T0 + 5, T0 + H], "rate": [1e-5, -2e-5]})
        with mock.patch.object(lv.carrylane, "lighter_prices", lambda s, a, b: c), \
                mock.patch.object(lv.carrylane, "lighter_funding", lambda s, a, b: f):
            rows = lv.fetch_lighter("BTC", T0, T0 + 2 * H)
        self.assertEqual([r[0] for r in rows], [T0, T0 + H])             # the bar still open is left out
        self.assertEqual(rows[0][3], 1e-5)
        self.assertEqual(rows[1][3], -2e-5)

    def test_unlisted_symbol_is_skipped_other_errors_raise(self):
        syms = [f"S{i:02d}" for i in range(16)]
        pos, mk, acc = files(T0 + 7 * 60_000, syms, [0.1] * 16)
        with tempfile.TemporaryDirectory() as d:
            for k, df in (("positions", pos), ("markets", mk), ("accounts", acc)):
                (Path(d) / "llp" / k).mkdir(parents=True)
                df.to_csv(Path(d) / "llp" / k / "2026-11-12.csv", index=False)
            seen = []

            def gone(s, a, b):
                seen.append(s)
                raise KeyError(s)
            with mock.patch.object(lv, "J", Path(d) / "journal"), \
                    mock.patch.object(lv.carrylane, "lighter_prices", gone), \
                    mock.patch.object(lv.time, "time", lambda: (T0 + 3 * H) / 1000):
                lv.forward(d)
                self.assertEqual(len(seen), 16)
                with mock.patch.object(lv.carrylane, "lighter_prices", mock.Mock(side_effect=RuntimeError("down"))), \
                        self.assertRaises(RuntimeError):
                    lv.forward(d)


class Frozen(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "llpinv_v1" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        text = re.sub(r"\s+", " ", p.read_text())
        for phrase in (f"from {lv.FWD_START}", f"counted from {lv.hi.COUNT_START}", "$10M", "$2M", "9 bp",
                       f"seed {lv.SEED}", "status active", "R454's rule", "9df27190"):
            self.assertIn(phrase, text, phrase)


if __name__ == "__main__":
    unittest.main()
