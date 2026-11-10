import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_stock_tugofwar as tw

HOUR = tw.HOUR


_READ_PARQUET, _READ_CSV = pd.read_parquet, pd.read_csv


def _guard(real, allowed):
    """A pandas reader that refuses every path outside the test's temporary folder."""
    def read(path, *a, **k):
        if not Path(path).resolve().is_relative_to(Path(allowed).resolve()):
            raise AssertionError(f"a synthetic test tried to read outside its temporary folder: {path}")
        return real(path, *a, **k)
    return read


def synth_bars(S, base, on_fn, id_fn, amount=1e5, t_first=None):
    """Hourly bars whose price jumps by on_fn(s) at each open proxy and by id_fn(s) at each close, flat otherwise."""
    t0 = int(S["close"].iloc[0]) - 40 * 24 * HOUR if t_first is None else t_first
    t1 = int(S["close"].iloc[-1]) + 24 * HOUR
    t = np.arange(t0, t1, HOUR, dtype=np.int64)
    logp = np.zeros(len(t))
    for s in range(len(S)):
        o, c = int(S["o+30"].iloc[s]), int(S["close"].iloc[s])
        logp[t + HOUR >= o] += on_fn(s)     # price at instant T = close of bar opening at T - 1h
        logp[t + HOUR >= c] += id_fn(s)
    close = base * np.exp(logp)
    return pd.DataFrame(dict(t=t, open=close, high=close, low=close, close=close, vol=1.0, amount=amount))


class TugOfWarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, real in (("read_parquet", _READ_PARQUET), ("read_csv", _READ_CSV)):
            p = mock.patch(f"pandas.{name}", _guard(real, self.tmp.name))
            p.start()
            self.addCleanup(p.stop)

    def test_guard_refuses_real_data(self):
        with self.assertRaises(AssertionError):
            pd.read_parquet(tw.ROOT / "data" / "mexc_tradfi" / "klines_1h" / "AAPLSTOCK_USDT.parquet")

    def test_loaders_on_a_temporary_root(self):
        root = Path(self.tmp.name)
        S = tw.sessions("2026-03-02", "2026-05-29")
        run = root / "data" / "mexc_tradfi" / "runs" / "1792671203016652636"
        run.mkdir(parents=True)
        (root / tw.LANE.relative_to(tw.ROOT)).mkdir(parents=True)
        syms = ["AAASTOCK_USDT", "BBBSTOCK_USDT"]
        (run / "contracts.json").write_text(json.dumps(
            [dict(symbol=s, base=s[:-5], type=2, state=0, taker=0.0002, maker=0.0) for s in syms]))
        (run / "manifest.json").write_text(json.dumps(dict(end_exclusive=int(S.close.iloc[-1]) + tw.DAY)))
        for sub in ("klines_1h", "index_price_1h", "funding"):
            (root / "data" / "mexc_tradfi" / sub).mkdir()
        for j, s in enumerate(syms):
            k = synth_bars(S, 10.0 + j, lambda d: 0.001, lambda d: 0.0)
            # index moves only in New York hours for the first name, only in Tokyo hours for the second
            tz = "America/New_York" if j == 0 else "Asia/Tokyo"
            hh = pd.to_datetime(k.t.values, unit="ms", utc=True).tz_convert(tz).hour
            step = np.where((hh >= 9) & (hh < 15), 0.002, 0.0) * np.where(np.arange(len(k)) % 2, 1, -1)
            ix = k.assign(close=10 * np.exp(np.cumsum(step)))
            k.to_parquet(root / "data" / "mexc_tradfi" / "klines_1h" / f"{s}.parquet")
            ix.to_parquet(root / "data" / "mexc_tradfi" / "index_price_1h" / f"{s}.parquet")
            pd.DataFrame(dict(t=k.t.values[::8], rate=1e-5, cycle_h=8)).to_parquet(
                root / "data" / "mexc_tradfi" / "funding" / f"{s}.parquet")
        tick = root / "data" / "recorders" / "mexc_ticker" / "2026-11-01"
        tick.mkdir(parents=True)
        pd.DataFrame(dict(symbol=syms, t_bid1=[9.99, 10.9], t_ask1=[10.01, 11.1])).to_parquet(tick / "01.parquet")
        late = root / "data" / "recorders" / "mexc_ticker" / "2026-11-20"
        late.mkdir()
        pd.DataFrame(dict(symbol=syms, t_bid1=[1.0, 1.0], t_ask1=[2.0, 2.0])).to_parquet(late / "01.parquet")
        got_syms, fee, S2 = tw.frame(root)
        self.assertEqual(got_syms, syms)
        panel, cls = tw.load(root, got_syms, S2)
        self.assertEqual(sorted(panel), ["AAASTOCK_USDT"])          # the Tokyo-hours name is not US
        self.assertFalse(cls["BBBSTOCK_USDT"]["us"])
        hs, n_rec, _ = tw.half_spreads(root, ["AAASTOCK_USDT"])
        self.assertAlmostEqual(hs["AAASTOCK_USDT"], 0.02 / 10.0 / 2)  # the day after TICKER_LAST is ignored
        self.assertEqual(n_rec, 1)
        self.assertEqual(len(tw.write_manifest(root)), 2 + 3 * 2 + 1)
        self.assertEqual(tw.check_manifest(root), 9)
        (root / "data" / "mexc_tradfi" / "funding" / "AAASTOCK_USDT.parquet").write_bytes(b"changed")
        with self.assertRaises(SystemExit):
            tw.check_manifest(root)

    def test_sessions_dst_holidays_early_close(self):
        S = tw.sessions("2025-11-24", "2025-12-02")
        days = S.day.tolist()
        self.assertNotIn("2025-11-27", days)            # Thanksgiving
        self.assertNotIn("2025-11-28", days)            # early close: not a session
        i = days.index("2025-12-01")
        self.assertFalse(S.prev_ok.iloc[i])             # its overnight spans the early close
        self.assertTrue(S.prev_ok.iloc[days.index("2025-12-02")])
        # 16:00 New York is 21:00 UTC in winter and 20:00 UTC in summer
        self.assertEqual(pd.to_datetime(S.close.iloc[0], unit="ms").hour, 21)
        S2 = tw.sessions("2026-07-06", "2026-07-07")
        self.assertEqual(pd.to_datetime(S2.close.iloc[0], unit="ms").hour, 20)
        self.assertEqual(pd.to_datetime(S2["o+30"].iloc[0], unit="ms").hour, 14)

    def test_price_at_is_exact_bar(self):
        t = np.array([0, HOUR, 3 * HOUR], np.int64)
        c = np.array([1.0, 2.0, 4.0])
        out = tw.price_at(t, c, [HOUR, 2 * HOUR, 3 * HOUR, 4 * HOUR])
        self.assertEqual(out[0], 1.0)
        self.assertEqual(out[1], 2.0)
        self.assertTrue(np.isnan(out[2]))               # the bar opening at 2h is missing
        self.assertEqual(out[3], 4.0)

    def test_funding_window_is_open_closed(self):
        ft = np.array([10, 20, 30], np.int64)
        fr = np.array([0.1, 0.2, 0.4])
        self.assertAlmostEqual(tw.funding_between(ft, fr, 10, 30), 0.6)    # (10, 30]
        self.assertAlmostEqual(tw.funding_between(ft, fr, 0, 9), 0.0)

    def test_overnight_persistence_is_found_and_costed(self):
        S = tw.sessions("2026-03-02", "2026-06-30")
        rng = np.random.default_rng(1)
        n = 20
        drift = np.linspace(-0.004, 0.004, n)           # a persistent overnight drift per name
        panel, fee, hs = {}, {}, {}
        empty_f = pd.DataFrame(dict(t=np.array([], np.int64), rate=np.array([], float)))
        for j in range(n):
            noise_on = rng.normal(0, 0.002, len(S))
            k = synth_bars(S, 100.0, lambda s, j=j: drift[j] + noise_on[s], lambda s, j=j: -drift[j] / 2)
            panel[f"S{j}"] = tw.symbol_arrays(k, empty_f, S)
            fee[f"S{j}"], hs[f"S{j}"] = 2e-4, 1e-4
        fr = tw.evaluate(panel, S, fee, hs, 20, "o+30", mult=1)
        tr = fr[fr.b1_net.notna()]
        self.assertGreater(len(tr), 50)
        self.assertGreater(tr.ic_on.mean(), 0.5)        # persistence
        self.assertLess(tr.ic_id.mean(), -0.5)          # intraday reversal
        self.assertGreater(tr.b1_gross.mean(), 0)
        # net = gross minus two legs' round trips of 2 x (2 + 1) bp
        self.assertAlmostEqual((tr.b1_gross - tr.b1_net).mean(), 2 * 2 * 3e-4, places=10)
        self.assertGreater(tr.b2_gross.mean(), 0)
        self.assertAlmostEqual((tr.b3_net - tr.b1_net - tr.b2_net).abs().max(), 0.0, places=12)
        # 2x costs double the cost wedge
        fr2 = tw.evaluate(panel, S, fee, hs, 20, "o+30", mult=2)
        self.assertAlmostEqual((fr2.b1_gross - fr2.b1_net).dropna().mean(), 2 * 2 * 6e-4, places=10)
        # API fee override replaces the per-name fee
        fa = tw.evaluate(panel, S, fee, hs, 20, "o+30", mult=1, fee_override=8e-4)
        self.assertAlmostEqual((fa.b1_gross - fa.b1_net).dropna().mean(), 2 * 2 * 9e-4, places=10)

    def test_no_lookahead_in_signal(self):
        # a name whose overnight return is large only on the next session must not be ranked by it
        S = tw.sessions("2026-03-02", "2026-05-29")
        empty_f = pd.DataFrame(dict(t=np.array([], np.int64), rate=np.array([], float)))
        panel, zs = {}, {}
        rng = np.random.default_rng(2)
        for j in range(16):
            z = rng.normal(0, 0.003, len(S))
            zs[j] = z
            k = synth_bars(S, 50.0, lambda s, z=z: z[s], lambda s: 0.0)
            panel[f"S{j}"] = tw.symbol_arrays(k, empty_f, S)
        on = panel["S0"]["on_o+30"]
        ok = S.prev_ok.values
        np.testing.assert_allclose(on[ok], zs[0][ok], atol=1e-12)          # the planted overnight jump, exactly
        np.testing.assert_allclose(panel["S0"]["id_o+30"], 0.0, atol=1e-12)
        sig = tw.signal(on, 20)
        d = 40
        self.assertAlmostEqual(sig[d], np.nanmean(on[d - 19:d + 1]))
        # the future return at d+1 is not in the signal at d
        on2 = on.copy()
        on2[d + 1] = 5.0
        self.assertAlmostEqual(tw.signal(on2, 20)[d], sig[d])
        fee = {s: 2e-4 for s in panel}
        hs = {s: 1e-4 for s in panel}
        fr = tw.evaluate(panel, S, fee, hs, 20, "o+30")
        tr = fr[fr.b1_net.notna()]
        self.assertLess(abs(tr.ic_on.mean()), 0.15)     # pure noise: no persistence

    def test_funding_sign_long_pays_short_receives(self):
        S = tw.sessions("2026-03-02", "2026-05-29")
        panel, fee, hs = {}, {}, {}
        for j in range(15):
            k = synth_bars(S, 10.0, lambda s, j=j: 1e-4 * (j - 7), lambda s: 0.0)
            # a funding print every 8 h at 0.01%
            ft = np.arange(int(k.t.min()), int(k.t.max()), 8 * HOUR, dtype=np.int64)
            f = pd.DataFrame(dict(t=ft, rate=np.full(len(ft), 1e-4)))
            panel[f"S{j}"] = tw.symbol_arrays(k, f, S)
            fee[f"S{j}"], hs[f"S{j}"] = 0.0, 0.0
        fr = tw.evaluate(panel, S, fee, hs, 20, "o+30")
        tr = fr[fr.b1_net.notna()]
        # equal funding on both legs cancels in a long-short book
        self.assertAlmostEqual((tr.b1_gross - tr.b1_net).abs().max(), 0.0, places=12)

    def test_listing_age_and_min_names(self):
        S = tw.sessions("2026-03-02", "2026-05-29")
        empty_f = pd.DataFrame(dict(t=np.array([], np.int64), rate=np.array([], float)))
        panel = {}
        for j in range(14):                              # fewer than MIN_NAMES
            k = synth_bars(S, 10.0, lambda s: 0.001, lambda s: 0.0)
            panel[f"S{j}"] = tw.symbol_arrays(k, empty_f, S)
        fr = tw.evaluate(panel, S, {s: 0 for s in panel}, {s: 0 for s in panel}, 20, "o+30")
        self.assertNotIn("b1_net", fr.columns)
        late = synth_bars(S, 10.0, lambda s: 0.001, lambda s: 0.0, t_first=int(S.close.iloc[-1]) - 10 * 24 * HOUR)
        self.assertGreater(tw.symbol_arrays(late, empty_f, S)["first"], int(S.close.iloc[0]))

    def test_us_classifier_is_point_in_time(self):
        t = np.arange(pd.Timestamp("2026-03-02", tz="UTC").value // 10**6,
                      pd.Timestamp("2026-05-28", tz="UTC").value // 10**6, HOUR, dtype=np.int64)
        ny_h = pd.to_datetime(t, unit="ms", utc=True).tz_convert("America/New_York").hour
        tk_h = pd.to_datetime(t, unit="ms", utc=True).tz_convert("Asia/Tokyo").hour
        sign = np.where(np.arange(len(t)) % 2, 1, -1)
        us = np.where((ny_h >= 9) & (ny_h < 16), 0.002, 0.0002)
        asia = np.where((tk_h >= 9) & (tk_h < 15), 0.002, 0.0002)
        self.assertTrue(tw.classify(pd.DataFrame(dict(t=t, close=100 * np.exp(np.cumsum(sign * us)))), t[0])["us"])
        self.assertFalse(tw.classify(pd.DataFrame(dict(t=t, close=100 * np.exp(np.cumsum(sign * asia)))), t[0])["us"])
        # moves after the first LIST_DAYS days do not change the class
        cut = t[0] + tw.LIST_DAYS * tw.DAY
        mixed = np.where(t < cut, asia, us * 50)
        self.assertFalse(tw.classify(pd.DataFrame(dict(t=t, close=100 * np.exp(np.cumsum(sign * mixed)))), t[0])["us"])

    def test_stock_candidates(self):
        c = [dict(symbol="AAPLSTOCK_USDT", base="AAPLSTOCK", type=2, state=0),
             dict(symbol="QQQSTOCK_USDT", base="QQQSTOCK", type=2, state=0),
             dict(symbol="NVIDIA_USDT", base="NVIDIA", type=2, state=0),
             dict(symbol="SPY_USDT", base="SPY", type=2, state=0),
             dict(symbol="BTC_USDT", base="BTC", type=1, state=0)]
        self.assertEqual(tw.stock_candidates(c), ["AAPLSTOCK_USDT", "NVIDIA_USDT"])

    def test_bootstrap_nw_and_verdict(self):
        rng = np.random.default_rng(0)
        ci = tw.block_boot(np.ones(200), np.arange(200) // 5, rng)
        self.assertEqual((ci["mean"], ci["lo"], ci["hi"], ci["p_le0"]), (1.0, 1.0, 1.0, 0.0))
        self.assertEqual(tw.verdict(np.ones(200), np.ones(200), ci), "PASS")
        self.assertEqual(tw.verdict(np.ones(100), np.ones(100), ci), "INCONCLUSIVE")
        self.assertEqual(tw.verdict(np.ones(200), -np.ones(200), ci), "NULL")          # 2x negative
        halves = np.r_[-np.ones(100), 3 * np.ones(100)]
        self.assertEqual(tw.verdict(halves, halves, dict(ci, lo=0.1)), "NULL")         # first half negative
        self.assertEqual(tw.verdict(np.ones(200), np.ones(200), dict(ci, lo=-0.1)), "NULL")
        st = tw.nw_t(np.r_[np.ones(50), -np.ones(50)] + 0.1)
        self.assertAlmostEqual(st["mean"], 0.1)
        self.assertGreater(st["t"], 0)

    def test_trial_count(self):
        self.assertEqual(tw.TRIALS, 20)
        self.assertEqual(tw.PRIMARY, ("B1", 20, "o+30"))


if __name__ == "__main__":
    unittest.main()
