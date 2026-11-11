"""llpinv_v1 (R455): Lighter LLP's inventory as a cross-sectional signal on Lighter's perps (M511), as set out in
experiments/llpinv_v1/PREREG.md. The rule is R454's (scripts/run_hlpinv.py, imported unchanged: bins, slice rows,
book, placebo and looks) applied to Lighter's protocol pool and Lighter's prices.

LLP makes markets and takes over liquidations on Lighter, as HLP does on Hyperliquid. Lighter's public `account`
endpoint lists its positions but keeps no history; scripts/record_llp_positions.py snapshots them hourly with every
market's open interest (claude-xyz-books.yml, llp/ on claude/xyz-books-data).

Per snapshot: share = LLP's signed position value in a market / the market's open interest in USD. Book F shorts the
eighth of eligible markets where LLP is most net short, book R the eighth where it is most net long; 72 h slices
hedged with the eligible markets; returns are Lighter's hourly closes less the funding a long pays; 9 bp a trade.

Reads a checkout of the data branch (no order, no key). Fetches Lighter's hourly closes and funding into journal/px/
(one CSV a month, rows never rewritten), appends one ticket per book per complete day to journal/tickets.csv and
rewrites journal/status.json.

usage: python scripts/run_llpinv.py --snapshots DIR [--status]
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane, prereg  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_hlpinv", ROOT / "scripts" / "run_hlpinv.py")
hi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hi)         # R454's frozen rule: bins, slice_rows, build, book_days, placebo, looks
fh = hi.fh

LANE = ROOT / "experiments" / "llpinv_v1"
J = LANE / "journal"
H, DAY = hi.H, hi.DAY
# ---- the frozen rule (PREREG "Rule"); everything else is R454's constant, read from scripts/run_hlpinv.py
FWD_START = hi.FWD_START             # 2026-11-12, as R454 (counted from hi.COUNT_START, 2026-11-15)
MIN_VLM_USD = 10e6                   # Lighter's 24 h quote volume at the snapshot
MIN_OI_USD = 2e6                     # Lighter's open interest in USD at the snapshot
SEED = 455                           # placebo seed
BOOKS = hi.BOOKS
log = fh.log


# ---------------------------------------------------------------- pure parts (tests/test_run_llpinv.py)
def snapshots(pos, mk, acc):
    """R454's table from LLP's files: one row per (run, market) of a run with an accounts row. coin = Lighter's
    symbol; net_szi holds LLP's signed position value (USD); share = that / open interest in USD."""
    cols = ["run", "snap", "coin", "mark", "oi_usd", "vlm", "net_szi", "share", "elig"]
    if mk.empty or acc.empty:
        return pd.DataFrame(columns=cols)
    runs = set(acc.ts.astype(np.int64))
    t = mk[mk.ts.astype(np.int64).isin(runs)].copy()
    for c in ("mark_price", "open_interest_usd", "daily_quote_token_volume"):
        t[c] = pd.to_numeric(t[c], errors="coerce")
    if len(pos):
        p = pos.assign(v=pd.to_numeric(pos.sign, errors="coerce") * pd.to_numeric(pos.position_value, errors="coerce"))
        net = p.groupby(["ts", "market_id"]).v.sum()
        t["net_szi"] = net.reindex(pd.MultiIndex.from_arrays([t.ts, t.market_id])).fillna(0.0).values
    else:
        t["net_szi"] = 0.0
    t = t.rename(columns={"ts": "run", "symbol": "coin", "mark_price": "mark", "open_interest_usd": "oi_usd",
                          "daily_quote_token_volume": "vlm"})
    t["snap"] = t.run
    with np.errstate(divide="ignore", invalid="ignore"):
        t["share"] = np.where(t.oi_usd > 0, t.net_szi / t.oi_usd, np.nan)
    t["elig"] = ((t.vlm >= MIN_VLM_USD) & (t.oi_usd >= MIN_OI_USD) & (t.mark > 0) & np.isfinite(t.share)
                 & (t.status.astype(str) == "active"))
    t = t.drop_duplicates(["run", "coin"])
    return t[cols].reset_index(drop=True)


# ---------------------------------------------------------------- inputs
def px_read():
    files = sorted((J / "px").glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=["t", "coin", "close", "rate"])
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True)


