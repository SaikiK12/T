"""R475 hip3stock_v1: trailing funding, slots, costs, liquidation, split guard and verdict on synthetic markets."""
import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_hip3stock as hs  # noqa: E402

H, D = hs.HOUR, hs.DAY


def world(rate=0.30, lo="2025-11-03", hi="2026-11-13", px=100.0, perp_mult=1.0):
    """A stock at a flat price, its perp (4-hour candles around the clock) and hourly funding at an annual rate."""
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range(lo, hi)]
    stock = pd.DataFrame({"date": days, "close": px, "adjclose": px})
    cal = pd.date_range(lo, hi, freq="4h", tz="UTC")
    opens = cal.as_unit("ms").asi8.astype(np.int64)
    candles = pd.DataFrame({"open_ms": opens, "open": px * perp_mult, "high": px * perp_mult, "low": px * perp_mult,
                            "close": px * perp_mult, "volume": 1000.0})
    hours = np.arange(opens[0], opens[-1] + 4 * H, H, dtype=np.int64)
    r = rate(hours) if callable(rate) else np.full(len(hours), rate)
    funding = pd.DataFrame({"time": hours + 40, "fundingRate": np.asarray(r) / 8760, "premium": 0.0})
    return stock, candles, funding


def market(t="AAA", **kw):
    s, c, f = world(**kw)
    return hs.Market(t, s, c, f, hs.PERP_BP_GROWTH, 10)


def bill(level=4.0):
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2025-10-01", "2026-11-13")]
    return pd.Series(level, index=days)


