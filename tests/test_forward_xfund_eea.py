import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from lab import carrylane, kraken


class Books(unittest.TestCase):
    def test_walk_and_sides(self):
        asks = [[101.0, 5.0], [102.0, 10.0]]
        bids = [[99.0, 5.0], [98.0, 10.0]]
        self.assertAlmostEqual(kraken.walk(asks, 101 * 5), 101.0)               # filled at the first level
        px = kraken.walk(asks, 101 * 5 + 102 * 5)
        self.assertAlmostEqual(px, (101 * 5 + 102 * 5) / 10)
        self.assertIsNone(kraken.walk(asks, 1e9))                                # too thin
        mid, fill, cost = kraken.side_fill(bids, asks, "buy", 505)
        self.assertEqual(mid, 100.0)
        self.assertAlmostEqual(cost, 100.0)                                      # 1% above mid = 100 bp
        _, _, cost_s = kraken.side_fill(bids, asks, "sell", 495)
        self.assertAlmostEqual(cost_s, 100.0)                                    # selling below mid is a cost too
        self.assertEqual(kraken.side_fill([], asks, "buy", 10), (None, None, None))
        self.assertEqual(kraken.sides("enter", "kraken", "hyperliquid"), {"kraken": "buy", "hyperliquid": "sell"})
        self.assertEqual(kraken.sides("exit", "kraken", "hyperliquid"), {"kraken": "sell", "hyperliquid": "buy"})


class Clients(unittest.TestCase):
    def test_funding_and_prices_parse(self):
        rates = {"rates": [{"timestamp": "2026-11-18T01:00:00.000Z", "relativeFundingRate": -2e-6, "fundingRate": -1.0},
                           {"timestamp": "2026-11-18T00:00:00.000Z", "relativeFundingRate": 3e-6, "fundingRate": 1.0}]}
        with mock.patch.object(kraken, "_json", return_value=rates):
            f = kraken.funding("PF_XBTUSD", 0, 2**62)
        t0 = kraken.iso_ms("2026-11-18T00:00:00Z")
        self.assertEqual(f.t.tolist(), [t0, t0 + 3_600_000])
        self.assertEqual(f.rate.tolist(), [3e-6, -2e-6])
        candles = {"candles": [{"time": t0, "open": "1", "high": "2", "low": "1", "close": "1.5", "volume": "10"},
                               {"time": t0 - kraken.DAY, "open": "1", "high": "2", "low": "1", "close": "1.2",
                                "volume": "0"}]}
        with mock.patch.object(kraken, "_json", return_value=candles):
            p = kraken.prices("PF_XBTUSD", t0 - kraken.DAY, t0 + kraken.DAY)
        self.assertEqual(p.close.tolist(), [1.2, 1.5])
        tick = {"tickers": [{"symbol": "PF_XBTUSD", "bid": 99, "ask": 101, "tag": "perpetual", "suspended": False},
                            {"symbol": "PF_ABCUSD", "bid": 1, "ask": 1.2, "tag": "perpetual", "suspended": True},
                            {"symbol": "FI_XBTUSD_261225", "bid": 1, "ask": 2, "tag": "month"}]}
        with mock.patch.object(kraken, "_json", return_value=tick):
            self.assertEqual(kraken.mids()["PF_XBTUSD"], 100.0)
            self.assertEqual(kraken.listed(), {"PF_XBTUSD"})

    def test_register(self):
        v = kraken.register()
        self.assertIs(carrylane.VENUES["kraken"], v)
        self.assertEqual(v.bar_h, 24)


