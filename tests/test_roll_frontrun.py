"""R529's event construction on a synthetic settlement map."""
import datetime as dt
import unittest

from scripts import run_roll_frontrun as rf


def world(drop=None):
    """One root (CL), contracts expiring on the 20th of each month 2020-01..2020-12, settlements on weekdays; prices:
    contract expiring in month k trades at 50 + k, and on 2020-03 business day 9 the June contract (B for March) rises
    by 1."""
    exps = {100 + k: dt.date(2020, k, 20) for k in range(1, 13)}
    ranks = {}
    d = dt.date(2020, 1, 1)
    while d <= dt.date(2020, 12, 31):                     # the three nearest unexpired contracts each day
        near = sorted((e, iid) for iid, e in exps.items() if e >= d)[:3]
        ranks[d] = {"CL": {k: (iid, e, 0.01, 1000, "x") for k, (e, iid) in enumerate(near)}}
        d += dt.timedelta(days=1)
    settle = {}
    d = dt.date(2020, 1, 1)
    while d <= dt.date(2020, 12, 31):
        if d.weekday() < 5:
            for iid, e in exps.items():
                if d <= e and (drop is None or (iid, d) != drop):
                    settle[(iid, d)] = 50.0 + (iid - 100)
        d += dt.timedelta(days=1)
    bd9 = [x for x in sorted({dd for _, dd in settle}) if (x.year, x.month) == (2020, 3)][8]
    if (105, bd9) in settle:
        settle[(105, bd9)] += 1.0
    return settle, ranks, bd9


class Roll(unittest.TestCase):
    def test_events_pick_contracts_by_expiry_month(self):
        settle, ranks, bd9 = world()
        ev = rf.events(settle, ranks, roots=("CL",), first=(2020, 2), last=(2020, 6))
        march = [px for r, ym, px in ev if ym == (2020, 3)][0]
        self.assertEqual(march[("A", 0)], 54.0)            # April contract (iid 104)
        self.assertEqual(march[("B", 9)], 56.0)            # May contract (iid 105): 55, bumped by 1 on BD9
        self.assertAlmostEqual(rf.ret(march, 0, 9), (56.0 / 55.0 - 1) - 0.0)

    def test_missing_settlement_drops_the_event(self):
        _, ranks, bd9 = world()
        settle2, _, _ = world(drop=(105, bd9))
        ev = rf.events(settle2, ranks, roots=("CL",), first=(2020, 3), last=(2020, 3))
        self.assertEqual(ev, [])

    def test_monthly_cost_and_decide(self):
        settle, ranks, _ = world()
        ev = rf.events(settle, ranks, roots=("CL",), first=(2020, 2), last=(2020, 6))
        m = rf.monthly(ev, 0, 9, 0.0002)
        self.assertAlmostEqual(m[(2020, 4)], -0.0002)
        self.assertEqual(rf.decide({"nw_t": 3.0}, {"mean_bp": 1}, [1, 1])[0], "PASS")
        self.assertEqual(rf.decide({"nw_t": 3.0}, {"mean_bp": -1}, [1, 1])[0], "FAIL")


if __name__ == "__main__":
    unittest.main()
