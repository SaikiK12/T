"""xvroll_fwd (R482, M533): forward paper pair on the same futures-priced commodity perp on two venues. Short
trade.xyz's perp and hold Lighter's long at equal notional. Both oracles track the same NYMEX/ICE futures, so the roll
and the price mostly net out; the pair keeps xyz's funding minus Lighter's, plus the basis between the two perps, minus
costs. NATGAS decides; WTI (xyz:CL) and BRENTOIL are reported.

The book, per pair (capital 1 at the first mark, 2026-11-16 20:00 UTC):
- Notional per leg N = L x equity, L = 1.5; each leg's margin starts at equity / 2 = N / 3 (M = 1/3), in USDC.
- Hourly, on the grid of 1-hour bar ends: each leg takes its price PnL (bar closes) and its funding print for that hour
  (xyz: fundingRate, + when longs pay, so the short receives rate x qty x close; Lighter: rate, + when longs pay, so
  the long pays it).
- Liquidation, checked each hour before the close: the xyz short at the bar's high and the Lighter long at the bar's low
  against maintenance (xyz NATGAS 5%, CL and BRENTOIL 2.5%; Lighter NATGAS 6%, WTI and BRENTOIL 3%). A liquidated leg
  loses its whole margin; the other leg is closed at that hour's close; the book re-enters at the next daily mark.
- Daily marks at 20:00 UTC (every calendar day; both perps trade around the clock). The book re-splits when a leg's
  margin leaves [M/2, 1.5 M] of its notional or the two notionals drift more than 5% apart: both legs are resized to
  N = L x equity and the margins re-split, moving USDC between the venues.
- Costs per unit traded: xyz 4.9 bp (2.9 bp taker in growth mode + 2 bp half-spread), Lighter 3 bp (Standard account,
  0 fee, + 3 bp half-spread); 10 bp of the USDC moved between venues. The 2x and 3x lines subtract the cost again.
- Idle USDC earns nothing. The hurdle is the 13-week bill (^IRX) on equity.
Weekly statistics as R478 and R480: ISO weeks of equity, excess over the bill, Newey-West t (lag 4), x 52.

Reads (`--auto`, the workflow): futility after 2027-05-15 00:00 UTC (weeks ending by 05-14; NULL if NATGAS excess
< 0, else CONTINUE) and final after 2027-11-13 00:00 UTC (weeks ending by 11-12; PASS at >= 2 pts/yr, NW t >= 2 and
2x > 0; PARTIAL > 0; NULL otherwise; a futility NULL stands). A read with more than 10% of hours missing on either leg,
or too few weeks, is INCONCLUSIVE. Each read fetches its inputs (xyz funding and 1-hour candles, merged with the
1-hour candles R480's recorder keeps on claude/futroll-data; Lighter 1-hour candles and funding; ^IRX), lists their
sha256 and writes results/<read>/ once.

usage: python scripts/run_xvroll.py --auto --data .futroll-data      (the workflow)
       python scripts/run_xvroll.py --read futility --data .futroll-data
"""
import argparse
import hashlib
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
from lab import carrylane as cl  # noqa: E402
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
import fetch_hip3stock as fs  # noqa: E402  (frozen in R475)
from fetch_cryptomon import CHART, epoch, parse_chart  # noqa: E402  (frozen in R471)
from fetch_hip3carry import retry  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "xvroll_fwd"
DATA = ROOT / "data" / "xvroll"
REGISTRY = "R482"
DECIDES = "NATGAS"
PAIRS = {"NATGAS": ("xyz:NATGAS", "NATGAS", "NATGAS"),       # name: (xyz coin, Lighter symbol, recorder file stem)
         "WTI": ("xyz:CL", "WTI", "CL"),
         "BRENTOIL": ("xyz:BRENTOIL", "BRENTOIL", "BRENTOIL")}
START = "2026-11-16"                                         # first mark, 20:00 UTC
MARK_H = 20
L = 1.5
M = 1 / (2 * L)
MAINT_X = {"NATGAS": 0.05, "WTI": 0.025, "BRENTOIL": 0.025}
MAINT_L = {"NATGAS": 0.06, "WTI": 0.03, "BRENTOIL": 0.03}
COST_X_BP, COST_L_BP, TRANSFER_BP = 4.9, 3.0, 10.0
DRIFT = 0.05
READS = {"futility": {"last": "2027-05-14", "after": "2027-05-15", "min_weeks": 22},
         "final": {"last": "2027-11-12", "after": "2027-11-13", "min_weeks": 44}}
