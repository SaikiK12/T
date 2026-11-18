import unittest

import numpy as np
import pandas as pd

from lab import xfund
from scripts import fetch_bitfinex_history as fb
from scripts import run_xfund_bfx as r

H = 3_600_000
E0 = 1_700_000_000_000 - 1_700_000_000_000 % (8 * H)


def status_row(t, evt, rate, acc=0.0):
    row = [None] * 23
    row[0], row[2], row[3], row[7], row[8], row[11], row[14], row[17], row[21], row[22] = (
        t, 100.0, 100.0, evt, acc, rate, 100.0, 5.0, 0.0005, 0.0025)
    return row


class Reduce(unittest.TestCase):
    def test_one_row_per_period_across_pages(self):
        rows = [status_row(E0 + m * 60_000, E0 + 8 * H, 0.0) for m in range(1, 300)]
        rows += [status_row(E0 + m * 60_000, E0 + 8 * H, 0.0002) for m in range(300, 480)]   # a change inside
        rows += [status_row(E0 + 8 * H + m * 60_000, E0 + 16 * H, 0.0003, acc=0.0008) for m in range(1, 481)]
        page1, page2 = rows[:400], rows[400:]                      # the first period is split across two pages
        parts = fb.reduce_page(page1) + fb.reduce_page(page2)
        df = fb.combine(parts)
        self.assertEqual(df.t.tolist(), [E0 + 8 * H, E0 + 16 * H])
        self.assertEqual(df.rows.tolist(), [479, 480])
        self.assertAlmostEqual(df.rate.iloc[0], 0.0002)            # the period's last row
        self.assertEqual(df.rate_changes.iloc[0], 1)
        self.assertEqual(df.rate_changes.iloc[1], 0)
        self.assertAlmostEqual(df.acc_last.iloc[1], 0.0008)

    def test_seam_change_is_counted(self):
        a = [status_row(E0 + m * 60_000, E0 + 8 * H, 0.0) for m in range(1, 10)]
        b = [status_row(E0 + m * 60_000, E0 + 8 * H, 0.0001) for m in range(10, 20)]
        df = fb.combine(fb.reduce_page(a) + fb.reduce_page(b))
        self.assertEqual(df.rate_changes.iloc[0], 1)

    def test_candles_frame_and_filter(self):
        c = fb.candles_frame([[2 * H, 1, 2, 3, 0.5, 10], [H, 1, 1.5, 2, 1, 5], [2 * H, 1, 2.5, 3, 0.5, 11]])
        self.assertEqual(c.t.tolist(), [H, 2 * H])
        self.assertEqual(c.close.tolist(), [1.5, 2.5])             # [MTS, OPEN, CLOSE, HIGH, LOW, VOLUME]
        self.assertEqual(list(c.columns), ["t", "open", "high", "low", "close", "volume"])
        self.assertTrue(fb.is_crypto("BTCF0:USTF0"))
        for p in ("EVIVF0:USTF0", "XPTF0:USTF0", "UKOILF0:USTF0", "GERMANY40IXF0:USTF0", "ETHF0:BTCF0",
                  "TESTBTCF0:TESTUSDTF0"):
            self.assertFalse(fb.is_crypto(p), p)


class Symbols(unittest.TestCase):
    def test_aliases_and_discovery(self):
        have = {"ALGOUSDT", "1000PEPEUSDT", "BTCUSDT", "1000000MOGUSDT", "ATOMUSDT"}
        cmap = {"ALG": "ALGO", "ATO": "ATOM", "UST": "USDt"}
        self.assertEqual(r.binance_for("ALG", cmap, have), "ALGOUSDT")
        self.assertEqual(r.binance_for("PEPE", cmap, have), "1000PEPEUSDT")
        self.assertEqual(r.binance_for("MOG", cmap, have), "1000000MOGUSDT")
        self.assertIsNone(r.binance_for("ZZZ", cmap, have))
        self.assertEqual(r.coin_name("1000PEPEUSDT"), "PEPE")
        self.assertEqual(r.coin_name("1000000MOGUSDT"), "MOG")
        codes = r.discovery_codes(sorted(have | {"币安人生USDT"}), cmap, ["BTC", "ALG"])
        self.assertEqual(codes, ["ALGO", "ATO", "ATOM", "MOG", "PEPE"])
        t = r.symbol_table(["ALG", "PEPE", "ZZZ"], cmap, have)
        self.assertEqual(t.to_dict("records"), [{"key": "ALG", "binance": "ALGOUSDT", "bitfinex": "ALG"},
                                                {"key": "PEPE", "binance": "1000PEPEUSDT", "bitfinex": "PEPE"}])


def world(spread_per_day, n_coins=8, nd=400, seed=0):
    """Two venues trading the same coins; Binance funding pays `spread_per_day` more than Bitfinex's."""
    rng = np.random.default_rng(seed)
    series = []
    for c in range(n_coins):
        px = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, nd)))
        noise = np.exp(rng.normal(0, 0.0005, nd))
        fresh = np.ones(nd, bool)
        fa = np.full(nd, 0.0) + rng.normal(0, 0.00002, nd)          # Bitfinex: dead zone, mostly zero
        fbn = np.full(nd, spread_per_day * (1 + 0.2 * c / n_coins)) + rng.normal(0, 0.00002, nd)
        n = np.full(nd, 3)
        series.append([xfund.Daily.build(px, fresh, fbn, n), xfund.Daily.build(px * noise, fresh, fa, n)])
    return xfund.Universe([f"C{c}" for c in range(n_coins)], ["binance", "bitfinex"], series, 0, nd, 30, 0.9, 20)


