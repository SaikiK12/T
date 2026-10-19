"""Carry forward integrity tests use synthetic exchange responses and temporary data only."""
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from scripts import forward_carry as fc


class ForwardCarryTests(unittest.TestCase):
    def tickets(self, days=90, invested=30):
        date = pd.date_range("2026-10-20", periods=days, freq="D").strftime("%Y-%m-%d")
        wave = np.sin(np.arange(days) * 1.7) * 0.00045
        net = 0.001 + wave
        opened = np.arange(days) < invested
        return pd.DataFrame({"day": date, "kind": "ontime", "net": net,
                             "avg_open": np.where(opened, 1.0, 0.0)})

    def test_decision_waits_for_complete_first_90_days_and_ignores_later_returns(self):
        x = self.tickets(89)
        pending = fc.decision(x)
        self.assertEqual(pending["decision"], "PENDING")
        self.assertEqual(pending["missing_days"], 1)
        full = self.tickets(100)
        result = fc.decision(full)
        self.assertEqual(result["decision"], "PASS")
        full.loc[full.index[-10:], "net"] = -0.1
        self.assertEqual(fc.decision(full)["decision"], "PASS")
        self.assertEqual(result["days"], 90)

    def test_inconclusive_and_fail_follow_frozen_order(self):
        few = fc.decision(self.tickets(90, invested=19))
        self.assertEqual(few["decision"], "INCONCLUSIVE")
        failed = self.tickets(90, invested=25)
        failed.loc[:24, "net"] = -0.001
        self.assertEqual(fc.decision(failed)["decision"], "FAIL")

    def test_decision_rejects_duplicate_bad_kind_and_nonfinite_tickets(self):
        x = self.tickets()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            fc.decision(pd.concat([x, x.iloc[[0]]], ignore_index=True))
        wrong = x.copy()
        wrong.loc[wrong.index[0], "kind"] = "replay"
        with self.assertRaisesRegex(ValueError, "cutoff"):
            fc.decision(wrong)
        bad = x.copy()
        bad.loc[0, "net"] = np.nan
        with self.assertRaisesRegex(ValueError, "Invalid"):
            fc.decision(bad)

    def test_fetch_fails_closed_when_any_stream_fails(self):
        def response(key):
            if key == "bad":
                raise fc.live.LiveError("synthetic outage")
            return pd.DataFrame()

        with self.assertRaisesRegex(SystemExit, "bad"):
            fc.fetch(response, ["good", "bad"])

    def test_fetch_preserves_successful_empty_streams(self):
        empty = pd.DataFrame(columns=["t", "rate"])
        got = fc.fetch(lambda key: empty, ["no_settlements"])
        self.assertIs(got["no_settlements"], empty)

    def test_grid_clamps_to_closed_r200_hour(self):
        t0, H = fc.ft.FWD_START, fc.H
        sig = pd.DataFrame({"t": t0 + np.arange(33) * H,
                            "symbol": ["BTCUSDT"] * 33, "rank": np.ones(33)})
        ticks = pd.DataFrame({"t": t0 + np.arange(33) * H})
        now = (t0 + 32 * H + H // 2) / 1000
        with (mock.patch.object(fc.ft, "read", side_effect=lambda name: sig if name == "signals.csv" else ticks),
              mock.patch.object(fc.time, "time", return_value=now)):
            g = fc.journal_grid()
        self.assertEqual(g["last"], t0 + 31 * H)
        self.assertEqual(g["T"], 32)
        self.assertEqual(g["tt"][-1], t0 + 31 * H)
        self.assertTrue(g["elig"][fc.LOOK + 31, 0])

    def test_grid_rejects_empty_r200_journal(self):
        with mock.patch.object(fc.ft, "read", return_value=pd.DataFrame()):
            with self.assertRaisesRegex(SystemExit, "empty"):
                fc.journal_grid()

    def test_incomplete_next_basis_defers_the_whole_day(self):
        t0, H = fc.ft.FWD_START, fc.H
        g = {"T": 49, "tt": t0 + np.arange(121) * H - fc.LOOK * H}
        v = {"elig": np.ones((len(g["tt"]), 2), bool), "has": np.ones(2, bool)}
        out = {name: np.zeros((48, 5)) for name in fc.VARIANTS}
        out["2x"][26, 0] = np.nan
        rows, daily = fc.day_tickets(g, "BIN", v, out, set())
        self.assertEqual([row["day"] for row in rows], ["2026-10-01"])
        self.assertTrue(np.isfinite(daily[0]))
        self.assertTrue(np.isnan(daily[1]))


if __name__ == "__main__":
    unittest.main()
