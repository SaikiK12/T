"""Reserved batch 1 (docs/GATES.md): every candidate the earlier lanes pre-committed, read once on the reserved samples
and decided together.

Each candidate is its own lane's frozen rule, unchanged; only the window differs. The runner has two modes:
- `--dry` runs the same code on the archive window each lane already read (2021-01-01..2026-09-30) and checks that it
  reproduces that lane's frozen numbers. It reads no reserved row, so it can run any time.
- `--run` reads the reserved samples. The engine and lab.panel refuse it unless experiments/reserved_batch1/PREREG.md
  is frozen and declares the samples' tokens (RESERVED-2020-READ ...). Run once, on or after 2026-11-03.

Event candidates (this file, so far):
- C09 prelist short +168 h and C10 earn_add short +168 h: R271's rule (experiments/announce_v1/spec.toml) on its
  notices labelled `reserved_2020`.
- C12: R273's top 3 by t (neg2 long +72 h, neg2 long +24 h, neg1 long +24 h; experiments/fundext_v1/spec.toml) and
  R274's bn_neg0.3 short +168 h with a 10% cover (experiments/squeeze_v1/spec.toml), on 2020 legs from
  scripts/reserved_legs.py.
- C01 unlock short: R265's rule (scripts/run_unlocks.py, its Prices.trade) on its events labelled reserved_2020
  (Binance prices from 2020, lab.panel with the reserved PREREG), reserved_mexc (MEXC-only contracts, mexc_hist,
  which needs RESERVED-MEXC-READ) and post_archive (Binance prices after 2026-09-30, data/binance_recent). One pooled
  test, week-clustered as R265; each window is reported.
- C14 carry: R275's binance+gate L14d th10% K20 book (`qx spread` on experiments/reserved_batch1/carry.toml, 2020 rows
  of Binance and Gate). Its dry twin is the same spec on the archive with Gate's open folders.
- C11 R263: its best single strategy (id 330: RSI(14) 10/90 on 1 h bars, long only) and its 6-month walk-forward
  stream (K = 20), on a 2020 universe built by R263's own rule (lab.research.make_universe(elig_top=50, col_top=50) on
  a 2020 panel; the top 20 crypto perps by trailing volume). The nets use scripts/run_brute5k.py's Bars, rules,
  variants and walk_forward unchanged; the dry mode checks them against R263's cache and its decided stream.

Each event candidate runs `qx events` on a spec that is its lane's spec with only these keys changed: events, filter,
kinds, start, end, out and (for --run) reserved_prereg. Its observations come from the engine's legs_priced.csv with
the engine's own rule (one observation per cluster: the mean net of its legs; net = sign x gross-with-funding - cost),
so the dry mode can be checked against each lane's strategies.csv.

`--rehearse` runs the `--run` code end to end on archive stand-ins for every reserved window (2021 for 2020, Binance
coins on MEXC prices for the MEXC-only coins, archive events on data/binance_recent for post_archive), under a
throwaway frozen PREREG holding every token. It reads nothing reserved; it shows the run path works before the freeze.

usage: python scripts/run_reserved_batch.py --dry [--only C09,C12a]
       python scripts/run_reserved_batch.py --rehearse [--work DIR]
       python scripts/run_reserved_batch.py --run
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data, panel, prereg  # noqa: E402
import run_brute5k as b5  # noqa: E402
import run_unlocks  # noqa: E402
from lab import flowfeat, research, stats  # noqa: E402

QX = ROOT / "engine" / "target" / "release" / "qx"
BATCH = ROOT / "experiments" / "reserved_batch1"
PREREG = BATCH / "PREREG.md"
ARCHIVE = ("2021-01-01", "2026-09-30")
TRIM = 0.10                                    # trimmed mean: 10% cut from each tail
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# Each event candidate: (id, lane, kind, direction, horizon h, cover in bp (0 = none)).
EVENTS = [
    ("C09", "announce_v1", "prelist", "short", 168, 0),
    ("C10", "announce_v1", "earn_add", "short", 168, 0),
    ("C12a", "fundext_v1", "neg2", "long", 72, 0),
    ("C12b", "fundext_v1", "neg2", "long", 24, 0),
    ("C12c", "fundext_v1", "neg1", "long", 24, 0),
    ("C12d", "squeeze_v1", "bn_neg0.3", "short", 168, 1000),
]
# The 2020 legs of R273/R274 come from scripts/reserved_legs.py (its output file per lane); R271's notices are already
# labelled by window in its legs.csv.
RESERVED_LEGS = {"fundext_v1": "fundext_legs.csv", "squeeze_v1": "squeeze_legs.csv"}
MEXC_TOKEN = "RESERVED-MEXC-READ"              # MEXC-only contracts (docs/GATES.md); mexc_hist has no reserved/ folder


@dataclass(frozen=True)
class Plan:
    """Where the read happens: `run` is the batch; `rehearse` swaps every reserved window for an archive one."""
    name: str
    prereg: Path
    out: Path
    events: tuple          # qx start, end and the window label of R271's notices
    legs: tuple            # scripts/reserved_legs.py start, end and window label
    brute: tuple           # the panel R263's universe is built from: start, end


def run_plan():
    return Plan("run", PREREG, BATCH / "results", ("2020-01-01", "2021-01-08", "reserved_2020"),
                ("2020-01-01", "2021-01-01", "reserved_2020"), ("2020-01-01", "2020-12-31"))


def rehearsal_plan(work):
    return Plan("rehearse", Path(work) / "PREREG.md", Path(work) / "results", ("2021-01-01", "2022-01-08", "archive"),
                ("2021-01-01", "2022-01-01", "rehearsal"), ("2021-01-01", "2021-12-31"))


def toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {toml_value(x)}" for k, x in v.items()) + " }"
    if isinstance(v, list):
        if v and all(isinstance(x, dict) for x in v):
            return "[\n" + "".join(f"  {toml_value(x)},\n" for x in v) + "]"
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    raise TypeError(type(v))


def dump_toml(d):
    return "".join(f"{k} = {toml_value(v)}\n" for k, v in d.items())


def lane_spec(lane):
    return tomllib.loads((ROOT / "experiments" / lane / "spec.toml").read_text())


def event_spec(lane, kinds, plan, out, legs_dir=None):
    """The lane's spec with only the window keys changed (plan None = the dry run on the archive)."""
    s = lane_spec(lane)
    s["kinds"] = sorted(kinds)
    s["out"] = str(out)
    if plan is None:
        s["start"], s["end"] = ARCHIVE
        s["filter"] = {"window": "archive"}
    else:
        s["start"], s["end"], window = plan.events
        s["filter"] = {"window": window}
        s["reserved_prereg"] = str(plan.prereg)
        if lane in RESERVED_LEGS:
            s["events"] = str(Path(legs_dir) / RESERVED_LEGS[lane])
            s["filter"] = {"window": plan.legs[2]}
    return s


