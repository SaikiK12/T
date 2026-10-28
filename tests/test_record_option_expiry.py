"""scripts/record_option_expiry.py: the 06:45-10:15 UTC window, one file per snapshot, the caps (offline)."""
import calendar
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import record_option_expiry as oe  # noqa: E402

DAY = calendar.timegm((2026, 10, 29, 0, 0, 0))


def at(h, m=0, s=0):
    return DAY + h * 3600 + m * 60 + s


def chain(n=3):
    return [{"instrument_name": f"BTC-29OCT26-{80000 + 1000 * i}-{cp}", "open_interest": 10.0 + i, "volume_usd": 1.0,
             "mark_iv": 40.0 + i, "mark_price": 0.01, "bid_price": 0.009, "ask_price": 0.011,
             "underlying_price": 81000.0, "underlying_index": "BTC-29OCT26", "estimated_delivery_price": 81010.0}
            for i in range(n) for cp in "CP"]


class WindowTests(unittest.TestCase):
    def test_window_edges(self):
        self.assertFalse(oe.in_window(at(6, 44, 59)))
        self.assertTrue(oe.in_window(at(6, 45)))
        self.assertTrue(oe.in_window(at(8, 0)))
        self.assertTrue(oe.in_window(at(10, 14, 59)))
        self.assertFalse(oe.in_window(at(10, 15)))
        self.assertFalse(oe.in_window(at(23)))


class SnapshotTests(unittest.TestCase):
    def test_a_snapshot_is_one_file_with_the_chain_columns_and_a_second_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertEqual(oe.take(at(8, 0, 0), out, get=lambda c: chain()), 6)
            path = out / "2026-10-29" / "080000.parquet"
            df = pd.read_parquet(path)
            self.assertEqual(list(df.columns), oe.COLS)
            self.assertEqual(set(df.cp), {"C", "P"})
            self.assertTrue((df.t_done >= df.ts).all())
            self.assertEqual(oe.take(at(8, 0, 0), out, get=lambda c: chain()), 0)
            self.assertEqual(len(list(out.rglob("*.parquet"))), 1)

    def test_an_empty_chain_writes_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(oe.take(at(8), Path(d), get=lambda c: []), 0)
            self.assertFalse(list(Path(d).rglob("*")))

    def test_caps(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertEqual(oe.full(out, free_gb=9.0), "")
            self.assertIn("free", oe.full(out, free_gb=oe.MIN_FREE_GB - 0.1))
            (out / "x").mkdir()
            (out / "x" / "big.parquet").write_bytes(b"0" * int(oe.MAX_MB * 1e6))
            self.assertIn("MB", oe.full(out, free_gb=9.0))


class DaemonTests(unittest.TestCase):
    def test_the_loop_writes_inside_the_window_only_and_records_failures(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "o"
            status = Path(d) / "status.json"
            stop = threading.Event()
            times = [at(5), at(8, 0, 5), at(8, 1, 5), at(11)]
            calls, n = [], [0]

            def get(c):
                calls.append(c)
                if len(calls) == 2:
                    raise OSError("boom")
                return chain()

            def clock():                                  # read twice per turn: the turn, then the wait
                i = n[0] // 2
                n[0] += 1
                if i >= len(times):
                    stop.set()
                    return times[-1]
                return times[i]

            stop_wait = stop.wait
            stop.wait = lambda timeout=None: stop_wait(0)
            oe.run(stop, out=out, get=get, every=60, status=status, clock=clock)
            self.assertEqual(calls, ["BTC", "BTC"])                       # two in-window turns, none at 05:00 or 11:00
            self.assertEqual(len(list(out.rglob("*.parquet"))), 1)       # the second one failed
            self.assertIn('"failed": 1', status.read_text())


if __name__ == "__main__":
    unittest.main()
