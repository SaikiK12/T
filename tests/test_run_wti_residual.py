import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_wti_residual as wr

T0 = int(datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc).timestamp())   # Tuesday 08:00 Chicago: CME open
OFFSET_BP = {"lighter": 0.0, "hl": 5.0, "kraken": -3.0, "binance": 1.0}
SPREAD_BP = {"lighter": 1.0, "hl": 1.0, "kraken": 10.0, "binance": 1.0}
DEV = (2500, 2530, 10.0)        # Lighter's mid sits 10 bp above its normal level from T0+2500 to T0+2529


def mid(venue, i, dev=DEV):
    bp = OFFSET_BP[venue] + (dev[2] if venue == "lighter" and dev[0] <= i < dev[1] else 0.0)
    return 100.0 * np.exp(bp * 1e-4)


def write_world(root, n=4000, lighter_end=None, dev=DEV):
    """One quote row per second per venue (t = T0 + i seconds exactly) for WTI; sessions cover [T0, T0 + n]."""
    paths = {"lighter": "lighter_trades/quote/WTI", "hl": "commodity_perps/hlbbo/CL",
             "kraken": "commodity_perps/krtick/PF_WTIOILUSD", "binance": "commodity_perps/bnbook/CLUSDT"}
    day = "2026-11-03"
    for v, rel in paths.items():
        i = np.arange(n + 1)
        m = np.array([mid(v, k, dev) for k in i])
        h = SPREAD_BP[v] / 2 * 1e-4
        d = pd.DataFrame(dict(t=(T0 + i) * 1_000_000, bid=m * np.exp(-h), ask=m * np.exp(h),
                              bq=np.ones(n + 1), aq=np.ones(n + 1)))
        if v == "kraken":
            d["suspended"] = 0
        p = Path(root) / rel / day
        p.mkdir(parents=True, exist_ok=True)
        d.to_parquet(p / "000000-1.parquet", index=False)
    iso = lambda s: datetime.fromtimestamp(s, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cp = Path(root) / "commodity_perps"
    pd.DataFrame([dict(venue=v, start_utc=iso(T0), end_utc=iso(T0 + n), seconds=n, messages=1, ended_by="stopped")
                  for v in ("hl", "kraken", "bn_public")]).to_csv(cp / "sessions.csv", index=False)
    le = T0 + (lighter_end if lighter_end is not None else n)
    pd.DataFrame([dict(start_utc=iso(T0), end_utc=iso(le), seconds=le - T0, messages=1, ended_by="stopped")]).to_csv(
        Path(root) / "lighter_trades" / "sessions.csv", index=False)


class WtiResidualTest(unittest.TestCase):
    """Synthetic only: every file read must sit under the temporary root, and the module's real data root is pointed at
    a path that does not exist, so a default argument or a stray global cannot reach data/ (orchestrator, 2026-11-09)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.real = [(wr, "DATA", wr.DATA), (wr, "MANIFEST", wr.MANIFEST), (wr, "LANE", wr.LANE)]
        wr.DATA = wr.MANIFEST = wr.LANE = Path("/nonexistent-real-data")
        root = self.root

        def guard(fn):
            def wrapped(path, *a, **k):
                if not Path(path).resolve().is_relative_to(root):
                    raise AssertionError(f"synthetic test opened a file outside its root: {path}")
                return fn(path, *a, **k)
            return wrapped
        self.patches = [mock.patch.object(wr.pd, "read_parquet", guard(pd.read_parquet)),
                        mock.patch.object(wr.pd, "read_csv", guard(pd.read_csv))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        for mod, name, val in self.real:
            setattr(mod, name, val)
        self.tmp.cleanup()

    def test_guard_refuses_real_data(self):
        with self.assertRaises(AssertionError):
            wr.load_sessions(Path(wr.ROOT) / "data", "hl")

    def test_trial_count(self):
        self.assertEqual(wr.TRIALS, 19 * 2 * 3 * 2)

    def test_cme_clock(self):
        ts = lambda *a: datetime(*a, tzinfo=timezone.utc).timestamp()
        cases = [(ts(2026, 10, 29, 21, 30), True),     # Thu 16:30 CDT: daily break
                 (ts(2026, 10, 29, 20, 30), False),    # Thu 15:30 CDT
                 (ts(2026, 11, 3, 22, 30), True),      # Tue 16:30 CST (after the DST change)
                 (ts(2026, 11, 3, 21, 30), False),     # Tue 15:30 CST
                 (ts(2026, 10, 31, 12, 0), True),      # Saturday
                 (ts(2026, 11, 1, 22, 30), True),      # Sun 16:30 CST
                 (ts(2026, 11, 1, 23, 30), False),     # Sun 17:30 CST: reopened
                 (ts(2026, 10, 30, 21, 30), True)]     # Fri 16:30 CDT: weekend close
        self.assertEqual(wr.cme_closed([c[0] for c in cases]).tolist(), [c[1] for c in cases])

    def test_planted_deviation_one_trade_converges(self):
        write_world(self.root)
        grid, sig, Q, S, venues = wr.build(self.root, "WTI")
        self.assertEqual(grid[0], T0 + wr.WARMUP_S)
        i = np.searchsorted(grid, T0 + 2500)
        self.assertAlmostEqual(sig["lighter"]["d"][i], 10.0, places=6)
        self.assertAlmostEqual(sig["lighter"]["d"][i - 1], 0.0, places=6)
        for v in ("hl", "kraken", "binance"):
            self.assertEqual(len(wr.triggers(sig, v, 2.0)), 0)
        t = wr.trades(grid, sig, Q, S, venues, "lighter", 2.0, 60)
        self.assertEqual(len(t), 1)
        r = t.iloc[0]
        self.assertEqual((r.s, r.te, r.tx, r.side), (T0 + 2500, T0 + 2501.3, T0 + 2561.3, -1.0))
        self.assertAlmostEqual(r.gross, 10.0, places=6)
        self.assertAlmostEqual(r.cost, 1.0, places=6)
        self.assertTrue(r.thin)
        self.assertAlmostEqual(r.age, 0.0)
        d = wr.diagnostics(t, Q, S, venues).iloc[0]
        self.assertAlmostEqual(d.closed_share, 1.0, places=6)
        self.assertAlmostEqual(d.venue_move, 10.0, places=6)
        self.assertAlmostEqual(d.others_toward, 0.0, places=6)

    def test_non_overlap_spacing(self):
        write_world(self.root)
        grid, sig, Q, S, venues = wr.build(self.root, "WTI")
        t = wr.trades(grid, sig, Q, S, venues, "lighter", 2.0, 10)
        self.assertEqual(t.s.tolist(), [T0 + 2500, T0 + 2512, T0 + 2524])
        self.assertTrue(np.allclose(t.gross.to_numpy(), [0.0, 0.0, 10.0]))
        self.assertTrue(np.allclose(wr.net(t, 1), [-1.0, -1.0, 9.0]))
        self.assertTrue(np.allclose(wr.net(t, 3), [-3.0, -3.0, 7.0]))

    def test_exit_after_feed_end_is_skipped(self):
        write_world(self.root, lighter_end=2540)
        grid, sig, Q, S, venues = wr.build(self.root, "WTI")
        self.assertEqual(len(wr.trades(grid, sig, Q, S, venues, "lighter", 2.0, 60)), 0)
        self.assertEqual(len(wr.trades(grid, sig, Q, S, venues, "lighter", 2.0, 10)), 3)

    def test_no_deviation_no_trade(self):
        write_world(self.root, dev=(0, 0, 0.0))
        grid, sig, Q, S, venues = wr.build(self.root, "WTI")
        for v in venues:
            self.assertEqual(len(wr.triggers(sig, v, 2.0)), 0)

    def test_end_to_end_and_manifest(self):
        write_world(self.root)
        man = self.root / "manifest.json"
        self.assertEqual(wr.write_manifest(self.root, man), 6)
        self.assertEqual(wr.check_manifest(self.root, man), 6)
        res = wr.run(self.root, out=self.root / "lane")
        self.assertEqual(res["verdict"], "INCONCLUSIVE")         # one primary trade
        self.assertEqual(res["primary_cell"]["n"], 1)
        self.assertAlmostEqual(res["primary_cell"]["net_1x"], 9.0, places=6)
        cells = pd.read_csv(self.root / "lane" / "results" / "cells.csv")
        self.assertEqual(len(cells), wr.TRIALS)
        self.assertTrue((self.root / "lane" / "results" / "summary.json").exists())
        json.loads((self.root / "lane" / "results" / "summary.json").read_text())
        f = next((self.root / "commodity_perps").rglob("*.parquet"))
        d = pd.read_parquet(f)
        d.loc[0, "bid"] += 0.01
        d.to_parquet(f, index=False)
        with self.assertRaises(wr.prereg.PreregError):
            wr.check_manifest(self.root, man)

    def test_block_bootstrap_and_verdict(self):
        rng = np.random.default_rng(0)
        ci = wr.block_boot(np.ones(100), np.repeat(np.arange(10), 10), rng)
        self.assertEqual((ci["mean"], ci["lo"], ci["hi"], ci["p_le0"], ci["blocks"]), (1.0, 1.0, 1.0, 0.0, 10))
        self.assertEqual(wr.verdict(100, ci, 0.5), "PASS")
        self.assertEqual(wr.verdict(100, dict(ci, lo=-0.1), 0.5), "NULL")
        self.assertEqual(wr.verdict(100, ci, -0.1), "NULL")
        self.assertEqual(wr.verdict(20, ci, 0.5), "INCONCLUSIVE")
        self.assertEqual(wr.verdict(100, dict(ci, blocks=3), 0.5), "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
