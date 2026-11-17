import datetime as dt
import unittest

from scripts import run_cmecarry as c


class CalendarTest(unittest.TestCase):
    def test_expiry_rule(self):
        self.assertEqual(c.last_friday(2024, 3), dt.date(2024, 3, 28))     # Good Friday 2024-03-29
        self.assertEqual(c.last_friday(2020, 12), dt.date(2020, 12, 24))   # Christmas Friday
        self.assertEqual(c.last_friday(2023, 6), dt.date(2023, 6, 30))
        e0, e1 = c.front_expiries(dt.date(2023, 6, 30))
        self.assertEqual((e0, e1), (dt.date(2023, 6, 30), dt.date(2023, 7, 28)))
        e0, _ = c.front_expiries(dt.date(2023, 7, 1))
        self.assertEqual(e0, dt.date(2023, 7, 28))

    def test_settlement_minute_follows_us_daylight_time(self):
        self.assertEqual(c.settle_utc(dt.date(2023, 7, 3)).hour, 20)
        self.assertEqual(c.settle_utc(dt.date(2023, 1, 3)).hour, 21)
        self.assertEqual(c.expiry_utc(dt.date(2023, 7, 28)).hour, 15)
        self.assertEqual(c.second_wednesday(2026, 9), dt.date(2026, 9, 9))


class RuleTest(unittest.TestCase):
    def test_hysteresis(self):
        self.assertEqual(c.step(0, 12), 1)
        self.assertEqual(c.step(1, 7), 1)
        self.assertEqual(c.step(1, 4), 0)
        self.assertEqual(c.step(1, -11), -1)
        self.assertEqual(c.step(-1, -6), -1)
        self.assertEqual(c.step(0, 9), 0)


def _world(n=60, fund_rate=0.0003, basis=0.0):
    """Daily settlements for two monthly contracts at a constant price; funding 3 times a day."""
    start = dt.date(2023, 3, 1)
    px, chain, close, fund_pairs = {}, {}, {}, []
    ids = {}
    for i in range(n):
        day = start + dt.timedelta(days=i)
        e0, e1 = c.front_expiries(day)
        i0, i1 = ids.setdefault(e0, len(ids) + 1), ids.setdefault(e1, len(ids) + 1)
        t = c.settle_utc(day)
        tau0 = (c.expiry_utc(e0) - t).total_seconds() / 86400
        tau1 = (c.expiry_utc(e1) - t).total_seconds() / 86400
        px[day] = {i0: 100 * (1 + basis * tau0 / 365), i1: 100 * (1 + basis * tau1 / 365)}
        chain[day] = (i0, i1)
        close[int(t.timestamp()) - 3600] = 100.0
        for h in (0, 8, 16):
            fund_pairs.append((dt.datetime(day.year, day.month, day.day, h, tzinfo=dt.timezone.utc).timestamp(),
                               fund_rate))
    ts, cum = [t for t, _ in fund_pairs], [0.0]
    for _, r in fund_pairs:
        cum.append(cum[-1] + r)
    return px, chain, close, (ts, cum)


class BuildTest(unittest.TestCase):
    def test_high_funding_zero_basis_goes_long_future_short_perp(self):
        px, chain, close, fund = _world(fund_rate=0.0003)            # 32.85%/yr
        rows = c.build("BTC", px, chain, close, fund, {}, "2023-03-08", "2023-04-29")
        self.assertTrue(all(r["w"] == 1 for r in rows))
        self.assertAlmostEqual(rows[3]["gross"], 3 * 0.0003, places=9)  # earns funding, prices flat
        self.assertEqual(sum(1 for r in rows if r["trade"]), 1)
        self.assertGreaterEqual(sum(1 for r in rows if r["roll"]), 1)    # rolls 14 days before the March expiry

    def test_basis_above_funding_shorts_the_future(self):
        px, chain, close, fund = _world(fund_rate=0.0, basis=0.2)     # 20%/yr basis, no funding
        rows = c.build("BTC", px, chain, close, fund, {}, "2023-03-08", "2023-04-29")
        self.assertTrue(all(r["w"] == -1 for r in rows))
        self.assertTrue(all(r["s"] < -10 for r in rows))
        # Short the future earns the convergence: positive gross on a non-roll day.
        self.assertGreater(rows[2]["gross"], 0)

    def test_cost_counts_fee_per_contract_and_measured_spread(self):
        px, chain, close, fund = _world(fund_rate=0.0003)
        half = {("2023-03", "c.0"): 1.0, ("2023-03", "c.1"): 2.0}
        rows = c.build("BTC", px, chain, close, fund, half, "2023-03-08", "2023-03-31")
        f = px[dt.date(2023, 3, 8)][chain[dt.date(2023, 3, 8)][0]]
        self.assertAlmostEqual(rows[0]["cme_bp"], 2.5 / (0.1 * f) * 1e4 + 1.0, places=3)
        self.assertAlmostEqual(rows[0]["cost"], (rows[0]["cme_bp"] + c.BINANCE_BP) / 1e4, places=9)
        rows3 = c.build("BTC", px, chain, close, fund, half, "2023-03-08", "2023-03-31", k=3.0)
        self.assertAlmostEqual(rows3[0]["cost"], 3 * rows[0]["cost"], places=12)


if __name__ == "__main__":
    unittest.main()
