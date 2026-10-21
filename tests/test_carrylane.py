import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import carrylane, xfund
from scripts import forward_xfund as fx
from tests.test_forward_xfund import synthetic

DAY, H = xfund.DAY, xfund.H


def synthetic_kc(root, t0, days, seed=0):
    """Three coins on Binance and Gate (hourly) and KuCoin (daily bars). KuCoin pays more on X and less on Z."""
    rng = np.random.default_rng(seed)
    hours = np.arange(t0, t0 + days * DAY, H)
    rates = {"XUSDT": {"binance": 1e-4, "gate": 1e-4, "kucoin": 4e-4},
             "YUSDT": {"binance": 1e-4, "gate": 1e-4, "kucoin": 1e-4},
             "ZUSDT": {"gate": 3e-4, "kucoin": 1e-5}}
    names = {"binance": "{}USDT", "gate": "{}_USDT", "kucoin": "{}USDTM"}
    vol = {"binance": "volume", "gate": "vol_contracts", "kucoin": "volume"}
    rows = []
    for key, by in rates.items():
        base = key[:-4]
        px = 10 * np.exp(np.cumsum(rng.normal(0, 0.01, len(hours))))
        row = {"key": key, "binance": "", "gate": "", "kucoin": ""}
        for v, r in by.items():
            sym = names[v].format(base)
            row[v] = sym
            p = px * np.exp(rng.normal(0, 0.0005, len(hours)))
            if v == "kucoin":
                tt = np.arange(t0, t0 + days * DAY, DAY)
                close = p[23::24][: len(tt)]
            else:
                tt, close = hours, p
            ft = hours[hours % (8 * H) == 0]
            for kind, df in (("prices", pd.DataFrame({"t": tt.astype(np.int64), "close": close,
                                                      vol[v]: np.ones(len(tt))})),
                             ("funding", pd.DataFrame({"t": ft.astype(np.int64), "rate": np.full(len(ft), r)}))):
                d = root / v / kind
                d.mkdir(parents=True, exist_ok=True)
                df.to_parquet(d / f"{sym}.parquet", index=False)
        rows.append(row)
    return pd.DataFrame(rows)


