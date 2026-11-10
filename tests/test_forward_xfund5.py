"""R440 xfund5_fwd: the lane runs R439's book, venues and universe (no network, no journal write)."""
import tomllib
import unittest
from pathlib import Path

from lab import prereg
from scripts import forward_xfund5 as f
from scripts import run_carry5

ROOT = Path(__file__).resolve().parent.parent


class Xfund5LaneTests(unittest.TestCase):
    def test_book_is_r439s(self):
        s, l, th, k, _ = f.LANE.books["A"]
        self.assertEqual((s, l, th, k), run_carry5.BOOK5)
        self.assertEqual(list(f.LANE.books), ["A"])

    def test_venues_in_r439_spec_order(self):
        spec = tomllib.loads((ROOT / "experiments" / "carry5_v1" / "spec.toml").read_text())
        self.assertEqual(f.LANE.names, [v["name"] for v in spec["venues"]])
        self.assertEqual(f.LANE.symbols, ROOT / spec["symbols"])

    def test_fixed_inputs_match(self):
        for path, sha in f.FIXED.items():
            self.assertEqual(prereg.sha256_file(ROOT / path), sha, path)

    def test_costs_and_guard_are_r439s(self):
        spec = tomllib.loads((ROOT / "experiments" / "carry5_v1" / "spec.toml").read_text())
        self.assertEqual(f.LANE.costs, tuple(spec["costs"]))
        self.assertEqual(f.LANE.corr, (spec["corr_days"], spec["corr_min"], spec["corr_obs"]))


if __name__ == "__main__":
    unittest.main()
