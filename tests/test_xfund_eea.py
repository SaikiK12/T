import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_xfund_eea as r

H = 3_600_000
DAY = 24 * H


class Symbols(unittest.TestCase):
    def test_rule(self):
        k = [{"symbol": "PF_XBTUSD", "base": "BTC", "route": "open"},
             {"symbol": "PF_PEPEUSD", "base": "PEPE", "route": "open"},
             {"symbol": "PF_PAXGUSD", "base": "PAXG", "route": "open"},          # gold token: left out
             {"symbol": "PF_AMDUSD", "base": "AMD", "route": "open"},            # equity: left out
             {"symbol": "PF_ABCUSD", "base": "ABC", "route": "reserved"},        # long tail: never read
             {"symbol": "PF_ZZZUSD", "base": "ZZZ", "route": "open"},            # not on Hyperliquid
             {"symbol": "PF_SHIBUSD", "base": "SHIB", "route": "open"}]
        hl = {"BTC", "kPEPE", "PAXG", "AMD", "ABC", "SHIB", "kSHIB"}
        t = r.symbol_table(k, hl)
        self.assertEqual(t.to_dict("records"), [
            {"key": "BTC", "kraken": "PF_XBTUSD", "hyperliquid": "BTC"},
            {"key": "PEPE", "kraken": "PF_PEPEUSD", "hyperliquid": "kPEPE"},
            {"key": "SHIB", "kraken": "PF_SHIBUSD", "hyperliquid": "SHIB"}])   # no multiplier prefix wins
        self.assertEqual(r.norm("1000000MOG"), "MOG")
        self.assertEqual(r.norm("1INCH"), "1INCH")


def write_world(data, coins, spread_per_hour, start, end, seed=0):
    """Kraken and Hyperliquid trading the same coins; Hyperliquid's funding pays `spread_per_hour` more."""
    rng = np.random.default_rng(seed)
    (data / "kraken_hist/open/candles_1d").mkdir(parents=True)
    (data / "kraken_hist/open/funding").mkdir(parents=True)
    (data / "hyperliquid/candles_1d").mkdir(parents=True)
    (data / "hyperliquid/funding").mkdir(parents=True)
    days = np.arange(start - 40 * DAY, end + 2 * DAY, DAY)
    hours = np.arange(start - 40 * DAY, end + 2 * DAY, H)
    rows = []
    for i, c in enumerate(coins):
        px = 50 * np.exp(np.cumsum(rng.normal(0, 0.03, len(days))))
        kc, hc = f"PF_{c}USD", c
        rows.append({"symbol": kc, "base": c, "route": "open"})
        pd.DataFrame({"t": days, "open": px, "high": px, "low": px, "close": px * np.exp(rng.normal(0, 5e-4, len(days))),
                      "volume": 1.0}).to_parquet(data / "kraken_hist/open/candles_1d" / f"{kc}.parquet")
        pd.DataFrame({"t": days, "open": px, "high": px, "low": px, "close": px, "volume": 2.0,
                      "trades": 1}).to_parquet(data / "hyperliquid/candles_1d" / f"{hc}.parquet")
        pd.DataFrame({"t": hours, "rate": rng.normal(0, 2e-6, len(hours)), "rate_usd": 0.0}).to_parquet(
            data / "kraken_hist/open/funding" / f"{kc}.parquet")
        pd.DataFrame({"rate": spread_per_hour * (1 + 0.1 * i) + rng.normal(0, 2e-6, len(hours)), "premium": 0.0,
                      "t": hours}).to_parquet(data / "hyperliquid/funding" / f"{hc}.parquet")
    pd.DataFrame(rows).to_csv(data / "kraken_hist" / "contracts.csv", index=False)


class EndToEnd(unittest.TestCase):
    def run_lane(self, spread):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        data, lane = root / "data", root / "lane"
        write_world(data, ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"], spread, r.ms(r.START), r.ms(r.END))
        sym = r.manifest(lane, data)
        self.assertEqual(len(sym), 6)
        with mock.patch("lab.prereg.verify", lambda p: None), mock.patch.object(r, "check_inputs", lambda p=None: []):
            rep = r.run(lane, data)
        return rep, lane, data

    def test_planted_spread_passes_and_reads_once(self):
        rep, lane, data = self.run_lane(0.0000125)             # Hyperliquid's floor, about 11%/yr
        self.assertEqual(rep["verdict"], "PASS")
        self.assertGreater(rep["primary"]["ann_1x_pct"], 2)
        self.assertEqual(set(rep["primary"]["by_long_venue_trades"]), {"kraken"})
        self.assertEqual(rep["data_files_verified"], 24)
        self.assertAlmostEqual(rep["funding_profile"]["AAA"]["hyperliquid_ann_pct"], 10.95, delta=0.2)
        with mock.patch("lab.prereg.verify", lambda p: None), mock.patch.object(r, "check_inputs", lambda p=None: []):
            with self.assertRaises(SystemExit):
                r.run(lane, data)

    def test_no_spread_does_not_pass(self):
        rep, _, _ = self.run_lane(0.0)
        self.assertNotEqual(rep["verdict"], "PASS")

    def test_changed_data_file_is_refused(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        data, lane = root / "data", root / "lane"
        write_world(data, ["AAA", "BBB"], 0.0, r.ms(r.START), r.ms(r.END))
        r.manifest(lane, data)
        f = data / "hyperliquid/funding/AAA.parquet"
        pd.DataFrame({"rate": [1.0], "premium": [0.0], "t": [0]}).to_parquet(f)
        with self.assertRaises(SystemExit):
            r.check_data(lane, data)
        (lane / "PREREG.sha256").write_text("x")
        with self.assertRaises(SystemExit):                     # no manifest after the freeze
            r.manifest(lane, data)


if __name__ == "__main__":
    unittest.main()
