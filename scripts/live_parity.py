"""Live vs archive parity: are the live public endpoints the same data as the archive the lanes were built on?

On the last archive days that the live ratio endpoints still cover (they keep about 28 days), rebuild the hourly
metrics, the flow features and their xs8 bins from live data with the archive's own code (lab/flowfeat.py), on the
archive's eligibility, and compare cell by cell; then compare the liquidity ranks rebuilt from live klines with the
archive's ranks. A data check, not a return statistic: nothing here reads returns.

usage: python scripts/live_parity.py [--start 2026-09-23] [--end 2026-10-01] [--skip-rank]
writes data/live/parity/*.parquet (cache) and the summary experiments/flow72_fwd/parity.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, flowfeat, live, panel, research  # noqa: E402

OUT = ROOT / "experiments" / "flow72_fwd2"
CHECK = ("top_vs_crowd", "taker[4]", "taker[24]", "crowd_ls", "top_ls", "oi_chg[24]")
HOUR = live.HOUR
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def raw_parity(live_m, arch_m, rows_ok):
    out = {}
    for c in flowfeat.METRIC_COLS:
        a, b = arch_m[c][rows_ok], live_m[c][rows_ok]
        both = np.isfinite(a) & np.isfinite(b) & (a != 0)
        rel = np.abs(b[both] / a[both] - 1)
        out[c] = {"cells_archive": int(np.isfinite(a).sum()), "cells_both": int(both.sum()),
                  "live_missing": int((np.isfinite(a) & ~np.isfinite(b)).sum()),
                  "median_rel_diff": float(np.median(rel)) if rel.size else None,
                  "share_within_1e-3": float((rel <= 1e-3).mean()) if rel.size else None}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-09-23")
    ap.add_argument("--end", default="2026-10-01")
    ap.add_argument("--warmup-hours", type=int, default=36)
    ap.add_argument("--skip-rank", action="store_true")
    ap.add_argument("--lane", default="flow72_fwd2")
    a = ap.parse_args()
    global OUT
    OUT = ROOT / "experiments" / a.lane
    u, _, _ = research.load_universe()
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    t = u.p.t
    r0, r1 = research.row_of(u.p, a.start), research.row_of(u.p, a.end)
    w0 = r0 - a.warmup_hours
    sl = slice(w0, r1)
    elig = u.elig[sl]
    cols = np.flatnonzero(elig.any(axis=0))
    syms = [u.p.symbols[j] for j in cols]
    log(f"rows {a.start}..{a.end} ({r1 - r0} h, warm-up {a.warmup_hours} h), {len(syms)} symbols eligible")

    # live 5-minute rows -> hourly metrics (taker stamped by window start: try both alignments)
    start, end = int(t[w0]), int(t[r1 - 1]) + HOUR
    frames = {}
    for i, s in enumerate(syms):
        frames[s] = live.ratios_cached(s, start, end)
        if i % 10 == 0:
            log(f"ratios {i + 1}/{len(syms)} {s}")
    tt = t[sl]
    arch = flowfeat.load("metrics", tt, syms, flowfeat.METRIC_COLS)
    rows_ok = np.zeros(len(tt), bool)
    rows_ok[a.warmup_hours:] = True
    summary = {"start": a.start, "end": a.end, "symbols": len(syms), "alignment": {}}
    # per endpoint, the stamp shift (minutes) that puts live rows on the archive's clock
    shifts = {}
    for ep in list(frames[syms[0]]):
        col = live.RATIOS[ep][0] if ep in live.RATIOS else "oi"
        best = None
        for sh in (-2 * live.FIVE, -live.FIVE, 0, live.FIVE):
            hm = {s: live.hourly_metrics({ep: f[ep]}, {ep: sh}) for s, f in frames.items()}
            lm1 = live.grid(hm, tt, col)
            a1, b1 = arch[col][rows_ok], lm1[rows_ok]
            both = np.isfinite(a1) & np.isfinite(b1) & (a1 != 0)
            share = float((np.abs(b1[both] / a1[both] - 1) <= 1e-4).mean()) if both.any() else 0.0
            summary["alignment"].setdefault(ep, {})[str(sh // 60_000)] = share
            if best is None or share > best[1]:
                best = (sh, share)
        shifts[ep] = int(best[0])
    summary["shifts_ms"] = shifts
    summary["shifts_match_archive_default"] = shifts == {k: v for k, v in live.ARCHIVE_SHIFTS.items() if k in shifts}
    hm = {s: live.hourly_metrics(f, shifts) for s, f in frames.items()}
    lm = {c: live.grid(hm, tt, c) for c in flowfeat.METRIC_COLS}
    rp = raw_parity(lm, arch, rows_ok)
    summary["raw"] = rp
    log("alignment", json.dumps(summary["alignment"]), "chosen", shifts)
    log("raw parity", json.dumps(rp, indent=1))

    # features and bins, built by the archive's code on the archive's eligibility
    close = u.p["close"][sl][:, cols]
    zero = np.zeros_like(close)
    elig = elig[:, cols]
    # "all": live values for every eligible coin; "common": live values only where the archive has the raw input
    # (the archive lacks metrics for coins with non-ASCII names), which isolates the data from coverage
    common = {c: np.where(np.isfinite(arch[c]), lm[c], np.nan) for c in lm}
    for mode, M in (("all", lm), ("common", common)):
        f_live = flowfeat.raw_features(M, None, close, zero)
        bins = {}
        for name in CHECK:
            spec = f"flow:{name}/xs8"
            if spec not in fn:
                continue
            lb = flowfeat.binned(f_live[name], flowfeat.XS8, elig)[rows_ok]
            ab = np.asarray(fb[fn.index(spec)][w0:r1])[:, cols][rows_ok]
            e = elig[rows_ok]
            valid = e & (ab >= 0)
            bins[spec] = {"eligible_cells": int(e.sum()), "archive_binned": int(valid.sum()),
                          "match": float((lb[valid] == ab[valid]).mean()) if valid.any() else None,
                          "within_one": float((np.abs(lb[valid].astype(int) - ab[valid]) <= 1).mean())
                          if valid.any() else None,
                          "bin0_archive": int((ab[valid] == 0).sum()), "bin0_live": int((lb[valid] == 0).sum()),
                          "bin0_agree": int(((ab == 0) & (lb == 0) & valid).sum())}
        summary["bins" if mode == "all" else "bins_common"] = bins
        log(f"bin parity ({mode})", json.dumps(bins, indent=1))
    summary["archive_no_metrics"] = [syms[j] for j in range(len(syms))
                                     if (elig[rows_ok, j] & ~np.isfinite(arch["top_ls_sum"][rows_ok, j])).any()]

    if not a.skip_rank:
        # liquidity rank at the last archive rows, rebuilt from live klines for every perpetual trading now
        perps = live.perpetuals(statuses=("TRADING", "SETTLING"))
        k0 = int(t[r1 - 1]) - 720 * HOUR - 24 * HOUR
        kl = {}
        for i, s in enumerate(perps):
            try:
                kl[s] = live.klines_cached(s, k0, int(time.time() * 1000) // HOUR * HOUR)
            except live.LiveError as e:
                log("klines failed", s, e)
            if i % 50 == 0:
                log(f"klines {i + 1}/{len(perps)}")
        kt = np.arange(k0, int(t[r1 - 1]) + HOUR, HOUR)
        lrank = live.liquidity_rank(live.grid(kl, kt, "quote_volume"), live.grid(kl, kt, "close"))
        names = list(kl)
        last = range(len(kt) - 24, len(kt))
        overlaps = []
        for i in last:
            row = research.row_of(u.p, "2026-09-30") + (i - (len(kt) - 24))
            arch_top = {u.p.symbols[j] for j in np.flatnonzero(u.elig[row])}
            live_top = {names[j] for j in np.flatnonzero(lrank[i] <= 50)}
            overlaps.append(len(arch_top & live_top) / max(len(arch_top), 1))
        summary["rank"] = {"perpetuals_live": len(perps), "top50_overlap_mean": float(np.mean(overlaps)),
                           "top50_overlap_min": float(np.min(overlaps))}
        log("rank parity", summary["rank"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "parity.json").write_text(json.dumps(summary, indent=1))
    log("written", OUT / "parity.json")


if __name__ == "__main__":
    main()
