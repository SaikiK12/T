import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_settlehop as sh

H, DAY = sh.H, sh.DAY
D0 = 1_740_009_600_000                         # 2025-02-20 00:00 UTC, an invented day inside the lane's rows


def bars(t0, close, traded=None, qv=None):
    n = len(close)
    return {"t": t0 + H * np.arange(n, dtype=np.int64), "close": np.asarray(close, float),
            "traded": np.ones(n, bool) if traded is None else np.asarray(traded, bool),
            "qv": None if qv is None else np.asarray(qv, float)}


def fund(ts, rates):
    r = np.asarray(rates, float)
    return np.asarray(ts, np.int64), r, np.concatenate([[0.0], np.cumsum(r)])


def hops(rows):
    """A table of selected hops with the columns book() and net() read."""
    return pd.DataFrame([{"T": t, "coin": c, "price": p, "fund": f, "cost_s_bp": 8.5, "cost_h_bp": 1.0, "e": e,
                          "same": True} for t, c, p, f, e in rows])


class TestSignals(unittest.TestCase):
    def test_gap_and_live_rules(self):
        T = D0 + 8 * H
        ts = [T - 16 * H, T - 8 * H, T, T + H, T + 40 * H]     # 8 h, 8 h, then a 1 h gap and a 39 h gap
        fs = fund(ts, [0.001, 0.004, 0.002, 0.003, 0.005])
        fh = fund(D0 - 20 * H + H * np.arange(0, 80), np.full(80, 0.0001))
        t, rp, hp, es = sh.signals(fs, fh)
        self.assertEqual(t.tolist(), [T - 8 * H, T])           # the 1 h and the 39 h gaps are not hops
        self.assertEqual(rp.tolist(), [0.001, 0.004])          # the rate settled before the entry
        np.testing.assert_allclose(es, [0.001 - 0.0002, 0.004 - 0.0002])

    def test_h_must_settle_in_the_two_hours_before_the_entry(self):
        T = D0 + 16 * H
        fs = fund([T - 8 * H, T], [0.004, 0.004])
        fh = fund([T - 6 * H, T - 5 * H], [0.0001, 0.0001])      # H's last settlement is 4 h before the entry
        self.assertEqual(len(sh.signals(fs, fh)[0]), 0)
        fh = fund([T - 3 * H, T + H], [0.0001, 0.0001])          # 2 h before the entry: live
        self.assertEqual(sh.signals(fs, fh)[0].tolist(), [T])

    def test_negative_spread_reverses_the_hop(self):
        T = D0 + 8 * H
        fs = fund([T - 8 * H, T], [-0.002, -0.002])
        fh = fund([T - 2 * H], [0.0005])
        _, _, _, es = sh.signals(fs, fh)
        self.assertAlmostEqual(es[0], -0.003)                  # long S (paid 0.2%), short H (paid 0.05% an hour)


