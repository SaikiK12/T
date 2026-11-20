import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import run_xfund_kokx as r


class Kokx(unittest.TestCase):
    def test_symbol_rule(self):
        bases = {"BTC": "BTC-USD_UM_XPERP-310404", "PEPE": "PEPE-USD_UM_XPERP-310500",
                 "1000SATS": "1000SATS-USD_UM_XPERP-310600", "PAXG": "PAXG-USD_UM_XPERP-1"}
        k = [{"symbol": "PF_XBTUSD", "base": "BTC", "route": "open"},
             {"symbol": "PF_PEPEUSD", "base": "PEPE", "route": "open"},
             {"symbol": "PF_SATSUSD", "base": "SATS", "route": "open"},
             {"symbol": "PF_PAXGUSD", "base": "PAXG", "route": "open"},
             {"symbol": "PF_ZZZUSD", "base": "ZZZ", "route": "open"}]
        t = r.symbol_table(k, bases)
        self.assertEqual(t.to_dict("records"), [
            {"key": "BTC", "kraken": "PF_XBTUSD", "okx": "BTC-USD_UM_XPERP-310404"},
            {"key": "PEPE", "kraken": "PF_PEPEUSD", "okx": "PEPE-USD_UM_XPERP-310500"},
            {"key": "SATS", "kraken": "PF_SATSUSD", "okx": "1000SATS-USD_UM_XPERP-310600"}])

    def test_build_okx(self):
        with tempfile.TemporaryDirectory() as tmp:
            okx = Path(tmp) / "okx"
            (okx / "funding").mkdir(parents=True)
            (okx / "trade_1d").mkdir(parents=True)
            inst = "X-USD_UM_XPERP-1"
            pd.DataFrame({"instId": [inst, inst, "Y"], "fundingTime": [2, 1, 1], "fundingRate": [0.2, 0.1, 9],
                          "realizedRate": 0, "method": "", "formulaType": ""}).to_csv(okx / "funding" / "d1.csv",
                                                                                     index=False)
            pd.DataFrame({"instId": [inst, inst], "fundingTime": [2, 3], "fundingRate": [0.2, 0.3],
                          "realizedRate": 0, "method": "", "formulaType": ""}).to_csv(okx / "funding" / "d2.csv",
                                                                                     index=False)
            pd.DataFrame({"instId": [inst], "ts": [5], "o": 1, "h": 1, "l": 1, "c": [1.5], "vol_quote": [7.0]}).to_csv(
                okx / "trade_1d" / "d1.csv", index=False)
            out = Path(tmp) / "built"
            r.build_okx(pd.DataFrame({"key": ["X"], "kraken": ["PF_XUSD"], "okx": [inst]}), okx, out)
            f = pd.read_parquet(out / "funding" / f"{inst}.parquet")
            self.assertEqual(f.t.tolist(), [1, 2, 3])               # sorted, the overlapping print kept once
            self.assertEqual(f.rate.tolist(), [0.1, 0.2, 0.3])
            p = pd.read_parquet(out / "prices" / f"{inst}.parquet")
            self.assertEqual(p.close.tolist(), [1.5])


if __name__ == "__main__":
    unittest.main()
