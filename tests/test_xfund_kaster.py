import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_xfund_kaster as r

H = 3_600_000
DAY = 24 * H


class Symbols(unittest.TestCase):
    def test_rule(self):
        info = {"symbols": [
            {"symbol": "1000PEPEUSDT", "baseAsset": "1000PEPE", "quoteAsset": "USDT", "contractType": "PERPETUAL",
             "status": "TRADING"},
            {"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "contractType": "PERPETUAL",
             "status": "TRADING"},
            {"symbol": "OLDUSDT", "baseAsset": "OLD", "quoteAsset": "USDT", "contractType": "PERPETUAL",
             "status": "SETTLING"},                                        # being delisted: kept
            {"symbol": "ETHUSD1", "baseAsset": "ETH", "quoteAsset": "USD1", "contractType": "PERPETUAL",
             "status": "TRADING"},                                         # not USDT: left out
            {"symbol": "PAXGUSDT", "baseAsset": "PAXG", "quoteAsset": "USDT", "contractType": "PERPETUAL",
             "status": "TRADING"},
            {"symbol": "NEWUSDT", "baseAsset": "NEW", "quoteAsset": "USDT", "contractType": "",
             "status": "PENDING_TRADING"}]}
        k = [{"symbol": "PF_XBTUSD", "base": "BTC", "route": "open"},
             {"symbol": "PF_PEPEUSD", "base": "PEPE", "route": "open"},
             {"symbol": "PF_OLDUSD", "base": "OLD", "route": "open"},
             {"symbol": "PF_ETHUSD", "base": "ETH", "route": "open"},
             {"symbol": "PF_PAXGUSD", "base": "PAXG", "route": "open"},
             {"symbol": "PF_NEWUSD", "base": "NEW", "route": "open"}]
        t = r.symbol_table(k, r.aster_contracts(info), {"BTC", "kPEPE"}, {"BTC"})
        self.assertEqual(t.to_dict("records"), [
            {"key": "BTC", "kraken": "PF_XBTUSD", "hyperliquid": "BTC", "aster": "BTCUSDT", "in_r508": True},
            {"key": "PEPE", "kraken": "PF_PEPEUSD", "hyperliquid": "kPEPE", "aster": "1000PEPEUSDT", "in_r508": False},
            {"key": "OLD", "kraken": "PF_OLDUSD", "hyperliquid": "", "aster": "OLDUSDT", "in_r508": False}])

    def test_funding_pages(self):
        a = r.ms("2026-01-01")
        page1 = [{"fundingTime": a + i * 8 * H, "fundingRate": "0.0001"} for i in range(1000)]
        page2 = [{"fundingTime": a + (1000 + i) * 8 * H, "fundingRate": "0.0002"} for i in range(5)]
        calls = []

        def fake(url, tries=5):
            calls.append(url)
            return page1 if len(calls) == 1 else page2
        with mock.patch.object(r, "get", fake), mock.patch.object(r, "PACE", 0):
            f = r.aster_funding("XUSDT", a, a + 2000 * 8 * H)
        self.assertEqual(len(f), 1005)
        self.assertIn(f"startTime={a + 999 * 8 * H + 1}", calls[1])


def write_world(data, coins, spread_8h, start, end, seed=0):
    rng = np.random.default_rng(seed)
    for d in ("kraken_hist/open/candles_1d", "kraken_hist/open/funding", "hyperliquid/candles_1d",
              "hyperliquid/funding", "aster_hist/candles_1d", "aster_hist/funding", "aster_hist/receipts"):
        (data / d).mkdir(parents=True)
    days = np.arange(start - 40 * DAY, end + 2 * DAY, DAY)
    hours = np.arange(start - 40 * DAY, end + 2 * DAY, H)
    evs = hours[hours % (8 * H) == 0]
    rows = []
    for i, c in enumerate(coins):
        px = 20 * np.exp(np.cumsum(rng.normal(0, 0.03, len(days))))
        rows.append({"symbol": f"PF_{c}USD", "base": c, "route": "open"})
        pd.DataFrame({"t": days, "open": px, "high": px, "low": px, "close": px, "volume": 1.0}).to_parquet(
            data / "kraken_hist/open/candles_1d" / f"PF_{c}USD.parquet")
        pd.DataFrame({"t": hours, "rate": rng.normal(0, 2e-6, len(hours)), "rate_usd": 0.0}).to_parquet(
            data / "kraken_hist/open/funding" / f"PF_{c}USD.parquet")
        a = f"{c}USDT"
        pd.DataFrame({"t": days, "close": px * np.exp(rng.normal(0, 5e-4, len(days))), "volume": 3.0}).to_parquet(
            data / "aster_hist/candles_1d" / f"{a}.parquet")
        pd.DataFrame({"t": evs, "rate": spread_8h * (1 + 0.1 * i) + rng.normal(0, 1e-5, len(evs))}).to_parquet(
            data / "aster_hist/funding" / f"{a}.parquet")
    pd.DataFrame(rows).to_csv(data / "kraken_hist" / "contracts.csv", index=False)
    info = {"symbols": [{"symbol": f"{c}USDT", "baseAsset": c, "quoteAsset": "USDT", "contractType": "PERPETUAL",
                         "status": "TRADING"} for c in coins]}
    return info


def receipts(data, sym):
    for s in sym.aster:
        (data / "aster_hist/receipts" / f"{s}.json").write_text(json.dumps({
            "funding_sha256": r.eea.sha256(data / "aster_hist/funding" / f"{s}.parquet"),
            "candles_sha256": r.eea.sha256(data / "aster_hist/candles_1d" / f"{s}.parquet")}))


class EndToEnd(unittest.TestCase):
    def test_planted_floor_passes_and_reads_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, lane = root / "data", root / "lane"
            info = write_world(data, ["AAA", "BBB", "CCC", "DDD", "EEE"], 0.0001, r.ms(r.START), r.ms(r.END))
            sym = r.manifest(lane, data, info=info)
            self.assertEqual(len(sym), 5)
            receipts(data, sym)
            with mock.patch("lab.prereg.verify", lambda p: None), \
                    mock.patch.object(r, "check_inputs", lambda p=None: []):
                rep = r.run(lane, data)
                self.assertEqual(rep["verdict"], "PASS")
                self.assertEqual(set(rep["primary"]["by_long_venue_trades"]), {"kraken"})
                self.assertEqual(rep["unseen_coins"], 5)                   # synthetic coins are not in R508's table
                self.assertEqual(rep["full_book"]["trades"], rep["primary"]["trades"])
                self.assertGreater(rep["primary"]["ann_1x_pct"], 1)
                with self.assertRaises(SystemExit):
                    r.run(lane, data)

    def test_changed_aster_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, lane = root / "data", root / "lane"
            info = write_world(data, ["AAA", "BBB"], 0.0, r.ms(r.START), r.ms(r.END))
            sym = r.manifest(lane, data, info=info)
            receipts(data, sym)
            pd.DataFrame({"t": [0], "rate": [1.0]}).to_parquet(data / "aster_hist/funding/AAAUSDT.parquet")
            sym = pd.read_csv(lane / "symbols.csv", dtype=str)
            with self.assertRaises(SystemExit):
                r.check_data(lane, data, sym)


if __name__ == "__main__":
    unittest.main()
