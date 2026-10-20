"""The Rust engine (engine/, `qx`) must reproduce a frozen Python lane exactly: R269 montag_v1's six variants."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QX = ROOT / "engine" / "target" / "release" / "qx"
R269 = ROOT / "experiments" / "montag_v1" / "results" / "verdict.json"
DATA = ROOT / "data" / "klines_1h" / "BTCUSDT.parquet"


@unittest.skipUnless(QX.exists() and R269.exists() and DATA.exists(), "needs the built engine, R269 results and the archive")
class QxParityTests(unittest.TestCase):
    def test_r269_variants_match(self):
        spec = (ROOT / "engine" / "specs" / "parity_r269.toml").read_text()
        with tempfile.TemporaryDirectory() as d:
            spec = "\n".join(f'out = "{d}"' if l.startswith("out =") else l for l in spec.splitlines())
            (Path(d) / "spec.toml").write_text(spec)
            subprocess.run([str(QX), "events", str(Path(d) / "spec.toml")], cwd=ROOT, check=True, capture_output=True,
                           env={**os.environ, "QX_DATA": str(ROOT / "data")})
            rep = json.loads((Path(d) / "report.json").read_text())
        got = {r["label"]: r["stats"] for r in rep["strategies"]}
        want = json.loads(R269.read_text())["variants"]
        names = {"1: tag 1h net": "tag short 1h", "2: tag 24h net": "tag short 24h", "3: tag 72h net": "tag short 72h",
                 "4: tag 1h hedged": "tag short 1h hedged", "5: tag 24h hedged": "tag short 24h hedged",
                 "6: tag 72h hedged": "tag short 72h hedged"}
        for py, rs in names.items():
            for m, k in enumerate(("1x", "2x", "3x")):
                for f in ("n", "legs", "mean_pct", "median_pct", "hit", "t", "half1_pct", "half2_pct", "y2025_pct", "y2025_n"):
                    self.assertAlmostEqual(got[rs][m][f], want[py][k][f], places=9, msg=f"{rs} {k} {f}")
        self.assertEqual(rep["priced_legs"], 86)
        self.assertEqual(rep["no_market"], 11)


if __name__ == "__main__":
    unittest.main()
