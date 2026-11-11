"""flow_hl_v1 (R448): R200's flow books on crypto perps only, traded on Hyperliquid's hourly closes and funding, as
set out in experiments/flow_hl_v1/PREREG.md. Hyperliquid takes no account and no KYC, so this is the books' execution
check on a venue the owner can reach from France. The signal is unchanged: Binance's public ratios, as R197/R200.

- gate0: the archive's flow bins (R197's cells) on 2026-04-01..2026-09-30 against Hyperliquid's candles and funding
  fetched on 2026-10-20 (data/hyperliquid, files pinned by hl_inputs.json); entry one bar late, as R214/R215. Next to
  it, the same coins and slices on Binance's prices (the venue gap) and every crypto coin on Binance (the coverage gap).
- forward: R200's live signals (experiments/flow72_fwd2/journal) from 2026-11-12; a slice enters at the first close
  after R200 computed its hour. Hyperliquid's closes and funding are fetched from the public API at run time and kept
  in journal/hl/ (one CSV a month, rows never rewritten), so the read does not depend on the API's 5,000-candle window.
  Appends one ticket per book per complete day and rewrites journal/status.json.

Paper only: public endpoints, no key, no order.

usage: python scripts/run_flow_hl.py --window gate0|forward [--status]
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import engine, prereg, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "flow_hl_v1"
J = LANE / "journal"
R200 = ROOT / "experiments" / "flow72_fwd2" / "journal"
RESEARCH = ROOT / "data" / "research"
HLDATA = ROOT / "data" / "hyperliquid"
TRADFI_JSON = ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json"
API = "https://api.hyperliquid.xyz/info"
H = 3_600_000
DAY = 24 * H
HOLD, K = 72, 9.316
UNIT = 1.0 / (HOLD * K)
CELLS = {"tvc": "flow:top_vs_crowd/xs8", "t24": "flow:taker[24]/xs8", "t4": "flow:taker[4]/xs8"}
BOOKS = {"A": ("tvc", "t24", "t4"), "B": ("tvc",)}
G0 = ("2026-04-01", "2026-10-01")          # [start, end) in UTC days
FWD_START = "2026-11-12"
ON_TIME_MIN = 60                            # docs/GATES.md: every hour of a counted day computed within 60 minutes
SCREEN_DAYS, FINAL_DAYS = 90, 365
ALPHA = 0.025                               # one-sided, per book (Bonferroni over the two books)
BLOCK, N_BOOT = 10, 20_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def day_label(t):
    return pd.Timestamp(int(t), unit="ms", tz="UTC").strftime("%Y-%m-%d")


# ---------------------------------------------------------------- pure parts (tests/test_run_flow_hl.py)
def hl_coin(symbol, coins):
    """Hyperliquid perp for a Binance USDT symbol: the base itself, else a 1000/1000000 prefix as Hyperliquid's k."""
    if not symbol.endswith("USDT"):
        return None
    base = symbol[:-4]
    if base in coins:
        return base
    for p in ("1000000", "1000"):
        if base.startswith(p) and "k" + base[len(p):] in coins:
            return "k" + base[len(p):]
    return None