class TestHop(unittest.TestCase):
    def setUp(self):
        self.T = D0 + 8 * H                                    # bars from D0: T - 2 h is row 6, T is row 8
        self.sb = bars(D0, [100] * 6 + [100, 98, 99, 99])      # entry close 100 (row 6), 98 at T, 99 at T + 1 h
        self.hb = bars(D0, [50] * 6 + [50, 50, 50.5, 50.5])    # entry 50, 50 at T, 50.5 at T + 1 h

    def test_short_s_long_h_accounting(self):
        T = self.T
        fs = fund([T - 8 * H, T - H, T, T + 2 * H], [0.01, 0.02, 0.005, 0.03])
        fh = fund([T - H, T, T + H, T + 2 * H], [0.001, 0.0002, 0.0003, 0.002])
        h = sh.hop(self.sb, self.hb, fs, fh, T, 1)
        self.assertAlmostEqual(h["price"], (50.5 / 50 - 1) - (99 / 100 - 1))
        self.assertAlmostEqual(h["fund"], 0.005 - (0.0002 + 0.0003))   # S at T; H at T and T + 1 h; T - 1 h is out
        self.assertAlmostEqual(h["fund_s"], 0.005)
        self.assertAlmostEqual(h["fund_h"], -0.0005)
        self.assertAlmostEqual(h["price0"], (50 / 50 - 1) - (98 / 100 - 1))   # closed at T
        self.assertAlmostEqual(h["fund0"], 0.005 - 0.0002)
        self.assertFalse(h["stale"])

    def test_long_s_short_h_mirrors(self):
        T = self.T
        fs, fh = fund([T], [-0.004]), fund([T, T + H], [0.0001, 0.0001])
        a = sh.hop(self.sb, self.hb, fs, fh, T, 1)
        b = sh.hop(self.sb, self.hb, fs, fh, T, -1)
        self.assertAlmostEqual(a["price"], -b["price"])
        self.assertAlmostEqual(b["fund"], 0.004 + 0.0002)      # the long receives 0.4% and the short H receives too

    def test_untraded_entry_is_no_hop_and_untraded_exit_is_stale(self):
        T = self.T
        fs, fh = fund([T], [0.004]), fund([T, T + H], [0.0, 0.0])
        sb = dict(self.sb, traded=np.array([True] * 6 + [False] + [True] * 3))
        self.assertIsNone(sh.hop(sb, self.hb, fs, fh, T, 1))
        hb = dict(self.hb, traded=np.array([True] * 7 + [False, False, False]))   # nothing trades after the entry
        h = sh.hop(self.sb, hb, fs, fh, T, 1)
        self.assertTrue(h["stale"])
        self.assertAlmostEqual(h["price"], -(99 / 100 - 1))     # the H leg exits at its entry close

    def test_lighter_volume_is_the_24_bars_before_the_entry(self):
        T = D0 + 30 * H
        n = 32
        hb = bars(D0, np.full(n, 10.0), qv=np.arange(n, dtype=float))
        sb = bars(D0, np.full(n, 10.0))
        h = sh.hop(sb, hb, fund([T], [0.004]), fund([T, T + H], [0.0, 0.0]), T, 1)
        self.assertEqual(h["qv24"], float(np.arange(5, 29).sum()))   # bars opening T - 25 h (row 5) to T - 2 h (row 28)

    def test_missing_h_settlement_is_no_hop(self):
        T = self.T
        fs = fund([T], [0.004])
        self.assertIsNone(sh.hop(self.sb, self.hb, fs, fund([T - H, T], [0.0, 0.0]), T, 1))       # no T + 1 h
        self.assertIsNone(sh.hop(self.sb, self.hb, fs, fund([T - H, T + H], [0.0, 0.0]), T, 1))   # no T
        self.assertIsNotNone(sh.hop(self.sb, self.hb, fs, fund([T - H, T, T + H], [0.0] * 3), T, 1))


class TestIdentityAndCost(unittest.TestCase):
    def closes(self, rets, start=100.0):
        days = D0 + DAY * np.arange(len(rets) + 1)
        c = start * np.cumprod(np.r_[1.0, 1 + np.asarray(rets)])
        return dict(zip(days.tolist(), c.tolist()))

    def test_same_coin(self):
        rng = np.random.default_rng(3)
        r = rng.normal(0, 0.03, 40)
        entry = D0 + 40 * DAY + 5 * H
        self.assertTrue(sh.same_coin(self.closes(r), self.closes(r * 1.01), entry))
        self.assertFalse(sh.same_coin(self.closes(r), self.closes(rng.normal(0, 0.03, 40)), entry))
        short = {k: v for k, v in self.closes(r).items() if k > entry - 15 * DAY}
        self.assertFalse(sh.same_coin(short, self.closes(r), entry))      # fewer than 20 paired days

    def test_lighter_bands(self):
        self.assertEqual(sh.lighter_cost_bp(5e3), 26.67)
        self.assertEqual(sh.lighter_cost_bp(1e4), 7.27)
        self.assertEqual(sh.lighter_cost_bp(2e6), 1.09)
        self.assertEqual(sh.lighter_cost_bp(5e9), 0.26)
        self.assertEqual(sh.lighter_cost_bp(np.nan), 26.67)


class TestBook(unittest.TestCase):
    def test_select_caps_slots_by_e(self):
        T = D0 + 8 * H
        rows = [(T, f"C{i}", 0.0, 0.0, 0.003 + i * 1e-4) for i in range(8)] + [(T + 8 * H, "X", 0, 0, 0.002)]
        cand = hops(rows)
        cand.loc[cand.coin == "C7", "same"] = False
        x = sh.select(cand, 0.003)
        self.assertEqual(x.coin.tolist(), ["C6", "C5", "C4", "C3", "C2"])   # C7 failed identity; X is under theta

    def test_book_and_costs(self):
        T = D0 + 8 * H
        h = hops([(T, "A", 0.001, 0.004, 0.005), (T + DAY, "B", -0.002, 0.003, 0.005)])
        days = D0 + DAY * np.arange(3)
        cost = 2 * (8.5 + 1.0) / 1e4
        x = sh.book(h, days, 1)
        np.testing.assert_allclose(x, [(0.005 - cost) / 5 * 1e4, (0.001 - cost) / 5 * 1e4, 0.0])
        np.testing.assert_allclose(sh.net(h, 3), [0.005 - 3 * cost, 0.001 - 3 * cost])
        np.testing.assert_allclose(sh.net(h, 1, s_bp=3.0), [0.005 - 2 * 4.0e-4, 0.001 - 2 * 4.0e-4])

    def test_decide(self):
        good = {"t1": 2.5, "day2_bp": 1.0, "half1_day1_bp": 2.0, "half2_day1_bp": 0.5, "wo_best_day1_bp": 0.3}
        self.assertEqual(sh.decide(good)["verdict"], "PASS")
        for k, v in (("t1", 1.9), ("day2_bp", -0.1), ("half2_day1_bp", np.nan), ("wo_best_day1_bp", -1.0)):
            self.assertEqual(sh.decide(dict(good, **{k: v}))["verdict"], "NULL", k)
        self.assertEqual(sh.decide({})["verdict"], "NULL")