def run_qx(kind, spec, workdir):
    p = Path(workdir) / "spec.toml"
    p.write_text(dump_toml(spec))
    with open(Path(workdir) / "qx.log", "w") as f:
        subprocess.run([str(QX), kind, str(p)], cwd=ROOT, check=True, stdout=f, stderr=subprocess.STDOUT,
                       env={**os.environ, "QX_DATA": str(ROOT / "data")})


def leg_column(dirn, h, stop_bp):
    """legs_priced.csv column holding the leg's gross + funding in the short's sign (the engine's leg_sg)."""
    return f"sg_{h}" if stop_bp == 0 else f"{dirn}_{h}_stop{stop_bp}"


def event_obs(legs, kind, dirn, h, stop_bp, cost, drop_tickers=()):
    """One observation per cluster (the engine's obs_with): clusters are (kind, r0); a leg's net is
    sign x leg_sg - cost; legs with a non-finite net are left out. Returns a frame in t0 order: r0, t0, net, legs."""
    sign = 1.0 if dirn == "short" else -1.0
    x = legs[(legs.kind == kind) & ~legs.ticker.isin(drop_tickers)]
    net = sign * pd.to_numeric(x[leg_column(dirn, h, stop_bp)], errors="coerce") - cost
    x = x.assign(net=net)[np.isfinite(net)]
    g = x.groupby("r0").agg(t0=("t0", "min"), net=("net", "mean"), legs=("net", "size")).reset_index()
    return g.sort_values("t0", kind="stable").reset_index(drop=True)


def tstat(x):
    x = np.asarray(x, float)
    if len(x) < 2 or not np.std(x, ddof=1) > 0:
        return np.nan
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def event_stats(legs, kind, dirn, h, stop_bp, costs):
    """The batch statistics of one event candidate at 1x/2x/3x of its lane's costs."""
    o1 = event_obs(legs, kind, dirn, h, stop_bp, costs[0])
    out = {"n": int(len(o1)), "legs": int(o1.legs.sum()) if len(o1) else 0}
    if len(o1) < 2:
        return out
    x = o1.net.values
    t = tstat(x)
    out.update({"mean_1x_pct": float(x.mean() * 100), "t": t, "p_one_sided": float(sps.t.sf(t, len(x) - 1)),
                "median_pct": float(np.median(x) * 100), "hit": float((x > 0).mean()),
                "trimmed_mean_pct": float(sps.trim_mean(x, TRIM) * 100)})
    for m, c in zip((2, 3), costs[1:]):
        out[f"mean_{m}x_pct"] = float(event_obs(legs, kind, dirn, h, stop_bp, c).net.mean() * 100)
    # leave two coins out: drop the two tickers with the largest summed leg net at 1x
    sign = 1.0 if dirn == "short" else -1.0
    k = legs[legs.kind == kind]
    lnet = sign * pd.to_numeric(k[leg_column(dirn, h, stop_bp)], errors="coerce") - costs[0]
    top = lnet.groupby(k.ticker).sum().sort_values(ascending=False).index[:2].tolist()
    out["l2co_dropped"] = top
    out["l2co_mean_pct"] = float(event_obs(legs, kind, dirn, h, stop_bp, costs[0], top).net.mean() * 100)
    return out


def run_events(plan, work, only=None, legs_dir=None):
    """Price every event candidate's lane once (qx), then compute each candidate's statistics. A lane the engine
    cannot price (no event with a market) gives its candidates n = 0, so the batch reads them as UNREADABLE."""
    res = {}
    by_lane = {}
    for c in EVENTS:
        if only and c[0] not in only:
            continue
        by_lane.setdefault(c[1], []).append(c)
    for lane, cands in by_lane.items():
        wd = Path(work) / lane
        wd.mkdir(parents=True, exist_ok=True)
        spec = event_spec(lane, {c[2] for c in cands}, plan, wd / "results", legs_dir)
        log(f"{lane}: qx events on {spec['filter']} {spec['start']}..{spec['end']}, kinds {spec['kinds']}")
        try:
            run_qx("events", spec, wd)
            legs = pd.read_csv(wd / "results" / "legs_priced.csv")
        except (subprocess.CalledProcessError, FileNotFoundError, pd.errors.EmptyDataError) as e:
            if plan is None:
                raise
            log(f"{lane}: no priced legs ({type(e).__name__}; see {wd / 'qx.log'})")
            legs = pd.DataFrame(columns=["kind", "ticker", "r0", "t0", "sg_1"])
        for cid, _, kind, dirn, h, stop in cands:
            res[cid] = {"lane": lane, "strategy": label(kind, dirn, h, stop), **event_stats(legs, kind, dirn, h, stop,
                                                                                          spec["costs"])}
            log(cid, json.dumps({k: v for k, v in res[cid].items() if k in ("strategy", "n", "mean_1x_pct", "t")}))
    return res


