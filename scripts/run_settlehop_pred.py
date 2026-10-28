"""R354 settlehop_pred_v1: R353's settlement-window hop on a point-in-time predicted rate, frozen in
experiments/settlehop_pred_v1/PREREG.md.

R353 found that hedged across venues the S perp is not repriced by its funding lump, but that S's last settled rate
forecasts only about a third of the next lump. A trader an hour before the settlement sees the rate S will settle at;
no venue's history file holds it. Binance sets it from its premium index (its funding page):

    F = [P + clamp(0.01% - P, -0.05%, +0.05%)] / (8 / N),   N = the funding interval in hours,

where P is the average of the interval's premium index samples, weighted 1, 2, ..., n so later samples count more.
This runner rebuilds P an hour before T from Binance's hourly premium index bars that have closed by then: hour h of
an m-hour interval weighs 2h - 1 (the linear weights summed over the hour), each closed hour counts at the mean of its
open, high, low and close, and the hour still to come counts at the last close. Everything else (bars, funding, the
hop, the identity check, costs, the book and the decision) is R353's frozen code, imported unchanged.

usage: python scripts/run_settlehop_pred.py              the frozen run (verifies the PREREG and every input hash)
       python scripts/run_settlehop_pred.py --manifest   write experiments/settlehop_pred_v1/data_files.csv
       python scripts/run_settlehop_pred.py --plumbing   counts of settlements, signals and tradable entries; no returns
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_settlehop as base  # noqa: E402  R353's frozen runner, unchanged (its sha256 is a frozen input)

LANE = ROOT / "experiments" / "settlehop_pred_v1"
REGISTRY = "R354"
SYMBOLS = base.LANE / "symbols.csv"          # R353's frozen symbol table
PREM = "premiumIndexKlines_1h"               # Binance's hourly premium index bars, keyed by the Binance perp
H, DAY = base.H, base.DAY
PAIRS = (("binance", "lighter"), ("mexc", "lighter"), ("gate", "lighter"))
THETAS = (0.003, 0.005)
PRIMARY = ("binance", "lighter", 0.005)
TRIALS = len(PAIRS) * len(THETAS)
BONF_T = round(float(norm.ppf(1 - 0.05 / TRIALS)), 2)   # one-sided 5% over the family: 2.39
INTERVALS = (4, 8)                           # S's funding interval in hours: the gap from its previous settlement
INTEREST = 0.0001                            # Binance's 8-hour interest rate
CLAMP = 0.0005
log = base.log


# -------------------------------------------------------------------------------------------------------------- data
def data_paths(rows):
    """Every file a run reads: both venues' bars and funding for each pair, and Binance's premium index bars."""
    out = set()
    for S, Hv in PAIRS:
        for r in rows:
            ks, kh = base.key_of(r, S), base.key_of(r, Hv)
            if not ks or not kh:
                continue
            for v, k in ((S, ks), (Hv, kh)):
                for folder in (base.VENUES[v][0], base.VENUES[v][2]):
                    p = base.DATA / folder / f"{k}.parquet"
                    if p.exists():
                        out.add(p.relative_to(ROOT).as_posix())
            p = base.DATA / PREM / f"{r['key']}.parquet"
            if p.exists():
                out.add(p.relative_to(ROOT).as_posix())
    return sorted(out)


def load_premium(key, t0=base.T0, t1=base.T1):
    """Binance's hourly premium index bars opening in [t0, t1): open time, the mean of open, high, low and close, and
    the close. Rows outside [t0, t1) are filtered by the reader and never loaded (2020 is reserved)."""
    p = base.DATA / PREM / f"{key}.parquet"
    if not key or not p.exists():
        return None
    k = pq.read_table(base.checked(p), columns=["t", "open", "high", "low", "close"],
                      filters=[("t", ">=", t0), ("t", "<", t1)]).to_pandas()
    k = k.drop_duplicates("t").sort_values("t", ignore_index=True)
    k = k[k.t % H == 0]
    ohlc = k[["open", "high", "low", "close"]].to_numpy(float)
    ok = np.isfinite(ohlc).all(axis=1)
    k, ohlc = k[ok], ohlc[ok]
    if not len(k):
        return None
    return {"t": k.t.to_numpy(np.int64), "mean": ohlc.mean(axis=1), "close": ohlc[:, 3]}


# ------------------------------------------------------------------------------------------------------------- rules
def predicted_rate(prem, T, m):
    """S's rate for the settlement at T over an m-hour interval, as known at T - 1 h, or NaN.
    Hours h = 1..m open at T - (m - h + 1) h and weigh 2h - 1. Hours 1..m-1 have closed by T - 1 h and count at their
    OHLC mean; hour m (opening at T - 1 h) counts at the close of hour m - 1, which must exist. A missing earlier hour
    is left out and the weights renormalized."""
    t = prem["t"]
    i_last = np.searchsorted(t, T - 2 * H)
    if i_last >= len(t) or t[i_last] != T - 2 * H:
        return np.nan
    num, den = 0.0, 0.0
    for h in range(1, m):
        i = np.searchsorted(t, T - (m - h + 1) * H)
        if i < len(t) and t[i] == T - (m - h + 1) * H:
            num += (2 * h - 1) * prem["mean"][i]
            den += 2 * h - 1
    num += (2 * m - 1) * prem["close"][i_last]
    den += 2 * m - 1
    P = num / den
    return (P + float(np.clip(INTEREST - P, -CLAMP, CLAMP))) * m / 8


def pred_signals(fs, fh, prem):
    """Every S settlement T whose interval (the gap from the previous one) is 4 or 8 hours, with H settling in the two
    hours before the entry: (T, F_hat, h_prev, e_signed = F_hat - 2 h_prev, m), all known at T - 1 h."""
    ts, _, _ = fs
    th, rh, _ = fh
    gap = np.diff(ts)
    T = ts[1:]
    m = np.rint(gap / H).astype(int)
    ok = np.isin(m, INTERVALS) & (np.abs(gap - m * H) <= 60_000)
    j = np.searchsorted(th, T - H, side="right") - 1
    jj = np.clip(j, 0, None)
    ok &= (j >= 0) & ((T - H) - th[jj] <= 2 * H)
    T, m, hprev = T[ok], m[ok], rh[jj][ok]
    fhat = np.array([predicted_rate(prem, int(t), int(k)) for t, k in zip(T, m)], float)
    keep = np.isfinite(fhat)
    return T[keep], fhat[keep], hprev[keep], fhat[keep] - 2 * hprev[keep], m[keep]


def pair_hops(S, Hv, rows, log_every=0):
    """R353's pair_hops with the predicted signal: every hop with e at or above the smallest theta, and the pair's
    calendar (the days from the first to the last eligible settlement with a prediction and H settling, at any e)."""
    out, first, last = [], None, None
    for n, r in enumerate(rows):
        ks, kh = base.key_of(r, S), base.key_of(r, Hv)
        if not ks or not kh:
            continue
        fs, fh = base.load_funding(S, ks), base.load_funding(Hv, kh)
        prem = load_premium(r["key"])
        if fs is None or fh is None or prem is None:
            continue
        T, fhat, hp, es, m = pred_signals(fs, fh, prem)
        keep = base.eligible(T)
        T, fhat, hp, es, m = T[keep], fhat[keep], hp[keep], es[keep], m[keep]
        if not len(T):
            continue
        first = int(T.min()) if first is None else min(first, int(T.min()))
        last = int(T.max()) if last is None else max(last, int(T.max()))
        big = np.abs(es) >= min(THETAS)
        if not big.any():
            continue
        sb, hb = base.load_bars(S, ks), base.load_bars(Hv, kh)
        if sb is None or hb is None:
            continue
        ds, dh = base.daily_closes(sb), base.daily_closes(hb)
        for t, fhat_, hp_, es_, m_ in zip(T[big], fhat[big], hp[big], es[big], m[big]):
            t = int(t)
            d = 1 if es_ > 0 else -1
            h = base.hop(sb, hb, fs, fh, t, d)
            if h is None:
                continue
            c_h = base.lighter_cost_bp(h["qv24"]) if Hv == "lighter" else base.COST_BP[Hv]
            out.append({"S": S, "H": Hv, "coin": r["key"], "T": t, "d": d, "interval_h": int(m_), "f_hat": fhat_,
                        "h_prev": hp_, "e": abs(es_), "same": base.same_coin(ds, dh, t - H),
                        "cost_s_bp": base.COST_BP[S], "cost_h_bp": c_h, **h})
        if log_every and n % log_every == 0:
            log(f"{S}+{Hv}: {n}/{len(rows)} coins, {len(out)} hops")
    days = (np.arange(first // DAY * DAY, last // DAY * DAY + DAY, DAY, dtype=np.int64) if first is not None
            else np.array([], np.int64))
    return pd.DataFrame(out), days


# -------------------------------------------------------------------------------------------------------------- main
def plumbing(rows):
    """Counts only: eligible settlements with a prediction, signals at each theta, tradable entries. No return, and no
    settled rate after the entry is read."""
    for S, Hv in PAIRS:
        n = {"coins": 0, "signals": 0, **{f"ge{th}": 0 for th in THETAS}, "entry_traded": 0}
        first, last = None, None
        for r in rows:
            ks, kh = base.key_of(r, S), base.key_of(r, Hv)
            if not ks or not kh:
                continue
            fs, fh = base.load_funding(S, ks), base.load_funding(Hv, kh)
            prem = load_premium(r["key"])
            if fs is None or fh is None or prem is None:
                continue
            T, _, _, es, _ = pred_signals(fs, fh, prem)
            keep = base.eligible(T)
            T, es = T[keep], es[keep]
            if not len(T):
                continue
            first = int(T.min()) if first is None else min(first, int(T.min()))
            last = int(T.max()) if last is None else max(last, int(T.max()))
            n["coins"] += 1
            n["signals"] += len(T)
            for th in THETAS:
                n[f"ge{th}"] += int((np.abs(es) >= th).sum())
            sb, hb = base.load_bars(S, ks), base.load_bars(Hv, kh)
            if sb is None or hb is None:
                continue
            for t in T[np.abs(es) >= min(THETAS)]:
                i_s, i_h = base.at(sb, int(t) - 2 * H), base.at(hb, int(t) - 2 * H)
                n["entry_traded"] += int(i_s >= 0 and i_h >= 0 and sb["traded"][i_s] and hb["traded"][i_h])
        span = (pd.Timestamp(first, unit="ms").date(), pd.Timestamp(last, unit="ms").date()) if first else None
        log(f"{S}+{Hv}: {n} span {span}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--manifest", action="store_true")
    a = ap.parse_args()
    rows = base.read_symbols(SYMBOLS)
    if a.manifest:
        paths = data_paths(rows)
        with open(LANE / "data_files.csv", "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["path", "sha256"])
            for rel in paths:
                w.writerow([rel, prereg.sha256_file(ROOT / rel)])
        log(f"{len(paths)} data files hashed")
        return
    if a.plumbing:
        plumbing(rows)
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = base.frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    n_snap = base.check_bands([p for p in shas if p.startswith("data/recorders/lighter_book/")])
    with open(LANE / "data_files.csv", newline="") as f:
        base.MANIFEST.update({r["path"]: r["sha256"] for r in csv.DictReader(f)})
    if sorted(base.MANIFEST) != data_paths(rows):
        raise prereg.PreregError("the data manifest does not list exactly the files this run reads")
    log(f"Lighter bands match {n_snap} snapshots; {len(base.MANIFEST)} data files in the manifest")
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    books, hops, daily, dec = [], [], [], None
    for S, Hv in PAIRS:
        cand, days = pair_hops(S, Hv, rows, log_every=50)
        log(f"{S}+{Hv}: {len(cand)} candidates, {int(cand.same.sum()) if len(cand) else 0} same-coin, {len(days)} days")
        for th in THETAS:
            h = base.select(cand, th) if len(cand) else cand
            label = f"{S}+{Hv} th{th * 100:g}%"
            dsc = base.describe(h, days, S, label)
            dsc.update({"S": S, "H": Hv, "theta": th})
            if len(h):
                dsc["f_hat_bp"] = float((h.d * h.f_hat).mean() * 1e4)     # the forecast S lump, signed for the hop
                dsc["fund_s_bp"] = float(h.fund_s.mean() * 1e4)           # the lump S paid
            books.append(dsc)
            if len(h):
                hops.append(h.assign(book=label, net1=base.net(h, 1)))
            daily.append(pd.DataFrame({"book": label, "day": pd.to_datetime(days, unit="ms").date,
                                       **{f"net{m}_bp": base.book(h, days, m) for m in base.MULTS}}))
            if (S, Hv, th) == PRIMARY:
                dec = base.decide(dsc)
            log(f"{label}: {dsc.get('hops', 0)} hops, net1 {dsc.get('net1_bp', float('nan')):.1f} bp a hop, "
                f"{dsc.get('day1_bp', float('nan')):.2f} bp/day t {dsc.get('t1', float('nan')):.2f}")
    bk = pd.DataFrame(books)
    bk.to_csv(res / "books.csv", index=False, float_format="%.6g")
    pd.concat(hops, ignore_index=True).to_csv(res / "hops.csv.gz", index=False, float_format="%.8g")
    pd.concat(daily, ignore_index=True).to_csv(res / "daily.csv.gz", index=False, float_format="%.6g")
    fam = {"bonferroni_t": BONF_T, "books_at_or_above": int((bk.t1 >= BONF_T).sum()),
           "books_t2": int((bk.t1 >= base.T_BAR).sum()), "books": len(bk)}
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "primary": list(PRIMARY),
               "decision": dec, "verdict": dec["verdict"], "family": fam, "costs_bp": base.COST_BP,
               "lighter_bands": [[u if np.isfinite(u) else None, bp] for u, bp in base.LIGHTER_BANDS],
               "inputs": shas}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {dec['verdict']} {dec['checks']}; family {fam}")


if __name__ == "__main__":
    main()
