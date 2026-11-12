"""R479 hip3carry_fwd: fee formula, marks, identity fix, capacity floor, measured costs, carry statistics, verdicts
and the read gating, on synthetic data (no market data)."""
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_hip3carry as hc  # noqa: E402
import run_hip3stock as hs  # noqa: E402

H = hs.HOUR


def hours(lo, hi, step=1):
    a, b = hs.day_ms(lo), hs.day_ms(hi)
    return np.arange(a, b, step * H, dtype=np.int64)


def candles(t, price, volume):
    p = np.broadcast_to(np.asarray(price, float), t.shape)
    return pd.DataFrame({"open_ms": t, "open": p, "high": p, "low": p, "close": p, "volume": volume})


def closes(days, price):
    p = np.broadcast_to(np.asarray(price, float), (len(days),))
    return pd.DataFrame({"date": days, "close": p, "adjclose": p})


def funding(t, rate):
    return pd.DataFrame({"time": t, "fundingRate": rate, "premium": 0.0})


def write_manifest(d):
    man = {"files": {str(p.relative_to(d)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(d.rglob("*")) if p.is_file() and p.name != "manifest.json"}}
    (d / "manifest.json").write_text(json.dumps(man))


def fake_fetch(end, out):
    """Three stock listings (one carries, one does not, one is too thin) and one twin pair."""
    out = Path(out)
    st, tw = out / "stocks", out / "twin"
    for sub in (st / "xyz", st / "yahoo", tw / "xyz", tw / "yahoo"):
        sub.mkdir(parents=True, exist_ok=True)
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-09-01", "2027-02-12")]
    h1, h4 = hours("2026-09-01", "2027-02-14"), hours("2026-09-01", "2027-02-14", 4)
    rows = []
    for tick, stock, rate, vol in (("xyz_AAA", "AAA", 2e-5, 200.0), ("para_BBB", "BBB", 1e-6, 200.0),
                                   ("io_CCC", "CCC", 3e-5, 1.0)):
        funding(h1, rate).to_csv(st / "xyz" / f"{tick}_funding.csv", index=False)
        candles(h1, 100.0, vol).to_csv(st / "xyz" / f"{tick}_1h.csv", index=False)
        closes(days, 100.0).to_parquet(st / "yahoo" / f"{stock}.parquet", index=False)
        rows.append({"coin": tick.replace("_", ":"), "ticker": tick, "dex": tick.split("_")[0], "stock": stock,
                     "equity": 1, "delisted": 0, "growth": "enabled", "fee_scale": 1.0, "max_lev": 10})
    pd.DataFrame(rows).to_csv(st / "universe.csv", index=False)
    closes(days, 4.0).to_parquet(st / "yahoo" / "IRX.parquet", index=False)
    funding(h1, 2e-5).to_csv(tw / "xyz" / "GOLD_funding.csv", index=False)
    px = 50 * np.exp(np.cumsum(np.random.default_rng(7).normal(0, 0.005, len(days))))   # moves, so returns correlate
    p4 = np.full(len(h4), px[0])
    with hc.xt.london_marks():
        for d, x in zip(days, px):
            p4[h4 >= hs.mark_ms(d)] = x
    candles(h4, p4, 1e4).to_csv(tw / "xyz" / "GOLD_4h.csv", index=False)
    closes(days, px).to_parquet(tw / "yahoo" / "GOLD.parquet", index=False)
    closes(days, 4.0).to_parquet(tw / "yahoo" / "IRX.parquet", index=False)
    pd.DataFrame([{"coin": "xyz:GOLD", "ticker": "GOLD", "twin": "IGLN.L", "twin_currency": "USD",
                   "twin_exchange": "LSE", "equity": 1, "delisted": 0, "growth": "", "max_lev": 25,
                   "first_funding": "2026-09-01"}]).to_csv(tw / "universe.csv", index=False)
    write_manifest(out)


def fake_books(d):
    for sub, coin, buy, sell in (("", "xyz:AAA", 10.0, 6.0), ("hip3", "para:BBB", np.nan, np.nan)):
        b = Path(d) / sub
        (b / "books").mkdir(parents=True, exist_ok=True)
        (b / "markets").mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"dex": coin.split(":")[0], "coin": coin, "ts": [1, 2], "buy_5000_bp": buy,
                      "sell_5000_bp": sell}).to_csv(b / "books" / "2026-12-01.csv", index=False)
        pd.DataFrame({"dex": [coin.split(":")[0]], "coin": [coin], "day": ["2026-12-01"], "growthMode": ["enabled"],
                      "deployerFeeScale": [1.0]}).to_csv(b / "markets" / "2026-12-01.csv", index=False)
        pd.DataFrame({"dex": "xyz", "coin": coin, "ts": [3], "buy_5000_bp": 99.0,
                      "sell_5000_bp": 99.0}).to_csv(b / "books" / "2026-11-01.csv", index=False)   # before START


