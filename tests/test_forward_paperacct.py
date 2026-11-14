import unittest

import numpy as np
import pandas as pd

from scripts import forward_paperacct as P


def book(n=5, carry=0.001, flow=0.0, events=0.0, final=None, start="2026-11-07"):
    days = pd.date_range(start, periods=n, freq="D").strftime("%Y-%m-%d")
    b = pd.DataFrame({"day": days, "carry": carry, "carry_2x": carry - 0.0001, "flow": flow, "flow_2x": flow,
                      "events": events, "events_2x": events})
    b["final"] = True if final is None else final
    return b


class Account(unittest.TestCase):
    def test_pots_compound_without_rebalancing(self):
        s, closed = P.statement(book(n=3, carry=0.01))
        pot = P.CAPITAL / 3
        self.assertAlmostEqual(s["pot_carry"].iloc[-1], pot * 1.01 ** 3)
        self.assertAlmostEqual(s["pot_flow"].iloc[-1], pot)
        self.assertAlmostEqual(s["balance"].iloc[-1], pot * 1.01 ** 3 + 2 * pot)
        self.assertAlmostEqual(s["pnl_day"].iloc[0], pot * 0.01)
        self.assertEqual(closed, {"carry": None, "flow": None, "events": None})

    def test_days_before_open_are_not_counted(self):
        b = pd.concat([book(n=3, carry=0.5, start="2026-11-01"), book(n=2, carry=0.0)])
        s, _ = P.statement(b)
        self.assertEqual(s.index[0], P.OPEN)
        self.assertAlmostEqual(s["balance"].iloc[-1], P.CAPITAL)

    def test_missing_value_is_idle_cash(self):
        b = book(n=2, carry=0.01)
        b.loc[1, "carry"] = np.nan
        b.loc[1, "carry_2x"] = np.nan
        s, _ = P.statement(b)
        self.assertAlmostEqual(s["pot_carry"].iloc[1], s["pot_carry"].iloc[0])

    def test_pot_closes_at_half_and_keeps_its_cash(self):
        b = book(n=4, flow=-0.3)
        s, closed = P.statement(b)
        pot = P.CAPITAL / 3
        self.assertEqual(closed["flow"], b.day.iloc[1])           # 0.7 then 0.49 of the pot
        self.assertAlmostEqual(s["pot_flow"].iloc[-1], pot * 0.49)

    def test_cost_multiples(self):
        s, _ = P.statement(book(n=1, carry=0.003))
        pot = P.CAPITAL / 3
        self.assertAlmostEqual(s["balance_2x"].iloc[0] - 2 * pot, pot * 1.0029)
        self.assertAlmostEqual(s["balance_3x"].iloc[0] - 2 * pot, pot * 1.0028)

    def test_official_stops_at_last_final_day(self):
        s, _ = P.statement(book(n=5, final=[True, True, False, True, False]))
        self.assertEqual(len(P.official(s)), 4)
        s2, _ = P.statement(book(n=2, final=[False, False]))
        self.assertEqual(len(P.official(s2)), 0)

    def test_decisions(self):
        rng = np.random.default_rng(0)
        up = book(n=200, carry=0.0)
        up["carry"] = 0.003 + rng.normal(0, 0.001, 200)
        up["carry_2x"] = up["carry"] - 0.0002
        o = P.official(P.statement(up)[0])
        d = P.decide(o, [])
        self.assertEqual([x["verdict"] for x in d], ["GAIN"])
        self.assertEqual(P.decide(o, [{"look": "180", "verdict": "GAIN"}]), [])
        down = book(n=200, carry=-0.0001)
        self.assertEqual(P.decide(P.official(P.statement(down)[0]), [])[0]["verdict"], "LOSS")
        short = book(n=100, carry=0.003)
        self.assertEqual(P.decide(P.official(P.statement(short)[0]), []), [])

    def test_french_statement_renders(self):
        s, closed = P.statement(book(n=3))
        st = {"updated": "x", "official": P.summary(P.official(s)), "provisional": P.summary(s), "closed": closed,
              "next_look": 180}
        self.assertIn("Relevé", P.french(st))


if __name__ == "__main__":
    unittest.main()
