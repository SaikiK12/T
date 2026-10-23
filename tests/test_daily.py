import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import daily

DAY, H = daily.DAY, daily.H
T0 = pd.Timestamp("2020-12-25", tz="UTC").value // 10**6     # bars start in the reserved year on purpose
DAYS = 60


def ms(day):
    return pd.Timestamp(day, tz="UTC").value // 10**6


def hourly(px, start=T0):
    n = len(px)
    t = start + np.arange(n) * H
    return pd.DataFrame({"t": t, "open": px, "high": px * 1.01, "low": px * 0.99, "close": px, "volume": 1.0,
                         "quote_volume": px * 10, "count": 5.0, "taker_buy_volume": 0.5,
                         "taker_buy_quote_volume": px * 4})


def write(root, rel, df):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)


def fixture(root, bump_from=None):
    """BTCUSDT and AAAUSDT (listed 2021-01-10) on Binance; AAA also on Gate (the same coin, 0.2% above) and on KuCoin
    (a different coin with the same ticker, 3x the price). bump_from: from that ms on, every price doubles and every
    funding rate gains 1, to check that no earlier row moves."""
    rng = np.random.default_rng(0)
    n = DAYS * 24
    btc = 30000 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    aaa_start = ms("2021-01-10")
    na = (T0 + n * H - aaa_start) // H
    aaa = 2.0 * np.exp(np.cumsum(rng.normal(0, 0.003, na)))
    bump = (lambda t, x: np.where(t >= bump_from, x * 2.0, x)) if bump_from else (lambda t, x: x)
    fb = (lambda t, x: np.where(t >= bump_from, x + 1.0, x)) if bump_from else (lambda t, x: x)

    def bars(px, start):
        d = hourly(px, start)
        for c in ("open", "high", "low", "close", "quote_volume", "taker_buy_quote_volume"):
            d[c] = bump(d.t.to_numpy(), d[c].to_numpy())
        return d

    dead = ms("2021-02-10 12:00")                                 # AAA is delisted: no-trade bars at a frozen close
    for sym, px, start in (("BTCUSDT", btc, T0), ("AAAUSDT", aaa, aaa_start)):
        k = bars(px, start)
        if sym == "AAAUSDT":
            gone = k.t >= dead
            k.loc[gone, "count"] = 0.0
            k.loc[gone, ["open", "high", "low", "close"]] = k.close[~gone].iloc[-1]
        write(root, f"klines_1h/{sym}.parquet", k)
        write(root, f"markPriceKlines_1h/{sym}.parquet", k.assign(close=k.close * 0.999, high=k.high * 0.999,
                                                                   low=k.low * 0.999))
        write(root, f"premiumIndexKlines_1h/{sym}.parquet", k.assign(close=0.0001))
        ft = np.arange(start, T0 + n * H, 8 * H) + 2              # Binance stamps 2 ms after the hour
        write(root, f"fundingRate/{sym}.parquet",
              pd.DataFrame({"t": ft, "interval_h": 8.0, "rate": fb(ft, np.full(len(ft), 0.0001))}))
    g = bars(aaa * 1.002, aaa_start)[["t", "open", "high", "low", "close"]].assign(vol_contracts=10.0)
    write(root, "gate_hist/open/candlesticks_1h/AAA_USDT.parquet", g)
    gt = np.arange(aaa_start, T0 + n * H, 8 * H)
    write(root, "gate_hist/open/funding_applies/AAA_USDT.parquet",
          pd.DataFrame({"t": gt, "rate": fb(gt, np.full(len(gt), 0.0003))}))
    for d in ("candlesticks_1h", "funding_applies"):
        (Path(root) / "gate_hist/open" / d).mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"name": ["AAA_USDT"], "route": ["open"], "binance_perp": ["AAAUSDT"], "quanto_multiplier": [1],
                  "live": [True], "candlesticks_1h_months": [2], "funding_applies_months": [2]}
                 ).to_csv(Path(root) / "gate_hist/contracts.csv", index=False)
    kd = pd.DataFrame({"t": np.arange(aaa_start, T0 + n * H - DAY + 1, DAY)})
    kd = kd.assign(open=6.0, high=6.0, low=6.0, close=6.0, volume=1.0, turnover=6.0)
    write(root, "kucoin_hist/open/candles_1d/AAAUSDTM.parquet", kd)
    write(root, "kucoin_hist/open/funding/AAAUSDTM.parquet", pd.DataFrame({"t": kd.t + 8 * H, "rate": 0.001}))
    pd.DataFrame({"symbol": ["AAAUSDTM"], "base": ["AAA"], "route": ["open"]}
                 ).to_csv(Path(root) / "kucoin_hist/contracts.csv", index=False)
    write(root, "macro/fng.parquet", pd.DataFrame({"t": [ms("2021-01-05"), ms("2021-01-20")], "value": [40.0, 70.0]}))
    return btc, aaa


