"""scripts/prefetch_carry_data.py: the five forward carry lanes load without network and expose their own refresh."""
import importlib.util
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prefetch_carry_data", ROOT / "scripts" / "prefetch_carry_data.py")
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)


class PrefetchCarryData(unittest.TestCase):
    def test_lanes_cover_the_carry_locks_and_r440(self):
        from lab import operations
        src = (ROOT / "lab" / "operations.py").read_text()
        for rid in ("R278", "R279", "R294", "R390"):
            self.assertIn(f'"{rid}": ".xfund', src)
            self.assertIn(rid, pf.SCRIPTS)
        self.assertEqual(pf.SCRIPTS["R440"], "forward_xfund5.py")
        self.assertTrue(operations)

    def test_each_lane_loads_and_exposes_refresh(self):
        for rid in pf.SCRIPTS:
            mod = pf.load(rid)
            fn = pf.refresher(mod)
            self.assertTrue(callable(fn), rid)
            self.assertEqual(fn.__name__, "refresh", rid)

    def test_refresher_prefers_the_lane_object(self):
        lane = types.SimpleNamespace(refresh=lambda now: "lane")
        self.assertEqual(pf.refresher(types.SimpleNamespace(LANE=lane, refresh=lambda now: "mod"))(0), "lane")
        self.assertEqual(pf.refresher(types.SimpleNamespace(refresh=lambda now: "mod"))(0), "mod")

    def test_unknown_lane_is_refused(self):
        with self.assertRaises(SystemExit):
            pf.main(["R999"])


if __name__ == "__main__":
    unittest.main()