class MarketTest(unittest.TestCase):
    def test_trailing_is_the_annualized_mean_and_needs_age(self):
        mk = market(rate=0.25)
        t = hs.close_ms("2026-01-16")
        self.assertAlmostEqual(mk.trailing(t), 25.0, places=6)
        self.assertTrue(math.isnan(mk.trailing(hs.close_ms("2025-11-20"))))

    def test_identity_rejects_a_ticker_collision(self):
        self.assertTrue(market().identity_ok())
        self.assertFalse(market(perp_mult=40.0).identity_ok())
        s, c, f = world()
        rng = np.random.default_rng(0)
        s["close"] = s["adjclose"] = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, len(s))))
        days = (pd.to_datetime(s["date"]).dt.tz_localize("UTC").dt.as_unit("ms").astype("int64") + 20 * H).to_numpy()
        idx = np.clip(np.searchsorted(days, c["open_ms"].to_numpy(), side="right") - 1, 0, None)
        c[["open", "high", "low", "close"]] = np.repeat(s["close"].to_numpy()[idx][:, None], 4, axis=1)
        self.assertTrue(hs.Market("AAA", s, c, f, hs.PERP_BP_GROWTH, 10).identity_ok())
        noise = c.copy()
        lvl = float(s["close"].iloc[-60:].median())
        noise[["open", "high", "low", "close"]] = np.repeat(lvl * np.exp(rng.normal(0, 0.003, (len(c), 1))), 4, axis=1)
        self.assertFalse(hs.Market("AAA", s, noise, f, hs.PERP_BP_GROWTH, 10).identity_ok())

    def test_marks_are_the_20utc_candle_open_and_notional_sums_a_day(self):
        s, c, f = world()
        c["open"] = 100.0 + (c["open_ms"] // H % 24)
        mk = hs.Market("AAA", s, c, f, hs.PERP_BP_GROWTH, 10)
        self.assertEqual(float(mk.perp.iloc[5]), 120.0)
        self.assertAlmostEqual(float(mk.ntl.iloc[5]), 6 * 1000 * 100.0)


class BookTest(unittest.TestCase):
    def run_book(self, markets, params=hs.BASE, end="2026-03-27", lvl=4.0):
        return hs.book(markets, bill(lvl), params, "2025-11-03", end)

    def test_flat_prices_earn_funding_less_costs_and_bill(self):
        r = 0.30
        daily, trades = self.run_book({"AAA": market(rate=r)})
        self.assertEqual(daily["slots"].max(), 1)
        cap = 1 / hs.BASE["slots"]
        v = cap / (1 + hs.M)
        opened = trades["opened"].iloc[0]
        held = daily[daily["date"] > opened]
        days = (pd.Timestamp("2026-03-27") - pd.Timestamp(opened)).days
        self.assertAlmostEqual(held["fund"].sum(), r / 8760 * 24 * days * v, delta=v * r / 8760 * 30)
        self.assertAlmostEqual(daily["price"].abs().sum(), 0.0, places=12)
        entry = (hs.STOCK_BP * v + hs.PERP_BP_GROWTH * v + hs.XFER_BP * (cap - v)) / 1e4
        self.assertGreater(daily["cost"].sum(), 2 * entry * 0.99)
        self.assertGreater(daily["excess"].sum(), 0)
        self.assertEqual(trades["why"].tolist(), ["end"])
        self.assertAlmostEqual(daily["div"].abs().sum(), 0.0, places=12)
        self.assertAlmostEqual(trades["ntl_usd"].iloc[0], 6 * 1000 * 100.0)

    def test_dividends_reach_the_book_through_adjclose(self):
        s, c, f = world(rate=0.30)
        ex = s["date"] >= "2026-02-17"
        s.loc[ex, "adjclose"] = 101.0
        mk = hs.Market("AAA", s, c, f, hs.PERP_BP_GROWTH, 10)
        daily, _ = self.run_book({"AAA": mk})
        cap = 1 / hs.BASE["slots"]
        v = cap / (1 + hs.M)
        self.assertAlmostEqual(daily["div"].sum(), 0.01 * v, delta=1e-4 * v)
        self.assertAlmostEqual(daily["price"].sum(), 0.01 * v, delta=1e-4 * v)

    def test_low_funding_never_enters_and_a_drop_exits(self):
        daily, trades = self.run_book({"LOW": market(rate=0.05)})
        self.assertEqual(daily["slots"].max(), 0)
        cut = hs.close_ms("2026-01-30")
        mk = market(rate=lambda h: np.where(h < cut, 0.30, 0.0))
        daily, trades = self.run_book({"DROP": mk})
        self.assertEqual(trades["why"].iloc[0], "exit")
        self.assertLess(trades["closed"].iloc[0], "2026-03-01")

    def test_best_funding_fills_limited_slots(self):
        mks = {f"S{i}": market(t=f"S{i}", rate=0.15 + 0.02 * i) for i in range(4)}
        daily, trades = self.run_book(mks, {**hs.BASE, "slots": 2})
        self.assertEqual(sorted(trades["ticker"]), ["S2", "S3"])

    def test_spike_liquidates_and_loses_the_margin(self):
        s, c, f = world(rate=0.30)
        spike = hs.day_ms("2026-02-10")
        c.loc[c["open_ms"] == spike, "high"] = 160.0
        mk = hs.Market("AAA", s, c, f, hs.PERP_BP_GROWTH, 10)
        daily, trades = self.run_book({"AAA": mk})
        self.assertEqual(int(daily["liquidations"].sum()), 1)
        self.assertEqual(trades["why"].iloc[0], "liquidated")
        cap = 1 / hs.BASE["slots"]
        loss = daily.loc[daily["liquidations"] == 1, "price"].iloc[0]
        self.assertLess(loss, -0.9 * cap * hs.M / (1 + hs.M))

    def test_a_delisted_perp_is_closed_at_its_last_mark(self):
        s, c, f = world(rate=0.30)
        c = c[c["open_ms"] < hs.day_ms("2026-02-20")]
        f = f[f["time"] < hs.day_ms("2026-02-20")]
        mk = hs.Market("AAA", s, c, f, hs.PERP_BP_GROWTH, 10)
        daily, trades = self.run_book({"AAA": mk, "BBB": market(t="BBB", rate=0.01)})
        self.assertEqual(trades["why"].tolist(), ["gone"])
        self.assertEqual(trades["closed"].iloc[0], "2026-02-19")
        self.assertEqual(int(daily["slots"].iloc[-1]), 0)

    def test_a_split_jump_is_flagged_not_booked(self):
        s, c, f = world(rate=0.30)
        cut = hs.day_ms("2026-02-10")
        c.loc[c["open_ms"] >= cut, ["open", "high", "low", "close"]] = 50.0
        mk = hs.Market("AAA", s, c, f, hs.PERP_BP_GROWTH, 10)
        daily, trades = self.run_book({"AAA": mk})
        self.assertGreaterEqual(int(daily["split_flags"].sum()), 1)
        self.assertAlmostEqual(daily["price"].abs().sum(), 0.0, places=12)
        self.assertEqual(int(daily["liquidations"].sum()), 0)


class VerdictTest(unittest.TestCase):
    def a(self, ex, t, ex2, active=30):
        return {"active_weeks": active, "weeks": 33, "ann_excess_pts": ex, "nw_t": t, "ann_excess_2x_pts": ex2,
                "ann_excess_3x_pts": ex2 - 1, "ann_funding_pts": 8, "ann_price_pts": 0, "ann_cost_pts": 1,
                "mean_slots": 4.0}

    def test_cases(self):
        self.assertEqual(hs.verdict(self.a(3.0, 2.5, 2.0))[0], "PASS")
        self.assertEqual(hs.verdict(self.a(3.0, 1.5, 2.0))[0], "PARTIAL")
        self.assertEqual(hs.verdict(self.a(1.0, 3.0, 0.5))[0], "PARTIAL")
        self.assertEqual(hs.verdict(self.a(3.0, 2.5, -0.1))[0], "PARTIAL")
        self.assertEqual(hs.verdict(self.a(-0.5, -1, -2))[0], "NULL")
        self.assertEqual(hs.verdict(self.a(5, 5, 4, active=19))[0], "INCONCLUSIVE")


class RunTest(unittest.TestCase):
    def test_run_writes_both_samples_and_drops_collisions(self):
        with tempfile.TemporaryDirectory() as d:
            data, lane = Path(d) / "data", Path(d) / "lane"
            (data / "xyz").mkdir(parents=True)
            (data / "yahoo").mkdir(parents=True)
            rows = []
            for i, (t, rate, mult) in enumerate([("AAA", 0.30, 1.0), ("BBB", 0.20, 1.0), ("CCC", 0.02, 1.0),
                                                 ("GOLD", 0.40, 40.0), ("ETFX", 0.40, 1.0)]):
                s, c, f = world(rate=rate, perp_mult=mult)
                f.to_csv(data / "xyz" / f"{t}_funding.csv", index=False)
                c.to_csv(data / "xyz" / f"{t}_4h.csv", index=False)
                s.to_parquet(data / "yahoo" / f"{t}.parquet", index=False)
                rows.append({"coin": f"xyz:{t}", "ticker": t, "equity": int(t != "ETFX"), "delisted": 0,
                             "growth": "enabled" if i % 2 == 0 else "", "max_lev": 10})
            pd.DataFrame(rows).to_csv(data / "universe.csv", index=False)
            pd.DataFrame({"date": bill().index, "close": 4.0, "adjclose": 4.0}).to_parquet(
                data / "yahoo" / "IRX.parquet", index=False)
            files = {str(p.relative_to(data)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(data.rglob("*")) if p.is_file()}
            (data / "manifest.json").write_text(json.dumps({"files": files}))
            state = hs.run(lane, data, check=False)
            s = json.loads((lane / "results" / "summary.json").read_text())
            self.assertEqual(s["state"], state)
            self.assertEqual(s["markets"], ["AAA", "BBB", "CCC"])
            self.assertIn(["GOLD", "identity"], s["dropped"])
            dec = s["variants"]["decide"]
            self.assertGreater(dec["A"]["weeks"], 20)
            self.assertGreater(dec["B"]["weeks"], 10)
            self.assertGreater(dec["A"]["ann_funding_pts"], 0)
            self.assertEqual(set(s["variants"]), {"decide", "slots10", "enter20"})
            self.assertEqual(state, "PASS")


if __name__ == "__main__":
    unittest.main()