def label(kind, dirn, h, stop_bp):
    return f"{kind} {dirn} {h}h" + (f" stop{stop_bp // 100}%" if stop_bp else "")


def mexc_panel(contracts, start, end, reserved):
    """A lab.panel.Panel of MEXC hourly bars (mexc_hist) for the unlock pricing: close, volume (contracts),
    quote_volume (amount) and fund_event (the rate on the bar where it settles). MEXC-only contracts are a reserved
    sample, so this needs the frozen batch PREREG declaring MEXC_TOKEN."""
    prereg.verify(reserved)
    if MEXC_TOKEN not in Path(reserved).read_text():
        raise PermissionError(f"{reserved} does not declare {MEXC_TOKEN}")
    t0 = panel.ms(start)
    t = np.arange(t0, panel.ms(end) + 24 * panel.HOUR, panel.HOUR)
    f = {k: np.full((len(t), len(contracts)), np.nan, np.float32) for k in panel.FIELDS + ("fund_event",)}
    for j, c in enumerate(contracts):
        k = pd.read_parquet(data.ROOT / "mexc_hist" / "klines_1h" / f"{c}.parquet")
        i = (k.t.values - t0) // panel.HOUR
        ok = (i >= 0) & (i < len(t))
        for dst, src in (("open", "open"), ("high", "high"), ("low", "low"), ("close", "close"), ("volume", "vol"),
                         ("quote_volume", "amount")):
            f[dst][i[ok], j] = k[src].values[ok]
        fp = data.ROOT / "mexc_hist" / "funding" / f"{c}.parquet"
        if fp.exists():
            r = pd.read_parquet(fp)
            i = (r.t.values - t0) // panel.HOUR
            ok = (i >= 0) & (i < len(t))
            f["fund_event"][i[ok], j] = r.rate.values[ok]
    return panel.Panel(t, list(contracts), f)


def unlock_sets(ev, plan):
    """(label, events, price source) per unlock window. A label is the reserved window the events stand for."""
    ev = ev[ev.check.isin(["verified", "unverified", "mexc_only"])]
    if plan is None:
        return [("archive", ev[(ev.window == "archive") & (ev.venue == "binance")].copy(), "binance")]
    if plan.name == "run":
        b = ev.venue == "binance"
        return [("reserved_2020", ev[(ev.window == "reserved_2020") & b].copy(), "binance_2020"),
                ("reserved_mexc", ev[ev.window == "reserved_mexc"].copy(), "mexc"),
                ("post_archive", ev[(ev.window == "post_archive") & b].copy(), "recent")]
    # rehearsal: archive events the lane already read, on the same three price paths
    a = ev[(ev.window == "archive") & (ev.venue == "binance")]
    y21 = a[a.day < "2022-01-01"].copy()
    mx = a[a.day >= "2025-05-01"].copy()
    mx["perp"] = mx.perp.str.replace(r"USDT$", "_USDT", regex=True)
    mx = mx[[(data.ROOT / "mexc_hist" / "klines_1h" / f"{c}.parquet").exists() for c in mx.perp]]
    rc = a[(a.day >= "2026-01-01") & a.perp.isin([q.stem for q in (data.ROOT / "binance_recent" / "klines_1h").glob("*.parquet")])].copy()
    return [("reserved_2020", y21, "binance_2020"), ("reserved_mexc", mx, "mexc"), ("post_archive", rc, "recent")]


def unlock_prices(source, perps, e, plan):
    """The price panel one unlock window is read from."""
    if source == "binance":
        return panel.load_panel(perps)
    if source == "binance_2020":
        start = "2020-01-01" if plan.name == "run" else "2021-01-01"
        return panel.load_panel(perps, start=start, reserved=str(plan.prereg))
    if source == "recent":
        root = data.ROOT / "binance_recent" / "klines_1h"
        last = [pd.read_parquet(root / f"{s}.parquet", columns=["t"]).t.max() for s in perps]
        if min(last) < int(e.day_ms.max()) + 23 * panel.HOUR:     # every perp must reach the last exit bar
            raise SystemExit("data/binance_recent ends before the last post_archive exit: run "
                             "scripts/fetch_binance_recent.py --unlock-post-archive --end <today> first")
        end = pd.Timestamp(int(max(last)), unit="ms").strftime("%Y-%m-%d")
        start = (pd.Timestamp(int(e.day_ms.min()), unit="ms") - pd.Timedelta(days=40)).strftime("%Y-%m-%d")
        return panel.load_panel(perps, root=root.parent, start=start, end=end)
    if source == "mexc":
        return mexc_panel(perps, "2025-04-01", time.strftime("%Y-%m-%d", time.gmtime()), str(plan.prereg))
    raise ValueError(source)


