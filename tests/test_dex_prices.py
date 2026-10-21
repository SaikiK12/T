import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from scripts import record_dex_prices as rd


def pair(sym, px, liq, vol, chain="solana", addr="P1", token="T1"):
    return {"chainId": chain, "dexId": "raydium", "pairAddress": addr, "baseToken": {"symbol": sym, "address": token},
            "priceUsd": str(px), "liquidity": {"usd": liq}, "volume": {"h24": vol, "h1": vol / 24, "m5": 1.0},
            "txns": {"h1": {"buys": 3, "sells": 4}}, "priceChange": {"m5": 0.1, "h1": -0.2}}


class DexPricesTest(unittest.TestCase):
    def test_split(self):
        self.assertEqual(rd.split("1000PEPE_USDT"), ("PEPE", 1000))
        self.assertEqual(rd.split("1000000BABYDOGE_USDT"), ("BABYDOGE", 1000000))
        self.assertEqual(rd.split("BTC_USDT"), ("BTC", 1))
        self.assertEqual(rd.split("1INCH_USDT"), ("1INCH", 1))

    def test_best_pool_rejects_impostors_and_prefers_close_prices(self):
        pairs = [pair("WIF", 0.0013, 1e5, 1e6, addr="fake"),                 # same ticker, wrong price
                 pair("$WIF", 0.2125, 6e6, 3e5, addr="real"),
                 pair("WIF", 0.2160, 9e8, 2e4, addr="inflated"),             # 1.6% off: second tier only
                 pair("$WIF", 0.2124, 4e4, 9e5, addr="shallow"),             # under the liquidity floor
                 pair("WIFE", 0.2125, 6e6, 9e6, addr="other")]
        self.assertEqual(rd.best_pool(pairs, "WIF", 1, 0.2125)["pairAddress"], "real")
        self.assertEqual(rd.best_pool(pairs[2:3], "WIF", 1, 0.2125)["pairAddress"], "inflated")
        self.assertIsNone(rd.best_pool(pairs[:1], "WIF", 1, 0.2125))
        self.assertEqual(rd.best_pool([pair("PEPE", 4.65e-6, 3e7, 2e6)], "PEPE", 1000, 4.65e-3)["pairAddress"], "P1")

    def test_map_then_snapshot_joins_the_perp_price(self):
        tick = pd.DataFrame([{"symbol": "WIF_USDT", "fairPrice": 0.2125, "lastPrice": 0.2126, "bid1": 0.2125,
                              "ask1": 0.2127, "timestamp": 1_792_600_000_000},
                             {"symbol": "ZZZ_USDT", "fairPrice": 1.0, "lastPrice": 1.0, "bid1": 1.0, "ask1": 1.0,
                              "timestamp": 1_792_600_000_000}])

        def get(url):
            if "/search?q=WIF" in url or "/search?q=%24WIF" in url:
                return {"pairs": [pair("$WIF", 0.2125, 6e6, 3e5, addr="real", token="EKp")]}
            if "/pairs/solana/real" in url:
                return {"pairs": [pair("$WIF", 0.2130, 6e6, 3e5, addr="real", token="EKp")]}
            return {"pairs": []}

        with mock.patch.object(rd, "data", mock.Mock(ROOT=Path(tempfile.gettempdir()) / "no_such_lab_data")):
            mp = rd.build_map(get=get, tick=tick, pace=0)
        self.assertEqual(list(mp.symbol), ["WIF_USDT"])
        self.assertEqual(mp.route.iloc[0], "reserved")                  # no Binance klines in the fake root
        df = rd.snapshot(mp, get=get, tick=tick, pace=0)
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df.price_usd.iloc[0], 0.2130)
        self.assertAlmostEqual(df.mexc_fair.iloc[0], 0.2125)
        self.assertEqual(list(df.columns), rd.COLS)

    def test_stale_map_starts_one_background_rebuild(self):
        with tempfile.TemporaryDirectory() as d:
            mp = Path(d) / "map.csv"
            popen = mock.Mock()
            self.assertIsNone(rd.refresh_if_stale(mp, popen=popen))                  # no map: nothing to refresh
            mp.write_text("symbol\n")
            day = 86400
            os.utime(mp, (time.time() - day,) * 2)
            self.assertIsNone(rd.refresh_if_stale(mp, popen=popen))
            os.utime(mp, (time.time() - 8 * day,) * 2)
            rd.refresh_if_stale(mp, popen=popen)
            rd.refresh_if_stale(mp, popen=popen)                                     # the lock holds the second
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(popen.call_args.args[0][-1], "map")
            self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_snapshots_of_an_hour_share_one_file_sealed_when_the_hour_ends(self):
        snap = pd.DataFrame({"ts": [1], "symbol": ["WIF_USDT"]})
        h = 1_792_598_400                                               # 2026-10-21 16:00 UTC
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rd.add(snap, h + 60, out)
            rd.add(snap, h + 360, out)
            self.assertEqual(rd.seal(h + 3000, out), [])                # the hour is still open
            self.assertEqual(rd.seal(h + 3600, out), [out / "2026-10-21/16.parquet"])
            self.assertEqual(len(pd.read_parquet(out / "2026-10-21/16.parquet")), 2)
            self.assertEqual(list(out.glob("*/*.part")), [])
            rd.add(snap, h + 120, out)                                  # a late .part for a written hour is merged
            rd.seal(h + 7200, out)
            self.assertEqual(len(pd.read_parquet(out / "2026-10-21/16.parquet")), 3)

    def test_run_polls_until_stopped_and_writes_status(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            pd.DataFrame({"symbol": ["WIF_USDT"]}).to_csv(out / "map.csv", index=False)
            stop, calls = mock.Mock(), []
            stop.is_set.side_effect = [False, False, True]
            snap = pd.DataFrame({"ts": [1], "symbol": ["WIF_USDT"]})
            with mock.patch.object(rd, "snapshot", lambda mp, get: calls.append(len(mp)) or snap), \
                    mock.patch.object(rd, "refresh_if_stale"):
                rd.run(stop, out=out, status=out / "status.json")
            self.assertEqual(calls, [1, 1])
            self.assertEqual(len(pd.read_parquet(next(out.glob("*/*.parquet.part")))), 2)
            self.assertEqual(json.loads((out / "status.json").read_text())["pools_read"], 1)


if __name__ == "__main__":
    unittest.main()