def entry_lag(t, run_at_ms):
    """Rows from signal row t to the first close at or after the moment R200 wrote the hour (never less than one)."""
    e = -(-int(run_at_ms) // H) - 1                 # the bar that closes at or after run_at opens at row e
    return max(1, (e * H - int(t)) // H)


def shift_rows(ind, elig, lag):
    """Slices signalled at row t enter at t + lag[t] if the coin is tradable there (R214's construction)."""
    out = np.zeros(ind.shape, dtype=np.int64)
    T = len(ind)
    for t in np.flatnonzero(ind.any(axis=1)):
        e = t + int(lag[t])
        if e < T:
            out[e] += ind[t]
    return np.where(elig, out, 0)


def grid(frames, tt, col):
    """{name: df with t (ms) and col} onto the hour grid tt -> [T, S]; a stamp falls on the hour it starts in."""
    out = np.full((len(tt), len(frames)), np.nan)
    for j, df in enumerate(frames.values()):
        if df is None or df.empty:
            continue
        i = (df["t"].values.astype(np.int64) // H * H - tt[0]) // H
        ok = (i >= 0) & (i < len(tt))
        out[i[ok], j] = df[col].values[ok].astype(float)
    return out


def hl_returns(close, rate):
    """ret[t] = close[t+1] / close[t] - 1 less the funding a long pays at the settlement on row t + 1 (engine's rule).
    close and rate are [T + 1, S]; returns [T, S]."""
    return close[1:] / close[:-1] - 1 - np.nan_to_num(rate[1:])


def book_days(inds, cells, ret, trad, cmat, a, b, cmult):
    """Daily results over rows [a, b) of slices opened from row 0: net, gross, cost, funding-free hedge, exposure."""
    P = sum(slices.positions(inds[k], HOLD, 0, b, UNIT, -1) for k in cells)
    o = slices.run(P, ret, trad, cmat, 0, b, cmult=cmult)
    D = (b - a) // 24
    day = lambda x: np.asarray(x)[a:a + D * 24].reshape(D, 24).sum(1)
    by_coin = (P * np.nan_to_num(np.asarray(ret[:b], float)))[a:a + D * 24].reshape(D, 24, -1).sum(1)
    return {"net": day(o["net"]), "gross": day(o["gross"]), "cost": day(o["cost"]),
            "hedge": day(np.asarray(o["hedge"]) - np.asarray(o["hedge_cost"])),
            "exposure": np.asarray(o["gross_exposure"])[a:a + D * 24].reshape(D, 24).mean(1), "by_coin": by_coin}


def describe(x):
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return {"days": 0}
    eq = np.cumsum(x)
    s = np.sort(x)
    trim = s[10:-10] if n > 20 else s
    return {"days": n, "total": float(x.sum()), "mean_bp_day": float(x.mean() * 1e4),
            "ann_pct": float(x.mean() * 365 * 100), "t_nw10": float(stats.newey_west_t(x, 10)[2]) if n > 2 else None,
            "hit": float((x > 0).mean()), "worst_day": float(x.min()),
            "max_dd": float(np.max(np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq)),
            "trimmed_mean_bp_day": float(trim.mean() * 1e4)}


def leave_two_out(by_coin):
    """Mean daily gross without the two coins with the largest total gross contribution."""
    g = np.asarray(by_coin, float)
    if g.size == 0:
        return None
    keep = np.ones(g.shape[1], bool)
    keep[np.argsort(-g.sum(0))[:2]] = False
    return float(g[:, keep].sum(1).mean() * 1e4)


def boot_threshold(null_days, n, alpha=ALPHA, block=BLOCK, n_boot=N_BOOT, seed=448):
    """Upper alpha quantile of an n-day mean under the null: gate-0 days, mean removed, in blocks of `block` days."""
    x = np.asarray(null_days, float)
    x = x - x.mean()
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    starts = rng.integers(0, len(x) - block + 1, size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)[:, :n]
    return float(np.quantile(x[idx].mean(1), 1 - alpha))


# ---------------------------------------------------------------- inputs
def check_inputs(prereg_path, block_name="inputs"):
    """Every file in the named PREREG block still hashes to its frozen sha256. `inputs` holds the code (checked on every
    run); `inputs-gate0` holds the archive files, which exist only where gate 0 runs."""
    text = Path(prereg_path).read_text()
    block = re.search(r"```" + re.escape(block_name) + r"\n(.*?)```", text, re.S).group(1)
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(ROOT / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")


def check_hl_files(manifest):
    for rel, want in json.loads(Path(manifest).read_text())["files"].items():
        got = prereg.sha256_file(ROOT / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")


def hl_manifest(symbols, coins):
    """The Hyperliquid files gate 0 reads: candles_1h and funding of every coin an archive symbol maps to."""
    files = {}
    for c in sorted({hl_coin(s, coins) for s in symbols} - {None}):
        for kind in ("candles_1h", "funding"):
            p = HLDATA / kind / f"{c}.parquet"
            if p.exists():
                files[str(p.relative_to(ROOT))] = prereg.sha256_file(p)
    return {"source": "data/hyperliquid (scripts/fetch_hyperliquid_history.py, fetched 2026-10-20)", "files": files}


# ---------------------------------------------------------------- gate 0
def gate0():
    meta = json.loads((RESEARCH / "meta.json").read_text())
    syms = meta["symbols"]
    t = np.load(RESEARCH / "t.npy")
    a0, b0 = int(np.searchsorted(t, ms(G0[0]))), int(np.searchsorted(t, ms(G0[1])))
    r0 = a0 - HOLD                                   # slices opened in the 72 h before the window carry in
    T = b0 - r0
    elig = np.load(RESEARCH / "elig.npy", mmap_mode="r")[r0:b0]
    cmat = np.load(RESEARCH / "cmat.npy", mmap_mode="r")[r0:b0]
    bret = np.load(RESEARCH / "ret.npy", mmap_mode="r")[r0:b0]
    names = json.loads((RESEARCH / "meta_flow.json").read_text())["names"]
    fb = np.load(RESEARCH / "bins_flow.npy", mmap_mode="r")
    raw = {k: np.asarray(fb[names.index(c), r0:b0]) == 0 for k, c in CELLS.items()}
    tf = set(json.loads(TRADFI_JSON.read_text()))
    coins = {p.stem for p in (HLDATA / "candles_1h").glob("*.parquet")}
    mp = {s: hl_coin(s, coins) for s in syms}
    mapped = sorted({c for c in mp.values() if c})
    tt = t[r0] + np.arange(T + 1) * H
    cf = {c: pd.read_parquet(HLDATA / "candles_1h" / f"{c}.parquet", columns=["t", "close"]) for c in mapped}
    ff = {c: pd.read_parquet(HLDATA / "funding" / f"{c}.parquet", columns=["t", "rate"])
          if (HLDATA / "funding" / f"{c}.parquet").exists() else None for c in mapped}
    cg, fg = grid(cf, tt, "close"), grid(ff, tt, "rate")
    col = {c: j for j, c in enumerate(mapped)}
    S = len(syms)
    close, rate = np.full((T + 1, S), np.nan), np.full((T + 1, S), np.nan)
    for j, s in enumerate(syms):
        if mp[s]:
            close[:, j], rate[:, j] = cg[:, col[mp[s]]], fg[:, col[mp[s]]]
    hret = hl_returns(close, rate)
    crypto = np.array([s not in tf for s in syms])
    base = np.asarray(elig) & crypto[None, :]
    trad_hl = base & np.isfinite(close[:T]) & np.isfinite(close[1:])
    lag = np.ones(T, int)
    a = HOLD
    out, rows = {}, []
    for label, trad, ret in (("hl", trad_hl, hret), ("binance_same_coins", trad_hl, bret),
                             ("binance_all_crypto", base, bret)):
        inds = {k: shift_rows(raw[k] & trad, trad, lag) for k in CELLS}
        for b_name, cells in BOOKS.items():
            for cm in (1.0, 2.0, 3.0):
                r = book_days(inds, cells, ret, trad, cmat, a, T, cm)
                key = f"{label}/{b_name}/{int(cm)}x"
                out[key] = r
                d = describe(r["net"])
                if cm == 1.0:
                    d["leave_two_coins_out_gross_bp_day"] = leave_two_out(r["by_coin"])
                    n_sig = sum((raw[k] & base)[a:].sum() for k in cells)
                    n_tr = sum((raw[k] & trad)[a:].sum() for k in cells)
                    d["coverage"] = float(n_tr / max(n_sig, 1))
                rows.append({"key": key, **d})
    days = [day_label(tt[a] + i * DAY) for i in range(len(out["hl/A/1x"]["net"]))]
    daily = pd.DataFrame({"day": days})
    for b_name in BOOKS:
        for cm in (1, 2, 3):
            daily[f"{b_name}_net_{cm}x"] = out[f"hl/{b_name}/{cm}x"]["net"]
        r1 = out[f"hl/{b_name}/1x"]
        for part in ("gross", "cost", "hedge"):
            daily[f"{b_name}_{part}"] = r1[part]
        daily[f"{b_name}_bin_same"] = out[f"binance_same_coins/{b_name}/1x"]["net"]
        daily[f"{b_name}_bin_all"] = out[f"binance_all_crypto/{b_name}/1x"]["net"]
    fund = {}
    for b_name, cells in BOOKS.items():
        inds = {k: shift_rows(raw[k] & trad_hl, trad_hl, lag) for k in CELLS}
        P = sum(slices.positions(inds[k], HOLD, 0, T, UNIT, -1) for k in cells)
        fund[b_name] = float(-(P * np.nan_to_num(rate[1:T + 1]))[a:].sum())
    contrib = []
    for b_name in BOOKS:
        g = out[f"hl/{b_name}/1x"]["by_coin"].sum(0)
        for j in np.argsort(-np.abs(g))[:10]:
            contrib.append({"book": b_name, "symbol": syms[j], "hl_coin": mp[syms[j]], "gross_total": float(g[j])})
    rep = {"window": f"{G0[0]}..{day_label(ms(G0[1]) - DAY)}", "rows": rows, "funding_received_total": fund,
           "mapped_symbols": int(sum(1 for s in syms if mp[s])), "eligible_crypto_symbols_in_window":
           int((base[a:].any(0)).sum()), "eligible_crypto_mapped": int((base[a:].any(0) & np.array(
               [bool(mp[s]) for s in syms])).sum()),
           "unmapped_eligible": sorted(s for j, s in enumerate(syms) if base[a:, j].any() and not mp[s]),
           "top_contributors": contrib}
    for b_name in BOOKS:
        hl1 = next(r for r in rows if r["key"] == f"hl/{b_name}/1x")
        rep[f"decision_{b_name}"] = "CONTINUE to gate 1" if hl1["mean_bp_day"] > 0 else "NULL (stop)"
        x, y = daily[f"{b_name}_net_1x"].values, daily[f"{b_name}_bin_same"].values
        rep[f"corr_hl_vs_binance_same_{b_name}"] = float(np.corrcoef(x, y)[0, 1])
    return daily, rep


# ---------------------------------------------------------------- forward
def post(body, tries=5):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(API, json.dumps(body).encode(),
                                         {"Content-Type": "application/json", "User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:      # noqa: BLE001 - retried, then raised
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"hyperliquid {body.get('type')}: {err}")


def fetch_hl(coin, start, end):
    """Closed hourly candles and funding settlements of one coin over [start, end)."""
    c = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": int(start),
                                                "endTime": int(end)}})
    rows = [(int(k["t"]), float(k["c"])) for k in c if int(k["t"]) + H <= end]
    f, s = [], int(start)
    while s < end:
        page = post({"type": "fundingHistory", "coin": coin, "startTime": s, "endTime": int(end)})
        if not page:
            break
        f += [(int(x["time"]) // H * H, float(x["fundingRate"])) for x in page]
        s = int(page[-1]["time"]) + 1
        if len(page) < 500:
            break
        time.sleep(0.3)
    fr = dict(f)
    return [(t_, coin, cl, fr.get(t_, np.nan)) for t_, cl in rows]


def hl_store_read():
    files = sorted((J / "hl").glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=["t", "coin", "close", "rate"])
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True)


def hl_store_add(rows):
    """Append rows whose (t, coin) is new to journal/hl/<month>.csv; stored rows are never rewritten."""
    old = hl_store_read()
    have = set(zip(old.t.astype(np.int64), old.coin)) if len(old) else set()
    new = pd.DataFrame([r for r in rows if (r[0], r[1]) not in have], columns=["t", "coin", "close", "rate"])
    if new.empty:
        return 0
    (J / "hl").mkdir(parents=True, exist_ok=True)
    new["month"] = [day_label(x)[:7] for x in new.t]
    for m, g in new.sort_values(["t", "coin"]).groupby("month"):
        p = J / "hl" / f"{m}.csv"
        g.drop(columns="month").to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
    return len(new)


def forward(status_only=False):
    sig = pd.read_csv(R200 / "signals.csv")
    ticks = pd.read_csv(R200 / "ticks.csv")
    t0 = ms(FWD_START)
    sig, ticks = sig[sig.t >= t0], ticks[ticks.t >= t0]
    if ticks.empty:
        log("no R200 hour on or after", FWD_START)
        return None
    last = int(ticks.t.max())
    T = (last - t0) // H + 1
    syms = sorted(sig.symbol.unique())
    tf = set(json.loads(TRADFI_JSON.read_text()))
    meta = post({"type": "meta"})
    coins = {u["name"] for u in meta["universe"]}
    mp = {s: (None if s in tf else hl_coin(s, coins)) for s in syms}
    mapped = sorted({c for c in mp.values() if c})
    now = int(time.time() * 1000) // H * H
    end = min(last + 2 * H, now)
    if not status_only:
        store = hl_store_read()
        got = []
        for c in mapped:
            done = store[store.coin == c].t.max() if len(store) else np.nan
            start = max(t0, int(done) + H) if np.isfinite(done) else t0
            if start < end:
                got += fetch_hl(c, start, end)
                time.sleep(0.3)
        log("hl rows added", hl_store_add(got))
    store = hl_store_read()
    tt = t0 + np.arange(T + 1) * H
    fr = {c: g[["t", "close", "rate"]] for c, g in store.groupby("coin")}
    cg, fg = grid({c: fr.get(c) for c in mapped}, tt, "close"), grid({c: fr.get(c) for c in mapped}, tt, "rate")
    col = {c: j for j, c in enumerate(mapped)}
    S = len(syms)
    close, rate = np.full((T + 1, S), np.nan), np.full((T + 1, S), np.nan)
    for j, s in enumerate(syms):
        if mp[s]:
            close[:, j], rate[:, j] = cg[:, col[mp[s]]], fg[:, col[mp[s]]]
    ret = hl_returns(close, rate)
    scol = {s: j for j, s in enumerate(syms)}
    ri, ci = ((sig.t.values - t0) // H).astype(int), sig.symbol.map(scol).values
    elig = np.zeros((T, S), bool)
    elig[ri, ci] = True
    rank = np.full((T, S), np.nan)
    rank[ri, ci] = sig["rank"].values
    cmat = engine.cost_matrix(rank)
    crypto = np.array([mp[s] is not None for s in syms])
    trad = elig & crypto[None, :] & np.isfinite(close[:T])
    run_ms = (pd.to_datetime(ticks.run_at, utc=True) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    run_at = dict(zip(ticks.t.astype(np.int64), run_ms.astype(np.int64)))
    lag = np.array([entry_lag(t0 + i * H, run_at.get(t0 + i * H, t0 + (i + 1) * H)) for i in range(T)])
    late_min = np.array([(run_at.get(t0 + i * H, np.inf) - (t0 + (i + 1) * H)) / 60_000 for i in range(T)])
    inds = {}
    for k in CELLS:
        x = np.zeros((T, S), bool)
        x[ri, ci] = sig[k].values == 0
        inds[k] = shift_rows(x & trad, trad, lag)
    known = np.isfinite(close[1:]).any(axis=1)
    D = (int(np.flatnonzero(known).max()) + 1 if known.any() else 0) // 24
    have = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame()
    done = set(zip(have.day, have.book)) if len(have) else set()
    rows, coin_rows = [], []
    for b_name, cells in BOOKS.items():
        res = {cm: book_days(inds, cells, ret, trad, cmat, 0, D * 24, cm) for cm in (1.0, 2.0, 3.0)}
        P = sum(slices.positions(inds[k], HOLD, 0, D * 24, UNIT, -1) for k in cells)
        fund = -(P * np.nan_to_num(rate[1:D * 24 + 1])).reshape(D, 24, S).sum((1, 2)) if D else []
        for d in range(D):
            day = day_label(t0 + d * DAY)
            if (day, b_name) in done or status_only:
                continue
            h = slice(d * 24, d * 24 + 24)
            rows.append({"day": day, "book": b_name, "net": res[1.0]["net"][d], "gross": res[1.0]["gross"][d],
                         "cost": res[1.0]["cost"][d], "funding": float(fund[d]), "hedge": res[1.0]["hedge"][d],
                         "net_2x": res[2.0]["net"][d], "net_3x": res[3.0]["net"][d],
                         "gross_exposure": res[1.0]["exposure"][d],
                         "max_late_min": float(np.max(late_min[h])),
                         "kind": "ontime" if np.max(late_min[h]) <= ON_TIME_MIN else "late"})
            for j in np.flatnonzero(res[1.0]["by_coin"][d] != 0):
                coin_rows.append({"day": day, "book": b_name, "symbol": syms[j], "gross": res[1.0]["by_coin"][d, j]})
    J.mkdir(parents=True, exist_ok=True)
    if rows:
        p = J / "tickets.csv"
        pd.DataFrame(rows).to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
    if coin_rows:
        p = J / "coins.csv"
        pd.DataFrame(coin_rows).to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
    return status(D, last, mapped, [s for s in syms if not mp[s]])


def read_decision(tk, coins, b_name, null_days):
    """The frozen looks on a book's strict on-time days (in calendar order)."""
    on = tk[(tk.book == b_name) & (tk.kind == "ontime")].sort_values("day")
    s = describe(on.net.values)
    s["mean_2x_bp_day"] = float(on.net_2x.mean() * 1e4) if len(on) else None
    cb = coins[(coins.book == b_name) & coins.day.isin(on.day)]
    if len(cb):
        piv = cb.pivot_table(index="day", columns="symbol", values="gross", aggfunc="sum").fillna(0.0)
        s["leave_two_coins_out_gross_bp_day"] = leave_two_out(piv.values)
    n = len(on)
    if n >= FINAL_DAYS:
        x = on.net.values[:FINAL_DAYS]
        thr = boot_threshold(null_days, FINAL_DAYS)
        ok = x.mean() > thr and on.net_2x.values[:FINAL_DAYS].mean() > 0 and describe(x)["trimmed_mean_bp_day"] > 0
        s["decision"] = ("PASS" if ok else "NULL") + f" at {FINAL_DAYS} days (threshold {thr * 1e4:.1f} bp/day)"
    elif n >= SCREEN_DAYS:
        x = on.net.values[:SCREEN_DAYS]
        s["decision"] = ("SURVIVES the futility screen" if x.mean() > 0 else "NULL (futility)") + \
            f" at {SCREEN_DAYS} days; final read at {FINAL_DAYS}"
    else:
        s["decision"] = f"pending ({n} strict on-time days of {SCREEN_DAYS})"
    eq = np.cumsum(tk[tk.book == b_name].sort_values("day").net.values)
    s["stop_rule_hit"] = bool(len(eq) and np.max(np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq) >= 0.5)
    return s


def status(D, last, mapped, unmapped):
    cols = ["day", "book", "net", "net_2x", "net_3x", "kind"]
    tk = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame(columns=cols)
    coins = pd.read_csv(J / "coins.csv") if (J / "coins.csv").exists() else pd.DataFrame(
        columns=["day", "book", "symbol", "gross"])
    g0 = pd.read_csv(LANE / "results" / "gate0" / "daily.csv")
    st = {"last_r200_hour": pd.Timestamp(last, unit="ms", tz="UTC").isoformat(), "complete_days": int(D),
          "hl_coins": mapped, "unmapped_symbols": unmapped}
    for b_name in BOOKS:
        st[b_name] = read_decision(tk, coins, b_name, g0[f"{b_name}_net_1x"].values)
        st[b_name]["all_days"] = describe(tk[tk.book == b_name].net.values if len(tk) else [])
    (J / "status.json").write_text(json.dumps(st, indent=1, default=float) + "\n")
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=("gate0", "forward"), required=True)
    ap.add_argument("--status", action="store_true", help="forward: rewrite status.json from the journal, no fetch")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs(LANE / "PREREG.md")
    if a.window == "gate0":
        check_inputs(LANE / "PREREG.md", "inputs-gate0")
        check_hl_files(LANE / "hl_inputs.json")
        daily, rep = gate0()
        out = LANE / "results" / "gate0"
        out.mkdir(parents=True, exist_ok=True)
        daily.to_csv(out / "daily.csv", index=False, lineterminator="\n")
        (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
        for r in rep["rows"]:
            log(r["key"], {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "key"})
        log({k: v for k, v in rep.items() if k.startswith(("decision", "corr", "funding", "mapped", "eligible"))})
    else:
        st = forward(a.status)
        if st:
            log({b: (st[b]["decision"], st[b]["all_days"].get("days"), round(st[b]["all_days"].get("total", 0), 4))
                 for b in BOOKS})


if __name__ == "__main__":
    main()
