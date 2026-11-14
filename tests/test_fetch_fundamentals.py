import unittest

from scripts import fetch_fundamentals as ff

DAY = ff.DAY


class FetchFundamentalsTest(unittest.TestCase):
    def test_candidates_use_parents(self):
        protocols = [
            {"slug": "aave-v3", "parentProtocol": "parent#aave", "symbol": "AAVE", "gecko_id": None},
            {"slug": "lido", "symbol": "LDO", "gecko_id": "lido-dao"},
            {"slug": "nolid", "symbol": "-", "gecko_id": "x"},
            {"slug": "notoken", "symbol": "ABC", "gecko_id": None},
        ]
        c = ff.candidates(protocols)
        self.assertEqual(c["aave"], {"symbol": "AAVE", "gecko_id": None, "parent": True})
        self.assertIn("lido", c)
        self.assertNotIn("nolid", c)
        self.assertNotIn("notoken", c)

    def test_mapping_drops_ambiguous_tickers(self):
        perps = {"AAVEUSDT", "LDOUSDT", "BABYUSDT", "1000PEPEUSDT"}
        cands = {"aave": {"symbol": "AAVE", "gecko_id": None, "parent": True},
                 "lido": {"symbol": "LDO", "gecko_id": "lido-dao", "parent": False},
                 "lido-v2": {"symbol": "LDO", "gecko_id": "lido-dao", "parent": False},
                 "baby-a": {"symbol": "BABY", "gecko_id": "babylon", "parent": False},
                 "baby-b": {"symbol": "BABY", "gecko_id": "babydoge", "parent": False},
                 "pepe": {"symbol": "PEPE", "gecko_id": "pepe", "parent": False}}
        rows = ff.mapping(cands, perps, {"aave": "aave"})
        ok = {r[0]: r[1] for r in rows if r[4] == "ok"}
        self.assertEqual(ok, {"AAVEUSDT": "aave", "LDOUSDT": "lido", "1000PEPEUSDT": "pepe"})
        self.assertEqual({r[1] for r in rows if r[4] == "ambiguous"}, {"baby-a", "baby-b"})

    def test_day_series_floors_and_keeps_last(self):
        s = ff.day_series([(86400 + 5, 1), (86400 + 60, 2), (0, 3)])
        self.assertEqual(s.index.tolist(), [0, DAY])
        self.assertEqual(s.tolist(), [3.0, 2.0])


if __name__ == "__main__":
    unittest.main()
