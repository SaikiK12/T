"""R347 tapelag_lighter_v1: zero-fee scalps on Lighter, traded toward Binance's quote after a dislocation (M264, M293).

Lighter's default account pays no fee on API orders, but a taker order, cancel or modify waits 300 ms before it
reaches the book (docs/VENUE_STRUCTURE.md). The question is whether Lighter's quote is still off Binance's after that
delay. The tape (scripts/record_tape.py, lab/tape.py) holds, for each second, the last best bid and ask of 12 coins on
both venues. Nobody has read it against price changes, so it is an unread sample (docs/GATES.md, gate 1).

The rule, for each coin and each second s:
- d(s) = 10,000 ln(Lighter mid / Binance mid), the basis in bp. ref(s) is its median over s-300..s-1, from at least
  200 of those seconds. dev(s) = d(s) - ref(s).
- c(t) is the cost of one side at second t: max(Lighter's quoted half-spread at t, the coin's median cost of a $1k
  market order on Lighter's book over the recorder's snapshots, 0.1 bp).
- dev(s) <= -(theta + 2 c(s)): Lighter is cheap by more than a round trip, so buy it. dev(s) >= theta + 2 c(s): sell.
- The order fills at the end of second s+1, at Lighter's mid plus c (to buy) or minus c (to sell). That is a full
  second after the signal, where Lighter's rules impose 300 ms.
- The position closes H seconds later at Lighter's mid minus (or plus) c. One position per coin. A hold that spans the
  top of an hour (Lighter's funding time) is skipped.
- Fee 0. 2x and 3x charge 2c and 3c a side.

A venue is connected over a stretch of seconds in which it sent an update for some coin at least every 5 seconds. A new
stretch starts after each recorded connection end (data/tape/sessions.csv). A coin's quote is its last update inside
the current stretch; before its first one, it is unknown.

usage: python scripts/run_tapelag_lighter.py --plumbing   coverage, quotes, sizes, signal counts; no forward prices
       python scripts/run_tapelag_lighter.py --run        verifies the frozen PREREG and its inputs, then runs
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "tapelag_lighter_v1"
TAPE = "data/tape"
SESSIONS = "experiments/tapelag_lighter_v1/inputs/sessions.csv"   # a frozen copy: the recorder appends to its own
BOOKS = "data/recorders/lighter_book/"
DAYS = ("2026-10-21", "2026-10-22", "2026-10-26")
COINS = ("BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "SUI", "ADA", "LINK", "AVAX", "LTC", "TRX")
STREAMS = {"binance": "binance_book", "lighter": "lighter"}
DAY_S = 86_400
GAP_MAX = 5           # seconds without an update on any coin before a venue counts as disconnected
WIN, WIN_MIN = 300, 200
DELAY = 1             # entry at the end of the second after the signal second
THETAS = (0.5, 1.0, 2.0)   # bp beyond the round-trip cost
HOLDS = (5, 30)
PRIMARY = (1.0, 5)
TOUCH_USD = 1_000.0        # reported only: the cost covers a $1k order
FLOOR_BP = 0.1             # per-side cost floor
BUCKET = 300          # seconds per bucket for the tests
NW_LAG = 3
BLOCK, DRAWS, SEED = 6, 2_000, 347
ALPHA = 0.05
TRIM = 10             # buckets removed at each end for the trimmed mean
TRIALS = len(THETAS) * len(HOLDS)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def day_ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def session_breaks(sessions, stream, d0):
    """Seconds of the day (from d0 ms) at which a connection of `stream` ended."""
    s = sessions[sessions.stream == stream]
    end = (pd.to_datetime(s.end_utc, utc=True) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    sec = (np.asarray(end, dtype=np.int64) - d0) // 1000
    return np.sort(sec[(sec >= 0) & (sec < DAY_S)]).astype(np.int64)


def stretches(alive, breaks=(), n=DAY_S, gap_max=GAP_MAX):
    """Stretch id of each second (-1: not connected). Consecutive seconds with an update belong to one stretch while
    the gap between them is at most gap_max seconds and no recorded break b (idx[k] <= b < idx[k+1]) lies between."""
    sid = np.full(n, -1, dtype=np.int64)
    idx = np.unique(np.asarray(alive, dtype=np.int64))
    idx = idx[(idx >= 0) & (idx < n)]
    if not len(idx):
        return sid
    cut = np.diff(idx) > gap_max
    br = np.asarray(breaks, dtype=np.int64)
    if len(br) and len(idx) > 1:
        pos = np.searchsorted(br, idx[:-1], side="left")
        cut |= (pos < len(br)) & (br[np.minimum(pos, len(br) - 1)] < idx[1:])
    starts = np.r_[0, np.flatnonzero(cut) + 1]
    ends = np.r_[np.flatnonzero(cut), len(idx) - 1]
    for k, (a, b) in enumerate(zip(starts, ends)):
        sid[idx[a]: idx[b] + 1] = k
    return sid


def grid(rows, d0, sid):
    """(bid, ask, bid_sz, ask_sz) of one coin at the end of each second: the last update at or before it in the same
    stretch, NaN outside stretches and before the coin's first update in its stretch."""
    sec = (rows.s.values - d0) // 1000
    keep = (sec >= 0) & (sec < len(sid))
    out = np.full((len(sid), 4), np.nan)
    out[sec[keep]] = rows[["bid", "ask", "bid_sz", "ask_sz"]].values[keep]
    out = pd.DataFrame(out).groupby(sid).ffill().to_numpy(copy=True)
    out[sid < 0] = np.nan
    return out.T


