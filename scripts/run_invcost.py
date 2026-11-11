"""invcost_v1 (R456): R454's and R455's inventory books re-priced at measured costs, as set out in
experiments/invcost_v1/PREREG.md.

R454 (HLP on Hyperliquid) and R455 (LLP on Lighter) charge every one-way trade a flat 9 bp. This lane recomputes their
books unchanged (their own frozen code, their own stored prices, no fetch) and replaces only the cost of each
coin-hour by
  the venue's taker fee (Hyperliquid tier 0: 4.5 bp; Lighter Standard account: 0) + slippage (the mean of the buy and
  sell cost of a $1k market order in the hourly book snapshot nearest the trade),
falling back to 9 bp where no snapshot is within 90 minutes or the shown book was too thin. Snapshots come from the
data branch claude/xyz-books-data: main/books/ (scripts/record_xyz_books.py --dex "") and lighter/books/
(scripts/record_lighter_costs.py). It adds no chance to pass: a book is only "executable at measured costs" if its
parent lane itself passes. It stops when its recomputation of a parent's 9 bp nets differs from the parent's tickets.

Reads only; writes experiments/invcost_v1/results/forward/{daily.csv, report.json} (rewritten each read).

usage: python scripts/run_invcost.py --snapshots DIR [--out DIR]
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
from lab import prereg, slices  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lv = _load("run_llpinv")             # R455; it loads R454's module as lv.hi
hi = lv.hi
fh = hi.fh
mc = _load("run_flow_hlstock_mc")    # R453: nearest_slip, the snapshot matcher

LANE = ROOT / "experiments" / "invcost_v1"
H, DAY = hi.H, hi.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_invcost.py checks these against the PREREG text
SIZE_USD = 1_000                     # the snapshot cost level used for slippage (primary)
SIZES = (1_000, 10_000)              # reported (Lighter's recorder has these two)
MAX_GAP_MIN = 90                     # a snapshot farther than this from the trade is not used
FEES = {"R454": 4.5e-4, "R455": 0.0}  # one-way taker fee: Hyperliquid tier 0; Lighter Standard account
log = fh.log


# ---------------------------------------------------------------- pure parts
def measured_costs(assumed, coins, t0, books, coin_col, fee, size=SIZE_USD, max_gap_min=MAX_GAP_MIN):
    """[T, S] one-way costs: fee + measured slippage where a snapshot is near the trade, `assumed` elsewhere. Row i's
    trades execute at the close of the bar opening at t0 + i * H, so the target time is t0 + (i + 1) * H. Returns
    (costs, measured mask)."""
    a = np.asarray(assumed, float)
    T = a.shape[0]
    targets = t0 + (np.arange(T) + 1) * H
    out, meas = a.copy(), np.zeros(a.shape, bool)
    col_b, col_s = cost_cols(coin_col, size)
    for j, c in enumerate(coins):
        g = books[books[coin_col] == c].sort_values("ts") if len(books) else books
        if not len(g):
            continue
        slip = ((pd.to_numeric(g[col_b], errors="coerce") + pd.to_numeric(g[col_s], errors="coerce")) / 2 / 1e4)
        sl = mc.nearest_slip(g.ts.to_numpy(np.int64), slip.to_numpy(float), targets, max_gap_min * 60_000)
        ok = np.isfinite(sl)
        out[ok, j] = fee + np.maximum(sl[ok], 0.0)
        meas[ok, j] = True
    return out, meas


def cost_cols(coin_col, size):
    """Column names of a $size market order's cost: main/ books write buy_1000_bp, Lighter's buy_1k_bp."""
    k = str(size) if coin_col == "coin" else f"{size // 1000}k"
    return f"buy_{k}_bp", f"sell_{k}_bp"


def book_net(ind, ret, basket, D, cmat, cmult=1.0):
    """Daily 1x/2x/3x net of one book with a cost matrix: R454's book_days with costs per coin-hour."""
    b = D * 24
    P = slices.positions(ind, hi.HOLD, 0, b, 1.0 / hi.HOLD, -1)
    o = slices.run(P, ret, basket, cmat, 0, b, hedge=True, cmult=cmult)
    return np.asarray(o["net"])[:b].reshape(D, 24).sum(1), P


