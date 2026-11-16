"""scripts/run_gatemaker.py (R497): sampling, windows, paging, markout signs, the sign check and the verdict."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_gatemaker as gm  # noqa: E402

T0 = datetime(2026, 11, 2, 5, tzinfo=timezone.utc)


def tape(rows):
    return pd.DataFrame(rows, columns=["id", "t", "size", "price"])


class Parts(unittest.TestCase):
    def test_universe_is_seeded_and_banded(self):
        contracts = [{"name": f"C{i:03d}_USDT", "quanto_multiplier": "1", "maker_fee_rate": "-0.0001",
                      "taker_fee_rate": "0.00075"} for i in range(100)]
        contracts.append({"name": "DEL_USDT", "in_delisting": True, "quanto_multiplier": "1"})
        tickers = [{"contract": f"C{i:03d}_USDT", "volume_24h_quote": str(10 ** (3 + i % 5))} for i in range(100)]
        a, b = gm.universe(contracts, tickers), gm.universe(list(reversed(contracts)), tickers)
        self.assertEqual([r["contract"] for r in a], [r["contract"] for r in b])
        self.assertNotIn("DEL_USDT", {r["contract"] for r in a})
        per = pd.Series([r["band"] for r in a]).value_counts()
        self.assertTrue((per <= gm.PER_BAND).all())
        self.assertAlmostEqual(a[0]["maker_fee_listed_bp"], -1.0)

    def test_windows(self):
        w = gm.windows()
        self.assertEqual(len(w), gm.DAYS * gm.HOURS_PER_DAY)
        self.assertEqual(w, gm.windows())
        self.assertTrue(all(x.minute == 0 for x in w))
        self.assertEqual(w[0].date().isoformat(), "2026-11-02")
        self.assertEqual(w[-1].date().isoformat(), "2026-11-15")

    def test_paging_dedupes_and_stops(self):
        calls = []
        full = [{"id": i, "create_time_ms": T0.timestamp() + i * 0.5, "size": 1, "price": "1"} for i in range(2500)]

        def get(url):
            calls.append(url)
            to = int(url.split("to=")[1])
            batch = sorted([t for t in full if t["create_time_ms"] <= to], key=lambda t: -t["id"])
            return batch[:gm.PAGE]
        x, cov, pages = gm.fetch_window(get, "X_USDT", T0, sleep=lambda s: None)
        self.assertEqual(len(x), 2500)
        self.assertEqual(x.id.nunique(), 2500)
        self.assertEqual(cov, int(T0.timestamp()) - gm.MARGIN_S)
        self.assertGreaterEqual(pages, 3)

    def test_markouts_planted(self):
        # Alternating taker sells at the bid (99.9) and buys at the ask (100.1) every second; at 05:30 the price
        # steps up by 1%. A taker sell just before the step fills a resting bid that then gains.
        rows, i = [], 0
        for s in range(-300, 3900):
            mid = 100.0 if s < 1800 else 101.0
            d = 1 if s % 2 else -1
            rows.append((i, T0.timestamp() + s, d * 10, mid + d * 0.1))
            i += 1
        out = gm.measure(tape(rows), T0, T0.timestamp() - gm.MARGIN_S, quanto=1.0)
        self.assertTrue(((out.t >= T0.timestamp()) & (out.t < T0.timestamp() + 3600)).all())
        flat = out[(out.t < T0.timestamp() + 1700)]
        self.assertAlmostEqual(flat.eff_half_bp.median(), 10.0, places=1)       # 0.1 on 100 = 10 bp
        self.assertAlmostEqual(flat["mk_1s_bp"].median(), 10.0, delta=0.2)
        before = out[(out.t >= T0.timestamp() + 1790) & (out.t < T0.timestamp() + 1800)]
        sells = before[before.d < 0]
        self.assertTrue((sells["mk_60s_bp"] > 90).all())                         # resting bids gained about 1%
        buys = before[before.d > 0]
        self.assertTrue((buys["mk_60s_bp"] < -80).all())                         # resting asks lost

    def test_sign_check(self):
        rows = [(i, 1000 + i * 0.5, (1 if i % 2 else -1) * 5, 100.1 if i % 2 else 99.9) for i in range(50)]
        good, n = gm.sign_check(tape(rows))
        self.assertEqual(good, 1.0)
        self.assertGreater(n, 40)
        flipped = tape([(a, b, -c, d) for a, b, c, d in rows])
        self.assertEqual(gm.sign_check(flipped)[0], 0.0)

    def test_verdict(self):
        hold = {"contracts": 10, "holds": True}
        fail = {"contracts": 10, "holds": False}
        self.assertEqual(gm.verdict([hold, hold], 40, 0.9), "LEVER_HOLDS")
        self.assertEqual(gm.verdict([hold, fail], 40, 0.9), "PARTIAL")
        self.assertEqual(gm.verdict([fail], 40, 0.9), "LEVER_FAILS")
        self.assertEqual(gm.verdict([hold], 20, 0.9), "INSUFFICIENT_DATA")
        self.assertEqual(gm.verdict([hold], 40, 0.4), "INVALID")
        self.assertEqual(gm.verdict([hold], 40, np.nan), "INVALID")

    def test_band_table_rule(self):
        per = pd.DataFrame({"band": ["a"] * 9, "trades": [500] * 9, "eff_half_bp": [5.0] * 9,
                            "mk_5s_bp_nw": [3.0] * 9, "maker_fee_listed_bp": [-1.0] * 9,
                            "flow_sell_usd_h": [1e4] * 9, "flow_buy_usd_h": [1e4] * 9,
                            **{f"mk_{k}s_bp_{w}": [3.0] * 9 for k in gm.DELTAS for w in ("nw", "tw") if k != 5 or w != "nw"}})
        b = gm.band_table(per)[0]
        self.assertAlmostEqual(b["taker_bp"], 12.5)
        self.assertAlmostEqual(b["hedged_maker_bp"], -1.0)
        self.assertTrue(b["holds"])


if __name__ == "__main__":
    unittest.main()
