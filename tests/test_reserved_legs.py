import importlib.util
import io
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def module():
    spec = importlib.util.spec_from_file_location("reserved_legs", ROOT / "scripts" / "reserved_legs.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ReservedLegsTest(unittest.TestCase):
    """The batch's onset rule must be R273's and R274's: on 2021-26 it rebuilds their frozen Binance legs."""

    @classmethod
    def setUpClass(cls):
        cls.m = module()
        if not (cls.m.SRC.exists() and (ROOT / "experiments" / "fundext_v1" / "legs.csv").exists()):
            raise unittest.SkipTest("funding archive not present")
        cls.fx = cls.m.fundext_legs("2021-01-01", "2026-10-01", "archive")

    def test_fundext_bytes(self):
        buf = io.StringIO()
        self.fx.to_csv(buf, index=False, float_format="%.8g")
        self.assertEqual(buf.getvalue(), (ROOT / "experiments" / "fundext_v1" / "legs.csv").read_text())

    def test_squeeze_binance_rows(self):
        mine = self.m.squeeze_legs(self.fx).drop(columns="notice").reset_index(drop=True)
        ref = pd.read_csv(ROOT / "experiments" / "squeeze_v1" / "legs.csv", keep_default_na=False)
        ref = ref[ref.kind.str.startswith("bn_")].drop(columns="notice").reset_index(drop=True)
        mine = pd.read_csv(io.StringIO(mine.to_csv(index=False, float_format="%.8g")), keep_default_na=False)
        pd.testing.assert_frame_equal(mine, ref)

    def test_reserved_start_needs_a_frozen_prereg(self):
        with self.assertRaises(PermissionError):
            self.m.main(["--out", "/nonexistent", "--start", "2020-01-01", "--end", "2021-01-01",
                         "--window", "reserved_2020"])


if __name__ == "__main__":
    unittest.main()