class TestReaders(unittest.TestCase):
    def test_rows_outside_the_lane_are_never_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "klines_1h").mkdir()
            (root / "fundingRate").mkdir()
            t = np.array([sh.T0 - DAY, sh.T0, sh.T0 + H, sh.T1 - H, sh.T1, sh.T1 + H], np.int64)
            pd.DataFrame({"t": t, "close": np.arange(6.0) + 1, "volume": np.ones(6)}).to_parquet(
                root / "klines_1h" / "XUSDT.parquet")
            ft = np.array([sh.T0 - 8 * H, sh.T0 + 8 * H + 2, sh.T1 - 8 * H - 1000, sh.T1 + 2], np.int64)
            pd.DataFrame({"t": ft, "rate": [0.1, 0.2, 0.3, 0.4]}).to_parquet(root / "fundingRate" / "XUSDT.parquet")
            with mock.patch.object(sh, "DATA", root):
                b = sh.load_bars("binance", "XUSDT")
                f = sh.load_funding("binance", "XUSDT")
            self.assertEqual(b["t"].tolist(), [sh.T0, sh.T0 + H, sh.T1 - H])
            self.assertEqual(f[0].tolist(), [sh.T0 + 8 * H, sh.T1 - 8 * H])   # stamps rounded to the hour
            self.assertEqual(f[1].tolist(), [0.2, 0.3])

    def test_manifest_refuses_unlisted_or_changed_files(self):
        with tempfile.TemporaryDirectory(dir=sh.ROOT / "experiments") as d:
            f = Path(d) / "x.parquet"
            f.write_bytes(b"abc")
            rel = f.relative_to(sh.ROOT).as_posix()
            with mock.patch.dict(sh.MANIFEST, {rel: sh.prereg.sha256_file(f)}, clear=True):
                self.assertEqual(sh.checked(f), f)
                f.write_bytes(b"abd")
                with self.assertRaises(sh.prereg.PreregError):
                    sh.checked(f)
            with mock.patch.dict(sh.MANIFEST, {"other": "0"}, clear=True), self.assertRaises(sh.prereg.PreregError):
                sh.checked(f)

    def test_bands_match_their_snapshots(self):
        rows = []
        for (upper, bp), lo in zip(sh.LIGHTER_BANDS, (0, 1e4, 1e5, 1e6, 1e7, 1e8)):
            for k in range(3):                                  # medians bp: one row each side of it, and it
                rows.append({"buy_1k_bp": bp + (k - 1), "sell_1k_bp": bp + (k - 1), "vol24_usd": lo * 1.5 + 1})
        with tempfile.TemporaryDirectory(dir=sh.ROOT / "experiments") as d:
            f = Path(d) / "00.parquet"
            pd.DataFrame(rows).to_parquet(f)
            rel = f.relative_to(sh.ROOT).as_posix()
            self.assertEqual(sh.check_bands([rel]), 1)
            rows[0]["buy_1k_bp"] = rows[1]["buy_1k_bp"] = 99.0          # moves the first band's median
            rows[0]["sell_1k_bp"] = rows[1]["sell_1k_bp"] = 99.0
            pd.DataFrame(rows).to_parquet(f)
            with self.assertRaises(ValueError):
                sh.check_bands([rel])

    def test_eligible(self):
        first = sh.T0 + (sh.CORR_DAYS + 1) * DAY + H
        T = np.array([first - H, first, sh.T1 - 2 * H, sh.T1 - H])
        self.assertEqual(sh.eligible(T).tolist(), [False, True, True, False])


if __name__ == "__main__":
    unittest.main()
