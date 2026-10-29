import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import eventlag_gaps as g  # noqa: E402

T = "2026-10-29T14:30:00Z"


def write(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


class GapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def sessions(self, bn, hl, lighter):
        cols = ["venue", "start_utc", "end_utc", "seconds", "messages", "ended_by"]
        write(self.root / "data/commodity_perps/sessions.csv",
              [dict(zip(cols, ["bn_public", *b, 0, 0, ""])) for b in bn] + [dict(zip(cols, ["hl", *h, 0, 0, ""])) for h in hl],
              cols)
        write(self.root / "data/lighter_trades/sessions.csv",
              [{"start_utc": s, "end_utc": e, "seconds": 0, "messages": 0, "ended_by": ""} for s, e in lighter],
              ["start_utc", "end_utc", "seconds", "messages", "ended_by"])

    def test_boundary_inside_window_marks_only_that_feed(self):
        self.sessions(bn=[("2026-10-29T14:00:00Z", "2026-10-29T14:30:20Z")], hl=[("2026-10-29T13:00:00Z", "2026-10-29T14:10:00Z")],
                      lighter=[("2026-10-29T13:00:00Z", "2026-10-29T14:10:00Z")])
        f = g.flags(T, self.root)
        self.assertEqual((f["binance"], f["hl"], f["lighter"], f["clean"]), (True, False, False, False))

    def test_lighter_reconnect_just_before_window_is_clean_and_just_inside_is_not(self):
        for end, clean in (("2026-10-29T14:29:40Z", True), ("2026-10-29T14:29:49Z", False), ("2026-10-29T14:31:10Z", True),
                           ("2026-10-29T14:31:05Z", False)):
            self.sessions(bn=[], hl=[], lighter=[("2026-10-29T14:00:00Z", end)])
            self.assertEqual(g.flags(T, self.root)["lighter"], not clean, end)

    def test_missing_files_are_clean(self):
        self.assertTrue(g.flags(T, self.root)["clean"])

    def test_decision_cells_filter_to_clean_releases(self):
        rows = []
        for e, rel, gross in (("ng", "A", 30.0), ("ng", "B", -10.0), ("ng", "C", 50.0)):
            rows.append({"event": e, "release_utc": rel, "kind": "event", "follower": "lighter", "lag_s": 1.0, "status": "ok",
                         "lag_ok": True, "gross": gross})
        rows.append({"event": "ng", "release_utc": "A", "kind": "placebo-2d", "follower": "lighter", "lag_s": 1.0, "status": "ok",
                     "lag_ok": True, "gross": 999.0})
        rows.append({"event": "ng", "release_utc": "C", "kind": "event", "follower": "hl", "lag_s": 1.0, "status": "ok",
                     "lag_ok": True, "gross": 999.0})
        out = g.decision_cells(pd.DataFrame(rows), {("ng", "A"), ("ng", "C")})
        self.assertEqual(out["ng"]["n"], 2)
        self.assertAlmostEqual(out["ng"]["mean_gross"], 40.0)
        self.assertAlmostEqual(out["ng"]["mean_net_2x"], 40.0 - 2 * 2 * 2.5)


if __name__ == "__main__":
    unittest.main()
