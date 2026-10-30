"""scripts/probe_kraken_orders.py and scripts/pilot_kraken_orders.py: offline, with fake responses (no network)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pilot_kraken_orders as pilot  # noqa: E402
import probe_kraken_orders as probe  # noqa: E402


def placed(uid, t, event_uid=None):
    return {"uid": event_uid or f"e{uid}-p", "timestamp": t, "event": {"OrderPlaced": {"order": {"uid": uid}}}}


def cancelled(uid, t):
    return {"uid": f"e{uid}-c", "timestamp": t, "event": {"OrderCancelled": {"order": {"uid": uid}}}}


def fill(uid, t, reason="full_fill"):
    return {"uid": f"e{uid}-f{t}", "timestamp": t, "event": {"OrderUpdated": {"newOrder": {"uid": uid},
                                                                             "oldOrder": {"uid": uid}, "reason": reason}}}


def execution(maker, taker, t, n=0):
    return {"uid": f"x{n}", "timestamp": t, "event": {"Execution": {"execution": {
        "timestamp": t, "makerOrder": {"uid": maker}, "takerOrder": {"uid": taker, "orderType": "Market"}}}}}


class ProbeTests(unittest.TestCase):
    def test_summary_keeps_metadata_only(self):
        body = {"elements": [{"timestamp": 1500, "event": {"OrderPlaced": {"order": {"uid": "secret"}}}},
                             {"timestamp": 1200, "event": {"OrderCancelled": {}}}]}
        s = probe.summarize(1000, 200, body, "tok")
        self.assertEqual((s["n"], s["oldest_ms"], s["newest_ms"], s["token"]), (2, 1200, 1500, True))
        self.assertEqual(s["types"], ["OrderCancelled", "OrderPlaced"])
        self.assertEqual(s["first_minus_requested_s"], 0.2)
        self.assertNotIn("secret", str(s))
        self.assertEqual(probe.summarize(1000, 0, None, "")["n"], 0)

    def test_probe_asks_both_directions_for_each_age_without_pausing(self):
        urls = []

        def fake(u):
            urls.append(u)
            return 200, {"elements": []}, ""

        rows = probe.probe("PF_XBTUSD", 10**12, ages=(("1h", 3600), ("1d", 86400)), fetch_fn=fake, pause=0)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["direction"] for r in rows], ["after", "before", "after", "before"])
        self.assertTrue(all("count=3" in u for u in urls))
        self.assertIn("sort=asc", urls[0])
        self.assertIn("sort=desc", urls[1])


class PilotTests(unittest.TestCase):
    def test_paging_follows_the_token_and_stops_at_the_cap(self):
        calls = []

        def fake(tradeable, kind, params, headers_out, **_):
            calls.append(dict(params))
            headers_out["token"] = "next"
            return {"elements": [{"timestamp": i} for i in range(1000)]}

        out, pages, capped = pilot.page("PF_XBTUSD", "orders", 0, 10**6, 3, get_fn=fake, pause=0)
        self.assertEqual((len(out), pages, capped), (3000, 3, True))
        self.assertNotIn("continuation_token", calls[0])
        self.assertEqual(calls[1]["continuation_token"], "next")

    def test_paging_ends_on_a_short_page(self):
        def fake(tradeable, kind, params, headers_out, **_):
            headers_out["token"] = "next"
            return {"elements": [{"timestamp": 1}] * 7}

        out, pages, capped = pilot.page("PF_XBTUSD", "orders", 0, 10, 5, get_fn=fake, pause=0)
        self.assertEqual((len(out), pages, capped), (7, 1, False))

    def test_quality_counts_the_lifecycle_and_the_execution_join(self):
        orders = [placed("a", 100), placed("b", 100), fill("a", 105), cancelled("b", 110), placed("c", 111),
                  fill("z", 120, "partial_fill")]
        execs = [execution("a", "t1", 106, 1), execution("z", "t2", 121, 2), execution("q", "t3", 130, 3)]
        q = pilot.quality(orders, execs)
        self.assertEqual((q["order_events"], q["executions"]), (6, 3))
        self.assertEqual(q["event_types"], {"OrderPlaced": 3, "OrderCancelled": 1, "OrderUpdated": 2})
        self.assertEqual(q["same_ms_ties"], 1)
        self.assertEqual(q["timestamp_decreases"], 0)
        self.assertEqual(q["placed_closed_in_window"], 2)
        self.assertEqual(q["placed_still_resting_at_end"], 1)
        self.assertEqual(q["exec_maker_uid_has_fill_update"], 2)
        self.assertEqual(q["exec_maker_fill_update_within_3ms"], 2)
        self.assertEqual(q["exec_maker_placed_in_window"], 1)


if __name__ == "__main__":
    unittest.main()
