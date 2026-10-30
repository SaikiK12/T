"""Hand-computed and adversarial checks, exclusively invented market paths."""
from dataclasses import replace
from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo

from lab.orb_family import (ARMS, MINUTE, Bar, Contract, Cost, Funding, Session,
                            account_trade, decision, index_bars, path_exit, run_family)


def session(day="2026-10-01", close=16):
    a = datetime.fromisoformat(day).replace(hour=9, minute=30, tzinfo=ZoneInfo("America/New_York"))
    b = a.replace(hour=close, minute=0)
    return Session(day, int(a.timestamp() * 1000), int(b.timestamp() * 1000))


def invented(s=None, volume=200):
    s = s or session()
    bars = []
    for t in range(s.open_ms, s.close_ms + 2 * MINUTE, MINUTE):
        i = (t - s.open_ms) // MINUTE
        if i < 30:
            bars.append(Bar(t, 99.0, 100.0, 98.0, 99.0, 100.0))
        elif i == 30:
            bars.append(Bar(t, 100.0, 102.0, 99.5, 101.0, float(volume)))
        else:
            bars.append(Bar(t, 102.0, 103.0, 101.0, 102.0, 100.0))
    return bars


class OrbFamilyTests(unittest.TestCase):
    def setUp(self):
        self.s = session()
        self.bars = invented(self.s)
        self.idx = index_bars(self.bars)
        self.contract = Contract(1.0, 1.0, 1.0, 1000.0, 0.01)

    def test_first_ticket_close_time_and_full_minute_delay(self):
        d = decision(self.idx, self.s)
        self.assertEqual(d["decision_ms"], self.s.open_ms + 31 * MINUTE)
        self.assertEqual(d["entry_ms"], self.s.open_ms + 32 * MINUTE)
        self.assertEqual(d["stop"], 98)
        self.assertEqual(d["opening_mean_volume"], 100)
        self.assertEqual(d["accept"], dict.fromkeys(ARMS, True))

    def test_future_prices_and_volume_cannot_change_ticket(self):
        d = decision(self.idx, self.s)
        future = dict(self.idx)
        for t, b in future.items():
            if t >= d["decision_ms"]:
                future[t] = replace(b, open=1.0, high=10000.0, low=0.1, close=2.0, volume=1e9)
        self.assertEqual(decision(future, self.s), d)
        prefix = {t: b for t, b in self.idx.items() if t < d["decision_ms"]}
        self.assertEqual(decision(prefix, self.s), d)

    def test_filter_rejection_does_not_wait_for_later_volume(self):
        bars = invented(volume=10)
        r = run_family(bars, [], [], [self.s], [self.s.day], self.contract)
        self.assertEqual(r["days"][0]["decision"]["decision_ms"], self.s.open_ms + 31 * MINUTE)
        self.assertEqual(r["days"][0]["accounts"]["volume_1x"]["pnl"], 0)
        self.assertEqual(r["days"][0]["accounts"]["joint_1x"]["pnl"], 0)
        self.assertEqual(r["days"][0]["accounts"]["parent_1x"]["status"], "trade")

    def test_missing_opening_or_predecision_bar_is_not_cash(self):
        for i in (0, 29, 30):
            idx = dict(self.idx)
            del idx[self.s.open_ms + i * MINUTE]
            self.assertEqual(decision(idx, self.s)["status"], "missing")

    def test_no_parent_does_not_require_future_exit(self):
        bars = [replace(b, open=99., high=100., low=98., close=99.) for b in self.bars[:120]]
        self.assertEqual(decision(index_bars(bars), self.s)["status"], "cash")
        r = run_family(bars, [], [], [self.s], [self.s.day], self.contract)
        self.assertTrue(r["complete"])
        self.assertEqual(set(r["equity"].values()), {2000.0})

    def test_stop_gap_gets_worse_price_and_next_minute(self):
        d = decision(self.idx, self.s)
        idx = dict(self.idx)
        t = d["entry_ms"] + 3 * MINUTE
        idx[t] = Bar(t, 102., 103., 95., 99., 100.)
        idx[t + MINUTE] = Bar(t + MINUTE, 90., 92., 89., 91., 100.)
        x = path_exit(idx, d, self.s)
        self.assertEqual((x["t"], x["price"]), (t + MINUTE, 90.0))

    def test_missing_and_untraded_active_bars_stay_unknown(self):
        d = decision(self.idx, self.s)
        for t in (d["entry_ms"], d["entry_ms"] + MINUTE, self.s.close_ms + MINUTE):
            for missing in (True, False):
                idx = dict(self.idx)
                if missing:
                    del idx[t]
                else:
                    idx[t] = replace(idx[t], volume=0.)
                self.assertEqual(path_exit(idx, d, self.s)["status"], "missing")

    def test_entry_below_stop_skips_all_arms(self):
        d = decision(self.idx, self.s)
        idx = dict(self.idx)
        t = d["entry_ms"]
        idx[t] = Bar(t, 90., 92., 89., 91., 10.)
        self.assertEqual(path_exit(idx, d, self.s)["reason"], "entry_below_stop")

    def test_funding_uses_fair_quantity_not_entry_notional(self):
        start = self.s.open_ms
        end = start + 10 * MINUTE
        idx = {t: Bar(t, 100., 110., 90., 100., 1.) for t in range(start, end, MINUTE)}
        ft = start + 5 * MINUTE
        fair = {ft: Bar(ft, 200., 200., 200., 200., 0.)}
        d = {"entry_ms": start}
        x = {"status": "exit", "t": end, "price": 110., "reason": "test"}
        r = account_trade(idx, fair, [Funding(ft, .01)], d, x, self.contract,
                          Cost(1, .001, 0.), 2000.)
        self.assertEqual(r["quantity"], 10)
        self.assertAlmostEqual(r["funding"], 20)
        self.assertAlmostEqual(r["fees"], 2.1)
        self.assertAlmostEqual(r["pnl"], 77.9)

    def test_exact_funding_time_missing_mark_and_boundary_refused(self):
        d = decision(self.idx, self.s)
        x = path_exit(self.idx, d, self.s)
        for t, reason in [(d["entry_ms"], "funding_boundary"),
                          (x["t"], "funding_boundary"),
                          (d["entry_ms"] + 1234, "funding_fair_open")]:
            r = account_trade(self.idx, {}, [Funding(t, .01)], d, x, self.contract, Cost(1), 2000)
            self.assertEqual(r["reason"], reason)
            self.assertIsNone(r["pnl"])

    def test_cost_sensitivity_tick_rounding_and_no_daily_cash_reset(self):
        s2 = session("2026-10-02")
        r = run_family(self.bars + invented(s2), [], [], [self.s, s2], [self.s.day, s2.day], self.contract)
        for scale in (1, 2, 3):
            pnl = sum(d["accounts"][f"parent_{scale}x"]["pnl"] for d in r["days"])
            self.assertAlmostEqual(r["equity"][f"parent_{scale}x"], 2000 + pnl)
        self.assertGreater(r["equity"]["parent_1x"], r["equity"]["parent_2x"])
        self.assertGreater(r["equity"]["parent_2x"], r["equity"]["parent_3x"])

    def test_unknown_account_does_not_restart_on_next_day(self):
        s2 = session("2026-10-02")
        r = run_family(self.bars[:-1] + invented(s2), [], [], [self.s, s2], [self.s.day, s2.day], self.contract)
        self.assertFalse(r["complete"])
        self.assertIsNone(r["equity"]["parent_1x"])
        self.assertEqual(r["days"][1]["accounts"]["parent_1x"]["reason"], "prior_unknown")

    def test_dst_and_early_close(self):
        self.assertEqual(datetime.fromtimestamp(session("2026-03-06").open_ms / 1000,
                                              ZoneInfo("UTC")).hour, 14)
        self.assertEqual(datetime.fromtimestamp(session("2026-03-09").open_ms / 1000,
                                              ZoneInfo("UTC")).hour, 13)
        s = session("2026-11-27", 13)
        idx = index_bars(invented(s))
        self.assertEqual(path_exit(idx, decision(idx, s), s)["t"], s.close_ms + MINUTE)

    def test_weekend_cash_and_explicit_holiday_required(self):
        s = session("2026-10-02")
        cal = ["2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05"]
        with self.assertRaises(ValueError):
            run_family(invented(s), [], [], [s], cal, self.contract)
        r = run_family(invented(s), [], [], [s], cal, self.contract, closed_days=["2026-10-05"])
        self.assertEqual(len(r["days"]), 4)
        self.assertEqual(r["days"][1]["accounts"]["parent_1x"]["reason"], "calendar_closed")

    def test_invalid_numbers_duplicates_order_calendar_and_scale(self):
        for kw in [dict(t=True), dict(close=float('nan')), dict(volume=float('inf')), dict(low=104.)]:
            with self.assertRaises(ValueError):
                replace(self.bars[0], **kw)
        for seq in [self.bars[:1] * 2, self.bars[:2][::-1]]:
            with self.assertRaises(ValueError):
                index_bars(seq)
        with self.assertRaises(ValueError):
            Cost(True)
        with self.assertRaises(ValueError):
            run_family([], [], [], [], ["2026-10-01", "2026-10-03"], self.contract)


if __name__ == "__main__":
    unittest.main()
