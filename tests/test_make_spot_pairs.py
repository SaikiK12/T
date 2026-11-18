import unittest

from scripts import make_spot_pairs as m


class SpotPairs(unittest.TestCase):
    def test_name_rule_multipliers_and_preference(self):
        perps = {"BTCUSDT", "1000PEPEUSDT", "ETHUSDT"}
        months = {"BTCUSDT": ["2020-01", "2026-09"], "PEPEUSDT": ["2023-05", "2026-09"],
                  "1000PEPEUSDT": ["2024-01", "2026-09"], "DOGEUSDT": ["2020-01", "2026-09"]}
        out = m.build(sorted(months), perps, months.get)
        self.assertEqual(out["BTCUSDT"], {"spot": "BTCUSDT", "months": ["2020-01", "2026-09"]})
        self.assertEqual(out["1000PEPEUSDT"]["spot"], "1000PEPEUSDT")      # the same name is preferred
        self.assertNotIn("ETHUSDT", out)                                    # no spot pair, no entry
        out = m.build(["PEPEUSDT"], perps, months.get)
        self.assertEqual(out["1000PEPEUSDT"]["spot"], "PEPEUSDT")           # matched through the multiplier
        self.assertEqual(m.build(["BTCUSDT"], perps, months.get, keep={"ETHUSDT"}), {})


if __name__ == "__main__":
    unittest.main()
