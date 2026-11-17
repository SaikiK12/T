import datetime as dt
import json
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import run_cmeterm as m


def world(planted, seed=7, start=dt.date(2015, 1, 1), end=dt.date(2018, 12, 31)):
    """13 roots, monthly contracts expiring on the 20th. F(t, T) = S_t exp(-c (T - t) / 365.25).
    planted: spot has no drift, so a backwardated curve rolls up into the held contract (carry is earned).
    null: spot drifts by -c, so futures prices have no drift (carry is not earned)."""
    rnd = random.Random(seed)
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    settle, ranks = {}, {}
    for j, root in enumerate(m.ROOTS):
        cbar, noise = rnd.uniform(-0.25, 0.25), 0.0
        logs = math.log(50 + j)
        for t in days:
            noise = 0.98 * noise + rnd.gauss(0, 0.01)
            c = cbar + noise
            drift = 0.0 if planted else -c / 252
            logs += drift + rnd.gauss(0, 0.01)
            exps = []
            y, mo = t.year, t.month
            while len(exps) < 3:
                e = dt.date(y, mo, 20)
                if e > t:
                    exps.append(e)
                y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
            rk = {}
            for i, e in enumerate(exps):
                iid = hash((root, e)) % 10**8
                settle[(iid, t)] = math.exp(logs - c * (e - t).days / 365.25)
                rk[i] = (iid, e, 0.01, 1000.0, f"{root}{e:%y%m}")
            # the far contract has the most open interest once the near one is within 10 days of expiry
            if (exps[0] - t).days < 10:
                rk = {0: rk[1], 1: rk[2], 2: rk[0]}
            ranks.setdefault(t, {})[root] = rk
    return m.calendar(settle, ranks), settle, ranks


