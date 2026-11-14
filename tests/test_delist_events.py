import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import delist_events as de  # noqa: E402


class DelistParseTests(unittest.TestCase):
    def test_spot_titles(self):
        self.assertEqual(de.parse("Binance Will Delist COS, D, HIGH, MBOX on 2026-06-19"),
                         ("spot", ["COS", "D", "HIGH", "MBOX"]))
        self.assertEqual(de.parse("Binance Will Delist QLC, NEBL and AUTO on 2023-04-18"), ("spot", ["QLC", "NEBL", "AUTO"]))
        kind, ticks = de.parse("Binance Announced the First Batch of Vote to Delist Results and Will Delist BADGER, BAL "
                               "on 2025-04-16")
        self.assertEqual((kind, ticks), ("spot", ["BADGER", "BAL"]))

    def test_futures_titles_and_bodies(self):
        self.assertEqual(de.parse("Binance Futures Will Delist USDⓈ-M HIFIUSDT and BAKEUSDT Perpetual Contracts (2025-10-03)"),
                         ("futures", ["HIFIUSDT", "BAKEUSDT"]))
        self.assertEqual(de.parse("Binance Futures Will Delist 1000BTTC and YFII USDT-Margined Contracts"),
                         ("futures", ["1000BTTC", "YFII"]))
        body = "settlement as below: 2026-10-05 09:00 (UTC) : USDⓈ-M PROMPTUSDT, PUMPBTCUSDT and 1000000BOBUSDT Perpetual"
        self.assertEqual(de.parse("Binance Futures Will Delist Multiple USDⓈ-M Perpetual Contracts (2026-10-05)", body),
                         ("futures", ["PROMPTUSDT", "PUMPBTCUSDT", "1000000BOBUSDT"]))
        self.assertEqual(de.parse("Binance Futures Will Delist USDⓈ-M DEFIUSDT and MEMEFI Perpetual Contracts (2025-08-11)",
                                  "USDⓈ-M DEFIUSDT"), ("futures", ["DEFIUSDT", "MEMEFI"]))

    def test_excluded_titles(self):
        for t in ("Binance Margin Will Delist ARDR on 2026-03-12",
                  "Binance Margin And Loan Will Delist HOT, THE on 2026-07-03",
                  "Delisting of USDⓈ-M OMGUSDT Perpetual Contract Postponed",
                  "Binance Futures Will Delist CRV Coin-Margined Perpetual Contract",
                  "Binance Futures Will Delist Multiple Perpetual Contracts",            # no body: no tickers
                  "Notice of Removal of Trading Pairs - 2022-02-24",
                  "Binance to Delist and Cease Redemption for XRPUP and XRPDOWN Leveraged Tokens (2023-07-25)"):
            self.assertEqual(de.parse(t), (None, []), t)

    def test_perp_mapping(self):
        perps = {"ALPHAUSDT", "1000XECUSDT", "1000000BOBUSDT"}
        self.assertEqual(de.perp_for("ALPHA", perps), ("ALPHAUSDT", True))
        self.assertEqual(de.perp_for("XEC", perps), ("1000XECUSDT", True))
        self.assertEqual(de.perp_for("1000000BOBUSDT", perps), ("1000000BOBUSDT", True))
        self.assertEqual(de.perp_for("GO", perps), ("GOUSDT", False))


if __name__ == "__main__":
    unittest.main()
