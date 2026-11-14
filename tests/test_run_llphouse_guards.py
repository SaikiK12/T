"""scripts/run_llphouse.py (R484) input guards: check_raw against raw/manifest.json, and main()'s drop of LLP stamps
after the 2026-11-10 cutoff. Separate from tests/test_run_llphouse.py, which is a frozen R484 input."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("run_llphouse", ROOT / "scripts" / "run_llphouse.py")
lh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lh)


def write_raw(root, bodies):
    """raw/hl/<name> bodies plus a manifest listing their sha256."""
    (root / "hl").mkdir(parents=True)
    files = {}
    for name, data in bodies.items():
        (root / "hl" / name).write_bytes(data)
        files[f"hl/{name}"] = hashlib.sha256(data).hexdigest()
    (root / "manifest.json").write_text(json.dumps({"files": files}))
    return files


class TestCheckRaw(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raw = Path(self._tmp.name) / "raw"
        write_raw(self.raw, {"BTC_candles_1d.json": b"[1]", "BTC_funding_0.json": b"[2]"})

    def tearDown(self):
        self._tmp.cleanup()

    def test_matching_bodies_return_the_manifest_sha(self):
        want = hashlib.sha256((self.raw / "manifest.json").read_bytes()).hexdigest()
        self.assertEqual(lh.check_raw(self.raw), want)

    def test_changed_body_is_refused(self):
        (self.raw / "hl" / "BTC_funding_0.json").write_bytes(b"[3]")
        with self.assertRaises(SystemExit) as cm:
            lh.check_raw(self.raw)
        self.assertIn("hl/BTC_funding_0.json", str(cm.exception))

    def test_unlisted_body_is_refused(self):
        (self.raw / "hl" / "ETH_funding_0.json").write_bytes(b"[]")
        with self.assertRaises(SystemExit) as cm:
            lh.check_raw(self.raw)
        self.assertIn("ETH_funding_0.json", str(cm.exception))

    def test_missing_body_is_refused(self):
        (self.raw / "hl" / "BTC_candles_1d.json").unlink()
        with self.assertRaises(SystemExit):
            lh.check_raw(self.raw)

    def test_the_lane_raw_dir_matches_its_manifest(self):
        lh.check_raw(lh.RAW)


class _Stop(Exception):
    pass


class TestMainCutoff(unittest.TestCase):
    def test_llp_stamps_after_the_cutoff_never_reach_the_signal(self):
        """main() passes llp_signals only stamps on or before 2026-11-10, whatever the data branch holds."""
        days = pd.date_range("2026-11-01", "2026-11-14", freq="D", tz="UTC")
        stamps = [int((d + pd.Timedelta(hours=20)).timestamp() * 1000) for d in days]
        prices = pd.Series(np.linspace(1.0, 1.1, len(stamps)), index=stamps)
        seen = {}

        def capture(p):
            seen["prices"] = p
            raise _Stop

        with mock.patch.object(sys, "argv", ["run_llphouse.py", "--data", "unused"]), \
                mock.patch("lab.prereg.verify", return_value="sha"), \
                mock.patch.object(lh.rx, "check_inputs", return_value="c0"), \
                mock.patch.object(lh.rx, "data_head", return_value="c0"), \
                mock.patch.object(lh, "check_raw", return_value="m0"), \
                mock.patch.object(lh.dv, "llp_prices", return_value=prices), \
                mock.patch.object(lh, "llp_signals", side_effect=capture):
            with self.assertRaises(_Stop):
                lh.main()
        got = seen["prices"]
        labels = [lh.rx.day_label(t) for t in got.index]
        self.assertEqual(labels[-1], lh.CUTOFF)
        self.assertEqual(len(got), 10)               # 2026-11-01 .. 2026-11-10
        self.assertTrue(all(x <= lh.CUTOFF for x in labels))

    def test_data_commit_other_than_the_pinned_one_is_refused(self):
        with mock.patch.object(sys, "argv", ["run_llphouse.py", "--data", "unused"]), \
                mock.patch("lab.prereg.verify", return_value="sha"), \
                mock.patch.object(lh.rx, "check_inputs", return_value="c0"), \
                mock.patch.object(lh.rx, "data_head", return_value="c1"), \
                mock.patch.object(lh, "check_raw", side_effect=AssertionError("must not be reached")):
            with self.assertRaises(SystemExit):
                lh.main()


if __name__ == "__main__":
    unittest.main()
