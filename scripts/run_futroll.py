"""R480 futroll_fwd: M532 forward. Short trade.xyz's futures-priced perps and hold the NYMEX contracts their oracle
references, rolled on xyz's own schedule: does the funding longs pay keep exceeding the roll-up the oracle passes
them? NATGAS decides (R478's pre-named pair); CL and BRENTOIL are reported, and so is their equal-weight pool.

The book is R478's frozen `simulate` (run_rollcarry.py) with the US fund replaced by a rolled-futures total-return
index: a fully collateralised long in xyz's designated front and next contracts, re-weighted at each 16:00 New York
mark to the oracle's weights for the next trading day (20% steps after the marks of business days 5-8, all next from
business day 9), plus the 13-week bill on the collateral, minus a cost per roll step. The index does not jump at a
roll; the perp does, so the pair keeps funding - roll-up - costs, plus mark noise. Capital layout, re-split rules,
liquidation on 1-hour highs, costs on the perp leg and transfers, and the weekly statistics are R478's.

Reads (each once, from claude/futroll-data recorded by scripts/record_futroll.py, plus the venue's 4-hour candles
and full funding history and ^IRX fetched at read time):
  futility  cycles 1-6:  marks 2026-11-13 .. 2027-05-14, after 2027-05-15 00:00 UTC; NULL if NATGAS excess < 0.
  final     cycles 1-12: marks 2026-11-13 .. 2027-11-12, after 2027-11-13 00:00 UTC;
            PASS if NATGAS excess >= 2 points/yr over the bill, NW t >= 2.0 and 2x-cost excess > 0;
            PARTIAL if excess > 0; NULL otherwise. A futility NULL stands.
INCONCLUSIVE when NATGAS has fewer weeks than the read's minimum or more than 10% of its marks are missing.

usage: python scripts/run_futroll.py --auto --data .futroll-data      (the workflow)
       python scripts/run_futroll.py --read futility --data .futroll-data
"""
import argparse
import hashlib
import json
import math
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
import run_rollcarry as rc  # noqa: E402  (frozen in R478: simulate, weekly, stats, cycles, bdays, mark_ms)
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "futroll_fwd"
DATA = ROOT / "data" / "futroll_fwd"
REGISTRY = "R480"
START = "2026-11-13"                      # business day 10 of November 2026: the first mark after a completed roll
PAIRS = {"NATGAS": "NG", "CL": "CL", "BRENTOIL": "BZ"}
AHEAD = {"NG": 1, "CL": 1, "BZ": 2}       # xyz's front contract: next calendar month (NG, CL), the one after (BZ)
DECIDES = "NATGAS"
READS = {"futility": {"last": "2027-05-14", "after": "2027-05-15", "cycles": 6, "min_weeks": 18},
         "final": {"last": "2027-11-12", "after": "2027-11-13", "cycles": 12, "min_weeks": 36}}
CODES = "FGHJKMNQUVXZ"
HEDGE_BP = 4.0          # futures leg, per unit traded at entry, exit and re-splits (commission + half a tick)
ROLL_LEG_BP = 4.0       # per leg of each roll step (sell front, buy next)
NEXT_W = {5: 0.2, 6: 0.4, 7: 0.6, 8: 0.8}   # weight on the next contract after the mark of business day b (>= 9: 1)
BAR_WINDOW = 3 * rc.HOUR                    # a contract mark: the latest 60-minute bar ending in (t - 3 h, t]
MAX_MISSING = 0.10
HURDLE, T_PASS, NW_LAG = 2.0, 2.0, 4
# NYSE full-day closures on weekdays in 2027 (R478's list stops at 2026); business days are weekdays without them.
HOLIDAYS_2027 = {"2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05",
                 "2027-09-06", "2027-11-25", "2027-12-24"}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


@contextmanager
def lane_settings():
    """R478's frozen module with this lane's futures-leg cost and the 2027 holidays; restored on exit."""
    old = rc.FUND_BP, rc.HOLIDAYS
    rc.FUND_BP, rc.HOLIDAYS = HEDGE_BP, set(old[1]) | HOLIDAYS_2027
    try:
        yield
    finally:
        rc.FUND_BP, rc.HOLIDAYS = old


def symbol(root, y, m, k):
    """Yahoo symbol of the contract k months after (y, m), e.g. symbol('NG', 2026, 11, 1) = 'NGZ26.NYM'."""
    i = m - 1 + k
    return f"{root}{CODES[i % 12]}{(y + i // 12) % 100:02d}.NYM"


def next_weight(b):
    return 0.0 if b < 5 else NEXT_W.get(b, 1.0)


