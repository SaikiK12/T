"""R392 reserved batch 3 (docs/GATES.md): three pre-committed candidates, read once, as set out in
experiments/reserved_batch3/PREREG.md.

- C17: R300's "us10 n3 follow" (experiments/intrars_v1, M318). At 10:00 New York on NYSE days, long the 3 top-50 perps
  that rose most since the 00:00 UTC close and short the 3 that rose least, flat at the last traded close at or before
  24:00 UTC. Read on reserved 2020 (Binance bars and funding before 2021-01-01, RESERVED-2020-READ).
- M319: the 08:00 clock's pick in R300's FINDINGS. At 16:00 UTC, long the 3 strongest and short the 3 weakest by their
  move since the 08:00 UTC close, held to 08:00 UTC the next day. Also on reserved 2020.
- GLT: R275's carry book (gate+mexc L14d th5% K20, qx spread) on the Gate long tail (`data/gate_hist/reserved/`,
  RESERVED-GATE-READ) with MEXC as the open partner venue, 2021-01-01..2026-09-30. Read 2 of 4 of the Gate sample.

The intraday books are scripts/run_intrars.py's own code (Grid, rows_for, day_books); only the universe build and the
loader are here, because R300's reads the 2021-26 research view. The universe is R300's rule: the liquidity rank of
lab.panel.liquidity_rank over every Binance perp with a bar in the window, restricted to the columns ever in the top
50 (scripts/build_views.py). The carry decision is scripts/decide_reserved_batch2.py's `stats`.

Modes. Every path and window is passed at call time; nothing is bound when the module loads.
- `--symbols` writes experiments/reserved_batch3/symbols.csv from contract lists and file names only (no bar is read).
- `--dry` reads archive data only (2021-01-01..2026-09-30). It shows that the loader rebuilds R300's rank view and
  reproduces R300's C17 and M319 numbers, that qx on Gate's open folders reproduces R275's gate+mexc row, and that the
  lab's and the engine's reserved guards refuse a reserved read without the frozen PREREG.
- `--rehearse --work DIR` runs the --run code end to end on archive stand-ins (2021 for 2020; R275's open Gate coins
  for the long tail) under a throwaway frozen PREREG in DIR. It reads nothing reserved.
- `--run` is the one read. It refuses unless PREREG.md is frozen, declares both tokens, every frozen input still has its
  sha256, and no result exists yet.

usage: python scripts/run_reserved_batch3.py --symbols
       python scripts/run_reserved_batch3.py --dry --work DIR
       python scripts/run_reserved_batch3.py --rehearse --work DIR
       python scripts/run_reserved_batch3.py --run
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as sps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import panel, prereg, sessions, stats  # noqa: E402
from scripts import decide_reserved_batch2 as rb2  # noqa: E402
from scripts import reserved_venue_table as rvt  # noqa: E402
from scripts.run_intrars import COST, MIN_NAMES, TOP, TURN, Grid, day_books, rows_for  # noqa: E402
from scripts.run_lotcap import series_stats  # noqa: E402

LANE = ROOT / "experiments" / "reserved_batch3"
QX = ROOT / "engine" / "target" / "release" / "qx"
H, DAY = 3_600_000, 86_400_000
RANK_WINDOW = 24 * 30
TOKENS = ("RESERVED-2020-READ", "RESERVED-GATE-READ")
CANDIDATES = ("C17", "M319", "GLT")
INTRADAY = {"C17": {"o": 0, "k": "us10", "n": 3, "seed": (300, 0, 10, 3)},
            "M319": {"o": 8, "k": 8, "n": 3, "seed": (300, 8, 8, 3)}}
GLT_LABEL = "gate+mexc L14d th5% K20"
TRIM = 0.10
N_MIN = 60                   # book days; below it a candidate is UNREADABLE and its alpha goes to the others
NW_LAG = 10
ARCHIVE = ("2021-01-01", "2026-09-30")
R300_WINDOWS = {"disc": ("2021-01-01", "2023-12-31"), "valid": ("2024-01-01", "2026-09-30")}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


# ----------------------------------------------------------------------------------------------------- universe
def load_grid(data_root, start, end, reserved):
    """R300's grid on [start 00:00, end + 1 day) UTC from data_root/klines_1h and data_root/fundingRate.

    lab.panel.check_reserved runs first: a window that starts before 2021-01-01 needs `reserved`, a frozen PREREG that
    declares RESERVED-2020-READ. Rows outside the window are filtered in the parquet read and asserted absent."""
    panel.check_reserved(start, reserved)
    root = Path(data_root)
    t0, t1 = ms(start), ms(end) + DAY
    n = (t1 - t0) // H
    syms = sorted(p.stem for p in (root / "klines_1h").glob("*.parquet"))
    win = [("t", ">=", t0), ("t", "<", t1)]
    close32 = np.full((n, len(syms)), np.nan, np.float32)
    qv32 = np.full((n, len(syms)), np.nan, np.float32)
    for j, s in enumerate(syms):                        # as lab.panel.load_panel, inside the window only
        k = pd.read_parquet(root / "klines_1h" / f"{s}.parquet", columns=["t", "close", "quote_volume"], filters=win)
        tt = k.t.to_numpy(np.int64)
        assert not len(tt) or (tt.min() >= t0 and tt.max() < t1), (s, "row outside the window")
        i = (tt - t0) // H
        close32[i, j] = k.close.to_numpy()
        qv32[i, j] = k.quote_volume.to_numpy()
    live = np.flatnonzero((~np.isnan(close32)).any(axis=0))       # as scripts/build_views.py
    syms = [syms[j] for j in live]
    rank_full = panel.liquidity_rank({"close": close32[:, live], "quote_volume": qv32[:, live]}, RANK_WINDOW)
    del close32, qv32
    cols = np.flatnonzero((rank_full <= TOP).any(axis=0))         # research.make_universe(col_top=50)
    syms = [syms[j] for j in cols]
    rank = rank_full[:, cols]
    close_t = t0 + (np.arange(n) + 1) * H
    C, G = np.full((n, len(syms)), np.nan), np.zeros((n, len(syms)))
    h = hashlib.sha256()
    for j, s in enumerate(syms):                        # as scripts/run_lotcap.Bars, with explicit bounds
        k = pd.read_parquet(root / "klines_1h" / f"{s}.parquet", columns=["t", "close", "volume"], filters=win)
        k = k.drop_duplicates("t")
        tt = k.t.to_numpy(np.int64)
        assert not len(tt) or (tt.min() >= t0 and tt.max() < t1), (s, "row outside the window")
        r = (tt - t0) // H
        close = np.full(n, np.nan)
        close[r] = k.close.to_numpy(np.float64)
        vol = np.zeros(n)
        vol[r] = k.volume.to_numpy(np.float64)
        traded = np.isfinite(close) & (vol > 0)
        C[:, j] = np.where(traded, close, np.nan)
        fp = root / "fundingRate" / f"{s}.parquet"
        f = pd.read_parquet(fp, columns=["t", "rate"], filters=win) if fp.exists() else pd.DataFrame({"t": [], "rate": []})
        assert not len(f) or (f.t.min() >= t0 and f.t.max() < t1), (s, "funding outside the window")
        f = f.sort_values("t").drop_duplicates("t")
        ft = np.rint(f.t.to_numpy(np.float64) / 60_000).astype(np.int64) * 60_000
        fcum = np.concatenate([[0.0], np.cumsum(f.rate.to_numpy(np.float64))])
        G[:, j] = fcum[np.searchsorted(ft, close_t, "right")]
        h.update(s.encode())
        for a in (C[:, j], ft, fcum):
            h.update(np.ascontiguousarray(a).tobytes())
    g = Grid(syms, C, G, rank)
    g.t0, g.digest = t0, h.hexdigest()
    return g


def us_hours(t0, nd):
    """Hours from 00:00 UTC to 10:00 New York on each day from t0 (14 in EDT, 15 in EST); 0 when the NYSE is closed."""
    noon = t0 + np.arange(nd, dtype=np.int64) * DAY + 12 * H
    trading, _ = sessions._nyse_open_day(sessions._local(noon, "America/New_York"))
    return np.where(trading, np.where(sessions.us_dst(noon) == 1, 14, 15), 0)


# -------------------------------------------------------------------------------------------------------- books
def intraday_book(g, cand):
    """One candidate's follow book on the grid (R300's day_books) plus each coin's share of each day's 1x net."""
    c = INTRADAY[cand]
    nd = g.C.shape[0] // 24
    k = us_hours(g.t0, nd) if c["k"] == "us10" else np.full(nd, c["k"])
    sp, e, x = rows_for(nd, c["o"], k)
    df = day_books(g, sp, e, x, k > 0, c["n"], seed=c["seed"])
    df["start"] = g.t0 + df.day.to_numpy(np.int64) * DAY + c["o"] * H
    idx = {s: j for j, s in enumerate(g.syms)}
    rows = []
    for d, top, bot in zip(df.day.to_numpy(), df.top, df.bot):
        ee, xx = e[d], x[d]
        for side, names in ((1.0, top), (-1.0, bot)):
            for s in names.split("|"):
                j = idx[s]
                xr = max(int(g.L[xx, j]), int(ee))
                lr = g.C[xr, j] / g.C[ee, j] - 1.0 - (g.G[xr, j] - g.G[ee, j])
                rows.append((d, s, side * lr / c["n"] - 2.0 * COST / c["n"]))
    shares = pd.DataFrame(rows, columns=["day", "coin", "net"])
    chk = shares.groupby("day").net.sum().reindex(df.day).to_numpy()
    assert np.allclose(chk, df.gross.to_numpy() - COST * TURN, rtol=0, atol=1e-10), "coin shares do not add up"
    return df, shares


def in_window(start, a, b):
    """R300's rule: the day's clock starts in [a, b] and its hold ends by the end of b."""
    start = np.asarray(start, np.int64)
    return (start >= ms(a)) & (start + DAY <= ms(b) + DAY)


def intraday_stats(df, shares, a, b):
    """Batch statistics on the days in [a, b]: Newey-West t (lag 10) over the calendar days, one-sided normal p, the
    10% trimmed mean, the mean without the two coins whose shares added most, and 1x/2x/3x means; plus R300's own
    report (scripts/run_lotcap.series_stats, lag 5) and the leg diagnostics."""
    m = in_window(df.start, a, b)
    d = df[m]
    if not len(d):
        return {"n": 0}
    net = {c: d.gross.to_numpy() - c * COST * TURN for c in (1, 2, 3)}
    x = net[1]
    grid = np.full((ms(b) - ms(a)) // DAY + 1, np.nan)
    grid[(d.start.to_numpy(np.int64) - ms(a)) // DAY] = x
    _, _, t = stats.newey_west_t(grid, NW_LAG)
    sh = shares[shares.day.isin(d.day)]
    by = sh.groupby("coin").net.sum().sort_values()
    top2 = by.index[::-1][:2].tolist()
    ts = d.start.to_numpy(np.int64)
    months = pd.to_datetime(ts, unit="ms").to_period("M").astype(str)
    out = {"n": int(len(x)), "first": str(pd.to_datetime(ts[0], unit="ms")), "last": str(pd.to_datetime(ts[-1], unit="ms")),
           "t": float(t), "p_one_sided": float(sps.norm.sf(t)) if np.isfinite(t) else float("nan"),
           **{f"mean_{c}x_bp": float(net[c].mean() * 1e4) for c in (1, 2, 3)},
           "gross_bp": float(d.gross.mean() * 1e4), "trimmed_mean_bp": float(sps.trim_mean(x, TRIM) * 1e4),
           "l2co_dropped": top2, "l2co_mean_bp": float((x.sum() - by[top2].sum()) / len(x) * 1e4),
           "price_bp": float(d.price.mean() * 1e4), "long_bp": float(d.long.mean() * 1e4),
           "short_bp": float(d.short.mean() * 1e4), "basket_bp": float(d.basket.mean() * 1e4),
           "names_median": float(d.names.median()), "names_min": int(d.names.min()),
           "breakeven_bp_side": float(d.gross.mean() * 1e4 / TURN),
           "by_month_1x_bp": {k: float(v * 1e4) for k, v in pd.Series(x).groupby(months).mean().items()},
           "halves_1x_bp": [float(h.mean() * 1e4) for h in np.array_split(x, 2)],
           "r300_report": {"gross": series_stats(d.gross.to_numpy(), ts, 24),
                           **{f"{c}x": series_stats(net[c], ts, 24) for c in (1, 2, 3)}}}
    return out


# -------------------------------------------------------------------------------------------------------- carry
def glt_symbols(data_root, repo_root):
    """The long-tail table and its overlaps, from contract lists and file names only: Gate contracts on the reserved
    route with 1 h bars and funding files, matched by base with MEXC (reserved_venue_table.mexc: hourly bars and
    funding, minus the MEXC-only reserved set)."""
    data_root, repo_root = Path(data_root), Path(repo_root)
    res = data_root / "gate_hist" / "reserved"
    have = rvt.stems(res / "candlesticks_1h") & rvt.stems(res / "funding_applies")
    gate, named = {}, 0
    with open(data_root / "gate_hist" / "contracts.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["route"] == "reserved" and r["name"] in have:
                gate[r["name"].rsplit("_", 1)[0].upper()] = r["name"]
                named += bool(r["binance_perp"])
    mx = rvt.mexc(data_root, repo_root)
    only = {s[: -len("_USDT")].upper() for s in rvt.mexc_only(repo_root) if s.endswith("_USDT")}
    rows = [{"key": b, "gate": gate[b], "mexc": mx[b]} for b in sorted(gate) if b in mx]
    other = {v: set(rvt.reserved_venue(v, data_root)) for v in rvt.RESERVED}
    overlap = {"gate_long_tail": len(gate), "rows": len(rows),
               "gate_without_mexc": len([b for b in gate if b not in mx]),
               "mexc_only_excluded": sorted(set(gate) & only),
               **{f"{v}_reserved_not_read": sorted(set(gate) & other[v]) for v in rvt.RESERVED},
               "with_binance_perp": named}
    return rows, overlap


def write_symbols(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, ["key", "gate", "mexc"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {toml_value(x)}" for k, x in v.items()) + " }"
    raise TypeError(v)


def dump_toml(d):
    return "".join(f"{k} = {toml_value(v)}\n" for k, v in d.items())


def run_qx(spec, workdir):
    """qx spread on a spec written to workdir (dry and rehearsal only; --run goes through qx_run_verified)."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    p = workdir / "spec.toml"
    p.write_text(dump_toml(spec))
    with open(workdir / "qx.log", "w") as f:
        r = subprocess.run([str(QX), "spread", str(p)], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                           env={**os.environ, "QX_DATA": str(ROOT / "data")})
    return r.returncode, (workdir / "qx.log").read_text()


