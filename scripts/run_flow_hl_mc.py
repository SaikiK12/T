"""flow_hl_mc_v1 (R458): R448's books (R200's flow signals on Hyperliquid's main-dex crypto perps) re-priced at
measured costs, as set out in experiments/flow_hl_mc_v1/PREREG.md.

R448 charges each one-way trade the lab's tier cost by Binance liquidity rank (6, 8, 12 or 20 bp). A funded account
on Hyperliquid pays the venue's tier-0 taker fee (4.5 bp) plus what a market order walks through the book. This lane
recomputes R448's positions unchanged and replaces only the cost of each coin-hour by
  4.5 bp + slippage (the mean of the buy and sell cost of a $1k market order in the hourly main-dex snapshot nearest
  the trade, scripts/record_xyz_books.py --dex ""),
falling back to R448's own cost where no snapshot is within 90 minutes. It adds no chance to pass: a book is only
"executable at measured costs" if R448 itself passes.

Reads (no fetch, no order): R200's journal, R448's journal (tickets and its Hyperliquid price store) and a checkout of
the data branch claude/xyz-books-data (main/books/).

usage: python scripts/run_flow_hl_mc.py --snapshots DIR [--out DIR]
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import engine, prereg, slices  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fh = _load("run_flow_hl")            # R448: its books, grid, returns, store and decision, unchanged
mc = _load("run_flow_hlstock_mc")    # R453: nearest_slip (the snapshot matcher) and git_head

LANE = ROOT / "experiments" / "flow_hl_mc_v1"
H, DAY, HOLD = fh.H, fh.DAY, fh.HOLD
# ---- the frozen rule (PREREG "Rule"); tests/test_run_flow_hl_mc.py checks these against the PREREG text
TAKER = 4.5e-4                       # Hyperliquid's tier-0 perp taker fee on the main dex, one way
SIZE_USD = 1_000                     # the snapshot cost level used for slippage (primary)
SIZES = (1_000, 5_000, 10_000)       # reported
MAX_GAP_MIN = 90                     # a snapshot farther than this from the trade is not used
SNAP_DIR = "main/books"
log = fh.log


# ---------------------------------------------------------------- pure parts
def measured_costs(assumed, coins, t0, books, size=SIZE_USD, fee=TAKER, max_gap_min=MAX_GAP_MIN):
    """[T, S] one-way costs: fee + measured slippage where a snapshot is near the trade, R448's cost elsewhere.
    `coins[j]` is column j's Hyperliquid coin (None if unmapped). Row i's trades execute at the close of the bar
    opening at t0 + i * H (fh.grid, fh.hl_returns), so the target time is t0 + (i + 1) * H. A coin-hour without an
    R448 cost stays out. Returns (costs, measured mask)."""
    a = np.asarray(assumed, float)
    T = a.shape[0]
    targets = t0 + (np.arange(T) + 1) * H
    out, meas = a.copy(), np.zeros(a.shape, bool)
    col_b, col_s = f"buy_{size}_bp", f"sell_{size}_bp"
    for j, c in enumerate(coins):
        if not c or not len(books):
            continue
        g = books[books.coin == c].sort_values("ts")
        if not len(g) or col_b not in g or col_s not in g:
            continue
        slip = (pd.to_numeric(g[col_b], errors="coerce") + pd.to_numeric(g[col_s], errors="coerce")) / 2 / 1e4
        sl = mc.nearest_slip(g.ts.to_numpy(np.int64), slip.to_numpy(float), targets, max_gap_min * 60_000)
        ok = np.isfinite(sl) & np.isfinite(a[:, j])
        out[ok, j] = fee + np.maximum(sl[ok], 0.0)
        meas[ok, j] = True
    return out, meas


def traded_mask(inds, cells, b):
    """[b, S] coin-hours where the book's main-leg position changes (where a cost is paid)."""
    P = sum(slices.positions(inds[k], HOLD, 0, b, fh.UNIT, -1) for k in cells)
    return np.diff(np.vstack([np.zeros((1, P.shape[1])), P]), axis=0) != 0


