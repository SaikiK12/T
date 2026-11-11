"""hlpinv_v1 (R454): HLP's inventory as a cross-sectional signal on Hyperliquid's main-dex perps (M510), as set out in
experiments/hlpinv_v1/PREREG.md.

HLP is Hyperliquid's protocol vault: its child vaults make markets and take over liquidated positions, so its net
position in a coin is roughly the other side of the crowd's. The positions are public in real time and kept nowhere;
scripts/record_hlp_positions.py snapshots them hourly (claude-xyz-books.yml, hlp/ on claude/xyz-books-data).

Rule, per snapshot (the first of each clock hour), on the coins eligible at that snapshot:
- share = HLP's net size in the coin (sum over its child vaults) / the coin's open interest;
- book F (follow HLP) opens a 72 h short slice on the eighth of coins where HLP is most net short (share < 0);
  book R (the reverse) on the eighth where HLP is most net long (share > 0);
- each slice enters at the first hourly close after the snapshot and is hedged with the eligible universe, as R200's
  flow books; returns are Hyperliquid's hourly closes less the funding a long pays; 9 bp a one-way trade.

Reads a checkout of the data branch (no order, no key). Fetches Hyperliquid's hourly closes and funding into
journal/hl/ (one CSV a month, rows never rewritten), appends one ticket per book per complete day to
journal/tickets.csv and rewrites journal/status.json.

usage: python scripts/run_hlpinv.py --snapshots DIR [--status]
"""
import argparse
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, slices  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_flow_hl", ROOT / "scripts" / "run_flow_hl.py")
fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fh)         # Hyperliquid fetch, hour grid, returns net of funding and summaries (R448)

LANE = ROOT / "experiments" / "hlpinv_v1"
J = LANE / "journal"
H, DAY = fh.H, fh.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_hlpinv.py checks these against the PREREG text
FWD_START = "2026-11-12"             # slices from snapshots on or after this UTC day
COUNT_START = "2026-11-15"           # first counted day: the 72 h book is full
HOLD = 72                            # hours a slice is held
FRAC = 1 / 8                         # share of the eligible coins in a book's bin
MIN_ELIG = 16                        # fewer eligible coins at a snapshot: no slice
MIN_VLM_USD = 10e6                   # 24 h notional volume at the snapshot
MIN_OI_USD = 2e6                     # open interest x mark at the snapshot
MATCH_MIN = 10                       # positions belong to the run whose context is at most this much older
ENTRY_GAP_MIN = 5                    # a slice enters at the first hourly close at least this long after its snapshot
MIN_HOURS = 20                       # a day counts when at least this many of its hours opened a slice
COST = 9e-4                          # one-way cost of a trade, main and hedge legs
SCREEN_DAYS, FINAL_DAYS = 90, 365
ALPHA = 0.025                        # one-sided, per book (Bonferroni over the two books)
N_PLACEBO, SEED = 1000, 454
STOP_DD = 0.5                        # stop rule: drawdown of the summed daily nets
BOOKS = ("F", "R")
log = fh.log


# ---------------------------------------------------------------- pure parts (tests/test_run_hlpinv.py)
def snapshots(pos, ctx, match_ms=MATCH_MIN * 60_000):
    """One row per (run, coin) of the context file: run (context ms), snap (latest position ms of the run), coin,
    mark, oi_usd, vlm, net_szi, share, elig. A run without positions within match_ms after its context is dropped."""
    ctx = ctx.copy()
    for c in ("mark", "open_interest", "day_ntl_vlm"):
        ctx[c] = pd.to_numeric(ctx[c], errors="coerce")
    runs = np.sort(ctx.ts.astype(np.int64).unique())
    if len(runs) == 0 or len(pos) == 0:
        return pd.DataFrame(columns=["run", "snap", "coin", "mark", "oi_usd", "vlm", "net_szi", "share", "elig"])
    pt = pos.ts.astype(np.int64).values
    i = np.searchsorted(runs, pt, side="right") - 1
    ok = (i >= 0) & (pt - runs[np.maximum(i, 0)] < match_ms)
    p = pos[ok].assign(run=runs[i[ok]], szi=pd.to_numeric(pos.szi[ok], errors="coerce"))
    snap = p.groupby("run").ts.max().astype(np.int64)
    net = p.groupby(["run", "coin"]).szi.sum()
    t = ctx[ctx.ts.isin(snap.index)].rename(columns={"ts": "run"})
    t = t.assign(snap=t.run.map(snap).values,
                 net_szi=net.reindex(pd.MultiIndex.from_arrays([t.run, t.coin])).fillna(0.0).values)
    t["oi_usd"] = t.open_interest * t.mark
    with np.errstate(divide="ignore", invalid="ignore"):
        t["share"] = np.where(t.open_interest > 0, t.net_szi / t.open_interest, np.nan)
    t["vlm"] = t.day_ntl_vlm
    t["elig"] = (t.vlm >= MIN_VLM_USD) & (t.oi_usd >= MIN_OI_USD) & (t.mark > 0) & np.isfinite(t.share)
    return t[["run", "snap", "coin", "mark", "oi_usd", "vlm", "net_szi", "share", "elig"]].reset_index(drop=True)