def deviation(bl, al, bb, ab, win=WIN, win_min=WIN_MIN):
    """Basis d in bp and its deviation from the median of the previous `win` seconds (NaN with fewer than win_min)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = (bl > 0) & (al > bl) & (bb > 0) & (ab > bb)
        d = np.where(ok, 1e4 * np.log((bl + al) / (bb + ab)), np.nan)
    ref = pd.Series(d).shift(1).rolling(win, min_periods=win_min).median().values
    return d, d - ref


def walk_costs(rows, coins=COINS, floor=FLOOR_BP):
    """Each coin's median cost of a $1k market order on Lighter's book (mean of the buy and sell sides), in bp a side,
    over the recorder's snapshots; a coin without snapshots gets NaN and cannot trade."""
    r = rows[rows.symbol.isin(coins)]
    med = ((r.buy_1k_bp + r.sell_1k_bp) / 2).groupby(r.symbol).median()
    return {c: max(float(med[c]), floor) if c in med.index and np.isfinite(med[c]) else float("nan") for c in coins}


def simulate(dev, bl, al, bsz, asz, theta, hold, walk, delay=DELAY):
    """Non-overlapping trades of one coin-day. Returns (trades DataFrame, skip counts)."""
    n = len(dev)
    with np.errstate(invalid="ignore", divide="ignore"):
        mid = (bl + al) / 2
        ok = (bl > 0) & (al > bl)
        cost = np.where(ok, np.maximum(1e4 * (al - bl) / (2 * mid), walk), np.nan)
        sig = np.flatnonzero(np.abs(dev) >= theta + 2 * cost)
    skips = dict(day_end=0, entry_quote=0, funding_hour=0, exit_quote=0)
    rows, free = [], 0
    for s in sig:
        if s < free:
            continue
        e, x = s + delay, s + delay + hold
        if x >= n:
            skips["day_end"] += 1
            break
        if not ok[e]:
            skips["entry_quote"] += 1
            continue
        if (e + 1) // 3600 != (x + 1) // 3600:
            skips["funding_hour"] += 1
            continue
        free = x + 1
        if not ok[x]:
            skips["exit_quote"] += 1
            continue
        side = 1 if dev[s] < 0 else -1
        gross = 1e4 * side * (mid[x] / mid[e] - 1)
        touch = al[e] * asz[e] if side > 0 else bl[e] * bsz[e]
        rows.append((s, e, x, side, dev[s], gross, gross - cost[e] - cost[x], cost[e], cost[x], touch))
    cols = ["s", "e", "x", "side", "dev", "gross", "net1", "c_e", "c_x", "touch_usd"]
    return pd.DataFrame(rows, columns=cols), skips


def stress(t, k):
    """Net at k times the cost: k c a side on entry and exit."""
    return t.gross - k * (t.c_e + t.c_x)


def bucket_series(trades, col, buckets):
    """Sum of `col` per bucket over the observable buckets (an ordered list of (day, bucket)), 0 with no trade."""
    s = trades.groupby(["day", "bucket"])[col].sum() if len(trades) else pd.Series(dtype=float)
    return np.array([float(s.get(b, 0.0)) for b in buckets])


