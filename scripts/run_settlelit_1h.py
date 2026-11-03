"""R387 settlelit_1h_v1: R363's Lighter settlement scalp on Binance settlements whose interval is 1 hour, frozen in
experiments/settlelit_1h_v1/PREREG.md.

R363 found that a Lighter position against the side that received a deep Binance funding lump, entered before T and
covered a minute after, took the capture crowd's exit (+23.4 bp a hop at 1x on 134 unseen hops). Its events were
R354's hops, which keep only 4 h and 8 h settlement intervals. Since 2025-05-02 Binance moves a perp to hourly
settlement after a print at its cap or floor, so deep hourly settlements form a population no settlement lane read.

The rule is R363's, unchanged except for the event set and the trigger, which an hourly interval forces:
- Event: a Binance settlement T that follows the previous Binance settlement by exactly 1 hour, on a coin Lighter
  lists (R353's symbol table), whose previous settled rate r_prev (settled at T - 1 h) is at least 0.3% in size.
- Direction d = sign(r_prev): the side that r_prev made receive at T - 1 h; short on Lighter when longs received.
- Trades, funding, cost: R363's run_settlelit.trade, its Lighter settlement at T, R353's volume-band cost.

usage: python -I scripts/run_settlelit_1h.py --fetch      fetch the Lighter minute windows, write their provenance and
                                                          the data manifest; counts only, no price change computed
       python -I scripts/run_settlelit_1h.py --plumbing   counts only from the files on disk
       python -I scripts/run_settlelit_1h.py              the frozen run (verifies the PREREG and every input)
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_settlehop as base  # noqa: E402  R353: read_symbols, lighter_cost_bp, frozen_inputs, log, DAY
import run_settlehop_exit as ex  # noqa: E402  R356: check_data, last_traded
import run_settlelit as lit  # noqa: E402  R363: trade, net, halves, calendar_days, ENTRIES, EXITS, MULTS
import settlehop_rule as rule  # noqa: E402  R355: decide_stats, trimmed, leave_two_coins_out

LANE = ROOT / "experiments" / "settlelit_1h_v1"
REGISTRY = "R387"
H, MIN = 3_600_000, 60_000
T0 = 1735689600000          # 2025-01-01 00:00 UTC: the first settlement considered (2020 stays reserved)
T1 = 1790812800000          # 2026-10-01 00:00 UTC: the Binance archive's end; T + 1 h must be before it
THETA = 0.003
BINANCE = ROOT / "data" / "fundingRate"
FUNDING = ROOT / "data" / "lighter_hist" / "open" / "funding"
CANDLES = ROOT / "data" / "lighter_hist" / "open" / "candles_1h"
SYMBOLS = base.LANE / "symbols.csv"
LIGHTER_IDS = ROOT / "data" / "lighter_hist" / "contracts.csv"
DATA = ROOT / "data" / "settlelit1h_1m"
PROV = ROOT / "docs" / "provenance" / "settlelit1h_1m.json"
MANIFEST = LANE / "data_files.csv"
ENTRIES, EXITS, MULTS = lit.ENTRIES, lit.EXITS, lit.MULTS
PRIMARY = (0, 1)
TRIALS = len(ENTRIES) * len(EXITS)
T_MIN = 2.0
log = base.log


# ------------------------------------------------------------------------------------------------------------ inputs
def lighter_map():
    lt = {r["key"]: r["lighter"] for r in base.read_symbols(SYMBOLS) if r.get("lighter")}
    ids = {r["symbol"]: int(r["market_id"]) for r in csv.DictReader(open(LIGHTER_IDS, newline=""))}
    return {k: (v, ids.get(v)) for k, v in lt.items()}


def binance(key):
    """Binance settlements stamped in [T0 - 2 h, T1), rounded to the hour: (T, rate). Rows before that are never
    loaded (the reader filters them), so no reserved 2020 row is read."""
    t = pq.read_table(BINANCE / f"{key}.parquet", columns=["t", "rate"],
                      filters=[("t", ">=", T0 - 2 * H), ("t", "<", T1)]).to_pandas()
    t["T"] = (t.t + H // 2) // H * H
    t = t.drop_duplicates("T").sort_values("T", ignore_index=True)
    return t["T"].to_numpy(np.int64), t.rate.to_numpy(float)


def lighter_times(sym):
    f = pq.read_table(FUNDING / f"{sym}.parquet", columns=["t"]).to_pandas()
    return set(f.t.astype("int64"))


def qv24(sym, T):
    """Lighter quote volume over the 24 hourly bars opening in [T - 25 h, T - 2 h] (R353's window)."""
    p = CANDLES / f"{sym}.parquet"
    if not p.exists():
        return np.nan
    k = pq.read_table(p, columns=["t", "quote_volume"],
                      filters=[("t", ">=", T - 25 * H), ("t", "<=", T - 2 * H)]).to_pandas()
    return float(np.nansum(k.quote_volume.to_numpy(float))) if len(k) else np.nan


def build_hops():
    """Every event, in T order: coin, Lighter symbol and market id, T, d, e = |r_prev|, Binance's rate at T (reported,
    never used to select), and the volume-band cost a side. Selection reads Binance rates and the existence of a
    Lighter settlement at T, never its value."""
    rows = []
    for key, (sym, mid) in sorted(lighter_map().items()):
        if not (BINANCE / f"{key}.parquet").exists() or not (FUNDING / f"{sym}.parquet").exists() or mid is None:
            continue
        T, r = binance(key)
        if len(T) < 2:
            continue
        lts = lighter_times(sym)
        for i in range(1, len(T)):
            if T[i] - T[i - 1] != H or not (T0 <= T[i] and T[i] + H < T1) or not np.isfinite(r[i - 1]):
                continue
            if abs(r[i - 1]) < THETA - 1e-15 or int(T[i]) not in lts:
                continue
            q = qv24(sym, int(T[i]))
            rows.append({"coin": key, "lighter": sym, "market_id": mid, "T": int(T[i]),
                         "d": int(np.sign(r[i - 1])), "e": abs(float(r[i - 1])), "binance_rate_T": float(r[i]),
                         "qv24": q, "cost_h_bp": base.lighter_cost_bp(q)})
    return pd.DataFrame(rows).sort_values(["T", "coin"], ignore_index=True)


def input_files(h):
    files = set()
    for key, sym in zip(h.coin, h.lighter):
        files |= {BINANCE / f"{key}.parquet", FUNDING / f"{sym}.parquet", CANDLES / f"{sym}.parquet"}
    return sorted(p for p in files if p.exists())


def write_manifest(h):
    with open(MANIFEST, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["path", "sha256"])
        for p in input_files(h):
            w.writerow([p.relative_to(ROOT).as_posix(), prereg.sha256_file(p)])


def check_manifest():
    with open(MANIFEST, newline="") as f:
        listed = {r["path"]: r["sha256"] for r in csv.DictReader(f)}
    for rel, want in listed.items():
        if prereg.sha256_file(ROOT / rel) != want:
            raise prereg.PreregError(f"{rel}: sha256 differs from {MANIFEST.name}")
    return len(listed)


def settlement(sym, T):
    f = pd.read_parquet(FUNDING / f"{sym}.parquet", columns=["t", "rate"])
    r = f.rate[f.t == T]
    if len(r) != 1 or not np.isfinite(r.iloc[0]):
        raise prereg.PreregError(f"{sym}: no single Lighter settlement at {T}")
    return float(r.iloc[0])


# ------------------------------------------------------------------------------------------------------------- fetch
def fetch(h):
    import fetch_settlelit_1m as fx
    now = int(time.time() * 1000)
    new = 0
    for r in h.itertuples(index=False):
        p = DATA / "lighter" / r.lighter / f"{int(r.T)}.parquet"
        if p.exists():
            continue
        df = fx.lighter_window(int(r.market_id), int(r.T), now)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)
        new += 1
    files = sorted(DATA.rglob("*.parquet"))
    PROV.write_text(json.dumps({
        "folder": DATA.relative_to(ROOT).as_posix(),
        "source": "https://mainnet.zklighter.elliot.ai/api/v1/candles resolution 1m (lab.carrylane)",
        "script": "python -I scripts/run_settlelit_1h.py --fetch",
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hops": f"{len(h)} Binance 1 h-interval settlements with |r_prev| >= {THETA:.1%} on Lighter-listed coins",
        "window": "Lighter 1-minute bars opening in [T - 10 min, T + 10 min), closed when fetched",
        "files": len(files), "bytes": sum(f.stat().st_size for f in files),
        "file_hashes": [{"path": f.relative_to(ROOT).as_posix(), "sha256": prereg.sha256_file(f)} for f in files],
    }, indent=1) + "\n")
    write_manifest(h)
    log(f"{new} new windows; {len(files)} minute files; manifest {len(input_files(h))} input files")


