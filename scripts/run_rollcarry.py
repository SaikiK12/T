"""rollcarry_v1 (M532), frozen in experiments/rollcarry_v1/PREREG.md: does the funding on trade.xyz's futures-priced
perps exceed the futures roll its oracle passes to longs?

trade.xyz prices NATGAS, CL (WTI) and BRENTOIL from futures. On business days 5-9 of each month its oracle moves from
the front to the next contract in 20% steps (17:30 ET). In contango that adds the calendar spread to the perp price, so
longs gain it and pay for it in funding. A short perp hedged with a fund that holds the front futures (UNG, USO, BNO:
excess return plus T-bills, no roll jump) earns funding minus that roll-up, plus mark noise.

Book per pair, continuous from the first mark a week after the perp's first funding print to the last fund close:
- Long the fund and short the same notional of the perp. The perp margin is M = 1/3 of notional in USDC.
- Daily mark at 16:00 New York (the fund's close): fund close; perp = close of the 1 h candle ending at 16:00, else
  the latest 4 h candle that ended within the 4 hours before 16:00 (before the 1 h history begins).
- Hourly funding is credited on the short at the price of the candle ending at that hour.
- Re-split when the hedge drifts 5% or the margin leaves [M/2, 1.5 M], as in R474.
- Liquidation: if a candle high between marks takes the margin below maintenance (half the initial margin at the
  maximum leverage: NATGAS 5%, CL and BRENTOIL 2.5%), the whole USDC margin is lost (isolated margin, R475's policy);
  funding stops at that candle and the book re-splits at the next mark.
- Costs: 5 bp of fund traded, 2.9 bp of perp notional traded, 10 bp of USDC moved; entry and exit included.
Weekly excess over the 13-week bill (^IRX); Newey-West t (lag 4); annualized x 52.
Samples: A = weeks whose last mark is on or before 2026-07-22 (decides, NATGAS-UNG only); B = later weeks (reported:
their funding was scanned before the freeze). CL-USO and BRENTOIL-BNO are reported.

usage: python scripts/run_rollcarry.py [--data data/rollcarry]
"""
import argparse
import json
import math
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "rollcarry_v1"
DATA = ROOT / "data" / "rollcarry"
REGISTRY = "R478"
PAIRS = {"NATGAS": "UNG", "CL": "USO", "BRENTOIL": "BNO"}
DECIDES = "NATGAS"
MAINT = {"NATGAS": 0.05, "CL": 0.025, "BRENTOIL": 0.025}
M = 1 / 3
FUND_BP, LEG_BP, XFER_BP = 5.0, 2.9, 10.0
DRIFT = 0.05
MARGIN_LO, MARGIN_HI = M / 2, 1.5 * M
HOUR = 3_600_000
WARMUP_DAYS = 7
A_END = "2026-07-22"
LAST = "2026-11-11"
MIN_WEEKS_A = 12
MAX_MISSING = 0.10
HURDLE, T_PASS, NW_LAG = 2.0, 2.0, 4
# NYSE full-day closures that fall on weekdays (business days for the roll count are weekdays without these).
HOLIDAYS = {"2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
            "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def mark_ms(day):
    """16:00 New York on a fund trading day, in ms UTC."""
    t = pd.Timestamp(f"{day} 16:00").tz_localize("America/New_York").tz_convert("UTC")
    return int(t.value // 1_000_000)


def price_at(c1, c4, t_ms):
    """(price, source) at t_ms: close of the 1 h candle ending at t_ms, else of the latest 4 h candle ending in
    [t_ms - 4 h, t_ms]; (nan, '') if neither exists."""
    o1 = c1["open_ms"].to_numpy(np.int64)
    i = np.searchsorted(o1, t_ms - HOUR)
    if i < len(o1) and o1[i] == t_ms - HOUR:
        return float(c1["close"].iloc[i]), "1h"
    o4 = c4["open_ms"].to_numpy(np.int64)
    j = np.searchsorted(o4, t_ms - 4 * HOUR, side="right") - 1
    if j >= 0 and t_ms - 8 * HOUR <= o4[j]:
        return float(c4["close"].iloc[j]), "4h"
    return math.nan, ""


def highs_between(c1, c4, lo_ms, hi_ms):
    """Candles (end_ms, high) that end in (lo_ms, hi_ms]: 1 h where the 1 h history covers lo_ms, else 4 h."""
    if len(c1) and int(c1["open_ms"].iloc[0]) <= lo_ms:
        c, w = c1, HOUR
    else:
        c, w = c4, 4 * HOUR
    end = c["open_ms"].to_numpy(np.int64) + w
    sel = (end > lo_ms) & (end <= hi_ms)
    return end[sel], c["high"].to_numpy(float)[sel]


def simulate(name, fund, c1, c4, funding, irx, first, last):
    """Daily hedged book for one pair. Returns one row per fund close (missing perp marks skipped)."""
    days = fund[(fund["date"] >= first) & (fund["date"] <= last)].dropna(subset=["close"]).reset_index(drop=True)
    rate = irx.set_index("date")["close"].sort_index()
    f_t = funding["time"].to_numpy(np.int64)
    f_r = funding["fundingRate"].to_numpy(float)
    maint = MAINT[name]
    rows, prev, missing = [], None, 0
    q = u = usdc = 0.0
    for _, d in days.iterrows():
        t, p = mark_ms(d["date"]), float(d["close"])
        x, src = price_at(c1, c4, t)
        if not np.isfinite(x):
            missing += 1
            continue
        bill = rate[rate.index <= d["date"]]
        r_ann = float(bill.iloc[-1]) / 100 if len(bill) else 0.0
        if prev is None:
            val = 1 / (1 + M)
            q, u, usdc = val / p, val / x, 1 - val
            cost = (FUND_BP * val + LEG_BP * val + XFER_BP * usdc) / 1e4
            usdc -= cost
            rows.append({"date": d["date"], "src": src, "fund_px": p, "perp": x, "fund": 0.0, "perp_pnl": 0.0,
                         "etf_pnl": 0.0, "bill": 0.0, "cost": cost, "resplit": 1, "liq": 0, "margin_pre": M,
                         "equity": q * p + usdc})
            prev = {"t": t, "p": p, "x": x, "r": r_ann}
            continue
        # liquidation check on candle highs since the last mark
        stop_ms, liq = t, 0
        if u > 0:
            ends, highs = highs_between(c1, c4, prev["t"], t)
            breach = (usdc - u * (highs - prev["x"])) < maint * u * highs
            if breach.any():
                stop_ms, liq = int(ends[np.argmax(breach)]), 1
        sel = (f_t > prev["t"]) & (f_t <= stop_ms)
        fund_amt = 0.0
        for ft, r in zip(f_t[sel], f_r[sel]):
            xf, _ = price_at(c1, c4, int(ft - ft % HOUR))
            if np.isfinite(xf):
                fund_amt += r * u * xf
        etf_pnl = q * (p - prev["p"])
        if liq:
            perp_pnl = -usdc               # the isolated margin is lost; funding up to the breach is kept
            usdc = fund_amt
            u_before, u = u, 0.0
        else:
            perp_pnl = -u * (x - prev["x"])
            usdc += perp_pnl + fund_amt
            u_before = u
        etf_val, notional = q * p, u * x
        equity = etf_val + usdc
        bill_acc = prev["r"] * (t - prev["t"]) / HOUR / 24 / 365
        margin = usdc / notional if notional > 0 else 0.0
        cost, resplit = 0.0, 0
        if liq or abs(notional - etf_val) / etf_val > DRIFT or not (MARGIN_LO <= margin <= MARGIN_HI):
            target = equity / (1 + M)
            cost = (FUND_BP * abs(target - etf_val) + LEG_BP * abs(target - notional)
                    + XFER_BP * abs((equity - target) - usdc)) / 1e4
            q, u, usdc = target / p, target / x, equity - target - cost
            resplit = 1
        rows.append({"date": d["date"], "src": src, "fund_px": p, "perp": x, "fund": fund_amt, "perp_pnl": perp_pnl,
                     "etf_pnl": etf_pnl, "bill": bill_acc, "cost": cost, "resplit": resplit, "liq": liq,
                     "margin_pre": margin if not liq else 0.0, "equity": q * p + usdc, "u_before": u_before})
        prev = {"t": t, "p": p, "x": x, "r": r_ann}
    df = pd.DataFrame(rows)
    if len(df):
        i = df.index[-1]
        exit_cost = (FUND_BP * q * df.at[i, "fund_px"] + LEG_BP * u * df.at[i, "perp"] + XFER_BP * max(usdc, 0.0)) / 1e4
        df.at[i, "cost"] += exit_cost
        df.at[i, "equity"] -= exit_cost
    df.attrs["missing_marks"] = missing
    return df


def weekly(daily):
    """ISO-week returns of equity (the first week against 1) with the bill, legs and cost of each week."""
    d = daily.assign(wk=pd.to_datetime(daily["date"]).dt.strftime("%G-W%V"))
    g = d.groupby("wk", sort=True)
    end = g["equity"].last()
    start = end.shift(1).fillna(1.0)
    out = pd.DataFrame({"last": g["date"].last(), "ret": end / start - 1, "bill": g["bill"].sum(),
                        "fund": g["fund"].sum(), "perp_pnl": g["perp_pnl"].sum(), "etf_pnl": g["etf_pnl"].sum(),
                        "cost": g["cost"].sum(), "liq": g["liq"].sum()})
    out["excess"] = out["ret"] - out["bill"]
    return out.reset_index()


def stats(wk, daily, funding):
    if len(wk) < 2:
        return {"weeks": int(len(wk))}
    n, mu, t = newey_west_t(wk["excess"].to_numpy(float), NW_LAG)
    days = daily[pd.to_datetime(daily["date"]).dt.strftime("%G-W%V").isin(set(wk["wk"]))]
    lo, hi = mark_ms(days["date"].iloc[0]), mark_ms(days["date"].iloc[-1])
    fr = funding[(funding["time"] > lo) & (funding["time"] <= hi)]["fundingRate"].astype(float)
    ann = lambda s: float(s.sum() / len(wk) * 52 * 100)  # noqa: E731
    return {"weeks": int(n), "first_week_end": wk["last"].iloc[0], "last_week_end": wk["last"].iloc[-1],
            "ann_excess_pct": float(mu * 52 * 100), "nw_t": float(t),
            "ann_excess_2x_pct": float((mu - wk["cost"].mean()) * 52 * 100),
            "ann_excess_3x_pct": float((mu - 2 * wk["cost"].mean()) * 52 * 100),
            "ann_vol_pct": float(wk["excess"].std(ddof=1) * math.sqrt(52) * 100),
            "weekly_sd_pct": float(wk["excess"].std(ddof=1) * 100),
            "funding_ann_pct": ann(wk["fund"]), "perp_price_ann_pct": ann(wk["perp_pnl"]),
            "fund_price_ann_pct": ann(wk["etf_pnl"]), "cost_ann_pct": ann(wk["cost"]), "bill_ann_pct": ann(wk["bill"]),
            "liquidations": int(wk["liq"].sum()),
            "funding_rate_ann_pct_mean": float(fr.mean() * 24 * 365 * 100) if len(fr) else math.nan,
            "share_hours_shorts_pay": float((fr < 0).mean()) if len(fr) else math.nan}


def bdays(year, month):
    d, out = date(year, month, 1), []
    while d.month == month:
        if d.weekday() < 5 and d.isoformat() not in HOLIDAYS:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def cycles(daily):
    """Roll-to-roll cycles: from the mark of business day 10 (the first after a completed roll) to the next one.
    Sums of the legs per cycle, as shares of capital; 'gap' = perp + fund price legs (minus the roll-up, plus noise)."""
    if not len(daily):
        return pd.DataFrame()
    first, last = pd.Timestamp(daily["date"].iloc[0]), pd.Timestamp(daily["date"].iloc[-1])
    edges, y, m = [], first.year, first.month
    while (y, m) <= (last.year, last.month):
        b = bdays(y, m)
        if len(b) >= 10:
            edges.append(b[9])
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    rows = []
    for a, b in zip(edges, edges[1:]):
        g = daily[(daily["date"] > a) & (daily["date"] <= b)]
        if not len(g) or a < daily["date"].iloc[0]:
            continue
        rows.append({"from": a, "to": b, "marks": int(len(g)), "fund": float(g["fund"].sum()),
                     "perp_pnl": float(g["perp_pnl"].sum()), "etf_pnl": float(g["etf_pnl"].sum()),
                     "gap": float(g["perp_pnl"].sum() + g["etf_pnl"].sum()), "cost": float(g["cost"].sum()),
                     "bill": float(g["bill"].sum()), "liq": int(g["liq"].sum())})
    return pd.DataFrame(rows)


def verdict(st, missing, marks):
    if st.get("weeks", 0) < MIN_WEEKS_A:
        return "INCONCLUSIVE", f"{st.get('weeks', 0)} weeks in A < {MIN_WEEKS_A}"
    if missing > MAX_MISSING * (marks + missing):
        return "INCONCLUSIVE", f"{missing} fund closes without a perp price"
    text = (f"A {st['weeks']} weeks: excess {st['ann_excess_pct']:+.2f} pts/yr over the bill (NW t {st['nw_t']:.2f}), "
            f"2x {st['ann_excess_2x_pct']:+.2f}, 3x {st['ann_excess_3x_pct']:+.2f}; funding "
            f"{st['funding_ann_pct']:+.2f}, perp price {st['perp_price_ann_pct']:+.2f}, fund price "
            f"{st['fund_price_ann_pct']:+.2f}, liquidations {st['liquidations']}")
    if st["ann_excess_pct"] >= HURDLE and st["nw_t"] >= T_PASS and st["ann_excess_2x_pct"] > 0:
        return "PASS", text
    if st["ann_excess_pct"] > 0:
        return "PARTIAL", text
    if st["nw_t"] <= -T_PASS:
        return "NULL", text + "; the reverse book (long perp, short futures) is a new idea, not a result"
    return "NULL", text


def verify_data(data):
    man = json.loads((data / "manifest.json").read_text())
    for rel, meta in man["files"].items():
        if prereg.sha256_file(data / rel) != meta["sha256"]:
            raise SystemExit(f"manifest mismatch: {rel}")
    return len(man["files"])


def load(data):
    out = {}
    irx = pd.read_parquet(data / "yahoo" / "IRX.parquet")
    for name, etf in PAIRS.items():
        fnd = pd.read_csv(data / "xyz" / f"{name}_funding.csv")
        c4 = pd.read_csv(data / "xyz" / f"{name}_4h.csv").sort_values("open_ms").reset_index(drop=True)
        c1 = pd.read_csv(data / "xyz" / f"{name}_1h.csv").sort_values("open_ms").reset_index(drop=True)
        fund = pd.read_parquet(data / "yahoo" / f"{etf}.parquet")
        out[name] = {"etf": etf, "funding": fnd, "c1": c1, "c4": c4, "fund": fund}
    return out, irx


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    log(f"data files verified: {verify_data(data)}")
    pairs, irx = load(data)
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    out = {"registry": REGISTRY, "decides": f"{DECIDES}-{PAIRS[DECIDES]}", "pairs": {}}
    for name, pr in pairs.items():
        fnd = pr["funding"]
        if not len(fnd):
            out["pairs"][name] = {"etf": pr["etf"], "state": "no funding"}
            continue
        listed = pd.to_datetime(int(fnd["time"].iloc[0]), unit="ms").strftime("%Y-%m-%d")
        first = (pd.Timestamp(listed) + pd.Timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
        daily = simulate(name, pr["fund"], pr["c1"], pr["c4"], fnd, irx, first, LAST)
        wk = weekly(daily)
        a, b = wk[wk["last"] <= A_END], wk[wk["last"] > A_END]
        cyc = cycles(daily)
        st = {"etf": pr["etf"], "first_funding": listed, "book_first": daily["date"].iloc[0] if len(daily) else None,
              "marks": int(len(daily)), "missing_marks": int(daily.attrs.get("missing_marks", 0)),
              "marks_from_4h": int((daily["src"] == "4h").sum()) if len(daily) else 0,
              "resplits": int(daily["resplit"].sum()) if len(daily) else 0,
              "min_margin": float(daily["margin_pre"].min()) if len(daily) else math.nan,
              "A": stats(a, daily, fnd), "B": stats(b, daily, fnd), "all": stats(wk, daily, fnd),
              "cycles": cyc.to_dict(orient="records")}
        if name == DECIDES:
            st["verdict"], st["text"] = verdict(st["A"], st["missing_marks"], st["marks"])
            out["state"], out["text"] = st["verdict"], st["text"]
        out["pairs"][name] = st
        daily.to_csv(res / f"daily_{name}.csv", index=False)
        wk.to_csv(res / f"weekly_{name}.csv", index=False)
        cyc.to_csv(res / f"cycles_{name}.csv", index=False)
        log(f"{name}-{pr['etf']}: A {st['A']} | B {st['B']}")
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    log(out.get("state"), out.get("text"))
    return out.get("state")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args()
    run(data=Path(a.data))


if __name__ == "__main__":
    main()
