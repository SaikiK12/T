import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import forward_announce as fa  # noqa: E402

H = fa.H
ms = lambda s: int(pd.Timestamp(s, tz="UTC").value // 10**6)
REL = ms("2026-10-22T07:00:30")          # notices released at 07:00, seen by the 07:05 loop
SEEN = "2026-10-22T07:05:40Z"
NEWS = pd.DataFrame([
    {"id": 1, "code": "a", "title": "Introducing OldCoin (OLD) on Binance HODLer Airdrops!",
     "release_ms": ms("2026-08-20T06:00"), "first_seen_utc": "2026-10-20T17:09:23Z"},              # backfill: ignored
    {"id": 2, "code": "b", "title": "Binance Futures Will Update the Funding Rate Settlement Frequency of AAAUSDT "
                                    "Perpetual Contract", "release_ms": REL, "first_seen_utc": SEEN},
    {"id": 3, "code": "c", "title": "Binance Futures Will Resume the Funding Rate Settlement Frequency of BBBUSDT "
                                    "Perpetual Contract", "release_ms": REL, "first_seen_utc": SEEN},   # resumed: not FF
    {"id": 4, "code": "d", "title": "Introducing Newcoin (NEW) on Binance HODLer Airdrops! Earn NEW With BNB",
     "release_ms": REL, "first_seen_utc": SEEN},
    {"id": 5, "code": "e", "title": "Introducing Lostcoin (LOST) on Binance Launchpool!", "release_ms": REL,
     "first_seen_utc": SEEN},                                                                     # no MEXC perp
])
LISTING = NEWS.iloc[[3]]                 # the same notice filed in two catalogs counts once
TABLE = pd.DataFrame({"symbol": ["AAA_USDT", "BBB_USDT", "NEW_USDT"], "base": ["AAA", "BBB", "NEW"],
                      "type": [1] * 3, "state": [0] * 3, "taker": [0.0002] * 3, "maker": [0.0] * 3,
                      "contract_size": [1] * 3, "settle": ["USDT"] * 3})
QUOTE = {"AAA_USDT": {"last": 2.0, "funding": -0.02}, "NEW_USDT": {"last": 1.0, "funding": 0.0001}}
SPOT = {"AAAUSDT": 2.1}


def bars(s, e, path=(2.0, 1.6)):
    t = np.arange(s, e, H)
    p = np.interp(t, [t[0], t[-1]], path)
    return pd.DataFrame({"t": t, "open": p, "high": p * 1.02, "low": p * 0.98, "close": p})


class ForwardAnnounceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.cats = [d / "news.csv", d / "listing.csv"]
        NEWS.to_csv(self.cats[0], index=False)
        LISTING.to_csv(self.cats[1], index=False)
        self.ticks = d / "ticks"
        self.old_j = fa.J
        fa.J = d / "journal"

    def tearDown(self):
        fa.J = self.old_j
        self.tmp.cleanup()

    def run_tick(self, now):
        return fa.tick(now, contracts=lambda: TABLE, quote=lambda c: QUOTE.get(c), spot_price=lambda s: SPOT.get(s),
                       klines=lambda c, s, e: bars(s, e),
                       funding=lambda c, s, e: pd.DataFrame({"t": [s + H + 8 * H, s + H + 16 * H],
                                                             "rate": [-0.001, 0.002]}),
                       catalogs=self.cats, ticks=self.ticks)

    def test_tickets_and_skips_once(self):
        now = ms("2026-10-22T07:06")
        st = self.run_tick(now)
        self.run_tick(now + 60_000)                                   # idempotent
        self.assertEqual(st["notices_seen"], 3)
        tk = pd.read_csv(fa.J / "tickets.csv").set_index("book")
        self.assertEqual(sorted(tk.index), ["FF", "PL"])
        self.assertEqual(tk.loc["FF", "ticket"], "FF2-AAA_USDT")
        self.assertEqual(int(tk.loc["FF", "entry_ms"]), ms("2026-10-22T08:00"))
        self.assertEqual(int(tk.loc["FF", "exit_ms"]), ms("2026-10-22T09:00"))
        self.assertEqual(int(tk.loc["PL", "exit_ms"]), ms("2026-10-29T08:00"))
        self.assertEqual(tk.loc["FF", "check"], "verified")
        self.assertEqual(tk.loc["PL", "check"], "unverified")         # no spot pair yet
        self.assertAlmostEqual(tk.loc["FF", "funding_rate_at_freeze"], -0.02)
        sk = pd.read_csv(fa.J / "skipped.csv")
        self.assertEqual(sk.set_index("ticker").reason.to_dict(), {"LOST": "no_contract"})
        self.assertEqual(len(pd.read_csv(fa.J / "tickets.csv")), 2)

    def test_missed(self):
        self.run_tick(ms("2026-10-22T10:30"))                         # entry 11:00 is > release + 3 h
        sk = pd.read_csv(fa.J / "skipped.csv")
        self.assertEqual(set(sk.reason), {"missed"})
        self.assertFalse((fa.J / "tickets.csv").exists())

    def test_score_math(self):
        self.run_tick(ms("2026-10-22T07:06"))
        tk = pd.read_csv(fa.J / "tickets.csv").set_index("book")
        e = int(tk.loc["FF", "entry_ms"])
        st = self.run_tick(e + 24 * H + H + 11 * 60_000)              # FF's last horizon (24 h logged) has closed
        sc = pd.read_csv(fa.J / "scores.csv").set_index("book")
        self.assertEqual(list(sc.index), ["FF"])                      # PL waits for 168 h
        b = bars(e - H, e + 24 * H + 2 * H)
        op = lambda m: b.loc[b.t == m, "open"].item()
        ff = sc.loc["FF"]
        self.assertAlmostEqual(ff.gross, op(e + H) / op(e) - 1)       # long
        self.assertAlmostEqual(ff.funding, 0.0)                       # no settlement inside the first hour
        self.assertAlmostEqual(ff.gross_24h, op(e + 24 * H) / op(e) - 1)
        self.assertAlmostEqual(ff.net_1x_24h, ff.gross_24h - 0.004 - (-0.001 + 0.002))   # the long pays funding
        self.assertAlmostEqual(ff.cost_measured, 2 * 0.0002 + 2 * fa.SPREAD_FALLBACK)
        self.assertAlmostEqual(ff.net, ff.gross - ff.cost_measured + ff.funding)
        self.assertAlmostEqual(ff.mae, 1 - b.loc[(b.t >= e) & (b.t < e + H), "low"].min() / op(e))
        self.assertTrue(np.isnan(ff.gross_72h))
        self.assertEqual(st["books"]["FF"]["scored_notices"], 1)
        st = self.run_tick(e + 168 * H + H + 11 * 60_000)
        pl = pd.read_csv(fa.J / "scores.csv").set_index("book").loc["PL"]
        b = bars(e - H, e + 168 * H + 2 * H)
        self.assertAlmostEqual(pl.gross, -(op(e + 168 * H) / op(e) - 1))
        self.assertAlmostEqual(pl.funding, -0.001 + 0.002)            # the short receives funding
        self.assertAlmostEqual(pl.gross_72h, -(op(e + 72 * H) / op(e) - 1))
        self.assertTrue(st["books"]["PL"]["decision"].startswith("pending"))


if __name__ == "__main__":
    unittest.main()
