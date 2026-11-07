import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pyarrow as pa

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_cmelead as run  # noqa: E402

T_MS = 1_800_000_000_000          # an anchor in ms; whole seconds so the offsets below are exact


def ts_iso(us):
    s, rem = divmod(int(us), 1_000_000)
    return pd.Timestamp(s, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%S") + f".{rem * 1000:09d}Z"


def write_cme(path, rows):
    """rows: (t_us, action, price). A csv.zst the way Databento sends it (ts_event as an ISO string, extra columns)."""
    lines = ["ts_recv,ts_event,rtype,action,side,price,size,symbol"]
    for t, act, px in rows:
        lines.append(f"{ts_iso(t)},{ts_iso(t)},0,{act},A,{px},1,NG.v.0")
    path.parent.mkdir(parents=True, exist_ok=True)
    with pa.CompressedOutputStream(str(path), "zstd") as f:
        f.write(("\n".join(lines) + "\n").encode())


def world(jump_bp=30.0):
    lo, hi = T_MS * 1000 - 310_000_000, T_MS * 1000 + 75_000_000
    cme = []
    for t in range(lo, hi + 1, 1_000_000):
        cme.append((t, "T", 3.0 * math.exp(jump_bp / 1e4) if t >= T_MS * 1000 + 200_000 else 3.0))
    cme += [(lo + 500_000, "A", 3.0), (lo + 600_000, "C", 0.0)]
    ts = np.arange(lo, hi + 1, 200_000)
    price = np.where(ts >= T_MS * 1000 + 3_000_000, 3.0 * math.exp(jump_bp / 1e4), 3.0)
    fol = pd.DataFrame({"t": ts // 1000, "price": price, "qty": 1.0, "buyer_maker": (np.arange(len(ts)) % 2).astype(bool),
                        "agg_id": np.arange(len(ts))})
    return cme, fol


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def lane(self, kinds=("event",), jump=30.0):
        lane = self.root / "lane"
        lane.mkdir()
        rows = [{"event": "ngs", "release_ms": T_MS, "kind": k, "anchor_ms": T_MS, "lo_ms": T_MS - 310_000,
                 "hi_ms": T_MS + 75_000, "cme": "NG.v.0", "binance": "NATGASUSDT"} for k in kinds]
        pd.DataFrame(rows).to_csv(lane / "windows.csv", index=False)
        cme, fol = world(jump)
        w = next(pd.read_csv(lane / "windows.csv").itertuples())
        with mock.patch.object(run, "CME", self.root / "cme"):
            write_cme(run.cme_path(w), cme)
        (self.root / "bn" / "NATGASUSDT").mkdir(parents=True)
        fol.to_parquet(self.root / "bn" / "NATGASUSDT" / f"{T_MS}.parquet", index=False)
        return lane

    def test_load_cme_keeps_only_trades_in_time_order_in_microseconds(self):
        p = self.root / "x.csv.zst"
        write_cme(p, [(2_000_000, "T", 3.1), (1_000_000, "T", 3.0), (1_500_000, "A", 9.9), (3_000_000, "T", 0.0)])
        out = run.load_cme(p)
        self.assertEqual(out["t"].tolist(), [1_000_000, 2_000_000])
        self.assertEqual(out["price"].tolist(), [3.0, 3.1])

    def test_end_to_end_on_a_planted_lag(self):
        lane = self.lane(kinds=("event", "placebo-2d"))
        with mock.patch.object(run, "CME", self.root / "cme"), mock.patch.object(run, "BN", self.root / "bn"):
            state = run.run(lane=lane, check=False)
        res = lane / "results"
        self.assertEqual(state, "INCONCLUSIVE")                       # one valid event is far below the minimum
        cells = pd.read_csv(res / "cells.csv")
        self.assertEqual(len(cells), 8)                               # 1 type x 4 latencies x filtered / all
        dec = cells[cells.decision]
        self.assertEqual(len(dec), 1)
        self.assertEqual((dec.n.iloc[0], dec.valid.iloc[0]), (1, 1))
        self.assertAlmostEqual(dec["mean"].iloc[0], 30.0, places=1)
        self.assertAlmostEqual(dec.net_1x.iloc[0], 20.0, places=1)
        self.assertAlmostEqual(dec.net_3x.iloc[0], 0.0, places=1)
        placebo = pd.read_csv(res / "placebo.csv")
        self.assertEqual(int(placebo.windows.iloc[0]), 1)
        self.assertEqual(json.loads((res / "summary.json").read_text())["registry"], "R370")

    def test_plumbing_computes_no_cell(self):
        lane = self.lane()
        with mock.patch.object(run, "CME", self.root / "cme"), mock.patch.object(run, "BN", self.root / "bn"):
            self.assertEqual(run.run(plumbing=True, lane=lane, check=False), "PLUMBING")
        self.assertFalse((lane / "results" / "cells.csv").exists())
        cov = pd.read_csv(lane / "results" / "coverage.csv")
        self.assertEqual(cov.invalid.fillna("").tolist(), [""])

    def test_a_window_without_a_reference_is_invalid_not_a_loss(self):
        lane = self.lane()
        w = next(pd.read_csv(lane / "windows.csv").itertuples())
        with mock.patch.object(run, "CME", self.root / "cme"):
            write_cme(run.cme_path(w), [(T_MS * 1000 + 1_000_000, "T", 3.0)])
        with mock.patch.object(run, "CME", self.root / "cme"), mock.patch.object(run, "BN", self.root / "bn"):
            run.run(lane=lane, check=False)
        cov = pd.read_csv(lane / "results" / "coverage.csv")
        self.assertEqual(cov.invalid.iloc[0], "no_ref")
        self.assertEqual(len(pd.read_csv(lane / "results" / "windows_scored.csv")), 0)

    def test_frozen_inputs_and_data_hashes_are_checked(self):
        f = self.root / "a.txt"
        f.write_text("one")
        good = prereg.sha256_file(f)
        pre = self.root / "PREREG.md"
        pre.write_text(f"```inputs\n{good}  a.txt\n```\n")
        self.assertEqual(run.frozen_inputs(pre, root=self.root), {"a.txt": good})
        f.write_text("two")
        with self.assertRaises(prereg.PreregError):
            run.frozen_inputs(pre, root=self.root)
        prov = self.root / "prov.json"
        prov.write_text(json.dumps({"combined_sha256": "ab", "file_hashes": [{"path": "a.txt", "sha256": good}]}))
        with self.assertRaises(prereg.PreregError):
            run.verify_data(prov, root=self.root)
        f.write_text("one")
        self.assertEqual(run.verify_data(prov, root=self.root), "ab")


if __name__ == "__main__":
    unittest.main()