def block_bootstrap(X, block=BLOCK, draws=DRAWS, seed=SEED):
    """Studentized circular block bootstrap of the bucket series (rows) of each trial (columns), resampled together
    with each column's mean removed. Returns (t, one-sided p of mean > 0, family-wise p over the columns)."""
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    rng = np.random.default_rng(seed)
    sd = X.std(0, ddof=1)
    t = np.where(sd > 0, X.mean(0) / (sd / np.sqrt(n)), np.nan)
    Z = X - X.mean(0)
    nb = -(-n // block)
    tb = np.empty((draws, k))
    for i in range(draws):
        ix = ((rng.integers(0, n, nb)[:, None] + np.arange(block)[None, :]).ravel()[:n]) % n
        Y = Z[ix]
        sy = Y.std(0, ddof=1)
        tb[i] = np.where(sy > 0, Y.mean(0) / (sy / np.sqrt(n)), 0.0)
    p = (1 + (tb >= t).sum(0)) / (draws + 1)
    pfw = (1 + (tb.max(1)[:, None] >= t[None, :]).sum(0)) / (draws + 1)
    undefined = ~np.isfinite(t)                  # a trial with no trade (or a constant series) cannot pass
    p[undefined], pfw[undefined] = 1.0, 1.0
    return t, p, pfw


def trimmed_mean(x, trim=TRIM):
    x = np.sort(np.asarray(x, dtype=float))
    return float(x[trim:len(x) - trim].mean()) if len(x) > 2 * trim else float("nan")


def load_day(day, sessions, root=ROOT):
    """{venue: book rows} for one day, and {venue: stretch ids}."""
    d0 = day_ms(day)
    books, sids = {}, {}
    for v in ("binance", "lighter"):
        b = pd.read_parquet(root / TAPE / v / "book" / f"{day}.parquet",
                            columns=["s", "sym", "bid", "bid_sz", "ask", "ask_sz", "lag_ms"])
        books[v] = b
        sids[v] = stretches((b.s.values - d0) // 1000, session_breaks(sessions, STREAMS[v], d0))
    return d0, books, sids


def coin_day(day, coin, d0, books, sids):
    """Grids and the deviation of one coin-day."""
    gb = grid(books["binance"][books["binance"].sym == coin], d0, sids["binance"])
    gl = grid(books["lighter"][books["lighter"].sym == coin], d0, sids["lighter"])
    d, dev = deviation(gl[0], gl[1], gb[0], gb[1])
    return gb, gl, d, dev


def q(x, ps=(0.5, 0.9, 0.99, 0.999)):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return {f"p{round(100 * p, 1):g}": round(float(np.quantile(x, p)), 3) for p in ps} if len(x) else {}


def book_rows(files, root=ROOT):
    return pd.concat([pd.read_parquet(root / f, columns=["symbol", "buy_1k_bp", "sell_1k_bp"]) for f in files])


def plumbing():
    """Coverage, quotes, touch sizes, lags and signal counts. It reads no price after a signal; the one return
    statistic is the unconditional spread of Lighter's mid change over each hold, for the power section."""
    sessions = pd.read_csv(ROOT / "data/tape/sessions.csv")
    snaps = sorted(str(f.relative_to(ROOT)) for f in (ROOT / BOOKS).glob("*/*.parquet"))
    walk = walk_costs(book_rows(snaps))
    out = {"days": {}, "coins": {}, "book_snapshots": len(snaps), "walk_cost_bp": walk}
    acc = {c: dict(hs_l=[], hs_b=[], touch=[], dev=[], joint=0, joint_touch=0, sd={h: [] for h in HOLDS},
                   above={str(t): 0 for t in THETAS}, episodes={str(t): 0 for t in THETAS}) for c in COINS}
    for day in DAYS:
        d0, books, sids = load_day(day, sessions)
        info = {v: dict(connected_h=round(float((sids[v] >= 0).sum()) / 3600, 2), stretches=int(sids[v].max() + 1),
                        lag_ms=q(books[v].lag_ms, (0.5, 0.9, 0.99))) for v in books}
        both = (sids["binance"] >= 0) & (sids["lighter"] >= 0)
        info["both_connected_h"] = round(float(both.sum()) / 3600, 2)
        out["days"][day] = info
        for c in COINS:
            gb, gl, d, dev = coin_day(day, c, d0, books, sids)
            a = acc[c]
            ok = np.isfinite(d)
            a["joint"] += int(ok.sum())
            mid_l = (gl[0] + gl[1]) / 2
            a["hs_l"].append((1e4 * (gl[1] - gl[0]) / (2 * mid_l))[ok])
            a["hs_b"].append((1e4 * (gb[1] - gb[0]) / (gb[0] + gb[1]))[ok])
            tmin = np.minimum(gl[0] * gl[2], gl[1] * gl[3])
            a["touch"].append(tmin[ok])
            a["joint_touch"] += int((tmin[ok] >= TOUCH_USD).sum())
            a["dev"].append(np.abs(dev[np.isfinite(dev)]))
            with np.errstate(invalid="ignore", divide="ignore"):
                cost = np.maximum(1e4 * (gl[1] - gl[0]) / (2 * mid_l), walk[c])
            for t in THETAS:
                with np.errstate(invalid="ignore"):
                    hit = np.abs(dev) >= t + 2 * cost
                a["above"][str(t)] += int(hit.sum())
                a["episodes"][str(t)] += int((hit[1:] & ~hit[:-1]).sum() + hit[0])
            for h in HOLDS:
                with np.errstate(invalid="ignore", divide="ignore"):
                    r = 1e4 * np.log(mid_l[h:] / mid_l[:-h])
                a["sd"][h].append(r[np.isfinite(r)])
    for c in COINS:
        a = acc[c]
        cat = {k: np.concatenate(a[k]) if a[k] else np.array([]) for k in ("hs_l", "hs_b", "touch", "dev")}
        out["coins"][c] = dict(
            joint_h=round(a["joint"] / 3600, 2),
            lighter_half_spread_bp=q(cat["hs_l"], (0.1, 0.5, 0.9)),
            binance_half_spread_bp=q(cat["hs_b"], (0.1, 0.5, 0.9)),
            lighter_touch_usd=q(cat["touch"], (0.1, 0.5, 0.9)),
            share_touch_ge_1k=round(a["joint_touch"] / max(a["joint"], 1), 3),
            abs_dev_bp=q(cat["dev"]),
            seconds_at_or_above=a["above"], episodes=a["episodes"],
            sd_mid_change_bp={str(h): round(float(np.concatenate(a["sd"][h]).std()), 3) if a["sd"][h] else None
                              for h in HOLDS})
    print(json.dumps(out, indent=1))


def frozen_inputs(prereg_path, root=ROOT):
    """Every file in the PREREG's inputs block must still hash to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    shas = {}
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
        shas[rel] = got
    return shas


def summarize(t, buckets, coins=COINS):
    """Per-trade means, bucket tests at 1x/2x/3x, trimmed and leave-two-coins-out means for one trial's trades."""
    out = dict(trades=int(len(t)))
    if not len(t):
        return out
    for k in (1, 2, 3):
        t[f"net{k}"] = stress(t, k) if k > 1 else t.net1
    out.update(gross_bp=round(float(t.gross.mean()), 3), cost_paid_bp=round(float((t.c_e + t.c_x).mean()), 3))
    deep = t[t.touch_usd >= TOUCH_USD]
    out["touch_ge_1k"] = dict(n=int(len(deep)), net1_bp=round(float(deep.net1.mean()), 3) if len(deep) else None)
    for k in (1, 2, 3):
        x = bucket_series(t, f"net{k}", buckets)
        _, mu, tt = newey_west_t(x, NW_LAG)
        out[f"{k}x"] = dict(per_trade_bp=round(float(t[f"net{k}"].mean()), 3),
                            per_bucket_bp=round(mu, 3), nw_t=round(tt, 2))
    x1 = bucket_series(t, "net1", buckets)
    out["trimmed_bucket_mean_1x"] = round(trimmed_mean(x1), 3)
    by = t.groupby("coin").net1.agg(["count", "mean", "sum"])
    top2 = by["sum"].nlargest(2).index.tolist()
    out["leave_two_coins_out_1x_bp"] = round(float(t[~t.coin.isin(top2)].net1.mean()), 3)
    out["two_coins_left_out"] = top2
    out["by_coin_1x"] = {c: dict(n=int(by.loc[c, "count"]), bp=round(float(by.loc[c, "mean"]), 2))
                         for c in coins if c in by.index}
    top3 = by["count"].sort_values(ascending=False, kind="stable").index[:3]
    out["top3_coins_by_trades"] = top3.tolist()
    out["top3_positive_1x"] = int((by.loc[top3, "mean"] > 0).sum())
    out["by_day_1x"] = {d: dict(n=int(len(g)), bp=round(float(g.net1.mean()), 2)) for d, g in t.groupby("day")}
    out["long_short"] = {("long" if s > 0 else "short"): dict(n=int(len(g)), bp=round(float(g.net1.mean()), 2))
                         for s, g in t.groupby("side")}
    return out


def run_days(days, sessions, walk, root=ROOT, delays=(DELAY,)):
    """All trials' trades on the given days, with the observable buckets (both venues quoting the coin)."""
    trades = {(th, h, dl): [] for th in THETAS for h in HOLDS for dl in delays}
    skips = {key: {} for key in trades}
    buckets = set()
    for day in days:
        d0, books, sids = load_day(day, sessions, root)
        for c in COINS:
            gb, gl, d, dev = coin_day(day, c, d0, books, sids)
            obs = np.flatnonzero(np.isfinite(dev))
            buckets.update((day, int(b)) for b in np.unique((obs + 1) // BUCKET))
            for key in trades:
                th, h, dl = key
                tr, sk = simulate(dev, gl[0], gl[1], gl[2], gl[3], th, h, walk[c], delay=dl)
                tr["coin"], tr["day"] = c, day
                tr["bucket"] = (tr.s + 1) // BUCKET      # the signal second is observable by construction
                trades[key].append(tr)
                for name, v in sk.items():
                    skips[key][name] = skips[key].get(name, 0) + v
    trades = {k: pd.concat(v, ignore_index=True) for k, v in trades.items()}
    return trades, skips, sorted(buckets)


def decide(primary, fam, trials):
    """PASS, PARTIAL or NULL by the frozen rule."""
    p = trials[primary]
    ok = (fam["p"][primary] <= ALPHA and p.get("2x", {}).get("per_trade_bp", -1) > 0
          and p.get("trimmed_bucket_mean_1x", -1) > 0 and p.get("top3_positive_1x", 0) >= 2)
    if ok:
        return "PASS"
    if any(fam["p_family"][k] <= ALPHA and trials[k].get("2x", {}).get("per_trade_bp", -1) > 0 for k in trials):
        return "PARTIAL"
    return "NULL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.plumbing:
        return plumbing()
    if not a.run:
        ap.error("use --plumbing, or --run once the PREREG is frozen")
    prereg.verify(LANE / "PREREG.md")
    shas = frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified; {len(shas)} inputs match")
    sessions = pd.read_csv(ROOT / SESSIONS)
    walk = walk_costs(book_rows([f for f in shas if f.startswith(BOOKS)]))
    log("walk cost bp a side: " + ", ".join(f"{c} {v:.2f}" for c, v in walk.items()))
    trades, skips, buckets = run_days(DAYS, sessions, walk, delays=(1, 2, 3))
    log(f"{len(buckets)} observable buckets of {BUCKET} s")
    keys = [(th, h) for th in THETAS for h in HOLDS]
    trials = {k: summarize(trades[(*k, DELAY)], buckets) for k in keys}
    X = np.column_stack([bucket_series(trades[(*k, DELAY)], "net1", buckets) for k in keys])
    tb, p, pfw = block_bootstrap(X)
    fam = dict(t={k: float(tb[i]) for i, k in enumerate(keys)}, p={k: float(p[i]) for i, k in enumerate(keys)},
               p_family={k: float(pfw[i]) for i, k in enumerate(keys)})
    verdict = decide(PRIMARY, fam, trials)
    delay = {f"theta{k[0]:g}_h{k[1]}": {f"delay_{dl}s_1x_bp": (round(float(trades[(*k, dl)].net1.mean()), 3)
                                                                if len(trades[(*k, dl)]) else None)
                                         for dl in (1, 2, 3)} for k in keys}
    out = dict(lane="tapelag_lighter_v1", registry="R347", trials=TRIALS, days=list(DAYS),
               observable_buckets=len(buckets), observable_hours=round(len(buckets) * BUCKET / 3600, 2),
               primary=f"theta{PRIMARY[0]:g}_h{PRIMARY[1]}", verdict=verdict,
               trials_detail={f"theta{k[0]:g}_h{k[1]}": dict(**trials[k], boot_t=round(fam["t"][k], 2),
                                                             boot_p=round(fam["p"][k], 4),
                                                             boot_p_family=round(fam["p_family"][k], 4),
                                                             skips=skips[(*k, DELAY)]) for k in keys},
               delay_sensitivity=delay, walk_cost_bp=walk, inputs=shas)
    (LANE / "results").mkdir(exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    for k in keys:
        trades[(*k, DELAY)].to_csv(LANE / "results" / f"trades_theta{k[0]:g}_h{k[1]}.csv.gz", index=False)
    log(f"verdict {verdict}; primary {out['trials_detail'][out['primary']].get('1x')}")


if __name__ == "__main__":
    main()