def unlock_window(label, e, source, plan):
    """R265's trade on one window's events: short the close of D-7, cover at the close of D (last traded closes)."""
    e = e.assign(window=label)
    if e.empty:
        return e.assign(gross=pd.Series(dtype=float))
    perps = sorted(set(e.perp))
    p = unlock_prices(source, perps, e, plan)
    px = run_unlocks.Prices(p)
    col = {s: i for i, s in enumerate(p.symbols)}
    D = px.row_close_of_day(e.day_ms.values)
    e["gross"] = [float(px.trade(col[s], d - 7 * run_unlocks.DAYH, d)[0]) for s, d in zip(e.perp, D)]
    return e


def unlock_stats(priced):
    """C01's batch statistics: R265's net (gross minus its round-trip cost) per event, week-clustered."""
    priced = priced[np.isfinite(priced.gross)].sort_values(["day_ms", "perp"]).reset_index(drop=True)
    out = {"n": int(len(priced)), "by_window": priced.window.value_counts().to_dict()}
    if len(priced) < 2:
        return out
    wk = pd.to_datetime(priced.day_ms, unit="ms", utc=True).dt.isocalendar()
    week = (wk.year * 100 + wk.week).values
    x = (priced.gross - run_unlocks.COST[1]).values
    t = run_unlocks.cluster_t(x, week)
    G = len(set(week))
    out.update({"mean_1x_pct": float(x.mean() * 100), "t": float(t), "clusters": G,
                "p_one_sided": float(sps.t.sf(t, G - 1)) if G > 1 else np.nan,
                "median_pct": float(np.median(x) * 100), "hit": float((x > 0).mean()),
                "trimmed_mean_pct": float(sps.trim_mean(x, TRIM) * 100)})
    for m in (2, 3):
        out[f"mean_{m}x_pct"] = float((priced.gross - run_unlocks.COST[m]).mean() * 100)
        out[f"t_{m}x"] = float(run_unlocks.cluster_t((priced.gross - run_unlocks.COST[m]).values, week))
    top = pd.Series(x, index=priced.perp).groupby(level=0).sum().sort_values(ascending=False).index[:2].tolist()
    out["l2co_dropped"] = top
    out["l2co_mean_pct"] = float(x[~priced.perp.isin(top).values].mean() * 100)
    out["windows"] = {w: {"n": int(len(g)), "mean_1x_pct": float((g.gross - run_unlocks.COST[1]).mean() * 100)}
                      for w, g in priced.groupby("window")}
    return out


def run_unlock(plan):
    ev = pd.read_csv(ROOT / "experiments" / "unlocks_v1" / "events.csv")
    priced = pd.concat([unlock_window(label, e, src, plan) for label, e, src in unlock_sets(ev, plan)],
                       ignore_index=True)
    res = {"lane": "unlocks_v1", "strategy": "unlock short D-7 to D", **unlock_stats(priced)}
    log("C01", json.dumps({k: res.get(k) for k in ("n", "mean_1x_pct", "t", "by_window")}))
    return res


def check_unlock_parity(r):
    """Dry mode: C01 on the archive must equal R265's frozen primary (n, mean and week-cluster t at 1x/2x/3x)."""
    v = json.loads((ROOT / "experiments" / "unlocks_v1" / "results" / "verdict.json").read_text())["primary"]
    pairs = [(r["n"], v["1x"]["n"]), (r["mean_1x_pct"], v["1x"]["mean_pct"]), (r["t"], v["1x"]["week_cluster_t"]),
             (r["mean_2x_pct"], v["2x"]["mean_pct"]), (r["t_2x"], v["2x"]["week_cluster_t"]),
             (r["mean_3x_pct"], v["3x"]["mean_pct"]), (r["t_3x"], v["3x"]["week_cluster_t"])]
    return [("C01", a, b) for a, b in pairs if not np.isclose(a, b, rtol=1e-9, atol=1e-12)]


CARRY_LABEL = "binance+gate L14d th10% K20"


def carry_spec(plan, out):
    """--run reads carry.toml as frozen. The dry twin changes only the window, Gate's folders (open, not reserved),
    the reserved PREREG, the output and R275's two report-only keys, so it must reproduce R275's row. The rehearsal
    twin is the frozen spec on 2021 with Gate's open folders."""
    s = tomllib.loads((BATCH / "carry.toml").read_text())
    if plan is None or plan.name == "rehearse":
        for v in s["venues"]:
            for k in ("prices", "funding"):
                v[k] = v[k].replace("gate_hist/reserved/", "gate_hist/open/")
    if plan is None:
        s["start"], s["end"] = ARCHIVE
        s.pop("reserved_prereg")
        s["recent_from"], s["hurdle_ann_pct"] = "2025-01-01", 4.13
    elif plan.name == "rehearse":
        s["start"], s["end"] = plan.brute
        s["recent_from"] = "2021-07-01"
        s["reserved_prereg"] = str(plan.prereg)
    s["out"] = str(out)
    return s


