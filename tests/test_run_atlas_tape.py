"""R386 atlas_tape_v1 on invented data: the event kernel against a plain loop, thresholds, cluster t, tape loading,
a planted signal that the screen must find and a null that it must not, the grid count and the verify-first rule."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_atlas_tape as at  # noqa: E402
from lab import prereg  # noqa: E402

QS = np.array(at.QS)


def naive(x, thr, tb, gate, pe, px, cl, eoff, xoff, i0, i1, shift, cl0):
    """The kernel's rule as a plain loop."""
    L = i1 - i0
    Q, K = thr.shape[1], len(eoff)
    G = np.zeros((Q, K, int(cl[i0:i1].max()) - cl0 + 1))
    N = np.zeros_like(G)
    nxt = np.full((Q, K), i0)
    for i in range(i0, i1):
        j = i - shift
        if j < i0:
            j += L
        if np.isnan(x[j]) or x[j] == 0 or not gate[j]:
            continue
        for q in range(Q):
            t = thr[tb[j], q]
            if np.isnan(t) or abs(x[j]) < t:
                break
            for k in range(K):
                if i < nxt[q, k] or i + xoff[k] >= i1:
                    continue
                p0, p1 = pe[i + eoff[k]], px[i + xoff[k]]
                if np.isfinite(p0) and np.isfinite(p1) and p0 > 0:
                    G[q, k, cl[i] - cl0] += np.sign(x[j]) * (p1 / p0 - 1)
                    N[q, k, cl[i] - cl0] += 1
                    nxt[q, k] = i + xoff[k]
    return G, N


