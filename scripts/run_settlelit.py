"""R363 settlelit_v1: short Lighter across a deep Binance settlement and cover a minute later, frozen in
experiments/settlelit_v1/PREREG.md.

R356 found that the capture crowd gives the whole pre-settlement gain back in the first minute after Binance pays a
deep funding lump at T: on its 87 hops the coin fell about 1% on Binance and on Lighter between the last trade
before T and the close of T + 1 min. Lighter charges no fee, settles funding every hour (a small part of an 8 h
lump), and needs no speed for a trade placed before T. This runner takes the position against the side that received
Binance's lump (d: short when longs received) on Lighter's own prices, from the last trade before T (or before
T - 5 min) to the last trade before T + 1, 2 or 5 min. The position pays or receives Lighter's settlement at T.

Decided on the 134 hops of R354's θ 0.3% Binance book that R356 did not read (θ 0.3-0.5%); its 87 are reported.

usage: python scripts/run_settlelit.py              the frozen run (verifies the PREREG, its inputs, every minute file
                                                    against docs/provenance/settlelit_1m.json and every Lighter
                                                    funding file against R354's data_files.csv)
       python scripts/run_settlelit.py --plumbing   counts only: hops, entries and exits found, stale bars, Lighter
                                                    settlements at T; no price change is computed
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_settlehop as base  # noqa: E402  R353's frozen runner: frozen_inputs, read_symbols, log, DAY
import run_settlehop_exit as ex  # noqa: E402  R356's frozen runner: check_data, last_traded
import settlehop_rule as rule  # noqa: E402  R355's frozen rule: CR1 t, trimmed and leave-two-coins-out means

LANE = ROOT / "experiments" / "settlelit_v1"
REGISTRY = "R363"
SRC = ROOT / "experiments" / "settlehop_pred_v1"                 # R354: frozen outputs and data manifest
BOOK = "binance+lighter th0.3%"                                  # R354's θ 0.3% Binance book: the events
SEEN = "binance+lighter th0.5%"                                  # R356's 87 hops, whose minute path was read
SYMBOLS = base.LANE / "symbols.csv"                               # R353's table: Binance key -> Lighter symbol
DATA = ROOT / "data" / "settlelit_1m"
PROV = ROOT / "docs" / "provenance" / "settlelit_1m.json"
FUNDING = ROOT / "data" / "lighter_hist" / "open" / "funding"
MIN = 60_000
ENTRIES = (0, 5)                         # minutes before T: entry at the last trade before T - j
EXITS = (1, 2, 5)                        # minutes after T: exit at the last trade before T + x
PRIMARY = (0, 1)
TRIALS = len(ENTRIES) * len(EXITS)
MULTS = (1, 2, 3)
T_MIN = 2.0                              # the primary's CR1 t at 1x
BONF_T = round(float(norm.ppf(1 - 0.05 / TRIALS)), 2)   # one-sided 5% over the six trials: 2.39
log = base.log


# ------------------------------------------------------------------------------------------------------------ inputs
def manifest(src=SRC):
    """R354's frozen data manifest: {path: sha256}."""
    with open(src / "data_files.csv", newline="") as f:
        return {r["path"]: r["sha256"] for r in csv.DictReader(f)}


def load_hops(src=SRC, symbols=SYMBOLS):
    """R354's θ 0.3% Binance hops in T order, with the Lighter symbol, the side cost, and seen = True for R356's 87."""
    h = pd.read_csv(src / "results" / "hops.csv.gz")
    seen = {(c, int(t)) for c, t in zip(h.coin[h.book == SEEN], h["T"][h.book == SEEN])}
    h = h[h.book == BOOK].sort_values(["T", "coin"], ignore_index=True)
    h["T"] = h["T"].astype("int64")
    h["seen"] = [(c, int(t)) in seen for c, t in zip(h.coin, h["T"])]
    lt = {r["key"]: r["lighter"] for r in base.read_symbols(symbols)}
    h["lighter"] = h.coin.map(lt)
    return h[["coin", "lighter", "T", "d", "e", "cost_h_bp", "seen"]]


def bars(sym, T, folder=DATA):
    """One hop's Lighter 1-minute bars: open time, close, traded (close > 0 and volume > 0)."""
    k = pd.read_parquet(folder / "lighter" / sym / f"{T}.parquet", columns=["t", "close", "volume"])
    k = k.drop_duplicates("t").sort_values("t", ignore_index=True)
    c, v = k.close.to_numpy(float), k.volume.to_numpy(float)
    return {"t": k.t.to_numpy(np.int64), "close": c, "traded": np.isfinite(c) & (c > 0) & np.isfinite(v) & (v > 0)}