MAX_MISSING = 0.10
HURDLE, T_PASS, NW_LAG = 2.0, 2.0, 4
H = 3_600_000
DAY = 24 * H
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def ms(day, hour=0):
    return int(pd.Timestamp(f"{day} {hour:02d}:00", tz="UTC").value // 1_000_000)


# ---------------------------------------------------------------------------------------------------- inputs
def xyz_1h(coin, start_ms, end_ms):
    """xyz 1-hour candles (the venue keeps the latest 5,000), in R480's recorder layout."""
    page = retry(fs.post, {"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": start_ms,
                                                            "endTime": end_ms}}) or []
    cols = ["open_ms", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(page)
    if not len(df):
        return pd.DataFrame(columns=cols)
    df = df.rename(columns={"t": "open_ms", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df[cols]


def lighter_1h(sym, start_ms, end_ms):
    """Lighter 1-hour candles with high and low (lab.carrylane's paced, locked client), 480 a call."""
    mid, out, s = cl._lighter_id(sym), [], start_ms - start_ms % H
    while s < end_ms:
        e = min(end_ms, s + 480 * H)
        out += cl._lighter("candles", market_id=mid, resolution="1h", start_timestamp=s, end_timestamp=e,
                           count_back=0).get("c") or []
        s = e
    cols = ["open_ms", "open", "high", "low", "close", "volume"]
    if not out:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame({"open_ms": [int(r["t"]) for r in out], "open": [float(r["o"]) for r in out],
                         "high": [float(r["h"]) for r in out], "low": [float(r["l"]) for r in out],
                         "close": [float(r["c"]) for r in out], "volume": [float(r.get("v", 0.0)) for r in out]})


def merge_bars(*frames):
    df = pd.concat([f for f in frames if f is not None and len(f)], ignore_index=True) if any(
        f is not None and len(f) for f in frames) else pd.DataFrame(columns=["open_ms", "high", "low", "close"])
    df["open_ms"] = df["open_ms"].astype("int64")
    return df.drop_duplicates("open_ms", keep="last").sort_values("open_ms", ignore_index=True)


def fetch(read, arch, out, start_ms, end_ms):
    """Every input of a read into out/ (CSV), with the sha256 of each file and of each recorded file used."""
    out.mkdir(parents=True, exist_ok=True)
    rec = {}
    for name, (coin, lsym, stem) in PAIRS.items():
        rf = Path(arch) / "xyz" / f"{stem}_1h.csv" if arch else None
        recorded = pd.read_csv(rf) if rf is not None and rf.exists() else None
        if recorded is not None:
            rec[str(rf)] = prereg.sha256_file(rf)
        merge_bars(recorded, xyz_1h(coin, start_ms - DAY, end_ms)).to_csv(out / f"xyz_{name}_1h.csv", index=False)
        time.sleep(1.5)
        retry(fs.funding, coin, start_ms - DAY, end_ms).to_csv(out / f"xyz_{name}_funding.csv", index=False)
        time.sleep(1.5)
        lighter_1h(lsym, start_ms - DAY, end_ms).to_csv(out / f"lighter_{name}_1h.csv", index=False)
        cl.lighter_funding(lsym, start_ms - DAY, end_ms).to_csv(out / f"lighter_{name}_funding.csv", index=False)
    a = (datetime.fromtimestamp(start_ms / 1000, timezone.utc) - pd.Timedelta(days=20)).strftime("%Y-%m-%d")
    b = datetime.fromtimestamp(end_ms / 1000, timezone.utc).strftime("%Y-%m-%d")
    raw = retry(fs.request, CHART.format(t="%5EIRX", a=epoch(a), b=epoch(b)))
    parse_chart(json.loads(raw))[["date", "close"]].to_csv(out / "IRX.csv", index=False)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.csv"))}
    return {"fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": files, "recorded": rec}


def load(src, name):
    xb = pd.read_csv(src / f"xyz_{name}_1h.csv")
    xf = pd.read_csv(src / f"xyz_{name}_funding.csv").rename(columns={"time": "t", "fundingRate": "rate"})
    lb = pd.read_csv(src / f"lighter_{name}_1h.csv")
    lf = pd.read_csv(src / f"lighter_{name}_funding.csv")
    return xb, xf[["t", "rate"]], lb, lf[["t", "rate"]]


# ---------------------------------------------------------------------------------------------------- the book
def on_grid(bars, grid):
    """close, high, low of the bars ending at each grid time (open = end - 1 h); closes carried over gaps."""
    b = bars.assign(end=bars["open_ms"].astype("int64") + H).drop_duplicates("end", keep="last").set_index("end")
    b = b.reindex(grid)
    miss = b["close"].isna().to_numpy()
    c = b["close"].astype(float).ffill().to_numpy()
    hi = b["high"].astype(float).to_numpy()
    lo = b["low"].astype(float).to_numpy()
    hi = np.where(np.isnan(hi), c, hi)
    lo = np.where(np.isnan(lo), c, lo)
    return c, hi, lo, miss


def rates_on_grid(f, grid):
    """Funding prints summed by the nearest hour, aligned with the grid; 0 where there is none."""
    if not len(f):
        return np.zeros(len(grid))
    k = (np.round(f["t"].astype("int64").to_numpy() / H) * H).astype("int64")
    s = pd.Series(f["rate"].astype(float).to_numpy()).groupby(k).sum()
    return s.reindex(grid).fillna(0.0).to_numpy()


def simulate(name, xb, xf, lb, lf, start_ms, end_ms):
    """Hourly book from the mark at start_ms to the mark at end_ms. Returns daily rows (one per 20:00 UTC mark)."""
    grid = np.arange(start_ms, end_ms + H, H, dtype=np.int64)
    cx, hx, _, mx_miss = on_grid(xb, grid)
    cl_, _, ll, ml_miss = on_grid(lb, grid)
    rx, rl = rates_on_grid(xf, grid), rates_on_grid(lf, grid)
    bx, bl = COST_X_BP / 1e4, COST_L_BP / 1e4
    E, active, qx, ql, mx, ml = 1.0, False, 0.0, 0.0, 0.0, 0.0
    stranded = 0.0                    # USDC left on one venue by a liquidation, moved at the next entry
    acc = dict(fund_x=0.0, fund_l=0.0, pnl_x=0.0, pnl_l=0.0, cost=0.0, liq=0, resplit=0)
    rows, e_prev = [], 1.0

    def enter(E, transfer):
        nonlocal qx, ql, mx, ml, active
        n = L * E
        if not (cx[i] > 0 and cl_[i] > 0):
            return E
        nqx, nql = n / cx[i], n / cl_[i]
        cost = abs(nqx - qx) * cx[i] * bx + abs(nql - ql) * cl_[i] * bl + transfer * TRANSFER_BP / 1e4
        E -= cost
        acc["cost"] += cost
        qx, ql = (L * E) / cx[i], (L * E) / cl_[i]
        mx = ml = E / 2
        active = True
        return E

    for i in range(len(grid)):
        if i > 0 and active:
            liq_x = mx - qx * (hx[i] - cx[i - 1]) <= MAINT_X[name] * qx * hx[i]
            liq_l = ml + ql * (ll[i] - cl_[i - 1]) <= MAINT_L[name] * ql * ll[i]
            fx, fl = rx[i] * qx * cx[i], rl[i] * ql * cl_[i]
            px, pl = -qx * (cx[i] - cx[i - 1]), ql * (cl_[i] - cl_[i - 1])
            if liq_x or liq_l:
                acc["liq"] += 1
                acc["pnl_x"] += -mx if liq_x else px
                acc["pnl_l"] += -ml if liq_l else pl
                if not liq_x:
                    acc["fund_x"] += fx
                if not liq_l:
                    acc["fund_l"] -= fl
                keep = (0.0 if liq_x else mx + px + fx) + (0.0 if liq_l else ml + pl - fl)
                close = (0.0 if liq_x else qx * cx[i] * bx) + (0.0 if liq_l else ql * cl_[i] * bl)
                acc["cost"] += close
                E = keep - close
                stranded = E / 2
                active, qx, ql, mx, ml = False, 0.0, 0.0, 0.0, 0.0
            else:
                mx += px + fx
                ml += pl - fl
                acc["pnl_x"] += px
                acc["pnl_l"] += pl
                acc["fund_x"] += fx
                acc["fund_l"] -= fl
                E = mx + ml
        if (grid[i] - MARK_H * H) % DAY == 0:
            if E <= 0:
                E, active = 0.0, False
            elif not active:
                E = enter(E, stranded)                        # after a liquidation the equity sits on one venue
                stranded = 0.0 if active else stranded
            else:
                rxm, rlm = mx / (qx * cx[i]), ml / (ql * cl_[i])
                drift = abs(qx * cx[i] - ql * cl_[i]) / (L * E)
                if min(rxm, rlm) < M / 2 or max(rxm, rlm) > 1.5 * M or drift > DRIFT:
                    acc["resplit"] += 1
                    E = enter(E, abs(mx - E / 2))
            day = datetime.fromtimestamp(grid[i] / 1000, timezone.utc).strftime("%Y-%m-%d")
            base = e_prev if e_prev > 0 else 1.0
            rows.append({"date": day, "equity": E, **{k: (acc[k] / base if k not in ("liq", "resplit") else acc[k])
                                                      for k in acc}})
            acc = dict(fund_x=0.0, fund_l=0.0, pnl_x=0.0, pnl_l=0.0, cost=0.0, liq=0, resplit=0)
            e_prev = E
    daily = pd.DataFrame(rows)
    daily.attrs["missing_share"] = float((mx_miss | ml_miss)[1:].mean()) if len(grid) > 1 else 1.0
    daily.attrs["funding_diff_ann_pct_notional"] = float((rx - rl)[1:].sum() / max(len(grid) - 1, 1) * 24 * 365 * 100)
    daily.attrs["share_hours_xyz_pays_more"] = float(((rx - rl)[1:] > 0).mean()) if len(grid) > 1 else math.nan
    return daily


def add_bill(daily, irx):
    rate = irx.set_index("date")["close"].sort_index()
    bills = []
    for d in daily["date"]:
        b = rate[rate.index <= d]
        bills.append((float(b.iloc[-1]) / 100 if len(b) else 0.0) / 365)
    daily = daily.copy()
    daily["bill"] = bills
    if len(daily):
        daily.loc[daily.index[0], "bill"] = 0.0                # the first mark is the entry
    return daily


def weekly(daily):
    d = daily.assign(wk=pd.to_datetime(daily["date"]).dt.strftime("%G-W%V"))
    g = d.groupby("wk", sort=True)
    end = g["equity"].last()
    start = end.shift(1).fillna(1.0)
    ret = (end / start.where(start > 0) - 1).fillna(0.0)    # a wiped-out book stays at 0
    out = pd.DataFrame({"last": g["date"].last(), "ret": ret, "bill": g["bill"].sum(),
                        "fund_x": g["fund_x"].sum(), "fund_l": g["fund_l"].sum(), "pnl_x": g["pnl_x"].sum(),
                        "pnl_l": g["pnl_l"].sum(), "cost": g["cost"].sum(), "liq": g["liq"].sum(),
                        "resplit": g["resplit"].sum()})
    out["excess"] = out["ret"] - out["bill"]
    return out.reset_index()


def stats(wk, daily):
    if len(wk) < 2:
        return {"weeks": int(len(wk))}
    n, mu, t = newey_west_t(wk["excess"].to_numpy(float), NW_LAG)
    ann = lambda c: float(wk[c].sum() / len(wk) * 52 * 100)  # noqa: E731
    return {"weeks": int(n), "first_week_end": wk["last"].iloc[0], "last_week_end": wk["last"].iloc[-1],
            "ann_excess_pct": float(mu * 52 * 100), "nw_t": float(t),
            "ann_excess_2x_pct": float((mu - wk["cost"].mean()) * 52 * 100),
            "ann_excess_3x_pct": float((mu - 2 * wk["cost"].mean()) * 52 * 100),
            "weekly_sd_pct": float(wk["excess"].std(ddof=1) * 100),
            "funding_xyz_short_ann_pct": ann("fund_x"), "funding_lighter_long_ann_pct": ann("fund_l"),
            "price_xyz_short_ann_pct": ann("pnl_x"), "price_lighter_long_ann_pct": ann("pnl_l"),
            "cost_ann_pct": ann("cost"), "bill_ann_pct": ann("bill"),
            "liquidations": int(wk["liq"].sum()), "resplits": int(wk["resplit"].sum()),
            "final_equity": float(daily["equity"].iloc[-1]),
            "missing_share": daily.attrs.get("missing_share", math.nan),
            "funding_diff_ann_pct_notional": daily.attrs.get("funding_diff_ann_pct_notional", math.nan),
            "share_hours_xyz_pays_more": daily.attrs.get("share_hours_xyz_pays_more", math.nan)}


def verdict(read, st, futility_state=None):
    need = READS[read]["min_weeks"]
    if st.get("weeks", 0) < need:
        return "INCONCLUSIVE", f"{st.get('weeks', 0)} weeks < {need}"
    if st["missing_share"] > MAX_MISSING:
        return "INCONCLUSIVE", f"{st['missing_share']:.0%} of hours missing > {MAX_MISSING:.0%}"
    text = (f"{st['weeks']} weeks: excess {st['ann_excess_pct']:+.2f} pts/yr over the bill (NW t {st['nw_t']:.2f}), "
            f"2x {st['ann_excess_2x_pct']:+.2f}, 3x {st['ann_excess_3x_pct']:+.2f}; funding xyz short "
            f"{st['funding_xyz_short_ann_pct']:+.2f}, Lighter long {st['funding_lighter_long_ann_pct']:+.2f}; price "
            f"{st['price_xyz_short_ann_pct'] + st['price_lighter_long_ann_pct']:+.2f}; cost {st['cost_ann_pct']:.2f}; "
            f"{st['liquidations']} liquidations")
    if read == "futility":
        return ("NULL" if st["ann_excess_pct"] < 0 else "CONTINUE"), text
    if futility_state == "NULL":
        return "NULL", text + " (stopped at the futility read)"
    if st["ann_excess_pct"] >= HURDLE and st["nw_t"] >= T_PASS and st["ann_excess_2x_pct"] > 0:
        return "PASS", text
    return ("PARTIAL" if st["ann_excess_pct"] > 0 else "NULL"), text


# ---------------------------------------------------------------------------------------------------- reads
def due(read, now):
    return now >= datetime.strptime(READS[read]["after"], "%Y-%m-%d").replace(tzinfo=timezone.utc)


def run(read, lane=LANE, arch=None, data=DATA, check=True, now=None, fetcher=fetch):
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
    start_ms, end_ms = ms(START, MARK_H), ms(cfg["last"], MARK_H)
    src = data / read
    inputs = fetcher(read, arch, src, start_ms, end_ms)
    fut = None
    if read == "final" and (lane / "results" / "futility" / "summary.json").exists():
        fut = json.loads((lane / "results" / "futility" / "summary.json").read_text()).get("verdict")
    irx = pd.read_csv(src / "IRX.csv")
    res.mkdir(parents=True, exist_ok=True)
    out = {"registry": REGISTRY, "read": read, "decides": DECIDES, "window": [START, cfg["last"]], "inputs": inputs,
           "pairs": {}}
    for name in PAIRS:
        xb, xf, lb, lf = load(src, name)
        daily = add_bill(simulate(name, xb, xf, lb, lf, start_ms, end_ms), irx)
        wk = weekly(daily)
        st = stats(wk, daily)
        v, text = verdict(read, st, fut if name == DECIDES else None)
        out["pairs"][name] = {"stats": st, "state": v, "text": text}
        daily.to_csv(res / f"daily_{name}.csv", index=False, float_format="%.8f")
        wk.to_csv(res / f"weekly_{name}.csv", index=False, float_format="%.8f")
        log(f"{name}: {v}: {text}")
    out["verdict"] = out["pairs"][DECIDES]["state"]
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    log(f"{read} verdict ({DECIDES}): {out['verdict']}")
    return out


def auto(lane=LANE, arch=None, data=DATA, now=None):
    now = now or datetime.now(timezone.utc)
    run("futility", lane, arch, data, now=now)
    run("final", lane, arch, data, now=now)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--read", choices=sorted(READS))
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--data", default=None, help="checkout of claude/futroll-data (R480's recordings, read only)")
    a = ap.parse_args()
    if a.auto:
        auto(arch=a.data)
    else:
        run(a.read, arch=a.data)


if __name__ == "__main__":
    main()
