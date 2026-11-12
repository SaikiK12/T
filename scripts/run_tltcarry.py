"""R474 tltcarry_fwd, frozen in experiments/tltcarry_fwd/PREREG.md: a hedged carry on trade.xyz's TLT perp.

Long the iShares $ Treasury Bond 20+yr UCITS ETF (DTLA, London, USD, accumulating; same ICE index as TLT) and short
the same notional of xyz:TLT, whose oracle follows TLT's unadjusted price. The book earns the bonds' coupons (through
the ETF) plus the funding that xyz:TLT longs pay, without interest-rate risk. Paper only, decided forward.

Daily mark at the London close (16:30 Europe/London): ETF close; perp = mean of the open and close of the 1 h candle
containing the mark (the 16:30 price is mid-candle; hourly candles are all the venue keeps for months).
Hourly funding is credited on the short at the close of the candle ending at that hour. The perp margin is M = 1/3
of notional in USDC. Re-split (ETF, perp notional, cash) when the hedge drifts 5% or the margin leaves [M/2, 1.5 M].
Costs: 5 bp of ETF traded, 2.9 bp of perp notional traded, 10 bp of cash moved between venues; entry and exit included.

Reads (each once; the runner refuses a read before its date and does nothing once its summary.json exists):
  held      2026-09-24 .. 2026-11-11, already partly seen (xyz funding); reported, decides nothing
  futility  2026-11-16 .. 2027-02-12, on or after 2027-02-13: NULL (stop) if the annualized excess is below 0
  final     2026-11-16 .. 2027-05-14, on or after 2027-05-15: PASS if excess >= 2 points a year at NW t >= 2.0

usage: python scripts/run_tltcarry.py --read held | --auto      (--auto: the due forward reads, for the workflow)
"""
import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "tltcarry_fwd"
DATA = ROOT / "data" / "tltcarry"
REGISTRY = "R474"
START = "2026-11-16"
M = 1 / 3                       # USDC margin per unit of perp notional (3x)
ETF_BP, LEG_BP, XFER_BP = 5.0, 2.9, 10.0
DRIFT = 0.05
MARGIN_LO, MARGIN_HI = M / 2, 1.5 * M
MAINT = 0.025                   # xyz:TLT maintenance margin at 20x maximum leverage (half the initial)
HOUR = 3_600_000
READS = {
    "held": {"first": "2026-09-24", "last": "2026-11-11", "after": None, "fetch": ("2026-09-17", "2026-11-12"),
             "min_weeks": 4},
    "futility": {"first": START, "last": "2027-02-12", "after": "2027-02-13", "fetch": ("2026-11-09", "2027-02-13"),
                 "min_weeks": 10},
    "final": {"first": START, "last": "2027-05-14", "after": "2027-05-15", "fetch": ("2026-11-09", "2027-05-15"),
              "min_weeks": 22},
}
HURDLE = 2.0                    # points a year above the 13-week bill
T_PASS = 2.0
NW_LAG = 4
MAX_MISSING = 0.10              # share of London closes without a perp candle that makes a read INCONCLUSIVE
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def mark_ms(day):
    """16:30 London on an LSE trading day, in ms UTC."""
    t = pd.Timestamp(f"{day} 16:30").tz_localize("Europe/London").tz_convert("UTC")
    return int(t.value // 1_000_000)


def perp_at(candles, t_ms, mid=False):
    """Close (or the mean of open and close, mid=True) of the 1 h candle whose hour contains t_ms; NaN if missing."""
    o = candles["open_ms"].to_numpy(np.int64)
    i = np.searchsorted(o, t_ms, side="right") - 1
    if i < 0 or t_ms >= o[i] + HOUR:
        return math.nan
    c = float(candles["close"].iloc[i])
    return (float(candles["open"].iloc[i]) + c) / 2 if mid else c


def simulate(etf, candles, funding, irx, first, last):
    """Daily book from the first to the last LSE close. Returns one row per mark."""
    days = etf[(etf["date"] >= first) & (etf["date"] <= last)].dropna(subset=["close"]).reset_index(drop=True)
    rate = irx.set_index("date")["close"].sort_index()
    f_t = funding["time"].to_numpy(np.int64)
    f_r = funding["fundingRate"].to_numpy(float)
    rows, prev, missing = [], None, 0
    for _, d in days.iterrows():
        t, p = mark_ms(d["date"]), float(d["close"])
        x = perp_at(candles, t, mid=True)
        if not np.isfinite(x):
            missing += 1
            continue
        bill = rate[rate.index <= d["date"]]
        r_ann = float(bill.iloc[-1]) / 100 if len(bill) else 0.0
        if prev is None:
            etf_val = 1 / (1 + M)
            q, u, usdc = etf_val / p, etf_val / x, 1 - etf_val
            cost = (ETF_BP * etf_val + LEG_BP * etf_val + XFER_BP * usdc) / 1e4
            usdc -= cost
            rows.append({"date": d["date"], "etf": p, "perp": x, "fund": 0.0, "perp_pnl": 0.0, "etf_pnl": 0.0,
                         "bill": 0.0, "cost": cost, "resplit": 1, "margin_pre": M, "equity": q * p + usdc})
            prev = {"t": t, "p": p, "x": x, "r": r_ann}
            continue
        sel = (f_t > prev["t"]) & (f_t <= t)
        px_f = [perp_at(candles, ft - ft % HOUR - 1) for ft in f_t[sel]]
        fund = sum(r * u * xf for r, xf in zip(f_r[sel], px_f) if np.isfinite(xf))
        perp_pnl = -u * (x - prev["x"])
        etf_pnl = q * (p - prev["p"])
        usdc += perp_pnl + fund
        etf_val, notional = q * p, u * x
        equity = etf_val + usdc
        bill_acc = prev["r"] * (t - prev["t"]) / HOUR / 24 / 365
        margin = usdc / notional
        cost, resplit = 0.0, 0
        if abs(notional - etf_val) / etf_val > DRIFT or not (MARGIN_LO <= margin <= MARGIN_HI):
            target = equity / (1 + M)
            cost = (ETF_BP * abs(target - etf_val) + LEG_BP * abs(target - notional)
                    + XFER_BP * abs((equity - target) - usdc)) / 1e4
            q, u, usdc = target / p, target / x, equity - target - cost
            resplit = 1
        rows.append({"date": d["date"], "etf": p, "perp": x, "fund": fund, "perp_pnl": perp_pnl, "etf_pnl": etf_pnl,
                     "bill": bill_acc, "cost": cost, "resplit": resplit, "margin_pre": margin,
                     "equity": q * p + usdc})
        prev = {"t": t, "p": p, "x": x, "r": r_ann}
    df = pd.DataFrame(rows)
    if len(df):
        last_row = df.index[-1]
        exit_cost = (ETF_BP * q * df.at[last_row, "etf"] + LEG_BP * u * df.at[last_row, "perp"]
                     + XFER_BP * max(usdc, 0.0)) / 1e4
        df.at[last_row, "cost"] += exit_cost
        df.at[last_row, "equity"] -= exit_cost
    df.attrs["missing_marks"] = missing
    return df


def weekly(daily):
    """ISO-week returns of equity (the first week against the starting equity of 1) and the bill over each week."""
    d = daily.assign(wk=pd.to_datetime(daily["date"]).dt.strftime("%G-W%V"))
    g = d.groupby("wk", sort=True)
    end = g["equity"].last()
    start = end.shift(1).fillna(1.0)
    out = pd.DataFrame({"ret": end / start - 1, "bill": g["bill"].sum(), "fund": g["fund"].sum(),
                        "price": g["perp_pnl"].sum() + g["etf_pnl"].sum(), "cost": g["cost"].sum()})
    out["excess"] = out["ret"] - out["bill"]
    return out.reset_index()


def stats(daily, wk, funding, first, last):
    if len(wk) < 2:
        return {"weeks": int(len(wk))}
    n, mu, t = newey_west_t(wk["excess"].to_numpy(float), NW_LAG)
    eq = daily["equity"].to_numpy(float)
    lo, hi = mark_ms(daily["date"].iloc[0]), mark_ms(daily["date"].iloc[-1])
    fr = funding[(funding["time"] > lo) & (funding["time"] <= hi)]["fundingRate"].astype(float)
    return {"weeks": int(n), "days": int(len(daily)), "missing_marks": int(daily.attrs.get("missing_marks", 0)),
            "first": daily["date"].iloc[0], "last": daily["date"].iloc[-1],
            "ann_return_pct": float(wk["ret"].mean() * 52 * 100), "ann_excess_pct": float(mu * 52 * 100),
            "nw_t": float(t), "ann_vol_pct": float(wk["excess"].std(ddof=1) * math.sqrt(52) * 100),
            "funding_pct": float(daily["fund"].sum() * 100), "price_pct": float((daily["perp_pnl"]
                                                                                 + daily["etf_pnl"]).sum() * 100),
            "cost_pct": float(daily["cost"].sum() * 100), "bill_pct": float(daily["bill"].sum() * 100),
            "ann_excess_2x_pct": float((mu - wk["cost"].mean()) * 52 * 100),
            "ann_excess_3x_pct": float((mu - 2 * wk["cost"].mean()) * 52 * 100),
            "resplits": int(daily["resplit"].sum()), "min_margin": float(daily["margin_pre"].min()),
            "below_maintenance_days": int((daily["margin_pre"] < MAINT).sum()),
            "max_dd_pct": float(np.max(np.maximum.accumulate(eq) - eq) * 100),
            "funding_hours": int(len(fr)), "share_hours_shorts_pay": float((fr < 0).mean()) if len(fr) else math.nan,
            "funding_ann_pct_mean": float(fr.mean() * 24 * 365 * 100) if len(fr) else math.nan}


def verdict(read, st):
    if st.get("weeks", 0) < READS[read]["min_weeks"]:
        return "INCONCLUSIVE", f"{st.get('weeks', 0)} weeks < {READS[read]['min_weeks']}"
    if st["missing_marks"] > MAX_MISSING * (st["days"] + st["missing_marks"]):
        return "INCONCLUSIVE", f"{st['missing_marks']} London closes without a perp price (halt or delisting)"
    text = (f"{st['weeks']} weeks: excess {st['ann_excess_pct']:+.2f} pts/yr over the bill (NW t {st['nw_t']:.2f}), "
            f"return {st['ann_return_pct']:+.2f}%/yr; funding {st['funding_pct']:+.2f}%, "
            f"price {st['price_pct']:+.2f}%, "
            f"cost {st['cost_pct']:.2f}%, min margin {st['min_margin']:.3f}")
    if read == "held":
        return "REPORTED", text
    if read == "futility":
        return ("NULL" if st["ann_excess_pct"] < 0 else "CONTINUE"), text
    if st["ann_excess_pct"] >= HURDLE and st["nw_t"] >= T_PASS:
        return "PASS", text
    return ("PARTIAL" if st["ann_excess_pct"] > 0 else "NULL"), text


def verify_data(data):
    man = json.loads((data / "manifest.json").read_text())
    for rel, meta in man["files"].items():
        if prereg.sha256_file(data / rel) != meta["sha256"]:
            raise SystemExit(f"manifest mismatch: {rel}")
    return len(man["files"])


def due(read, now):
    after = READS[read]["after"]
    return after is None or now >= datetime.strptime(after, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def run(read, lane=LANE, data=DATA, check=True, now=None, fetcher="default"):
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
    src = data / read
    if fetcher == "default":
        from fetch_tltcarry import fetch
        fetch(cfg["fetch"][0], cfg["fetch"][1], src)
    elif fetcher is not None:
        fetcher(cfg["fetch"][0], cfg["fetch"][1], src)
    log(f"{read}: data files verified: {verify_data(src)}")
    meta = json.loads((src / "yahoo" / "DTLA.json").read_text())["chart"]["result"][0]["meta"]
    if meta.get("currency") != "USD":
        raise SystemExit(f"DTLA is quoted in {meta.get('currency')}, not USD")
    etf = pd.read_parquet(src / "yahoo" / "DTLA.parquet")
    irx = pd.read_parquet(src / "yahoo" / "IRX.parquet")
    funding = pd.read_csv(src / "xyz" / "funding.csv")
    candles = pd.read_csv(src / "xyz" / "candles_1h.csv")
    daily = simulate(etf, candles, funding, irx, cfg["first"], cfg["last"])
    wk = weekly(daily) if len(daily) else pd.DataFrame()
    st = stats(daily, wk, funding, cfg["first"], cfg["last"]) if len(daily) else {"weeks": 0}
    state, text = verdict(read, st)
    res.mkdir(parents=True, exist_ok=True)
    daily.to_csv(res / "daily.csv", index=False)
    wk.to_csv(res / "weekly.csv", index=False)
    (res / "summary.json").write_text(json.dumps({"registry": REGISTRY, "read": read, "state": state, "text": text,
                                                  "stats": st}, indent=1, default=float) + "\n")
    log(read, state, text)
    return state


def auto(lane=LANE, data=DATA, now=None):
    """The workflow's entry: the futility read, then the final read unless the futility read stopped the lane."""
    now = now or datetime.now(timezone.utc)
    run("futility", lane, data, now=now)
    fut = lane / "results" / "futility" / "summary.json"
    if fut.exists() and json.loads(fut.read_text())["state"] == "NULL":
        log("final: skipped, the futility read stopped the lane")
        return
    run("final", lane, data, now=now)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--read", choices=sorted(READS))
    g.add_argument("--auto", action="store_true")
    a = ap.parse_args()
    if a.auto:
        auto()
    else:
        run(a.read)


if __name__ == "__main__":
    main()