class TimingTest(unittest.TestCase):
    def test_rows_and_settlements(self):
        x = ms("2021-03-01") // DAY
        self.assertEqual(daily.row_of(ms("2021-03-01 23:00") + H), x + 1)          # last hour bar of day x
        self.assertEqual(daily.row_of(ms("2021-03-01 22:00") + H), x + 1)
        self.assertEqual(daily.settle_row(ms("2021-03-02") + 2), x + 1)              # 00:00 settles the day before
        self.assertEqual(daily.settle_row(ms("2021-03-01 08:00")), x + 1)
        self.assertEqual(daily.row_of(ms("2021-03-01 15:00") + DAY), x + 2)          # Bithumb's KST candle
        self.assertEqual(daily.row_of(ms("2021-03-01") + DAY), x + 1)                # a UTC daily candle

    def test_columns_are_unique_and_documented(self):
        names = [c for c, *_ in daily.columns()]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("gate_gap", names)
        self.assertNotIn("kraken_qvol", names)
        self.assertTrue(all(kind in ("pit", "vintage") for *_, kind in daily.columns()))


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.btc, cls.aaa = fixture(cls.tmp.name)
        cls.df, cls.mk, _ = daily.build(cls.tmp.name, end="2021-02-15", workers=2, log=lambda *a: None)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def row(self, perp, day):
        r = self.df[(self.df.perp == perp) & (self.df.day == pd.Timestamp(day).date())]
        self.assertEqual(len(r), 1)
        return r.iloc[0]

    def test_no_reserved_row_or_value(self):
        self.assertEqual(self.df.day.min(), pd.Timestamp("2021-01-02").date())
        self.assertEqual(self.df.day.max(), pd.Timestamp("2021-02-15").date())
        first = self.row("BTCUSDT", "2021-01-02")
        self.assertTrue(np.isnan(first.ret))                     # would need the 2020-12-31 close
        self.assertTrue(np.isnan(first.age_days))                 # BTC traded at the start: age unknown
        with self.assertRaises(PermissionError):
            daily.build(self.tmp.name, start="2020-12-01")

    def test_binance_values_sit_on_the_next_row(self):
        r = self.row("BTCUSDT", "2021-01-20")
        i = (ms("2021-01-19 23:00") - T0) // H                    # the last bar of 2021-01-19
        self.assertAlmostEqual(r.close, self.btc[i], places=0)
        self.assertAlmostEqual(r.ret, self.btc[i] / self.btc[i - 24] - 1, places=5)
        self.assertAlmostEqual(r.fund, 0.0003, places=7)          # settlements at 08:00, 16:00 and 00:00
        self.assertEqual(r.fund_n, 3)
        self.assertEqual(r.bars, 24)
        self.assertAlmostEqual(r.mark_gap, 1 / 0.999 - 1, places=5)
        self.assertAlmostEqual(r.premium, 0.0001, places=7)

    def test_venues_and_identity(self):
        r = self.row("AAAUSDT", "2021-01-25")
        self.assertAlmostEqual(r.gate_gap, 0.002, places=4)
        self.assertAlmostEqual(r.gate_fund, 0.0009, places=7)
        self.assertAlmostEqual(r.gate_fund_gap, 0.0006, places=7)
        self.assertTrue(np.isnan(r.kucoin_gap))                   # 3x the price: another coin, masked
        self.assertTrue(np.isnan(r.kucoin_fund))
        self.assertEqual(r.n_venues, 1)
        self.assertEqual(r.age_days, 14)                          # first bar 2021-01-10, so first row 01-11
        early = self.row("AAAUSDT", "2021-01-12")                 # fewer than IDENT_MIN gap observations yet
        self.assertTrue(np.isnan(early.gate_gap))

    def test_no_trade_bars_are_not_rows(self):
        aaa = self.df[self.df.perp == "AAAUSDT"]
        self.assertEqual(aaa.day.max(), pd.Timestamp("2021-02-11").date())      # 12 live bars on 02-10
        self.assertEqual(self.row("AAAUSDT", "2021-02-11").bars, 12)
        self.assertEqual(self.df[self.df.perp == "BTCUSDT"].day.max(), pd.Timestamp("2021-02-15").date())

    def test_market_series_wait_for_their_lag(self):
        m = self.mk.set_index("day").fng
        self.assertTrue(np.isnan(m[pd.Timestamp("2021-01-05").date()]))
        self.assertEqual(m[pd.Timestamp("2021-01-06").date()], 40.0)
        self.assertEqual(m[pd.Timestamp("2021-01-20").date()], 40.0)
        self.assertEqual(m[pd.Timestamp("2021-01-21").date()], 70.0)

    def test_a_different_future_changes_no_earlier_row(self):
        cut = ms("2021-02-01 13:00")
        with tempfile.TemporaryDirectory() as tmp:
            fixture(tmp, bump_from=cut)
            other, _, _ = daily.build(tmp, end="2021-02-15", workers=2, log=lambda *a: None)
        a, b = self.df.set_index(["day", "perp"]), other.set_index(["day", "perp"])
        known = a.index.get_level_values(0) <= pd.Timestamp("2021-02-01").date()
        pd.testing.assert_frame_equal(a[known], b[known])
        self.assertFalse(a[~known].equals(b[~known]))


class LoadTest(unittest.TestCase):
    def test_load_refuses_reserved_rows(self):
        with self.assertRaises(PermissionError):
            daily.load(start="2020-06-01", root="/nonexistent")


if __name__ == "__main__":
    unittest.main()
