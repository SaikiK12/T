"""Synthetic cash/depth cases only. No gitignored market data or network."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from decimal import Decimal as D

from lab.carry_execution import Book, Tier, common_quantity, number, pair_sweep, requirement, stress_replay, sweep


def quoted(price="100", size="10000"):
    p = D(price)
    return dict(bids=[[str(p - D(".05")), size]], asks=[[str(p + D(".05")), size]])


def scenario():
    tier = [dict(ceiling="10000000", initial=".1", maintenance=".05", deduction="0")]
    return dict(lot=".001", entry_books={k: quoted() for k in ("long", "short")},
                transfer_outage_until_ms=33 * 60000,
                legs={k: dict(tiers=tier, fee_rate=".001", liquidation_fee=".005")
                      for k in ("long", "short")},
                events=[dict(time_ms=t, label=label, marks={k: p for k in ("long", "short")},
                             books={k: quoted(p) for k in ("long", "short")},
                             funding_cash_per_notional={"long": "0", "short": "0"}, **extra)
                        for t, label, p, extra in [
                            (60000, "gap", "210", {"transfer": ["long", "short", ".3"]}),
                            (14 * 60000, "before_recovery", "80", {}),
                            (34 * 60000, "recovery", "100", {}),
                            (35 * 60000, "terminal", "100", {"close_all": True})]])


class DepthExecutionTests(unittest.TestCase):
    def test_rejects_invalid_and_crossed_books(self):
        for x in [None, True, "NaN", "Infinity"]:
            with self.assertRaises(ValueError): number(x)
        for b in [dict(bids=[[100, 1]], asks=[[100, 1]]),
                  dict(bids=[[99, 1], [100, 1]], asks=[[101, 1]]),
                  dict(bids=[[99, 0]], asks=[[101, 1]])]:
            with self.assertRaises(ValueError): Book(**b)

    def test_walks_base_not_quote_and_retains_partial(self):
        book = Book(bids=((99, 2),), asks=((101, 1), (103, 2)))
        out = sweep(book, "buy", "2", fee_rate=".001")
        self.assertEqual((out["quote"], out["vwap"], out["fee"]), (D(204), D(102), D(".204")))
        self.assertEqual(sweep(book, "buy", 4)["filled"], 3)
        self.assertFalse(sweep(book, "buy", 4)["complete"])
        self.assertIsNone(sweep(book, "buy", 2)["fee"])

    def test_common_lot_and_minimum(self):
        books = (Book(**quoted()), Book(**quoted()))
        self.assertEqual(common_quantity("101", books, (".003", ".002")), (D("1.008"), D(".006")))
        out = pair_sweep("1", books, (".01", ".01"), (".02", ".02"), (0, 0))
        self.assertEqual(out["state"], "BLOCKED_MINIMUM")

    def test_partial_pair_does_not_export_complete_cost(self):
        books = (Book(**quoted(size="10")), Book(**quoted(size=".5")))
        out = pair_sweep(100, books, (".001", ".001"), (".001", ".001"), (0, 0))
        row = out["directions"][0]
        self.assertEqual(row["unmatched_base"], D(".5"))
        self.assertEqual(row["state"], "PARTIAL_PAIR")
        self.assertIsNone(row["complete_entry_cost"])

    def test_unknown_fee_and_cost_sensitivity_keep_quantity(self):
        books = (Book(**quoted()), Book(**quoted()))
        rows = [pair_sweep(10000, books, (".001", ".001"), (".001", ".001"), (".001", 0), multiple=m)
                for m in (1, 2, 3)]
        self.assertEqual({r["quantity"] for r in rows}, {D(100)})
        self.assertEqual([r["directions"][0]["book_cost"] for r in rows], [D(10), D(20), D(30)])
        unknown = pair_sweep(10000, books, (".001", ".001"), (".001", ".001"), (None, 0))
        self.assertIsNone(unknown["directions"][0]["complete_entry_cost"])

    def test_tier_boundary_and_unsupported_size(self):
        tiers = (Tier(100, ".1", ".05"), Tier(200, ".2", ".1", 5))
        self.assertEqual(requirement(tiers, 100), 5)
        self.assertEqual(requirement(tiers, 101), D("5.1"))
        self.assertEqual(requirement(tiers, 101, initial=True), D("20.2"))
        self.assertIsNone(requirement(tiers, 201))
        self.assertIsNone(requirement((), 1))
        self.assertEqual(requirement((), 0), 0)


class SegregatedStressTests(unittest.TestCase):
    def test_outage_blocks_transfer_and_short_loss_survives_recovery(self):
        out = stress_replay(scenario(), 10000)
        self.assertIn("TRANSFER_BLOCKED_OUTAGE", out["rows"][0]["actions"])
        self.assertIn("short_LIQUIDATED", out["rows"][0]["actions"])
        first = out["rows"][0]["wallets"]["short"]
        self.assertLess(first["cash"], 0)
        for row in out["rows"]:
            self.assertEqual(row["wallets"]["short"]["quantity"], 0)
            self.assertEqual(row["wallets"]["short"]["cash"], first["cash"])
        self.assertLess(out["final_net"], -10000)
        # This would be near just the fees under phantom constant-notional
        # reopening. The fixed account retains the original forced loss.
        self.assertEqual(out["rows"][-1]["equity"], sum(w["cash"] for w in out["rows"][-1]["wallets"].values()))

    def test_independent_simple_cash_identity(self):
        case = scenario()
        out = stress_replay(case, 10000)
        final = out["rows"][-1]["wallets"]
        q = D(100)
        long_pnl = q * (D("99.95") - D("100.05"))
        short_pnl = -q * (D("210.05") - D("99.95"))
        for key, pnl in [("long", long_pnl), ("short", short_pnl)]:
            w = final[key]
            self.assertEqual(w["realized"], pnl)
            self.assertEqual(w["cash"], D(10000) + pnl + w["funding"] - w["fees"])

    def test_adl_price_is_explicit_and_inventory_stays_closed(self):
        case = scenario()
        case["events"][0].update(marks={"long": "80", "short": "80"},
                                  books={k: quoted("80") for k in ("long", "short")},
                                  forced={"short": dict(kind="ADL", price="79", fee_rate="0")})
        out = stress_replay(case, 10000)
        self.assertIn("short_ADL_CLOSED", out["rows"][0]["actions"])
        self.assertEqual(out["rows"][-1]["wallets"]["short"]["realized"], D(100) * (D("99.95") - 79))

    def test_missing_funding_blocks_even_when_zero_would_help(self):
        case = scenario()
        del case["events"][1]["funding_cash_per_notional"]["long"]
        out = stress_replay(case, 10000)
        self.assertEqual(out["state"], "UNKNOWN_MARK_OR_FUNDING")
        self.assertIsNone(out["final_net"])

    def test_closed_leg_does_not_receive_future_funding(self):
        case = scenario()
        case["events"][-1]["funding_cash_per_notional"]["short"] = "99"
        self.assertEqual(stress_replay(case, 10000)["rows"][-1]["wallets"]["short"]["funding"], 0)

    def test_unknown_margin_is_not_safe_margin(self):
        case = scenario()
        case["legs"]["short"]["tiers"] = None
        out = stress_replay(case, 10000)
        self.assertEqual(out["state"], "UNKNOWN_MARGIN")
        self.assertIsNone(out["final_net"])

    def test_terminal_partial_exit_keeps_open_inventory_and_unknown_net(self):
        case = scenario()
        case["events"][-1]["books"]["long"] = quoted(size=".001")
        out = stress_replay(case, 10000)
        self.assertEqual(out["state"], "OPEN")
        self.assertIsNone(out["final_net"])
        self.assertGreater(out["rows"][-1]["wallets"]["long"]["quantity"], 0)

    def test_cost_tiers_keep_same_position_and_increase_loss(self):
        outs = [stress_replay(scenario(), 10000, multiple=m) for m in (1, 2, 3)]
        self.assertEqual({o["initial_quantity"] for o in outs}, {D(100)})
        self.assertGreater(outs[0]["final_net"], outs[1]["final_net"])
        self.assertGreater(outs[1]["final_net"], outs[2]["final_net"])

    def test_after_outage_transfer_is_conservative_and_cash_conserving(self):
        case = scenario()
        case["transfer_outage_until_ms"] = 0
        out = stress_replay(case, 10000)
        self.assertIn("TRANSFER_COMPLETED", out["rows"][0]["actions"])
        self.assertNotIn("short_LIQUIDATED", out["rows"][0]["actions"])
        self.assertLess(abs(out["final_net"]), 1000)

    def test_out_of_order_events_rejected(self):
        case = scenario()
        case["events"][1]["time_ms"] = 1
        with self.assertRaises(ValueError): stress_replay(case, 10000)

    def test_fixture_can_roundtrip_through_temporary_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "case.json"
            p.write_text(json.dumps(scenario()))
            out = stress_replay(json.loads(p.read_text()), 10000)
            self.assertEqual(out["state"], "CONDITIONAL_CLOSED")


if __name__ == "__main__":
    unittest.main()
