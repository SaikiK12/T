import csv
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from lab.equation_data import load_panel, parent_states
from lab.equations import HOUR
from tests.test_equations import toy_panel


class EquationDataTests(unittest.TestCase):
    def test_primary_parent_does_not_use_the_last_future_traded_bar(self):
        p = toy_panel(days=80)
        x = np.exp(np.cumsum(np.random.default_rng(9).normal(0, .001, len(p.times))))
        p.prices[:, 0, 0] *= x
        p.prices[:, 0, 1] *= x
        p.rates[:, 0, 1] = .00003
        p.settlement[:] = True
        p.fresh[50*24, 0] = False
        a, _ = parent_states(p, int(p.times[0]), int(p.times[-1]))
        p.fresh[50*24+1:] = False
        b, _ = parent_states(p, int(p.times[0]), int(p.times[-1]))
        np.testing.assert_array_equal(a[:51], b[:51])

    def test_hour_start_shift_and_missing_settlement_are_not_silently_repaired(self):
        t0 = 1735689600000
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            table = root / "symbols.csv"
            table.write_text("key,binance,mexc,lighter\nTOYUSDT,TOYUSDT,TOY_USDT,TOY\n")
            meta = {"mexc": [{"symbol": "TOY_USDT", "type": 1, "settleCoin": "USDT", "contractSize": .1,
                               "volUnit": 1, "minVol": 1}],
                    "lighter": [{"symbol": "TOY", "supported_size_decimals": 2,
                                  "min_base_amount": .01, "min_quote_amount": 1}]}
            for venue in ("mexc", "lighter"):
                (root/(venue+"_contracts_current.json")).write_text(json.dumps(meta[venue]))
                for kind in ("prices", "funding"):
                    (root/venue/kind).mkdir(parents=True)
                sym = "TOY_USDT" if venue == "mexc" else "TOY"
                vol = "vol" if venue == "mexc" else "volume"
                pd.DataFrame({"t": t0+np.arange(24)*HOUR, "close": np.arange(24)+100., vol: 1.}).to_parquet(
                    root/venue/"prices"/(sym+".parquet"), index=False)
                hrs = [0, 8, 24] if venue == "mexc" else list(range(1, 25))
                pd.DataFrame({"t": t0+np.array(hrs)*HOUR, "rate": .0001,
                              "cycle_h": 8. if venue == "mexc" else 1.}).to_parquet(
                    root/venue/"funding"/(sym+".parquet"), index=False)
            p, coverage = load_panel(root, table, t0, t0+24*HOUR)
            self.assertTrue(np.isnan(p.prices[0]).all())
            np.testing.assert_array_equal(p.prices[1, 0], [100, 100])
            self.assertTrue(p.funding_ok[1:9, 0, 0].all())
            self.assertFalse(p.funding_ok[16, 0, 0])
            self.assertTrue(p.funding_ok[24, 0, 0])
            self.assertEqual(p.rates[16, 0, 0], 0)  # stored 0 carries UNKNOWN flag
            self.assertFalse(coverage["historical_rule_vintages"])
            self.assertEqual(coverage["metadata_admissible_pairs"], 1)
            path = root/"mexc/funding/TOY_USDT.parquet"
            frame = pd.read_parquet(path)
            frame["cycle_h"] = [8., 8., 16.]
            frame.to_parquet(path, index=False)
            changed, _ = load_panel(root, table, t0, t0+24*HOUR)
            self.assertFalse(changed.funding_ok[16, 0, 0])
            self.assertFalse(changed.funding_ok[23, 0, 0])


if __name__ == "__main__":
    unittest.main()