def carry_stats(res_dir, costs, slots):
    """C14's batch statistics from qx spread's tables: daily net at 1x/2x/3x, Newey-West t (lag 10), the 10% trimmed
    daily mean, and the mean without the two coins whose trades added most (their trade pnl minus the 4 legs' cost,
    over 2K, is exactly their share of the daily sum)."""
    st = pd.read_csv(Path(res_dir) / "strategies.csv").set_index("label").loc[CARRY_LABEL]
    d = pd.read_csv(Path(res_dir) / "daily.csv")
    d = d[d.strategy == CARRY_LABEL]
    x = d[d.cost_multiple == 1].net.values
    out = {"n": int(len(x)), "days": int(st.days), "ann_1x_pct": float(st.ann_1x_pct), "ann_2x_pct": float(st.ann_2x_pct),
           "ann_3x_pct": float(st.ann_3x_pct), "t_1x": float(st.t_1x), "t": float(st.t_nw_1x)}
    if len(x) < 3:
        return out
    out.update({"mean_1x_bp": float(x.mean() * 1e4), "p_one_sided": float(sps.norm.sf(st.t_nw_1x)),
                "trimmed_mean_bp": float(sps.trim_mean(x, TRIM) * 1e4), "engine_trimmed_bp": float(st.trimmed_bp)})
    for m in (2, 3):
        out[f"mean_{m}x_bp"] = float(d[d.cost_multiple == m].net.mean() * 1e4)
    tr = pd.read_csv(Path(res_dir) / "trades.csv")
    tr = tr[tr.strategy == CARRY_LABEL]
    by = ((tr.price_pnl + tr.funding_pnl - 4 * costs[0]) / (2 * slots)).groupby(tr.coin).sum().sort_values()
    top = by.index[::-1][:2].tolist()
    out["l2co_dropped"] = top
    out["l2co_mean_bp"] = float((x.sum() - by[top].sum()) / len(x) * 1e4)
    return out


def run_carry(plan, work):
    wd = Path(work) / "carry"
    wd.mkdir(parents=True, exist_ok=True)
    spec = carry_spec(plan, wd / "results")
    log(f"C14: qx spread {spec['start']}..{spec['end']}")
    if plan is None or plan.name == "rehearse":
        run_qx("spread", spec, wd)
    else:
        with open(wd / "qx.log", "w") as f:                       # the frozen file itself, not a copy
            subprocess.run([str(QX), "spread", str(BATCH / "carry.toml")], cwd=ROOT, check=True, stdout=f,
                           stderr=subprocess.STDOUT, env={**os.environ, "QX_DATA": str(ROOT / "data")})
        spec["out"] = str(ROOT / tomllib.loads((BATCH / "carry.toml").read_text())["out"])
    r = {"lane": "xfund_v1", "strategy": CARRY_LABEL, **carry_stats(spec["out"], spec["costs"], spec["slots"][0])}
    log("C14", json.dumps({k: r.get(k) for k in ("days", "ann_1x_pct", "t", "l2co_mean_bp")}))
    return r


def check_carry_parity(r):
    """Dry mode: C14 on the archive must equal R275's frozen row."""
    row = pd.read_csv(ROOT / "experiments" / "xfund_v1" / "results" / "strategies.csv").set_index("label").loc[CARRY_LABEL]
    pairs = [(r["days"], row.days), (r["ann_1x_pct"], row.ann_1x_pct), (r["ann_2x_pct"], row.ann_2x_pct),
             (r["ann_3x_pct"], row.ann_3x_pct), (r["t_1x"], row.t_1x), (r["t"], row.t_nw_1x),
             (r["engine_trimmed_bp"], row.trimmed_bp)]
    return [("C14", a, b) for a, b in pairs if not np.isclose(a, b, rtol=0, atol=1e-4)]


BRUTE_BEST = 330                               # R263's best single strategy (experiments/brute5k_v1/FINDINGS.md)
BRUTE_RULES = len(b5.base_rules())
VARIANTS = len(b5.DIRS) * len(b5.FILTERS) * len(b5.STOPS)


def brute_inputs(u):
    """R263's members and per-coin arrays from a universe (scripts/run_brute5k.py compute(), unchanged)."""
    T = len(u.p.t)
    syms = list(u.p.symbols)
    tf = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
    crypto = np.array([s not in tf for s in syms])
    rank, elig = np.asarray(u.rank), np.asarray(u.elig)
    day0 = (rank[::24] <= b5.TOP) & elig[::24] & crypto[None, :]
    member = np.repeat(day0, 24, axis=0)[:T] & elig
    cols = np.flatnonzero(member.any(axis=0))
    kl = flowfeat.load("klines", u.p.t, u.p.symbols, ("open", "high", "low", "quote_volume"))
    o, h, l, v = (np.asarray(kl[x], np.float64)[:, cols] for x in ("open", "high", "low", "quote_volume"))
    c = np.asarray(u.p["close"], np.float64)[:, cols]
    D = T // 24
    return {"T": T, "D": D, "cols": cols, "syms": [syms[j] for j in cols], "w": member[:, cols] / b5.TOP,
            "r0": np.nan_to_num(np.asarray(u.ret, np.float64)[:, cols]), "cm0": np.asarray(u.cmat, np.float64)[:, cols],
            "o": o, "h": h, "l": l, "c": c, "v": v,
            "ema200": pd.DataFrame(c[23::24][:D]).ewm(span=200, adjust=False, min_periods=200).mean().values,
            "days": np.asarray(u.p.t[0:D * 24:24])}