def px_add(rows):
    """Append rows whose (t, coin) is new to journal/px/<month>.csv; stored rows are never rewritten."""
    old = px_read()
    have = set(zip(old.t.astype(np.int64), old.coin)) if len(old) else set()
    new = pd.DataFrame([r for r in rows if (r[0], r[1]) not in have], columns=["t", "coin", "close", "rate"])
    new = new[np.isfinite(new.close.astype(float))]
    if new.empty:
        return 0
    (J / "px").mkdir(parents=True, exist_ok=True)
    new["month"] = [fh.day_label(x)[:7] for x in new.t]
    for m, g in new.sort_values(["t", "coin"]).groupby("month"):
        p = J / "px" / f"{m}.csv"
        g.drop(columns="month").to_csv(p, mode="a", header=not p.exists(), index=False, lineterminator="\n")
    return len(new)


def fetch_lighter(coin, start, end):
    """Closed hourly candles (t = bar open) and the funding settled at each bar's open, as (t, coin, close, rate)."""
    c = carrylane.lighter_prices(coin, start, end)
    c = c[(c.t >= start) & (c.t + H <= end)]
    f = carrylane.lighter_funding(coin, start, end)
    fr = dict(zip((f.t.astype(np.int64) // H * H), f.rate)) if len(f) else {}
    return [(int(t), coin, float(cl), fr.get(int(t), np.nan)) for t, cl in zip(c.t, c.close)]


# ---------------------------------------------------------------- forward
def forward(snap_dir, status_only=False):
    llp = Path(snap_dir) / "llp"
    pos, mk, acc = (hi.read_days(llp / k) for k in ("positions", "markets", "accounts"))
    t0 = fh.ms(FWD_START)
    if mk.empty or acc.empty or int(mk.ts.max()) < t0:
        log("no LLP snapshot on or after", FWD_START)
        return None
    tab = snapshots(pos, mk, acc)
    tab = tab[tab.run >= t0 - H]
    last_run = int(tab.run.max())
    coins = sorted(set(tab.coin[tab.elig]))
    now = int(time.time() * 1000) // H * H
    if not status_only:
        store = px_read()
        got = []
        for c in coins:
            done = store[store.coin == c].t.max() if len(store) else np.nan
            start = max(t0, int(done) + H) if np.isfinite(done) else t0
            if start < now:
                try:
                    got += fetch_lighter(c, start, now)
                except KeyError:                    # no longer listed by Lighter: no closes, its slices count 0
                    log("not listed on Lighter, skipped:", c)
        log("px rows added", px_add(got))
    store = px_read()
    known_last = int(store.t.max()) if len(store) else t0
    end = min(known_last, last_run // H * H)                # as R454
    T = max(0, (end - t0) // H)
    D = T // 24
    tt = t0 + np.arange(T + 1) * H
    fr = {c: g[["t", "close", "rate"]] for c, g in store.groupby("coin")}
    close = fh.grid({c: fr.get(c) for c in coins}, tt, "close")
    rate = fh.grid({c: fr.get(c) for c in coins}, tt, "rate")
    ret = fh.hl_returns(close, rate)
    ind, basket, opened = hi.build(tab, coins, t0, T, close)
    have = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame()
    done = set(zip(have.day, have.book)) if len(have) else set()
    rows, coin_rows = [], []
    if D and not status_only:
        for b_name in BOOKS:
            res = {cm: hi.book_days(ind[b_name], ret, basket, D, cm) for cm in (1.0, 2.0, 3.0)}
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
                             "kind": hi.day_kind(day, n_open)})
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
            return float(np.quantile(hi.placebo_means(ind[b_name], ret, basket, D, idx, seed=SEED), 1 - hi.ALPHA))
        return thr

    st = {"data_commit": hi.git_head(snap_dir),
          "last_snapshot": pd.Timestamp(last_run, unit="ms", tz="UTC").isoformat(),
          "runs": int(tab.run.nunique()), "rows": int(T), "rows_opened": int(opened.sum()), "complete_days": int(D),
          "coins_ever_eligible": len(coins)}
    tk = pd.read_csv(J / "tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame(
        columns=["day", "book", "net", "net_2x", "net_3x", "kind"])
    cs = pd.read_csv(J / "coins.csv") if (J / "coins.csv").exists() else pd.DataFrame(
        columns=["day", "book", "coin", "gross"])
    for b_name in BOOKS:
        st[b_name] = hi.read_decision(tk, cs, b_name, threshold_for(b_name))
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
