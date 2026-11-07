import csv
import gc
import json
import shutil
import subprocess
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from lab import xfund
from scripts import forward_xfund as fx

DAY, H = xfund.DAY, xfund.H
ROOT = Path(__file__).resolve().parent.parent
QX = ROOT / "engine" / "target" / "release" / "qx"


def synthetic(root, t0, days, seed=0):
    """Three coins on four venues. Coin X pays more on Gate and Binance; Y has no spread; Z is listed on two venues."""
    rng = np.random.default_rng(seed)
    hours = np.arange(t0, t0 + days * DAY, H)
    rates = {"XUSDT": {"binance": 2e-4, "gate": 3e-4, "hyperliquid": 1e-5, "mexc": 1e-4},
             "YUSDT": {"binance": 1e-4, "gate": 1e-4, "hyperliquid": 1.25e-5, "mexc": 1e-4},
             "ZUSDT": {"gate": 2e-4, "hyperliquid": 1e-6}}
    names = {"binance": "{}USDT", "gate": "{}_USDT", "hyperliquid": "{}", "mexc": "{}_USDT"}
    vol = {"binance": "volume", "gate": "vol_contracts", "hyperliquid": "volume", "mexc": "vol"}
    rows = []
    for key, by in rates.items():
        base = key[:-4]
        px = 10 * np.exp(np.cumsum(rng.normal(0, 0.01, len(hours))))
        row = {"key": key, "binance": "", "gate": "", "hyperliquid": "", "mexc": ""}
        for v, r in by.items():
            sym = names[v].format(base)
            row[v] = sym
            p = px * np.exp(rng.normal(0, 0.0005, len(hours)))
            if v == "hyperliquid":
                tt = np.arange(t0, t0 + days * DAY, DAY)
                close = p[23::24][: len(tt)]
                ft = hours
            else:
                tt, close = hours, p
                ft = hours[hours % (8 * H) == 0]
            d = root / v / "prices"
            d.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"t": tt.astype(np.int64), "close": close, vol[v]: np.ones(len(tt))}).to_parquet(
                d / f"{sym}.parquet", index=False)
            d = root / v / "funding"
            d.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"t": ft.astype(np.int64), "rate": np.full(len(ft), r)}).to_parquet(
                d / f"{sym}.parquet", index=False)
        rows.append(row)
    return pd.DataFrame(rows)


class ForwardXfundTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = {k: getattr(fx, k) for k in ("DATA", "J", "SYMBOLS", "WARM", "ON_TIME")}
        fx.WARM, fx.ON_TIME = "2026-08-01", "2026-10-22"
        fx.DATA, fx.J, fx.SYMBOLS = self.tmp / "fwd", self.tmp / "journal", self.tmp / "symbols.csv"
        self.t0 = fx.ms(fx.WARM)
        synthetic(fx.DATA, self.t0, 84).to_csv(fx.SYMBOLS, index=False)
        self.mids = lambda: {}
        self.listed = lambda: {}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(fx, k, v)
        shutil.rmtree(self.tmp)

    def run_at(self, day, hour=0.1, mids=None):
        now = fx.ms(day) + int(hour * H)
        return fx.tick(now, fetch=False, mids_fn=mids or self.mids, listed_fn=self.listed)

    def test_journal_reader_closes_its_csv_file(self):
        path = fx.J / "decisions.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("run,day\nr1,2026-10-21\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            self.assertEqual(fx.rows("decisions.csv"), [{"run": "r1", "day": "2026-10-21"}])
            gc.collect()
        self.assertFalse([w for w in caught if issubclass(w.category, ResourceWarning)])

    def test_replay_matches_the_twin_and_reruns_write_nothing(self):
        self.run_at("2026-10-21")
        dec, tk, dy = fx.journal()
        self.assertTrue(dec and tk and dy)
        self.assertEqual({r["kind"] for r in dec}, {"replay"})
        u, t = fx.universe((fx.ms("2026-10-21") - self.t0) // DAY + 1)
        for b, (s, l, th, k, _) in fx.BOOKS.items():
            vset = [fx.NAMES.index(v) for v in s.split("+")]
            w0 = xfund.window_start(u, vset, l)
            book = xfund.Book(vset, l, th, k)
            rows, trades = xfund.replay(u, book, w0)
            rows.loc[rows.index[-1], "legs"] -= 2.0 * len(book.open)   # the twin closes what is open at the end
            mine = [r for r in dy if r["book"] == b]
            self.assertEqual(len(mine), len(rows))                     # intervals up to "now"
            got = np.array([float(r["net_close"]) for r in mine])
            np.testing.assert_allclose(got, xfund.net(rows, k, fx.COSTS[0]).to_numpy(), atol=1e-9)
            enters = [r for r in tk if r["book"] == b and r["action"] == "enter" and r["day"] < "2026-10-21"]
            self.assertEqual([r["coin"] for r in enters], [x["coin"] for x in trades])
        n = sum(1 for _ in open(fx.J / "tickets.csv"))
        self.assertIsNone(self.run_at("2026-10-21", hour=1))
        self.assertEqual(n, sum(1 for _ in open(fx.J / "tickets.csv")))

    def test_first_live_day_takes_over_at_live_prices(self):
        self.run_at("2026-10-21")
        live = lambda: {"gate": {"X_USDT": 1.0, "Z_USDT": 1.0}, "hyperliquid": {"X": 1.0, "Z": 1.0},
                        "binance": {"XUSDT": 1.0}, "mexc": {"X_USDT": 1.0}}
        self.run_at("2026-10-22", mids=live)
        dec, tk, dy = fx.journal()
        today = [r for r in tk if r["day"] == "2026-10-22"]
        self.assertTrue(any(r["action"] == "inherit" for r in today))
        self.assertTrue(all(r["kind"] == "ontime" for r in today))
        self.assertTrue(all(r["fill_long"] for r in today if r["action"] == "inherit"))
        self.run_at("2026-10-23")
        _, tk, dy = fx.journal()
        first = [r for r in dy if r["day"] == "2026-10-23"]
        self.assertEqual({r["kind"] for r in first}, {"ontime"})
        for r in first:                                         # the take-over pays its legs in the decided book only
            inh = sum(x["action"] == "inherit" for x in tk if x["book"] == r["book"] and x["day"] == "2026-10-22")
            self.assertGreaterEqual(float(r["legs"]), 2 * inh)
            if inh:
                self.assertNotEqual(r["fill_adj"], "0.0000000000")
        status = json.loads((fx.J / "status.json").read_text())
        self.assertEqual(status["A"]["scored_days"], 1)

    def test_rows_of_a_cut_run_are_ignored(self):
        self.run_at("2026-10-21")
        with open(fx.J / "tickets.csv", "a", newline="") as f:
            w = csv.DictWriter(f, fx.TICKET_COLS, lineterminator="\n")
            w.writerow({"run": "cut", "day": "2026-10-22", "book": "A", "action": "enter", "coin": "YUSDT",
                        "long": "gate", "short": "hyperliquid", "spread_ann": "1", "forced": "false",
                        "kind": "ontime"})
        _, tk, _ = fx.journal()
        self.assertFalse(any(r["run"] == "cut" for r in tk))

    def test_gate_funding_pages_back_from_the_end(self):
        hours = list(range(0, 2500 * 3600, 3600))
        calls = []

        def fake(url, body=None, tries=5):
            q = dict(x.split("=") for x in url.split("?")[1].split("&"))
            calls.append(q)
            got = [h for h in reversed(hours) if int(q["from"]) <= h <= int(q["to"])][: int(q["limit"])]
            return [{"t": h, "r": "0.0001"} for h in got]

        saved, fx._json = fx._json, fake
        try:
            df = fx.gate_funding("X_USDT", 0, hours[-1] * 1000)
        finally:
            fx._json = saved
        self.assertEqual(len(calls), 3)
        self.assertEqual(sorted(df.t.tolist()), [h * 1000 for h in hours])

    @unittest.skipUnless(QX.exists(), "qx not built")
    def test_twin_matches_qx_on_the_synthetic_root(self):
        nd_end = "2026-10-20"
        spec = self.tmp / "spec.toml"
        venues = ",\n".join(f'{{ name = "{v}", prices = "{v}/prices", vol = "{c}", funding = "{v}/funding", '
                            f'bar_h = {24 if v == "hyperliquid" else 1} }}'
                            for v, c in (("binance", "volume"), ("gate", "vol_contracts"),
                                         ("hyperliquid", "volume"), ("mexc", "vol")))
        spec.write_text(f'''name = "t"
start = "{fx.WARM}"
end = "{nd_end}"
symbols = "{fx.SYMBOLS}"
venues = [
{venues}
]
sets = [["gate", "hyperliquid"], ["binance", "mexc"]]
lookbacks = [14]
thresholds = [0.05]
slots = [20]
costs = [0.0007, 0.0014, 0.0021]
corr_days = 30
corr_min = 0.9
corr_obs = 20
block_days = 10
reps = 10
seed = 1
keep_daily = 10
out = "{self.tmp / 'out'}"
''')
        subprocess.run([str(QX), "spread", str(spec)], check=True, capture_output=True,
                       env={"QX_DATA": str(fx.DATA), "PATH": "/usr/bin:/bin"})
        eng = pd.read_csv(self.tmp / "out" / "trades.csv")
        nd = (fx.ms(nd_end) + DAY - self.t0) // DAY + 1
        u, _ = fx.universe(nd)
        for s in ("gate+hyperliquid", "binance+mexc"):
            vset = [fx.NAMES.index(v) for v in s.split("+")]
            _, trades = xfund.replay(u, xfund.Book(vset, 14, 0.05, 20), xfund.window_start(u, vset, 14))
            e = eng[eng.strategy == f"{s} L14d th5% K20"]
            self.assertEqual([x["coin"] for x in trades], e.coin.tolist())
            self.assertEqual([x["long"] for x in trades], e.long.tolist())


if __name__ == "__main__":
    unittest.main()
