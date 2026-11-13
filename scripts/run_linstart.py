"""linstart_v1 (R485, M538): short an OKX USDT swap from the 1Dutc close of D-7 to the 1Dutc close of D+14 around an
insiders/privateSale linear-vesting start D, as set out in experiments/linstart_v1/PREREG.md. Gate 0.
Verifies the PREREG, the frozen inputs and the snapshot, rebuilds events.csv and symbol_map.csv byte for byte, and
only then reads the candles fetched after the freeze (scripts/fetch_linstart.py, raw/manifest.json).

usage: python scripts/run_linstart.py
"""
import gzip
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data, prereg  # noqa: E402
import linstart_events as le  # noqa: E402
from run_unlocks import cluster_t  # noqa: E402  (R265's week-cluster t, same formula)

LANE = ROOT / "experiments" / "linstart_v1"
SNAP = data.ROOT / "unlocks" / "2026-11-13"
FROZEN = {"events.csv": "1d671c0467254640cd5163d70e1816ea0c48893cfa8977188e546e5fabd29f9f",
          "symbol_map.csv": "bacb9e3ac400a9a9345631d94dd663b01716da1180df28160bb7984445eb5509",
          "okx_instruments_swap.json": "e0ca70b9b3e62eda2317afecc02325c2959d0a30b5db9f2779a86328698810b7",
          "okx_tickers_swap.json": "371a8c31e8dbd901809d4ddfc5bb701fdbb0699177f21adc82594da44c39602f"}
SNAP_MANIFEST = "7163cf7d237dd3f02e7955f43b8e36f18d3965f273d61a2354358ab7415ea50c"
COST = {1: 0.002, 2: 0.004, 3: 0.006}            # round trip
REPS, SEED = 2000, 485
MIN_N = 20
ENTRY_OFF, EXIT_OFF = -7, 14                     # days relative to D
NULL_GAP = 30                                    # admissible D' is more than 30 days from every event day of the swap
DAY = le.DAY
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_inputs():
    for name, want in FROZEN.items():
        assert sha(LANE / name) == want, f"{name} differs from the frozen sha"
    assert sha(SNAP / "manifest.json") == SNAP_MANIFEST, "snapshot manifest differs from the frozen sha"
    files = json.loads((SNAP / "manifest.json").read_text())["files"]
    for rel, meta in files.items():
        raw = gzip.decompress((SNAP / rel).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == meta["sha256"], f"snapshot file {rel} changed"
    with tempfile.TemporaryDirectory() as d:
        le.build(SNAP, d, LANE / "okx_instruments_swap.json", LANE / "okx_tickers_swap.json", SNAP.name)
        for name in ("events.csv", "symbol_map.csv"):
            assert sha(Path(d) / name) == FROZEN[name], f"rebuilt {name} does not reproduce the frozen file"
    log(f"inputs: frozen files match, {len(files)} snapshot files verified, rebuild reproduces both byte for byte")


def check_raw():
    man_path = LANE / "raw" / "manifest.json"
    man = json.loads(man_path.read_text())
    for rel, meta in man["files"].items():
        assert sha(LANE / "raw" / rel) == meta["sha256"], f"raw file {rel} changed"
    return sha(man_path), man


def closes_from_rows(rows):
    """OKX candle rows [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm] -> Series of confirmed closes by day ms."""
    s = {int(r[0]): float(r[4]) for r in rows if str(r[8]) == "1"}
    return pd.Series(s, dtype=float).sort_index()


def trade(closes, day_ms):
    """Short from the close of D-7 to the close of D+14. Returns (gross, exit_early) or None (no_market: no candle
    at D-7). If D+14 has no candle, the exit is the last close after the entry and before D+14 (exit_early)."""
    e = day_ms + ENTRY_OFF * DAY
    x = day_ms + EXIT_OFF * DAY
    if e not in closes.index:
        return None
    ce = closes[e]
    if x in closes.index:
        return -(closes[x] / ce - 1), False
    later = closes[(closes.index > e) & (closes.index < x)]
    cx = later.iloc[-1] if len(later) else ce
    return -(cx / ce - 1), True


def net(gross, mult):
    return np.asarray(gross, float) - COST[mult]


def admissible_days(closes, event_days, first_ms, last_ms):
    """D' in [first, last] with candles at both D'-7 and D'+14, more than 30 days from every event day."""
    days = np.arange(first_ms, last_ms + 1, DAY, dtype=np.int64)
    ev = np.asarray(sorted(event_days), np.int64)
    if len(ev):
        far = np.abs(days[:, None] - ev[None, :]).min(axis=1) > NULL_GAP * DAY
        days = days[far]
    idx = set(closes.index)
    ok = [d for d in days if d + ENTRY_OFF * DAY in idx and d + EXIT_OFF * DAY in idx]
    return np.asarray(ok, np.int64)


def null_means(cand, groups, n, reps=REPS, seed=SEED):
    """cand: swap -> array of admissible net 1x returns; groups: swap -> count of observed events."""
    rng = np.random.default_rng(seed)
    out = np.zeros(reps)
    for rep in range(reps):
        tot = 0.0
        for s, k in groups.items():
            c = cand[s]
            tot += c[rng.integers(0, len(c), k)].sum()
        out[rep] = tot / n
    return out


def iso_week(day_ms):
    wk = pd.to_datetime(pd.Series(day_ms), unit="ms", utc=True).dt.isocalendar()
    return (wk.year * 100 + wk.week).values


def summarize(x, groups):
    x = np.asarray(x, float)
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "mean_pct": float(x.mean() * 100), "median_pct": float(np.median(x) * 100),
            "hit": float((x > 0).mean()), "week_cluster_t": float(cluster_t(x, groups))}


