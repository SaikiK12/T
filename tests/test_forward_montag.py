import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import forward_montag as fm  # noqa: E402

H = fm.H
ms = lambda s: int(pd.Timestamp(s, tz="UTC").value // 10**6)
REL = ms("2026-10-22T07:00:30")          # a tag notice released at 07:00, seen by the 07:06 tick
SEEN = "2026-10-22T07:06:10Z"
NEWS = pd.DataFrame([
    {"id": 1, "code": "a", "title": "Binance Will Extend the Monitoring Tag to Include OLD on 2026-09-01",
     "release_ms": ms("2026-08-20T06:00"), "first_seen_utc": "2026-10-20T17:09:23Z"},              # backfill: ignored
    {"id": 2, "code": "b", "title": "Binance Will Delist AAA on 2026-10-30", "release_ms": REL,
     "first_seen_utc": SEEN},                                                                     # not a tag: ignored
    {"id": 3, "code": "c", "title": "Binance Will Extend the Monitoring Tag to Include AAA, BBB and CCC, and Remove "
                                    "the Monitoring Tag for DDD on 2026-10-23", "release_ms": REL,
     "first_seen_utc": SEEN},
])
DELIST = NEWS.iloc[[2]]                  # the same notice filed in both catalogs counts once
TABLE = pd.DataFrame({"symbol": ["AAA_USDT", "BBB_USDT", "DDD_USDT"], "base": ["AAA", "BBB", "DDD"], "type": [1] * 3,
                      "state": [0] * 3, "taker": [0.0002] * 3, "maker": [0.0] * 3, "contract_size": [1] * 3,
                      "settle": ["USDT"] * 3})
LAST = {"AAA_USDT": 2.0, "BBB_USDT": 9.0, "DDD_USDT": 1.0}
SPOT = {"AAAUSDT": 2.1, "BBBUSDT": 1.0, "CCCUSDT": 1.0, "DDDUSDT": 1.0}


def bars(s, e, path=(2.0, 1.6)):
    t = np.arange(s, e, H)
    p = np.interp(t, [t[0], t[-1]], path)
    return pd.DataFrame({"t": t, "open": p, "high": p * 1.02, "low": p * 0.98, "close": p})


class ForwardMontagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.cats = [d / "news.csv", d / "delisting.csv"]
        NEWS.to_csv(self.cats[0], index=False)
        DELIST.to_csv(self.cats[1], index=False)
        self.ticks = d / "ticks"
        self.old_j = fm.J
        fm.J = d / "journal"

    def tearDown(self):
        fm.J = self.old_j
        self.tmp.cleanup()

    def run_tick(self, now, spot=SPOT):
        return fm.tick(now, contracts=lambda: TABLE, last_price=lambda c: LAST[c], spot_price=lambda s: spot.get(s),
                       klines=lambda c, s, e: bars(s, e),
                       funding=lambda c, s, e: pd.DataFrame({"t": [s + H + 8 * H, s + H + 16 * H, s + H + 24 * H],
                                                             "rate": [-0.001, 0.0005, 0.002]}),
                       catalogs=self.cats, ticks=self.ticks)

    def test_tickets_and_skips_once(self):
        now = ms("2026-10-22T07:07")
        st = self.run_tick(now)
        self.run_tick(now + 60_000)                                   # idempotent
        self.assertEqual(st["tag_notices_seen"], 1)
        tk = pd.read_csv(fm.J / "tickets.csv")
        self.assertEqual(list(tk.contract), ["AAA_USDT"])           # DDD is untagged in the same title: not traded
        self.assertEqual(int(tk.entry_ms.iloc[0]), ms("2026-10-22T08:00"))
        self.assertEqual(int(tk.exit_ms.iloc[0]), ms("2026-10-23T08:00"))
        self.assertEqual(int(tk.exit1h_ms.iloc[0]), ms("2026-10-22T09:00"))
        self.assertEqual(tk.check.iloc[0], "verified")
        sk = pd.read_csv(fm.J / "skipped.csv")
        self.assertEqual(sk.set_index("ticker").reason.to_dict(), {"BBB": "mismatch", "CCC": "no_contract"})

    def test_missed(self):
        self.run_tick(ms("2026-10-22T10:30"))                         # entry 11:00 is > release + 3 h
        sk = pd.read_csv(fm.J / "skipped.csv")
        self.assertEqual(set(sk.reason), {"missed"})
        self.assertFalse((fm.J / "tickets.csv").exists())

    def test_score_math(self):
        self.run_tick(ms("2026-10-22T07:07"))
        tk = pd.read_csv(fm.J / "tickets.csv").iloc[0]
        self.assertEqual(self.run_tick(int(tk.exit_ms) + H)["scored_notices"], 0)    # bar not closed long enough
        st = self.run_tick(int(tk.exit_ms) + H + 11 * 60_000)
        sc = pd.read_csv(fm.J / "scores.csv").iloc[0]
        e = int(tk.entry_ms)
        b = bars(e - H, int(tk.exit_ms) + 2 * H)
        op = lambda m: b.loc[b.t == m, "open"].item()
        self.assertAlmostEqual(sc.gross, -(op(e + 24 * H) / op(e) - 1))
        self.assertAlmostEqual(sc.gross_1h, -(op(e + H) / op(e) - 1))
        self.assertAlmostEqual(sc.funding, -0.001 + 0.0005 + 0.002)    # settlements at +8, +16 and +24 h
        self.assertAlmostEqual(sc.funding_1h, 0.0)
        self.assertAlmostEqual(sc.cost_measured, 2 * 0.0002 + 2 * fm.SPREAD_FALLBACK)
        self.assertAlmostEqual(sc.net, sc.gross - sc.cost_measured + sc.funding)
        self.assertAlmostEqual(sc.net_2x, sc.gross - 0.008 + sc.funding)
        self.assertAlmostEqual(sc.mae_24h, b.loc[(b.t >= e) & (b.t < e + 24 * H), "high"].max() / op(e) - 1)
        self.assertEqual(st["scored_notices"], 1)
        self.assertTrue(st["decision"].startswith("pending"))


if __name__ == "__main__":
    unittest.main()
