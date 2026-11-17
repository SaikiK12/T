import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from scripts import run_cmeterm as r1
from scripts import run_cmeterm_grid as g
from tests.test_cmeterm import world


class Grid(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.multiple(r1, FIRST_MONTH="2015-06", LAST_DAY="2018-12-31")
        self.p.start()
        self.cal, self.settle, self.ranks = world(True)
        self.w = g.World(self.cal, self.settle, self.ranks)

    def tearDown(self):
        self.p.stop()

    def test_the_grid_is_432_distinct_variants(self):
        cs = g.configs()
        self.assertEqual(len(cs), 432)
        self.assertEqual(len({g.name(c) for c in cs}), 432)
        self.assertIn(g.PRIMARY_R503, cs)

    def test_r503s_rule_reproduces_r503s_engine_exactly(self):
        x = g.run_config(self.w, g.PRIMARY_R503)
        rows, _ = r1.build(self.cal, self.settle, self.ranks)
        net = x["gross"] - x["cost"]
        self.assertEqual(len(rows), len(net))
        for r, n, gr in zip(rows, net, x["gross"]):
            self.assertAlmostEqual(r["net"], n, places=12)
            self.assertAlmostEqual(r["gross"], gr, places=12)

    def test_schedules(self):
        m = self.w.schedule("1m")
        two = self.w.schedule("2w")
        three = self.w.schedule("3m")
        self.assertTrue(all(sig and mon for _, sig, mon in m.values()))
        self.assertEqual(len(two), 2 * len(m))
        self.assertTrue(any(d.day >= 15 for d, _, _ in two.values()))
        sig3 = [d for d, sig, _ in three.values() if sig]
        self.assertTrue(all(d.month in (3, 6, 9, 12) for d in sig3))
        self.assertEqual(len(three), len(m))                       # monthly roll dates kept
        for e, (d, _, _) in m.items():
            self.assertLess(d, e)

    def test_select_band_gate_and_confidence(self):
        d = [x for x in self.cal if x >= dt.date(2016, 3, 1)][0]
        e = self.cal[self.cal.index(d) + 1]
        cands = self.w.candidates(d, e)
        base = dict(g.PRIMARY_R503, k=2)
        t = g.select(base, self.w, d, cands, {}, {})
        self.assertEqual(sum(v > 0 for v in t.values()), 2)
        self.assertAlmostEqual(sum(v for v in t.values() if v > 0), 0.5)
        order = sorted(cands, key=lambda r: -cands[r]["carry"])
        third = order[2]
        held = {third: 0.25}                                      # ranked third: kept with a band, dropped without
        self.assertIn(third, g.select(dict(base, band=True), self.w, d, cands, held, {}))
        self.assertNotIn(third, g.select(base, self.w, d, cands, held, {}))
        costly = {r: dict(x, rate=1.0) for r, x in cands.items()}  # no carry covers a 100% cost: no book
        self.assertEqual(g.select(dict(base, gate=True), self.w, d, costly, {}, {}), {})
        conf = g.select(dict(base, weight="conf"), self.w, d, cands, {}, {})
        z = g.zscores({r: x["carry"] for r, x in cands.items()})
        longs = [r for r, v in conf.items() if v > 0]
        a, b = longs
        self.assertAlmostEqual(conf[a] / conf[b], (abs(z[a]) / cands[a]["sd"]) / (abs(z[b]) / cands[b]["sd"]))

    def test_walk_forward_uses_only_the_past(self):
        days = [dt.date(2012, 1, 2) + dt.timedelta(days=i) for i in range(365 * 4)]
        T = len(days)
        rng = np.random.default_rng(1)
        G = rng.normal(0, 0.01, (3, T))
        G[1, [i for i, d in enumerate(days) if d.year < 2014]] += 0.01          # best before 2014
        C = np.zeros((3, T))
        W = np.zeros((3, T, 2))
        R = np.zeros((T, 2))
        net, _, _, d1, picks = g.walk_forward(G, C, W, R, days)
        self.assertEqual(picks[2014], 1)
        G2 = G.copy()
        G2[2, [i for i, d in enumerate(days) if d.year >= 2014]] += 1.0         # a great future changes no pick
        self.assertEqual(g.walk_forward(G2, C, W, R, days)[4][2014], 1)
        self.assertEqual(d1[0], dt.date(2014, 1, 1))

    def test_verdict(self):
        ok = {"ann_net_pct": 3.0, "nw_t": 2.5}
        self.assertEqual(g.verdict_of(ok, {"ann_net_pct": 1.0}, 0.01), "GRID_PASS")
        self.assertEqual(g.verdict_of(ok, {"ann_net_pct": 1.0}, 0.20), "GRID_WEAK")
        self.assertEqual(g.verdict_of(ok, {"ann_net_pct": -1.0}, 0.01), "GRID_WEAK")
        self.assertEqual(g.verdict_of({"ann_net_pct": -0.1, "nw_t": -1}, {}, 0.01), "GRID_NULL")

    def test_switch_cost_is_charged(self):
        days = [dt.date(2013, 1, 1) + dt.timedelta(days=i) for i in range(800)]
        T = len(days)
        G = np.zeros((2, T))
        G[0, :] = 0.001
        C = np.zeros((2, T))
        W = np.zeros((2, T, 1))
        W[0, :, 0] = 0.5
        R = np.full((T, 1), 0.001)
        net, gross, cost, d1, picks = g.walk_forward(G, C, W, R, days)
        self.assertAlmostEqual(cost[0], 0.5 * 0.001)                          # entering the book at the start

    def test_analyze_and_run_on_a_small_grid(self):
        small = mock.patch.multiple(g, SIGNALS=("carry", "mom12"), KS=(2, "third"), WEIGHTS=("ivol",),
                                    FREQS=("1m", "3m"), BANDS=(False,), GATES=(False, True), WF_FIRST_YEAR=2017,
                                    PBO_BLOCKS=8, SPA_BOOT=100)
        with small, tempfile.TemporaryDirectory() as tmp:
            w = (self.cal, self.settle, self.ranks, 0)
            with mock.patch.object(g, "LANE", Path(tmp)), mock.patch.object(g, "check_inputs", lambda: []), \
                    mock.patch("lab.prereg.verify", lambda p: None), mock.patch.object(g.m3, "load", lambda: w), \
                    mock.patch.object(g, "PRIMARY_R503", dict(g.PRIMARY_R503)):
                g.run()
            rep = json.loads((Path(tmp) / "results" / "report.json").read_text())
            self.assertEqual(rep["grid_size"], 16)
            self.assertIn(rep["verdict"], ("GRID_PASS", "GRID_WEAK", "GRID_NULL"))
            for key in ("walk_forward_1x", "walk_forward_2x", "walk_forward_3x", "walk_forward_picks", "pbo", "spa",
                        "best_full_sample", "marginals_1x", "walk_forward_gross_by_root_pct",
                        "walk_forward_gross_by_leg_pct", "walk_forward_break_even_cost_multiple"):
                self.assertIn(key, rep)
            self.assertGreater(rep["walk_forward_1x"]["ann_net_pct"], 0)         # the planted carry is found
            self.assertTrue((Path(tmp) / "results" / "grid.csv").exists())


if __name__ == "__main__":
    unittest.main()