class FeeMarkTest(unittest.TestCase):
    def test_fee_formula_matches_r453_and_r475(self):
        self.assertAlmostEqual(hc.taker_fee_bp("enabled", 1.0) + hc.SLIP_BP, hs.PERP_BP_GROWTH)
        self.assertAlmostEqual(hc.taker_fee_bp("", 1.0) + hc.SLIP_BP, hs.PERP_BP_FULL)
        self.assertAlmostEqual(hc.taker_fee_bp("enabled", 0.5), 0.675)
        self.assertAlmostEqual(hc.taker_fee_bp("", float("nan")), 9.0)

    def test_new_york_marks_are_patched_and_restored(self):
        with hc.ny_marks():
            winter = datetime.fromtimestamp(hs.mark_ms("2026-12-01") / 1000, timezone.utc)
            summer = datetime.fromtimestamp(hs.mark_ms("2027-06-01") / 1000, timezone.utc)
        self.assertEqual((winter.hour, summer.hour), (21, 20))
        self.assertEqual(datetime.fromtimestamp(hs.mark_ms("2026-12-01") / 1000, timezone.utc).hour, 20)


class MarketTest(unittest.TestCase):
    def market(self, n_days, volume, cls):
        rng = np.random.default_rng(1)
        days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-11-02", periods=n_days)]
        px = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))
        t = hours("2026-10-01", "2027-01-31")
        p = np.full(len(t), np.nan)
        with hc.ny_marks():
            for d, x in zip(days, px):
                p[t >= hs.mark_ms(d)] = x
            p[np.isnan(p)] = px[0]
            mk = cls("xyz_T", closes(days, px), candles(t, p, volume), funding(t, 2e-5), 2.9, 10)
        return mk

    def test_identity_drops_the_nan(self):
        frozen, fixed = self.market(30, 200.0, hs.Market), self.market(30, 200.0, hc.StockMarket)
        self.assertFalse(frozen.identity_ok())        # R475's check: NaN with fewer than 60 marks
        self.assertTrue(fixed.identity_ok())

    def test_capacity_floor(self):
        with hc.ny_marks():
            liquid, thin = self.market(40, 200.0, hc.StockMarket), self.market(40, 1.0, hc.StockMarket)
            t = hs.mark_ms(liquid.days[-1])
            self.assertTrue(np.isfinite(liquid.trailing(t)))
            self.assertAlmostEqual(liquid.trailing(t), hs.Market.trailing(liquid, t))
            self.assertTrue(np.isnan(thin.trailing(t)))


class MeasuredTest(unittest.TestCase):
    def test_measured_costs_by_ticker_and_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_books(tmp)
            m = hc.measured(tmp, hc.START, "2027-02-12")
        self.assertEqual(m["xyz_AAA"], (0.9, 8.0, 2))
        self.assertEqual(m["AAA"], (0.9, 8.0, 2))                      # the bare xyz name, for the twin book
        self.assertEqual(m["para_BBB"], (0.9, hc.THIN_BP, 2))
        self.assertEqual(hc.measured(None, hc.START, "2027-02-12"), {})


