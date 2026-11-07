import ast
import math
import unittest
from pathlib import Path

import numpy as np

from lab.mexc_depth import MexcDepthLevel, parse_depth_levels, parse_mexc_depth_level


ROOT = Path(__file__).resolve().parent.parent


def r224_helpers():
    """Load R224's pure math helpers without importing its recorder runtime."""
    path = ROOT / "scripts" / "record_mexc_depth.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    wanted = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ("walk", "side")]
    namespace = {"np": np, "BAND": 0.005}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["walk"], namespace["side"]


class MexcDepthSchemaTests(unittest.TestCase):
    def test_schema_keeps_contract_quantity_separate_from_order_count(self):
        rows = parse_depth_levels([[100.0, 22522, 7], [99.9, 185, 1]])
        self.assertEqual(rows, (MexcDepthLevel(100.0, 7, 22522.0), MexcDepthLevel(99.9, 1, 185.0)))
        self.assertAlmostEqual(rows[0].base_quantity(0.0001), 2.2522)
        self.assertAlmostEqual(rows[1].base_quantity(0.0001), 0.0185)

    def test_single_level_parser_reads_contract_volume_and_accepts_numeric_strings(self):
        self.assertEqual(parse_mexc_depth_level(["100.25", "22522", "7"]), (100.25, 22522.0))
        self.assertEqual(parse_mexc_depth_level((100.25, 0, 0)), (100.25, 0.0))

    def test_malformed_or_nonphysical_full_depth_fails_closed(self):
        bad_inputs = ([], [[100, 2]], [[100, 2, 3, 4]], [[100, True, 3]], [[100, 3, True]],
                      [[100, 3, 1.5]], [[100, -1, 3]], [[100, 2, -1]],
                      [[100, 2, 0]], [[100, 0, 2]], [[0, 2, 3]], [[math.nan, 2, 3]],
                      [[100, 2, math.inf]], "not rows")
        for rows in bad_inputs:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                parse_depth_levels(rows)

    def test_base_quantity_rejects_invalid_contract_size(self):
        level = MexcDepthLevel(100.0, 1, 2.0)
        for size in (0, -1, math.nan, True, "not-a-number"):
            with self.subTest(size=size), self.assertRaises(ValueError):
                level.base_quantity(size)
        self.assertAlmostEqual(level.base_quantity("0.01"), 0.02)

    def test_normalized_levels_feed_r224_walk_and_near_depth_helpers(self):
        asks = parse_depth_levels([[100.2, 3, 1000], [100.3, 4, 2000]])
        walk_rows = [level.bookwalk_row() for level in asks]
        walk, side = r224_helpers()
        size = 0.01
        near, reach_bp = side(walk_rows, size, 100.0)
        self.assertAlmostEqual(near, 100.2 * 3 * size + 100.3 * 4 * size)
        self.assertAlmostEqual(reach_bp, 30.0)
        expected = (3.006 * 20.0 + 0.994 * 30.0) / 4.0
        self.assertAlmostEqual(walk(walk_rows, size, 4.0, 100.0), expected)

    def test_bookwalk_projection_does_not_reuse_raw_order_count(self):
        (level,) = parse_depth_levels([[100.0, 2, 5000]])
        self.assertEqual(level.bookwalk_row(), (100.0, 2.0, 5000))

    def test_live_btc_payload_shape_maps_large_second_field_to_contract_volume(self):
        # Public BTC_USDT depth returned [price, 54145, 4]; contractSize was 0.0001.
        # The second field implies about $441k at that level; the third would imply about $33.
        (level,) = parse_depth_levels([[81460.7, 54145, 4]])
        self.assertEqual((level.quantity_contracts, level.order_count), (54145.0, 4))
        self.assertAlmostEqual(81460.7 * level.base_quantity(0.0001), 441068.96015, places=5)


if __name__ == "__main__":
    unittest.main()