def bins(tab, frac=FRAC, min_elig=MIN_ELIG):
    """{run: (k, F coins, R coins)}: k = ceil(frac x eligible coins); F the k with the lowest share among share < 0,
    R the k with the highest among share > 0 (ties by coin name). Runs with fewer than min_elig coins get none."""
    out = {}
    for run, g in tab[tab.elig].groupby("run"):
        n = len(g)
        if n < min_elig:
            continue
        k = math.ceil(frac * n)
        lo = g[g.share < 0].sort_values(["share", "coin"]).coin.tolist()[:k]
        hi = g[g.share > 0].assign(neg=-g.share).sort_values(["neg", "coin"]).coin.tolist()[:k]
        out[int(run)] = (k, lo, hi)
    return out


def slice_rows(tab, t0, gap_ms=ENTRY_GAP_MIN * 60_000):
    """{row: run}: row r earns from the close at t0 + (r + 1) h, so a run's slice opens on the row whose close is
    the first at least gap_ms after its snapshot; the earliest run of a row only; snapshots before t0 dropped."""
    first = tab.groupby("run").snap.first().sort_values()
    out = {}
    for run, snap in first.items():
        if snap < t0:
            continue
        r = int(-(-(int(snap) + gap_ms - t0) // H)) - 1
        out.setdefault(r, int(run))
    return out


def build(tab, coins, t0, T, close):
    """ind {book: [T, S] float, 1/k on a bin's coins}, the hedge basket [T, S] (eligibility of the latest run at or
    before the row, among coins with a close on the row) and opened [T] (rows where a run opened slices)."""
    col = {c: j for j, c in enumerate(coins)}
    S = len(coins)
    ind = {b: np.zeros((T, S)) for b in BOOKS}
    opened = np.zeros(T, bool)
    rows = slice_rows(tab, t0)
    bn = bins(tab)
    el = np.zeros((T, S), bool)
    have = np.zeros(T, bool)
    elig_by_run = {int(r): set(g.coin[g.elig]) for r, g in tab.groupby("run")}
    for r, run in rows.items():
        if r >= T:
            continue
        el[r, [col[c] for c in elig_by_run.get(run, ()) if c in col]] = True
        have[r] = True
        if run not in bn:
            continue
        k, lo, hi = bn[run]
        opened[r] = True
        for b, cs in (("F", lo), ("R", hi)):
            for c in cs:
                if c in col and np.isfinite(close[r, col[c]]):
                    ind[b][r, col[c]] = 1.0 / k
    last = None
    for r in range(T):                                  # carry each run's eligibility forward to later rows
        if have[r]:
            last = el[r].copy()
        elif last is not None:
            el[r] = last
    basket = el & np.isfinite(close[:T])
    return ind, basket, opened


def book_days(ind, ret, basket, D, cmult=1.0, cost=COST):
    """Daily results over the first D days of slices opened from row 0."""
    b = D * 24
    P = slices.positions(ind, HOLD, 0, b, 1.0 / HOLD, -1)
    cmat = np.full(ret.shape, cost)
    o = slices.run(P, ret, basket, cmat, 0, b, hedge=True, cmult=cmult)
    day = lambda x: np.asarray(x)[:b].reshape(D, 24).sum(1)
    by_coin = (P * np.nan_to_num(np.asarray(ret[:b], float))).reshape(D, 24, -1).sum(1)
    return {"net": day(o["net"]), "gross": day(o["gross"]), "cost": day(np.asarray(o["cost"]) + o["hedge_cost"]),
            "hedge": day(o["hedge"]), "exposure": np.asarray(o["gross_exposure"])[:b].reshape(D, 24).mean(1),
            "P": P, "by_coin": by_coin}


def placebo_means(ind, ret, basket, D, day_idx, n_placebo=N_PLACEBO, seed=SEED):
    """1x mean daily net over the days day_idx of books whose bins are drawn at random: on each row the same number
    of coins as the real bin, uniformly from that row's hedge basket, at the same weight and cost."""
    b = D * 24
    w = ind[:b]
    k = (w > 0).sum(1)
    wt = np.where(k > 0, w.sum(1) / np.maximum(k, 1), 0.0)
    bk = np.asarray(basket[:b])
    rng = np.random.default_rng(seed)
    out = np.empty(n_placebo)
    for i in range(n_placebo):
        key = rng.random(bk.shape)
        key[~bk] = np.inf
        rank = key.argsort(1).argsort(1)
        pick = (rank < k[:, None]) & bk
        r = book_days(pick * wt[:, None], ret, basket, D)
        out[i] = r["net"][day_idx].mean()
    return out


def read_decision(tk, coins, b_name, threshold=None):
    """The frozen looks on a book's counted days (in calendar order). threshold(n) gives the placebo threshold."""
    on = tk[(tk.book == b_name) & (tk.kind == "counted")].sort_values("day")
    s = fh.describe(on.net.values)
    s["mean_2x_bp_day"] = float(on.net_2x.mean() * 1e4) if len(on) else None
    s["mean_3x_bp_day"] = float(on.net_3x.mean() * 1e4) if len(on) else None
    cb = coins[(coins.book == b_name) & coins.day.isin(on.day)]
    if len(cb):
        piv = cb.pivot_table(index="day", columns="coin", values="gross", aggfunc="sum").fillna(0.0)
        s["leave_two_coins_out_gross_bp_day"] = fh.leave_two_out(piv.values)
    n = len(on)
    if n >= FINAL_DAYS:
        x = on.net.values[:FINAL_DAYS]
        thr = threshold(FINAL_DAYS) if threshold else float("nan")
        ok = (x.mean() > thr and x.mean() > 0 and on.net_2x.values[:FINAL_DAYS].mean() > 0
              and fh.describe(x)["trimmed_mean_bp_day"] > 0)
        s["decision"] = ("PASS" if ok else "NULL") + f" at {FINAL_DAYS} days (placebo threshold {thr * 1e4:.2f} bp/day)"
    elif n >= SCREEN_DAYS:
        x = on.net.values[:SCREEN_DAYS]
        s["decision"] = ("SURVIVES the futility screen" if x.mean() > 0 else "NULL (futility)") + \
            f" at {SCREEN_DAYS} days; final read at {FINAL_DAYS}"
    else:
        s["decision"] = f"pending ({n} counted days of {SCREEN_DAYS})"
    eq = np.cumsum(on.net.values)
    s["stop_rule_hit"] = bool(len(eq) and np.max(np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:] - eq)
                              >= STOP_DD)
    return s


def day_kind(day, hours_opened):
    if day < COUNT_START:
        return "ramp"
    return "counted" if hours_opened >= MIN_HOURS else "thin"


# ---------------------------------------------------------------- inputs
def read_days(folder):
    files = sorted(Path(folder).glob("*.csv"))
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True) if files else pd.DataFrame()


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
    new = new[np.isfinite(new.close.astype(float))]
    if new.empty:
        return 0
    (J / "hl").mkdir(parents=True, exist_ok=True)
    new["month"] = [fh.day_label(x)[:7] for x in new.t]
    for m, g in new.sort_values(["t", "coin"]).groupby("month"):
        p = J / "hl" / f"{m}.csv"
        g.drop(columns="month").to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
    return len(new)