def gates(priced, p_null):
    x1 = priced.net1x.values
    t1 = cluster_t(x1, priced.week.values) if len(x1) else np.nan
    half = len(priced) // 2
    h1, h2 = priced.net1x.iloc[:half], priced.net1x.iloc[half:]
    top3 = priced.groupby("inst_id").net1x.sum().nlargest(3).index.tolist()
    rest = priced[~priced.inst_id.isin(top3)]
    g = {"G1_cluster_t_ge_2": bool(np.isfinite(t1) and t1 >= 2),
         "G2_null_p_lt_0.05": bool(p_null < 0.05),
         "G3_mean_net_2x_gt_0": bool(len(priced) and priced.net2x.mean() > 0),
         "G4_both_halves_positive": bool(len(h1) and len(h2) and h1.mean() > 0 and h2.mean() > 0),
         "G5_positive_without_top3": bool(len(rest) and rest.net1x.mean() > 0)}
    detail = {"t_1x": float(t1), "half1_mean_pct": float(h1.mean() * 100) if len(h1) else None,
              "half2_mean_pct": float(h2.mean() * 100) if len(h2) else None,
              "half_split_day": priced.day.iloc[half] if len(priced) else None, "top3": top3,
              "without_top3_n": int(len(rest)),
              "without_top3_mean_pct": float(rest.net1x.mean() * 100) if len(rest) else None}
    return g, detail


def verdict(n, g):
    if n < MIN_N:
        return "INSUFFICIENT"
    return "CONFIRMS-ON-HISTORY" if all(g.values()) else "NULL"


