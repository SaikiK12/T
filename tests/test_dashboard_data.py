"""Control-room exporter semantics on synthetic journals only; no network or market-cache reads."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import dashboard_data as dashboard


class DashboardData(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exp = self.root / "experiments"
        self.exp.mkdir()
        self.patches = [patch.object(dashboard, "ROOT", self.root),
                        patch.object(dashboard, "EXP", self.exp),
                        patch.object(dashboard, "NOW", 1000.)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def journal(self, lane, name, rows):
        path = self.exp / lane / "journal" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name.endswith("json"):
            path.write_text(json.dumps(rows))
        else:
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)

    def lane(self, lane, days=()):
        return next(r for r in dashboard.forward_lanes(days) if r["lane"] == lane)

    def test_missing_returns_stay_unknown_and_zero_is_valid(self):
        rows = [dict(lane="mexc_fwd", kind="ontime", book="A", day="2026-10-20",
                     net=.01, net_2x=None, net_3x=0.),
                dict(lane="mexc_fwd", kind="ontime", book="B", day="2026-10-20",
                     net=.03, net_2x=.02, net_3x=0.)]
        lane = self.lane("mexc_fwd", rows)
        self.assertAlmostEqual(lane["net_pct"], 2.)
        self.assertIsNone(lane["net_2x_pct"])
        self.assertEqual(lane["net_3x_pct"], 0.)
        rows[1]["net"] = float("nan")
        self.assertIsNone(self.lane("mexc_fwd", rows)["net_pct"])

    def test_empty_daily_lane_does_not_become_event_lane(self):
        lane = self.lane("mexc_fwd")
        self.assertEqual(lane["kind"], "daily book")
        self.assertEqual(lane["unit"], "on-time days")
        self.assertIsNone(lane["net_pct"])

    def test_method_text_and_blocker_are_not_truncated(self):
        path = self.root / "registry/methods.csv"
        path.parent.mkdir()
        title = "a" * 220 + " exact remaining mechanics"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "method", "status", "data_held", "cheap", "note"])
            writer.writeheader()
            writer.writerow(dict(id="M001", method=title, status="BLOCKED", data_held="N", cheap="3",
                                 note="Missing first-seen timestamps"))
        row = dashboard.methods()[0]
        self.assertEqual(row["method"], title)
        self.assertEqual(row["note"], "Missing first-seen timestamps")

    def test_partial_primary_variant_does_not_get_pass_ring(self):
        path = self.exp / "toy/results/verdict.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"verdict": "PARTIAL", "variants": {"1: primary": {
            "1x": {"n": 5, "mean_pct": 1}, "2x": {}, "3x": {}}}}))
        with patch.object(dashboard, "rid_by_path", return_value={"experiments/toy": "R999"}):
            self.assertFalse(dashboard.strategies()[0]["passed"])

    def test_checkout_without_local_market_cache_exports_empty_inventory(self):
        self.assertEqual(dashboard.data_sources(), [])

    def test_volatility_target_uses_365_day_frozen_decision(self):
        lane = self.lane("vt_fwd")
        self.assertEqual(lane["needed"], 365)
        self.assertIn("risk-only", lane["decision"])
        self.assertEqual(lane["round"], "R225")
        self.assertIn("volatility target", lane["display_name"].lower())

    def test_announcement_progress_cannot_pool_two_book_decisions(self):
        self.journal("announce_fwd", "status.json", dict(scored_notices=15, books={
            "FF": {"scored_notices": 12}, "PL": {"scored_notices": 3}}))
        lane = self.lane("announce_fwd")
        self.assertEqual(lane["scored"], 3)
        self.assertEqual(lane["progress"], .25)
        self.assertEqual(lane["scored_by_book"], {"FF": 12, "PL": 3})

    def test_announcement_missing_book_count_is_unknown(self):
        self.journal("announce_fwd", "status.json", dict(scored_notices=12, books={
            "FF": {"scored_notices": 12}}))
        lane = self.lane("announce_fwd")
        self.assertIsNone(lane["scored"])
        self.assertIsNone(lane["progress"])
        self.assertIn("unknown", lane["progress_note"])

    def test_ticket_states_and_unlock_scores_are_not_inferred_from_clock_alone(self):
        rows = [dict(ticket=key, contract="TOY_USDT", entry_ms=entry, exit_ms=exit_, frac_max_supply=0.)
                for key, entry, exit_ in (("future", 1_100_000, 1_200_000),
                                         ("open", 900_000, 1_100_000),
                                         ("waiting", 800_000, 900_000),
                                         ("done", 800_000, 900_000),
                                         ("bad-score", 800_000, 900_000))]
        self.journal("unlocks_fwd", "tickets.csv", rows)
        self.journal("unlocks_fwd", "scores.csv", [{"ticket": "done", "net": 0.},
                                                    {"ticket": "bad-score", "net": "NaN"}])
        tickets = {r["key"]: r for r in dashboard.event_tickets()}
        self.assertEqual({k: r["state"] for k, r in tickets.items()}, {
            "future": "frozen, not entered", "open": "open", "waiting": "awaiting score",
            "done": "scored", "bad-score": "score unavailable"})
        self.assertEqual(tickets["done"]["net_pct"], 0.)
        self.assertEqual(tickets["done"]["size_pct_supply"], 0.)

    def test_notice_future_and_elapsed_tickets_are_not_both_open(self):
        self.journal("announce_fwd", "tickets.csv", [
            dict(ticket="future", contract="TOY_USDT", entry_ms=1_100_000, exit_ms=1_200_000),
            dict(ticket="waiting", contract="TOY_USDT", entry_ms=800_000, exit_ms=900_000)])
        tickets = {r["key"]: r for r in dashboard.event_tickets()}
        self.assertEqual(tickets["future"]["state"], "frozen, not entered")
        self.assertEqual(tickets["waiting"]["state"], "awaiting score")

    def test_calendar_deduplication_uses_exact_contract_not_ticker_substring(self):
        self.journal("unlocks_fwd", "tickets.csv", [dict(ticket="other", contract="STO_USDT",
            entry_ms=1_100_000, exit_ms=1_200_000, frac_max_supply=.01)])
        self.journal("unlocks_fwd", "status.json", {"next_entries": [
            "1970-01-01T00:18:20Z STO", "1970-01-01T00:18:20Z TO"]})
        tickets = dashboard.event_tickets()
        self.assertEqual(len(tickets), 2)
        self.assertEqual([r["symbol"] for r in tickets if r["state"] == "upcoming on the calendar"], ["TO"])


if __name__ == "__main__":
    unittest.main()