def git_head(path):
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


# ---------------------------------------------------------------- forward
def forward(snap_dir, status_only=False):
    hlp = Path(snap_dir) / "hlp"
    pos, ctx = read_days(hlp / "positions"), read_days(hlp / "ctx")
    t0 = fh.ms(FWD_START)
    if ctx.empty or pos.empty or int(ctx.ts.max()) < t0:
        log("no HLP snapshot on or after", FWD_START)
        return None
    tab = snapshots(pos, ctx)
    tab = tab[tab.run >= t0 - MATCH_MIN * 60_000]
    last_run = int(tab.run.max())
    coins = sorted(set(tab.coin[tab.elig]))
    now = int(time.time() * 1000) // H * H
    if not status_only:
        store = hl_store_read()
        got = []
        for c in coins:
            done = store[store.coin == c].t.max() if len(store) else np.nan
            start = max(t0, int(done) + H) if np.isfinite(done) else t0
            if start < now:
                got += fh.fetch_hl(c, start, now)
                time.sleep(1.0)
        log("hl rows added", hl_store_add(got))
    store = hl_store_read()
    known_last = int(store.t.max()) if len(store) else t0      # open time of the latest stored closed candle
    # Rows [0, T): row i earns close[i + 1] / close[i], so the last row needs the candle opening at known_last; and
    # every hour of a row has passed the recorder by the last run, so no later snapshot can open a slice there.
    end = min(known_last, last_run // H * H)
    T = max(0, (end - t0) // H)
    D = T // 24
    tt = t0 + np.arange(T + 1) * H
    fr = {c: g[["t", "close", "rate"]] for c, g in store.groupby("coin")}
    close = fh.grid({c: fr.get(c) for c in coins}, tt, "close")
    rate = fh.grid({c: fr.get(c) for c in coins}, tt, "rate")
    ret = fh.hl_returns(close, rate)
    ind, basket, opened = build(tab, coins, t0, T, close)
    have = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame()
    done = set(zip(have.day, have.book)) if len(have) else set()
    rows, coin_rows = [], []
    if D and not status_only:
        for b_name in BOOKS:
            res = {cm: book_days(ind[b_name], ret, basket, D, cm) for cm in (1.0, 2.0, 3.0)}
            P = res[1.0]["P"]
            fund = -(P * np.nan_to_num(rate[1:D * 24 + 1])).reshape(D, 24, -1).sum((1, 2))
            for d in range(D):
                day = fh.day_label(t0 + d * DAY)
                if (day, b_name) in done:
                    continue
                n_open = int(opened[d * 24:(d + 1) * 24].sum())
                rows.append({"day": day, "book": b_name, "net": res[1.0]["net"][d], "gross": res[1.0]["gross"][d],
                             "cost": res[1.0]["cost"][d], "funding": float(fund[d]), "hedge": res[1.0]["hedge"][d],
                             "net_2x": res[2.0]["net"][d], "net_3x": res[3.0]["net"][d],
                             "gross_exposure": res[1.0]["exposure"][d], "hours_opened": n_open,
                             "kind": day_kind(day, n_open)})
                for j in np.flatnonzero(res[1.0]["by_coin"][d] != 0):
                    coin_rows.append({"day": day, "book": b_name, "coin": coins[j],
                                      "gross": res[1.0]["by_coin"][d, j]})
    J.mkdir(parents=True, exist_ok=True)
    if rows:
        p = J / "tickets.csv"
        pd.DataFrame(rows).to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
    if coin_rows:
        p = J / "coins.csv"
        pd.DataFrame(coin_rows).to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")

    def threshold_for(b_name):
        def thr(n):
            tk = pd.read_csv(J / "tickets.csv")
            on = tk[(tk.book == b_name) & (tk.kind == "counted")].sort_values("day").day.values[:n]
            idx = np.array([(fh.ms(d) - t0) // DAY for d in on], int)
            if len(idx) < n or idx.max() >= D:
                return float("nan")
            return float(np.quantile(placebo_means(ind[b_name], ret, basket, D, idx), 1 - ALPHA))
        return thr

    st = {"data_commit": git_head(snap_dir), "last_snapshot": pd.Timestamp(last_run, unit="ms", tz="UTC").isoformat(),
          "runs": int(tab.run.nunique()), "rows": int(T), "rows_opened": int(opened.sum()), "complete_days": int(D),
          "coins_ever_eligible": len(coins)}
    tk = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame(
        columns=["day", "book", "net", "net_2x", "net_3x", "kind"])
    cs = pd.read_csv(J / "coins.csv") if (J / "coins.csv").exists() else pd.DataFrame(
        columns=["day", "book", "coin", "gross"])
    for b_name in BOOKS:
        st[b_name] = read_decision(tk, cs, b_name, threshold_for(b_name))
        st[b_name]["all_days"] = fh.describe(tk[tk.book == b_name].net.values if len(tk) else [])
    (J / "status.json").write_text(json.dumps(st, indent=1, default=float) + "\n")
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, help="checkout of claude/xyz-books-data")
    ap.add_argument("--status", action="store_true", help="rewrite status.json from the journal, no fetch, no ticket")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    fh.check_inputs(LANE / "PREREG.md")
    st = forward(a.snapshots, a.status)
    if st:
        log({b: (st[b]["decision"], st[b]["all_days"].get("days")) for b in BOOKS})


if __name__ == "__main__":
    main()
