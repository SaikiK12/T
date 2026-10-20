import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import qx_run


class InputsTest(unittest.TestCase):
    def test_parse_and_rebuild_only_checks_lane_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane, other = root / "experiments" / "a", root / "experiments" / "b"
            lane.mkdir(parents=True)
            other.mkdir(parents=True)
            (lane / "legs.csv").write_text("x\n1\n")
            (other / "legs.csv").write_text("x\n2\n")          # same name, another lane's frozen input
            (root / "build.py").write_text(
                "import sys, pathlib\np = pathlib.Path(sys.argv[2])\np.mkdir(exist_ok=True)\n"
                "(p / 'legs.csv').write_text('x\\n1\\n')\n")
            h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            text = ("```inputs\n"
                    f"experiments/a/legs.csv  {h(lane / 'legs.csv')}\n"
                    f"experiments/b/legs.csv  {h(other / 'legs.csv')}  # hashed only\n"
                    "rebuild: python build.py --out {tmp}\n```\n")
            files, rebuild = qx_run.inputs(text)
            self.assertEqual(len(files), 2)
            self.assertEqual(rebuild, "python build.py --out {tmp}")
            with mock.patch.object(qx_run, "ROOT", root):
                qx_run.check(lane, text)                         # passes: b's legs.csv is not compared
                (lane / "legs.csv").write_text("x\n3\n")
                with self.assertRaises(SystemExit):
                    qx_run.check(lane, text)                     # hash changed


if __name__ == "__main__":
    unittest.main()
