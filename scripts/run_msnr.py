"""R306 msnr_v1: Malaysian support and resistance (M323) on 4-hour candles, as set out in experiments/msnr_v1/PREREG.md.

Malaysian SnR draws levels from candle bodies, not wicks:
- an A-level (resistance) is the close of a bullish 4-hour candle followed by a bearish one: a line-chart peak;
- a V-level (support) is the close of a bearish candle followed by a bullish one: a line-chart valley;
- a level is fresh until a wick touches it. The method trades the first touch of a fresh level.

Two modes, each with both sides:
- fade: a resting limit order at the level fills on the first touch (the wick must pass it by PEN), against the move;
- break: the 4-hour candle of the first touch closes beyond the level; enter at that close, with the move.

Exits: a time exit (24 or 72 hours) or a bracket (stop 1 ATR, target 2 ATR, at most 72 hours). Within an hour bar the
stop is assumed to come first. One position per instrument at a time. Costs per side, funding paid by longs.

usage: python scripts/run_msnr.py [--plumbing | --trees]
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, flowfeat, prereg, research, stats  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402

LANE = ROOT / "experiments" / "msnr_v1"
HOUR = 3_600_000
PEN = 2e-4                       # the wick must pass the level by 2 bp for a resting order to count as filled
ATR_N = 14                       # 4-hour candles
TOP = 50                         # crypto: trailing 30-day volume rank at the event
MODES = ("fade", "break")
AGES = (30, 180)                 # 4-hour candles a level stays live: 5 and 30 days
EXITS = ("t24", "t72", "bracket")
BOOKS = [(m, a, x) for m in MODES for a in AGES for x in EXITS]
WINDOWS = {"disc": ("2021-01-01", "2024-01-01"), "valid": ("2024-01-01", "2026-10-01")}
END = "2026-10-01"               # nothing at or after this hour is read (archive end; later rows are reserved)
FLAT_COST = 8.5e-4               # per side, the secondary set (API, 1x)
T_MIN = 2.0
SECONDARY = {
    "binance": ["XAUUSDT", "XAGUSDT", "PAXGUSDT"],
    "mexc_hist": ["EUR_USDT", "GBP_USDT", "JPY_USDT", "SILVER_USDT", "XAU_USDT"],
    "mexc_tradfi": ["NAS100_USDT", "SPX500_USDT", "US30_USDT", "HK50_USDT", "JP225_USDT", "USOIL_USDT", "UKOIL_USDT",
                    "NGAS_USDT", "QQQSTOCK_USDT"],
}
TRIALS = 2 * len(BOOKS)          # the crypto family, plus the same books read once on the secondary set
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def label(b):
    return f"{b[0]} age{b[1]} {b[2]}"


# ------------------------------------------------------------------------------------------------------- levels
def candles(o, h, l, c):
    """4-hour candles from hourly rows 4k..4k+3 (row 0 must open at a 4-hour boundary). NaN if any hour is missing."""
    n = len(c) // 4
    sl = slice(0, 4 * n)
    O = o[sl][0::4].copy()
    C = c[sl][3::4].copy()
    H = h[sl].reshape(n, 4).max(axis=1)
    L = l[sl].reshape(n, 4).min(axis=1)
    bad = ~np.isfinite(np.column_stack([o[sl].reshape(n, 4), h[sl].reshape(n, 4), l[sl].reshape(n, 4),
                                        c[sl].reshape(n, 4)])).all(axis=1)
    for x in (O, H, L, C):
        x[bad] = np.nan
    return O, H, L, C


def atr_frac(H, L, C, n=ATR_N):
    """ATR(n) over the candles up to and including k, as a fraction of C[k]."""
    pc = np.concatenate([[np.nan], C[:-1]])
    tr = np.nanmax(np.column_stack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=1)
    tr[~np.isfinite(H - L)] = np.nan
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy() / C


def levels(O, H, L, C):
    """[(kind, price, live_from_row, atr)]: kind +1 for an A-level (resistance), -1 for a V-level (support). The pair
    (k, k+1) is known when candle k+1 closes, so the level is live from hourly row 4(k+2)."""
    bull = C > O
    bear = C < O
    atr = atr_frac(H, L, C)
    out = []
    for k in np.flatnonzero((bull[:-1] & bear[1:]) | (bear[:-1] & bull[1:])):
        if not np.isfinite(atr[k + 1]):
            continue
        out.append((1 if bull[k] else -1, float(C[k]), 4 * (k + 2), float(atr[k + 1])))
    return out


def first_touch(h, l, kind, price, start, stop, pen=PEN):
    """The first hourly row in [start, stop) whose wick passes the level by pen; -1 if none."""
    if kind == 1:
        hit = h[start:stop] >= price * (1 + pen)
    else:
        hit = l[start:stop] <= price * (1 - pen)
    i = np.flatnonzero(hit)
    return int(start + i[0]) if len(i) else -1


# -------------------------------------------------------------------------------------------------------- trades
def events(lv, o, h, l, c, mode, age):
    """Candidate entries [(row, side, entry_price, atr, level)] in time order. Fade: the touch row, at the level.
    Break: the last row of the touch's 4-hour candle, at its close, when that close is beyond the level."""
    T = len(c)
    out = []
    for kind, price, live, atr in lv:
        if live >= T:
            continue
        r = first_touch(h, l, kind, price, live, min(T, live + 4 * age))
        if r < 0:
            continue
        if mode == "fade":
            if not (np.isfinite(o[r]) and (o[r] < price if kind == 1 else o[r] > price)):
                continue                                   # opened beyond the level: no resting fill at it
            out.append((r, -kind, price, atr, price))
        else:
            e = 4 * (r // 4) + 3
            if e >= T or not np.isfinite(c[e]):
                continue
            if (kind == 1 and c[e] > price) or (kind == -1 and c[e] < price):
                out.append((e, kind, float(c[e]), atr, price))
    # several levels touched in one bar: keep the nearest to the entry (one trade per row)
    out.sort(key=lambda z: (z[0], -z[1] * z[4]))          # the lowest A-level or the highest V-level is reached first
    seen, uniq = set(), []
    for z in out:
        if z[0] not in seen:
            seen.add(z[0])
            uniq.append(z)
    return uniq


def time_exit(entry_row, c, rule):
    """(exit_row, close) after 24 or 72 hours, or None if the data ends first."""
    last = entry_row + (24 if rule == "t24" else 72)
    if last >= len(c) or not np.isfinite(c[last]):
        return None
    return last, float(c[last])


def bracket_exit(side, entry_row, entry, atr, h, l, c, fade, cap=72):
    """Stop 1 ATR, target 2 ATR, else the close after `cap` hours. Fade entries fill inside their bar, so that bar can
    only stop out (the order of its moves is unknown); break entries start on the next bar. Stop first within a bar."""
    T = len(c)
    last = entry_row + cap
    if last >= T:
        return None
    stop = entry * (1 - side * atr)
    target = entry * (1 + side * 2 * atr)
    for r in range(entry_row if fade else entry_row + 1, last + 1):
        hi, lo = h[r], l[r]
        if not (np.isfinite(hi) and np.isfinite(lo)):
            continue
        if (side == 1 and lo <= stop) or (side == -1 and hi >= stop):
            return r, float(stop)
        if r == entry_row:
            continue
        if (side == 1 and hi >= target) or (side == -1 and lo <= target):
            return r, float(target)
    return (last, float(c[last])) if np.isfinite(c[last]) else None


def trades(lv, t, o, h, l, c, fund, cost, ok, book):
    """Non-overlapping trades for one instrument: dicts with entry/exit times, side, gross and funding (fractions) and
    the one-way cost at entry. `ok[row]` says whether the instrument may be entered at that row."""
    mode, age, rule = book
    fade = mode == "fade"
    busy_until = -1
    out = []
    for row, side, entry, atr, level in events(lv, o, h, l, c, mode, age):
        if row <= busy_until or not ok[row]:
            continue
        ex = bracket_exit(side, row, entry, atr, h, l, c, fade) if rule == "bracket" else time_exit(row, c, rule)
        if ex is None:
            continue
        xr, xp = ex
        f = float(np.nansum(fund[row + 1:xr + 1]))
        out.append({"t": int(t[row]), "t_exit": int(t[xr]), "side": side, "gross": side * (xp / entry - 1.0),
                    "funding": -side * f, "cost": float(cost[row]), "kind": "A" if (side == -1) == fade else "V"})
        busy_until = xr
    return out


def net(tr, cmult):
    return tr["gross"] + tr["funding"] - 2.0 * cmult * tr["cost"]


# --------------------------------------------------------------------------------------------------------- stats
def cohort_stats(tr_list, a_ms, b_ms, cmult, lag=3):
    """Per-day mean net of the trades entered that day (exits inside the window): the equal-weight book of each day's
    entries. Returns mean (bp per trade-day), Newey-West t, days, trades, mean per trade, without the 10 best days."""
    rows = [(x["t"], net(x, cmult)) for x in tr_list if a_ms <= x["t"] and x["t_exit"] < b_ms]
    if not rows:
        return {"trades": 0}
    df = pd.DataFrame(rows, columns=["t", "net"])
    df["day"] = df.t // (24 * HOUR)
    d = df.groupby("day").net.mean().to_numpy()
    n, m, tt = stats.newey_west_t(d, lag) if len(d) > 10 else (len(d), float(np.mean(d)), None)
    s = np.sort(d)
    return {"trades": int(len(df)), "days": int(len(d)), "mean_bp": float(m * 1e4),
            "t": None if tt is None or not np.isfinite(tt) else float(tt),
            "per_trade_bp": float(df.net.mean() * 1e4), "hit": float((df.net > 0).mean()),
            "wo_best10_bp": float(s[:-10].mean() * 1e4) if len(s) > 20 else None}


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


# ---------------------------------------------------------------------------------------------------------- data
def crypto():
    """Binance perps from the research universe (2021-01-01 .. 2026-09-30): per symbol (o, h, l, c, fund, cost, ok)."""
    u, _, _ = research.load_universe()
    t = np.asarray(u.p.t)
    end = int(np.searchsorted(t, ms(END)))
    t = t[:end]
    syms = list(u.p.symbols)
    kl = flowfeat.load("klines", t, syms, ("open", "high", "low"))
    c = np.asarray(u.p["close"], np.float64)[:end]
    ret = np.asarray(u.ret, np.float64)[:end]
    fund = np.zeros_like(c)
    with np.errstate(invalid="ignore", divide="ignore"):
        fund[1:] = np.nan_to_num(c[1:] / c[:-1] - 1.0 - ret[:-1], nan=0.0)   # the rate settling on each row
    rank = np.asarray(u.rank)[:end]
    elig = np.asarray(u.elig)[:end]
    cmat = np.asarray(u.cmat, np.float64)[:end]
    out = {}
    for j, s in enumerate(syms):
        ok = elig[:, j] & (rank[:, j] <= TOP)
        if not ok.any():
            continue
        out[s] = (np.asarray(kl["open"][:, j], np.float64), np.asarray(kl["high"][:, j], np.float64),
                  np.asarray(kl["low"][:, j], np.float64), c[:, j], fund[:, j], cmat[:, j], ok)
    return t, out


def hourly_grid(df, fund_df, start_ms, end_ms):
    """An hourly frame from a kline parquet (t, open, high, low, close) on a full grid starting at a 4-hour boundary,
    with the funding rate settling on each row."""
    t0 = int(max(df.t.min(), start_ms))
    t0 += (-t0) % (4 * HOUR)
    t = np.arange(t0, end_ms, HOUR, dtype=np.int64)
    g = df.set_index(df.t.astype(np.int64))[["open", "high", "low", "close"]].reindex(t)
    f = np.zeros(len(t))
    if fund_df is not None and len(fund_df):
        ft = (fund_df.t.astype(np.int64) // HOUR) * HOUR
        i = np.searchsorted(t, ft.to_numpy())
        okf = (i < len(t)) & (t[np.minimum(i, len(t) - 1)] == ft.to_numpy())
        np.add.at(f, i[okf], fund_df.rate.to_numpy()[okf])
    return t, g, f


def secondary():
    """The metal, FX and index perps: per symbol (t, o, h, l, c, fund, cost, ok) up to END."""
    end = ms(END)
    out = {}
    for venue, syms in SECONDARY.items():
        for s in syms:
            if venue == "binance":
                k, fpath = data.ROOT / "klines_1h" / f"{s}.parquet", data.ROOT / "fundingRate" / f"{s}.parquet"
            elif venue == "mexc_hist":
                k, fpath = data.ROOT / "mexc_hist" / "klines_1h" / f"{s}.parquet", \
                    data.ROOT / "mexc_hist" / "funding" / f"{s}.parquet"
            else:
                k, fpath = data.ROOT / "mexc_tradfi" / "klines_1h" / f"{s}.parquet", \
                    data.ROOT / "mexc_tradfi" / "funding" / f"{s}.parquet"
            if not k.exists():
                continue
            df = pd.read_parquet(k, columns=["t", "open", "high", "low", "close"])
            df = df[df.t < end]                            # rows at or after END are reserved: dropped on read
            fd = pd.read_parquet(fpath) if fpath.exists() else None
            if fd is not None:
                fd = fd[fd.t < end]
            t, g, f = hourly_grid(df, fd, ms(WINDOWS["disc"][0]), end)
            if len(t) < 24 * 60:
                continue
            out[f"{venue}:{s}"] = (t, g.open.to_numpy(float), g.high.to_numpy(float), g.low.to_numpy(float),
                                   g.close.to_numpy(float), f, np.full(len(t), FLAT_COST), np.ones(len(t), bool))
    return out


def secondary_files():
    """The secondary set's kline and funding files that exist, in a fixed order."""
    out = []
    for venue, syms in SECONDARY.items():
        base = data.ROOT if venue == "binance" else data.ROOT / venue
        fund = "fundingRate" if venue == "binance" else "funding"
        for s in syms:
            out += [p for p in (base / "klines_1h" / f"{s}.parquet", base / fund / f"{s}.parquet") if p.exists()]
    return out


def tree_sha(paths, root=ROOT):
    """One sha256 over (relative path, file sha256) lines: pins hundreds of files in one frozen line."""
    h = hashlib.sha256()
    for p in sorted(paths, key=str):
        h.update(f"{prereg.sha256_file(p)}  {Path(p).relative_to(root)}\n".encode())
    return h.hexdigest()


def tree_paths():
    """The two file trees this lane reads besides its listed inputs: the hourly klines of every research-universe
    perp, and the secondary set."""
    meta = json.loads((data.ROOT / "research" / "meta.json").read_text())
    kl = [p for p in (data.ROOT / "klines_1h" / f"{s}.parquet" for s in meta["symbols"]) if p.exists()]
    return {"klines_1h": kl, "secondary": secondary_files()}


def check_trees(prereg_path):
    """Every tree in the PREREG's trees block must still hash to its frozen sha256."""
    block = re.search(r"```trees\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    want = dict(line.split()[::-1] for line in block.strip().splitlines())
    paths = tree_paths()
    got = {}
    for name, sha in want.items():
        got[name] = tree_sha(paths[name])
        if got[name] != sha:
            raise prereg.PreregError(f"tree {name}: sha256 {got[name]} != frozen {sha}")
    return got


# ---------------------------------------------------------------------------------------------------------- main
def run_crypto():
    t, inst = crypto()
    log(f"crypto: {len(inst)} perps ever in the top {TOP}, {len(t)} hours")
    res = {}
    for b in BOOKS:
        allt = []
        for s, (o, h, l, c, fund, cost, ok) in inst.items():
            O, H, L, C = candles(o, h, l, c)
            allt += [{**x, "inst": s} for x in trades(levels(O, H, L, C), t, o, h, l, c, fund, cost, ok, b)]
        res[b] = allt
        log(f"{label(b)}: {len(allt)} trades")
    return t, res


def report(res):
    rep = {}
    va, vb = ms(WINDOWS["valid"][0]), ms(WINDOWS["valid"][1])
    for b, tr in res.items():
        rep[label(b)] = {w: {f"{m}x": cohort_stats(tr, ms(a), ms(e), m) for m in (1, 2, 3)}
                         for w, (a, e) in WINDOWS.items()}
        rep[label(b)]["sides_valid_1x"] = {k: cohort_stats([x for x in tr if x["kind"] == k], va, vb, 1)
                                           for k in ("A", "V")}
    return rep


def decide(rep):
    cand = [(k, v["disc"]["1x"]) for k, v in rep.items() if v["disc"]["1x"].get("t") is not None
            and v["disc"]["1x"]["mean_bp"] > 0]
    if not cand:
        return None, False, {}
    pick = max(cand, key=lambda z: z[1]["t"])[0]
    v = rep[pick]["valid"]
    checks = {"t_1x": (v["1x"].get("t") or -np.inf) >= T_MIN, "mean_2x": v["2x"].get("mean_bp", -1) > 0,
              "wo_best": (v["1x"].get("wo_best10_bp") or -1) > 0}
    return pick, all(checks.values()), checks


def run_secondary():
    inst = secondary()
    log(f"secondary: {len(inst)} instruments")
    out = {}
    for b in BOOKS:
        allt = []
        for s, (t, o, h, l, c, fund, cost, ok) in inst.items():
            O, H, L, C = candles(o, h, l, c)
            allt += [{**x, "inst": s} for x in trades(levels(O, H, L, C), t, o, h, l, c, fund, cost, ok, b)]
        out[label(b)] = allt
    rep = {k: {f"{m}x": cohort_stats(tr, ms(WINDOWS["disc"][0]), ms(END), m) for m in (1, 2, 3)}
           for k, tr in out.items()}
    return {"instruments": sorted(inst), "books": rep}, out


def plumbing():
    """Counts only: levels and first touches per mode, no return read."""
    t, inst = crypto()
    n_lv, n_ev = 0, {m: 0 for m in MODES}
    for s, (o, h, l, c, fund, cost, ok) in inst.items():
        O, H, L, C = candles(o, h, l, c)
        lv = levels(O, H, L, C)
        n_lv += len(lv)
        for m in MODES:
            n_ev[m] += sum(1 for e in events(lv, o, h, l, c, m, 30) if ok[e[0]])
    sec = secondary()
    return {"perps": len(inst), "hours": len(t), "levels": n_lv, "events_age30": n_ev,
            "secondary": {k: int(len(v[0])) for k, v in sec.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no return read")
    ap.add_argument("--trees", action="store_true", help="print the file-tree hashes for the PREREG")
    a = ap.parse_args()
    if a.plumbing:
        print(json.dumps(plumbing(), indent=1))
        return
    if a.trees:
        for name, paths in tree_paths().items():
            print(f"{tree_sha(paths)}  {name}  ({len(paths)} files)")
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    trees = check_trees(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs and {len(trees)} file trees match")
    t, res = run_crypto()
    rep = report(res)
    pick, ok, checks = decide(rep)
    for k, v in rep.items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc {d.get('mean_bp', float('nan')):+.2f} bp t {d.get('t')} ({d.get('trades')} trades); valid "
            f"{va.get('mean_bp', float('nan')):+.2f} t {va.get('t')} ({va.get('trades')})")
    log(f"pick {pick}, passes {ok} {checks}")
    sec, sec_trades = run_secondary()
    for k, v in sec["books"].items():
        log(f"secondary {k}: {v.get('1x', {}).get('mean_bp')} bp t {v.get('1x', {}).get('t')} "
            f"({v.get('1x', {}).get('trades')} trades)")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"book": label(b), **x} for b, tr in res.items() for x in tr]).to_csv(
        res_dir / "trades.csv.gz", index=False, float_format="%.6g")
    pd.DataFrame([{"book": k, **x} for k, tr in sec_trades.items() for x in tr]).to_csv(
        res_dir / "secondary_trades.csv", index=False, float_format="%.6g")
    summary = {"rid": "R306", "verdict": "PARTIAL" if ok else "NULL", "trials": TRIALS, "prereg_sha256": sha,
               "inputs": shas, "trees": trees, "pick": pick, "pick_passes": bool(ok), "checks": checks, "books": rep,
               "secondary": sec}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