def no_reserved_paths(spec):
    paths = [spec["symbols"]] + [v[k] for v in spec["venues"] for k in ("prices", "funding")]
    assert not any("reserved" in p for p in paths) and "reserved_prereg" not in spec, paths
    assert ms(spec["start"]) >= ms("2021-01-01"), spec["start"]


def dry_carry_spec(frozen, out):
    """The frozen spec with Gate's open folders and R275's symbol table on R275's window and report keys, so it must
    reproduce R275's gate+mexc L14d th5% K20 row."""
    s = dict(frozen)
    s["venues"] = [dict(v) for v in frozen["venues"]]
    for v in s["venues"]:
        for k in ("prices", "funding"):
            v[k] = v[k].replace("gate_hist/reserved/", "gate_hist/open/")
    s.pop("reserved_prereg", None)
    s["symbols"] = "experiments/xfund_v1/symbols.csv"
    s["start"], s["end"] = ARCHIVE
    s["recent_from"], s["hurdle_ann_pct"], s["seed"] = "2025-01-01", 4.13, 275
    s["out"] = str(out)
    no_reserved_paths(s)
    return s


def rehearsal_carry_spec(frozen, out, prereg_path):
    """The frozen spec on archive stand-ins: Gate's open folders and R275's table (the long-tail names have no open
    files), 2025-05-01..2025-12-31, under the throwaway PREREG."""
    s = dry_carry_spec(frozen, out)
    s["start"], s["end"], s["recent_from"], s["hurdle_ann_pct"], s["seed"] = "2025-05-01", "2025-12-31", "2025-09-01", 0.0, frozen["seed"]
    s["reserved_prereg"] = str(prereg_path)
    return s