def held(root, day):
    """Contract weights held after the 16:00 New York mark of `day` (the oracle's weights for the next trading day)."""
    d = date.fromisoformat(day)
    b = rc.bdays(d.year, d.month).index(day) + 1
    w = next_weight(b)
    f, n = symbol(root, d.year, d.month, AHEAD[root]), symbol(root, d.year, d.month, AHEAD[root] + 1)
    return {s: x for s, x in ((f, 1.0 - w), (n, w)) if x > 0}


def contract_mark(bars, t):
    if bars is None or not len(bars):
        return math.nan
    o = bars["open_ms"].to_numpy(np.int64)
    j = np.searchsorted(o, t - rc.HOUR, side="right") - 1
    return float(bars["close"].iloc[j]) if j >= 0 and o[j] + rc.HOUR > t - BAR_WINDOW else math.nan


def business_days(first, last):
    out, y, m = [], int(first[:4]), int(first[5:7])
    while (y, m) <= (int(last[:4]), int(last[5:7])):
        out += [d for d in rc.bdays(y, m) if first <= d <= last]
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def hedge_index(root, bars, irx, first, last):
    """Daily total-return index of the rolled hedge at 16:00 New York (date, close) with its parts per mark:
    ret (contract returns at the previous weights), bill, roll_cost, roll_spread (the jump the oracle's blend makes at
    this mark's re-weighting, at this mark's prices: the roll-up passed to perp longs), weights."""
    rate = irx.set_index("date")["close"].sort_index()
    rows, prev, missing, level = [], None, 0, 1.0
    for day in business_days(first, last):
        t = rc.mark_ms(day)
        new_w = held(root, day)
        need = set(new_w) | (set(prev["w"]) if prev else set())
        px = {s: contract_mark(bars.get(s), t) for s in need}
        if any(not np.isfinite(v) for v in px.values()):
            missing += 1
            continue
        if prev is None:
            rows.append({"date": day, "close": level, "ret": 0.0, "bill": 0.0, "roll_cost": 0.0, "roll_spread": 0.0,
                         "weights": ";".join(f"{s}:{w:.1f}" for s, w in sorted(new_w.items()))})
            prev = {"t": t, "w": new_w, "px": px}
            continue
        ret = sum(w * (px[s] / prev["px"][s] - 1) for s, w in prev["w"].items())
        b = rate[rate.index <= day]
        bill = (float(b.iloc[-1]) / 100 if len(b) else 0.0) * (t - prev["t"]) / rc.HOUR / 24 / 365
        moved = sum(max(new_w.get(s, 0.0) - prev["w"].get(s, 0.0), 0.0) for s in need)
        roll_cost = 2 * moved * ROLL_LEG_BP / 1e4
        old_blend = sum(w * px[s] for s, w in prev["w"].items())
        roll_spread = sum(w * px[s] for s, w in new_w.items()) / old_blend - 1 if moved else 0.0
        level *= 1 + ret + bill - roll_cost
        rows.append({"date": day, "close": level, "ret": ret, "bill": bill, "roll_cost": roll_cost,
                     "roll_spread": roll_spread, "weights": ";".join(f"{s}:{w:.1f}" for s, w in sorted(new_w.items()))})
        prev = {"t": t, "w": new_w, "px": px}
    df = pd.DataFrame(rows)
    df.attrs["missing_marks"] = missing
    return df


def add_roll_costs(daily, idx):
    """Move the index's roll costs into the book's cost column (and out of the hedge leg) so the 2x and 3x lines
    double them too. Equity and weekly returns are unchanged. Hedge value at the mark before: 1/(1+M) of equity
    (R478's split; re-splits keep it within 5%)."""
    if not len(daily):
        return daily
    rcost = daily["date"].map(idx.set_index("date")["roll_cost"]).fillna(0.0)
    amt = daily["equity"].shift(1).fillna(1.0) / (1 + rc.M) * rcost
    out = daily.copy()
    out["cost"] = out["cost"] + amt
    out["etf_pnl"] = out["etf_pnl"] + amt
    out["roll_cost"] = amt
    out.attrs.update(daily.attrs)
    return out


def read_bars(path):
    if not path.exists():
        return None
    return pd.read_csv(path).dropna(subset=["close"]).sort_values("open_ms").reset_index(drop=True)


