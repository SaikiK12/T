import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import forward_delist as fd  # noqa: E402

H = fd.H
ms = lambda s: int(pd.Timestamp(s, tz="UTC").value // 10**6)
REL = ms("2026-10-22T07:00:30")          # a spot notice released at 07:00, seen by the 07:06 tick
CATALOG = pd.DataFrame([
    {"id": 1, "code": "a", "title": "Binance Will Delist OLD on 2026-09-01", "release_ms": ms("2026-08-20T06:00"),
     "first_seen_utc": "2026-10-20T12:42:01Z"},                                         # backfill: ignored
    {"id": 2, "code": "b", "title": "Binance Margin Will Delist AAA on 2026-10-30", "release_ms": REL,
     "first_seen_utc": "2026-10-22T07:06:10Z"},                                         # margin: ignored
    {"id": 3, "code": "c", "title": "Binance Will Delist AAA, BBB, CCC on 2026-11-05", "release_ms": REL,
     "first_seen_utc": "2026-10-22T07:06:10Z"},
])
TABLE = pd.DataFrame({"symbol": ["AAA_USDT", "BBB_USDT"], "base": ["AAA", "BBB"], "type": [1, 1], "state": [0, 0],
                      "taker": [0.0002, 0.0002], "maker": [0.0, 0.0], "contract_size": [1, 1], "settle": ["USDT"] * 2})
LAST = {"AAA_USDT": 2.0, "BBB_USDT": 9.0}
SPOT = {"AAAUSDT": 2.1, "BBBUSDT": 1.0, "CCCUSDT": 1.0}


def bars(s, e, path=(2.0, 1.6)):
    t = np.arange(s, e, H)
    p = np.interp(t, [t[0], t[-1]], path)
    return pd.DataFrame({"t": t, "open": p, "high": p * 1.02, "low": p * 0.98, "close": p})


class ForwardDelistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.cat, self.ticks = d / "catalog.csv", d / "ticks"
        CATALOG.to_csv(self.cat, index=False)
        self.old_j = fd.J
        fd.J = d / "journal"

    def tearDown(self):
        fd.J = self.old_j
        self.tmp.cleanup()

    def run_tick(self, now, spot=SPOT):
        return fd.tick(now, contracts=lambda: TABLE, last_price=lambda c: LAST[c], spot_price=lambda s: spot.get(s),
                       klines=lambda c, s, e: bars(s, e),
                       funding=lambda c, s, e: pd.DataFrame({"t": [s + H + 8 * H, s + H + 16 * H], "rate": [-0.001, 0.0005]}),
                       catalog=self.cat, ticks=self.ticks)

    def test_tickets_and_skips_once(self):
        now = ms("2026-10-22T07:07")
        self.run_tick(now)
        self.run_tick(now + 60_000)                                   # idempotent
        tk = pd.read_csv(fd.J / "tickets.csv")
        self.assertEqual(list(tk.contract), ["AAA_USDT"])
        self.assertEqual(int(tk.entry_ms.iloc[0]), ms("2026-10-22T08:00"))
        self.assertEqual(int(tk.exit_ms.iloc[0]), ms("2026-10-22T09:00"))
        self.assertEqual(tk.check.iloc[0], "verified")
        sk = pd.read_csv(fd.J / "skipped.csv")
        self.assertEqual(sk.set_index("ticker").reason.to_dict(), {"BBB": "mismatch", "CCC": "no_contract"})

    def test_missed_and_unverified(self):
        self.run_tick(ms("2026-10-22T10:30"))                         # entry 11:00 is > release + 3 h
        sk = pd.read_csv(fd.J / "skipped.csv")
        self.assertEqual(set(sk.reason), {"missed"})
        self.assertFalse((fd.J / "tickets.csv").exists())

    def test_unverified_without_spot_price(self):
        self.run_tick(ms("2026-10-22T07:07"), spot={})
        tk = pd.read_csv(fd.J / "tickets.csv")
        self.assertEqual(sorted(tk.contract), ["AAA_USDT", "BBB_USDT"])
        self.assertEqual(set(tk.check), {"unverified"})

    def test_score_math(self):
        self.run_tick(ms("2026-10-22T07:07"))
        tk = pd.read_csv(fd.J / "tickets.csv").iloc[0]
        st = self.run_tick(int(tk.exit24_ms) + H + 11 * 60_000)
        sc = pd.read_csv(fd.J / "scores.csv").iloc[0]
        e = int(tk.entry_ms)
        b = bars(e - H, int(tk.exit24_ms) + 2 * H)
        op = lambda m: b.loc[b.t == m, "open"].item()
        self.assertAlmostEqual(sc.gross, -(op(e + H) / op(e) - 1))
        self.assertAlmostEqual(sc.gross_24h, -(op(e + 24 * H) / op(e) - 1))
        self.assertAlmostEqual(sc.funding, 0.0)                       # first settlement is at entry + 8 h
        self.assertAlmostEqual(sc.funding_24h, -0.001 + 0.0005)
        self.assertAlmostEqual(sc.cost_measured, 2 * 0.0002 + 2 * fd.SPREAD_FALLBACK)
        self.assertAlmostEqual(sc.net, sc.gross - sc.cost_measured + sc.funding)
        self.assertAlmostEqual(sc.net_2x, sc.gross - 0.008 + sc.funding)
        self.assertAlmostEqual(sc.mae_1h, b.loc[b.t == e, "high"].item() / op(e) - 1)
        self.assertEqual(st["scored_notices"], 1)
        self.assertTrue(st["decision"].startswith("pending"))


if __name__ == "__main__":
    unittest.main()