def check_glt_parity(r):
    row = pd.read_csv(ROOT / "experiments" / "xfund_v1" / "results" / "strategies.csv").set_index("label").loc[GLT_LABEL]
    st = pd.read_csv(Path(r) / "strategies.csv").set_index("label").loc[GLT_LABEL]
    keys = ("days", "window_from", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_1x", "t_nw_1x", "trimmed_bp", "trades")
    # p_rc is not compared: it is the engine's reality check over the strategies in one spec (R275 ran its whole
    # family, this spec one book), so it is a family statistic, not the book's.
    bad = []
    for k in keys:
        a, b = st[k], row[k]
        same = a == b if isinstance(a, str) or isinstance(b, str) else np.isclose(float(a), float(b), rtol=0, atol=1e-4)
        if not same:
            bad.append((k, a, b))
    return {k: (st[k].item() if hasattr(st[k], "item") else st[k]) for k in keys}, bad


# ------------------------------------------------------------------------------------------------------ decision
def decide(res, alpha):
    """Weighted Bonferroni over the batch. Below N_MIN book days a candidate is UNREADABLE and its alpha goes to the
    readable ones in proportion. A readable candidate PASSES when its one-sided p <= its alpha, its 2x mean > 0, its
    10% trimmed 1x mean > 0 and its 1x mean without the two best coins > 0."""
    readable = [c for c in alpha if res.get(c, {}).get("n", 0) >= N_MIN and np.isfinite(res[c].get("p_one_sided", np.nan))]
    total, kept = sum(alpha.values()), sum(alpha[c] for c in readable)
    out = {}
    for c in alpha:
        r = res.get(c, {})
        if c not in readable:
            out[c] = {"verdict": "UNREADABLE", "n": int(r.get("n", 0)), "n_min": N_MIN, "alpha": 0.0}
            continue
        a = alpha[c] * total / kept
        checks = {"p_le_alpha": bool(r["p_one_sided"] <= a), "mean_2x_pos": bool(r["mean_2x_bp"] > 0),
                  "trimmed_pos": bool(r["trimmed_mean_bp"] > 0), "l2co_pos": bool(r["l2co_mean_bp"] > 0)}
        out[c] = {"verdict": "PASS" if all(checks.values()) else "FAIL", "n": int(r["n"]), "alpha": a,
                  "p_one_sided": float(r["p_one_sided"]), "t": float(r["t"]), **checks}
    return out


def alpha_from_prereg(text):
    m = re.search(r"```alpha\n(.*?)```", text, re.S)
    if not m:
        raise SystemExit("the batch PREREG has no ```alpha block")
    a = {}
    for line in m.group(1).splitlines():
        line = line.split("#")[0].strip()
        if line:
            c, v = line.split()
            a[c] = float(v)
    if tuple(a) != CANDIDATES or abs(sum(a.values()) - 0.05) > 1e-9:
        raise SystemExit(f"alpha block must list {CANDIDATES} summing to 0.05: {a}")
    return a


def inputs_ok(text):
    """Every file in the PREREG's ```inputs block still has its frozen sha256 (qx_run's format)."""
    m = re.search(r"```inputs\n(.*?)```", text, re.S)
    if not m:
        raise SystemExit("the batch PREREG has no ```inputs block")
    bad, n = [], 0
    for line in m.group(1).splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        rel, want = line.split()
        n += 1
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != want:
            bad.append(rel)
    if not n or bad:
        raise SystemExit(f"inputs changed since the freeze (or none listed): {bad}")
    return n


def check_prereg(path, tokens=TOKENS):
    sha = prereg.verify(path)
    text = Path(path).read_text()
    missing = [t for t in tokens if t not in text]
    if missing:
        raise SystemExit(f"{path} does not declare {missing}")
    return sha, text


# ------------------------------------------------------------------------------------------------------------ plans
@dataclass
class Plan:
    name: str
    prereg: Path           # the frozen PREREG the reads are checked against
    data_root: Path
    sample: tuple          # intraday sample days, inclusive
    out: Path


def read_batch(plan, carry_res, alpha):
    """The two intraday candidates on the plan's sample, the carry stats from qx's tables, then the decision."""
    res = {}
    g = load_grid(plan.data_root, plan.sample[0], plan.sample[1], str(plan.prereg))
    log(f"grid {plan.sample[0]}..{plan.sample[1]}: {len(g.syms)} columns, digest {g.digest[:12]}")
    for c in INTRADAY:
        df, shares = intraday_book(g, c)
        res[c] = intraday_stats(df, shares, *plan.sample)
        log(c, json.dumps({k: res[c].get(k) for k in ("n", "mean_1x_bp", "t", "mean_2x_bp", "trimmed_mean_bp", "l2co_mean_bp")}))
    spec = tomllib.loads((LANE / "spec.toml").read_text())
    r = rb2.stats(Path(carry_res), spec["costs"][0], spec["slots"][0], GLT_LABEL)
    r["t"] = r["t_nw_1x"]
    res["GLT"] = r
    log("GLT", json.dumps({k: r.get(k) for k in ("n", "ann_1x_pct", "t", "mean_2x_bp", "trimmed_mean_bp", "l2co_mean_bp")}))
    dec = decide(res, alpha)
    out = {"round": "R392", "plan": plan.name, "prereg_sha256": prereg.verify(plan.prereg), "alpha": alpha,
           "decision": dec, "results": res, "grid": {"columns": len(g.syms), "digest": g.digest,
                                                       "min_names": MIN_NAMES, "top": TOP}}
    plan.out.mkdir(parents=True, exist_ok=True)
    (plan.out / "batch3.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    pd.DataFrame([{"candidate": c, **v} for c, v in dec.items()]).to_csv(plan.out / "decisions.csv", index=False)
    log("decision", json.dumps({c: v["verdict"] for c, v in dec.items()}))
    return out


def manifest_preflight():
    """What scripts/qx_run_verified.py will check at --run, without opening a reserved file: MEXC's folder is hashed
    against docs/provenance/mexc_hist.json (open data); Gate's folder is compared by path, size and mtime only."""
    from scripts import qx_run_verified as qv
    out, bad = {}, []
    mp = ROOT / "docs" / "provenance" / "mexc_hist.json"
    try:
        out["mexc_hist"] = qv._manifest_snapshot(ROOT, mp, json.loads(mp.read_text()))
    except ValueError as e:
        bad.append(f"mexc_hist: {e}")
    gp = ROOT / "docs" / "provenance" / "gate_hist.json"
    rec = json.loads(gp.read_text())
    folder = ROOT / rec["folder"]
    skip = tuple(x.rstrip("/") + "/" for x in rec.get("excluded", []))
    have, newest = [], 0
    for p in folder.rglob("*"):
        rel = p.relative_to(folder).as_posix()
        if rel.startswith(skip) or not p.is_file():
            continue
        st = p.stat()
        have.append({"path": rel, "bytes": st.st_size})
        newest = max(newest, st.st_mtime_ns)
    want = [{"path": r["path"], "bytes": r["bytes"]} for r in rec["file_hashes"]]
    recorded = pd.Timestamp(rec["recorded_utc"]).value
    out["gate_hist"] = {"files": len(have), "manifest_files": len(want), "same_paths_and_sizes": sorted(have, key=lambda r: r["path"]) == want,
                        "newest_mtime_utc": str(pd.Timestamp(newest, tz="UTC")), "recorded_utc": rec["recorded_utc"],
                        "no_file_newer_than_record": newest <= recorded}
    if not (out["gate_hist"]["same_paths_and_sizes"] and out["gate_hist"]["no_file_newer_than_record"]):
        bad.append(f"gate_hist: {out['gate_hist']}")
    return out, bad


def dry(work):
    """Archive only. Returns the parity report; exits non-zero on any mismatch."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    rep, bad = {}, []
    # 1. the guards refuse a reserved read without the frozen PREREG
    try:
        panel.check_reserved("2020-01-01", None)
        bad.append("lab guard let 2020 through without a PREREG")
    except PermissionError as e:
        rep["lab_guard_no_prereg"] = str(e)
    fake = work / "guard" / "PREREG.md"
    fake.parent.mkdir(parents=True, exist_ok=True)
    if not fake.exists():
        fake.write_text("throwaway, no token\n")
        prereg.freeze(fake)
    try:
        panel.check_reserved("2020-01-01", str(fake))
        bad.append("lab guard let 2020 through without the token")
    except PermissionError as e:
        rep["lab_guard_no_token"] = str(e)
    try:
        load_grid(work / "nodata", "2020-01-01", "2020-12-31", None)
        bad.append("load_grid let 2020 through without a PREREG")
    except PermissionError as e:
        rep["load_grid_guard"] = str(e)
    frozen = tomllib.loads((LANE / "spec.toml").read_text())
    s = dict(frozen)
    s.pop("reserved_prereg")
    s["out"] = str(work / "guard" / "results")
    code, text = run_qx(s, work / "guard")
    if code == 0 or "RESERVED-GATE-READ" not in text:
        bad.append(f"engine guard did not refuse the reserved Gate folders without a PREREG: {code}")
    rep["engine_guard"] = next((ln.strip() for ln in text.splitlines() if "RESERVED-GATE-READ" in ln), "")
    # 2. the loader rebuilds R300's rank view
    g = load_grid(ROOT / "data", *ARCHIVE, None)
    meta = json.loads((ROOT / "data" / "research" / "meta.json").read_text())
    rank = np.load(ROOT / "data" / "research" / "rank.npy")
    same_cols = g.syms == meta["symbols"]
    rep["rank_view"] = {"columns": len(g.syms), "view_columns": len(meta["symbols"]), "same_columns": same_cols}
    if same_cols:
        eq = np.array_equal(np.nan_to_num(g.R, nan=-1), np.nan_to_num(rank, nan=-1))
        rep["rank_view"]["equal"] = bool(eq)
        if not eq:
            bad.append("rank differs from data/research/rank.npy")
    else:
        bad.append("columns differ from data/research/meta.json")
    rep["grid_digest"] = g.digest
    # 3. R300's numbers
    summ = json.loads((ROOT / "experiments" / "intrars_v1" / "results" / "summary.json").read_text())
    for c in INTRADAY:
        df, shares = intraday_book(g, c)
        rep[c] = {"archive": intraday_stats(df, shares, *ARCHIVE)}
        for w, (a, b) in R300_WINDOWS.items():
            rep[c][w] = intraday_stats(df, shares, a, b)
        rep[c]["archive"].pop("by_month_1x_bp")
    want = summ["strategies"]["us10 n3 follow"]
    for w in R300_WINDOWS:
        for k in ("periods", "mean_bp", "t", "mean_wo_best_bp"):
            a, b = rep["C17"][w]["r300_report"]["1x"][k], want[w]["1x"][k]
            if not np.isclose(a, b, rtol=0, atol=1e-6):
                bad.append(("C17", w, k, a, b))
    clk = summ["clocks"]["8"]
    for k, a in (("pick_valid_t", rep["M319"]["valid"]["r300_report"]["1x"]["t"]),
                 ("pick_valid_bp_day", rep["M319"]["valid"]["r300_report"]["1x"]["bp_day"])):
        if not np.isclose(a, clk[k], rtol=0, atol=1e-6):
            bad.append(("M319", k, a, clk[k]))
    del g
    # 4. R275's gate+mexc row through qx on Gate's open folders
    spec = dry_carry_spec(frozen, work / "carry" / "results")
    code, text = run_qx(spec, work / "carry")
    if code:
        bad.append(f"qx failed: {text[-500:]}")
    else:
        rep["GLT_parity"], diff = check_glt_parity(spec["out"])
        bad += [("GLT",) + d for d in diff]
        rep["GLT_archive"] = rb2.stats(Path(spec["out"]), spec["costs"][0], spec["slots"][0], GLT_LABEL)
        rep["GLT_archive"].pop("by_coin_bp_per_day", None)
    rep["manifests"], mb = manifest_preflight()
    bad += mb
    rep["mismatches"] = [list(map(str, b)) if isinstance(b, tuple) else b for b in bad]
    (work / "dry.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")
    log("dry", "OK" if not bad else f"MISMATCH {bad}")
    return rep, bad


def rehearse(work, alpha):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    fake = work / "PREREG.md"
    if not fake.exists():
        fake.write_text("throwaway rehearsal PREREG for R392: " + " ".join(TOKENS) + "\n")
        prereg.freeze(fake)
    frozen = tomllib.loads((LANE / "spec.toml").read_text())
    spec = rehearsal_carry_spec(frozen, work / "carry" / "results", fake)
    code, text = run_qx(spec, work / "carry")
    if code:
        raise SystemExit(f"rehearsal qx failed: {text[-500:]}")
    plan = Plan("rehearse", fake, ROOT / "data", ("2021-01-01", "2021-12-31"), work / "results")
    return read_batch(plan, spec["out"], alpha)


def run():
    pre = LANE / "PREREG.md"
    sha, text = check_prereg(pre)
    check_prereg(LANE / "RESERVED.md", ("RESERVED-GATE-READ",))
    n = inputs_ok(text)
    alpha = alpha_from_prereg(text)
    out = LANE / "results"
    if (out / "batch3.json").exists() or (out / "report.json").exists():
        raise SystemExit("R392 has already been read: results exist")
    log(f"R392 --run: PREREG {sha[:12]}, {n} frozen inputs verified, alpha {alpha}")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "qx_run_verified.py"), "experiments/reserved_batch3"],
                   cwd=ROOT, check=True)
    spec = tomllib.loads((LANE / "spec.toml").read_text())
    plan = Plan("run", pre, ROOT / "data", ("2020-01-01", "2020-12-31"), out)
    r = read_batch(plan, ROOT / spec["out"], alpha)
    inputs_ok(text)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    m = ap.add_mutually_exclusive_group(required=True)
    m.add_argument("--symbols", action="store_true")
    m.add_argument("--dry", action="store_true")
    m.add_argument("--rehearse", action="store_true")
    m.add_argument("--run", action="store_true")
    m.add_argument("--preflight", action="store_true")
    ap.add_argument("--work")
    ap.add_argument("--alpha", help="C17,M319,GLT alphas for --rehearse before the PREREG exists")
    a = ap.parse_args()
    if a.symbols:
        rows, overlap = glt_symbols(ROOT / "data", ROOT)
        write_symbols(rows, LANE / "symbols.csv")
        print(json.dumps(overlap))
    elif a.preflight:
        out, bad = manifest_preflight()
        print(json.dumps(out, default=str))
        return 1 if bad else 0
    elif a.dry:
        _, bad = dry(a.work)
        return 1 if bad else 0
    elif a.rehearse:
        if a.alpha:
            alpha = dict(zip(CANDIDATES, map(float, a.alpha.split(","))))
        else:
            alpha = alpha_from_prereg((LANE / "PREREG.md").read_text())
        rehearse(a.work, alpha)
    else:
        run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
