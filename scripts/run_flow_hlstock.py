"""flow_hlstock_v1 (R451): R200's flow books on stock, index and commodity perps only, traded on Hyperliquid's xyz
markets (HIP-3, builder-deployed perps), as set out in experiments/flow_hlstock_v1/PREREG.md.

R216 found that R200's forward gain came mostly from Binance's TradFi perps, and R448 that the crypto part is small on
Hyperliquid. This lane is the France-reachable execution check of the TradFi part: the same signals (R200's journal),
the same slices, hedge and tier costs as R448 (its frozen functions are imported), with three changes:
- the universe is R216's TradFi symbols that map to an xyz coin (the base, or one of five fixed aliases);
- prices and funding are xyz's (`xyz:<COIN>` in Hyperliquid's public candleSnapshot and fundingHistory);
- each one-way cost is at least FEE_FLOOR, Hyperliquid's base taker fee doubled for builder-deployed markets.

- gate0: R200's journal rows of 2026-10-01..2026-11-10 (copied to data/) against xyz prices fetched before the
  freeze (data/, pinned by hash);
  entry one bar late. Next to it, Binance's closes from R200's journal on the same coins and on every TradFi symbol.
- forward: from 2026-11-12, the entry and the strict on-time days of R448.

Paper only: public endpoints, no key, no order.

usage: python scripts/run_flow_hlstock.py --window fetch|gate0|forward [--status]
"""
import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import engine, prereg, slices  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_flow_hl", ROOT / "scripts" / "run_flow_hl.py")
fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fh)

LANE = ROOT / "experiments" / "flow_hlstock_v1"
DATA = LANE / "data"
J = LANE / "journal"
R200 = ROOT / "experiments" / "flow72_fwd2" / "journal"
TRADFI_JSON = ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json"
H, DAY, HOLD = fh.H, fh.DAY, fh.HOLD
CELLS, BOOKS = fh.CELLS, fh.BOOKS
DEX = "xyz"
ALIAS = {"XAU": "GOLD", "XAG": "SILVER", "BZ": "BRENTOIL", "SPY": "SP500", "SAMSUNG": "SMSN"}
FEE_FLOOR = 9e-4                            # one way: 4.5 bp base taker x 2 on builder-deployed markets
G0 = ("2026-10-01", "2026-11-11")           # [start, end) in UTC days
FWD_START = fh.FWD_START                    # 2026-11-12
ON_TIME_MIN = fh.ON_TIME_MIN
log = fh.log
ms, day_label = fh.ms, fh.day_label


# ---------------------------------------------------------------- pure parts (tests/test_run_flow_hlstock.py)
def xyz_coin(symbol, coins):
    """xyz coin for a Binance USDT TradFi symbol: `xyz:<base>`, or `xyz:<alias>` for the five fixed aliases."""
    if not symbol.endswith("USDT"):
        return None
    base = symbol[:-4]
    c = f"{DEX}:{ALIAS.get(base, base)}"
    return c if c in coins else None


def floor_costs(cmat):
    """The lab's tier cost by Binance rank, never below FEE_FLOOR; NaN (no rank) stays NaN."""
    c = np.asarray(cmat, float)
    return np.where(np.isfinite(c), np.maximum(c, FEE_FLOOR), c)


