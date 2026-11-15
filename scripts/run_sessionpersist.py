"""sessionpersist_v1 (R493, M541): does the trailing same-session return of an altcoin perp predict
its next-day return in the cross-section, with the opposite sign across sessions (Bogousslavsky 2021
transfer)? Gate 0 on Binance Vision history; the frozen PREREG decides. The holdout is never read.

Two phases, one writer:
  prepare  metadata-only: freeze the candidate set (first 80 archive USDT perps in listing order),
           write universe.json and the PREREG inputs block, freeze the PREREG. No price, volume
           or funding value of any candidate is read here.
  run      verify the freeze and input hashes; fetch the candidates' klines with strict SHA-256;
           select the top 50 by trailing 30-day quote volume at 2026-09-30 (a declared
           latest-vintage selection diagnostic, computed before any factor); fetch funding for
           the chosen 50 (diagnostic only); compute the three pre-registered factors; report
           discovery/validation at 1x/2x/3x against a moving-block bootstrap null; write
           results/report.json and FINDINGS.md.

usage: python scripts/run_sessionpersist.py prepare
       python scripts/run_sessionpersist.py run
"""
import argparse
import hashlib
import json
import re
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, factor_report, prereg, registry  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "sessionpersist_v1"
RAW = LANE / "raw"
TOP = 50
RANK_END = "2026-09-30"          # trailing-liquidity rank as of the archive end (latest vintage)
RANK_WINDOW_DAYS = 30
FIRST_DAY = "2020-10-01"         # 92 warm-up days before the 2021-01-01 discovery start
END = "2026-09-30"
DISC = ("2021-01-01", "2023-12-31")
VAL = ("2024-01-01", "2025-06-30")
HOLDOUT_START = "2025-07-01"     # never read by this lane
SESSION_A = tuple(range(0, 14))  # hours [00:00, 14:00) UTC
SESSION_B = tuple(range(14, 24)) # hours [14:00, 24:00) UTC
LOOKBACK = 7
MIN_SESSION_HOURS = 150          # of 168 lookback hours, per session factor
MIN_24H_DAYS = 6                 # of 7 daily returns, for the control
MIN_SCORES = 15                  # cross-sectional minimum, as R222
Q = 5
COST_PER_SIDE = 0.0009363545168920655  # R224 median $10k API all-in: 8 bp taker + 0.6765 half-spread + 1.3635 impact
COST_MULT = (1, 2, 3)
NW_LAG = 10
N_NULL = 200
BLOCK = 20
SEED = 20261115
FACTORS = ("S_A", "S_B", "MOM24")
DAY_MS = 86_400_000
HOUR_MS = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


# ---------------------------------------------------------------- prepare
def _prov_symbols(path):
    d = json.loads((ROOT / path).read_text())
    cov = d.get("coverage", {}).get("", {})
    if cov:
        return set(cov)
    return {Path(f["path"]).stem for f in d.get("file_hashes", [])}


def prepare():
    if (LANE / "PREREG.sha256").exists():
        raise SystemExit("already frozen; a changed idea is a new lane")
    kl = _prov_symbols("docs/provenance/klines_1h.json")
    fr = _prov_symbols("docs/provenance/fundingRate.json")
    tradfi = set(json.loads((ROOT / "experiments/venue_gap_v1/results/tradfi_symbols.json").read_text()))
    cut = ms("2024-01-01")
    prov = json.loads((ROOT / "docs/provenance/klines_1h.json").read_text())["coverage"][""]
    # point-in-time, delisting-inclusive: listed before discovery, crypto (R216 TradFi excluded),
    # and present in the frozen funding manifest so the carry diagnostic is available.
    cands = sorted(s for s in kl & fr
                   if s.endswith("USDT") and s not in tradfi and prov[s]["first"] < cut)
    body = {"rule": "USDT perps in the frozen docs/provenance/klines_1h.json AND fundingRate.json "
                    "coverage, first bar before 2024-01-01 (point-in-time, delisting-inclusive), "
                    "minus R216's frozen TradFi list (experiments/venue_gap_v1/results/tradfi_symbols.json). "
                    f"Universe = top {TOP} by trailing {RANK_WINDOW_DAYS}-day quote volume at {RANK_END}, "
                    "computed in run before any factor; eligibility re-ranks point-in-time daily.",
            "listed_utc": datetime.now(timezone.utc).isoformat(),
            "klines_provenance_symbols": len(kl), "funding_provenance_symbols": len(fr),
            "candidate_count": len(cands), "candidates": cands}
    (LANE / "universe.json").write_text(json.dumps(body, indent=1) + "\n")
    prereg_path = LANE / "PREREG.md"
    text = prereg_path.read_text()
    if "```inputs" in text:
        raise SystemExit("PREREG already has an inputs block")
    inputs = ["experiments/sessionpersist_v1/universe.json",
              "docs/provenance/klines_1h.json",
              "docs/provenance/fundingRate.json",
              "experiments/venue_gap_v1/results/tradfi_symbols.json"]
    block = "```inputs\n" + "".join(f"{sha(ROOT / p)} {p}\n" for p in inputs) + "```\n"
    prereg_path.write_text(text.rstrip() + "\n\n## Inputs (frozen)\n" + block)
    digest = prereg.freeze(prereg_path)
    log(f"frozen {digest[:12]}; {len(cands)} candidates "
        f"(klines prov {len(kl)}, funding prov {len(fr)}, R216 tradfi {len(tradfi)})")


