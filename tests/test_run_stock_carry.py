import unittest

import numpy as np
import pandas as pd

from scripts import run_stock_carry as sc

H, DAY = sc.H, sc.DAY


def world(rates, price=100.0, weeks=12, divs=None, splits=None, cash_mult=None):
    """Flat prices (perp == cash unless cash_mult), constant funding rate per 8 h per name. No file is read."""
    sessions = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-02-02", periods=weeks * 5)]
    t0 = sc.ny_close_ms(sessions[0]) - 30 * DAY
    t1 = sc.ny_close_ms(sessions[-1]) + 2 * H
    hours = np.arange(t0 - t0 % H, t1, H)
    ft = np.arange(t0 - t0 % (8 * H), t1, 8 * H)
    names, perp, funding, cash, events, taker = [], {}, {}, {}, {}, {}
    for i, r in enumerate(rates):
        s = f"N{i}STOCK_USDT"
        perp[s] = pd.DataFrame({"t": hours, "close": price, "high": price, "amount": 1e6})
        funding[s] = pd.DataFrame({"t": ft, "rate": r})
        c = np.full(len(sessions), price * (cash_mult or {}).get(i, 1.0))
        cash[s] = pd.DataFrame({"date": sessions, "close": c, "volume": 1e6})
        events[s] = {"div": (divs or {}).get(i, {}), "split": set((splits or {}).get(i, set()))}
        taker[s] = 2e-4
        names.append(s)
    tb = pd.DataFrame({"t": hours[::24], "rate": 0.04})
    return sc.Universe(names, perp, funding, cash, events, sessions, taker, tb)


class StockCarryTest(unittest.TestCase):
    def test_symbols_and_fees(self):
        self.assertEqual(sc.yahoo_symbol("AAPLSTOCK"), "AAPL")
        self.assertEqual(sc.yahoo_symbol("BRKBSTOCK"), "BRK-B")
        self.assertEqual(sc.yahoo_symbol("TESLA"), "TSLA")
        self.assertIsNone(sc.yahoo_symbol("NAS100"))
        self.assertEqual(sc.commission(1000.0, 100.0), 1.0)            # 10 shares: the 1.00 minimum
        self.assertAlmostEqual(sc.commission(100_000.0, 10.0), 50.0)   # 10,000 shares x 0.005
        self.assertAlmostEqual(sc.commission(50.0, 1.0), 0.5)          # capped at 1% of value

    def test_close_clock(self):
        self.assertEqual(pd.Timestamp(sc.ny_close_ms("2026-07-01"), unit="ms").hour, 20)   # EDT
        self.assertEqual(pd.Timestamp(sc.ny_close_ms("2026-01-07"), unit="ms").hour, 21)   # EST
        self.assertEqual(pd.Timestamp(sc.ny_close_ms("2025-12-24"), unit="ms").hour, 18)   # early close

    def test_funding_only_accounting(self):
        u = world([5e-4, 2e-4, 0.0])
        dates = sc.rebalance_dates(u.sessions, u.sessions[0], u.sessions[-1])
        res = sc.simulate(u, dates, 14, 1, 0.20)
        self.assertEqual({r["sym"] for r in res["log"]}, {"N0STOCK_USDT"})
        entry = res["log"][0]["entry"]
        n = sc.CAPITAL * 2 / 3
        q = n / 100.0
        b = sc.Book(u, "N0STOCK_USDT")
        fund = b.funding_cash(q, sc.ny_close_ms(entry), sc.ny_close_ms(dates[-1]))
        side = (2e-4 + sc.PERP_HALF_SPREAD) * n + sc.commission(n, 100.0) + sc.STOCK_HALF_SPREAD * n
        self.assertAlmostEqual(res["weekly"].sum(), fund - 2 * side, places=6)
        self.assertAlmostEqual(res["parts"]["perp"] + res["parts"]["stock"], 0.0)
        three = sc.simulate(u, dates, 14, 1, 0.20, mult=3)
        self.assertAlmostEqual(three["weekly"].sum(), fund - 6 * side, places=6)

    def test_dividend_net_of_withholding(self):
        u = world([5e-4])
        dates = sc.rebalance_dates(u.sessions, u.sessions[0], u.sessions[-1])
        ex = u.sessions[30]
        u.events["N0STOCK_USDT"]["div"] = {ex: 2.0}
        u.cash["N0STOCK_USDT"].loc[u.cash["N0STOCK_USDT"].date >= ex, "close"] = 98.0   # ex-date drop
        res = sc.simulate(u, dates, 14, 1, 0.20)
        qs = sc.CAPITAL * 2 / 3 / 100.0
        self.assertAlmostEqual(res["parts"]["stock"] + res["parts"]["div"], qs * (-2.0 + 2.0 * (1 - sc.WHT)))

    def test_split_ratio_and_threshold_exclude(self):
        u = world([5e-4], cash_mult={0: 1.2})                      # perp/cash outside the band: never entered
        dates = sc.rebalance_dates(u.sessions, u.sessions[0], u.sessions[-1])
        self.assertEqual(sc.simulate(u, dates, 14, 1, 0.20)["log"], [])
        u = world([1e-4])                                          # 10.95%/yr < 20%: never entered
        self.assertEqual(sc.simulate(u, dates, 14, 1, 0.20)["log"], [])
        u = world([5e-4], splits={0: set(world([0]).sessions)})    # a split inside every hold: never entered
        self.assertEqual(sc.simulate(u, dates, 14, 1, 0.20)["log"], [])

    def test_hysteresis_and_ranking(self):
        u = world([3e-4, 5e-4, 2.5e-4])                            # 32.9%, 54.8%, 27.4%/yr
        dates = sc.rebalance_dates(u.sessions, u.sessions[0], u.sessions[-1])
        res = sc.simulate(u, dates, 14, 2, 0.20)
        self.assertEqual({r["sym"] for r in res["log"]}, {"N0STOCK_USDT", "N1STOCK_USDT"})

    def test_guard_blocks_file_reads(self):
        sc.GUARD["on"] = True
        try:
            with self.assertRaises(RuntimeError):
                sc.load()
        finally:
            sc.GUARD["on"] = False

    def test_stats_and_verdict(self):
        ci = sc.block_boot(np.full(30, 0.01), np.random.default_rng(0), reps=200)
        self.assertAlmostEqual(ci["lo"], 0.01)
        self.assertGreater(sc.nw_t(np.r_[np.full(20, 0.02), np.full(20, 0.0)]), 0)
        good = {"excess_over_tbill": 0.05, "max_rally": 0.1}
        self.assertEqual(sc.verdict(good, good, {"lo": 0.001}, 1.0, 30)[0], "PASS")
        self.assertEqual(sc.verdict(dict(good, max_rally=0.6), good, {"lo": 0.001}, 1.0, 30)[0], "PARTIAL")
        self.assertEqual(sc.verdict(good, good, {"lo": -0.001}, 1.0, 30)[0], "NULL")
        self.assertEqual(sc.verdict(good, good, {"lo": 0.001}, 1.0, 10)[0], "INCONCLUSIVE")

    def test_dry_run_is_guarded(self):
        out = sc.dry_run()
        self.assertEqual(len(out["cells"]), 12)
        self.assertFalse(sc.GUARD["on"])


if __name__ == "__main__":
    unittest.main()
