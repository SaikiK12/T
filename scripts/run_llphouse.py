"""llphouse_v1 (R484, M536): does Lighter LLP's day return, the house side of Lighter's crowd P&L, predict the next
UTC day's BTC move on Hyperliquid? Rule, costs, window and decision are in experiments/llphouse_v1/PREREG.md.

Signal: LLP's share-price return between consecutive daily stamps (R446's `llp_prices`, the last stamp of each UTC
day, near 20:00 or 21:00 UTC). A house-loss event is a return below the 10th percentile of the previous 90 calendar
days' returns (strictly before the signal day, at least 60 present), a house-win event one above the 90th. On an
event day t, book F holds the sign of BTC's day-t close-to-close return over UTC day t+1 (open to close), book R the
opposite sign. Costs: 13 bp a round trip at 1x plus Hyperliquid's hourly funding over the held day.

Inputs, all pinned: LLP share prices from the data branch claude/okx-xperp-data at the PREREG's gate-0 commit
(`--data`, a worktree at that commit); Hyperliquid BTC/ETH daily candles and hourly funding in
experiments/llphouse_v1/raw/ (scripts/fetch_llphouse.py, sha256 in raw/manifest.json); LIT perp daily candles and
hourly funding from the same data commit (lit/). Paper only: it reads files and writes results.

usage: python scripts/run_llphouse.py --data DIR [--out DIR]
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("run_dexvault", ROOT / "scripts" / "run_dexvault.py")
dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dv)
rx = dv.rx

LANE = ROOT / "experiments" / "llphouse_v1"
RAW = LANE / "raw"
DAY = rx.DAY
HOUR = 3_600_000
# ---- the frozen rule (PREREG "Rule")
CUTOFF = "2026-11-10"            # last trade day; signal days end one day earlier
LOOKBACK = 90                    # calendar days before the signal day
MIN_PRIOR = 60                   # returns needed in the lookback
LO_Q, HI_Q = 10.0, 90.0          # percentiles (numpy linear interpolation)
MAX_SPAN = 1.5                   # a return spanning more stamps-days than this is not a signal and not in a lookback
FEE_SIDE = 0.00045               # Hyperliquid tier-0 taker, per side
SLIP_SIDE = 0.0002               # slippage, per side
COST_RT = 2 * (FEE_SIDE + SLIP_SIDE)     # 13 bp a round trip at 1x
MULTS = (1, 2, 3)
BOOKS = {"F": 1, "R": -1}
MIN_EVENTS = 30
T_MIN = 2.0
PLACEBO_N, PLACEBO_Q = 1000, 97.5
BOOT_N, BOOT_BLOCK = 10000, 2
SEED = 536
EVENT_COLS = ["asset", "day", "trade_day", "kind", "stamp_ms", "stamp_hour", "llp_ret", "p_lo", "p_hi", "n_prior",
              "open_ms", "dir_ret", "d", "move", "fund_sum"] + \
             [f"{b}_net_{m}x" for b in BOOKS for m in MULTS] + [f"{b}_fund" for b in BOOKS]


# ---------------------------------------------------------------- signal
def llp_signals(prices):
    """One row per LLP return (by the UTC day of its later stamp) with its prior-only percentile thresholds.
    `prices`: Series of share prices indexed by stamp ms (one per UTC day, as R446's llp_prices)."""
    ts, v = prices.index.to_numpy(np.int64), prices.to_numpy(float)
    rows = []
    for i in range(1, len(ts)):
        rows.append({"day": rx.day_label(ts[i]), "stamp_ms": int(ts[i]), "span": (ts[i] - ts[i - 1]) / DAY,
                     "llp_ret": v[i] / v[i - 1] - 1})
    df = pd.DataFrame(rows, columns=["day", "stamp_ms", "span", "llp_ret"])
    if not len(df):
        return df.assign(n_prior=[], p_lo=[], p_hi=[], kind=[])
    ok = df[df.span <= MAX_SPAN]
    by_day = dict(zip(ok.day, ok.llp_ret))
    n_prior, p_lo, p_hi, kind = [], [], [], []
    for d, r, span in zip(df.day, df.llp_ret, df.span):
        t0 = rx.ms(d)
        prior = [by_day[x] for x in (rx.day_label(t0 - k * DAY) for k in range(1, LOOKBACK + 1)) if x in by_day]
        n_prior.append(len(prior))
        if len(prior) >= MIN_PRIOR and span <= MAX_SPAN:
            lo, hi = float(np.percentile(prior, LO_Q)), float(np.percentile(prior, HI_Q))
            k = "loss" if r < lo else "win" if r > hi else ""
        else:
            lo, hi, k = float("nan"), float("nan"), ""
        p_lo.append(lo)
        p_hi.append(hi)
        kind.append(k)
    return df.assign(n_prior=n_prior, p_lo=p_lo, p_hi=p_hi, kind=kind)


def first_signal_day(sig):
    """The first day with LOOKBACK returns labelled before it."""
    ok = sig[sig.span <= MAX_SPAN].reset_index(drop=True)
    return ok.day.iloc[LOOKBACK] if len(ok) > LOOKBACK else None


# ---------------------------------------------------------------- prices and funding
def hl_candles(raw, coin):
    """Hyperliquid daily candles by UTC day label of the bar's open: open_ms, open, close."""
    js = json.loads((Path(raw) / "hl" / f"{coin}_candles_1d.json").read_bytes())
    df = pd.DataFrame({"open_ms": [int(x["t"]) for x in js], "open": [float(x["o"]) for x in js],
                       "close": [float(x["c"]) for x in js]})
    return frame_by_day(df)


def lit_candles(data):
    c = rx.read_dir(Path(data) / "lit" / "perp_candles_1d")
    df = pd.DataFrame({"open_ms": c.ts.astype(np.int64), "open": c.open.astype(float), "close": c.close.astype(float)})
    return frame_by_day(df)


def frame_by_day(df):
    df = df.drop_duplicates("open_ms").sort_values("open_ms")
    df.index = [rx.day_label(t) for t in df.open_ms]
    return df


def hl_funding(raw, coin):
    """Hourly rates (+ when longs pay) indexed by the settlement hour (ms, floored to the hour)."""
    rows = []
    for p in sorted((Path(raw) / "hl").glob(f"{coin}_funding_*.json")):
        rows += json.loads(p.read_bytes())
    s = pd.Series([float(x["fundingRate"]) for x in rows], index=[int(x["time"]) // HOUR * HOUR for x in rows])
    return s[~s.index.duplicated()].sort_index()


def lit_funding(data):
    f = rx.read_dir(Path(data) / "lit" / "perp_funding")
    s = pd.Series(f.rate.astype(float).to_numpy(), index=(f.ts.astype(np.int64) // HOUR * HOUR).to_numpy())
    return s[~s.index.duplicated()].sort_index()


def held_funding(fund, open_ms):
    """Sum of the rates settled while a position opened at open_ms is held for one day: hours in (open, open + 1d]."""
    i = fund.index
    return float(fund[(i > open_ms) & (i <= open_ms + DAY)].sum()), int(((i > open_ms) & (i <= open_ms + DAY)).sum())


# ---------------------------------------------------------------- trades
def trade_row(day, candles, fund):
    """The day-t+1 trade for signal day t: direction from day t's close-to-close, move from t+1's open to close.
    None if a bar is missing."""
    t0 = rx.ms(day)
    prev, nxt = rx.day_label(t0 - DAY), rx.day_label(t0 + DAY)
    if not all(x in candles.index for x in (prev, day, nxt)):
        return None
    c_prev, c_t = candles.close[prev], candles.close[day]
    o_n, c_n, open_ms = candles.open[nxt], candles.close[nxt], int(candles.open_ms[nxt])
    if open_ms != t0 + DAY:
        raise ValueError(f"{nxt}: bar opens at {open_ms}, not at the UTC day's start")
    dir_ret = c_t / c_prev - 1
    fs, hours = held_funding(fund, open_ms)
    row = {"day": day, "trade_day": nxt, "open_ms": open_ms, "dir_ret": dir_ret, "d": int(np.sign(dir_ret)),
           "move": c_n / o_n - 1, "fund_sum": fs, "fund_hours": hours}
    row.update(book_nets(row["d"], row["move"], fs))
    return row


def book_nets(d, move, fund_sum):
    """Per-book net per trade at 1x/2x/3x. Position s*d; funding: positive rate means longs pay."""
    out = {}
    for b, s in BOOKS.items():
        pos = s * d
        fpnl = -pos * fund_sum
        out[f"{b}_fund"] = fpnl
        for m in MULTS:
            out[f"{b}_net_{m}x"] = pos * move + fpnl - m * COST_RT if pos != 0 else 0.0
    return out


def build(sig, candles, fund, start, end, asset):
    """(events, pool): trades on event days, and trades on every eligible signal day (the placebo pool)."""
    pool, ev = [], []
    for r in sig[(sig.day >= start) & (sig.day <= end)].itertuples():
        if not np.isfinite(r.p_lo):
            continue
        tr = trade_row(r.day, candles, fund)
        if tr is None or tr["d"] == 0:
            continue
        if not r.stamp_ms < tr["open_ms"]:
            raise ValueError(f"{r.day}: LLP stamp {r.stamp_ms} is not before the trade's open {tr['open_ms']}")
        row = {"asset": asset, "kind": r.kind, "stamp_ms": r.stamp_ms,
               "stamp_hour": pd.Timestamp(r.stamp_ms, unit="ms", tz="UTC").hour, "llp_ret": r.llp_ret,
               "p_lo": r.p_lo, "p_hi": r.p_hi, "n_prior": r.n_prior, **tr}
        pool.append(row)
        if r.kind:
            ev.append(row)
    cols = EVENT_COLS + ["fund_hours"]
    return pd.DataFrame(ev, columns=cols), pd.DataFrame(pool, columns=cols)


# ---------------------------------------------------------------- statistics
def mean_t(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return {"n": n, "mean": float(x.mean()) if n else None, "sd": None, "t": None}
    sd = float(x.std(ddof=1))
    return {"n": n, "mean": float(x.mean()), "sd": sd, "t": float(x.mean() / (sd / np.sqrt(n))) if sd > 0 else None}


def block_bootstrap(x, block=BOOT_BLOCK, reps=BOOT_N, seed=SEED):
    """Moving-block bootstrap of the mean over events in date order: 2.5/97.5 percentiles and P(mean <= 0)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < block + 1:
        return {"lo": None, "hi": None, "p_le_0": None}
    rng = np.random.default_rng(seed)
    k = -(-n // block)
    starts = rng.integers(0, n - block + 1, size=(reps, k))
    idx = (starts[:, :, None] + np.arange(block)).reshape(reps, -1)[:, :n]
    m = x[idx].mean(axis=1)
    return {"lo": float(np.percentile(m, 2.5)), "hi": float(np.percentile(m, 97.5)), "p_le_0": float((m <= 0).mean())}


def placebo(pool_x, n, actual, reps=PLACEBO_N, seed=SEED):
    """Means of `reps` books on n days drawn without replacement from the pool; the actual mean's percentile."""
    pool_x = np.asarray(pool_x, float)
    if n == 0 or n > len(pool_x):
        return {"q975": None, "pctile": None, "pool_mean": None}
    rng = np.random.default_rng(seed)
    m = np.array([pool_x[rng.choice(len(pool_x), n, replace=False)].mean() for _ in range(reps)])
    return {"q975": float(np.percentile(m, PLACEBO_Q)), "pctile": float((m < actual).mean() * 100),
            "pool_mean": float(pool_x.mean()), "pool_n": int(len(pool_x))}


def book_report(ev, pool, b):
    out = {f"{m}x": mean_t(ev[f"{b}_net_{m}x"]) for m in MULTS}
    out["gross"] = mean_t(ev[f"{b}_net_1x"] + COST_RT)
    out["funding_mean"] = float(ev[f"{b}_fund"].mean()) if len(ev) else None
    out["bootstrap_1x"] = block_bootstrap(ev[f"{b}_net_1x"].to_numpy())
    out["placebo_1x"] = placebo(pool[f"{b}_net_1x"].to_numpy(), len(ev), out["1x"]["mean"] or 0.0)
    out["by_kind"] = {k: {f"{m}x": mean_t(ev[ev.kind == k][f"{b}_net_{m}x"]) for m in MULTS}
                      for k in ("loss", "win")}
    out["all_days_1x"] = mean_t(pool[f"{b}_net_1x"])
    return out


def decide(r):
    """EARNED when every condition of the PREREG holds, else NULL."""
    one, two, pl = r["1x"], r["2x"], r["placebo_1x"]
    ok = (one["n"] >= MIN_EVENTS and one["mean"] is not None and one["mean"] > 0 and one["t"] is not None
          and one["t"] >= T_MIN and two["mean"] is not None and two["mean"] > 0 and pl["q975"] is not None
          and one["mean"] > pl["q975"])
    return "EARNED" if ok else "NULL"


def asset_report(sig, candles, fund, start, end, asset):
    ev, pool = build(sig, candles, fund, start, end, asset)
    rep = {"asset": asset, "events": int(len(ev)), "loss_events": int((ev.kind == "loss").sum()),
           "win_events": int((ev.kind == "win").sum()), "pool_days": int(len(pool)),
           "first": ev.day.iloc[0] if len(ev) else None, "last": ev.day.iloc[-1] if len(ev) else None,
           "stamp_hours": {str(k): int(v) for k, v in ev.stamp_hour.value_counts().sort_index().items()},
           "short_funding_days": int((pool.fund_hours < 24).sum()) if len(pool) else 0,
           "books": {b: book_report(ev, pool, b) for b in BOOKS}}
    return rep, ev


# ---------------------------------------------------------------- inputs
def check_raw(raw):
    """Every body in raw/manifest.json still hashes to its recorded sha256, and no unlisted body is present."""
    man = json.loads((Path(raw) / "manifest.json").read_text())
    listed = set(man["files"])
    present = {str(p.relative_to(raw)) for p in (Path(raw) / "hl").glob("*.json")}
    if listed != present:
        raise SystemExit(f"raw/ bodies differ from the manifest: {sorted(listed ^ present)}")
    for rel, want in man["files"].items():
        got = hashlib.sha256((Path(raw) / rel).read_bytes()).hexdigest()
        if got != want:
            raise SystemExit(f"{rel}: sha256 {got} != manifest {want}")
    return hashlib.sha256((Path(raw) / "manifest.json").read_bytes()).hexdigest()


def hl_crosscheck(data, candles, coin, end):
    """Largest relative gap between the fetched closes and the recorder's hl/candles_1d closes on common days."""
    c = rx.read_dir(Path(data) / "hl" / "candles_1d")
    if not len(c):
        return None
    c = c[c.coin == coin].drop_duplicates("ts")
    c.index = [rx.day_label(t) for t in c.ts]
    common = [d for d in c.index if d in candles.index and d <= end]
    if not common:
        return None
    gap = np.abs(candles.close[common].to_numpy() / c.c[common].astype(float).to_numpy() - 1)
    return {"days": len(common), "max_rel_gap": float(gap.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="worktree of claude/okx-xperp-data at the gate-0 data commit")
    ap.add_argument("--out")
    a = ap.parse_args()
    from lab import prereg
    sha = prereg.verify(LANE / "PREREG.md")
    pinned = rx.check_inputs(LANE / "PREREG.md")
    if rx.data_head(a.data) != pinned:
        raise SystemExit(f"this lane reads the data branch at {pinned} only; {a.data} is at {rx.data_head(a.data)}")
    man_sha = check_raw(RAW)
    prices = dv.llp_prices(a.data)
    prices = prices[[rx.day_label(t) <= CUTOFF for t in prices.index]]
    sig = llp_signals(prices)
    start = first_signal_day(sig)
    end = rx.day_label(rx.ms(CUTOFF) - DAY)
    out = Path(a.out) if a.out else LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    rep = {"prereg_sha256": sha, "data_commit": pinned, "raw_manifest_sha256": man_sha, "signal_start": start,
           "signal_end": end, "llp_signals": int(((sig.day >= start) & (sig.day <= end)).sum()), "assets": {}}
    evs = []
    for coin in ("BTC", "ETH"):
        cd = hl_candles(RAW, coin)
        r, ev = asset_report(sig, cd, hl_funding(RAW, coin), start, end, coin)
        r["crosscheck_hl_candles_1d"] = hl_crosscheck(a.data, cd, coin, CUTOFF)
        rep["assets"][coin] = r
        evs.append(ev)
    r, ev = asset_report(sig, lit_candles(a.data), lit_funding(a.data), start, end, "LIT")
    rep["assets"]["LIT"] = r
    evs.append(ev)
    rep["decision"] = {b: decide(rep["assets"]["BTC"]["books"][b]) for b in BOOKS}
    pd.concat(evs, ignore_index=True).to_csv(out / "events.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    print(json.dumps({"decision": rep["decision"], "events": rep["assets"]["BTC"]["events"]}, indent=1))


if __name__ == "__main__":
    main()
