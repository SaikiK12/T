"""llpstake_v1 (R447, M506): Lighter's LLP pool as a depositor must hold it. Lighter takes LLP deposits only from LIT
stakers, up to 10 USDC per LIT staked. One unit of the book stakes 1 LIT (fixed 6%/yr staking reward), deposits
10 USDC in LLP and shorts 1 LIT on Lighter's LIT perp with margin equal to its notional. The short cancels the stake's
price move. Read as a return on capital against the 4% hurdle. Rule, costs, windows and decision are in
experiments/llpstake_v1/PREREG.md.

Data, on the data branch claude/okx-xperp-data: vaults/llp/share_prices (scripts/record_dex_vaults.py) and lit/
(scripts/record_lit_hedge.py). LLP's return is R446's (the frozen scripts/run_dexvault.py); the report and the gate-1
decision are R441's (the frozen scripts/run_xperp_carry.py). Paper only: it reads files and writes results.

usage: python scripts/run_llpstake.py --data DIR --window gate0|forward [--until YYYY-MM-DD] [--out DIR] [--status]
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
_spec = importlib.util.spec_from_file_location("run_dexvault", ROOT / "scripts" / "run_dexvault.py")
dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dv)
rx = dv.rx

LANE = ROOT / "experiments" / "llpstake_v1"
DAY = rx.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_llpstake.py checks these against the PREREG text
USDC_PER_LIT = 10.0                  # LLP deposit per LIT staked (Lighter's cap, used in full)
STAKE_APR = 0.06                     # Lighter's fixed staking reward, paid in LIT, valued at the spot close
MARGIN_K = 1.0                       # the short's margin, as a multiple of its notional at the previous close
MAINT = 0.20                         # maintenance margin assumed for the liquidation check
COST_STAKE_RT = 0.0040               # one round trip a year on the stake and its hedge: 10 bp a leg a side, 4 legs
COST_LLP_RT = 0.0010                 # one round trip a year on the LLP deposit (R446's)
HURDLE_ANN = rx.HURDLE_ANN           # 4%
WINDOWS = {"gate0": ("2026-01-15", "2026-11-10"), "forward": ("2026-11-11", None)}
LOOKS = {90: "2027-02-08", 180: "2027-05-09"}
DAILY_COLS = ["day", "held", "forced", "missing", "capital", "w_llp", "llp", "stake", "funding", "price", "cost_1x",
              "gross", "net_1x", "net_2x", "net_3x", "naked_1x"]


# ---------------------------------------------------------------- data
def candle_closes(data, which):
    """Daily closes (and highs) by UTC day label of the bar's open."""
    c = rx.read_dir(Path(data) / "lit" / f"{which}_candles_1d")
    if not len(c):
        return pd.DataFrame(columns=["close", "high"])
    c = c.drop_duplicates("ts").sort_values("ts")
    c.index = [rx.day_label(t) for t in c.ts]
    return c[["close", "high"]].astype(float)


def funding_by_day(data):
    """Sum of the short's received hourly rate (+ when longs pay) and the count of hours, by UTC day."""
    f = rx.read_dir(Path(data) / "lit" / "perp_funding")
    if not len(f):
        return pd.DataFrame(columns=["rate", "hours"])
    f = f.drop_duplicates("ts")
    f["day"] = [rx.day_label(t) for t in f.ts]
    return f.groupby("day").agg(rate=("rate", "sum"), hours=("rate", "size"))


