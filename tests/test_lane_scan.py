import json
import tempfile
import unittest
from pathlib import Path

from scripts import lane_scan as s


class LaneScan(unittest.TestCase):
    def test_csv_and_json_cells_are_grouped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "experiments" / "demo_v1" / "results"
            d.mkdir(parents=True)
            (d / "books.csv").write_text(
                "book,window,cmult,gross_bp_day,cost_bp_day,days,mean_bp_day,t_nw10\n"
                "A,validation,1,20,5,500,15,2.5\nA,validation,2,20,10,500,10,1.8\n"
                "B,discovery,1,4,6,500,-2,-0.5\nC,holdout,1,-3,2,400,-5,-1.0\nD,holdout,1,9,3,400,6,1.2\n")
            (d / "report.json").write_text(json.dumps(
                {"micro_1x": {"ann_net_pct": 3.0, "nw_t": 3.1, "ann_gross_pct": 7.0},
                 "micro_2x": {"ann_net_pct": -1.0, "nw_t": -1.2, "ann_gross_pct": 7.0},
                 "x": {"valid": {"gross": {"ann_pct": 99.0, "t_nw": 9.0}}}}))
            cells = s.harvest([str(d / "books.csv")]) + s.harvest_json([str(d / "report.json")])
            g = {(c["label"], c["window"]): c for c in s.classify(cells)}
        self.assertEqual(g[("A", "validation")]["group"], "robust")
        self.assertTrue(g[("A", "validation")]["oos"])
        self.assertEqual(g[("B", "discovery")]["group"], "cost_killed")
        self.assertAlmostEqual(g[("B", "discovery")]["break_even_cost_multiple"], 0.67)
        self.assertEqual(g[("C", "holdout")]["group"], "gross_negative")
        self.assertEqual(g[("D", "holdout")]["group"], "underpowered")
        micro = g[("micro", "micro")]
        self.assertEqual(micro["group"], "underpowered")             # t >= 2 at 1x but negative at 2x
        self.assertAlmostEqual(micro["net_2x_bp_day"], -1.0 / 3.65)
        self.assertFalse(any("gross" in k[0] for k in g))           # a gross branch is not read as a net


if __name__ == "__main__":
    unittest.main()