class Pieces(unittest.TestCase):
    def test_carry_sign_and_annualization(self):
        day = dt.date(2020, 1, 2)
        n0 = (1, dt.date(2020, 2, 20), 0.01, 10.0, "A")
        n1 = (2, dt.date(2020, 3, 20), 0.01, 10.0, "B")
        settle = {(1, day): 101.0, (2, day): 100.0}
        c, far = m.carry_of(n0, n1, settle, day)
        self.assertAlmostEqual(c, math.log(1.01) * 365.25 / 29)
        self.assertEqual(far[0], 2)
        c2, far2 = m.carry_of(n1, n0, settle, day)          # order of ranks does not matter
        self.assertAlmostEqual(c, c2)
        self.assertEqual(far2[0], 2)
        self.assertIsNone(m.carry_of(n0, n0, settle, day))

    def test_settlement_last_publication(self):
        rows = [{"stat_type": "3", "update_action": "1", "ts_ref": "2020-01-02", "instrument_id": "5",
                 "ts_recv": "2020-01-02T20:00:00Z", "price": "10.0"},
                {"stat_type": "3", "update_action": "1", "ts_ref": "2020-01-02", "instrument_id": "5",
                 "ts_recv": "2020-01-03T00:50:00Z", "price": "10.5"},
                {"stat_type": "4", "update_action": "1", "ts_ref": "2020-01-02", "instrument_id": "5",
                 "ts_recv": "2020-01-03T01:00:00Z", "price": "99"}]
        self.assertEqual(m.settlements_from_rows(rows), {(5, dt.date(2020, 1, 2)): 10.5})

    def test_ranks_take_the_first_record_of_the_day(self):
        base = {"min_price_increment": "0.01", "unit_of_measure_qty": "1000", "raw_symbol": "CLF0"}
        rows = [dict(base, symbol="CL.n.0", ts_recv="2020-01-02T00:00:00Z", instrument_id="1",
                     expiration="2020-01-21T19:30:00Z"),
                dict(base, symbol="CL.n.0", ts_recv="2020-01-02T15:00:00Z", instrument_id="2",
                     expiration="2020-02-20T19:30:00Z")]
        r = m.ranks_from_definitions(rows)
        self.assertEqual(r[dt.date(2020, 1, 2)]["CL"][0][0], 1)
        self.assertEqual(r[dt.date(2020, 1, 2)]["CL"][0][3], 1000.0)
        rows = [dict(rows[0], symbol="ZC.n.0", unit_of_measure_qty="5000")]
        self.assertEqual(m.ranks_from_definitions(rows)[dt.date(2020, 1, 2)]["ZC"][0][3], 50.0)   # cents

    def test_decide_legs_and_weights(self):
        cal, settle, ranks = world(True)
        vols = m.vol_series(cal, settle, ranks)
        d = [x for x in cal if x >= dt.date(2016, 3, 1)][0]
        e = cal[cal.index(d) + 1]
        hold, info = m.decide(d, e, settle, ranks, vols)
        self.assertTrue(info["book"])
        self.assertEqual(len(info["longs"]), info["valid"] // 3)
        self.assertAlmostEqual(sum(w for w, *_ in hold.values() if w > 0), 0.5)
        self.assertAlmostEqual(sum(w for w, *_ in hold.values() if w < 0), -0.5)
        self.assertGreater(info["carry_spread"], 0)

    def test_too_few_roots_means_no_book(self):
        cal, settle, ranks = world(True)
        vols = m.vol_series(cal, settle, ranks)
        d = [x for x in cal if x >= dt.date(2016, 3, 1)][0]
        e = cal[cal.index(d) + 1]
        few = {day: {r: v for r, v in roots.items() if r in ("CL", "GC", "ZC")} for day, roots in ranks.items()}
        hold, info = m.decide(d, e, settle, few, vols)
        self.assertEqual(hold, {})
        self.assertFalse(info["book"])


class Book(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.multiple(m, FIRST_MONTH="2015-06", LAST_DAY="2018-12-31")
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_planted_carry_is_found_and_null_is_not(self):
        cal, settle, ranks = world(True)
        s = m.summarize(m.build(cal, settle, ranks)[0])
        self.assertGreater(s["ann_net_pct"], 0)
        self.assertGreater(s["nw_t"], 2.0)
        cal, settle, ranks = world(False)
        s0 = m.summarize(m.build(cal, settle, ranks)[0])
        self.assertLess(abs(s0["nw_t"]), 2.0)
        self.assertLess(s0["ann_gross_pct"], s["ann_gross_pct"])

    def test_costs_scale_and_entry_is_after_the_decision(self):
        cal, settle, ranks = world(True)
        r1, dec = m.build(cal, settle, ranks)
        r2, _ = m.build(cal, settle, ranks, cost_k=2.0)
        c1, c2 = sum(r["cost"] for r in r1), sum(r["cost"] for r in r2)
        self.assertGreater(c1, 0)
        self.assertAlmostEqual(c2, 2 * c1)
        for x in dec:
            self.assertLess(x["decision"], x["entry"])
        self.assertTrue(any(x["decision"] == x["entry"] for x in m.build(cal, settle, ranks, lag=False)[1]))

    def test_a_changed_contract_pays_both_sides(self):
        cal, settle, ranks = world(True)
        rows, dec = m.build(cal, settle, ranks)
        # every month the held far contract changes in this world: cost per entry is about two gross sides
        entries = {x["entry"] for x in dec if x["book"]}
        per = [r["cost"] for r in rows if r["day"] in entries][1:]
        rate = (m.FEE_USD + m.SLIP_TICKS * 0.01 * 1000.0) / (62 * 1000.0)
        self.assertTrue(all(c > 1.5 * rate for c in per))

    def test_run_end_to_end(self):
        w = world(True)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(m, "LANE", Path(tmp)), mock.patch.object(m, "check_inputs", lambda: []), \
                    mock.patch("lab.prereg.verify", lambda p: None), mock.patch.object(m, "load", lambda: w):
                m.run()
            rep = json.loads((Path(tmp) / "results" / "report.json").read_text())
            self.assertIn(rep["verdict"], ("CARRY_PASS", "CARRY_WEAK", "CARRY_NULL"))
            self.assertEqual(rep["verdict"], "CARRY_PASS")
            for key in ("primary_2x", "primary_3x", "by_year_1x", "equal_weight_1x", "k3_1x", "no_lag_1x",
                        "carry12_1x", "by_sector_gross_pct", "months"):
                self.assertIn(key, rep)
            self.assertTrue((Path(tmp) / "results" / "daily.csv").exists())

    def test_definition_gaps_are_carried_forward(self):
        cal, settle, ranks = world(True)
        sparse = {d: v for i, (d, v) in enumerate(sorted(ranks.items())) if i % 5 == 0}
        rows, dec = m.build(m.calendar(settle, sparse), settle, sparse)
        self.assertTrue(any(x["book"] for x in dec))
        self.assertGreater(len(rows), 500)

    def test_a_zero_or_negative_price_does_not_crash(self):
        cal, settle, ranks = world(True)
        bad = dict(settle)
        for key in list(bad)[::997]:
            bad[key] = 0.0 if key[0] % 2 else -5.0
        rows, _ = m.build(cal, bad, ranks)
        self.assertTrue(all(math.isfinite(r["net"]) for r in rows))

    def test_run_on_a_world_without_a_book(self):
        cal, settle, ranks = world(True)
        few = {d: {r: v for r, v in roots.items() if r in ("CL", "GC", "ZC", "LE", "HE", "NG", "SI", "HG")}
               for d, roots in ranks.items()}
        w = (m.calendar(settle, few), settle, few)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(m, "LANE", Path(tmp)), mock.patch.object(m, "check_inputs", lambda: []), \
                    mock.patch("lab.prereg.verify", lambda p: None), mock.patch.object(m, "load", lambda: w):
                m.run()
            rep = json.loads((Path(tmp) / "results" / "report.json").read_text())
            self.assertEqual(rep["verdict"], "CARRY_NULL")
            self.assertEqual(rep["months"]["with_book"], 0)


if __name__ == "__main__":
    unittest.main()
