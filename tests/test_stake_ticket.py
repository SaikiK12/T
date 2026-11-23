"""The stake ticket: open pairs, R526's live filters, the margin split, and the DRY RUN header."""
import math
import unittest

import pandas as pd

from lab import margin
from scripts import stake_ticket as st


def tk(action, coin, lo="kraken", hi="hyperliquid", book="A"):
    return {"book": book, "action": action, "coin": coin, "long": lo, "short": hi}


class FakeLane:
    venues = ["kraken", "hyperliquid"]

    def __init__(self, tickets):
        self.tickets = tickets

    def journal(self):
        return [], self.tickets, []

    def table(self):
        return pd.DataFrame({"key": ["NEIRO", "PEPE", "THIN"], "kraken": ["PF_NEIROUSD", "PF_PEPEUSD", "PF_THINUSD"],
                             "hyperliquid": ["NEIRO", "kPEPE", "THIN"]})


def book(mid, depth=1e6, spread_bp=10):
    h = mid * spread_bp / 2e4
    return [[mid - h, depth / mid]], [[mid + h, depth / mid]]


class Ticket(unittest.TestCase):
    def test_open_pairs_replays_entries_and_exits(self):
        t = [tk("enter", "A"), tk("enter", "B"), tk("inherit", "B"), tk("exit", "A"), tk("enter", "C"),
             tk("drop", "C"), tk("enter", "D", book="B")]
        self.assertEqual(st.open_pairs(t), [("B", "kraken", "hyperliquid")])

    def test_agree_divides_out_the_multiplier(self):
        self.assertTrue(st.agree(1.0e-5, 1.01e-2)[0])          # PEPE against kPEPE (1000x), 1% apart
        self.assertFalse(st.agree(1.0e-5, 1.05e-2)[0])         # 5% apart after the multiplier
        self.assertFalse(st.agree(0.0001, 0.000528)[0])        # LUNA, May 2022: 5x apart
        self.assertFalse(st.agree(None, 1.0)[0])

    def test_split_equalises_liquidation_moves(self):
        a, b = st.split(1000, [(1250, 0.05)], [(-1250, 0.05)])
        self.assertAlmostEqual(a + b, 1000)
        self.assertAlmostEqual(margin.liq_move(a, [(1250, 0.05)]), margin.liq_move(b, [(-1250, 0.05)]), places=6)
        self.assertEqual(st.split(100, [], []), (50, 50))

    def test_ticket_filters_and_sizes(self):
        lane = FakeLane([tk("enter", "NEIRO"), tk("enter", "PEPE"), tk("enter", "THIN")])
        books = {"kraken": lambda s: {"PF_NEIROUSD": book(0.10), "PF_PEPEUSD": book(1e-5),
                                      "PF_THINUSD": book(1.0, depth=10)}[s],
                 "hyperliquid": lambda s: {"NEIRO": book(0.1005), "kPEPE": book(1.1e-2), "THIN": book(1.0)}[s]}
        rows, acct = st.ticket_lane("R509", lane, books, 1000, 2.5, spec_by_venue={})
        by = {r["coin"]: r for r in rows}
        self.assertEqual(by["NEIRO"]["status"], "OK")
        self.assertAlmostEqual(by["NEIRO"]["notional"], 1000 * 2.5 / 40)
        self.assertAlmostEqual(by["NEIRO"]["qty_long"], 62.5 / 0.10, places=3)
        self.assertEqual(by["PEPE"]["status"], "SKIP")           # 10% apart after the multiplier
        self.assertIn("disagree", by["PEPE"]["why"])
        self.assertEqual(by["THIN"]["status"], "SKIP")            # $10 of depth for a $62.5 leg
        self.assertIn("cannot fill", by["THIN"]["why"])
        self.assertEqual(acct["kraken"]["legs"], 1)
        self.assertAlmostEqual(acct["kraken"]["equity"] + acct["hyperliquid"]["equity"], 1000)
        self.assertTrue(math.isfinite(acct["kraken"]["liq_move"]))

    def test_lots_minimums_and_initial_margin(self):
        lane = FakeLane([tk("enter", "NEIRO"), tk("enter", "THIN")])
        books = {"kraken": lambda s: {"PF_NEIROUSD": book(0.10), "PF_THINUSD": book(40.0)}[s],
                 "hyperliquid": lambda s: {"NEIRO": book(0.1001), "THIN": book(40.0)}[s]}
        spec = {"kraken": {"PF_NEIROUSD": {"step": 1.0, "min_qty": 1.0, "min_usd": 0, "im": 0.5, "mm": 0.25, "src": ""},
                           "PF_THINUSD": {"step": 1.0, "min_qty": 1.0, "min_usd": 0, "im": 0.5, "mm": 0.25, "src": ""}},
                "hyperliquid": {"NEIRO": {"step": 1.0, "min_qty": 1.0, "min_usd": 10, "im": 0.1, "mm": 0.05, "src": ""},
                                "THIN": {"step": 0.01, "min_qty": 0.01, "min_usd": 10, "im": 0.1, "mm": 0.05, "src": ""}}}
        rows, acct = st.ticket_lane("R509", lane, books, 1000, 2.5, spec_by_venue=spec)
        by = {r["coin"]: r for r in rows}
        self.assertEqual(by["NEIRO"]["qty_long"], 625.0)        # $62.5 at 0.10, whole contracts
        self.assertEqual(by["NEIRO"]["status"], "OK")
        self.assertEqual(by["THIN"]["status"], "SKIP")          # 1 Kraken lot of $40 against $62.4 on Hyperliquid
        self.assertIn("hedge", by["THIN"]["why"])
        self.assertAlmostEqual(acct["kraken"]["initial_margin"], 62.5 * 0.5)
        self.assertGreaterEqual(acct["kraken"]["equity"], acct["kraken"]["initial_margin"])
        self.assertFalse(acct["kraken"]["short_of_initial"])
        rows, acct = st.ticket_lane("R509", FakeLane([tk("enter", "NEIRO")]), books, 40, 2.5, spec_by_venue=spec)
        self.assertEqual(rows[0]["status"], "SKIP")             # a $2.5 leg is under Hyperliquid's $10 minimum

    def test_initial_margin_binds_the_split(self):
        lane = FakeLane([tk("enter", "NEIRO")])
        books = {"kraken": lambda s: book(0.10), "hyperliquid": lambda s: book(0.10)}
        # one $6.25 leg with an artificial 900% initial margin, so that it binds against the equalising split (~$47)
        spec = {"kraken": {"PF_NEIROUSD": {"step": 1e-6, "min_qty": 0, "min_usd": 0, "im": 9.0, "mm": 0.05, "src": ""}},
                "hyperliquid": {"NEIRO": {"step": 1e-6, "min_qty": 0, "min_usd": 0, "im": 0.1, "mm": 0.05, "src": ""}}}
        _, acct = st.ticket_lane("R509", lane, books, 100, 2.5, spec_by_venue=spec)
        self.assertAlmostEqual(acct["kraken"]["equity"], 6.25 * 9.0)   # funded to its initial margin first
        self.assertAlmostEqual(acct["kraken"]["equity"] + acct["hyperliquid"]["equity"], 100)

    def test_lot(self):
        s = {"step": 0.01, "min_qty": 0.05}
        self.assertAlmostEqual(st.lot(0.1299, s), 0.12)
        self.assertEqual(st.lot(0.049, s), 0.0)
        self.assertEqual(st.lot(3.3, None), 3.3)

    def test_retail_schedule_is_the_most_conservative(self):
        sched = {"europa": {"retail": [{"initialMargin": 0.1, "maintenanceMargin": 0.05}]},
                 "dlt": {"retail": [{"initialMargin": 0.5, "maintenanceMargin": 0.25}],
                         "professional": [{"initialMargin": 0.1, "maintenanceMargin": 0.05}]}}
        self.assertEqual(st._retail_first(sched), (0.5, 0.25))
        self.assertIsNone(st._retail_first({}))

    def test_a_failed_book_is_a_skip(self):
        def boom(s):
            raise OSError("down")
        lane = FakeLane([tk("enter", "NEIRO")])
        rows, _ = st.ticket_lane("R509", lane, {"kraken": boom, "hyperliquid": lambda s: book(0.1)}, 1000, 2.5,
                                 spec_by_venue={})
        self.assertEqual(rows[0]["status"], "SKIP")
        self.assertIn("book failed", rows[0]["why"])

    def test_render_is_a_dry_run_without_a_pass(self):
        lane = FakeLane([tk("enter", "NEIRO")])
        out = {"R509": st.ticket_lane("R509", lane, {}, 1000, 2.5, offline=True)}
        self.assertIn("DRY RUN", st.render(out, 1000, 2.5, "", True))
        self.assertIn("After the PASS of R527", st.render(out, 1000, 2.5, "R527", True))

    def test_leverage_cap(self):
        with self.assertRaises(SystemExit):
            st.main(["--leverage", "3", "--offline"])


if __name__ == "__main__":
    unittest.main()
