"""R369 eventlag_fwd: the rule and the runner on synthetic quotes (offline; says nothing about the real venues)."""
import datetime as dt
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import eventlag_calendar as cal  # noqa: E402
import eventlag_rule as rule  # noqa: E402
import run_eventlag as run  # noqa: E402

US = 1_000_000
T0 = int(dt.datetime(2026, 11, 5, 15, 30, tzinfo=dt.timezone.utc).timestamp()) * US


def quotes(T, jump_bp, at_s, base=3.0, half_spread=0.0005, until_s=70, size=5000.0):
    """A venue that quotes `base` every 2 s from T-120 s, then `base * (1 + jump_bp/1e4)` from `at_s` after T; at_s None
    means it never moves. One extra quote lands exactly at the jump."""
    ts = [T + int(k * 2 * US) for k in range(-60, until_s // 2 + 1)]
    mids = [base] * len(ts)
    if at_s is not None:
        up = base * (1 + jump_bp / 1e4)
        ts.append(T + int(at_s * US))
        mids.append(up)
        mids = [up if t >= T + int(at_s * US) else m for t, m in zip(ts, mids)]
    order = np.argsort(ts, kind="stable")
    t = np.array(ts, dtype=np.int64)[order]
    m = np.array(mids)[order]
    return {"t": t, "bid": m - half_spread, "ask": m + half_spread, "bq": np.full(len(t), size), "aq": np.full(len(t), size)}


def world(T, lead_at=0.1, hl_at=0.4, lighter_at=4.0, jump=30.0):
    return {"binance": quotes(T, jump, lead_at), "hl": quotes(T, jump, hl_at), "lighter": quotes(T, jump, lighter_at)}


class RuleTests(unittest.TestCase):
    def test_a_lagging_follower_pays_the_catch_up(self):
        r = rule.evaluate(world(T0), T0, "ng", "lighter", 1.0)
        self.assertEqual(r["status"], "ok")
        self.assertEqual((r["lead"], r["s"]), ("binance", 1))
        self.assertAlmostEqual(r["t_star_s"], 0.1, places=3)
        self.assertTrue(r["lag_ok"])
        self.assertLess(r["c"], 0.01)
        self.assertAlmostEqual(r["entry"], 3.0005)            # the stale ask
        self.assertAlmostEqual(r["gross"], 1e4 * math.log((3.009 - 0.0005) / 3.0005), places=6)
        self.assertGreater(r["gross"], 25)

    def test_a_follower_that_has_already_moved_is_filtered_and_loses_the_spread(self):
        r = rule.evaluate(world(T0, lighter_at=0.15), T0, "ng", "lighter", 1.0)
        self.assertEqual(r["status"], "ok")
        self.assertFalse(r["lag_ok"])
        self.assertGreater(r["c"], 0.9)
        self.assertLess(r["gross"], 0)

    def test_a_longer_latency_lets_the_follower_catch_up(self):
        w = world(T0, lighter_at=3.0)
        self.assertTrue(rule.evaluate(w, T0, "ng", "lighter", 1.0)["lag_ok"])
        self.assertFalse(rule.evaluate(w, T0, "ng", "lighter", 5.0)["lag_ok"])

    def test_short_side_uses_the_bid_and_a_down_move(self):
        r = rule.evaluate(world(T0, jump=-30.0), T0, "ng", "lighter", 1.0)
        self.assertEqual(r["s"], -1)
        self.assertAlmostEqual(r["entry"], 3.0 - 0.0005)      # the stale bid
        self.assertGreater(r["gross"], 25)

    def test_no_event_no_crossing_and_a_small_move_stays_below_the_threshold(self):
        w = {v: quotes(T0, 0.0, None) for v in rule.VENUES}
        self.assertEqual(rule.evaluate(w, T0, "ng", "lighter", 1.0)["status"], "no_cross")
        small = world(T0, jump=12.0)                           # 12 bp is under the gas threshold of 20
        self.assertEqual(rule.evaluate(small, T0, "ng", "lighter", 1.0)["status"], "no_cross")
        self.assertEqual(rule.evaluate(small, T0, "wpsr", "lighter", 1.0)["status"], "ok")   # but over crude's 8

    def test_a_leader_that_reverts_before_the_decision_is_skipped(self):
        w = world(T0)
        for v in ("binance", "hl"):                           # both fall back to the old level 0.6 s after T
            q = w[v]
            t = np.append(q["t"], T0 + int(0.6 * US))
            order = np.argsort(t, kind="stable")
            for k, val in (("bid", 3.0 - 0.0005), ("ask", 3.0 + 0.0005)):
                q[k] = np.append(q[k], val)[order]
            for k, val in (("bq", 5000.0), ("aq", 5000.0)):
                q[k] = np.append(q[k], val)[order]
            q["t"] = t[order]
            back = q["t"] >= T0 + int(0.6 * US)
            q["bid"][back], q["ask"][back] = 3.0 - 0.0005, 3.0 + 0.0005
        self.assertEqual(rule.evaluate(w, T0, "ng", "lighter", 1.0)["status"], "reverted")

    def test_thin_follower_book_is_not_a_fill(self):
        w = world(T0)
        w["lighter"] = quotes(T0, 30.0, 4.0, size=10.0)       # 10 units * 3.0 = $30 shown
        self.assertEqual(rule.evaluate(w, T0, "ng", "lighter", 1.0)["status"], "no_size")

    def test_missing_reference_is_reported(self):
        w = world(T0)
        w["lighter"] = {k: v[:0] for k, v in w["lighter"].items()}
        self.assertEqual(rule.evaluate(w, T0, "ng", "lighter", 1.0)["status"], "no_ref")

    def test_nothing_after_t_is_used_to_set_the_reference(self):
        # a venue that jumped 5 s BEFORE T (a clock offset) has a reference taken over T-60..T-10 only
        q = quotes(T0 - 5 * US, 30.0, 0.0)
        shifted = {k: v.copy() for k, v in q.items()}
        ref = rule.reference(shifted, T0)
        self.assertAlmostEqual(ref, 3.0, places=6)

    def test_net_and_holm_and_sign_flip(self):
        self.assertAlmostEqual(rule.net(20.0, "lighter", 2), 20.0 - 2 * 2 * 2.5)
        np.testing.assert_allclose(rule.holm([0.01, 0.04]), [0.02, 0.04])
        self.assertAlmostEqual(rule.sign_flip_p([1.0, 1.0, 1.0], np.random.default_rng(0)), 1 / 8)

    def test_verdict(self):
        c = lambda n, valid, mean, p: {"n": n, "valid": valid, "mean": mean, "p_holm": p}     # noqa: E731
        self.assertEqual(rule.verdict([c(9, 9, 30, 0.01)])[0], "PASS")
        self.assertEqual(rule.verdict([c(9, 9, 7, 0.01)])[0], "PARTIAL")        # unit is 5 bp, 2 units 10 bp
        self.assertEqual(rule.verdict([c(9, 9, 30, 0.3)])[0], "NULL")
        self.assertEqual(rule.verdict([c(5, 9, 30, 0.01)])[0], "INCONCLUSIVE")
        self.assertEqual(rule.verdict([c(9, 7, 30, 0.01)])[0], "INCONCLUSIVE")
        self.assertEqual(rule.verdict([])[0], "INCONCLUSIVE")


class CalendarTests(unittest.TestCase):
    def test_the_release_instants_follow_the_eia_pages(self):
        rows = {(n, t.strftime("%Y-%m-%dT%H:%M")): 1 for n, t in cal.events(dt.date(2026, 10, 29), dt.date(2026, 12, 31))}
        self.assertIn(("ng", "2026-10-29T14:30"), rows)         # daylight time
        self.assertIn(("wpsr", "2026-11-04T15:30"), rows)       # standard time
        self.assertIn(("wpsr", "2026-11-12T17:00"), rows)       # Veterans Day, Thursday 12:00 p.m. ET
        self.assertNotIn(("wpsr", "2026-11-11T15:30"), rows)
        self.assertIn(("ng", "2026-11-13T15:30"), rows)         # Friday 10:30 a.m. ET
        self.assertNotIn(("ng", "2026-11-12T15:30"), rows)
        self.assertIn(("ng", "2026-11-25T17:00"), rows)         # Thanksgiving week, Wednesday 12:00 p.m. ET
        self.assertNotIn(("ng", "2026-11-26T15:30"), rows)
        self.assertEqual(sum(1 for k in rows if k[0] == "ng"), 10)
        self.assertEqual(sum(1 for k in rows if k[0] == "wpsr"), 9)

    def test_the_committed_file_matches_the_script(self):
        built = [(n, int(t.timestamp() * 1000)) for n, t in cal.events(dt.date(2026, 10, 29), dt.date(2026, 12, 31))]
        have = pd.read_csv(ROOT / "experiments" / "eventlag_fwd" / "events.csv")
        self.assertEqual(built, list(zip(have.event, have.release_ms)))


class RunnerTests(unittest.TestCase):
    def write(self, root, etype, T, w):
        """Lay one event's quotes out as the recorders do: <folder>/<SYM>/<day>/<part>.parquet."""
        day = dt.datetime.fromtimestamp(T / 1e6, dt.timezone.utc).strftime("%Y-%m-%d")
        for v, (folder, sym) in self.sources(root)[etype].items():
            d = Path(folder) / sym / day
            d.mkdir(parents=True, exist_ok=True)
            q = w[v]
            pd.DataFrame({"t": q["t"], "bid": q["bid"], "bq": q["bq"], "ask": q["ask"], "aq": q["aq"]}).to_parquet(
                d / f"part-{int(T)}.parquet", index=False)

    def sources(self, root):
        return {e: {v: (Path(root) / v, sym) for v, (_, sym) in venues.items()} for e, venues in run.SOURCES.items()}

    def lane(self, root, rows):
        lane = Path(root) / "lane"
        lane.mkdir()
        pd.DataFrame([{"event": e, "release_utc": dt.datetime.fromtimestamp(T / 1e6, dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"), "release_ms": T // 1000, "source": "x"} for e, T in rows]).to_csv(
            lane / "events.csv", index=False)
        return lane

    def test_one_lagged_event_is_scored_once_and_the_journal_is_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, "ng", T0, world(T0))
            lane = self.lane(d, [("ng", T0)])
            now = dt.datetime.fromtimestamp(T0 / 1e6 + 1200, dt.timezone.utc)
            self.assertEqual(run.process(lane, now, self.sources(d)), 1)
            ev = pd.read_csv(lane / "journal" / "events.csv")
            self.assertEqual(list(ev.validity), ["valid"])
            cells = pd.read_csv(lane / "journal" / "cells.csv")
            prim = cells[(cells.kind == "event") & (cells.follower == "lighter")]
            self.assertEqual(sorted(prim.lag_s), [0.5, 1.0, 2.0, 5.0])
            self.assertEqual(run.process(lane, now, self.sources(d)), 0)      # nothing new: no second scoring
            self.assertEqual(len(pd.read_csv(lane / "journal" / "events.csv")), 1)

    def test_an_event_is_not_due_before_fifteen_minutes_or_before_the_first_release(self):
        with tempfile.TemporaryDirectory() as d:
            lane = self.lane(d, [("ng", T0)])
            early = dt.datetime.fromtimestamp(T0 / 1e6 + 600, dt.timezone.utc)
            self.assertEqual(run.process(lane, early, self.sources(d)), 0)
        with tempfile.TemporaryDirectory() as d:
            old = int(dt.datetime(2026, 10, 22, 14, 30, tzinfo=dt.timezone.utc).timestamp()) * US
            lane = self.lane(d, [("ng", old)])
            self.assertEqual(run.process(lane, dt.datetime(2026, 12, 1, tzinfo=dt.timezone.utc), self.sources(d)), 0)

    def test_a_venue_that_was_not_recorded_makes_the_event_invalid_not_a_loss(self):
        with tempfile.TemporaryDirectory() as d:
            w = world(T0)
            w["lighter"] = {k: v[:0] for k, v in w["lighter"].items()}
            self.write(d, "ng", T0, w)
            lane = self.lane(d, [("ng", T0)])
            run.process(lane, dt.datetime.fromtimestamp(T0 / 1e6 + 1200, dt.timezone.utc), self.sources(d))
            ev = pd.read_csv(lane / "journal" / "events.csv")
            self.assertEqual(ev.validity[0], "lighter:no_reference")
            self.assertFalse((lane / "journal" / "cells.csv").exists() and len(pd.read_csv(lane / "journal" / "cells.csv")))

    def test_nine_lagged_gas_events_pass_and_nine_unlagged_ones_stay_inconclusive(self):
        for lighter_at, want in ((4.0, "PASS"), (0.15, "INCONCLUSIVE")):
            with tempfile.TemporaryDirectory() as d:
                rows = []
                for k in range(9):
                    T = T0 + k * 7 * 86_400 * US
                    self.write(d, "ng", T, world(T, lighter_at=lighter_at, jump=30.0 + k))
                    rows.append(("ng", T))
                lane = self.lane(d, rows)
                run.process(lane, dt.datetime(2027, 1, 20, tzinfo=dt.timezone.utc), self.sources(d))
                self.assertEqual(run.summarize(lane), want)
                summary = json.loads((lane / "results" / "summary.json").read_text())
                self.assertEqual(summary["valid"], {"ng": 9})
                if want == "PASS":
                    dec = summary["decisions"][0]
                    self.assertEqual((dec["n"], dec["follower"], dec["lag_s"]), (9, "lighter", 1.0))
                    self.assertGreater(dec["net_2x"], 0)

    def test_the_frozen_input_check_refuses_a_changed_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("one")
            good = prereg.sha256_file(root / "a.txt")
            spec = root / "PREREG.md"
            spec.write_text(f"```inputs\n{good}  a.txt\n```\n")
            self.assertEqual(run.frozen_inputs(spec, root), {"a.txt": good})
            (root / "a.txt").write_text("two")
            with self.assertRaises(prereg.PreregError):
                run.frozen_inputs(spec, root)

    def test_crossed_or_empty_quotes_are_dropped_on_reading(self):
        with tempfile.TemporaryDirectory() as d:
            T = T0
            day = dt.datetime.fromtimestamp(T / 1e6, dt.timezone.utc).strftime("%Y-%m-%d")
            p = Path(d) / "X" / day
            p.mkdir(parents=True)
            pd.DataFrame({"t": [T - 5 * US, T - 4 * US, T - 3 * US, T - 2 * US], "bid": [3.0, 3.1, 0.0, 3.0],
                          "bq": [1.0, 1.0, 1.0, 0.0], "ask": [3.001, 3.0, 3.001, 3.001],
                          "aq": [1.0, 1.0, 1.0, 1.0]}).to_parquet(p / "a.parquet", index=False)
            q = run.read_quotes(Path(d), "X", T - 10 * US, T)
            self.assertEqual(len(q["t"]), 1)


if __name__ == "__main__":
    unittest.main()
