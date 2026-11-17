import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts import run_carrycost_hist_v2 as c


def _gate_hour(day, ask=101.0):
    h = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
    lines = [f"{h},set,99,1000,1,0", f"{h},set,{ask},-1000,1,0"]
    return gzip.compress("\n".join(lines).encode())


class GateMetricsTest(unittest.TestCase):
    def test_reduces_an_hour_to_side_costs(self):
        met = c.gate_metrics(_gate_hour("2023-06-01"), "2023-06-01", mult=1.0)
        self.assertEqual(set(met), {"buy", "sell"})
        self.assertEqual(len(met["buy"]), len(c.HOWS) * len(c.SIZES))
        # Mid 100, ask 101 holds $101k: every size fills at 100 bp, every minute (the book never changes).
        self.assertAlmostEqual(met["buy"]["median_1000"], 100.0)
        self.assertAlmostEqual(met["sell"]["snap0_250"], 100.0)

    def test_reuses_and_releases_r499_raw_copy(self):
        with tempfile.TemporaryDirectory() as t:
            old, new = Path(t) / "old", Path(t) / "new"
            (old / "gate").mkdir(parents=True)
            raw = old / "gate" / "MTL_USDT-2023060100.csv.gz"
            raw.write_bytes(_gate_hour("2023-06-01", ask=102.0))
            sess = mock.Mock()
            with mock.patch.object(c, "OLD", old), mock.patch.object(c, "DATA", new):
                res = c.fetch_gate("MTL_USDT", "2023-06-01", sess, {"MTL_USDT": 1.0})
            sess.get.assert_not_called()
            self.assertFalse(raw.exists())
            self.assertEqual(res["bytes"], 0)
            met = json.loads((new / "gate" / "MTL_USDT-20230601.json").read_text())
            self.assertAlmostEqual(met["buy"]["median_1000"], (102 / 100.5 - 1) * 1e4, places=4)

    def test_cut_short_copy_is_fetched_again(self):
        with tempfile.TemporaryDirectory() as t:
            old, new = Path(t) / "old", Path(t) / "new"
            (old / "gate").mkdir(parents=True)
            (old / "gate" / "MTL_USDT-2023060100.csv.gz").write_bytes(_gate_hour("2023-06-01")[:10])
            sess = mock.Mock()
            sess.get.return_value = mock.Mock(status_code=200, content=_gate_hour("2023-06-01"))
            with mock.patch.object(c, "OLD", old), mock.patch.object(c, "DATA", new):
                res = c.fetch_gate("MTL_USDT", "2023-06-01", sess, {"MTL_USDT": 1.0})
            sess.get.assert_called_once()
            self.assertGreater(res["bytes"], 0)


class BinanceProxyTest(unittest.TestCase):
    def test_truncates_r499_samples_to_15_minutes(self):
        book = [[[99.0, 100.0]], [[101.0, 100.0]]]
        with tempfile.TemporaryDirectory() as t:
            old, new = Path(t) / "old", Path(t) / "new"
            (old / "binance").mkdir(parents=True)
            (old / "binance" / "XUSDT-2023-06.json.gz").write_bytes(gzip.compress(json.dumps([book] * 60).encode()))
            with mock.patch.object(c, "OLD", old), mock.patch.object(c, "DATA", new):
                c.fetch_binance("XUSDT", "2023-06", mock.Mock())
                s = c._binance_samples("XUSDT", "2023-06")
        self.assertEqual(len(s), c.BIN_MINUTES)

    def test_eight_of_fifteen(self):
        book = ([(99.0, 100.0)], [(101.0, 100.0)])
        empty = ([], [])
        self.assertAlmostEqual(c.event_cost([book] * 8 + [empty] * 7, "buy", 100, "median", c.BIN_MIN), 100.0)
        self.assertIsNone(c.event_cost([book] * 7 + [empty] * 8, "buy", 100, "median", c.BIN_MIN))


if __name__ == "__main__":
    unittest.main()