def journal_grid(sig, syms, t0, T):
    """R200's signal rows onto the hour grid [t0, t0 + T h): eligibility, rank, Binance close and the three cells'
    bin-0 flags, each [T, S]."""
    col = {s: j for j, s in enumerate(syms)}
    sig = sig[(sig.t >= t0) & (sig.t < t0 + T * H) & sig.symbol.isin(col)]
    ri, ci = ((sig.t.values - t0) // H).astype(int), sig.symbol.map(col).values
    S = len(syms)
    elig = np.zeros((T, S), bool)
    elig[ri, ci] = True
    rank, bclose = np.full((T, S), np.nan), np.full((T, S), np.nan)
    rank[ri, ci] = sig["rank"].values
    bclose[ri, ci] = sig["close"].values
    raw = {}
    for k in CELLS:
        x = np.zeros((T, S), bool)
        x[ri, ci] = sig[k].values == 0
        raw[k] = x
    return elig, rank, bclose, raw


def binance_returns(bclose):
    """ret[t] = close[t + 1] / close[t] - 1 from R200's hourly Binance closes (no funding: the journal has none)."""
    r = np.full(bclose.shape, np.nan)
    r[:-1] = bclose[1:] / bclose[:-1] - 1
    return r


# ---------------------------------------------------------------- data
def xyz_coins():
    meta = fh.post({"type": "meta", "dex": DEX})
    return {u["name"] for u in meta["universe"] if not u.get("isDelisted")}


def fetch_gate0():
    """xyz candles and funding of every mapped TradFi symbol in R200's gate-0 journal, and that journal's gate-0 rows;
    files only, no return."""
    sig = pd.read_csv(R200 / "signals.csv")
    sig = sig[(sig.t >= ms(G0[0])) & (sig.t < ms(G0[1]))]
    tf = set(json.loads(TRADFI_JSON.read_text()))
    coins = xyz_coins()
    syms = sorted(s for s in sig.symbol.unique() if s in tf)
    mp = {s: xyz_coin(s, coins) for s in syms}
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "xyz_coins.json").write_text(json.dumps(sorted(coins), indent=0) + "\n")
    sig.to_csv(DATA / "r200_signals.csv", index=False, lineterminator="\n")
    a, b = ms(G0[0]) - DAY, ms(G0[1]) + H           # the last candle read opens at G0's end and has closed
    for c in sorted({c for c in mp.values() if c}):
        rows = fh.fetch_hl(c, a, b)
        pd.DataFrame(rows, columns=["t", "coin", "close", "rate"]).to_csv(
            DATA / f"{c.replace(':', '_')}.csv", index=False, lineterminator="\n")
        log(c, len(rows), "hours")
        time.sleep(0.3)
    log("mapped", {s: mp[s] for s in syms})


def read_prices(coins, src):
    """{coin: DataFrame(t, close, rate)} from gate-0 files (src=DATA) or the forward journal (src=None)."""
    if src is not None:
        out = {}
        for c in coins:
            p = src / f"{c.replace(':', '_')}.csv"
            out[c] = pd.read_csv(p) if p.exists() else None
        return out
    store = hl_store_read()
    return {c: g[["t", "close", "rate"]] for c, g in store.groupby("coin")} if len(store) else {}


