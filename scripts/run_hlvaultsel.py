"""hlvaultsel_v1 (R450, M507): Hyperliquid user vaults picked by their past record. At each month end, among vaults at
least 180 days old holding at least $500k, deposit equally in the 10 with the best ratio of mean to sd of their period
returns over the past 180 days (past return above 0), for one month. Net of the leader's profit share on gains and a
switching cost; an empty slot earns the hurdle. Read against the 4% hurdle. Rule, windows and decision are in
experiments/hlvaultsel_v1/PREREG.md.

Data: the data branch claude/hl-vaults-data (scripts/record_hl_vaults.py): every vault in the public list, closed ones
included, and each vault's allTime account value and pnl. Paper only: it reads files and writes results.

usage: python scripts/run_hlvaultsel.py --data DIR --window gate0|forward [--out DIR]
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "hlvaultsel_v1"
DAY = 86_400_000
# ---- the frozen rule (PREREG "Rule"); tests/test_run_hlvaultsel.py checks these against the PREREG text
MIN_AGE_DAYS = 180
MIN_AV = 500_000.0
LOOKBACK_DAYS = 180
MIN_PERIODS = 6
MIN_ACTIVE = 0.8                     # share of the window's periods whose pnl changed (no dormant vault)
TOP_N = 10
DEFAULT_COMMISSION = 0.10            # the leader's profit share when the vault's own is not on file
SWITCH_COST = 0.0010                 # withdrawal and deposit of one slot's capital, at 1x
HURDLE_ANN = 0.04
NW_LAG = 3
EXCLUDE = {"0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"}      # HLP, a protocol vault (R446)
WINDOWS = {"gate0": ("2024-01-31", "2026-09-30"), "forward": ("2026-11-30", None)}
LOOK_MONTHS = 12                     # forward decision after 12 held months


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def month_ends(first, last):
    return [str(d.date()) for d in pd.date_range(first, last, freq="ME")]


# ---------------------------------------------------------------- data
def load(data):
    """{address: (ts array, account value array, pnl array)} for eligible kinds, and {address: (created_ms, fee)}."""
    data = Path(data)
    idx = {r["address"]: r for r in csv.DictReader(open(data / "index.csv", newline=""))}
    meta = {r["address"]: r for r in csv.DictReader(open(data / "meta.csv", newline=""))} \
        if (data / "meta.csv").exists() else {}
    hist, info = {}, {}
    for p in sorted((data / "hist").glob("*/*.csv")):
        a = p.stem
        r = idx.get(a)
        if r is None or r["relationship"] == "child" or a in EXCLUDE:
            continue
        h = pd.read_csv(p).drop_duplicates("ts").sort_values("ts")
        hist[a] = (h.ts.to_numpy(np.int64), h.account_value.to_numpy(float), h.pnl.to_numpy(float))
        fee = meta.get(a, {}).get("leader_commission", "")
        info[a] = (int(float(r["created_ms"])) if r["created_ms"] else 0,
                   float(fee) if fee not in ("", None) else DEFAULT_COMMISSION)
    return hist, info


def at(h, t):
    """Index of the last point at or before t, or None."""
    i = int(np.searchsorted(h[0], t, side="right")) - 1
    return i if i >= 0 else None


def period_returns(h, i0, i1):
    """Returns between consecutive points i0..i1: the pnl change over the capital at risk, the larger of the account
    value at the period's start and that value plus the period's net inflow (account value change minus pnl change).
    A deposit inside a period thus does not inflate its return, and a withdrawal does not either. A period with no
    capital returns 0."""
    _, av, pnl = h
    dp = np.diff(pnl[i0:i1 + 1])
    base = np.maximum(av[i0:i1], av[i0 + 1:i1 + 1] - dp)
    return np.where(base > 0, dp / np.where(base > 0, base, 1.0), 0.0).clip(-1.0, None)


def score(h, t):
    """Mean over sd of the period returns in (t - LOOKBACK, t], with their sum; None if too few periods, or if the
    pnl changed in fewer than MIN_ACTIVE of them (a dormant vault's rare moves give a tiny sd and a high score)."""
    i0, i1 = at(h, t - LOOKBACK_DAYS * DAY), at(h, t)
    if i0 is None or i1 is None or i1 - i0 < MIN_PERIODS:
        return None
    if h[1][i0] <= 0:
        return None
    if (np.diff(h[2][i0:i1 + 1]) != 0).mean() < MIN_ACTIVE:
        return None
    r = period_returns(h, i0, i1)
    sd = r.std(ddof=1)
    if not np.isfinite(sd) or sd <= 0:
        return None
    return float(r.mean() / sd), float(r.sum())


def held_return(h, t0, t1):
    """The period returns chained from the last point at or before t0 to the last point at or before t1."""
    i0, i1 = at(h, t0), at(h, t1)
    if i0 is None or i1 is None or i1 <= i0 or h[1][i0] <= 0:
        return 0.0
    return float(np.prod(1.0 + period_returns(h, i0, i1)) - 1.0)


# ---------------------------------------------------------------- book
def run(hist, info, first, last):
    """One row per formation month end in [first, last]: picks, gross and net returns held to the next month end."""
    rows, prev = [], set()
    for f in month_ends(first, last):
        t0 = ms(f) + DAY - 1                                          # the end of the formation day
        nxt = (pd.Timestamp(f) + pd.offsets.MonthEnd(1)).date()
        t1 = ms(str(nxt)) + DAY - 1
        cand = []
        elig = 0
        for a, h in hist.items():
            created, _ = info[a]
            i = at(h, t0)
            if created > t0 - MIN_AGE_DAYS * DAY or i is None or h[1][i] < MIN_AV:
                continue
            elig += 1
            sc = score(h, t0)
            if sc is not None and sc[1] > 0:
                cand.append((sc[0], a))
        picks = [a for _, a in sorted(cand, reverse=True)[:TOP_N]]
        gross = [held_return(hist[a], t0, t1) for a in picks]
        net = [g - info[a][1] * max(g, 0.0) for g, a in zip(gross, picks)]
        new = len(set(picks) - prev)
        gone = len(prev - set(picks))
        cost = SWITCH_COST * max(new, gone) / TOP_N
        days = (t1 - t0) / DAY
        idle = HURDLE_ANN * days / 365 * (TOP_N - len(picks))         # an empty slot earns the hurdle (cash)
        book_net = (sum(net) + idle) / TOP_N
        rows.append({"formation": f, "held_to": str(nxt), "days": days, "eligible": elig, "candidates": len(cand),
                     "picks": len(picks), "new": new, "gross": (sum(gross) + idle) / TOP_N, "net_fee": book_net,
                     "cost_1x": cost, "net_1x": book_net - cost, "net_2x": book_net - 2 * cost,
                     "net_3x": book_net - 3 * cost, "addresses": " ".join(picks)})
        prev = set(picks)
    return pd.DataFrame(rows)


def eligible_mean(hist, info, first, last):
    """Reported only: the equal-weight return of every eligible vault, net of its fee, by month."""
    out = []
    for f in month_ends(first, last):
        t0 = ms(f) + DAY - 1
        t1 = ms(str((pd.Timestamp(f) + pd.offsets.MonthEnd(1)).date())) + DAY - 1
        rs = []
        for a, h in hist.items():
            i = at(h, t0)
            if info[a][0] > t0 - MIN_AGE_DAYS * DAY or i is None or h[1][i] < MIN_AV:
                continue
            g = held_return(h, t0, t1)
            rs.append(g - info[a][1] * max(g, 0.0))
        out.append(float(np.mean(rs)) if rs else 0.0)
    return out


def summary(book):
    out = {"months": int(len(book))}
    if not len(book):
        return out
    hurdle = HURDLE_ANN * book.days.to_numpy() / 365
    years = book.days.sum() / 365
    for m in ("1x", "2x", "3x"):
        x = book[f"net_{m}"].to_numpy(float)
        _, _, t = newey_west_t(x - hurdle, NW_LAG)
        out[m] = {"net_ann": float(x.sum() / years), "excess_ann": float((x - hurdle).sum() / years),
                  "nw_t_excess": t}
    x = book.net_1x.to_numpy(float)
    cum = np.cumsum(x)
    out["max_dd"] = float((cum - np.maximum.accumulate(np.maximum(cum, 0))).min())
    out["worst_month"] = float(x.min())
    out["worst_month_formation"] = str(book.formation.iloc[int(x.argmin())])
    out["sd_month"] = float(np.std(x - hurdle, ddof=1)) if len(x) > 1 else float("nan")
    out["avg_picks"] = float(book.picks.mean())
    out["avg_new"] = float(book.new.mean())
    out["fee_ann"] = float((book.gross - book.net_fee).sum() / years)
    return out


def last_formation(first, today):
    """The last month end from `first` whose holding month has ended before `today` (forward reads)."""
    done = [f for f in month_ends(first, today) if pd.Timestamp(f) + pd.offsets.MonthEnd(1) < today]
    return done[-1] if done else str((pd.Timestamp(first) - pd.offsets.MonthEnd(1)).date())


def decide_gate0(s):
    """Gate 0 decides: EARNED (forward continues) or NULL."""
    e1, t1, e2 = s["1x"]["excess_ann"], s["1x"]["nw_t_excess"], s["2x"]["excess_ann"]
    ok = e1 is not None and e1 >= 0.03 and np.isfinite(t1) and t1 >= 2.0 and e2 > 0
    return "EARNED (forward continues)" if ok else "NULL (stop)"


def decide_forward(s):
    if s["months"] < LOOK_MONTHS:
        return f"no look reached ({s['months']} held months)"
    return "CONFIRMED" if s["1x"]["excess_ann"] > 0 else "NOT CONFIRMED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--window", choices=sorted(WINDOWS), required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    import importlib.util
    from lab import prereg
    spec = importlib.util.spec_from_file_location("run_xperp_carry", ROOT / "scripts" / "run_xperp_carry.py")
    rx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rx)
    prereg.verify(LANE / "PREREG.md")
    pinned = rx.check_inputs(LANE / "PREREG.md")
    if a.window == "gate0" and rx.data_head(a.data) != pinned:
        raise SystemExit(f"gate 0 reads the data branch at {pinned} only; {a.data} is at {rx.data_head(a.data)}")
    first, last = WINDOWS[a.window]
    if last is None:
        last = last_formation(first, pd.Timestamp.now(tz="UTC").normalize().tz_localize(None))
    out = Path(a.out) if a.out else LANE / "results" / a.window
    out.mkdir(parents=True, exist_ok=True)
    hist, info = load(a.data)
    book = run(hist, info, first, last) if last >= first else pd.DataFrame()
    s = summary(book)
    s["vaults_with_history"] = len(hist)
    if len(book):
        s["eligible_mean_ann"] = float(np.sum(eligible_mean(hist, info, first, last)) / (book.days.sum() / 365))
        s["decision"] = decide_gate0(s) if a.window == "gate0" else decide_forward(s)
    rep = {"window": a.window, "first_formation": first, "last_formation": last, **s}
    book.to_csv(out / "months.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
