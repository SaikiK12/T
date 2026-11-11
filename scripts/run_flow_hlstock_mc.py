"""flow_hlstock_mc_v1 (R453): R451's books (R200's flow signals on stock/commodity perps traded on Hyperliquid's xyz)
re-priced at measured costs, as set out in experiments/flow_hlstock_mc_v1/PREREG.md.

R451 charges each one-way trade the lab's tier cost, never below 9 bp. Two things it did not measure:
- the fee: 117 of xyz's 122 markets ran in HIP-3 growth mode on 2026-11-11, whose taker fee is a tenth of 9 bp;
- the book: what a market order actually pays against xyz's depth.
This lane recomputes R451's positions unchanged and replaces only the cost of each coin-hour by
  fee (from the market's growth mode and deployer fee scale that day) + slippage (the mean of the buy and sell cost
  of a $1k market order in the hourly snapshot nearest the trade, scripts/record_xyz_books.py),
falling back to R451's own cost where no snapshot is within 90 minutes. It adds no chance to pass: a book is only
"executable at measured costs" if R451 itself passes.

Reads (no fetch, no order): R200's journal, R451's journal (tickets and its xyz price store) and a checkout of the
data branch claude/xyz-books-data.

usage: python scripts/run_flow_hlstock_mc.py --books DIR [--out DIR]
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import engine, prereg, slices  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_flow_hlstock", ROOT / "scripts" / "run_flow_hlstock.py")
r451 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r451)
fh = r451.fh

LANE = ROOT / "experiments" / "flow_hlstock_mc_v1"
H, DAY, HOLD = fh.H, fh.DAY, fh.HOLD
# ---- the frozen rule (PREREG "Rule"); tests/test_run_flow_hlstock_mc.py checks these against the PREREG text
BASE_TAKER = 4.5e-4                  # Hyperliquid's tier-0 perp taker fee, one way
SIZE_USD = 1_000                     # the snapshot cost level used for slippage (primary)
SIZES = (1_000, 5_000, 10_000)       # reported
MAX_GAP_MIN = 90                     # a snapshot farther than this from the trade is not used
SCREEN_DAYS, FINAL_DAYS = fh.SCREEN_DAYS, fh.FINAL_DAYS


# ---------------------------------------------------------------- pure parts
def taker_fee(growth_mode, fee_scale):
    """One-way taker fee of a HIP-3 perp at tier 0 (Hyperliquid's fee formula: scaleIfHip3 and growthModeScale)."""
    s = float(fee_scale)
    scale = s + 1 if s < 1 else 2 * s
    return BASE_TAKER * scale * (0.1 if str(growth_mode).strip().lower() == "enabled" else 1.0)


def fee_lookup(markets):
    """{coin: sorted [(day, fee)]} from the markets/ day files (a DataFrame with dex, coin, day, growthMode,
    deployerFeeScale)."""
    out = {}
    for r in markets.itertuples(index=False):
        fs = r.deployerFeeScale if pd.notna(r.deployerFeeScale) and str(r.deployerFeeScale) != "" else 1.0
        out.setdefault(r.coin, []).append((str(r.day), taker_fee(r.growthMode if pd.notna(r.growthMode) else "",
                                                                  fs)))
    return {c: sorted(v) for c, v in out.items()}


def fee_at(fees, coin, day):
    """The fee listed on the latest day at or before `day`; the base fee doubled (9 bp) if none is."""
    best = None
    for d, f in fees.get(coin, []):
        if d <= day:
            best = f
    return best if best is not None else 2 * BASE_TAKER


def nearest_slip(ts, slip, targets, max_gap_ms):
    """For each target time (ms), the slippage of the snapshot nearest to it within max_gap_ms, else NaN.
    ts sorted ascending; slip aligned with ts (NaN where the book was too thin)."""
    ts = np.asarray(ts, np.int64)
    slip = np.asarray(slip, float)
    out = np.full(len(targets), np.nan)
    if not len(ts):
        return out
    tg = np.asarray(targets, np.int64)
    j = np.searchsorted(ts, tg)
    lo, hi = np.clip(j - 1, 0, len(ts) - 1), np.clip(j, 0, len(ts) - 1)
    pick = np.where(np.abs(ts[lo] - tg) <= np.abs(ts[hi] - tg), lo, hi)
    ok = np.abs(ts[pick] - tg) <= max_gap_ms
    out[ok] = slip[pick[ok]]
    return out


def measured_costs(assumed, syms, mp, t0, books, fees, size=SIZE_USD, max_gap_min=MAX_GAP_MIN):
    """[T, S] one-way costs: fee + measured slippage where a snapshot is near the trade, R451's cost elsewhere.
    Row i's trades execute at the close of the bar opening at t0 + i*H (fh.grid, fh.hl_returns), so the target time is
    t0 + (i + 1) * H. Returns (costs, measured mask)."""
    a = np.asarray(assumed, float)
    T = a.shape[0]
    targets = t0 + (np.arange(T) + 1) * H
    days = [fh.day_label(int(x)) for x in targets]
    out, meas = a.copy(), np.zeros(a.shape, bool)
    col_b, col_s = f"buy_{size}_bp", f"sell_{size}_bp"
    for j, s in enumerate(syms):
        c = mp.get(s)
        if not c:
            continue
        g = books[books.coin == c].sort_values("ts") if len(books) else books
        slip = ((g[col_b].astype(float) + g[col_s].astype(float)) / 2 / 1e4).to_numpy() if len(g) else []
        sl = nearest_slip(g.ts.to_numpy() if len(g) else [], slip, targets, max_gap_min * 60_000)
        fee = np.array([fee_at(fees, c, d) for d in days])
        ok = np.isfinite(sl) & np.isfinite(a[:, j])
        out[ok, j] = fee[ok] + np.maximum(sl[ok], 0.0)
        meas[ok, j] = True
    return out, meas


# ---------------------------------------------------------------- data
def read_books(d):
    d = Path(d)
    files = sorted((d / "books").glob("*.csv"))
    books = pd.concat([pd.read_csv(p) for p in files], ignore_index=True) if files else pd.DataFrame(
        columns=["coin", "ts"])
    mfiles = sorted((d / "markets").glob("*.csv"))
    markets = pd.concat([pd.read_csv(p, dtype={"day": str}) for p in mfiles], ignore_index=True) if mfiles else \
        pd.DataFrame(columns=["coin", "day", "growthMode", "deployerFeeScale"])
    return books, markets


def assemble():
    """R451's forward computation without fetching: R200's signals and ticks, R451's stored xyz prices."""
    sig = pd.read_csv(r451.R200 / "signals.csv")
    ticks = pd.read_csv(r451.R200 / "ticks.csv")
    t0 = r451.ms(r451.FWD_START)
    sig, ticks = sig[sig.t >= t0], ticks[ticks.t >= t0]
    if ticks.empty:
        return None
    last = int(ticks.t.max())
    T = (last - t0) // H + 1
    tf = set(json.loads(r451.TRADFI_JSON.read_text()))
    syms = sorted(s for s in sig.symbol.unique() if s in tf)
    store = r451.hl_store_read()
    coins = set(store.coin) if len(store) else set()
    mp = {s: r451.xyz_coin(s, coins) for s in syms}
    mapped = sorted({c for c in mp.values() if c})
    tt = t0 + np.arange(T + 1) * H
    pr = r451.read_prices(mapped, None)
    cg, fg = fh.grid({c: pr.get(c) for c in mapped}, tt, "close"), fh.grid({c: pr.get(c) for c in mapped}, tt, "rate")
    col = {c: j for j, c in enumerate(mapped)}
    S = len(syms)
    close, rate = np.full((T + 1, S), np.nan), np.full((T + 1, S), np.nan)
    for j, s in enumerate(syms):
        if mp[s]:
            close[:, j], rate[:, j] = cg[:, col[mp[s]]], fg[:, col[mp[s]]]
    ret = fh.hl_returns(close, rate)
    elig, rank, _, raw = r451.journal_grid(sig, syms, t0, T)
    cmat = r451.floor_costs(engine.cost_matrix(rank))
    is_mapped = np.array([mp[s] is not None for s in syms])
    trad = elig & is_mapped[None, :] & np.isfinite(close[:T])
    run_ms = (pd.to_datetime(ticks.run_at, utc=True) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)
    run_at = dict(zip(ticks.t.astype(np.int64), run_ms.astype(np.int64)))
    lag = np.array([fh.entry_lag(t0 + i * H, run_at.get(t0 + i * H, t0 + (i + 1) * H)) for i in range(T)])
    inds = {k: fh.shift_rows(raw[k] & trad, trad, lag) for k in r451.CELLS}
    known = np.isfinite(close[1:]).any(axis=1)
    D = (int(np.flatnonzero(known).max()) + 1 if known.any() else 0) // 24
    return {"t0": t0, "syms": syms, "mp": mp, "ret": ret, "trad": trad, "cmat": cmat, "inds": inds, "D": D}


def daily(a, cmat, b_name, cmult):
    return fh.book_days(a["inds"], r451.BOOKS[b_name], a["ret"], a["trad"], cmat, 0, a["D"] * 24, cmult)["net"]


def traded_share(a, b_name, meas):
    """Share of the book's traded coin-hours (main legs) priced from a snapshot."""
    P = sum(slices.positions(a["inds"][k], HOLD, 0, a["D"] * 24, fh.UNIT, -1) for k in r451.BOOKS[b_name])
    dP = np.diff(np.vstack([np.zeros((1, P.shape[1])), P]), axis=0) != 0
    n = dP.sum()
    return float((dP & meas[:a["D"] * 24]).sum() / n) if n else None


def read(books_dir, out):
    a = assemble()
    if a is None or a["D"] == 0:
        return {"status": "no complete forward day yet"}
    tk = pd.read_csv(r451.J / "tickets.csv") if (r451.J / "tickets.csv").exists() else pd.DataFrame(
        columns=["day", "book", "net", "net_2x", "net_3x", "kind"])
    books, markets = read_books(books_dir)
    fees = fee_lookup(markets) if len(markets) else {}
    days = [fh.day_label(a["t0"] + d * DAY) for d in range(a["D"])]
    null = pd.read_csv(r451.LANE / "results" / "gate0" / "daily.csv")
    rep = {"books_commit": git_head(books_dir), "complete_days": a["D"]}
    rows = []
    for b_name in r451.BOOKS:
        assumed = daily(a, a["cmat"], b_name, 1.0)
        t = tk[tk.book == b_name].set_index("day")
        both = [d for d in days if d in t.index]
        x = np.array([assumed[days.index(d)] for d in both])
        if len(both) and not np.allclose(x, t.loc[both, "net"].to_numpy(float), rtol=0, atol=1e-9):
            raise SystemExit(f"book {b_name}: recomputed R451 nets differ from its tickets")
        res = {"assumed_1x": assumed}
        for n in SIZES:
            cm, meas = measured_costs(a["cmat"], a["syms"], a["mp"], a["t0"], books, fees, size=n)
            for m in (1.0, 2.0, 3.0):
                res[f"meas_{n}_{int(m)}x"] = daily(a, cm, b_name, m)
            if n == SIZE_USD:
                rep[f"{b_name}_traded_share_measured"] = traded_share(a, b_name, meas)
        df = pd.DataFrame({"day": days, "book": b_name, **res})
        df = df.merge(t[["kind"]].reset_index(), on="day", how="left")
        rows.append(df)
        rep[b_name] = decide(df, tk, b_name, null[f"{b_name}_net_1x"].to_numpy(float))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pd.concat(rows).to_csv(out / "daily.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    return rep


def decide(df, tk, b_name, null_days):
    """The frozen reads on R451's strict on-time days, in calendar order. R451's own decision is fh.read_decision on
    its tickets, as R451's status() computes it."""
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
    if n >= FINAL_DAYS:
        x = m[:FINAL_DAYS]
        r = fh.read_decision(tk, pd.DataFrame(columns=["day", "book", "symbol", "gross"]), b_name, null_days)
        thr = fh.boot_threshold(null_days, FINAL_DAYS)
        ok = (x.mean() > thr and on[f"meas_{SIZE_USD}_2x"].to_numpy(float)[:FINAL_DAYS].mean() > 0
              and fh.describe(x)["trimmed_mean_bp_day"] > 0)
        if not str(r["decision"]).startswith("PASS") or r["stop_rule_hit"]:
            s["decision"] = f"n/a: R451 did not pass ({r['decision']}; stop rule hit {r['stop_rule_hit']})"
        else:
            s["decision"] = ("EXECUTABLE AT MEASURED COSTS" if ok else "NOT EXECUTABLE AT MEASURED COSTS") + \
                f" (threshold {thr * 1e4:.1f} bp/day)"
    elif n >= SCREEN_DAYS:
        g = gap[:SCREEN_DAYS].mean()
        s["decision"] = ("NO WORSE THAN ASSUMED" if g >= 0 else "COSTLIER THAN ASSUMED") + \
            f" at {SCREEN_DAYS} days ({g * 1e4:+.2f} bp/day)"
    else:
        s["decision"] = f"pending ({n} strict on-time days of {SCREEN_DAYS})"
    return s


def check_inputs():
    """Every file in the PREREG's inputs block still has its frozen sha256."""
    text = (LANE / "PREREG.md").read_text()
    lines = text.split("```inputs\n", 1)[1].split("```", 1)[0].splitlines()
    for line in lines:
        sha, rel = line.split()
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != sha:
            raise SystemExit(f"input changed since the freeze: {rel}")
    return len(lines)


def git_head(d):
    try:
        return subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True, help="checkout of the data branch claude/xyz-books-data")
    ap.add_argument("--out")
    a = ap.parse_args()
    prereg.verify(LANE / "PREREG.md")
    check_inputs()
    rep = read(a.books, Path(a.out) if a.out else LANE / "results" / "forward")
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