def load(arch, src, first, last):
    """Per pair: contract bars (archive), perp 1-hour candles (archive), 4-hour candles (read-time fetch), funding
    (archive and read-time fetch, merged by time). Returns (pairs, irx)."""
    irx = pd.read_parquet(src / "yahoo" / "IRX.parquet")
    d0, d1 = date.fromisoformat(first), date.fromisoformat(last)
    pairs = {}
    for name, root in PAIRS.items():
        syms, y, m = set(), d0.year, d0.month
        while (y, m) <= (d1.year, d1.month):
            syms |= {symbol(root, y, m, AHEAD[root]), symbol(root, y, m, AHEAD[root] + 1)}
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        bars = {s: read_bars(arch / "yahoo" / f"{s}.csv") for s in sorted(syms)}
        c1 = read_bars(arch / "xyz" / f"{name}_1h.csv")
        c1 = c1 if c1 is not None else pd.DataFrame(columns=["open_ms", "open", "high", "low", "close", "volume"])
        c4 = pd.read_csv(src / "xyz" / f"{name}_4h.csv").sort_values("open_ms").reset_index(drop=True)
        parts = [pd.read_csv(p) for p in (arch / "xyz" / f"{name}_funding.csv", src / "xyz" / f"{name}_funding.csv")
                 if p.exists()]
        fnd = (pd.concat(parts).drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
               if parts else pd.DataFrame(columns=["time", "fundingRate", "premium"]))
        pairs[name] = {"root": root, "bars": bars, "c1": c1, "c4": c4, "funding": fnd,
                       "contracts_missing": sorted(s for s, b in bars.items() if b is None)}
    return pairs, irx