def brute_nets(x, ids=None, per_coin=()):
    """Daily gross, cost and month-end exposure of R263's strategies (all of them, or `ids`), in R263's id order:
    id = timeframe x 1368 + base rule x 18 + variant. For ids in `per_coin`, also the daily net per coin at 1x."""
    T, D = x["T"], x["D"]
    wr = x["w"] * x["r0"]
    dt = pd.to_datetime(x["days"], unit="ms", utc=True).to_period("M")
    first = np.r_[True, dt[1:] != dt[:-1]]
    rows_month_end = np.flatnonzero(first)[1:] * 24 - 1
    want = None if ids is None else set(ids)
    out, coin = {}, {}
    for ti, k in enumerate(b5.TFS):
        lo = ti * BRUTE_RULES * VARIANTS
        if want is not None and not any(lo <= i < lo + BRUTE_RULES * VARIANTS for i in want):
            continue
        B = b5.Bars(x["o"], x["h"], x["l"], x["c"], x["v"], k, x["ema200"])
        jidx = (np.arange(T) + 1) // k - 1
        valid = jidx >= 0
        jidx = np.maximum(jidx, 0)
        for ri, (fam, prm) in enumerate(b5.base_rules()):
            r_lo = lo + ri * VARIANTS
            if want is not None and not any(r_lo <= i < r_lo + VARIANTS for i in want):
                continue
            base = B.rule(fam, prm)
            for vi, (_, pos) in enumerate(B.variants(base)):
                i = r_lo + vi
                if want is not None and i not in want:
                    continue
                ph = pos[jidx].astype(np.float64)
                ph[~valid] = 0
                P = ph * x["w"]
                g = ph * wr
                adp = np.abs(np.diff(P, axis=0, prepend=0))
                if ((adp > 0) & ~np.isfinite(x["cm0"])).any():
                    raise ValueError(f"traded cell without a tier cost: strategy {i}")
                gross, cost = g.sum(axis=1), (adp * x["cm0"]).sum(axis=1)       # as R263, NaN cells included
                cst = np.where(adp > 0, adp * x["cm0"], 0.0)
                out[i] = (gross[:D * 24].reshape(D, 24).sum(1).astype(np.float32),
                          cost[:D * 24].reshape(D, 24).sum(1).astype(np.float32),
                          np.abs(P[rows_month_end]).sum(axis=1).astype(np.float32))
                if i in per_coin:
                    coin[i] = (g - cst)[:D * 24].reshape(D, 24, -1).sum(1)
    return out, coin


def brute_universe(plan):
    if plan is None:
        u, _, _ = research.load_universe()
        return u
    p = panel.load_panel(start=plan.brute[0], end=plan.brute[1], reserved=str(plan.prereg))
    live = ~np.isnan(p["close"])
    p = p.columns(np.flatnonzero(live.any(axis=0)))       # as scripts/build_views.py
    return research.make_universe(p, elig_top=50, col_top=50)


def daily_stats(x, coin_net, syms, lag=10):
    """Batch statistics of a daily net stream (1x): NW t, trimmed mean and the mean without the two best coins."""
    t = float(stats.newey_west_t(x, lag)[2])
    tot = coin_net.sum(axis=0)
    top = np.argsort(-tot)[:2]
    return {"n": int(len(x)), "mean_1x_bp": float(x.mean() * 1e4), "t": t, "p_one_sided": float(sps.norm.sf(t)),
            "trimmed_mean_bp": float(sps.trim_mean(x, TRIM) * 1e4), "l2co_dropped": [syms[j] for j in top],
            "l2co_mean_bp": float((x.sum() - tot[top].sum()) / len(x) * 1e4)}


def run_brute(plan):
    """C11a (strategy 330) and C11b (the 6-month walk-forward stream) on 2020; in dry mode, on the archive."""
    u = brute_universe(plan)
    x = brute_inputs(u)
    res = {}
    if plan is None:
        z = np.load(ROOT / "experiments" / "brute5k_v1" / "cache" / "nets.npz")
        gross, cost, expo = z["gross"].astype(np.float64), z["cost"].astype(np.float64), z["expo"]
        nets, coin = brute_nets(x, ids=(0, BRUTE_BEST, 2000, 4000, 5471), per_coin=(BRUTE_BEST,))
        res["cache_parity"] = {i: max(diff(nets[i][j], z[k][i]) for j, k in enumerate(("gross", "cost", "expo")))
                               for i in nets}
    else:
        nets, _ = brute_nets(x)
        gross = np.array([nets[i][0] for i in range(len(nets))], np.float64)
        cost = np.array([nets[i][1] for i in range(len(nets))], np.float64)
        expo = np.array([nets[i][2] for i in range(len(nets))])
    D = gross.shape[1]
    days = x["days"][:D]
    net = {cm: gross - cm * cost for cm in (1.0, 2.0, 3.0)}
    dt = pd.to_datetime(days, unit="ms", utc=True)
    per = dt.to_period("M")
    months = per.unique()
    mon_id = np.searchsorted(months.to_timestamp().values, per.to_timestamp().values)
    # C11b: the stream R263 decided on (L = 6 months), selecting on 1x and earning each cost multiple
    streams, picks = {}, None
    for cm in (1.0, 2.0, 3.0):
        on, streams[cm], pk = b5.walk_forward(net[1.0], net[cm], expo, mon_id, months, b5.MAIN_L, cm)
        picks = picks or pk
    if plan is None:
        dec = (dt >= pd.Timestamp(b5.DECIDE[0], tz="UTC")) & (dt < pd.Timestamp(b5.DECIDE[1], tz="UTC")) & on
        s1 = streams[1.0][dec]
        res["C11b"] = {"n": int(dec.sum()), "mean_1x_bp": float(s1.mean() * 1e4),
                       "t": float(stats.newey_west_t(s1, 10)[2]), "mean_2x_bp": float(streams[2.0][dec].mean() * 1e4)}
        res["C11a"] = {"n": int(D), "mean_1x_bp": float(net[1.0][BRUTE_BEST].mean() * 1e4)}
        return res
    sel = sorted({i for v in picks.values() for i in v})
    _, coin = brute_nets(x, ids=sel + [BRUTE_BEST], per_coin=set(sel) | {BRUTE_BEST})
    # C11a: every 2020 day
    a = net[1.0][BRUTE_BEST]
    res["C11a"] = {"lane": "brute5k_v1", "strategy": "id 330 RSI(14) 10/90 1h long", **daily_stats(a, coin[BRUTE_BEST], x["syms"]),
                   "mean_2x_bp": float(net[2.0][BRUTE_BEST].mean() * 1e4),
                   "mean_3x_bp": float(net[3.0][BRUTE_BEST].mean() * 1e4)}
    # C11b: the stream's days (months L.. of 2020); per-coin shares of the picked strategies, switch costs unassigned
    cn = np.zeros((D, len(x["syms"])))
    for m, ids in picks.items():
        dm = per == pd.Period(m)
        for i in ids:
            cn[dm] += coin[i][dm] / b5.K_SEL
    s1 = streams[1.0][on]
    res["C11b"] = {"lane": "brute5k_v1", "strategy": "walk-forward L6 K20", **daily_stats(s1, cn[on], x["syms"]),
                   "mean_2x_bp": float(streams[2.0][on].mean() * 1e4), "mean_3x_bp": float(streams[3.0][on].mean() * 1e4)}
    return res