def settlement(sym, T, man, folder=FUNDING, root=ROOT):
    """Lighter's funding rate settled at T (positive when longs pay), from a file R354's manifest lists."""
    p = folder / f"{sym}.parquet"
    rel = p.relative_to(root).as_posix()
    if man.get(rel) is None or prereg.sha256_file(p) != man[rel]:
        raise prereg.PreregError(f"{rel}: not in R354's data manifest or changed since")
    f = pd.read_parquet(p, columns=["t", "rate"])
    r = f.rate[f.t == T]
    if len(r) != 1 or not np.isfinite(r.iloc[0]):
        raise prereg.PreregError(f"{sym}: no single Lighter settlement at {T}")
    return float(r.iloc[0])


# ------------------------------------------------------------------------------------------------------------- rules
def trade(b, T, d, j, x):
    """Position d from the last trade before T - j min to the last trade before T + x min: (price return signed by
    d, entry stale, exit stale), or None when no traded bar opens in [T - 10 min, T - j - 1 min]."""
    t_in = T - (j + 1) * MIN                 # the bar opening here closes at T - j
    i = ex.last_traded(b, t_in, b["t"][0] if len(b["t"]) else t_in)
    if i < 0:
        return None
    t_out = T + (x - 1) * MIN
    k = ex.last_traded(b, t_out, b["t"][i])
    return d * (b["close"][k] / b["close"][i] - 1), bool(b["t"][i] != t_in), bool(b["t"][k] != t_out)


def net(price, fund, cost_bp, m):
    """A hop's net: its price return, the funding its position took at T, and m times its round-trip book cost."""
    return price + fund - 2 * m * cost_bp / 1e4


def calendar_days(T):
    day = np.asarray(T, np.int64) // base.DAY
    return int(day.max() - day.min() + 1)


def halves(T):
    """True for hops in the first half of their calendar (two equal runs of days)."""
    day = np.asarray(T, np.int64) // base.DAY
    return day < day.min() + calendar_days(T) / 2


def describe(x, name):
    """One trial's statistics over a set of hops (x: price, fund, cost_h_bp, coin, T, stale flags)."""
    out = {"trial": name, "hops": len(x), "coins": int(x.coin.nunique()), "times": int(x["T"].nunique()),
           "price_bp": x.price.mean() * 1e4, "fund_bp": x.fund.mean() * 1e4,
           "gross_bp": (x.price + x.fund).mean() * 1e4, "cost_rt_bp": 2 * x.cost_h_bp.mean(),
           "stale_entry": int(x.stale_in.sum()), "stale_exit": int(x.stale_out.sum())}
    for m in MULTS:
        n = net(x.price.to_numpy(), x.fund.to_numpy(), x.cost_h_bp.to_numpy(), m)
        mu, t = rule.decide_stats(n, x["T"].to_numpy())
        out.update({f"net{m}_bp": mu * 1e4, f"t{m}": t, f"hit{m}": float((n > 0).mean())})
    n1 = net(x.price.to_numpy(), x.fund.to_numpy(), x.cost_h_bp.to_numpy(), 1)
    first = halves(x["T"].to_numpy())
    best = x.assign(n1=n1).groupby("coin").n1.sum().idxmax()
    out.update({"half1_net1_bp": n1[first].mean() * 1e4, "half2_net1_bp": n1[~first].mean() * 1e4,
                "best_coin": best, "wo_best_net1_bp": n1[x.coin.to_numpy() != best].mean() * 1e4,
                "trim10_net1_bp": rule.trimmed(n1) * 1e4,
                "l2co_net1_bp": rule.leave_two_coins_out(n1, x.coin.tolist()) * 1e4,
                "median_net1_bp": float(np.median(n1)) * 1e4,
                "sd1_bp": float(n1.std(ddof=1)) * 1e4 if len(n1) > 1 else np.nan,
                "day1_bp": n1.sum() * 1e4 / calendar_days(x["T"].to_numpy())})
    return out


def decide(d):
    """The primary trial on the unseen hops: PASS when all five checks hold."""
    checks = {"t1": bool(np.isfinite(d["t1"]) and d["t1"] >= T_MIN),
              "net2_positive": bool(d["net2_bp"] > 0),
              "both_halves": bool(d["half1_net1_bp"] > 0 and d["half2_net1_bp"] > 0),
              "without_best_coin": bool(d["wo_best_net1_bp"] > 0),
              "trimmed_positive": bool(np.isfinite(d["trim10_net1_bp"]) and d["trim10_net1_bp"] > 0)}
    return {"checks": checks, "verdict": "PASS" if all(checks.values()) else "NULL"}


def name(j, x):
    return f"in{j}_out{x}"