def cost_summary(traded, meas, assumed, measured):
    """Share of traded coin-hours priced from a snapshot, and the mean one-way cost on those, assumed and measured."""
    n = int(traded.sum())
    both = traded & meas
    k = int(both.sum())
    return {"traded_coin_hours": n, "traded_share_measured": float(k / n) if n else None,
            "assumed_cost_bp": float(np.asarray(assumed)[both].mean() * 1e4) if k else None,
            "measured_cost_bp": float(np.asarray(measured)[both].mean() * 1e4) if k else None}


def decide(df, tk, b_name, null_days):
    """The frozen reads on R448's strict on-time days, in calendar order. R448's own decision is fh.read_decision on
    its tickets, as R448's status() computes it."""
    on = df[df.kind == "ontime"].sort_values("day")
    m = on[f"meas_{SIZE_USD}_1x"].to_numpy(float)
    gap = m - on.assumed_1x.to_numpy(float)
    s = {"ontime_days": int(len(on)), "measured_1x_bp_day": float(m.mean() * 1e4) if len(m) else None,
         "assumed_1x_bp_day": float(on.assumed_1x.mean() * 1e4) if len(on) else None,
         "gap_bp_day": float(gap.mean() * 1e4) if len(gap) else None}
    for n in SIZES:
        for k in (1, 2, 3):
            c = f"meas_{n}_{k}x"
            s[f"{c}_bp_day"] = float(on[c].mean() * 1e4) if len(on) else None
    n = len(on)
    if n >= fh.FINAL_DAYS:
        x = m[:fh.FINAL_DAYS]
        r = fh.read_decision(tk, pd.DataFrame(columns=["day", "book", "symbol", "gross"]), b_name, null_days)
        thr = fh.boot_threshold(null_days, fh.FINAL_DAYS)
        ok = (x.mean() > thr and on[f"meas_{SIZE_USD}_2x"].to_numpy(float)[:fh.FINAL_DAYS].mean() > 0
              and fh.describe(x)["trimmed_mean_bp_day"] > 0)
        if not str(r["decision"]).startswith("PASS") or r["stop_rule_hit"]:
            s["decision"] = f"n/a: R448 did not pass ({r['decision']}; stop rule hit {r['stop_rule_hit']})"
        else:
            s["decision"] = ("EXECUTABLE AT MEASURED COSTS" if ok else "NOT EXECUTABLE AT MEASURED COSTS") + \
                f" (threshold {thr * 1e4:.1f} bp/day)"
    elif n >= fh.SCREEN_DAYS:
        g = gap[:fh.SCREEN_DAYS].mean()
        s["decision"] = ("NO WORSE THAN ASSUMED" if g >= 0 else "COSTLIER THAN ASSUMED") + \
            f" at {fh.SCREEN_DAYS} days ({g * 1e4:+.2f} bp/day)"
    else:
        s["decision"] = f"pending ({n} strict on-time days of {fh.SCREEN_DAYS})"
    return s


# ---------------------------------------------------------------- R448's state, recomputed without fetching
def assemble(r200=None, store=None):
    """R448's forward() computation without fetching: R200's signals and ticks and R448's stored Hyperliquid closes
    and funding. Coins are those in the store (R448 maps with the live meta; a coin it mapped but never stored has no
    close, so it is untradable either way; the parity check below catches any other difference)."""
    r200 = Path(r200) if r200 else fh.R200
    sig = pd.read_csv(r200 / "signals.csv")
    ticks = pd.read_csv(r200 / "ticks.csv")
    t0 = fh.ms(fh.FWD_START)
    sig, ticks = sig[sig.t >= t0], ticks[ticks.t >= t0]
    if ticks.empty:
        return None
    last = int(ticks.t.max())
    T = (last - t0) // H + 1
    syms = sorted(sig.symbol.unique())
    tf = set(json.loads(fh.TRADFI_JSON.read_text()))
    store = fh.hl_store_read() if store is None else store
    coins = set(store.coin) if len(store) else set()
    mp = {s: (None if s in tf else fh.hl_coin(s, coins)) for s in syms}
    mapped = sorted({c for c in mp.values() if c})
    tt = t0 + np.arange(T + 1) * H
    fr = {c: g[["t", "close", "rate"]] for c, g in store.groupby("coin")} if len(store) else {}
    cg = fh.grid({c: fr.get(c) for c in mapped}, tt, "close")
    fg = fh.grid({c: fr.get(c) for c in mapped}, tt, "rate")
    col = {c: j for j, c in enumerate(mapped)}
    S = len(syms)
    close, rate = np.full((T + 1, S), np.nan), np.full((T + 1, S), np.nan)
    for j, s in enumerate(syms):
        if mp[s]:
            close[:, j], rate[:, j] = cg[:, col[mp[s]]], fg[:, col[mp[s]]]
    ret = fh.hl_returns(close, rate)
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
    lag = np.array([fh.entry_lag(t0 + i * H, run_at.get(t0 + i * H, t0 + (i + 1) * H)) for i in range(T)])
    inds = {}
    for k in fh.CELLS:
        x = np.zeros((T, S), bool)
        x[ri, ci] = sig[k].values == 0
        inds[k] = fh.shift_rows(x & trad, trad, lag)
    known = np.isfinite(close[1:]).any(axis=1)
    D = (int(np.flatnonzero(known).max()) + 1 if known.any() else 0) // 24
    return {"t0": t0, "syms": syms, "coins": [mp[s] for s in syms], "ret": ret, "trad": trad, "cmat": cmat,
            "inds": inds, "D": D}