def diff(a, b):
    """Largest absolute difference; a NaN on one side only counts as infinite."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape or (np.isnan(a) != np.isnan(b)).any():
        return float("inf")
    d = np.abs(a - b)[~np.isnan(a)]
    return float(d.max()) if d.size else 0.0


def check_brute_parity(r):
    """Dry mode: strategy nets equal R263's cache, and the decided stream equals R263's primary."""
    v = json.loads((ROOT / "experiments" / "brute5k_v1" / "results" / "verdict.json").read_text())["primary"]
    bad = [("C11 cache", i, d) for i, d in r["cache_parity"].items() if d > 1e-6]
    for a, b in ((r["C11b"]["mean_1x_bp"], v["mean_1x_bp"]), (r["C11b"]["t"], v["t_1x"]),
                 (r["C11b"]["mean_2x_bp"], v["mean_2x_bp"])):
        if not np.isclose(a, b, rtol=1e-6, atol=1e-9):
            bad.append(("C11b", a, b))
    return bad


def check_parity(res):
    """Dry mode: each event candidate must reproduce its lane's frozen strategies.csv row (n, mean at 1x/2x/3x, t)."""
    bad = []
    for cid, r in res.items():
        lane = r["lane"]
        f = pd.read_csv(ROOT / "experiments" / lane / "results" / "strategies.csv")
        row = f[f.label == r["strategy"]]
        if len(row) != 1:
            bad.append((cid, "no frozen row"))
            continue
        row = row.iloc[0]
        for ours, theirs in (("n", "n"), ("mean_1x_pct", "mean_1x_pct"), ("mean_2x_pct", "mean_2x_pct"),
                             ("mean_3x_pct", "mean_3x_pct"), ("t", "t")):
            if not np.isclose(r[ours], row[theirs], rtol=1e-7, atol=1e-9):
                bad.append((cid, ours, r[ours], row[theirs]))
    return bad


# ---------------------------------------------------------------- the batch decision (fixed in the batch PREREG)
RUN_FROM = "2026-11-03"
CANDIDATES = ("C14", "C01", "C09", "C10", "C11a", "C11b", "C12a", "C12b", "C12c", "C12d")
DAILY = ("C14", "C11a", "C11b")                 # daily streams; the rest are events (one observation per cluster)
N_MIN = {"daily": 60, "event": 8}
TOKENS = ("RESERVED-2020-READ", "RESERVED-GATE-READ", MEXC_TOKEN)


def pick(r, stem):
    """A candidate's statistic in whichever unit its lane reports (percent per event or bp per day)."""
    for unit in ("pct", "bp"):
        if f"{stem}_{unit}" in r:
            return r[f"{stem}_{unit}"]
    return np.nan


def decide(res, alpha):
    """Weighted Bonferroni over the batch. A candidate with fewer than N_MIN observations is UNREADABLE and its alpha
    goes to the readable ones in proportion to theirs. A readable candidate PASSES when its one-sided p <= its alpha
    and, at 1x, its 10% trimmed mean and its mean without the two best coins are > 0, and its 2x mean is > 0."""
    n_min = {c: N_MIN["daily" if c in DAILY else "event"] for c in alpha}
    readable = [c for c in alpha if res.get(c, {}).get("n", 0) >= n_min[c] and np.isfinite(res[c].get("p_one_sided", np.nan))]
    total = sum(alpha.values())
    kept = sum(alpha[c] for c in readable)
    out = {}
    for c in alpha:
        r = res.get(c, {})
        if c not in readable:
            out[c] = {"verdict": "UNREADABLE", "n": int(r.get("n", 0)), "n_min": n_min[c], "alpha": 0.0}
            continue
        a = alpha[c] * total / kept
        checks = {"p_le_alpha": bool(r["p_one_sided"] <= a), "mean_2x_pos": bool(pick(r, "mean_2x") > 0),
                  "trimmed_pos": bool(pick(r, "trimmed_mean") > 0), "l2co_pos": bool(pick(r, "l2co_mean") > 0)}
        out[c] = {"verdict": "PASS" if all(checks.values()) else "FAIL", "n": int(r["n"]), "alpha": a,
                  "p_one_sided": float(r["p_one_sided"]), "t": float(r["t"]), **checks}
    return out