class LaneMatchesR278Test(unittest.TestCase):
    """The general lane, set up as R278, writes the same journal as R278's frozen script."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = {k: getattr(fx, k) for k in ("DATA", "J", "SYMBOLS", "WARM", "ON_TIME")}
        fx.WARM, fx.ON_TIME = "2026-08-01", "2026-10-22"
        fx.DATA, fx.J, fx.SYMBOLS = self.tmp / "a" / "fwd", self.tmp / "a" / "journal", self.tmp / "symbols.csv"
        synthetic(fx.DATA, fx.ms(fx.WARM), 84).to_csv(fx.SYMBOLS, index=False)
        shutil.copytree(fx.DATA, self.tmp / "b" / "fwd")
        self.lane = carrylane.Lane("xfund_fwd", "R278", self.tmp / "b", fx.SYMBOLS, fx.BOOKS, fx.NAMES, fx.WARM,
                                   fx.ON_TIME, data_dir=self.tmp / "b" / "fwd", enter_delisted=True)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(fx, k, v)
        shutil.rmtree(self.tmp)

    def test_three_ticks_write_identical_journals(self):
        live = lambda: {"gate": {"X_USDT": 1.0, "Z_USDT": 1.0}, "hyperliquid": {"X": 1.0, "Z": 1.0},
                        "binance": {"XUSDT": 1.0}, "mexc": {"X_USDT": 1.0}}
        gone = lambda: {"gate": {"X_USDT", "Y_USDT"}}                # Z leaves Gate on the second live day
        for day, mids, listed in (("2026-10-21", dict, dict), ("2026-10-22", live, dict),
                                  ("2026-10-23", live, gone), ("2026-10-24", dict, dict)):
            now = fx.ms(day) + int(0.1 * H)
            a = fx.tick(now, fetch=False, mids_fn=mids, listed_fn=listed)
            b = self.lane.tick(now, fetch=False, mids_fn=mids, listed_fn=listed)
            self.assertEqual(a, b)
        for name in ("tickets.csv", "days.csv", "decisions.csv"):
            self.assertEqual((fx.J / name).read_text(), (self.lane.j / name).read_text(), name)
        sa, sb = (json.loads((j / "status.json").read_text()) for j in (fx.J, self.lane.j))
        sa.pop("updated"), sb.pop("updated")
        self.assertEqual(sa, sb)
        tk = (fx.J / "tickets.csv").read_text()
        self.assertIn("inherit", tk)
        self.assertIn(",true,ontime,", tk)                         # the delisting forced an exit


class KucoinClientTest(unittest.TestCase):
    def setUp(self):
        self.saved = carrylane._json, carrylane.time.sleep
        carrylane.time.sleep = lambda s: None

    def tearDown(self):
        carrylane._json, carrylane.time.sleep = self.saved

    def test_candles_page_forwards_and_funding_pages_back(self):
        days = [k * DAY for k in range(450)]
        settle = list(range(0, 250 * 8 * H, 8 * H))
        calls = []

        def fake(url, body=None, tries=5):
            path, q = url.split("?")
            q = dict(x.split("=") for x in q.split("&"))
            calls.append(path)
            lo, hi = int(q["from"]), int(q["to"])
            if path.endswith("kline/query"):
                got = [t for t in days if lo <= t <= hi][:200]
                return {"code": "200000", "data": [[t, 1, 2, 0.5, 1.5, 7, 9] for t in got]}
            got = [t for t in reversed(settle) if lo <= t <= hi][:100]
            return {"code": "200000", "data": [{"symbol": q["symbol"], "timepoint": t, "fundingRate": 1e-4}
                                               for t in got]}

        carrylane._json = fake
        p = carrylane.kucoin_prices("XUSDTM", 0, days[-1] + DAY)
        self.assertEqual(p.t.tolist(), days)
        self.assertEqual(list(p.columns), ["t", "close", "volume"])
        self.assertEqual(sum(c.endswith("kline/query") for c in calls), 3)
        f = carrylane.kucoin_funding("XUSDTM", 0, settle[-1])
        self.assertEqual(sorted(f.t.tolist()), settle)
        self.assertEqual(sum(c.endswith("funding-rates") for c in calls), 3)

    def test_mids_listed_and_error_codes(self):
        answers = {"/api/v1/allTickers": [{"symbol": "XUSDTM", "bestBidPrice": "1.0", "bestAskPrice": "1.2"},
                                          {"symbol": "YUSDTM", "bestBidPrice": "0", "bestAskPrice": "1.2"}],
                   "/api/v1/contracts/active": [{"symbol": "XUSDTM", "status": "Open"},
                                                {"symbol": "YUSDTM", "status": "Paused"}]}
        carrylane._json = lambda url, body=None, tries=5: {"code": "200000",
                                                            "data": answers[url[len(carrylane.KUCOIN):]]}
        self.assertEqual(carrylane.kucoin_mids(), {"XUSDTM": 1.1})
        self.assertEqual(carrylane.kucoin_listed(), {"XUSDTM"})
        carrylane._json = lambda url, body=None, tries=5: {"code": "429000", "msg": "too many requests"}
        with self.assertRaises(RuntimeError):
            carrylane.kucoin_mids()


class KucoinLaneTest(unittest.TestCase):
    """A lane with a daily-bar venue (KuCoin) replays as the twin does and ticks live."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        books = {"A": ("gate+kucoin", 14, 0.05, 20, "test"), "B": ("binance+kucoin", 14, 0.05, 20, "test")}
        self.lane = carrylane.Lane("kc", "R0", self.tmp, self.tmp / "symbols.csv", books, ["binance", "gate", "kucoin"],
                                   "2026-08-01", "2026-10-22", data_dir=self.tmp / "fwd")
        synthetic_kc(self.lane.data, carrylane.ms("2026-08-01"), 84).to_csv(self.lane.symbols, index=False)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_replay_matches_the_twin_then_a_delisting_forces_the_exit(self):
        lane = self.lane
        lane.tick(carrylane.ms("2026-10-21") + H // 10, fetch=False, mids_fn=dict, listed_fn=dict)
        dec, tk, dy = lane.journal()
        u, _ = lane.universe((carrylane.ms("2026-10-21") - carrylane.ms(lane.warm)) // DAY + 1)
        for b, (s, l, th, k, _) in lane.books.items():
            vset = [lane.names.index(v) for v in s.split("+")]
            book = xfund.Book(vset, l, th, k)
            rows, trades = xfund.replay(u, book, xfund.window_start(u, vset, l))
            self.assertTrue(trades)
            rows.loc[rows.index[-1], "legs"] -= 2.0 * len(book.open)
            got = np.array([float(r["net_close"]) for r in dy if r["book"] == b])
            np.testing.assert_allclose(got, xfund.net(rows, k, carrylane.COSTS[0]).to_numpy(), atol=1e-9)
            self.assertEqual([r["coin"] for r in tk if r["book"] == b and r["action"] == "enter"],
                             [x["coin"] for x in trades])
        held = {r["coin"] for r in tk if r["book"] == "A" and r["action"] == "enter"}
        self.assertIn("XUSDT", held)
        live = lambda: {"gate": {"X_USDT": 1.0, "Z_USDT": 1.0}, "kucoin": {"XUSDTM": 1.01, "ZUSDTM": 1.0},
                        "binance": {"XUSDT": 1.0}}
        lane.tick(carrylane.ms("2026-10-22") + H // 10, fetch=False, mids_fn=live, listed_fn=dict)
        lane.tick(carrylane.ms("2026-10-23") + H // 10, fetch=False, mids_fn=live,
                  listed_fn=lambda: {"kucoin": {"ZUSDTM"}})
        _, tk, dy = lane.journal()
        out = [r for r in tk if r["day"] == "2026-10-23" and r["coin"] == "XUSDT"]
        self.assertEqual(len(out), 2)                           # forced out of both books, and not entered again
        self.assertTrue(all(r["action"] == "exit" and r["forced"] == "true" for r in out))
        inh = [r for r in tk if r["day"] == "2026-10-22" and r["action"] == "inherit"]
        self.assertTrue(inh and all(r["fill_long"] and r["fill_short"] for r in inh))
        status = json.loads((lane.j / "status.json").read_text())
        self.assertEqual((status["lane"], status["A"]["scored_days"]), ("kc", 1))

    def test_books_must_use_lane_venues(self):
        with self.assertRaises(ValueError):
            carrylane.Lane("x", "R0", self.tmp, self.tmp / "s.csv", {"A": ("gate+mexc", 14, 0.05, 20, "")},
                           ["gate", "kucoin"], "2026-08-01", "2026-10-22")


if __name__ == "__main__":
    unittest.main()