# -------------------------------------------------------------------------------------------------------------- main
def run_all(h, man, folder=DATA):
    """Every hop's trials: a frame of trial, hop columns, price, fund, stale flags."""
    rows = []
    for r in h.itertuples(index=False):
        T, d = int(r.T), int(r.d)
        b = bars(r.lighter, T, folder)
        fund = -d * settlement(r.lighter, T, man)          # the position d pays d times the rate
        for j in ENTRIES:
            for x in EXITS:
                z = trade(b, T, d, j, x)
                if z is None:
                    continue
                rows.append({"trial": name(j, x), "coin": r.coin, "lighter": r.lighter, "T": T, "d": d, "e": r.e,
                             "seen": r.seen, "cost_h_bp": r.cost_h_bp, "price": z[0], "fund": fund,
                             "stale_in": z[1], "stale_out": z[2]})
    return pd.DataFrame(rows)


def plumbing(h, folder=DATA):
    """Counts only: hops, windows, entries and exits found, stale bars, and Lighter settlements found at T."""
    log(f"{len(h)} hops on {h.coin.nunique()} coins at {h['T'].nunique()} settlement times; "
        f"{int(h.seen.sum())} in R356's book, {int((~h.seen).sum())} outside it at "
        f"{h['T'][~h.seen].nunique()} times; Lighter symbol missing {int(h.lighter.isna().sum())}")
    man = manifest()
    cnt = {name(j, x): [0, 0, 0] for j in ENTRIES for x in EXITS}
    miss, fund_ok = 0, 0
    for r in h.itertuples(index=False):
        T = int(r.T)
        if not (folder / "lighter" / r.lighter / f"{T}.parquet").exists():
            miss += 1
            continue
        b = bars(r.lighter, T, folder)
        try:
            settlement(r.lighter, T, man)
            fund_ok += 1
        except prereg.PreregError:
            pass
        for j in ENTRIES:
            for x in EXITS:
                t_in, t_out = T - (j + 1) * MIN, T + (x - 1) * MIN
                i = ex.last_traded(b, t_in, b["t"][0] if len(b["t"]) else t_in)
                if i < 0:
                    continue
                k = ex.last_traded(b, t_out, b["t"][i])
                c = cnt[name(j, x)]
                c[0] += 1
                c[1] += int(b["t"][i] != t_in)
                c[2] += int(b["t"][k] != t_out)
    log(f"missing windows {miss}; Lighter settlement at T found {fund_ok}; per trial [traded, stale entry, "
        f"stale exit]: {cnt}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    h = load_hops()
    if a.plumbing:
        plumbing(h)
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = base.frozen_inputs(LANE / "PREREG.md")
    n_files = ex.check_data(PROV, DATA, ROOT)
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match; {n_files} minute files match their provenance")
    if len(h) != 221 or int(h.seen.sum()) != 87 or h.lighter.isna().any():
        raise prereg.PreregError("R354's θ 0.3% Binance book is not the 221 hops holding R356's 87, each on Lighter")
    man = manifest()
    tr = run_all(h, man)
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    rows = []
    for j in ENTRIES:
        for x in EXITS:
            t = tr[tr.trial == name(j, x)]
            for subset, mask in (("unseen", ~t.seen), ("seen", t.seen), ("all", t.seen | ~t.seen)):
                d = describe(t[mask.to_numpy()], name(j, x))
                d["subset"] = subset
                rows.append(d)
            u = rows[-3]
            log(f"{name(j, x)} unseen: {u['hops']} hops, price {u['price_bp']:+.1f} fund {u['fund_bp']:+.1f} "
                f"net1 {u['net1_bp']:+.1f} (t {u['t1']:.2f}) net2 {u['net2_bp']:+.1f} net3 {u['net3_bp']:+.1f}")
    bk = pd.DataFrame(rows)
    unseen = bk[bk.subset == "unseen"]
    prim = unseen[unseen.trial == name(*PRIMARY)].iloc[0].to_dict()
    dec = decide(prim)
    fam = {"bonferroni_t": BONF_T, "t1_at_or_above": int((unseen.t1 >= BONF_T).sum()),
           "t1_at_or_above_2": int((unseen.t1 >= T_MIN).sum()), "trials": TRIALS}
    bk.to_csv(res / "trials.csv", index=False, float_format="%.6g")
    tr.to_csv(res / "hops.csv.gz", index=False, float_format="%.8g")
    if ex.check_data(PROV, DATA, ROOT) != n_files:
        raise prereg.PreregError("the minute files changed during the run")
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "primary": name(*PRIMARY),
               "decision": dec, "verdict": dec["verdict"], "family": fam, "inputs": shas, "minute_files": n_files}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {dec['verdict']} {dec['checks']}; family {fam}")


if __name__ == "__main__":
    main()
