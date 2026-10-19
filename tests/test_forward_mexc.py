"""Forward-loader/scorer tests use invented feeds and temporary journals only."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from scripts import forward_mexc as fm


class ForwardMexcTests(unittest.TestCase):
    def state(self, now_hour=50, missing=None, fail=False):
        t0, H = fm.ft.FWD_START, fm.H
        rows = [{"t": t0 + h * H, "symbol": s, "rank": rank,
                 **{k: (0 if k == "tvc" and s == "BTCUSDT" and h in (22, 23) else 7)
                    for k in fm.ft.CELLS}}
                for h in range(49) for s, rank in (("BTCUSDT", 1), ("ETHUSDT", 2))]
        sig = pd.DataFrame(rows)
        ticks = pd.DataFrame({"t": t0 + np.arange(49) * H})
        table = pd.DataFrame({"symbol": ["BTC_USDT", "ETH_USDT"], "type": [1, 1],
                              "taker": [0.0008, 0.0008], "maker": [0.0006, 0.0006]})
        calls = []

        def prices(symbol, start, end):
            calls.append((start, end))
            if fail:
                raise fm.mexc.MexcError("invented feed failure")
            tt = np.arange(start, end, H)
            frame = pd.DataFrame({"t": tt, "close": np.full(len(tt), 100.0)})
            if missing is not None and symbol == "BTC_USDT":
                frame = frame[frame.t != t0 + missing * H]
            return frame

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(fm.ft, "read", side_effect=lambda n: sig if n == "signals.csv" else ticks))
            stack.enter_context(mock.patch.object(fm.mexc, "contracts", return_value=table))
            stack.enter_context(mock.patch.object(fm.live, "tradfi", return_value=set()))
            stack.enter_context(mock.patch.object(fm.mexc, "klines_cached", side_effect=prices))
            stack.enter_context(mock.patch.object(fm.mexc, "funding_history", return_value=pd.DataFrame(columns=["t", "rate"])))
            stack.enter_context(mock.patch.object(fm.time, "time", return_value=(t0 + now_hour * H + H // 2) / 1000))
            state = fm.load()
        return state, calls

    def test_open_final_bar_cannot_complete_a_day(self):
        before, calls = self.state(now_hour=24)
        after, _ = self.state(now_hour=25)
        self.assertEqual(before["D"], 0)
        self.assertEqual(after["D"], 1)
        self.assertTrue(all(end == fm.ft.FWD_START + 24 * fm.H for _, end in calls))

    def test_delayed_coverage_is_grouped_by_entry_day_and_journal_is_idempotent(self):
        state, _ = self.state(missing=24)
        # One entry succeeds at 23:00, the other is unavailable at midnight.
        # Zero targets isolate coverage from missing-price accounting.
        books = {"B": (np.zeros((48, 2)), fm.ft.BOOKS["B"])}
        with tempfile.TemporaryDirectory() as d:
            journal = Path(d)
            fm.score(state, books, journal, ref=None)
            path = journal / "tickets.csv"
            original = path.read_bytes()
            tickets = pd.read_csv(path)
            np.testing.assert_allclose(tickets.coverage, [1.0, 0.0])
            fm.score(state, books, journal, ref=None)
            self.assertEqual(path.read_bytes(), original)

    def test_feed_failure_aborts_before_scoring(self):
        with self.assertRaises(SystemExit):
            self.state(fail=True)

    def test_ambiguous_mapping_aborts_before_price_fetches(self):
        collision = {"BTCUSDT": "ONE_USDT", "ETHUSDT": "ONE_USDT"}
        with mock.patch.object(fm.mexc, "map_symbols", return_value=collision):
            with self.assertRaisesRegex(SystemExit, "ambiguous"):
                self.state()


if __name__ == "__main__":
    unittest.main()