def fetch_read(after, src):
    """Read-time inputs: the venue's 4-hour candles and full funding history for the three perps, and ^IRX."""
    import fetch_hip3stock as fs  # noqa: E402  (frozen in R475)
    from fetch_hip3carry import retry, yahoo  # noqa: E402  (frozen in R479)
    (src / "xyz").mkdir(parents=True, exist_ok=True)
    (src / "yahoo").mkdir(parents=True, exist_ok=True)
    a, b = fs.ms("2026-10-01"), fs.ms(after)
    for name in PAIRS:
        coin = f"xyz:{name}"
        retry(fs.funding, coin, a, b).to_csv(src / "xyz" / f"{name}_funding.csv", index=False)
        time.sleep(1.5)
        retry(fs.candles, coin, a, b).to_csv(src / "xyz" / f"{name}_4h.csv", index=False)
        time.sleep(1.5)
    yahoo("%5EIRX", "2026-10-01", after, src / "yahoo", "IRX")
    man = {"source": "api.hyperliquid.xyz/info (fundingHistory, candleSnapshot 4h) and query1.finance.yahoo.com "
                     "(^IRX), public, no key", "end": after,
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "files": {str(p.relative_to(src)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(src.rglob("*")) if p.is_file() and p.name != "manifest.json"}}
    (src / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")


def archive_manifest(arch):
    return {str(p.relative_to(arch)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(arch.rglob("*.csv"))}


def pooled(wks):
    """Equal-weight pool of the pairs' weekly excess (weeks where at least one pair has a row)."""
    s = pd.concat({k: w.set_index("wk")["excess"] for k, w in wks.items() if len(w)}, axis=1).sort_index()
    if not len(s):
        return {"weeks": 0}
    x = s.mean(axis=1).to_numpy(float)
    n, mu, t = newey_west_t(x, NW_LAG)
    return {"weeks": int(n), "pairs": list(s.columns), "ann_excess_pct": float(mu * 52 * 100), "nw_t": float(t)}


def verdict(read, st, missing_share, futility_state=None):
    need = READS[read]["min_weeks"]
    if st.get("weeks", 0) < need:
        return "INCONCLUSIVE", f"{st.get('weeks', 0)} weeks < {need}"
    if missing_share > MAX_MISSING:
        return "INCONCLUSIVE", f"{missing_share:.0%} of marks missing > {MAX_MISSING:.0%}"
    text = (f"{st['weeks']} weeks: excess {st['ann_excess_pct']:+.2f} pts/yr over the bill (NW t {st['nw_t']:.2f}), "
            f"2x {st['ann_excess_2x_pct']:+.2f}, 3x {st['ann_excess_3x_pct']:+.2f}; funding {st['funding_ann_pct']:+.2f},"
            f" perp {st['perp_price_ann_pct']:+.2f}, hedge {st['fund_price_ann_pct']:+.2f}, cost "
            f"{st['cost_ann_pct']:.2f}; {st['liquidations']} liquidations")
    if read == "futility":
        return ("NULL" if st["ann_excess_pct"] < 0 else "CONTINUE"), text
    if futility_state == "NULL":
        return "NULL", text + " (stopped at the futility read)"
    if st["ann_excess_pct"] >= HURDLE and st["nw_t"] >= T_PASS and st["ann_excess_2x_pct"] > 0:
        return "PASS", text
    return ("PARTIAL" if st["ann_excess_pct"] > 0 else "NULL"), text


def due(read, now):
    return now >= datetime.strptime(READS[read]["after"], "%Y-%m-%d").replace(tzinfo=timezone.utc)


def run(read, lane=LANE, arch=None, data=DATA, check=True, now=None, fetcher="default"):
    cfg, res = READS[read], lane / "results" / read
    now = now or datetime.now(timezone.utc)
    if (res / "summary.json").exists():
        log(f"{read}: already read; nothing to do")
        return None
    if not due(read, now):
        log(f"{read}: refused before {cfg['after']} 00:00 UTC")
        return None
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    arch = Path(arch) if arch else ROOT / ".futroll-data"
    src = data / read
    if fetcher == "default":
        fetch_read(cfg["after"], src)
    elif fetcher is not None:
        fetcher(cfg["after"], src)
    res.mkdir(parents=True, exist_ok=True)
    fut_state = None
    if read == "final" and (lane / "results" / "futility" / "summary.json").exists():
        fut_state = json.loads((lane / "results" / "futility" / "summary.json").read_text()).get("state")
    out = {"registry": REGISTRY, "read": read, "first": START, "last": cfg["last"], "decides": DECIDES,
           "archive_files": archive_manifest(arch), "pairs": {}}
    wks = {}
    with lane_settings():
        pairs, irx = load(arch, src, START, cfg["last"])
        for name, p in pairs.items():
            idx = hedge_index(p["root"], p["bars"], irx, START, cfg["last"])
            fnd = p["funding"]
            if not len(idx) or not len(fnd):
                out["pairs"][name] = {"state": "no data", "contracts_missing": p["contracts_missing"]}
                continue
            daily = rc.simulate(name, idx[["date", "close"]], p["c1"], p["c4"], fnd, irx, START, cfg["last"])
            daily = add_roll_costs(daily, idx)
            wk = rc.weekly(daily)
            cyc = rc.cycles(daily)
            if len(cyc):
                cyc["roll_spread"] = [float(idx[(idx["date"] > a) & (idx["date"] <= b)]["roll_spread"].sum())
                                      for a, b in zip(cyc["from"], cyc["to"])]
            n_days = len(business_days(START, cfg["last"]))
            miss = idx.attrs["missing_marks"] + daily.attrs.get("missing_marks", 0)
            st = {"contract": PAIRS[name], "marks": int(len(daily)), "business_days": n_days,
                  "index_missing": int(idx.attrs["missing_marks"]),
                  "perp_missing": int(daily.attrs.get("missing_marks", 0)), "missing_share": miss / n_days,
                  "marks_from_4h": int((daily["src"] == "4h").sum()) if len(daily) else 0,
                  "resplits": int(daily["resplit"].sum()) if len(daily) else 0,
                  "min_margin": float(daily["margin_pre"].min()) if len(daily) else math.nan,
                  "contracts_missing": p["contracts_missing"],
                  "roll_spread_sum": float(idx["roll_spread"].sum()), "roll_cost_sum": float(idx["roll_cost"].sum()),
                  "all": rc.stats(wk, daily, fnd), "cycles": cyc.to_dict(orient="records")}
            if name == DECIDES:
                st["verdict"], st["text"] = verdict(read, st["all"], st["missing_share"], fut_state)
                out["state"], out["text"] = st["verdict"], st["text"]
            out["pairs"][name] = st
            wks[name] = wk
            idx.to_csv(res / f"index_{name}.csv", index=False)
            daily.to_csv(res / f"daily_{name}.csv", index=False)
            wk.to_csv(res / f"weekly_{name}.csv", index=False)
            cyc.to_csv(res / f"cycles_{name}.csv", index=False)
            log(f"{name}: {st['all']}")
    if "state" not in out:
        out["state"], out["text"] = "INCONCLUSIVE", f"{DECIDES}: no data"
    out["pooled"] = pooled(wks)
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    log(f"{read}: {out['state']}: {out['text']}")
    return out["state"]


def auto(lane=LANE, arch=None, data=DATA, now=None):
    """The workflow's entry: the futility read, then the final read (a futility NULL stands)."""
    now = now or datetime.now(timezone.utc)
    run("futility", lane, arch, data, now=now)
    run("final", lane, arch, data, now=now)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--read", choices=sorted(READS))
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--data", default=None, help="checkout of claude/futroll-data (the recorder's archive)")
    a = ap.parse_args()
    if a.auto:
        auto(arch=a.data)
    else:
        run(a.read, arch=a.data)


if __name__ == "__main__":
    main()
