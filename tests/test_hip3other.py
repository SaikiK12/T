"""R476 hip3other_v1: universe naming across deployers and R475's frozen book on a two-dex synthetic market."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import fetch_hip3other as fo  # noqa: E402
import run_hip3other as ro  # noqa: E402
from test_hip3stock import bill, world  # noqa: E402


class UniverseTest(unittest.TestCase):
    def test_every_dex_but_xyz_named_by_dex_and_one_yahoo_call_per_stock(self):
        metas = {"flx": [{"name": "flx:AAA", "isDelisted": True, "maxLeverage": 10}, {"name": "flx:SPY"}],
                 "cash": [{"name": "cash:AAA", "growthMode": "enabled", "maxLeverage": 20}]}

        def post(body):
            if body["type"] == "perpDexs":
                return [None, {"name": "xyz"}, {"name": "flx"}, {"name": "cash"}]
            return {"universe": metas[body["dex"]]}

        yahoo = {"AAA": {"instrumentType": "EQUITY", "currency": "USD", "exchangeName": "NMS", "longName": "A, Inc."},
                 "SPY": {"instrumentType": "ETF", "currency": "USD", "exchangeName": "PCX"}}
        with mock.patch.object(fo.fs, "post", side_effect=post), \
                mock.patch.object(fo.fs, "yahoo_meta", side_effect=lambda t: yahoo[t]) as ym, \
                mock.patch.object(fo.time, "sleep"):
            uni = fo.universe()
        self.assertEqual(uni["ticker"].tolist(), ["flx_AAA", "flx_SPY", "cash_AAA"])
        self.assertEqual(uni["equity"].tolist(), [1, 0, 1])
        self.assertEqual(uni["delisted"].tolist(), [1, 0, 0])
        self.assertEqual(uni["growth"].tolist(), ["", "", "enabled"])
        self.assertEqual(ym.call_count, 2)
        self.assertEqual(uni["y_name"].iloc[0], "A  Inc.")


class RunTest(unittest.TestCase):
    def test_run_books_two_deployers_and_reports_by_dex(self):
        with tempfile.TemporaryDirectory() as d:
            data, lane = Path(d) / "data", Path(d) / "lane"
            (data / "xyz").mkdir(parents=True)
            (data / "yahoo").mkdir(parents=True)
            rows = []
            for t, rate, mult, end in [("flx_AAA", 0.30, 1.0, "2026-06-20"), ("cash_AAA", 0.20, 1.0, "2026-11-13"),
                                       ("cash_GOLD", 0.40, 40.0, "2026-11-13")]:
                s, c, f = world(rate=rate, perp_mult=mult)
                cut = hs_ms(end)
                c, f = c[c["open_ms"] < cut], f[f["time"] < cut]
                f.to_csv(data / "xyz" / f"{t}_funding.csv", index=False)
                c.to_csv(data / "xyz" / f"{t}_4h.csv", index=False)
                s.to_parquet(data / "yahoo" / f"{t}.parquet", index=False)
                rows.append({"coin": t.replace("_", ":"), "ticker": t, "equity": 1, "delisted": int(end < "2026-11"),
                             "growth": "enabled", "max_lev": 10})
            pd.DataFrame(rows).to_csv(data / "universe.csv", index=False)
            pd.DataFrame({"date": bill().index, "close": 4.0, "adjclose": 4.0}).to_parquet(
                data / "yahoo" / "IRX.parquet", index=False)
            files = {str(p.relative_to(data)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(data.rglob("*")) if p.is_file()}
            (data / "manifest.json").write_text(json.dumps({"files": files}))
            state = ro.run(lane, data, check=False)
            s = json.loads((lane / "results" / "summary.json").read_text())
            self.assertEqual(s["registry"], "R476")
            self.assertEqual(s["state"], state)
            self.assertEqual(s["markets"], ["cash_AAA", "flx_AAA"])
            dex = s["variants"]["decide"]["by_dex"]
            self.assertEqual(dex["flx"]["why"], {"gone": 1})
            self.assertIn("end", dex["cash"]["why"])
            self.assertGreater(s["variants"]["decide"]["A"]["ann_funding_pts"], 0)


def hs_ms(day):
    return ro.hs.day_ms(day)


if __name__ == "__main__":
    unittest.main()
