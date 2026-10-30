"""Synthetic delayed-entry checks; no source journal or network is used."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from lab import slices
from scripts import forward_delayed as fd


class DelayedSlicesTests(unittest.TestCase):
    def test_backlogged_signals_keep_each_slice_at_a_shared_entry(self):
        ind = np.zeros((8, 2), dtype=bool)
        ind[0, 0] = ind[1, 0] = ind[2, 1] = True
        lag = np.array([3, 2, 1, 1, 1, 1, 1, 1])
        shifted = fd.shift_rows(ind, np.ones_like(ind), lag)
        np.testing.assert_array_equal(shifted[3], [2, 1])
        self.assertEqual(shifted.sum(), 3)
        # Every submitted slice keeps the frozen holding period from entry.
        p = slices.positions(shifted, 3, 0, 8, 0.1, -1)
        np.testing.assert_allclose(p[3:6], [[-0.2, -0.1]] * 3)
        np.testing.assert_array_equal(p[6:], 0)

    def test_entry_eligibility_rejects_all_colliding_slices(self):
        ind = np.zeros((5, 2), dtype=bool)
        ind[0] = ind[1] = True
        elig = np.ones_like(ind)
        elig[3, 0] = False
        shifted = fd.shift_rows(ind, elig, np.array([3, 2, 1, 1, 1]))
        np.testing.assert_array_equal(shifted[3], [0, 2])
        self.assertEqual(shifted.sum(), 2)

    def test_fixed_one_bar_delay_is_unchanged_and_drops_pending_entries(self):
        ind = np.array([[1, 0], [1, 1], [0, 1], [1, 1]], dtype=bool)
        elig = np.ones_like(ind)
        elig[2, 0] = False
        expected = np.array([[0, 0], [1, 0], [0, 1], [0, 1]])
        np.testing.assert_array_equal(fd.shift_rows(ind, elig, np.ones(4, int)), expected)

    def test_realized_lag_scoring_counts_both_backlogged_entries_once(self):
        # Two signal bars are first observed at 03:12. Both slices enter at
        # the 04:00 close (row 3), not one slice for the entire backlog.
        t0, H = fd.ON_TIME, fd.H
        syms = ["BTCUSDT", "ETHUSDT"]
        sig = pd.DataFrame([
            {"t": t0 + h * H, "symbol": s, "rank": j + 1,
             **{k: (0 if j == 0 and h < 2 and k == "tvc" else 7) for k in fd.ft.CELLS}}
            for h in range(25) for j, s in enumerate(syms)
        ])
        ready = t0 + (np.arange(25) + 1) * H + 12 * 60_000
        ready[:2] = t0 + 3 * H + 12 * 60_000
        ticks = pd.DataFrame({"t": t0 + np.arange(25) * H,
                              "run_at": pd.to_datetime(ready, unit="ms", utc=True).astype(str)})
        tt = t0 + np.arange(26) * H
        close = np.full((26, 2), 100.0)
        # One realized -10% move in the short coin after the common entry.
        close[4:, 0] = 90.0
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            journal = Path(d)
            stack.enter_context(mock.patch.object(fd, "J", journal))
            stack.enter_context(mock.patch.object(fd.ft, "FWD_START", t0))
            stack.enter_context(mock.patch.object(fd.ft, "read", side_effect=lambda name: {
                "signals.csv": sig, "ticks.csv": ticks}.get(name, pd.DataFrame())))
            stack.enter_context(mock.patch.object(fd.ft, "funding_event", return_value=np.zeros((26, 2))))
            fd.score(tt, syms, close)
            original = (journal / "tickets.csv").read_bytes()
            tickets = pd.read_csv(journal / "tickets.csv").set_index("book")
            u = 1 / (fd.ft.HOLD * fd.ft.K)
            cost = 4 * u * 0.0006  # two short slices and their equal-notional long hedge
            # -2u short plus +u on each of two hedge coins earns +0.1u.
            self.assertAlmostEqual(tickets.loc["A_rt", "gross"], 0.2 * u)
            self.assertAlmostEqual(tickets.loc["A_rt", "gross_exposure"], 2 * u * 21 / 24)
            self.assertAlmostEqual(tickets.loc["A_rt", "net"], 0.1 * u - cost)
            self.assertAlmostEqual(tickets.loc["A_rt", "net_2x"], 0.1 * u - 2 * cost)
            self.assertAlmostEqual(tickets.loc["A_rt", "net_3x"], 0.1 * u - 3 * cost)
            self.assertAlmostEqual(tickets.loc["A", "net"], tickets.loc["A_rt", "net"])
            fd.score(tt, syms, close)
            self.assertEqual((journal / "tickets.csv").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