# ---------------------------------------------------------------- verification
def check_inputs():
    block = re.search(r"```inputs\n(.*?)```", (LANE / "PREREG.md").read_text(), re.S).group(1)
    n = 0
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = sha(ROOT / rel)
        if got != want:
            raise SystemExit(f"{rel}: sha256 {got} != frozen {want}")
        n += 1
    return n


def check_raw_manifest():
    man = json.loads((RAW / "manifest.json").read_text())
    for rel, want in man["files"].items():
        if sha(RAW / rel) != want:
            raise SystemExit(f"raw/{rel}: sha256 differs from raw/manifest.json")
    return man


def write_raw_manifest():
    files = {}
    for p in sorted(RAW.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files[str(p.relative_to(RAW))] = sha(p)
    body = {"written_utc": datetime.now(timezone.utc).isoformat(), "files": files}
    (RAW / "manifest.json").write_text(json.dumps(body, indent=1, sort_keys=True) + "\n")
    return body


# ---------------------------------------------------------------- selection and panel
def fetch_rank_month(candidates):
    """One monthly kline file per candidate (the rank month), strict SHA-256. Bounded screen:
    reads quote volume only, no factor or forward return."""
    keys = [f"data/futures/um/monthly/klines/{s}/1h/{s}-1h-{RANK_END[:7]}.zip" for s in candidates]
    paths = {}
    with ThreadPoolExecutor(8) as ex:
        got = ex.map(lambda k: data.fetch(k, RAW / "zips", strict=True), keys)
        for s, p in zip(candidates, got):
            if p is not None:
                paths[s] = p
    log(f"rank month {RANK_END[:7]}: {len(paths)}/{len(candidates)} candidate files")
    return paths


def select_universe(rank_paths):
    """Top TOP candidates by trailing quote volume at RANK_END. Reads volume only; no factor,
    forward return or funding value is computed here."""
    t1 = ms(RANK_END) + DAY_MS
    t0 = t1 - RANK_WINDOW_DAYS * DAY_MS
    vol = {}
    for sym, p in rank_paths.items():
        df = data.parse(p, "klines")
        w = df[(df.t >= t0) & (df.t < t1)]
        if len(w) >= 24 * (RANK_WINDOW_DAYS - 2):
            vol[sym] = float(w.quote_volume.sum())
    ranked = sorted(vol, key=lambda s: (-vol[s], s))
    chosen = ranked[:TOP]
    if len(chosen) < TOP:
        raise SystemExit(f"only {len(chosen)} candidates have a full rank window")
    return chosen, {s: vol[s] for s in ranked}


def load_panel(symbols):
    """Daily 00:00 UTC closes (the hour-0 bar's open), session sums of hourly log returns and
    daily quote volume, all [D, S]; NaN where the bar is absent."""
    days = pd.date_range(FIRST_DAY, END, freq="D", tz="UTC")
    d, s = len(days), len(symbols)
    close = np.full((d, s), np.nan)
    sess = {k: np.full((d, s), np.nan) for k in ("A", "B")}
    hours = {k: np.zeros((d, s)) for k in ("A", "B")}
    qvol = np.full((d, s), np.nan)
    barcount = np.zeros((d, s))
    coverage = {}
    base = ms(FIRST_DAY)
    for j, sym in enumerate(symbols):
        df = pd.read_parquet(RAW / "klines_1h" / f"{sym}.parquet")
        df = df[(df.t >= base) & (df.t < ms(END) + DAY_MS)]
        if df.empty:
            coverage[sym] = {"hours": 0}
            continue
        t = df.t.to_numpy()
        di = ((t - base) // DAY_MS).astype(int)
        hr = ((t % DAY_MS) // HOUR_MS).astype(int)
        c = df.close.to_numpy(dtype=float)
        lr = np.full(len(df), np.nan)
        lr[1:] = np.log(c[1:] / c[:-1])
        sel0 = hr == 0
        close[di[sel0], j] = df.open.to_numpy(dtype=float)[sel0]
        for name, hrs in (("A", SESSION_A), ("B", SESSION_B)):
            m = np.isin(hr, hrs) & np.isfinite(lr)
            np.add.at(sess[name], (di[m], j), lr[m])
            np.add.at(hours[name], (di[m], j), 1.0)
        np.add.at(qvol, (di, j), df.quote_volume.to_numpy(dtype=float))
        np.add.at(barcount, (di, j), 1.0)
        coverage[sym] = {"hours": int(len(df)),
                         "first_utc": str(pd.Timestamp(int(t[0]), unit="ms", tz="UTC")),
                         "last_utc": str(pd.Timestamp(int(t[-1]), unit="ms", tz="UTC"))}
    qvol[barcount < 20] = np.nan   # a day with fewer than 20 of 24 bars is not a liquidity observation
    return days, close, sess, hours, qvol, coverage


def eligibility(close, qvol):
    """Point-in-time top-50 by trailing 30-day mean quote volume through day d-1, among symbols
    with a close at d-1 and d. Returns bool [D, S]."""
    d, s = close.shape
    trail = np.full((d, s), np.nan)
    win = np.lib.stride_tricks.sliding_window_view(qvol, RANK_WINDOW_DAYS, axis=0)
    ok = np.isfinite(win).sum(axis=2) >= RANK_WINDOW_DAYS - 5
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN windows are expected before listing
        means = np.where(ok, np.nanmean(win, axis=2), np.nan)
    trail[RANK_WINDOW_DAYS - 1:] = means
    elig = np.zeros((d, s), dtype=bool)
    for i in range(1, d):
        have = np.isfinite(close[i]) & np.isfinite(close[i - 1]) & np.isfinite(trail[i - 1])
        idx = np.flatnonzero(have)
        if len(idx) == 0:
            continue
        order = idx[np.argsort(-trail[i - 1][idx], kind="stable")][:TOP]
        elig[i, order] = True
    return elig, trail


def build_factors(close, sess, hours):
    d, s = close.shape
    ret = np.full((d, s), np.nan)
    ret[1:] = np.log(close[1:] / close[:-1])
    factors = {}
    for name, key in (("S_A", "A"), ("S_B", "B")):
        arr, hrs = sess[key], hours[key]
        wsum = np.lib.stride_tricks.sliding_window_view(arr, LOOKBACK, axis=0)
        whrs = np.lib.stride_tricks.sliding_window_view(hrs, LOOKBACK, axis=0)
        tot = np.where(np.isnan(wsum).any(axis=2), np.nan, np.nansum(wsum, axis=2))
        enough = whrs.sum(axis=2) >= MIN_SESSION_HOURS
        f = np.full((d, s), np.nan)
        f[LOOKBACK - 1:] = np.where(enough, tot, np.nan)
        factors[name] = f
    wret = np.lib.stride_tricks.sliding_window_view(ret, LOOKBACK, axis=0)
    nok = np.isfinite(wret).sum(axis=2)
    tot = np.where(nok >= MIN_24H_DAYS, np.nansum(wret, axis=2), np.nan)
    f = np.full((d, s), np.nan)
    f[LOOKBACK - 1:] = tot
    factors["MOM24"] = f
    return factors, ret


# ---------------------------------------------------------------- statistics
def window_slice(days, window):
    lo = int(days.searchsorted(pd.Timestamp(window[0], tz="UTC")))
    hi = int(days.searchsorted(pd.Timestamp(window[1], tz="UTC"))) + 1
    return lo, hi


def holdout_cut(days):
    return int(days.searchsorted(pd.Timestamp(HOLDOUT_START, tz="UTC")))


def _nanmean(x):
    x = np.asarray(x, dtype=float)
    return float(np.nanmean(x)) if np.isfinite(x).any() else float("nan")


def nw_t(x, lag=NW_LAG):
    n, mean, t = newey_west_t(np.asarray(x, dtype=float), lag)
    return {"days": n, "mean_bp_day": mean * 1e4, "nw_t": t}


def book_series(factor, fwd, elig):
    w = factor_report.book_weights(factor, elig, q=Q, min_obs=MIN_SCORES)
    gross = factor_report.gross_book(w, fwd)
    to = factor_report.turnover(w)
    return w, gross, to


def block_bootstrap_t(gross, n_null=N_NULL, block=BLOCK, seed=SEED):
    """Moving-block bootstrap of the centered daily series; returns all null NW t values."""
    x = np.asarray(gross, dtype=float)
    ok = np.isfinite(x)
    if ok.sum() < block * 2:
        return np.zeros(n_null)
    z = np.where(ok, x - np.nanmean(x), 0.0)
    n = len(z)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    ts = np.empty(n_null)
    for b in range(n_null):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([z[s:s + block] for s in starts])[:n]
        _, _, t = newey_west_t(sample, NW_LAG)
        ts[b] = t if np.isfinite(t) else 0.0
    return ts


def evaluate(days, factors, ret, elig):
    fwd = np.full_like(ret, np.nan)
    fwd[:-1] = ret[1:]
    disc_lo, disc_hi = window_slice(days, DISC)
    val_lo, val_hi = window_slice(days, VAL)
    out, null_ts = {}, {}
    for name in FACTORS:
        f = factors[name]
        ic, _ = factor_report.rank_ic(f, fwd, elig, min_obs=MIN_SCORES)
        w, gross, to = book_series(f, fwd, elig)
        nets = {m: gross - to * COST_PER_SIDE * m for m in COST_MULT}
        row = {"ic": {}, "book": {}}
        for label, (lo, hi) in (("disc", (disc_lo, disc_hi)), ("val", (val_lo, val_hi))):
            row["ic"][label] = factor_report.ic_summary(ic[lo:hi], lag=NW_LAG)
            row["book"][label] = {
                "gross": nw_t(gross[lo:hi]),
                "net": {str(m): nw_t(nets[m][lo:hi]) for m in COST_MULT},
                "mean_one_way_turnover": _nanmean(to[lo:hi]),
            }
        d_net = row["book"]["disc"]["net"]["1"]
        v_net = row["book"]["val"]["net"]["1"]
        row["discovery_pass"] = bool(d_net["mean_bp_day"] > 0 and d_net["nw_t"] >= 2.0)
        row["validation_pass"] = bool(v_net["mean_bp_day"] > 0 and v_net["nw_t"] >= 1.5)
        out[name] = row
        null_ts[name] = block_bootstrap_t(gross[disc_lo:disc_hi])
    fam_max = np.max(np.stack([null_ts[n] for n in FACTORS]), axis=0)
    null = {"per_factor_q95_t": {n: float(np.quantile(null_ts[n], 0.95)) for n in FACTORS},
            "family_max_q95_t": float(np.quantile(fam_max, 0.95)),
            "n_null": N_NULL, "block": BLOCK, "seed": SEED}
    for name in FACTORS:
        t_real = out[name]["book"]["disc"]["net"]["1"]["nw_t"]
        out[name]["null"] = {"q95_t": null["per_factor_q95_t"][name],
                             "family_fwer_p": float((fam_max >= t_real).mean())}
    return out, null


def funding_diagnostic(symbols):
    """Mean settled funding per symbol over the read window (diagnostic; books are gross of it)."""
    out = {}
    for sym in symbols:
        p = RAW / "fundingRate" / f"{sym}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        df = df[(df.t >= ms(FIRST_DAY)) & (df.t < ms(HOLDOUT_START))]
        if df.empty:
            continue
        out[sym] = {"settlements": int(len(df)), "mean_rate_bp": float(df.rate.mean()) * 1e4}
    return out


def verdict_of(results):
    disc_pass = [n for n in FACTORS if results[n]["discovery_pass"]]
    if not disc_pass:
        return "NULL"
    if any(results[n]["validation_pass"] for n in disc_pass):
        return "PARTIAL"
    return "NULL"


def write_findings(rep):
    r, null = rep["results"], rep["null"]
    lines = ["# FINDINGS: sessionpersist_v1 (R493, M541)",
             "",
             f"Run {rep['completed_utc']} by `scripts/run_sessionpersist.py run`; PREREG "
             f"`{rep['prereg_sha256'][:12]}` verified before and after; raw manifest "
             f"`{rep['raw_manifest_sha256'][:12]}`. Gate 0, latest-vintage public archive, "
             "exploratory. The holdout (2025-07-01 onward) was not read.",
             "",
             f"**Verdict: {rep['verdict']}.** Three pre-registered factors, no search. "
             f"Program trials before: {rep['program_trials_before']:,}; this lane adds {rep['trials']}.",
             "",
             "## Universe and coverage",
             "- Candidates: USDT perps present in both frozen provenance manifests with a first bar "
             "before 2024-01-01, minus R216's frozen TradFi list (frozen in universe.json before any "
             f"price was read). Universe: top {TOP} by trailing {RANK_WINDOW_DAYS}-day quote volume "
             f"at {RANK_END} (latest-vintage selection, declared); daily eligibility re-ranks "
             "point-in-time on trailing volume through d-1.",
             f"- Mean eligible names per day: {rep['coverage']['mean_eligible_per_day']:.1f}. "
             f"Book-leg mentions: {rep['coverage']['book_leg_mentions']['survivor']} survivor / "
             f"{rep['coverage']['book_leg_mentions']['later_delisted']} later-delisted symbols.",
             "- Survivorship: the archive includes delisted contracts, and eligibility uses only "
             "data through d-1, so a name that later dies is tradable while it lived. The "
             "first-bar-before-2024 filter excludes later listings by design (they have no "
             "discovery-window history); the result is bounded to seasoned perps, not the full "
             "listing universe. Latest-vintage volume ranking is the remaining selection caveat.",
             "",
             f"## Results (bp/day; NW t lag 10; cost {COST_PER_SIDE*1e4:.2f} bp/side at 1x = R224 median $10k API all-in)",
             "",
             "| factor | window | gross | net 1x | net 2x | net 3x | NW t (1x) | rank IC | IC t |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name in FACTORS:
        for w in ("disc", "val"):
            b = r[name]["book"][w]
            ic = r[name]["ic"][w]
            lines.append(
                f"| {name} | {w} | {b['gross']['mean_bp_day']:+.2f} | "
                f"{b['net']['1']['mean_bp_day']:+.2f} | {b['net']['2']['mean_bp_day']:+.2f} | "
                f"{b['net']['3']['mean_bp_day']:+.2f} | {b['net']['1']['nw_t']:+.2f} | "
                f"{ic['mean_ic']:+.4f} | {ic['nw_t']:+.2f} |")
    lines += ["",
              f"Discovery gate: net 1x mean > 0 and NW t >= 2.0. Validation gate (read for every "
              f"factor, no selection): mean > 0 and t >= 1.5. Passes: "
              f"{[n for n in FACTORS if r[n]['discovery_pass']] or 'none'} (discovery), "
              f"{[n for n in FACTORS if r[n]['validation_pass']] or 'none'} (validation).",
              "",
              "## Null (moving-block bootstrap, centered discovery gross)",
              f"- {N_NULL} replicas, block {BLOCK} days, seed {SEED}.",
              f"- Per-factor 95th-pct t: " +
              ", ".join(f"{n} {null['per_factor_q95_t'][n]:.2f}" for n in FACTORS) + ".",
              f"- Family-max 95th-pct t (3 trials): {null['family_max_q95_t']:.2f}.",
              f"- Family-wise p (share of null family maxima >= real discovery 1x t): " +
              ", ".join(f"{n} {r[n]['null']['family_fwer_p']:.3f}" for n in FACTORS) + ".",
              "",
              "## Funding diagnostic (not charged to the books)",
              "Mean settled funding over the read window, bp per settlement: " +
              ", ".join(f"{s} {v['mean_rate_bp']:+.2f}" for s, v in
                        sorted(rep["funding_diagnostic"].items())[:10]) +
              " (first 10 symbols; full table in results/report.json).",
              "",
              "## Limits",
              "- Gate 0 on seen history; no reserved sample, no forward day, no gate-1 claim.",
              "- Costs are R224's measured median $10k MEXC API all-in per side (8 bp taker + "
              "0.6765 bp half-spread + 1.3635 bp impact); 2x/3x bracket a worse book. R224 reports "
              "every one of its 37 coins above the assumed 8 bp at $10k, so 1x is not conservative.",
              "- Books are gross of funding; the diagnostic above bounds the carry overlay.",
              "- Session cut 00-14/14-24 UTC is fixed, not tuned; the 24h control MOM24 is the "
              "no-split comparison. A different cut is a new lane.",
              "- Rank IC and quantile reports come from lab/factor_report.py (unit-tested).",
              "",
              "## Reproduce",
              "```sh",
              "python scripts/run_sessionpersist.py run   # verifies the freeze, re-fetches, re-runs",
              "```",
              ""]
    (LANE / "FINDINGS.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=["prepare", "run"])
    a = ap.parse_args()
    if a.phase == "prepare":
        prepare()
        return
    frozen = prereg.verify(LANE / "PREREG.md")
    n_inputs = check_inputs()
    started = datetime.now(timezone.utc).isoformat()
    cands = json.loads((LANE / "universe.json").read_text())["candidates"]
    log(f"bounded rank screen over {len(cands)} candidates")
    rank_paths = fetch_rank_month(cands)
    chosen, rank_vol = select_universe(rank_paths)
    log(f"universe ({len(chosen)}): {' '.join(chosen)}")
    log(f"fetching full history for the {len(chosen)} chosen symbols (klines 1h, strict)")
    data.build("klines", "1h", symbols=chosen, workers=8, strict=True, end=END, root=RAW, log=log)
    log("fetching fundingRate for the universe (diagnostic only)")
    data.build("fundingRate", symbols=chosen, workers=8, strict=True, end=END, root=RAW, log=log)
    write_raw_manifest()
    days, close, sess, hours, qvol, coverage = load_panel(chosen)
    elig, _ = eligibility(close, qvol)
    factors, ret = build_factors(close, sess, hours)
    cut = holdout_cut(days)
    days, close = days[:cut], close[:cut]
    elig, ret = elig[:cut], ret[:cut]
    factors = {k: v[:cut] for k, v in factors.items()}
    results, null = evaluate(days, factors, ret, elig)
    last_day = ms(END)
    alive = {s for s in chosen if coverage[s]["hours"] > 0 and
             ms(coverage[s]["last_utc"][:10]) >= last_day - 2 * DAY_MS}
    leg_counts = {"survivor": 0, "later_delisted": 0}
    for name in FACTORS:
        w = factor_report.book_weights(factors[name], elig, q=Q, min_obs=MIN_SCORES)
        for j, sym in enumerate(chosen):
            if (w[:, j] != 0).any():
                leg_counts["survivor" if sym in alive else "later_delisted"] += 1
    rep = {
        "round": "R493", "method": "M541", "lane": "sessionpersist_v1",
        "prereg_sha256": frozen, "inputs_checked": n_inputs,
        "raw_manifest_sha256": sha(RAW / "manifest.json"),
        "started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
        "program_trials_before": registry.program_trials(ROOT / "registry" / "rounds.csv"),
        "trials": len(FACTORS),
        "universe": chosen, "rank_volume_usd": rank_vol,
        "cost_per_side": COST_PER_SIDE, "cost_mult": list(COST_MULT),
        "holdout_read": False,
        "results": results, "null": null,
        "coverage": {"symbols": coverage, "book_leg_mentions": leg_counts,
                     "mean_eligible_per_day": _nanmean(elig.sum(axis=1))},
        "funding_diagnostic": funding_diagnostic(chosen),
    }
    rep["verdict"] = verdict_of(results)
    out = LANE / "results"
    out.mkdir(exist_ok=False)
    (out / "report.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")
    check_inputs()
    check_raw_manifest()
    write_findings(rep)
    log(f"verdict {rep['verdict']}; wrote {out / 'report.json'} and FINDINGS.md")


if __name__ == "__main__":
    main()
