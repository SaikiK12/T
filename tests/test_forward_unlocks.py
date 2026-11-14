import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import forward_unlocks as fu  # noqa: E402

H, DAY = fu.H, fu.DAY
D1 = fu.panel.ms("2026-10-27")     # unlock day of token A (entry 2026-10-21 00:00)
D2 = fu.panel.ms("2026-10-28")     # token B: price mismatch
D3 = fu.panel.ms("2026-10-29")     # token C: no MEXC contract


def index_row(gid, sym, price, max_supply, cliffs):
    return {"gecko_id": gid, "maxSupply": str(max_supply),
            "tokenPrice": [{"symbol": sym, "price": price}],
            "unlockEvents": [{"timestamp": d // 1000 + 3600,
                              "cliffAllocations": [{"category": c, "amount": a, "unlockType": "cliff"} for c, a in cl]}
                             for d, cl in cliffs]}


SNAP = {"data": [
    index_row("tok-a", "AAA", 2.0, 1_000_000, [(D1, [("insiders", 15_000), ("privateSale", 5_000)]),
                                                (D1 + 7 * DAY, [("insiders", 50_000)])]),   # second is within 14 days
    index_row("tok-b", "BBB", 1.0, 1_000_000, [(D2, [("insiders", 20_000)])]),
    index_row("tok-c", "CCC", 1.0, 1_000_000, [(D3, [("privateSale", 20_000)])]),
    index_row("tok-d", "DDD", 1.0, 1_000_000, [(D1, [("noncirculating", 90_000), ("insiders", 5_000)])]),  # 0.5%
]}
TABLE = pd.DataFrame({"symbol": ["AAA_USDT", "BBB_USDT"], "base": ["AAA", "BBB"], "type": [1, 1], "state": [0, 0],
                      "taker": [0.0002, 0.0002], "maker": [0.0, 0.0], "contract_size": [1, 1], "settle": ["USDT"] * 2})
LAST = {"AAA_USDT": 2.1, "BBB_USDT": 9.0}


def bars(entry_ms, exit_ms, path):
    t = np.arange(entry_ms, exit_ms + 2 * H, H)
    p = np.interp(t, [t[0], t[-1]], path)
    return pd.DataFrame({"t": t, "open": p, "high": p * 1.01, "low": p * 0.99, "close": p})


class ForwardUnlockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.snaps, self.ticks = d / "snaps", d / "ticks"
        self.snaps.mkdir()
        (self.snaps / "2026-10-20.json.gz").write_bytes(gzip.compress(json.dumps(SNAP).encode()))
        self.old_j = fu.J
        fu.J = d / "journal"

    def tearDown(self):
        fu.J = self.old_j
        self.tmp.cleanup()

    def run_tick(self, now, path=(2.0, 1.8)):
        return fu.tick(now, contracts=lambda: TABLE, last_price=lambda c: LAST[c],
                       klines=lambda c, s, e: bars(s, e - 2 * H, path),
                       funding=lambda c, s, e: pd.DataFrame({"t": [s + 8 * H, s + 16 * H], "rate": [-0.001, 0.0005]}),
                       binance_bases={"AAA"}, snaps=self.snaps, ticks=self.ticks)

    def test_events_follow_r265_rule(self):
        ev = fu.snapshot_events(self.snaps / "2026-10-20.json.gz")
        got = sorted((e["ticker"], e["day_ms"]) for e in ev)
        self.assertEqual(got, [("AAA", D1), ("BBB", D2), ("CCC", D3)])
        a = [e for e in ev if e["ticker"] == "AAA"][0]
        self.assertAlmostEqual(a["frac_max_supply"], 0.02)

    def test_tickets_written_in_window_once_and_skips_journaled(self):
        E1 = D1 - 6 * DAY
        self.run_tick(E1 - DAY - H)                        # too early: nothing
        self.assertFalse((fu.J / "tickets.csv").exists())
        self.run_tick(E1 - 12 * H)                         # in A's window
        self.run_tick(E1 + 10 * 60_000)                    # again: idempotent
        tk = pd.read_csv(fu.J / "tickets.csv")
        self.assertEqual(list(tk.contract), ["AAA_USDT"])
        self.assertTrue(bool(tk.listed_binance.iloc[0]))
        self.run_tick(D3 - 6 * DAY - 2 * H)                # B and C windows open
        sk = pd.read_csv(fu.J / "skipped.csv")
        self.assertEqual(sorted(sk.reason), ["mismatch", "no_contract"])
        tk = pd.read_csv(fu.J / "tickets.csv")
        self.assertEqual(len(tk), 1)

    def test_missed_window_is_journaled(self):
        self.run_tick(D1 - 6 * DAY + 2 * H)                # A's window closed at E + 1 h
        sk = pd.read_csv(fu.J / "skipped.csv")
        self.assertEqual(sk.set_index("ticker").reason.to_dict(), {"AAA": "missed", "BBB": "mismatch"})  # B's window is open
        self.assertFalse((fu.J / "tickets.csv").exists())

    def test_score_math(self):
        E1 = D1 - 6 * DAY
        self.run_tick(E1 - H)
        st = self.run_tick(D1 + DAY + H + 20 * 60_000)    # exit bar has opened
        sc = pd.read_csv(fu.J / "scores.csv")
        self.assertEqual(len(sc), 1)
        r = sc.iloc[0]
        b = bars(E1, D1 + DAY, (2.0, 1.8))
        entry = b.loc[b.t == E1 + H, "open"].item()
        exit_ = b.loc[b.t == D1 + DAY + H, "open"].item()
        self.assertAlmostEqual(r.gross, -(exit_ / entry - 1))
        self.assertAlmostEqual(r.funding, -0.001 + 0.0005)    # both settlements fall inside (E+1h, X+1h]
        self.assertTrue(bool(r.spread_flag))                  # no ticker recorder files in the fixture
        self.assertAlmostEqual(r.cost_measured, 2 * 0.0002 + 2 * fu.SPREAD_FALLBACK)
        self.assertAlmostEqual(r.net, r.gross - r.cost_measured + r.funding)
        self.assertAlmostEqual(r.net_1x, r.gross - 0.002 + r.funding)
        self.assertAlmostEqual(r.mae, b[(b.t >= E1 + H) & (b.t < D1 + DAY + H)].high.max() / entry - 1)
        self.assertFalse(bool(r.liq_1x))
        self.assertEqual(st["scored"], 1)
        self.assertTrue(st["decision"].startswith("pending"))
        book = pd.read_csv(fu.J / "book_days.csv")
        self.assertAlmostEqual(book.ret.sum(), fu.WEIGHT * r.net, places=3)   # daily-rebalanced marks


if __name__ == "__main__":
    unittest.main()