def funding_sum(fund, day_ms):
    """Funding received by the short over (close of D-7, close of D+14], or None if OKX's history starts later."""
    if fund is None or not len(fund):
        return None
    lo = day_ms + (ENTRY_OFF + 1) * DAY
    hi = day_ms + (EXIT_OFF + 1) * DAY
    if fund.index.min() > lo:
        return None
    return float(fund[(fund.index > lo) & (fund.index <= hi)].sum())


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs()
    man_sha, man = check_raw()
    log(f"raw: manifest {man_sha[:12]}, {len(man['files'])} files verified")
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    ev = pd.read_csv(LANE / "events.csv")
    arch = ev[ev.window == "archive"].copy()
    closes, fund = {}, {}
    for inst in arch.inst_id.unique():
        closes[inst] = closes_from_rows(json.loads((LANE / "raw" / "okx" / f"{inst}_1Dutc.json").read_text()))
        fr = json.loads((LANE / "raw" / "okx" / f"{inst}_funding.json").read_text())
        fund[inst] = pd.Series({int(r["fundingTime"]): float(r["fundingRate"]) for r in fr}, dtype=float).sort_index()

    gross, early, fsum = [], [], []
    for r in arch.itertuples():
        t = trade(closes[r.inst_id], int(r.day_ms))
        gross.append(np.nan if t is None else t[0])
        early.append(False if t is None else t[1])
        fsum.append(None if t is None else funding_sum(fund[r.inst_id], int(r.day_ms)))
    arch["gross"], arch["exit_early"] = gross, early
    arch["funding"] = pd.Series(fsum, index=arch.index, dtype=float)
    arch["no_market"] = arch.gross.isna()
    priced_all = arch[~arch.no_market].copy()
    priced_all["week"] = iso_week(priced_all.day_ms.values)
    for m in COST:
        priced_all[f"net{m}x"] = net(priced_all.gross, m)
    priced_all = priced_all.sort_values(["day_ms", "inst_id"]).reset_index(drop=True)
    prim = priced_all[priced_all.label == "pure"].reset_index(drop=True)
    log(f"archive {len(arch)} events: priced {len(priced_all)}, no_market {int(arch.no_market.sum())}; "
        f"primary (pure) priced {len(prim)}")

    res = {"prereg_sha": prereg.sha256_file(LANE / "PREREG.md"), "raw_manifest_sha256": man_sha,
           "counts": {"archive_events": int(len(arch)),
                      "archive_by_label": arch.label.value_counts().to_dict(),
                      "no_market_by_label": arch[arch.no_market].label.value_counts().to_dict(),
                      "priced_by_label": priced_all.label.value_counts().to_dict(),
                      "exit_early": int(priced_all.exit_early.sum()),
                      "other_windows": ev[ev.window != "archive"].window.value_counts().to_dict()}}
    res["primary"] = {f"{m}x": summarize(prim[f"net{m}x"], prim.week) for m in COST}
    res["primary"]["gross"] = summarize(prim.gross, prim.week)

    p_null, null = np.nan, None
    if len(prim):
        lo, hi = le.ms(le.FIRST_D), le.ms(le.LAST_D)
        cand = {}
        for s in prim.inst_id.unique():
            days = admissible_days(closes[s], ev[ev.inst_id == s].day_ms.values, lo, hi)
            cand[s] = np.array([trade(closes[s], int(d))[0] for d in days], float) - COST[1]
        empty = sorted(s for s, c in cand.items() if not len(c))
        res["null"] = {"reps": REPS, "seed": SEED, "admissible_days": {s: int(len(c)) for s, c in cand.items()},
                       "swaps_without_admissible_day": empty}
        if not empty:                      # otherwise G2 fails (PREREG)
            groups = prim.groupby("inst_id").size().to_dict()
            null = null_means(cand, groups, len(prim))
            p_null = float((1 + (null >= prim.net1x.mean()).sum()) / (REPS + 1))
            np.savetxt(out / "null_means.csv", null, fmt="%.8f", header="mean net 1x per replication", comments="")
            res["null"].update(mean_pct=float(null.mean() * 100), p95_pct=float(np.quantile(null, 0.95) * 100),
                               p=p_null)
    g, detail = gates(prim, p_null)
    res["gates"], res["gate_detail"] = g, detail
    res["verdict"] = verdict(len(prim), g)
    res["min_n"] = MIN_N

    rep = {}
    for name, df in (("all_archive", priced_all), ("with_cliff", priced_all[priced_all.label == "with_cliff"])):
        rep[name] = {f"{m}x": summarize(df[f"net{m}x"], df.week) for m in COST}
    band = le.dose_band(prim.frac_max_supply.values) if len(prim) else np.array([])
    rep["dose_bands_primary_1x"] = {b: summarize(prim.net1x[band == b], prim.week[band == b])
                                    for b in ("0.25-0.5pct", "0.5-1pct", "ge_1pct")}
    has_f = prim.funding.notna()
    rep["funding"] = {"events_with_funding": int(has_f.sum()),
                      "net1x_incl_funding": summarize((prim.net1x + prim.funding.fillna(0))[has_f], prim.week[has_f]),
                      "funding_mean_pct": float(prim.funding[has_f].mean() * 100) if has_f.any() else None}
    fwd = ev[ev.window == "forward"]
    rep["forward_instances"] = fwd[["day", "inst_id", "frac_max_supply", "label"]].to_dict("records")
    res["reported"] = rep
    res["trials"] = 1
    cols = ["day", "inst_id", "ticker", "label", "frac_max_supply", "cliff_frac_max", "no_market", "exit_early",
            "gross", "funding"]
    arch.sort_values(["day_ms", "inst_id"])[cols].to_csv(out / "events_priced.csv", index=False, float_format="%.6g")
    (out / "verdict.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    log("counts", json.dumps(res["counts"]))
    log("primary", json.dumps(res["primary"]))
    log("null", json.dumps(res.get("null")))
    log("gates", json.dumps(g), json.dumps(detail, default=float))
    log("reported", json.dumps(rep, default=float))
    log("verdict", res["verdict"])


if __name__ == "__main__":
    main()
