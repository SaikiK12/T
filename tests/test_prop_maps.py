import unittest

import numpy as np

from lab import propfirm
from scripts import prop_cost_map, prop_edge_map


class PropMapInputsTest(unittest.TestCase):
    def test_stream_is_seeded_and_scaled(self):
        a = prop_edge_map.stream(1.0, "normal", days=500, seed=3)
        np.testing.assert_array_equal(a, prop_edge_map.stream(1.0, "normal", days=500, seed=3))
        self.assertEqual(len(a), 500)
        base = prop_edge_map.stream(0.0, "normal", days=500, seed=3)
        np.testing.assert_allclose(a - base, 0.01 / np.sqrt(252))

    def test_t4_stream_has_unit_variance_scale(self):
        r = prop_edge_map.stream(0.0, "t4", days=200_000, seed=1)
        self.assertAlmostEqual(float(r.std()), 0.01, delta=0.0005)

    def test_presets_and_fees_exist_in_lab_propfirm(self):
        for name in prop_edge_map.PRESETS + prop_cost_map.PRESETS:
            self.assertIn(name, propfirm.PRESETS)
        self.assertTrue(set(prop_edge_map.FEES) <= set(prop_edge_map.PRESETS))


if __name__ == "__main__":
    unittest.main()
