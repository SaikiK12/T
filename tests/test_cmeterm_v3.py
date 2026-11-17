import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import run_cmeterm as r1
from scripts import run_cmeterm_v3 as m
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


class Guards(unittest.TestCase):
    def setUp(self):
        m.UNIT_LOG.update({"fallback_rows": 0, "mismatch_rows": 0, "mismatches": {}})

    def test_missing_or_zero_units_take_the_contract_unit(self):
        base = {"snap": "2010-06-07", "expiration": "2010-08-20T19:30Z", "min_price_increment": "0.01"}
        rows = [dict(base, instrument_id="1", raw_symbol="CLQ0", unit_of_measure_qty=None),
                dict(base, instrument_id="2", raw_symbol="ZCU0", unit_of_measure_qty="0", min_price_increment="0.25"),
                dict(base, instrument_id="3", raw_symbol="GCQ0", unit_of_measure_qty="1000"),
                dict(base, instrument_id="4", raw_symbol="HOQ0", unit_of_measure_qty="42000", expiration=None)]
        idx = m.info_index(rows, {1: "CL", 2: "ZC", 3: "GC", 4: "HO"})
        self.assertEqual(idx[1][0][3], 1000.0)
        self.assertEqual(idx[2][0][3], 50.0)                      # 5000 bushels, quoted in cents
        self.assertEqual(idx[3][0][3], 1000.0)                    # a positive value is kept, and reported
        self.assertNotIn(4, idx)                                  # no expiry: dropped
        self.assertEqual(m.UNIT_LOG["fallback_rows"], 2)
        self.assertEqual(m.UNIT_LOG["mismatch_rows"], 1)
        self.assertEqual(m.UNIT_LOG["mismatches"], {"GC": 1000.0})

    def test_incomplete_settlement_rows_are_dropped(self):
        self.assertTrue(m.complete({"price": "1.5", "instrument_id": "3", "stat_type": "3", "update_action": "1"}))
        self.assertFalse(m.complete({"price": "", "instrument_id": "3", "stat_type": "3", "update_action": "1"}))
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "settle_CL.csv").write_text("ts_recv,instrument_id,ts_ref,price,stat_type,update_action,stat_flags,"
                                             "symbol\n2020-01-03T00:50Z,5,2020-01-02,,3,1,3,CL.n.0\n"
                                             "2020-01-03T00:50Z,5,2020-01-02,61.2,3,1,3,CL.n.0\n")
            (d / "resolve.json").write_text(json.dumps({"CL.n.0": [{"d0": "2020-01-02", "d1": "2020-01-03",
                                                                     "s": "5"}]}))
            with mock.patch.multiple(m, DATA=d, OLD=d), mock.patch.object(m, "read_defs", lambda: []):
                cal, settle, ranks, missing = m.load()
            self.assertEqual(settle, {(5, dt.date(2020, 1, 2)): 61.2})
            self.assertEqual(m.UNIT_LOG["settlement_rows_dropped"], 1)

    def test_old_snapshots_must_match_r504s_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "defs").mkdir()
            (d / "defs" / "def_q2010-07-01.csv.zst").write_bytes(b"abc")
            (d / "manifest_defs.csv").write_text("file,ids,start,end,quoted_usd,bytes,sha256\n"
                                                 "def_q2010-07-01.csv.zst,1,a,b,0,3,"
                                                 "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad\n")
            with mock.patch.object(m, "OLD", d):
                self.assertEqual(len(m.old_defs_checked()), 1)
                (d / "defs" / "def_q2010-07-01.csv.zst").write_bytes(b"abd")
                with self.assertRaises(SystemExit):
                    m.old_defs_checked()

    def test_a_raw_file_on_disk_is_reduced_not_refetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            name = "GLBX.MDP3_CL.n.0+CL.n.1+CL.n.2_statistics_2026-11-02_2026-11-16.csv.zst"
            (d / name).write_bytes(b"x")
            fd = mock.MagicMock()
            with mock.patch.multiple(m, DATA=d, FETCH_START="2026-11-02", FETCH_END="2026-11-16"), \
                    mock.patch.dict("sys.modules", {"scripts.fetch_databento": fd}), \
                    mock.patch("scripts.fetch_databento", fd, create=True), \
                    mock.patch.object(r1, "reduce_stats", lambda path, out: 7):
                m.fetch_root("CL", "k", [0.0], lambda msg: None)
            fd.fetch.assert_not_called()
            self.assertFalse((d / name).exists())
            self.assertIn("|statistics|2026-11-02|2026-11-16", (d / "reduced.csv").read_text())


if __name__ == "__main__":
    unittest.main()