class Book(unittest.TestCase):
    def run_book(self, u, th=0.05, k=4):
        vset = [0, 1]
        rows, trades = xfund.replay(u, xfund.Book(vset, 14, th, k), xfund.window_start(u, vset, 14))
        tr = r.trade_pnl(u, trades, int(rows.day.iloc[-1]))
        return rows, tr, r.summarize(rows, tr, k, r.COST)

    def test_planted_spread_passes_and_contributions_add_up(self):
        u = world(0.0006)                                           # about 22%/yr of funding spread
        rows, tr, (rep, x) = self.run_book(u)
        self.assertGreater(rep["ann_1x_pct"], 5)
        self.assertEqual(r.decide(rep)[0], "PASS")
        self.assertEqual(set(rep["by_long_venue_trades"]), {"bitfinex"})   # long the venue paying less
        self.assertAlmostEqual(sum(rep["by_coin_bp_per_day"].values()), x.mean() * 1e4, places=6)
        self.assertGreater(rep["funding_share"], 0.5)

    def test_no_spread_does_not_pass(self):
        u = world(0.0)
        rows, tr, (rep, x) = self.run_book(u)
        self.assertNotEqual(r.decide(rep)[0], "PASS")

    def test_decide_rules(self):
        ok = {"n": 100, "p_one_sided": 0.01, "mean_2x_bp": 1.0, "trimmed_mean_bp": 0.5, "l2co_mean_bp": 0.2}
        self.assertEqual(r.decide(ok)[0], "PASS")
        self.assertEqual(r.decide(dict(ok, l2co_mean_bp=-0.1))[0], "FAIL")
        self.assertEqual(r.decide(dict(ok, n=10))[0], "UNREADABLE")


if __name__ == "__main__":
    unittest.main()


class EndToEnd(unittest.TestCase):
    def test_run_on_synthetic_parquet(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            for d in ("klines_1h", "fundingRate", "bitfinex_hist/candles_1h", "bitfinex_hist/funding",
                      "bitfinex_hist/receipts"):
                (data / d).mkdir(parents=True)
            t0 = fb.ms("2021-01-01")
            hours = np.arange(t0, fb.ms("2021-12-31"), H)
            rng = np.random.default_rng(3)
            for code, bn in (("ALG", "ALGOUSDT"), ("BTC", "BTCUSDT"), ("PEPE", "1000PEPEUSDT")):
                px = 50 * np.exp(np.cumsum(rng.normal(0, 0.004, len(hours))))
                pd.DataFrame({"t": hours, "close": px, "volume": 1.0}).to_parquet(data / "klines_1h" / f"{bn}.parquet")
                ev = hours[hours % (8 * H) == 0]
                pd.DataFrame({"t": ev, "interval_h": 8, "rate": 0.0002}).to_parquet(data / "fundingRate" / f"{bn}.parquet")
                k = 1000 if bn.startswith("1000") else 1
                pd.DataFrame({"t": hours, "open": px / k, "high": px / k, "low": px / k, "close": px / k * 1.0001,
                              "volume": 2.0}).to_parquet(data / "bitfinex_hist/candles_1h" / f"{code}.parquet")
                pd.DataFrame({"t": ev, "rate": 0.0}).to_parquet(data / "bitfinex_hist/funding" / f"{code}.parquet")
                (data / "bitfinex_hist/receipts" / f"{code}.json").write_text("{}")
            (data / "bitfinex_hist" / "currency_map.json").write_text(json.dumps({"ALG": "ALGO"}))
            lane = root / "lane"
            with mock.patch.object(r, "ROOT", root), mock.patch.object(r, "DATA", data / "bitfinex_hist"), \
                    mock.patch.object(r, "LANE", lane), mock.patch.object(r, "END", "2021-12-30"), \
                    mock.patch.object(r, "check_inputs", lambda: []), mock.patch("lab.prereg.verify", lambda p: None), \
                    mock.patch.object(r, "binance_symbols", lambda root=None: ["1000PEPEUSDT", "ALGOUSDT", "BTCUSDT"]):
                r.run()
                rep = json.loads((lane / "results" / "report.json").read_text())
                self.assertEqual(rep["symbols"], 3)
                self.assertIn(rep["verdict"], ("PASS", "FAIL", "UNREADABLE"))
                self.assertGreater(rep["primary"]["ann_1x_pct"], 0)      # 0.02%/8 h of spread, no price drift
                self.assertAlmostEqual(rep["funding_profile"]["BTC"]["bitfinex_zero_share"], 1.0)
                self.assertTrue((lane / "results" / "daily.csv").exists())
                with self.assertRaises(SystemExit):                      # read once
                    r.run()