class StatsVerdictTest(unittest.TestCase):
    def test_carry_and_total(self):
        wk = pd.DataFrame({"wk": ["2026-W48", "2026-W49", "2026-W50"], "fund": [0.002, 0.003, 0.001],
                           "price": [0.01, -0.02, 0.0], "div": [0.0, 0.001, 0.0], "cost": [0.0005, 0.0, 0.0],
                           "bill": [0.0003, 0.0003, 0.0003], "liquidations": 0, "split_flags": 0, "resplits": 0,
                           "last": ["2026-11-27", "2026-12-04", "2026-12-11"], "slots": [1.0, 1.0, 1.0]})
        wk["excess"] = wk["fund"] + wk["price"] - wk["cost"] - wk["bill"]
        st = hc.carry_stats(wk, pd.DataFrame(columns=["ticker", "opened", "closed", "why", "ntl_usd"]))
        carry = (wk["fund"] + 0.85 * wk["div"] - wk["cost"] - wk["bill"]).mean() * 5200
        total = (wk["excess"] - 0.15 * wk["div"]).mean() * 5200
        self.assertAlmostEqual(st["carry_pts"], carry)
        self.assertAlmostEqual(st["total_pts"], total)
        self.assertAlmostEqual(st["carry_2x_pts"], carry - wk["cost"].mean() * 5200)

    def test_verdicts(self):
        base = {"weeks": 26, "active_weeks": 20, "carry_pts": 4.0, "carry_t": 2.5, "carry_2x_pts": 3.0,
                "total_pts": 1.0, "total_t": 0.3, "mean_slots": 2.0, "trades": 6, "liquidations": 0}
        self.assertEqual(hc.verdict("final", base, {"total_pts": 0.5})[0], "PASS")
        self.assertEqual(hc.verdict("final", base, {"total_pts": -0.5})[0], "PARTIAL")
        self.assertEqual(hc.verdict("final", {**base, "total_pts": -1.0}, {"total_pts": 1.0})[0], "PARTIAL")
        self.assertEqual(hc.verdict("final", {**base, "carry_t": 1.9}, {"total_pts": 1.0})[0], "PARTIAL")
        self.assertEqual(hc.verdict("final", {**base, "carry_pts": -0.1}, {"total_pts": 1.0})[0], "NULL")
        self.assertEqual(hc.verdict("final", {**base, "active_weeks": 12}, {"total_pts": 1.0})[0], "INCONCLUSIVE")
        self.assertEqual(hc.verdict("futility", {**base, "carry_pts": -0.1}, {})[0], "NULL")
        self.assertEqual(hc.verdict("futility", {**base, "carry_pts": 0.0}, {})[0], "CONTINUE")
        self.assertEqual(hc.verdict("futility", {**base, "active_weeks": 5}, {})[0], "INCONCLUSIVE")


class RunTest(unittest.TestCase):
    def test_reads_are_gated_and_run_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data, books = Path(tmp) / "lane", Path(tmp) / "data", Path(tmp) / "books"
            fake_books(books)
            early = datetime(2027, 2, 12, 23, tzinfo=timezone.utc)
            self.assertIsNone(hc.run("futility", lane, data, books, check=False, now=early, fetcher=fake_fetch))
            self.assertFalse((lane / "results" / "futility").exists())
            now = datetime(2027, 2, 14, tzinfo=timezone.utc)
            states = hc.run("futility", lane, data, books, check=False, now=now, fetcher=fake_fetch)
            s = json.loads((lane / "results" / "futility" / "summary.json").read_text())
            self.assertEqual(states, {"S": s["S"]["state"], "T": s["T"]["state"]})
            self.assertEqual(s["S"]["markets"], 3)
            self.assertEqual(s["S"]["trades_by_dex"], {"xyz": 1})     # BBB never carries; CCC is too thin
            self.assertEqual(s["S_nofloor"]["trades_by_dex"], {"xyz": 1, "io": 1})   # without the floor CCC enters
            a, m = s["S"]["assumed"], s["S"]["measured"]
            # one slot of 1/5: funding 2e-5 an hour on 3/4 of it, less the bill at 4% on the slot, flat prices
            self.assertAlmostEqual(a["ann_price_pts"], 0.0, places=9)
            self.assertGreater(a["carry_pts"], 1.0)
            self.assertLess(a["carry_pts"], 2.0)
            self.assertLess(m["carry_pts"], a["carry_pts"])          # measured slippage (8 bp) > assumed (2 bp)
            self.assertEqual(s["S"]["measured_share"], 2 / 3)
            self.assertEqual(s["T"]["markets"], 1)
            self.assertGreater(s["T"]["assumed"]["carry_pts"], 0)
            self.assertIn("carry_pts", s["combined"])
            self.assertIn(s["S"]["state"], ("CONTINUE", "NULL", "INCONCLUSIVE"))
            self.assertIsNone(hc.run("futility", lane, data, books, check=False, now=now, fetcher=fake_fetch))
            self.assertIsNone(hc.run("final", lane, data, books, check=False, now=now, fetcher=fake_fetch))


if __name__ == "__main__":
    unittest.main()