def daily(a, cmat, b_name, cmult):
    return fh.book_days(a["inds"], fh.BOOKS[b_name], a["ret"], a["trad"], cmat, 0, a["D"] * 24, cmult)["net"]


# ---------------------------------------------------------------- the read
def read_books(d):
    files = sorted(Path(d).glob("*.csv"))
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True) if files else pd.DataFrame(
        columns=["coin", "ts"])


def read(snap_dir, out, a=None, tk=None, null=None):
    a = assemble() if a is None else a
    if a is None or a["D"] == 0:
        return {"status": "no complete forward day yet"}
    if tk is None:
        tk = pd.read_csv(fh.J / "tickets.csv") if (fh.J / "tickets.csv").exists() else pd.DataFrame(
            columns=["day", "book", "net", "net_2x", "net_3x", "kind"])
    null = pd.read_csv(fh.LANE / "results" / "gate0" / "daily.csv") if null is None else null
    books = read_books(Path(snap_dir) / SNAP_DIR)
    D = a["D"]
    days = [fh.day_label(a["t0"] + d * DAY) for d in range(D)]
    costs = {n: measured_costs(a["cmat"], a["coins"], a["t0"], books, size=n) for n in SIZES}
    rep = {"data_commit": mc.git_head(snap_dir), "complete_days": D}
    rows = []
    for b_name in fh.BOOKS:
        assumed = daily(a, a["cmat"], b_name, 1.0)
        t = tk[tk.book == b_name].set_index("day")
        both = [d for d in days if d in t.index]
        x = np.array([assumed[days.index(d)] for d in both])
        if len(both) and not np.allclose(x, t.loc[both, "net"].to_numpy(float), rtol=0, atol=1e-9):
            raise SystemExit(f"book {b_name}: recomputed R448 nets differ from its tickets")
        res = {"assumed_1x": assumed}
        for n in SIZES:
            for m in (1.0, 2.0, 3.0):
                res[f"meas_{n}_{int(m)}x"] = daily(a, costs[n][0], b_name, m)
        df = pd.DataFrame({"day": days, "book": b_name, **res})
        df = df.merge(t[["kind"]].reset_index(), on="day", how="left")
        rows.append(df)
        rep[b_name] = decide(df, tk, b_name, null[f"{b_name}_net_1x"].to_numpy(float))
        cm, meas = costs[SIZE_USD]
        rep[b_name].update(cost_summary(traded_mask(a["inds"], fh.BOOKS[b_name], D * 24), meas[:D * 24],
                                        a["cmat"][:D * 24], cm[:D * 24]))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(rows).to_csv(out / "daily.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, help="checkout of the data branch claude/xyz-books-data")
    ap.add_argument("--out")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    fh.check_inputs(LANE / "PREREG.md")
    rep = read(a.snapshots, Path(a.out) if a.out else LANE / "results" / "forward")
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
