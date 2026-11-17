"""R505 cmeterm_v3 (supersedes R504, whose frozen fetch crashed on 2010 definition rows without a unit of measure,
before any settlement was pulled): commodity term-structure carry on 13 CME futures roots, 2010-09..2026-10.

Same rule as R503 and R504 (imported unchanged from the frozen `scripts/run_cmeterm.py`), same plumbing as R504, plus:
- a definition row without a unit of measure, or with one of zero or less, takes the root's standard CME contract
  unit (UNITS below); rows with a positive unit are checked against UNITS and any mismatch is reported (the
  definition's value is used);
- a definition row without an expiry, tick or raw symbol is dropped;
- settlement rows without a price, contract id, statistic type or update action are dropped before R503's parser;
- a raw statistics file already on disk (a run stopped between download and reduction) is reduced, not refetched;
- R504's daily rank map (`resolve.json`) and its 67 quarterly definition snapshots are reused from
  `data/databento/cmeterm_v2/`, pinned by hash; each snapshot is checked against R504's manifest before use.

R504's description of the plumbing follows.

The rule is R503's, imported unchanged from the frozen `scripts/run_cmeterm.py` (signal, validity, legs, weights,
holding, costs, statistics, variants and verdict). Only the way the data arrive changes:

- R503 asked Databento for 16 years of continuous-symbol definitions per root in one stream. That stream is generated
  day by day and was cut after about 15 minutes, before its end (2026-11-17, at 2020-05 of CL). This lane:
  - takes the daily rank -> contract map (n.0, n.1, n.2 by the previous day's open interest) from Databento's free
    symbology.resolve, one call per root;
  - takes each contract's expiry, tick and unit of measure from definition snapshots with stype_in=instrument_id: one
    request per quarter for the contracts mapped in that quarter (a 4-day window from the quarter's start), then one
    request per first-mapped day for any contract still missing;
  - pulls statistics one root and one calendar year per request (well under the cut), four roots at a time, each
    reduced on arrival to its settlement rows with R503's reducer; the raw file is deleted and the manifest keeps its
    quote, size and sha256.
- A day's rank map is the resolved mapping for that UTC date; a contract's details are taken from the latest snapshot
  on or before that date in which it is listed and not expired (else the earliest later one).

Paper research only: nothing here can place an order.

    python scripts/run_cmeterm_v3.py fetch    # PREREG must verify; capped
    python scripts/run_cmeterm_v3.py run      # PREREG must verify
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import statistics
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import run_cmeterm as r1          # noqa: E402  R503's frozen rule

LANE = ROOT / "experiments" / "cmeterm_v3"
DATA = ROOT / "data" / "databento" / "cmeterm_v3"
OLD = ROOT / "data" / "databento" / "cmeterm_v2"            # R504's pulls: resolve.json and defs/, pinned
UNITS = {"CL": 1000, "HO": 42000, "RB": 42000, "NG": 10000, "GC": 100, "SI": 5000, "HG": 25000, "PL": 50,
         "ZC": 5000, "ZS": 5000, "ZW": 5000, "LE": 40000, "HE": 40000}    # CME contract units (bbl, gal, MMBtu, oz, lb, bu)
UNIT_LOG = {"fallback_rows": 0, "mismatch_rows": 0, "mismatches": {}}
FETCH_START, FETCH_END = r1.FETCH_START, r1.FETCH_END
CAP_STATS_USD, CAP_DEF_USD, CAP_TOTAL_USD = 0.15, 0.05, 4.00
THREADS = 4
RETRIES = 4
BACKOFF_S = (30, 90, 240)
_LOCK = threading.Lock()


# ---------- calendar of requests ----------

def year_chunks(start=None, end=None):
    start, end = start or FETCH_START, end or FETCH_END
    out, a = [], dt.date.fromisoformat(start)
    stop = dt.date.fromisoformat(end)
    while a < stop:
        b = min(dt.date(a.year + 1, 1, 1), stop)
        out.append((a.isoformat(), b.isoformat()))
        a = b
    return out


def quarter_starts(start=None, end=None):
    start, end = start or FETCH_START, end or FETCH_END
    a, stop = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    out = [a]
    y, m = a.year, (a.month - 1) // 3 * 3 + 1
    while True:
        m += 3
        if m > 12:
            y, m = y + 1, m - 12
        q = dt.date(y, m, 1)
        if q >= stop:
            return out
        out.append(q)


# ---------- symbology and definitions ----------

def intervals_from_resolve(res):
    """{root: {rank: [(d0, d1, iid)]}} from symbology.resolve results (d1 exclusive)."""
    out = defaultdict(lambda: defaultdict(list))
    for sym, ivs in res.items():
        root, _, rank = sym.split(".")
        for iv in ivs:
            if str(iv.get("s", "")).isdigit():
                out[root][int(rank)].append((dt.date.fromisoformat(iv["d0"]), dt.date.fromisoformat(iv["d1"]),
                                             int(iv["s"])))
    return {k: dict(v) for k, v in out.items()}


def root_of_iids(intervals):
    return {iid: root for root, by_rank in intervals.items() for ivs in by_rank.values() for _, _, iid in ivs}


def info_index(defrows, roots):
    """{iid: [(snapshot day, expiry, tick, dollars per price unit, raw, root)]} sorted by snapshot day. roots maps
    each mapped contract id to its root; a definition whose raw symbol is not that root's (an id reused by another
    instrument) is dropped."""
    idx = defaultdict(list)
    seen = set()
    for r in defrows:
        if r.get("instrument_id") is None or not r.get("raw_symbol") or r.get("expiration") in (None, "") or \
                r.get("min_price_increment") in (None, ""):
            continue
        iid = int(r["instrument_id"])
        key = (iid, r["snap"])
        root = roots.get(iid)
        if key in seen or root is None or str(r["raw_symbol"])[:-2] != root:
            continue
        seen.add(key)
        uom = r.get("unit_of_measure_qty")
        if uom in (None, "") or float(uom) <= 0:
            uom = UNITS[root]
            UNIT_LOG["fallback_rows"] += 1
        elif float(uom) != UNITS[root]:
            UNIT_LOG["mismatch_rows"] += 1
            UNIT_LOG["mismatches"][root] = float(uom)
        mult = float(uom) * (0.01 if root in r1.CENTS else 1.0)
        idx[int(r["instrument_id"])].append((dt.date.fromisoformat(r["snap"]), r1.day_of(r["expiration"]),
                                             float(r["min_price_increment"]), mult, r["raw_symbol"], root))
    for v in idx.values():
        v.sort()
    return dict(idx)


def info_for(idx, iid, day):
    """(iid, expiry, tick, mult, raw) for a contract on day, or None."""
    cands = [c for c in idx.get(iid, []) if c[1] >= day]
    before = [c for c in cands if c[0] <= day]
    c = before[-1] if before else (cands[0] if cands else None)
    return None if c is None else (iid, c[1], c[2], c[3], c[4])


def ranks_from(intervals, idx, start=None, end=None):
    """R503's rank structure {day: {root: {rank: (iid, expiry, tick, mult, raw)}}} and the count of mapped
    contract-days without details."""
    ranks = defaultdict(lambda: defaultdict(dict))
    a, b = dt.date.fromisoformat(start or FETCH_START), dt.date.fromisoformat(end or FETCH_END)
    missing = 0
    for root, by_rank in intervals.items():
        for rank, ivs in by_rank.items():
            for d0, d1, iid in ivs:
                d = max(d0, a)
                while d < min(d1, b):
                    inf = info_for(idx, iid, d)
                    if inf:
                        ranks[d][root][rank] = inf
                    else:
                        missing += 1
                    d += dt.timedelta(days=1)
    return {d: dict(v) for d, v in ranks.items()}, missing


# ---------- fetch ----------

def _cost_ok(usd, cap, spent):
    with _LOCK:
        if usd > cap:
            raise SystemExit(f"refused: quoted ${usd:.4f} above the request cap ${cap}")
        if spent[0] + usd > CAP_TOTAL_USD:
            raise SystemExit(f"stop: total cap ${CAP_TOTAL_USD} would be passed (spent ${spent[0]:.4f})")
        spent[0] += usd


def get_defs(ids, start, end, key, tag, spent):
    """Definitions for instrument ids in [start, end): quoted, capped (every attempt counts), kept (small), manifest
    row appended."""
    import requests
    from scripts import fetch_databento as fd
    p = {"dataset": "GLBX.MDP3", "symbols": ",".join(str(i) for i in sorted(ids)), "stype_in": "instrument_id",
         "schema": "definition", "start": start, "end": end}
    path = DATA / "defs" / f"def_{tag}.csv.zst"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = dict(p, stype_out="instrument_id", encoding="csv", compression="zstd", map_symbols="true",
                pretty_px="true", pretty_ts="true")
    tmp = path.with_suffix(".tmp")
    for attempt in range(RETRIES):
        usd = fd.quote(p, key)
        _cost_ok(usd, CAP_DEF_USD, spent)
        try:
            with requests.post(f"{fd.BASE}/timeseries.get_range", data=body, auth=(key, ""), stream=True,
                               timeout=300) as r:
                if r.status_code != 200:
                    raise RuntimeError(f"get_range failed: http {r.status_code} {r.text[:200]}")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            break
        except Exception:
            if attempt == RETRIES - 1:
                raise
            time.sleep(BACKOFF_S[attempt])
    tmp.rename(path)
    with _LOCK:
        new = not (DATA / "manifest_defs.csv").exists()
        with open(DATA / "manifest_defs.csv", "a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(["file", "ids", "start", "end", "quoted_usd", "bytes", "sha256"])
            w.writerow([path.name, len(ids), start, end, f"{usd:.6f}", path.stat().st_size, fd.sha256(path)])
    return path


def old_defs_checked():
    """R504's quarterly snapshots, each checked against R504's manifest."""
    with (OLD / "manifest_defs.csv").open(newline="") as f:
        man = {r["file"]: r["sha256"] for r in csv.DictReader(f)}
    paths = sorted((OLD / "defs").glob("def_*.csv.zst"))
    for p in paths:
        if hashlib.sha256(p.read_bytes()).hexdigest() != man.get(p.name):
            raise SystemExit(f"{p} does not match R504's manifest")
    return paths


def read_defs():
    rows = []
    own = sorted((DATA / "defs").glob("def_*.csv.zst")) if (DATA / "defs").exists() else []
    for path in old_defs_checked() + own:
        for batch in r1._reader(path, r1.DEF_COLS):
            for r in batch.to_pylist():
                r["snap"] = r1.day_of(r["ts_recv"]).isoformat()
                rows.append(r)
    return rows


def resolve_all(key):
    import requests
    from scripts import fetch_databento as fd
    res = {}
    for root in r1.ROOTS:
        r = requests.post(f"{fd.BASE}/symbology.resolve",
                          data={"dataset": "GLBX.MDP3", "symbols": ",".join(f"{root}.n.{i}" for i in r1.RANKS),
                                "stype_in": "continuous", "stype_out": "instrument_id", "start_date": FETCH_START,
                                "end_date": FETCH_END}, auth=(key, ""), timeout=300)
        if r.status_code != 200:
            raise SystemExit(f"resolve {root}: http {r.status_code} {r.text[:200]}")
        res.update(r.json()["result"])
    return res


def done_set():
    if not (DATA / "reduced.csv").exists():
        return set()
    with (DATA / "reduced.csv").open(newline="") as f:
        return {r["request"] for r in csv.DictReader(f)}


def fetch_root(root, key, spent, log):
    from scripts import fetch_databento as fd
    done = done_set()
    for a, b in year_chunks():
        p = {"dataset": "GLBX.MDP3", "symbols": ",".join(f"{root}.n.{i}" for i in r1.RANKS),
             "stype_in": "continuous", "schema": "statistics", "start": a, "end": b}
        tag = f"{p['symbols']}|statistics|{a}|{b}"
        if tag in done:
            continue
        stem = "_".join([p["dataset"], p["symbols"].replace(",", "+"), p["schema"], p["start"], p["end"]])
        path = DATA / f"{stem.replace(':', '')}.csv.zst"
        usd = 0.0
        for attempt in range(RETRIES if not path.exists() else 0):   # each attempt counts against the cap
            usd = fd.quote(p, key)
            _cost_ok(usd, CAP_STATS_USD, spent)
            try:
                path, _ = fd.fetch(p, key, DATA, CAP_STATS_USD)
                break
            except (Exception, SystemExit) as e:             # a cut stream or a 5xx: wait and ask again
                if isinstance(e, SystemExit) and ("refused" in str(e) or "exists" in str(e)):
                    raise
                log(f"retry {root} {a} after {type(e).__name__}: {str(e)[:80]}")
                if attempt == RETRIES - 1:
                    raise
                time.sleep(BACKOFF_S[attempt])
        kept = r1.reduce_stats(path, DATA / f"settle_{root}.csv")
        path.unlink()
        with _LOCK:
            new = not (DATA / "reduced.csv").exists()
            with (DATA / "reduced.csv").open("a", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                if new:
                    w.writerow(["request", "kept_rows", "raw_deleted"])
                w.writerow([tag, kept, True])
        log(f"statistics {root} {a} ${usd:.4f} {kept}")


def fetch():
    from lab.prereg import verify
    from scripts import fetch_databento as fd
    verify(LANE / "PREREG.md")
    check_inputs()
    key, spent = fd.read_key(), [0.0]
    DATA.mkdir(parents=True, exist_ok=True)

    def log(msg):
        with _LOCK:
            print(msg, flush=True)

    iv = intervals_from_resolve(json.loads((OLD / "resolve.json").read_text()))     # R504's, pinned
    log(f"resolved {sum(len(x) for r in iv.values() for x in r.values())} intervals (R504's map)")
    # R504's 67 quarterly snapshots are reused; then the first-mapped day of any contract still without details
    have = {p.name for p in (DATA / "defs").glob("*.csv.zst")} if (DATA / "defs").exists() else set()
    idx = info_index(read_defs(), root_of_iids(iv))
    first = {}
    for r in iv.values():
        for ivs in r.values():
            for d0, d1, iid in ivs:
                if info_for(idx, iid, max(d0, dt.date.fromisoformat(FETCH_START))) is None:
                    first[iid] = min(first.get(iid, d0), d0)
    by_day = defaultdict(set)
    for iid, d0 in first.items():
        by_day[d0].add(iid)
    jobs = [(ids, d0.isoformat(), (d0 + dt.timedelta(days=4)).isoformat(), key, f"d{d0.isoformat()}", spent)
            for d0, ids in sorted(by_day.items()) if f"def_d{d0.isoformat()}.csv.zst" not in have]
    with ThreadPoolExecutor(THREADS) as ex:
        for f in [ex.submit(get_defs, *j) for j in jobs]:
            f.result()
    log(f"definitions follow-up for {len(first)} contracts on {len(by_day)} days")
    with ThreadPoolExecutor(THREADS) as ex:
        for f in [ex.submit(fetch_root, root, key, spent, log) for root in r1.ROOTS]:
            f.result()
    log(f"spent ${spent[0]:.4f}")


def check_inputs(prereg=None):
    import re
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        got = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if got != digest:
            raise SystemExit(f"{path} changed since the freeze: {got} != {digest}")
    return pairs


# ---------- run ----------

def complete(r):
    return all(r.get(c) not in (None, "") for c in ("price", "instrument_id", "stat_type", "update_action"))


def load():
    rows, dropped = [], 0
    for root in r1.ROOTS:
        p = DATA / f"settle_{root}.csv"
        if p.exists():
            with p.open(newline="") as f:
                for r in csv.DictReader(f):
                    if complete(r):
                        rows.append(r)
                    else:
                        dropped += 1
    UNIT_LOG["settlement_rows_dropped"] = dropped
    settle = r1.settlements_from_rows(rows)
    iv = intervals_from_resolve(json.loads((OLD / "resolve.json").read_text()))
    ranks, missing = ranks_from(iv, info_index(read_defs(), root_of_iids(iv)))
    return r1.calendar(settle, ranks), settle, ranks, missing


def report(cal, settle, ranks):
    """R503's report, computed with R503's functions (same cells as R503's run)."""
    vols = r1.vol_series(cal, settle, ranks)
    rep = {"rule": {"roots": r1.ROOTS, "fee_usd": r1.FEE_USD, "slip_ticks": r1.SLIP_TICKS, "min_roots": r1.MIN_ROOTS,
                    "min_days_to_expiry": r1.MIN_DAYS_TO_EXPIRY, "vol_n": r1.VOL_N, "nw_lag": r1.NW_LAG},
           "calendar_days": len(cal), "settlements": len(settle)}
    prim, dec = r1.build(cal, settle, ranks, vols=vols)
    rep["primary_1x"] = p1 = r1.summarize(prim)
    rep["primary_2x"] = p2 = r1.summarize(r1.build(cal, settle, ranks, cost_k=2.0, vols=vols)[0])
    rep["primary_3x"] = r1.summarize(r1.build(cal, settle, ranks, cost_k=3.0, vols=vols)[0])
    rep["verdict"] = r1.verdict_of(p1, p2)
    rep["by_year_1x"] = r1.by_year(prim)
    rep["first_half_1x"] = r1.summarize([r for r in prim if r["day"] < "2018-07-01"])
    rep["second_half_1x"] = r1.summarize([r for r in prim if r["day"] >= "2018-07-01"])
    rep["since_2024_1x"] = r1.summarize([r for r in prim if r["day"] >= "2024-01-01"])
    rep["by_root_gross_pct"], rep["by_sector_gross_pct"] = r1.contributions(prim)
    books = [x for x in dec if x["book"]]

    def mean_(xs, f=statistics.mean, nd=2):
        xs = list(xs)
        return round(f(xs), nd) if xs else None

    rep["months"] = {"decisions": len(dec), "with_book": len(books),
                     "mean_valid_roots": mean_(x["valid"] for x in dec),
                     "skips": {k: sum(x["skipped"].get(k, 0) for x in dec) for k in
                               ("no_rank", "no_carry", "near_expiry", "no_entry_price", "no_vol")},
                     "mean_carry_spread_pct": mean_(x["carry_spread"] * 100 for x in books),
                     "holdings": sum(len(x["longs"]) + len(x["shorts"]) for x in books),
                     "holdings_under_60d_to_expiry": sum(x["under_60d"] for x in books),
                     "min_capital_usd_median": mean_((x["min_capital"] for x in books), statistics.median, 0),
                     "min_capital_usd_last": round(books[-1]["min_capital"]) if books else None,
                     "long_share": {r: mean_((r in x["longs"] for x in books), nd=3) for r in r1.ROOTS},
                     "short_share": {r: mean_((r in x["shorts"] for x in books), nd=3) for r in r1.ROOTS}}
    rep["equal_weight_1x"] = r1.summarize(r1.build(cal, settle, ranks, weighting="ew", vols=vols)[0])
    rep["k3_1x"] = r1.summarize(r1.build(cal, settle, ranks, k=3, vols=vols)[0])
    rep["no_lag_1x"] = r1.summarize(r1.build(cal, settle, ranks, lag=False, vols=vols)[0])
    rep["carry12_1x"] = r1.summarize(r1.build(cal, settle, ranks, signal="carry12", vols=vols)[0])
    return rep, prim, dec


def run():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    cal, settle, ranks, missing = load()
    rep, prim, dec = report(cal, settle, ranks)
    rep["mapped_contract_days_without_details"] = missing
    rep["data_checks"] = dict(UNIT_LOG)
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    with (res / "daily.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "gross", "cost", "net"])
        for r in prim:
            w.writerow([r["day"], f"{r['gross']:.8f}", f"{r['cost']:.8f}", f"{r['net']:.8f}"])
    with (res / "months.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["decision", "entry", "valid", "book", "longs", "shorts", "carry_spread", "min_capital"])
        for x in dec:
            w.writerow([x["decision"], x["entry"], x["valid"], x["book"], " ".join(x.get("longs", [])),
                        " ".join(x.get("shorts", [])),
                        f"{x['carry_spread']:.5f}" if x["book"] else "", f"{x['min_capital']:.0f}" if x["book"] else ""])
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], "primary_1x": rep["primary_1x"], "primary_2x": rep["primary_2x"]},
                     default=str))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("fetch", "run"))
    a = ap.parse_args(argv)
    return fetch() if a.cmd == "fetch" else run()


if __name__ == "__main__":
    sys.exit(main() or 0)
