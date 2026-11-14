"""ltroll_v1 (R481, M532 on Lighter): did Lighter's funding on its futures-priced commodity perps exceed the roll-up
the oracle passed to longs, before Lighter moved WTI, NATGAS and XCU to RedStone prices on 2026-10-22?

Per roll month M (business days from R478's NYSE calendar, scripts/run_rollcarry.py), marks at 20:00 UTC:
    r(day) = Lighter perp close / Yahoo continuous front close - 1      (the 1-hour bars ending at the mark)
    roll_M = r(BD10) - r(BD4)          the roll-up the oracle passed to longs (R478's post hoc identity)
    roll_wide_M = r(BD12) - r(BD3)     the same with a wider bracket (reported)
A cycle runs from the BD10 mark of M-1 (or the first Lighter candle close, if later) to the BD10 mark of M:
    fund_c = sum of hourly funding prints in (start, end], signed + when longs pay = what the short received
    net_c  = fund_c - roll_M                                              (fraction of notional)
    cost_c = 8 bp when the hedge rolls (4 bp a leg) + 2 bp of margin re-splits, + 9 bp entry in the first cycle and
             9 bp exit in the last (perp 5 bp, futures 4 bp)
    bill_c = 13-week bill (^IRX, the latest close on or before each day) accrued over the cycle
    excess_c(k) = 0.75 x (net_c - k x cost_c) - 0.25 x bill_c             (fraction of capital; notional = 3/4)
The hedge (a fully collateralised futures position on the contracts the oracle references) earns the bill on its 3/4
of capital, so only the idle quarter lags the bill. Annualized excess = sum of excess_c / years spanned x 100;
t = mean / (sd / sqrt(n)) over cycles. NATGAS decides; WTI, BRENTOIL and XCU are reported.

usage: .venv/bin/python scripts/run_ltroll.py [--no-check]
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_rollcarry as rc  # noqa: E402  (frozen in R478; bdays only)
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "ltroll_v1"
DATA = ROOT / "data" / "ltroll"
REGISTRY = "R481"
DECIDES = "NATGAS"
FRONT = {"NATGAS": "NG_F", "WTI": "CL_F", "BRENTOIL": "BZ_F", "XCU": "HG_F"}
MONTHS = [(2026, m) for m in range(2, 11)]          # roll months February .. October 2026
DOCUMENTED = {"2026-07", "2026-08", "2026-09", "2026-10"}  # months in Lighter's published roll table
XCU_ROLLS = {2, 4, 6, 8, 11}                        # copper's bimonthly roll months (H/K/N/U/Z)
NOTIONAL = 0.75
ROLL_BP, RESPLIT_BP, ENTRY_BP = 8.0, 2.0, 9.0
MAX_LAG_H = 3                                       # a mark may fall back up to 3 hours to a common bar end
H = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def mark(day):
    return int(pd.Timestamp(f"{day} 20:00", tz="UTC").value // 1_000_000)


def close_ending(df, col, t_ms):
    """Close of the bar that opened at t_ms - 1 h (ends at t_ms), or nan."""
    o = df[col].to_numpy(np.int64)
    i = np.searchsorted(o, t_ms - H)
    return float(df["close"].iloc[i]) if i < len(o) and o[i] == t_ms - H else math.nan


def r_at(perp, front, t_ms):
    """(r, lag hours): perp / front - 1 at the latest common bar end in [t_ms - 3 h, t_ms]; (nan, -1) if none."""
    for k in range(MAX_LAG_H + 1):
        p = close_ending(perp, "t", t_ms - k * H)
        f = close_ending(front, "open_ms", t_ms - k * H)
        if p == p and f == f and f > 0:
            return p / f - 1, k
    return math.nan, -1


def bill(irx, start_ms, end_ms):
    """The 13-week bill accrued from start to end (fraction), on the latest ^IRX close on or before each day."""
    rate = irx.set_index("date")["close"].sort_index()
    days = pd.date_range(pd.to_datetime(start_ms, unit="ms").normalize(), pd.to_datetime(end_ms, unit="ms"), freq="D")
    acc = 0.0
    for d in days:
        lo = max(start_ms, int(d.value // 1_000_000))
        hi = min(end_ms, int((d + pd.Timedelta(days=1)).value // 1_000_000))
        if hi <= lo:
            continue
        b = rate[rate.index <= d.strftime("%Y-%m-%d")]
        acc += (float(b.iloc[-1]) / 100 if len(b) else 0.0) * (hi - lo) / H / 24 / 365
    return acc


def cycles(name, perp, funding, front, irx):
    rows, start_data = [], int(perp["t"].iloc[0]) + H
    end_data = int(perp["t"].iloc[-1]) + H
    for y, m in MONTHS:
        b = rc.bdays(y, m)
        py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
        start = max(mark(rc.bdays(py, pm)[9]), start_data)
        t4, t10 = mark(b[3]), mark(b[9])
        if t4 <= start or t10 > end_data:
            continue
        r4, l4 = r_at(perp, front, t4)
        r10, l10 = r_at(perp, front, t10)
        r3, _ = r_at(perp, front, mark(b[2]))
        r12, _ = r_at(perp, front, mark(b[11]))
        f = funding[(funding["t"] > start) & (funding["t"] <= t10)]
        rolls = m in XCU_ROLLS if name == "XCU" else True
        p0 = close_ending(perp, "t", start)
        held = perp[(perp["t"] + H > start) & (perp["t"] + H <= t10)]["close"]
        rows.append({"market": name, "month": f"{y}-{m:02d}", "start": pd.to_datetime(start, unit="ms").isoformat(),
                     "end": b[9], "bd4": b[3], "hours": int((t10 - start) // H), "prints": int(len(f)),
                     "fund": float(f["rate"].sum()),
                     "short_pays_share": float((f["rate"] < 0).mean()) if len(f) else math.nan,
                     "r_bd4": r4, "r_bd10": r10, "lag_bd4": l4, "lag_bd10": l10, "roll": r10 - r4,
                     "roll_wide": r12 - r3, "hedge_rolls": int(rolls),
                     "cost_bp": (ROLL_BP if rolls else 0.0) + RESPLIT_BP,
                     "bill": bill(irx, start, t10),
                     "max_up": float(held.max() / p0 - 1) if p0 > 0 and len(held) else math.nan,
                     "t_start": start, "t_end": t10})
    df = pd.DataFrame(rows)
    if len(df):
        df.loc[df.index[0], "cost_bp"] += ENTRY_BP
        df.loc[df.index[-1], "cost_bp"] += ENTRY_BP
        df["net"] = df["fund"] - df["roll"]
        df["net_wide"] = df["fund"] - df["roll_wide"]
        for k in (1, 2, 3):
            df[f"excess_{k}x"] = NOTIONAL * (df["net"] - k * df["cost_bp"] / 1e4) - (1 - NOTIONAL) * df["bill"]
        df["excess_wide"] = NOTIONAL * (df["net_wide"] - df["cost_bp"] / 1e4) - (1 - NOTIONAL) * df["bill"]
    return df


def stats(df, col="excess_1x"):
    d = df.dropna(subset=[col])
    n = len(d)
    if n < 2:
        return {"cycles": n}
    years = (d["t_end"].iloc[-1] - d["t_start"].iloc[0]) / H / 24 / 365.25
    sd = float(d[col].std(ddof=1))
    mu = float(d[col].mean())
    out = {"cycles": n, "first_start": d["start"].iloc[0], "last_end": d["end"].iloc[-1], "years": years,
           "ann_excess_pct": float(d[col].sum() / years * 100), "t": mu / (sd / math.sqrt(n)) if sd > 0 else math.nan,
           "cycle_mean_pct": mu * 100, "cycle_sd_pct": sd * 100, "positive": int((d[col] > 0).sum())}
    if col == "excess_1x":
        for k in (2, 3):
            out[f"ann_excess_{k}x_pct"] = float(d[f"excess_{k}x"].sum() / years * 100)
        ann = lambda c: float(d[c].sum() / years * 100)  # noqa: E731
        out.update({"funding_ann_pct_notional": ann("fund"), "roll_ann_pct_notional": ann("roll"),
                    "cost_ann_pct_notional": float((d["cost_bp"] / 1e4).sum() / years * 100),
                    "bill_ann_pct": ann("bill"), "net_mean_pct_notional": float(d["net"].mean() * 100),
                    "net_sd_pct_notional": float(d["net"].std(ddof=1) * 100),
                    "abs_r_bd4_max_pct": float(d["r_bd4"].abs().max() * 100),
                    "marks_lagged": int(((d["lag_bd4"] > 0) | (d["lag_bd10"] > 0)).sum()),
                    "missing_prints": int((d["hours"] - d["prints"]).clip(lower=0).sum()),
                    "max_up_pct": float(d["max_up"].max() * 100)})
    return out


def verdict(st):
    if st.get("cycles", 0) < 2:
        return "NULL"
    if st["ann_excess_pct"] >= 2.0 and st["t"] >= 2.0 and st["ann_excess_2x_pct"] > 0:
        return "PASS"
    return "PARTIAL" if st["ann_excess_pct"] > 0 else "NULL"


def verify_data(data):
    man = json.loads((data / "manifest.json").read_text())
    for rel, meta in man["files"].items():
        if prereg.sha256_file(data / rel) != meta["sha256"]:
            raise SystemExit(f"manifest mismatch: {rel}")
    return len(man["files"])


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    log(f"data files verified: {verify_data(data)}")
    irx = pd.read_csv(data / "yahoo" / "IRX.csv")
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    out, allc = {"registry": REGISTRY, "decides": DECIDES, "markets": {}}, []
    for name, stem in FRONT.items():
        perp = pd.read_csv(data / "lighter" / f"{name}_1h.csv").sort_values("t", ignore_index=True)
        fnd = pd.read_csv(data / "lighter" / f"{name}_funding.csv").sort_values("t", ignore_index=True)
        front = pd.read_csv(data / "yahoo" / f"{stem}_60m.csv").sort_values("open_ms", ignore_index=True)
        df = cycles(name, perp, fnd, front, irx)
        allc.append(df)
        st = stats(df)
        out["markets"][name] = {"all": st, "documented": stats(df[df["month"].isin(DOCUMENTED)]) if len(df) else {},
                                "wide": stats(df, "excess_wide") if len(df) else {}}
        log(f"{name}: {st.get('cycles', 0)} cycles; excess {st.get('ann_excess_pct', math.nan):+.2f} pts/yr "
            f"(t {st.get('t', math.nan):.2f}), 2x {st.get('ann_excess_2x_pct', math.nan):+.2f}")
    out["verdict"] = verdict(out["markets"][DECIDES]["all"])
    cyc = pd.concat(allc, ignore_index=True)
    cyc.drop(columns=["t_start", "t_end"]).to_csv(res / "cycles.csv", index=False, float_format="%.6f")
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    log(f"verdict ({DECIDES}): {out['verdict']}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-check", action="store_true", help="skip the PREREG check (tests only)")
    a = ap.parse_args()
    run(check=not a.no_check)


if __name__ == "__main__":
    main()