def inputs_ok(text):
    """Every file in the PREREG's ```inputs block still has its frozen sha256."""
    import hashlib
    import re
    m = re.search(r"```inputs\n(.*?)```", text, re.S)
    if not m:
        raise SystemExit("the batch PREREG has no ```inputs block")
    lines = [x.split("#")[0].strip() for x in m.group(1).splitlines()]
    lines = [x for x in lines if x]
    if not lines:
        raise SystemExit("the batch PREREG's inputs block is empty")
    bad = []
    for line in lines:
        path, want = line.split()
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != want:
            bad.append(path)
    if bad:
        raise SystemExit(f"inputs changed since the freeze: {bad}")


def alpha_from_prereg(text):
    """The alpha column of the PREREG's ```alpha block: one `Cxx <alpha>` per line."""
    import re
    m = re.search(r"```alpha\n(.*?)```", text, re.S)
    a = {}
    for line in m.group(1).splitlines():
        line = line.split("#")[0].strip()
        if line:
            c, v = line.split()
            a[c] = float(v)
    assert tuple(a) == CANDIDATES and abs(sum(a.values()) - 0.05) < 1e-9, a
    return a


ALPHA = {"C14": 0.0273, "C01": 0.0147, "C09": 0.001, "C10": 0.001, "C11a": 0.001, "C11b": 0.001, "C12a": 0.001,
         "C12b": 0.001, "C12c": 0.001, "C12d": 0.001}


def alpha_block():
    return "```alpha\n" + "".join(f"{c} {a}\n" for c, a in ALPHA.items()) + "```\n"


def read_batch(plan, work):
    """Every candidate on the plan's windows, then the decision. Shared by --run and --rehearse."""
    legs = Path(work) / "legs"
    cmd = [sys.executable, str(ROOT / "scripts" / "reserved_legs.py"), "--out", str(legs), "--start", plan.legs[0],
           "--end", plan.legs[1], "--window", plan.legs[2], "--prereg", str(plan.prereg)]
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    res = run_events(plan, work, legs_dir=legs)
    res["C01"] = run_unlock(plan)
    res["C14"] = run_carry(plan, work)
    res.update(run_brute(plan))
    dec = decide(res, alpha_from_prereg(plan.prereg.read_text()))
    plan.out.mkdir(parents=True, exist_ok=True)
    (plan.out / "batch.json").write_text(json.dumps({"plan": plan.name, "results": res, "decisions": dec}, indent=1,
                                                    default=str))
    pd.DataFrame([{"candidate": c, **d} for c, d in dec.items()]).to_csv(plan.out / "decisions.csv", index=False)
    log("decisions", {c: d["verdict"] for c, d in dec.items()})
    return res, dec


def run_batch():
    """The one read. Refuses before RUN_FROM, without the frozen PREREG and its tokens, with changed inputs, or a
    second time."""
    if time.strftime("%Y-%m-%d", time.gmtime()) < RUN_FROM:
        raise SystemExit(f"the batch reads on or after {RUN_FROM}")
    plan = run_plan()
    log("prereg sha", prereg.verify(PREREG)[:12])
    text = PREREG.read_text()
    missing = [t for t in TOKENS if t not in text]
    if missing:
        raise SystemExit(f"the batch PREREG does not declare {missing}")
    if alpha_block() not in text:
        raise SystemExit("the PREREG's alpha block differs from ALPHA in this runner")
    inputs_ok(text)
    if (plan.out / "batch.json").exists():
        raise SystemExit("the batch has already been read: results/batch.json exists")
    with tempfile.TemporaryDirectory() as tmp:                     # the rules are still the lanes' rules, today
        _, bad = dry_check(tmp)
    if bad:
        raise SystemExit(f"the dry parity fails before the read, so the rules changed: {bad}")
    return read_batch(plan, BATCH / "work")


def rehearse(work):
    """The --run code on archive stand-ins, under a throwaway frozen PREREG holding every token."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    plan = rehearsal_plan(work)
    plan.prereg.write_text("# rehearsal of reserved batch 1 (not a batch)\n" + " ".join(TOKENS) + "\n\n" + alpha_block())
    prereg.freeze(plan.prereg)
    return read_batch(plan, work)


def dry_check(work, only=None):
    """Every candidate on the archive, against its lane's frozen numbers. Returns (results, mismatches)."""
    work = Path(work)
    res = run_events(None, work, only)
    bad = check_parity(res)
    if not only or "C01" in only:
        res["C01"] = run_unlock(None)
        bad += check_unlock_parity(res["C01"])
    if not only or "C14" in only:
        res["C14"] = run_carry(None, work)
        bad += check_carry_parity(res["C14"])
    if not only or "C11" in only:
        res["C11"] = run_brute(None)
        bad += check_brute_parity(res["C11"])
    return res, bad


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--rehearse", action="store_true")
    ap.add_argument("--only", help="comma-separated candidate ids")
    ap.add_argument("--work", help="working folder (default: a temporary one for --dry, BATCH/work for --run)")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    if a.run:
        run_batch()
        return
    if a.rehearse:
        res, dec = rehearse(a.work or tempfile.mkdtemp(prefix="batch_rehearsal_"))
        print(json.dumps(res, indent=1, default=str))
        return
    with tempfile.TemporaryDirectory() as tmp:
        res, bad = dry_check(a.work or tmp, only)
    print(json.dumps(res, indent=1, default=str))
    if bad:
        raise SystemExit(f"dry run does not reproduce the frozen lanes: {bad}")
    log(f"dry run reproduces {len(res)} frozen strategies")


if __name__ == "__main__":
    main()