class Recorder(unittest.TestCase):
    def test_records_once_per_ontime_ticket(self):
        from scripts import forward_xfund_eea as fw
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sym = root / "symbols.csv"
            pd.DataFrame({"key": ["NEIRO"], "kraken": ["PF_NEIROUSD"], "hyperliquid": ["kNEIRO"]}).to_csv(sym,
                                                                                                         index=False)
            lane = carrylane.Lane("t", "R0", root / "lane", sym, {"A": ("kraken+hyperliquid", 14, 0.05, 20, "")},
                                  ["kraken", "hyperliquid"], "2026-10-01", "2026-11-20", data_dir=root / "data")
            run = "2026-11-20T00:30:00Z"
            tk = {"run": run, "day": "2026-11-20", "book": "A", "action": "enter", "coin": "NEIRO", "long": "hyperliquid",
                  "short": "kraken", "spread_ann": "1.5", "forced": "false", "kind": "ontime", "close_long": "1",
                  "close_short": "1", "fill_long": "1", "fill_short": "1"}
            lane.append("tickets.csv", carrylane.TICKET_COLS, [tk, dict(tk, kind="replay", day="2026-11-19")])
            lane.append("decisions.csv", carrylane.DEC_COLS,
                        [{"run": run, "day": "2026-11-20", "book": "A", "kind": "ontime", "exits": 0, "entries": 1,
                          "held": 1, "ready": "{}"},
                         {"run": run, "day": "2026-11-19", "book": "A", "kind": "replay", "exits": 0, "entries": 1,
                          "held": 1, "ready": "{}"}])
            book = ([[0.99, 10000.0]], [[1.01, 10000.0]])
            n = fw.record_books(lane, {"kraken": lambda s: book, "hyperliquid": lambda s: ([], [])}, now="x")
            self.assertEqual(n, 2)                              # one row per leg of the one on-time ticket
            rows = {r["venue"]: r for r in lane.rows("book_fills.csv")}
            self.assertEqual(rows["kraken"]["side"], "sell")    # entering short Kraken sells there
            self.assertAlmostEqual(float(rows["kraken"]["cost_bp_1000"]), 100.0)
            self.assertEqual(rows["hyperliquid"]["cost_bp_1000"], "")   # a missing book is recorded as missing
            self.assertEqual(fw.record_books(lane, {"kraken": lambda s: book, "hyperliquid": lambda s: book}), 0)


class Read(unittest.TestCase):
    def test_measured_costs_replace_the_flat_cost(self):
        from scripts import read_xfund_eea_fwd as rd
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp)
            j = lane / "journal"
            j.mkdir()
            run = "r1"
            pd.DataFrame([{"run": run, "day": d, "book": "A", "kind": k, "exits": 0, "entries": 1, "held": 1,
                           "ready": "{}"} for d, k in (("2026-11-20", "ontime"), ("2026-11-21", "late"))]).to_csv(
                j / "decisions.csv", index=False)
            t = {"run": run, "day": "2026-11-20", "book": "A", "action": "enter", "coin": "X", "long": "kraken",
                 "short": "hyperliquid", "spread_ann": "1", "forced": "false", "kind": "ontime", "close_long": "1",
                 "close_short": "1", "fill_long": "1", "fill_short": "1"}
            pd.DataFrame([t, dict(t, action="drop", coin="Y")]).to_csv(j / "tickets.csv", index=False)
            pd.DataFrame([{"day": "2026-11-21", "book": "A", "kind": "ontime", "run": run, "held": 1, "legs": 2.0,
                           "gross": 0.001, "funding": 0.001, "fill_adj": 0, "net": 0.001 - 0.0007 * 2 / 40,
                           "net_2x": 0, "net_3x": 0, "net_close": 0, "net_close_2x": 0, "net_close_3x": 0},
                          {"day": "2026-11-20", "book": "A", "kind": "replay", "run": run, "held": 1, "legs": 0,
                           "gross": 0, "funding": 0, "fill_adj": 0, "net": 0.5, "net_2x": 0, "net_3x": 0,
                           "net_close": 0, "net_close_2x": 0, "net_close_3x": 0}]).to_csv(j / "days.csv", index=False)
            pd.DataFrame([{"run": run, "day": "2026-11-20", "book": "A", "action": "enter", "coin": "X",
                           "venue": "kraken", "symbol": "PF_X", "side": "buy", "utc": "", "mid": 1,
                           "fill_1000": 1, "cost_bp_1000": 20.0, "fill_2500": "", "cost_bp_2500": ""}]).to_csv(
                j / "book_fills.csv", index=False)
            s = rd.series(lane)
            self.assertEqual(s.day.tolist(), ["2026-11-21"])              # the replayed day is not scored
            c = (20.0 + 5.0) / 1e4 + 0.0021                               # Kraken measured + fee; Hyperliquid missing
            self.assertAlmostEqual(s.measured_cost.iloc[0], c)
            self.assertAlmostEqual(s.net_book.iloc[0], 0.001 - c / 40)
            self.assertAlmostEqual(s.net_book_2x.iloc[0], 0.001 - 2 * c / 40)
            self.assertTrue(rd.read(s, 1)["verdict"].startswith("NOT DUE"))


if __name__ == "__main__":
    unittest.main()
