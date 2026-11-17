import unittest

from scripts import carte


class CarteTest(unittest.TestCase):
    def test_every_lane_has_a_known_family(self):
        rounds, fam = carte.load()
        self.assertEqual(carte.problems(rounds, fam), [],
                         "add the lane to registry/lane_families.csv with a family from scripts/carte.py")

    def test_committed_map_is_current(self):
        rounds, fam = carte.load()
        self.assertEqual(carte.OUT.read_text(encoding="utf-8"), carte.render(rounds, fam),
                         "run python scripts/carte.py")

    def test_verdict_words(self):
        self.assertEqual(carte.verdict("DONE", "NULL"), "nul")
        self.assertEqual(carte.verdict("ABANDONED", "PARTIAL"), "abandonné")
        self.assertEqual(carte.column(carte.verdict("DONE", "DATA_PASS")), "autre")


if __name__ == "__main__":
    unittest.main()