def plumbing(h):
    """Counts only: hops, coins, windows on disk, traded entries and exits per trial. No price change."""
    clusters = (h.coin + ":" + (h["T"] // base.DAY).astype(str)).nunique()
    log(f"{len(h)} hops on {h.coin.nunique()} coins at {h['T'].nunique()} times in {clusters} coin-days; "
        f"{h['T'].map(lambda t: time.strftime('%Y-%m', time.gmtime(t / 1000))).min()}.."
        f"{h['T'].map(lambda t: time.strftime('%Y-%m', time.gmtime(t / 1000))).max()}; per coin "
        f"{h.coin.value_counts().to_dict()}; band costs {h.cost_h_bp.value_counts().to_dict()}")
    cnt = {lit.name(j, x): [0, 0, 0] for j in ENTRIES for x in EXITS}
    miss = 0
    for r in h.itertuples(index=False):
        p = DATA / "lighter" / r.lighter / f"{int(r.T)}.parquet"
        if not p.exists():
            miss += 1
            continue
        b = lit.bars(r.lighter, int(r.T), DATA)
        for j in ENTRIES:
            for x in EXITS:
                t_in, t_out = int(r.T) - (j + 1) * MIN, int(r.T) + (x - 1) * MIN
                i = ex.last_traded(b, t_in, b["t"][0] if len(b["t"]) else t_in)
                if i < 0:
                    continue
                k = ex.last_traded(b, t_out, b["t"][i])
                c = cnt[lit.name(j, x)]
                c[0] += 1
                c[1] += int(b["t"][i] != t_in)
                c[2] += int(b["t"][k] != t_out)
    log(f"missing windows {miss}; per trial [traded, stale entry, stale exit]: {cnt}")


# --------------------------------------------------------------------------------------------------------------- run
def run_all(h):
    rows = []
    for r in h.itertuples(index=False):
        T, d = int(r.T), int(r.d)
        b = lit.bars(r.lighter, T, DATA)
        fund = -d * settlement(r.lighter, T)
        for j in ENTRIES:
            for x in EXITS:
                z = lit.trade(b, T, d, j, x)
                if z is None:
                    continue
                rows.append({"trial": lit.name(j, x), "coin": r.coin, "lighter": r.lighter, "T": T, "d": d,
                             "e": r.e, "binance_rate_T": r.binance_rate_T, "cost_h_bp": r.cost_h_bp,
                             "cluster": f"{r.coin}:{T // base.DAY}", "price": z[0], "fund": fund,
                             "stale_in": z[1], "stale_out": z[2]})
    return pd.DataFrame(rows)


def describe(x, name):
    """R363's statistics, with the CR1 standard error clustered by coin and UTC day (consecutive hourly hops of one
    coin are not independent), and the settlement-time clustering reported next to it."""
    out = {"trial": name, "hops": len(x), "coins": int(x.coin.nunique()), "clusters": int(x.cluster.nunique()),
           "price_bp": x.price.mean() * 1e4, "fund_bp": x.fund.mean() * 1e4,
           "gross_bp": (x.price + x.fund).mean() * 1e4, "cost_rt_bp": 2 * x.cost_h_bp.mean(),
           "stale_entry": int(x.stale_in.sum()), "stale_exit": int(x.stale_out.sum())}
    for m in MULTS:
        n = lit.net(x.price.to_numpy(), x.fund.to_numpy(), x.cost_h_bp.to_numpy(), m)
        mu, t = rule.decide_stats(n, x.cluster.to_numpy())
        out.update({f"net{m}_bp": mu * 1e4, f"t{m}": t, f"hit{m}": float((n > 0).mean())})
    n1 = lit.net(x.price.to_numpy(), x.fund.to_numpy(), x.cost_h_bp.to_numpy(), 1)
    out["t1_by_T"] = rule.decide_stats(n1, x["T"].to_numpy())[1]
    first = lit.halves(x["T"].to_numpy())
    best = x.assign(n1=n1).groupby("coin").n1.sum().idxmax()
    out.update({"half1_net1_bp": n1[first].mean() * 1e4, "half2_net1_bp": n1[~first].mean() * 1e4,
                "best_coin": best, "wo_best_net1_bp": n1[x.coin.to_numpy() != best].mean() * 1e4,
                "trim10_net1_bp": rule.trimmed(n1) * 1e4,
                "l2co_net1_bp": rule.leave_two_coins_out(n1, x.coin.tolist()) * 1e4,
                "median_net1_bp": float(np.median(n1)) * 1e4,
                "persist_same_sign": float((np.sign(x.binance_rate_T) == x.d).mean()),
                "day1_bp": n1.sum() * 1e4 / lit.calendar_days(x["T"].to_numpy())})
    return out


def decide(d):
    """PASS when all seven checks hold on the primary trial."""
    checks = {"t1": bool(np.isfinite(d["t1"]) and d["t1"] >= T_MIN),
              "net2_positive": bool(d["net2_bp"] > 0),
              "net3_positive": bool(d["net3_bp"] > 0),
              "both_halves": bool(d["half1_net1_bp"] > 0 and d["half2_net1_bp"] > 0),
              "without_best_coin": bool(d["wo_best_net1_bp"] > 0),
              "trimmed_positive": bool(np.isfinite(d["trim10_net1_bp"]) and d["trim10_net1_bp"] > 0),
              "leave_two_coins_out": bool(np.isfinite(d["l2co_net1_bp"]) and d["l2co_net1_bp"] > 0)}
    return {"checks": checks, "verdict": "PASS" if all(checks.values()) else "NULL"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    h = build_hops()
    if a.fetch:
        fetch(h)
        plumbing(h)
        return
    if a.plumbing:
        plumbing(h)
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = base.frozen_inputs(LANE / "PREREG.md")
    n_in = check_manifest()
    n_files = ex.check_data(PROV, DATA, ROOT)
    log(f"PREREG verified {sha[:12]}; {len(shas)} frozen inputs, {n_in} data files, {n_files} minute files match")
    tr = run_all(h)
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    rows = []
    for j in ENTRIES:
        for x in EXITS:
            d = describe(tr[tr.trial == lit.name(j, x)], lit.name(j, x))
            rows.append(d)
            log(f"{d['trial']}: {d['hops']} hops, price {d['price_bp']:+.1f} fund {d['fund_bp']:+.1f} net1 "
                f"{d['net1_bp']:+.1f} (t {d['t1']:.2f}) net2 {d['net2_bp']:+.1f} net3 {d['net3_bp']:+.1f}")
    bk = pd.DataFrame(rows)
    prim = bk[bk.trial == lit.name(*PRIMARY)].iloc[0].to_dict()
    dec = decide(prim)
    per_coin = (tr[tr.trial == lit.name(*PRIMARY)]
                .assign(net1=lambda z: lit.net(z.price.to_numpy(), z.fund.to_numpy(), z.cost_h_bp.to_numpy(), 1))
                .groupby("coin").agg(hops=("net1", "size"), net1_bp=("net1", lambda v: v.mean() * 1e4),
                                     price_bp=("price", lambda v: v.mean() * 1e4),
                                     fund_bp=("fund", lambda v: v.mean() * 1e4),
                                     cost_rt_bp=("cost_h_bp", lambda v: 2 * v.mean())))
    bk.to_csv(res / "trials.csv", index=False, float_format="%.6g")
    per_coin.to_csv(res / "per_coin.csv", float_format="%.6g")
    tr.to_csv(res / "hops.csv.gz", index=False, float_format="%.8g")
    if ex.check_data(PROV, DATA, ROOT) != n_files or check_manifest() != n_in:
        raise prereg.PreregError("inputs changed during the run")
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "primary": lit.name(*PRIMARY),
               "decision": dec, "verdict": dec["verdict"], "inputs": shas, "data_files": n_in,
               "minute_files": n_files, "primary_stats": prim}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {dec['verdict']} {dec['checks']}")


if __name__ == "__main__":
    main()