# ---------------------------------------------------------------- the parents' state, recomputed without fetching
def state_r454(snap_dir):
    d = Path(snap_dir) / "hlp"
    pos, ctx = hi.read_days(d / "positions"), hi.read_days(d / "ctx")
    t0 = fh.ms(hi.FWD_START)
    if ctx.empty or pos.empty or int(ctx.ts.max()) < t0:
        return None
    tab = hi.snapshots(pos, ctx)
    tab = tab[tab.run >= t0 - hi.MATCH_MIN * 60_000]
    return _grid(tab, hi.hl_store_read(), t0, hi.J, hi.SEED)


def state_r455(snap_dir):
    d = Path(snap_dir) / "llp"
    pos, mk, acc = (hi.read_days(d / k) for k in ("positions", "markets", "accounts"))
    t0 = fh.ms(lv.FWD_START)
    if mk.empty or acc.empty or int(mk.ts.max()) < t0:
        return None
    tab = lv.snapshots(pos, mk, acc)
    tab = tab[tab.run >= t0 - H]
    return _grid(tab, lv.px_read(), t0, lv.J, lv.SEED)


def _grid(tab, store, t0, journal, seed):
    """The parent's forward() arithmetic after its fetch: rows, prices, returns, slices and baskets."""
    if tab.empty:
        return None
    last_run = int(tab.run.max())
    coins = sorted(set(tab.coin[tab.elig]))
    known_last = int(store.t.max()) if len(store) else t0
    end = min(known_last, last_run // H * H)
    T = max(0, (end - t0) // H)
    tt = t0 + np.arange(T + 1) * H
    fr = {c: g[["t", "close", "rate"]] for c, g in store.groupby("coin")} if len(store) else {}
    close = fh.grid({c: fr.get(c) for c in coins}, tt, "close")
    rate = fh.grid({c: fr.get(c) for c in coins}, tt, "rate")
    ret = fh.hl_returns(close, rate)
    ind, basket, opened = hi.build(tab, coins, t0, T, close)
    tk = pd.read_csv(journal / "tickets.csv") if (journal / "tickets.csv").exists() else pd.DataFrame(
        columns=["day", "book", "net", "net_2x", "net_3x", "kind"])
    return {"t0": t0, "T": T, "D": T // 24, "coins": coins, "ret": ret, "ind": ind, "basket": basket, "tk": tk,
            "seed": seed}


# ---------------------------------------------------------------- data
def read_books(d):
    files = sorted(Path(d).glob("*.csv"))
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True) if files else pd.DataFrame(columns=["ts"])


def parent_threshold(st, b_name, days):
    """The parent's own placebo threshold over its first `days` counted days (its frozen seed and costs)."""
    tk = st["tk"]
    on = tk[(tk.book == b_name) & (tk.kind == "counted")].sort_values("day").day.values[:days]
    idx = np.array([(fh.ms(d) - st["t0"]) // DAY for d in on], int)
    if len(idx) < days or idx.max() >= st["D"]:
        return float("nan")
    q = hi.placebo_means(st["ind"][b_name], st["ret"], st["basket"], st["D"], idx, seed=st["seed"])
    return float(np.quantile(q, 1 - hi.ALPHA))


def decide(df, st, b_name):
    """The frozen reads on the parent's counted days, in calendar order."""
    on = df[df.kind == "counted"].sort_values("day")
    m = on[f"meas_{SIZE_USD}_1x"].to_numpy(float)
    gap = m - on.assumed_1x.to_numpy(float)
    s = {"counted_days": int(len(on)), "measured_1x_bp_day": float(m.mean() * 1e4) if len(m) else None,
         "assumed_1x_bp_day": float(on.assumed_1x.mean() * 1e4) if len(on) else None,
         "gap_bp_day": float(gap.mean() * 1e4) if len(gap) else None}
    for n in SIZES:
        for k in (1, 2, 3):
            c = f"meas_{n}_{k}x"
            s[f"{c}_bp_day"] = float(on[c].mean() * 1e4) if len(on) else None
    n = len(on)
    if n >= hi.FINAL_DAYS:
        cs = pd.DataFrame(columns=["day", "book", "coin", "gross"])
        r = hi.read_decision(st["tk"], cs, b_name, lambda k: parent_threshold(st, b_name, k))
        if not str(r["decision"]).startswith("PASS") or r["stop_rule_hit"]:
            s["decision"] = f"n/a: the parent did not pass ({r['decision']}; stop rule hit {r['stop_rule_hit']})"
        else:
            x = m[:hi.FINAL_DAYS]
            thr = parent_threshold(st, b_name, hi.FINAL_DAYS)
            ok = (x.mean() > thr and x.mean() > 0 and on[f"meas_{SIZE_USD}_2x"].to_numpy(float)[:hi.FINAL_DAYS].mean()
                  > 0 and fh.describe(x)["trimmed_mean_bp_day"] > 0)
            s["decision"] = ("EXECUTABLE AT MEASURED COSTS" if ok else "NOT EXECUTABLE AT MEASURED COSTS") + \
                f" (parent's placebo threshold {thr * 1e4:.2f} bp/day)"
    elif n >= hi.SCREEN_DAYS:
        g = gap[:hi.SCREEN_DAYS].mean()
        s["decision"] = ("NO WORSE THAN ASSUMED" if g >= 0 else "COSTLIER THAN ASSUMED") + \
            f" at {hi.SCREEN_DAYS} days ({g * 1e4:+.2f} bp/day)"
    else:
        s["decision"] = f"pending ({n} counted days of {hi.SCREEN_DAYS})"
    return s


def read_parent(rid, st, books, coin_col):
    """Daily rows and the per-book reads of one parent lane."""
    if st is None or st["D"] == 0:
        return [], {"status": "no complete forward day yet"}
    D, T = st["D"], st["T"]
    days = [fh.day_label(st["t0"] + d * DAY) for d in range(D)]
    assumed_c = np.full((T, len(st["coins"])), hi.COST)
    costs = {n: measured_costs(assumed_c, st["coins"], st["t0"], books, coin_col, FEES[rid], size=n) for n in SIZES}
    rep, rows = {}, []
    for b_name in hi.BOOKS:
        assumed, P = book_net(st["ind"][b_name], st["ret"], st["basket"], D, assumed_c)
        t = st["tk"][st["tk"].book == b_name].set_index("day")
        both = [d for d in days if d in t.index]
        x = np.array([assumed[days.index(d)] for d in both])
        if len(both) and not np.allclose(x, t.loc[both, "net"].to_numpy(float), rtol=0, atol=1e-9):
            raise SystemExit(f"{rid} book {b_name}: recomputed 9 bp nets differ from its tickets")
        res = {"assumed_1x": assumed}
        for n in SIZES:
            for k in (1.0, 2.0, 3.0):
                res[f"meas_{n}_{int(k)}x"] = book_net(st["ind"][b_name], st["ret"], st["basket"], D, costs[n][0], k)[0]
        dP = np.diff(np.vstack([np.zeros((1, P.shape[1])), P]), axis=0) != 0
        traded = int(dP.sum())
        df = pd.DataFrame({"lane": rid, "day": days, "book": b_name, **res})
        df = df.merge(t[["kind"]].reset_index(), on="day", how="left")
        rows.append(df)
        rep[b_name] = decide(df, st, b_name)
        rep[b_name]["traded_share_measured"] = (float((dP & costs[SIZE_USD][1][:D * 24]).sum() / traded)
                                                if traded else None)
    return rows, rep


def read(snap_dir, out):
    snap_dir = Path(snap_dir)
    rep = {"data_commit": hi.git_head(snap_dir)}
    rows = []
    for rid, state, sub, coin_col in (("R454", state_r454, "main/books", "coin"),
                                      ("R455", state_r455, "lighter/books", "symbol")):
        r, rep[rid] = read_parent(rid, state(snap_dir), read_books(snap_dir / sub), coin_col)
        rows += r
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if rows:
        pd.concat(rows).to_csv(out / "daily.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, help="checkout of claude/xyz-books-data")
    ap.add_argument("--out", default=str(LANE / "results" / "forward"))
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    fh.check_inputs(LANE / "PREREG.md")
    rep = read(a.snapshots, a.out)
    log({rid: {b: v.get("decision") for b, v in r.items() if isinstance(v, dict)} if isinstance(r, dict) else r
         for rid, r in rep.items() if rid != "data_commit"})


if __name__ == "__main__":
    main()
