import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import run_cmeterm as r1
from scripts import run_cmeterm_v2 as m
from tests.test_cmeterm import world


class Plumbing(unittest.TestCase):
    def test_chunks_and_quarters_cover_the_window(self):
        yc = m.year_chunks()
        self.assertEqual(yc[0], ("2010-06-06", "2011-01-01"))
        self.assertEqual(yc[-1], ("2026-01-01", "2026-11-01"))
        self.assertEqual(len(yc), 17)
        qs = m.quarter_starts()
        self.assertEqual(qs[0], dt.date(2010, 6, 6))
        self.assertEqual(qs[1], dt.date(2010, 7, 1))
        self.assertEqual(qs[-1], dt.date(2026, 10, 1))
        with mock.patch.multiple(m, FETCH_START="2026-11-02", FETCH_END="2026-11-16"):
            self.assertEqual(m.year_chunks(), [("2026-11-02", "2026-11-16")])        # read at call time
            self.assertEqual(m.quarter_starts(), [dt.date(2026, 11, 2)])

    def test_resolve_intervals_and_ranks(self):
        res = {"CL.n.0": [{"d0": "2026-11-02", "d1": "2026-11-04", "s": "11"},
                          {"d0": "2026-11-04", "d1": "2026-11-06", "s": "12"}],
               "CL.n.1": [{"d0": "2026-11-02", "d1": "2026-11-06", "s": "12"}],
               "CL.n.2": [{"d0": "2026-11-02", "d1": "2026-11-06", "s": ""}]}
        iv = m.intervals_from_resolve(res)
        self.assertEqual(iv["CL"][0][1], (dt.date(2026, 11, 4), dt.date(2026, 11, 6), 12))
        self.assertNotIn(2, iv["CL"])                                    # an unmapped interval is dropped
        defs = [{"instrument_id": "11", "snap": "2026-11-02", "raw_symbol": "CLZ6", "expiration": "2026-11-20T19:30Z",
                 "min_price_increment": "0.01", "unit_of_measure_qty": "1000"},
                {"instrument_id": "12", "snap": "2026-11-02", "raw_symbol": "CLF7", "expiration": "2026-12-21T19:30Z",
                 "min_price_increment": "0.01", "unit_of_measure_qty": "1000"},
                {"instrument_id": "12", "snap": "2026-11-03", "raw_symbol": "ZCH7", "expiration": "2027-03-12T18:01Z",
                 "min_price_increment": "0.25", "unit_of_measure_qty": "5000"}]   # id reused by another root
        idx = m.info_index(defs, m.root_of_iids(iv))
        self.assertEqual(len(idx[12]), 1)
        with mock.patch.multiple(m, FETCH_START="2026-11-02", FETCH_END="2026-11-06"):
            ranks, missing = m.ranks_from(iv, idx)
        self.assertEqual(missing, 0)
        self.assertEqual(ranks[dt.date(2026, 11, 3)]["CL"][0][4], "CLZ6")
        self.assertEqual(ranks[dt.date(2026, 11, 5)]["CL"][0][4], "CLF7")
        self.assertEqual(ranks[dt.date(2026, 11, 5)]["CL"][1][3], 1000.0)
        self.assertNotIn(dt.date(2026, 11, 6), ranks)                    # d1 is exclusive

    def test_details_come_from_the_latest_live_snapshot(self):
        idx = {5: [(dt.date(2020, 1, 1), dt.date(2020, 3, 20), 0.01, 1000.0, "CLH0", "CL"),
                   (dt.date(2024, 1, 1), dt.date(2024, 6, 20), 0.01, 1000.0, "CLN4", "CL")]}
        self.assertEqual(m.info_for(idx, 5, dt.date(2020, 2, 1))[4], "CLH0")
        self.assertEqual(m.info_for(idx, 5, dt.date(2024, 2, 1))[4], "CLN4")
        self.assertEqual(m.info_for(idx, 5, dt.date(2023, 12, 20))[4], "CLN4")    # listed later: next snapshot
        self.assertIsNone(m.info_for(idx, 5, dt.date(2024, 7, 1)))


class Report(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.multiple(r1, FIRST_MONTH="2015-06", LAST_DAY="2018-12-31")
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_report_is_r503s_rule(self):
        cal, settle, ranks = world(True)
        rep, prim, dec = m.report(cal, settle, ranks)
        same = r1.summarize(r1.build(cal, settle, ranks)[0])
        self.assertEqual(rep["primary_1x"], same)
        self.assertEqual(rep["verdict"], "CARRY_PASS")

    def test_run_end_to_end(self):
        w = world(True) + (0,)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(m, "LANE", Path(tmp)), mock.patch.object(m, "check_inputs", lambda: []), \
                    mock.patch("lab.prereg.verify", lambda p: None), mock.patch.object(m, "load", lambda: w):
                m.run()
            rep = json.loads((Path(tmp) / "results" / "report.json").read_text())
            self.assertIn(rep["verdict"], ("CARRY_PASS", "CARRY_WEAK", "CARRY_NULL"))
            self.assertEqual(rep["mapped_contract_days_without_details"], 0)
            for key in ("primary_2x", "primary_3x", "by_year_1x", "equal_weight_1x", "k3_1x", "no_lag_1x",
                        "carry12_1x", "by_sector_gross_pct", "months"):
                self.assertIn(key, rep)
            self.assertTrue((Path(tmp) / "results" / "months.csv").exists())


if __name__ == "__main__":
    unittest.main()
