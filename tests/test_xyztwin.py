"""R477 xyztwin_v1: London marks, twin scaling, return-correlation identity and an end-to-end run on synthetic pairs."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import run_xyztwin as xt  # noqa: E402
from test_hip3stock import bill, world  # noqa: E402

H = xt.hs.HOUR


def tracked(scale=0.1, seed=0, noise=False):
    """A perp following a random-walk twin at 16:00 UTC; the twin quoted at `scale` of the perp's price."""
    s, c, f = world(rate=0.30)
    rng = np.random.default_rng(seed)
    s["close"] = s["adjclose"] = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(s))))
    marks = (pd.to_datetime(s["date"]).dt.tz_localize("UTC").dt.as_unit("ms").astype("int64") + 16 * H).to_numpy()
    idx = np.clip(np.searchsorted(marks, c["open_ms"].to_numpy(), side="right") - 1, 0, None)
    px = s["close"].to_numpy()[idx]
    if noise:
        px = float(np.median(px)) * np.exp(rng.normal(0, 0.01, len(c)))
    c[["open", "high", "low", "close"]] = np.repeat(px[:, None], 4, axis=1)
    twin = s.assign(close=s["close"] * scale, adjclose=s["adjclose"] * scale)
    return twin, c, f


class PairTest(unittest.TestCase):
    def test_marks_move_to_1600_only_inside_the_lane(self):
        before = xt.hs.mark_ms
        with xt.london_marks():
            self.assertEqual(xt.hs.mark_ms("2026-03-02") - xt.hs.day_ms("2026-03-02"), 16 * H)
        self.assertIs(xt.hs.mark_ms, before)
        self.assertEqual(xt.hs.mark_ms("2026-03-02") - xt.hs.day_ms("2026-03-02"), 20 * H)

    def test_scaling_aligns_levels_and_identity_uses_returns(self):
        with xt.london_marks():
            twin, c, f = tracked(scale=0.1)
            mk, k = xt.pair(twin, c, f, xt.hs.PERP_BP_GROWTH, 10, "AAA")
            self.assertAlmostEqual(k, 10.0, places=6)
            self.assertAlmostEqual(float((mk.perp / mk.close).median()), 1.0, places=6)
            self.assertTrue(xt.correlated(mk))
            twin, c, f = tracked(scale=0.1, noise=True)
            mk, _ = xt.pair(twin, c, f, xt.hs.PERP_BP_GROWTH, 10, "BBB")
            self.assertFalse(xt.correlated(mk))


class RunTest(unittest.TestCase):
    def test_run_keeps_tracked_pairs_and_restores_marks(self):
        before = xt.hs.mark_ms
        with tempfile.TemporaryDirectory() as d:
            data, lane = Path(d) / "data", Path(d) / "lane"
            (data / "xyz").mkdir(parents=True)
            (data / "yahoo").mkdir(parents=True)
            rows = []
            for t, kw, cur in [("SMH", {"scale": 0.12}, "USD"), ("KR200", {"scale": 0.01, "noise": True}, "USD"),
                               ("EWZ", {"scale": 1.0}, "GBp")]:
                twin, c, f = tracked(**kw)
                f.to_csv(data / "xyz" / f"{t}_funding.csv", index=False)
                c.to_csv(data / "xyz" / f"{t}_4h.csv", index=False)
                twin.to_parquet(data / "yahoo" / f"{t}.parquet", index=False)
                rows.append({"coin": f"xyz:{t}", "ticker": t, "twin": t + ".L", "twin_currency": cur,
                             "equity": int(cur == "USD"), "delisted": 0, "growth": "enabled", "max_lev": 20})
            pd.DataFrame(rows).to_csv(data / "universe.csv", index=False)
            pd.DataFrame({"date": bill().index, "close": 4.0, "adjclose": 4.0}).to_parquet(
                data / "yahoo" / "IRX.parquet", index=False)
            files = {str(p.relative_to(data)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(data.rglob("*")) if p.is_file()}
            (data / "manifest.json").write_text(json.dumps({"files": files}))
            state = xt.run(lane, data, check=False)
            s = json.loads((lane / "results" / "summary.json").read_text())
        self.assertIs(xt.hs.mark_ms, before)
        self.assertEqual(s["registry"], "R477")
        self.assertEqual(s["state"], state)
        self.assertEqual(s["markets"], ["SMH"])
        self.assertEqual(sorted(t for t, _ in s["dropped"]), ["EWZ", "KR200"])
        self.assertAlmostEqual(s["scale"]["SMH"], 1 / 0.12, places=6)
        self.assertGreater(s["variants"]["decide"]["A"]["ann_funding_pts"], 0)


if __name__ == "__main__":
    unittest.main()