def check_inputs(block_name):
    text = (LANE / "PREREG.md").read_text()
    block = re.search(r"```" + re.escape(block_name) + r"\n(.*?)```", text, re.S).group(1)
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(ROOT / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")


# ---------------------------------------------------------------- gate 0
def gate0():
    sig = pd.read_csv(DATA / "r200_signals.csv")
    tf = set(json.loads(TRADFI_JSON.read_text()))
    coins = set(json.loads((DATA / "xyz_coins.json").read_text()))
    syms = sorted(s for s in sig.symbol.unique() if s in tf)
    mp = {s: xyz_coin(s, coins) for s in syms}
    mapped = sorted({c for c in mp.values() if c})
    t0 = ms(G0[0])
    T = (ms(G0[1]) - t0) // H
    elig, rank, bclose, raw = journal_grid(sig, syms, t0, T + 1)
    elig, rank, raw = elig[:T], rank[:T], {k: v[:T] for k, v in raw.items()}
    tt = t0 + np.arange(T + 1) * H
    pr = read_prices(mapped, DATA)
    cg, fg = fh.grid(pr, tt, "close"), fh.grid(pr, tt, "rate")
    col = {c: j for j, c in enumerate(mapped)}
    S = len(syms)
    close, rate = np.full((T + 1, S), np.nan), np.full((T + 1, S), np.nan)
    for j, s in enumerate(syms):
        if mp[s]:
            close[:, j], rate[:, j] = cg[:, col[mp[s]]], fg[:, col[mp[s]]]
    hret = fh.hl_returns(close, rate)
    bret = binance_returns(bclose)[:T]
    cmat = floor_costs(engine.cost_matrix(rank))
    is_mapped = np.array([mp[s] is not None for s in syms])
    trad_hl = elig & is_mapped[None, :] & np.isfinite(close[:T]) & np.isfinite(close[1:])
    trad_ball = elig & np.isfinite(bclose[:T]) & np.isfinite(np.r_[bclose[1:T + 1]])
    lag = np.ones(T, int)
    out, rows = {}, []
    for lab_, trad, ret in (("xyz", trad_hl, hret), ("binance_same_coins", trad_hl, bret),
                            ("binance_all_tradfi", trad_ball, bret)):
        inds = {k: fh.shift_rows(raw[k] & trad, trad, lag) for k in CELLS}
        for b_name, cells in BOOKS.items():
            for cm in (1.0, 2.0, 3.0):
                r = fh.book_days(inds, cells, ret, trad, cmat, 0, T, cm)
                key = f"{lab_}/{b_name}/{int(cm)}x"
                out[key] = r
                d = fh.describe(r["net"])
                if cm == 1.0:
                    d["leave_two_coins_out_gross_bp_day"] = fh.leave_two_out(r["by_coin"])
                    n_sig = sum((raw[k] & elig)[:T].sum() for k in cells)
                    n_tr = sum((raw[k] & trad).sum() for k in cells)
                    d["coverage"] = float(n_tr / max(n_sig, 1))
                rows.append({"key": key, **d})
    days = [day_label(t0 + i * DAY) for i in range(len(out["xyz/A/1x"]["net"]))]
    daily = pd.DataFrame({"day": days})
    for b_name in BOOKS:
        for cm in (1, 2, 3):
            daily[f"{b_name}_net_{cm}x"] = out[f"xyz/{b_name}/{cm}x"]["net"]
        r1 = out[f"xyz/{b_name}/1x"]
        for part in ("gross", "cost", "hedge"):
            daily[f"{b_name}_{part}"] = r1[part]
        daily[f"{b_name}_bin_same"] = out[f"binance_same_coins/{b_name}/1x"]["net"]
        daily[f"{b_name}_bin_all"] = out[f"binance_all_tradfi/{b_name}/1x"]["net"]
    fund, contrib = {}, []
    for b_name, cells in BOOKS.items():
        inds = {k: fh.shift_rows(raw[k] & trad_hl, trad_hl, lag) for k in CELLS}
        P = sum(slices.positions(inds[k], HOLD, 0, T, fh.UNIT, -1) for k in cells)
        fund[b_name] = float(-(P * np.nan_to_num(rate[1:T + 1])).sum())
        g = out[f"xyz/{b_name}/1x"]["by_coin"].sum(0)
        for j in np.argsort(-np.abs(g))[:10]:
            contrib.append({"book": b_name, "symbol": syms[j], "xyz_coin": mp[syms[j]], "gross_total": float(g[j])})
    rep = {"window": f"{G0[0]}..{day_label(ms(G0[1]) - DAY)}", "rows": rows, "funding_received_total": fund,
           "tradfi_symbols": syms, "mapping": mp, "unmapped": [s for s in syms if not mp[s]],
           "top_contributors": contrib}
    for b_name in BOOKS:
        x1 = next(r for r in rows if r["key"] == f"xyz/{b_name}/1x")
        rep[f"decision_{b_name}"] = "CONTINUE to gate 1" if x1["mean_bp_day"] > 0 else "NULL (stop)"
        x, y = daily[f"{b_name}_net_1x"].values, daily[f"{b_name}_bin_same"].values
        rep[f"corr_xyz_vs_binance_same_{b_name}"] = float(np.corrcoef(x, y)[0, 1]) if x.std() and y.std() else None
    return daily, rep


# ---------------------------------------------------------------- forward
def hl_store_read():
    files = sorted((J / "hl").glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=["t", "coin", "close", "rate"])
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def hl_store_add(rows):
    """Append closed hours not stored yet, one CSV a month; stored rows are never rewritten."""
    if not rows:
        return 0
    df = pd.DataFrame(rows, columns=["t", "coin", "close", "rate"])
    have = hl_store_read()
    if len(have):
        key = set(zip(have.t.astype(np.int64), have.coin))
        df = df[[(int(t), c) not in key for t, c in zip(df.t, df.coin)]]
    if df.empty:
        return 0
    (J / "hl").mkdir(parents=True, exist_ok=True)
    df["month"] = pd.to_datetime(df.t, unit="ms", utc=True).dt.strftime("%Y-%m")
    for m, g in df.groupby("month"):
        p = J / "hl" / f"{m}.csv"
        g.drop(columns="month").to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
    return len(df)


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
    tf = set(json.loads(TRADFI_JSON.read_text()))
    syms = sorted(s for s in sig.symbol.unique() if s in tf)
    coins = xyz_coins()
    mp = {s: xyz_coin(s, coins) for s in syms}
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
                got += fh.fetch_hl(c, start, end)
                time.sleep(0.3)
        log("xyz rows added", hl_store_add(got))
    tt = t0 + np.arange(T + 1) * H
    pr = read_prices(mapped, None)
    cg, fg = fh.grid({c: pr.get(c) for c in mapped}, tt, "close"), fh.grid({c: pr.get(c) for c in mapped}, tt, "rate")
    col = {c: j for j, c in enumerate(mapped)}
    S = len(syms)
    close, rate = np.full((T + 1, S), np.nan), np.full((T + 1, S), np.nan)
    for j, s in enumerate(syms):
        if mp[s]:
            close[:, j], rate[:, j] = cg[:, col[mp[s]]], fg[:, col[mp[s]]]
    ret = fh.hl_returns(close, rate)
    elig, rank, _, raw = journal_grid(sig, syms, t0, T)
    cmat = floor_costs(engine.cost_matrix(rank))
    is_mapped = np.array([mp[s] is not None for s in syms])
    trad = elig & is_mapped[None, :] & np.isfinite(close[:T])
    run_ms = (pd.to_datetime(ticks.run_at, utc=True) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    run_at = dict(zip(ticks.t.astype(np.int64), run_ms.astype(np.int64)))
    lag = np.array([fh.entry_lag(t0 + i * H, run_at.get(t0 + i * H, t0 + (i + 1) * H)) for i in range(T)])
    late_min = np.array([(run_at.get(t0 + i * H, np.inf) - (t0 + (i + 1) * H)) / 60_000 for i in range(T)])
    inds = {k: fh.shift_rows(raw[k] & trad, trad, lag) for k in CELLS}
    known = np.isfinite(close[1:]).any(axis=1)
    D = (int(np.flatnonzero(known).max()) + 1 if known.any() else 0) // 24
    have = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame()
    done = set(zip(have.day, have.book)) if len(have) else set()
    rows, coin_rows = [], []
    for b_name, cells in BOOKS.items():
        res = {cm: fh.book_days(inds, cells, ret, trad, cmat, 0, D * 24, cm) for cm in (1.0, 2.0, 3.0)}
        P = sum(slices.positions(inds[k], HOLD, 0, D * 24, fh.UNIT, -1) for k in cells)
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


def status(D, last, mapped, unmapped):
    cols = ["day", "book", "net", "net_2x", "net_3x", "kind"]
    tk = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame(columns=cols)
    coins = pd.read_csv(J / "coins.csv") if (J / "coins.csv").exists() else pd.DataFrame(
        columns=["day", "book", "symbol", "gross"])
    g0 = pd.read_csv(LANE / "results" / "gate0" / "daily.csv")
    st = {"last_r200_hour": pd.Timestamp(last, unit="ms", tz="UTC").isoformat(), "complete_days": int(D),
          "xyz_coins": mapped, "unmapped_symbols": unmapped}
    for b_name in BOOKS:
        st[b_name] = fh.read_decision(tk, coins, b_name, g0[f"{b_name}_net_1x"].values)
        st[b_name]["all_days"] = fh.describe(tk[tk.book == b_name].net.values if len(tk) else [])
    (J / "status.json").write_text(json.dumps(st, indent=1, default=float) + "\n")
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=("fetch", "gate0", "forward"), required=True)
    ap.add_argument("--status", action="store_true", help="forward: rewrite status.json from the journal, no fetch")
    a = ap.parse_args()
    if a.window == "fetch":
        if (LANE / "PREREG.sha256").exists():
            raise SystemExit("frozen: gate-0 data are fixed")
        fetch_gate0()
        return
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs("inputs")
    if a.window == "gate0":
        check_inputs("inputs-gate0")
        daily, rep = gate0()
        out = LANE / "results" / "gate0"
        out.mkdir(parents=True, exist_ok=True)
        daily.to_csv(out / "daily.csv", index=False, lineterminator="\n")
        (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
        for r in rep["rows"]:
            log(r["key"], {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "key"})
        log({k: v for k, v in rep.items() if k.startswith(("decision", "corr", "funding", "unmapped"))})
    else:
        st = forward(a.status)
        if st:
            log({b: (st[b]["decision"], st[b]["all_days"].get("days"), round(st[b]["all_days"].get("total", 0), 4))
                 for b in BOOKS})


if __name__ == "__main__":
    main()