class Kernel(unittest.TestCase):
    def test_matches_a_plain_loop_with_gaps_gates_shift_and_thinning(self):
        rng = np.random.default_rng(1)
        n, blk = 4000, 100
        x = rng.normal(size=n)
        x[rng.random(n) < 0.05] = np.nan
        x[rng.random(n) < 0.02] = 0.0
        px = 100 * np.exp(np.cumsum(rng.normal(0, 1e-3, n)))
        px[rng.random(n) < 0.03] = np.nan
        pe = px * (1 + 1e-4)
        gate = (rng.random(n) < 0.7).astype(np.uint8)
        tb = (np.arange(n) // blk).astype(np.int32)
        cl = (np.arange(n) // 500).astype(np.int32)
        thr = at.block_thresholds(x, blk, 300, 100, QS, n // blk)
        self.assertTrue(np.isnan(thr[:3]).all() and np.isfinite(thr[4:]).all())
        self.assertTrue((np.diff(thr[5:], axis=1) >= 0).all())
        eoff, xoff = np.array([1, 1, 2], np.int64), np.array([1, 5, 9], np.int64)
        for shift in (0, 700):
            G = np.zeros((len(QS), 3, 6))
            N = np.zeros_like(G)
            at.kernel(x, thr, tb, gate, pe, px, cl, eoff, xoff, 1000, 4000, shift, 2, G, N)
            Gn, Nn = naive(x, thr, tb, gate, pe, px, cl, eoff, xoff, 1000, 4000, shift, 2)
            self.assertEqual(N.sum(), Nn.sum())
            self.assertGreater(N.sum(), 50)
            self.assertTrue(np.allclose(N, np.pad(Nn, ((0, 0), (0, 0), (0, N.shape[2] - Nn.shape[2])))))
            self.assertTrue(np.allclose(G, np.pad(Gn, ((0, 0), (0, 0), (0, G.shape[2] - Gn.shape[2]))), atol=1e-12))

    def test_thresholds_use_only_the_window_before_the_block(self):
        x = np.r_[np.full(100, 1.0), np.full(100, 5.0)]
        thr = at.block_thresholds(x, 50, 100, 50, QS, 4)
        self.assertTrue(np.isnan(thr[0]).all() and np.isnan(thr[1]).all())
        self.assertTrue((thr[2] == 1.0).all())            # block 2 (bars 100-149) sees bars 0-99 only
        self.assertEqual(thr[3, 0], 5.0)


class Stats(unittest.TestCase):
    def test_rolling_sums_need_every_value(self):
        a = np.array([1.0, 2, np.nan, 4, 5, 6])
        self.assertTrue(np.allclose(at.rollsum(a, 2), [np.nan, 3, np.nan, np.nan, 9, 11], equal_nan=True))
        m = at.rollmean_tol(a, 3, 0.6)
        self.assertTrue(np.isnan(m[:2]).all() and np.isclose(m[2], 1.5) and np.isclose(m[5], 5.0))

    def test_cluster_t_matches_a_hand_calculation(self):
        G = np.array([[0.02, 0.04, -0.01, 0.03]])
        N = np.array([[2.0, 2.0, 1.0, 3.0]])
        C = N * 0.001
        mean, t = at.cluster_t(G, N, C, 1.0, 1)
        R = G - C
        mu = R.sum() / N.sum()
        res = R - mu * N
        se = np.sqrt((res ** 2).sum() * 4 / 3) / N.sum()
        self.assertAlmostEqual(float(mean[0]), mu)
        self.assertAlmostEqual(float(t[0]), mu / se)
        _, tf = at.cluster_t(G, N, C, -1.0, 0)
        _, tp = at.cluster_t(G, N, C, 1.0, 0)
        self.assertAlmostEqual(float(tf[0]), float(-tp[0]))      # the centred statistic is odd in the side

    def test_sets_and_grid_size(self):
        names, W = at.sets_of(at.COINS)
        self.assertEqual(len(names), 14)
        self.assertEqual(W[12].sum(), 12)
        self.assertEqual(W[13].sum(), 3)
        a = SimpleNamespace(name="A", bases=at.A_BASES, gate_names=at.A_GATES, eoff=at.A_HOLDS, set_names=names)
        b = SimpleNamespace(name="B", bases=at.B_BASES, gate_names=at.B_GATES, eoff=at.B_HOLDS, set_names=names)
        s = at.grid_size([a, b])
        self.assertEqual((len(at.A_BASES), len(at.B_BASES), len(at.B_HOLDS)), (22, 26, 12))
        self.assertEqual(s, {"A": 22 * 8 * 5 * 7 * 14 * 2, "B": 26 * 3 * 5 * 12 * 14 * 2})
        self.assertEqual(sum(s.values()), 303520)

    def test_pvalues_count_the_placebos_at_least_as_large(self):
        df = pd.DataFrame({"block": ["A"] * 3, "eligible": [True] * 3, "t_val_1x": [0.5, 3.1, 9.0],
                           "net2x_val_bp": [1.0, 1.0, 1.0], "disc_ok": [True] * 3})
        part = ("A", "x", df, np.array([1.0, 2.0, 3.0, 4.0]), np.array([1.0, 2.0, 3.0, 4.0]),
                np.array([0, 1, 0, 0]), np.array([1, 1, 1, 1]), 0.0)
        out, joint, *_ = at.combine([part], 4)
        self.assertTrue(np.allclose(out.p_fullgrid, [1.0, (1 + 1) / 5, 1 / 5]))
        self.assertEqual(out.candidate.tolist(), [False] * 3)      # 0.2 is above the 0.05 rule


def planted_bars(coins, n_days, seed, edge):
    """Random-walk minute bars where the next minute's return follows this minute's taker imbalance by `edge`."""
    rng = np.random.default_rng(seed)
    n = n_days * 1440
    bars = {}
    for c in coins:
        f = rng.uniform(0.3, 0.7, n)
        vol = rng.uniform(50, 150, n)
        r = rng.normal(0, 4e-4, n)
        r[1:] += edge * (2 * f[:-1] - 1) / 0.4
        close = 100 * np.exp(np.cumsum(r))
        openp = np.r_[100.0, close[:-1]]
        bars[c] = dict(open=openp, high=close, low=close, close=close, volume=vol, tbv=f * vol)
    return bars


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.old = (at.MIN_TRADES, dict(at.BLOCKS))
        at.MIN_TRADES = 30

    def tearDown(self):
        at.MIN_TRADES = self.old[0]
        at.BLOCKS.clear()
        at.BLOCKS.update(self.old[1])

    def run_a(self, edge):
        coins = ("BTC", "ETH", "SOL")
        walk = {c: 0.3 for c in at.COINS}
        t0 = at.r349.ms("2021-01-01")
        bars = planted_bars(coins, 120, 5, edge)
        blk = at.build_block_a(bars, walk, coins=coins, t0=t0, t1=t0 + 120 * 86_400_000,
                               split_ms=t0 + 60 * 86_400_000, nplacebo=8)
        at.BLOCKS["A"] = blk
        res = at.run_base(("A", at.A_BASES.index("flow_1"), 8))
        return res, blk

    def test_a_planted_flow_signal_is_found_and_the_placebo_does_not_find_it(self):
        (name, base, df, Mf, Ms, cnt, cnt2, _), blk = self.run_a(edge=6e-4)
        self.assertEqual((name, base, len(df)), ("A", "flow_1", 2 * 5 * 8 * 5 * 7))
        top = df[df.eligible & (df.side == "follow") & (df.gate == "none") & (df.hold == "1m") & (df.coin_set == "BTC")]
        self.assertGreater(top.t_val_1x.max(), 8.0)
        self.assertGreater(top.net1x_val_bp.max(), 0.0)
        fade = df[(df.side == "fade") & (df.gate == "none") & (df.coin_set == "BTC") & (df.hold == "1m") & df.eligible]
        self.assertLess(fade.net1x_val_bp.max(), 0.0)
        self.assertLess(Mf.max(), top.t_val_1x.max() / 2)          # shifting the signal destroys it
        self.assertEqual(len(Mf), 8)
        self.assertTrue(df[df.q == 0.995].n_val.min() >= 0)

    def test_a_null_world_gives_no_cell_that_pays(self):
        (_, _, df, Mf, *_), _ = self.run_a(edge=0.0)
        self.assertLess(df[df.eligible].t_val_1x.max(), 4.0)
        chance = int((df.disc_ok & (df.t_val_1x >= 2) & (df.net2x_val_bp > 0)).sum())
        self.assertGreater(df.eligible.sum(), 1000)
        self.assertLess(chance, 0.03 * df.eligible.sum())      # a few small cells pass by chance; max-T is what stops them

    def test_b_planted_lighter_lag_is_found_on_the_dev_signal(self):
        coins = ("BTC", "ETH", "SOL")
        rng = np.random.default_rng(9)
        days = 4
        ns = days * at.DAY_S
        off = [i * at.DAY_S for i in range(days)]
        tp = {}
        for c in coins:
            b = 100 * np.exp(np.cumsum(rng.normal(0, 2e-4, ns)))
            lm = np.r_[np.full(3, b[0]), b[:-3]]
            tp[c] = {k: np.full(ns, np.nan) for k in ("bmid", "bofi", "bimb", "bn", "tf", "lmid", "lofi", "mmid", "mofi")}
            tp[c].update(bmid=b, lmid=lm, mmid=b, bn=np.full(ns, 20.0), bofi=rng.normal(size=ns),
                         lofi=rng.normal(size=ns), mofi=rng.normal(size=ns), tf=rng.normal(size=ns),
                         bimb=rng.uniform(-1, 1, ns))
        walk = {c: 0.01 for c in at.COINS}
        blk = at.build_block_b(tp, ns, off, walk, coins=coins, nplacebo=6, n_disc_days=2)
        self.assertEqual(blk.per["val"][0], 2 * at.DAY_S)
        at.BLOCKS["B"] = blk
        _, base, df, Mf, *_ = at.run_base(("B", at.B_BASES.index("dev_bl"), 6))
        self.assertEqual(len(df), 2 * 5 * 3 * 5 * 12)
        best = df[df.eligible & (df.side == "follow") & (df.gate == "none") & (df.coin_set == "all12")]
        self.assertGreater(best.t_val_1x.max(), 5.0)
        self.assertLess(Mf.max(), best.t_val_1x.max())


class Loaders(unittest.TestCase):
    def test_day_offsets_leave_a_gap_only_across_missing_days(self):
        off, ns = at.day_offsets(["2026-10-21", "2026-10-22", "2026-10-26"])
        self.assertEqual(off, [0, at.DAY_S, 2 * at.DAY_S + at.GAP_S])
        self.assertEqual(ns, 3 * at.DAY_S + at.GAP_S)

    def test_tape_loader_carries_lighter_forward_but_not_across_an_outage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            day = "2026-10-21"
            d0 = int(pd.Timestamp(day, tz="UTC").timestamp()) * 1000
            secs = np.r_[0:100, 200:300]                      # a recorder outage from second 100 to 199

            def book(venue, secs_):
                (root / "data" / "tape" / venue / "book").mkdir(parents=True, exist_ok=True)
                n = len(secs_)
                pd.DataFrame({"s": d0 + secs_ * 1000, "sym": "BTC", "bid": 99.0, "bid_sz": 3.0, "ask": 101.0,
                              "ask_sz": 1.0, "ofi": 2.0, "n": 5}).iloc[:n].to_parquet(
                    root / "data" / "tape" / venue / "book" / f"{day}.parquet", index=False)

            book("binance", secs)
            book("lighter", np.array([10, 250]))               # one update at 10 s, one at 250 s
            book("mexc", secs)
            (root / "data" / "tape" / "binance" / "trades").mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"s": [d0 + 5000], "sym": ["BTC"], "buy_qty": [3.0], "sell_qty": [1.0]}).to_parquet(
                root / "data" / "tape" / "binance" / "trades" / f"{day}.parquet", index=False)
            tp, ns, off = at.load_tape(root, [day], ["BTC"])
        t = tp["BTC"]
        self.assertEqual(ns, at.DAY_S)
        self.assertEqual(t["bmid"][50], 100.0)
        self.assertTrue(np.isnan(t["bmid"][150]))
        self.assertTrue(np.isnan(t["lmid"][5]) and t["lmid"][10] == 100.0 and t["lmid"][99] == 100.0)
        self.assertTrue(np.isnan(t["lmid"][150]))              # down: masked
        self.assertTrue(np.isnan(t["lmid"][200]))              # the carry does not cross the outage
        self.assertEqual(t["lmid"][250], 100.0)
        self.assertEqual(t["lofi"][50], 0.0)                   # no row while recording means no flow
        self.assertTrue(np.isnan(t["lofi"][150]))
        self.assertEqual(t["tf"][5], 2.0)
        self.assertEqual(t["tf"][6], 0.0)
        self.assertEqual(t["bimb"][50], 0.5)


class VerifyFirst(unittest.TestCase):
    def test_main_refuses_an_unfrozen_prereg(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "PREREG.md").write_text("x")
            old = at.LANE
            at.LANE = Path(d)
            try:
                with self.assertRaises(prereg.PreregError):
                    at.main()
            finally:
                at.LANE = old


if __name__ == "__main__":
    unittest.main()