# ---------------------------------------------------------------- book
def run(data, start, end):
    """One row per UTC day in [start, end] for one unit (1 LIT staked, 10 USDC in LLP, 1 LIT short)."""
    days = [rx.day_label(t) for t in range(rx.ms(start), rx.ms(end) + DAY, DAY)]
    pre = rx.day_label(rx.ms(start) - DAY)
    spot, perp, fund = candle_closes(data, "spot"), candle_closes(data, "perp"), funding_by_day(data)
    llp = {d: r for d, _, r in dv.llp_periods(dv.llp_prices(data), start, end)}
    idx = sorted(set(spot.index) | set(perp.index) | {pre} | set(days))
    s = spot.close.reindex(idx).ffill()
    p = perp.close.reindex(idx).ffill()
    hi = perp.high.reindex(idx)
    rows = []
    for d in days:
        i = idx.index(d)
        s0, p0, s1, p1 = s.iloc[i - 1], p.iloc[i - 1], s.iloc[i], p.iloc[i]
        if not (np.isfinite(s0) and np.isfinite(p0) and s0 > 0 and p0 > 0):
            rows.append({"day": d, "held": 0, "forced": 0, "missing": 1, **{c: 0.0 for c in DAILY_COLS[4:]}})
            continue
        cap = USDC_PER_LIT + s0 + MARGIN_K * p0
        r_llp = llp.get(d)
        miss = int(r_llp is None or d not in spot.index or d not in perp.index or d not in fund.index)
        r_llp = 0.0 if r_llp is None else r_llp
        f = float(fund.rate.get(d, 0.0))
        llp_pnl, stake_pnl, fund_pnl = USDC_PER_LIT * r_llp, s0 * STAKE_APR / 365, p0 * f
        price_pnl = (s1 - s0) - (p1 - p0)                            # spot stake against the perp short: the basis
        forced = 0
        h = hi.get(d)
        if h is not None and np.isfinite(h) and h >= p0 * (1 + MARGIN_K) / (1 + MAINT):
            forced = 1                                               # the short is liquidated: its whole margin
            price_pnl = (s1 - s0) - MARGIN_K * p0                    # is lost, and the hedge is put back at close
        cost = (COST_STAKE_RT * s0 + COST_LLP_RT * USDC_PER_LIT) / 365
        gross = (llp_pnl + stake_pnl + fund_pnl + price_pnl) / cap
        naked_cap = USDC_PER_LIT + s0                                # reported: the stake held without the short
        naked = (llp_pnl + stake_pnl + (s1 - s0) - (COST_STAKE_RT / 2 * s0 + COST_LLP_RT * USDC_PER_LIT) / 365) \
            / naked_cap
        rows.append({"day": d, "held": 1, "forced": forced, "missing": miss, "capital": cap,
                     "w_llp": USDC_PER_LIT / cap, "llp": llp_pnl / cap, "stake": stake_pnl / cap,
                     "funding": fund_pnl / cap, "price": price_pnl / cap, "cost_1x": cost / cap, "gross": gross,
                     "net_1x": gross - cost / cap, "net_2x": gross - 2 * cost / cap, "net_3x": gross - 3 * cost / cap,
                     "naked_1x": naked})
    return pd.DataFrame(rows, columns=DAILY_COLS)


def parts(daily):
    """Annualized parts of the 1x net on capital, and the reported naked-stake read."""
    if not len(daily):
        return {}
    out = {k: float(daily[k].mean() * 365) for k in ("llp", "stake", "funding", "price")}
    out["cost_1x"] = -float(daily.cost_1x.mean() * 365)
    out["avg_w_llp"] = float(daily.w_llp[daily.held == 1].mean()) if (daily.held == 1).any() else None
    x = daily.naked_1x.to_numpy(float)
    out["naked_net_ann"] = float(x.mean() * 365)
    out["naked_sd_daily"] = float(x.std(ddof=1)) if len(x) > 1 else float("nan")
    return out


def decide_gate0(s):
    """Gate 0 decides only a stop."""
    e1 = s["1x"]["excess_ann"]
    return "NULL (stop)" if e1 is None or e1 < 0 else "CONTINUE to gate 1"


def last_day(data):
    """The last UTC day every input covers."""
    ends = []
    pr = dv.llp_prices(data)
    if len(pr):
        ends.append(rx.day_label(pr.index[-1]))
    for which in ("spot", "perp"):
        c = candle_closes(data, which)
        if len(c):
            ends.append(c.index[-1])
    f = funding_by_day(data)
    full = f[f.hours >= 24]
    if len(full):
        ends.append(full.index[-1])
    return min(ends) if len(ends) == 4 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--window", choices=sorted(WINDOWS), required=True)
    ap.add_argument("--until", help="last day of a forward read (default: the last day every input covers)")
    ap.add_argument("--status", action="store_true", help="forward progress read: no decision")
    ap.add_argument("--out")
    a = ap.parse_args()
    from lab import prereg
    prereg.verify(LANE / "PREREG.md")
    pinned = rx.check_inputs(LANE / "PREREG.md")
    if a.window == "gate0" and rx.data_head(a.data) != pinned:
        raise SystemExit(f"gate 0 reads the data branch at {pinned} only; {a.data} is at {rx.data_head(a.data)}")
    start, end = WINDOWS[a.window]
    if a.window == "forward":
        end = a.until or last_day(a.data) or rx.day_label(rx.ms(start) - DAY)     # no data yet: an empty read
    out = Path(a.out) if a.out else LANE / "results" / (a.window + ("_status" if a.status else ""))
    out.mkdir(parents=True, exist_ok=True)
    daily = run(a.data, start, end) if end >= start else pd.DataFrame(columns=DAILY_COLS)
    s = rx.summary(daily)
    s["missing_days"] = int(daily.missing.sum()) if len(daily) else 0
    s["parts"] = parts(daily)
    if a.window == "gate0":
        s["decision"] = decide_gate0(s)
    elif not a.status:
        n = s["days"]
        look = max((k for k in LOOKS if n >= k), default=None)
        s["decision"] = rx.decide(s, look) if look else f"no look reached ({n} scored days)"
    rep = {"window": a.window, "start": start, "end": end, **s}
    daily.to_csv(out / "daily.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=float) + "\n")
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
