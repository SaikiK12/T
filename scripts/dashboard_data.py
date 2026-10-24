"""Export the lab's state as the dashboard's datasets: dashboard/data/<id>.json, one array of row objects each.

Read-only on the lab: the registry, the candidates watchlist, every family report and event-lane verdict, the forward
lanes' journals, the methods queue, the data folders and the loop's logs. It decides nothing; numbers are copied from
the files that hold them. The page (dashboard/index.html) is published to the Control Room artifact; each loop tick
re-runs this script and uploads the files whose hash changed (dashboard/data/manifest.json lists them).

usage: python -m lab export             # immutable datasets + atomic latest manifest
       python -m lab export --changed   # {generation, files}; upload exactly these paths
       python -m lab export --record jobs=/_blob/<id> --generation <export-id>
       python -m lab export --docs      # acknowledged generations only

Publication acknowledges returned upload URLs; remote delivery itself is not verified by this script.
"""
import csv
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import stat
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"
OUT = ROOT / "dashboard" / "data"
sys.path.insert(0, str(ROOT))
NOW = time.time()
ISO = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
# forward lanes: (registry id, lane, what it trades, venue, mode, rows needed for its decision, decision rule)
from lab.operations import LANES, OBJECTIVE

FORWARD = [(l.rid, l.path, l.what, l.venue, l.mode, l.needed, l.rule) for l in LANES]

def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def read_json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def rows_csv(p):
    try:
        with open(p, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def rid_by_path():
    return {r["path"].rstrip("/"): r["id"] for r in rows_csv(ROOT / "registry" / "rounds.csv") if r.get("path")}


def rounds():
    out = []
    for i, r in enumerate(rows_csv(ROOT / "registry" / "rounds.csv")):
        out.append({"id": r["id"], "order": i + 1, "date": r["date"] or None, "lane": r["lane"], "status": r["status"],
                    "verdict": r["verdict"], "trials": num(r["trials"]), "title": r["title"],
                    "notes": (r["notes"] or "")[:240]})
    return out


def program(rnd):
    from lab import registry
    trials = registry.program_trials(str(ROOT / "registry" / "rounds.csv"))
    lag = read_json(EXP / "forward_lag" / "status.json")
    cand = rows_csv(ROOT / "registry" / "candidates.csv")
    due = sorted(c["due"] for c in cand if c["due"])
    du = shutil.disk_usage(ROOT)
    count = lambda v: sum(r["verdict"] == v for r in rnd)
    return [{"generated_at": ISO(NOW), "objective": OBJECTIVE, "program_trials": trials, "rounds": len(rnd), "null": count("NULL"),
             "partial": count("PARTIAL"), "confirmed": count("CONFIRMED"),
             "running": sum(r["status"] in ("RUNNING", "ARMED") for r in rnd),
             "strict_ontime_days": lag.get("strict_ontime_days"), "candidates": len(cand),
             "next_due": due[0] if due else None, "disk_free_gb": round(du.free / 1e9, 1)}]


def stat_row(rid, lane, family, label, by_cost, p_rc=None, null_p=None, passed=False, n_strats=None):
    s1, s2, s3 = (by_cost.get(k) or {} for k in ("1x", "2x", "3x"))
    return {"key": f"{rid} {label}", "round": rid, "lane": lane, "family_size": n_strats, "strategy": label,
            "n": s1.get("n"), "mean_pct": num(s1.get("mean_pct")), "median_pct": num(s1.get("median_pct")),
            "hit": num(s1.get("hit")), "t": num(s1.get("t", s1.get("week_cluster_t"))),
            "mean_2x_pct": num(s2.get("mean_pct")), "mean_3x_pct": num(s3.get("mean_pct")),
            "half1_pct": num(s1.get("half1_pct")), "half2_pct": num(s1.get("half2_pct")),
            "y2025_pct": num(s1.get("y2025_pct")), "y2025_n": s1.get("y2025_n"), "p_rc": num(p_rc),
            "null_p": num(null_p), "passed": bool(passed), "family": family}


def per_day(x):
    """A qx spread book's day stats in the per-event fields: the mean and halves are per day, in %."""
    pct = lambda v: v / 100 if isinstance(v, (int, float)) else None
    return {"n": x.get("days"), "mean_pct": pct(x.get("mean_bp")), "t": x.get("t"), "half1_pct": pct(x.get("half1_bp")),
            "half2_pct": pct(x.get("half2_bp")), "y2025_pct": pct(x.get("recent_bp")), "y2025_n": x.get("recent_days")}


def strategies():
    """Every tested strategy on file: qx family reports (event families per event, spread books per day, factor
    reports per factor and horizon) and the event lanes' variants."""
    rids, out = rid_by_path(), []
    for rep_path in sorted(EXP.glob("*/results/report.json")):
        lane = rep_path.parent.parent.name
        rid = rids.get(f"experiments/{lane}")
        rep = read_json(rep_path)
        if not rid:
            continue
        factor_rows = (rep.get("results") or []) if "factors" in (rep.get("spec") or {}) else []
        for r in factor_rows:
            ls = r.get("ls_bp")
            out.append(stat_row(rid, lane, rep["name"], f"{r['factor']} {r['horizon_h']}h",
                                {"1x": {"n": r.get("dates"), "mean_pct": ls / 100 if ls is not None else None,
                                        "hit": r.get("rank_ic_pos"), "t": r.get("rank_ic_t")}},
                                r.get("p_rc"), None, r.get("rc_pass"), rep["trials"]))
        for s in rep.get("strategies") or []:
            st = [per_day(x) if "ann_pct" in x else x for x in s["stats"]]
            out.append(stat_row(rid, lane, rep["name"], s["label"], {"1x": st[0], "2x": st[1], "3x": st[2]},
                                s.get("p_rc"), (s.get("null") or {}).get("p"), s.get("pass"), rep["trials"]))
    for v_path in sorted(EXP.glob("*/results/verdict.json")):
        lane = v_path.parent.parent.name
        rid = rids.get(f"experiments/{lane}")
        v = read_json(v_path)
        if not rid:
            continue
        if isinstance(v.get("variants"), dict):
            nv = len(v["variants"])
            for k, var in v["variants"].items():
                primary = k.startswith("1:")
                null_p = (v.get("null") or {}).get("p") if primary else None
                ok = primary and v.get("verdict") in ("REPLICATES", "PASS", "CONFIRMED")
                out.append(stat_row(rid, lane, lane, re.sub(r"^\d+:\s*", "", k), var, None, null_p, ok, nv))
        elif isinstance(v.get("primary"), dict) and "1x" in v["primary"]:
            out.append(stat_row(rid, lane, lane, "primary", v["primary"], None, (v.get("null") or {}).get("p"),
                                v.get("verdict") in ("REPLICATES", "PASS", "CONFIRMED"), v.get("trials")))
    return out


def forward_days():
    from lab.operations import forward_days as project
    return project(ROOT)


def forward_lanes(days):
    from lab.operations import forward_lanes as project
    return project(ROOT, days, NOW)


def event_tickets():
    out = []

    def state(ticket, score):
        if score is not None:
            return "scored" if num(score.get("net")) is not None else "score unavailable"
        if NOW < int(ticket["entry_ms"]) / 1000:
            return "frozen, not entered"
        if NOW >= int(ticket["exit_ms"]) / 1000:
            return "awaiting score"
        return "open"

    u = read_json(EXP / "unlocks_fwd" / "journal" / "status.json")
    unlock_scores = {r["ticket"]: r for r in rows_csv(EXP / "unlocks_fwd" / "journal" / "scores.csv")}
    for r in rows_csv(EXP / "unlocks_fwd" / "journal" / "tickets.csv"):
        score = unlock_scores.get(r["ticket"])
        net = num(score.get("net")) if score is not None else None
        size = num(r.get("frac_max_supply"))
        out.append({"key": r["ticket"], "round": "R266", "lane": "unlocks_fwd", "symbol": r["contract"],
                    "entry_at": ISO(int(r["entry_ms"]) / 1000), "exit_at": ISO(int(r["exit_ms"]) / 1000),
                    "state": state(r, score), "size_pct_supply": None if size is None else size * 100,
                    "net_pct": None if net is None else net * 100})
    for e in u.get("next_entries", []):
        at, sym = e.split(" ", 1)
        key = f"next {sym} {at[:10]}"
        if not any(t["symbol"] == f"{sym}_USDT" and t["entry_at"][:10] == at[:10] for t in out):
            out.append({"key": key, "round": "R266", "lane": "unlocks_fwd", "symbol": sym, "entry_at": at,
                        "exit_at": None, "state": "upcoming on the calendar", "size_pct_supply": None, "net_pct": None})
    for lane, rid in (("delist_fwd", "R268"), ("montag_fwd", "R270"), ("announce_fwd", "R272")):
        scores = {r["ticket"]: r for r in rows_csv(EXP / lane / "journal" / "scores.csv")}
        for r in rows_csv(EXP / lane / "journal" / "tickets.csv"):
            score = scores.get(r["ticket"])
            net = num(score.get("net")) if score is not None else None
            out.append({"key": r["ticket"], "round": rid, "lane": lane, "symbol": r.get("contract"),
                        "entry_at": ISO(int(r["entry_ms"]) / 1000), "exit_at": ISO(int(r["exit_ms"]) / 1000),
                        "state": state(r, score), "size_pct_supply": None,
                        "net_pct": None if net is None else net * 100})
    return sorted(out, key=lambda r: r["entry_at"] or "")


def methods():
    out = []
    for r in rows_csv(ROOT / "registry" / "methods.csv"):
        out.append({"id": r["id"], "method": r["method"], "status": r["status"], "data_held": r["data_held"],
                    "cheap": r["cheap"], "round": r.get("rid") or None, "source": r.get("source") or None,
                    "note": r.get("note") or None})
    return out


def data_sources():
    """Metadata inventory only: never follow links or infer market coverage from file activity."""
    prov = {p.stem for p in (ROOT / "docs" / "provenance").glob("*.json")}
    fresh_h = {"live": 2, "recorders": 2, "mexc": 2, "logs": 2, "hyperliquid": 26, "tape": 1}
    labels = {
        "mexc": ("MEXC forward-data cache", "Prospective collection"),
        "mexc_hist": ("MEXC historical futures", "Historical market data"),
        "recorders": ("Point-in-time exchange and event snapshots", "Prospective collection"),
        "tape": ("Order-flow tape: best bid/ask and trades per second, Binance and MEXC", "Prospective collection"),
        "daily": ("Daily point-in-time panel", "Derived data"),
        "live": ("Live market observations", "Prospective collection"),
        "logs": ("Collector and scheduler logs", "Operational logs"),
        "hyperliquid": ("Hyperliquid observations", "Prospective collection"),
        "klines_1h": ("Binance hourly perpetual candles", "Historical market data"),
        "fundingRate": ("Binance settled funding", "Historical market data"),
        "metrics_1h": ("Binance hourly positioning metrics", "Historical market data"),
        "spot_1h": ("Hourly spot candles", "Historical market data"),
        "coinm_1h": ("Legacy coin-margined futures candles (original labels)", "Historical market data"),
        "coinm_1h_v2": ("Coin-margined futures candles (corrected base-volume units)", "Historical market data"),
        "unlocks": ("Token unlock calendars", "Event data"),
        "gate_hist": ("Gate bulk archive: all USDT perps, hourly candles and funding", "Historical market data"),
        "gate_1h": ("Gate hourly contract stats (180-day window)", "Historical market data"),
        "premiumIndexKlines_1h": ("Binance hourly premium index", "Historical market data"),
        "bookDepth_1h": ("Binance hourly book depth", "Historical market data"),
        "deribit": ("Deribit implied-volatility index (DVOL)", "Historical market data"),
        "coinbase": ("Coinbase hourly spot candles", "Historical market data"),
        "binance_spot": ("Binance hourly spot klines (BTC, ETH)", "Historical market data"),
        "markets": ("TradFi daily markets", "Historical market data"),
        "research": ("Built research panels", "Derived data"),
        "raw": ("Raw archive downloads", "Raw downloads"),
    }
    base = ROOT / "data"
    if base.is_symlink() or not base.is_dir():
        return []
    out = []
    for d in sorted(base.iterdir()):
        if not d.is_symlink() and not d.is_dir():
            continue
        n = size = skipped = 0
        newest = None
        errors = []
        if d.is_symlink():
            skipped = 1
        else:
            for dp, directories, files in os.walk(d, onerror=errors.append, followlinks=False):
                links = [name for name in directories if (Path(dp) / name).is_symlink()]
                skipped += len(links)
                directories[:] = [name for name in directories if name not in links]
                for name in files:
                    try:
                        st = (Path(dp) / name).lstat()
                        if stat.S_ISLNK(st.st_mode):
                            skipped += 1
                        elif stat.S_ISREG(st.st_mode):
                            n, size = n + 1, size + st.st_size
                            newest = st.st_mtime if newest is None else max(newest, st.st_mtime)
                    except OSError as error:  # A downloader can replace/remove a file during inventory.
                        errors.append(error)
        age = round((NOW - newest) / 3600, 2) if newest is not None else None
        limit = fresh_h.get(d.name)
        complete = not errors and not skipped
        stale = age > limit if complete and limit and age is not None and age >= 0 else None
        label, category = labels.get(d.name, (d.name, "Unclassified data"))
        out.append({"source": d.name, "display_name": label, "category": category,
                    "files": n, "size_gb": round(size / 1e9, 3),
                    "newest_at": ISO(newest) if newest is not None else None,
                    "age_h": age, "kind": category, "stale": stale, "provenance": d.name in prov,
                    "inventory_state": "COMPLETE" if complete else "PARTIAL",
                    "scan_errors": len(errors), "skipped_links": skipped,
                    "freshness_basis": "filesystem modification time only; market coverage unverified"})
    return out


def jobs(state_dir=None):
    """Read categorized process reports; legacy log timestamps never imply success."""
    try:
        from scripts.dashboard_jobs import build_jobs
    except ModuleNotFoundError:
        from dashboard_jobs import build_jobs
    return build_jobs(ROOT, now=NOW, state_dir=state_dir) + running()


def running(proc=Path("/proc")):
    """Lab scripts and qx runs alive now (downloads, family runs, loops), by script name and start time only: no
    command line, argument or environment is exported. A running process says nothing about success."""
    out = []
    try:
        pids = [p for p in os.listdir(proc) if p.isdigit()]
    except OSError:
        return out
    for pid in pids:
        try:
            cmd = (proc / pid / "cmdline").read_bytes().split(b"\0")
            start = (proc / pid).stat().st_mtime
        except OSError:
            continue
        words = [w.decode(errors="replace") for w in cmd if w]
        name = next((Path(w).name for w in words if re.fullmatch(r"scripts/[A-Za-z0-9_]+\.(?:py|sh)", w)), None)
        if name is None and any(w.endswith("target/release/qx") for w in words):
            name = "qx engine"
        if name is None or name == "dashboard_data.py":
            continue
        out.append({"key": f"process {name} {pid}", "task_id": f"process {pid}", "job": name, "display_name": name,
                    "category": "Background processes", "kind": "Background processes", "lane": None, "run_id": None,
                    "state": "RUNNING", "status_source": "process_table", "returncode": None, "at": ISO(start),
                    "age_h": round(max(0, NOW - start) / 3600, 2), "stale": None, "ok": None, "log_path": None,
                    "note": "Running now. The process table shows that it runs, not that it succeeds."})
    return sorted(out, key=lambda r: r["key"])


TITLES = {
    "program": ("Lab program summary", "One row: program trials (lab.registry.program_trials), rounds by verdict, "
                "watchlist size, strict on-time paper days, the next due date and free disk."),
    "rounds": ("Registered rounds", "Every round in registry/rounds.csv with its verdict and trial count."),
    "candidates": ("Candidate watchlist", "registry/candidates.csv: each edge still alive, its best evidence, its "
                   "funnel stage and what decides it next."),
    "strategies": ("Tested strategies", "Stats at 1x/2x/3x cost for every strategy in a qx family report or an event "
                   "lane's verdict (experiments/*/results): per event for event families, per day for spread books, "
                   "and for factor reports the long-short per date with t of the rank IC."),
    "forward_lanes": ("Forward paper lanes", "Each forward paper lane's progress toward its decision and its paper "
                      "net, from its journal."),
    "forward_days": ("Daily paper returns", "Net return per day at 1x/2x/3x cost for each daily book, replayed or "
                     "traded on time, from the forward journals."),
    "event_tickets": ("Event tickets", "Unlock, delisting and Monitoring Tag paper tickets, and the unlocks next on "
                      "the recorded calendar."),
    "methods": ("Method queue", "registry/methods.csv: every method from the literature, old sessions and both AIs, "
                "with its status."),
    "data_sources": ("Data folders", "Size, newest file and provenance note of each folder under data/."),
    "tearsheets": ("Performance tear sheets", "lab.tearsheet metrics for every forward paper book and saved research "
                   "stream: CAGR, Sharpe (naive and autocorrelation-adjusted), drawdown, Newey-West t, PSR and the "
                   "Sharpe deflated at the program's trial count."),
    "equity": ("Equity and drawdown by day", "Compounded equity, drawdown and 90-day rolling Sharpe per series and "
               "day, for the tear sheets."),
    "monthly": ("Monthly returns", "Compounded net return per series and calendar month."),
    "leaderboard": ("Rounds against their bars", "Each registered round's trial count, running program total, best t "
                    "on file, the chance bar for that many tries and the family's own reality-check null."),
    "coverage": ("Data coverage", "First and last bar, files, size and missing hours of each downloaded dataset "
                 "(provenance records) and each live recorder."),
    "funding_board": ("Cross-venue funding board", "Latest hourly snapshot of funding on seven venues, 8-hour "
                      "equivalent, widest spreads first. Descriptive only."),
    "factor_ic": ("Factor IC by month", "Monthly mean IC, rank IC and long-short of each factor and horizon in a "
                  "registered qx factor report, for IC decay and stability."),
    "jobs": ("Operations by responsibility", "Categorized task reports (legacy activity is unverified) and the lab "
             "scripts running now, by script name only. No raw logs or process command lines are exported."),
}


def _generation(generation=None):
    """A pinned immutable manifest, never an acknowledgement of whatever is latest."""
    man = read_json(OUT / "manifest.json") if generation is None else None
    if generation is None:
        generation = man.get("generation")
    if not isinstance(generation, str) or not re.fullmatch(r"[a-f0-9]{64}", generation):
        raise ValueError("a verified export generation is required; export again")
    directory = OUT / "generations" / generation
    if directory.is_symlink() or any(p.is_symlink() for p in directory.parents):
        raise ValueError("symlink generation")
    pinned = json.loads((directory / "manifest.json").read_text())
    if pinned.get("generation") != generation:
        raise ValueError("generation identity mismatch")
    signatures = {k: value["sha256"] for k, value in pinned["sets"].items()}
    identity = hashlib.sha256(json.dumps({"at": pinned["generated_at"], "sets": signatures},
                                         sort_keys=True).encode()).hexdigest()
    if identity != generation:
        raise ValueError("manifest content disagrees with generation identity")
    if man is not None and pinned != man:
        raise ValueError("current manifest disagrees with immutable generation")
    return pinned


@contextmanager
def publication_lock():
    """Serialize local publication pointers, receipts and their derived docs."""
    fd = os.open(OUT / ".publish.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def publish_sets(sets, generated_at):
    """Write immutable bytes, then switch the derived latest manifest atomically."""
    from lab.runtime import atomic_json
    bodies = {k: json.dumps(rows, separators=(",", ":"), default=str, allow_nan=False).encode()
              for k, rows in sets.items()}
    if any(k not in TITLES for k in bodies):
        raise ValueError("unknown dataset")
    signatures = {k: hashlib.sha256(body).hexdigest() for k, body in bodies.items()}
    generation = hashlib.sha256(json.dumps({"at": generated_at, "sets": signatures},
                                          sort_keys=True).encode()).hexdigest()
    directory = OUT / "generations" / generation
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        # A completed export is idempotent; an interrupted one without a valid
        # manifest stays blocked. No previous bytes are changed or deleted.
        manifest = _generation(generation)
        for key in bodies:
            _dataset(manifest, key)
    else:
        manifest = {"schema_version": 2, "generation": generation, "generated_at": generated_at, "sets": {}}
        for k, body in bodies.items():
            path = directory / (k + ".json")
            with path.open("xb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            manifest["sets"][k] = {"file": str(path.relative_to(ROOT)), "rows": len(sets[k]),
                                   "sha256": signatures[k]}
        with (directory / "manifest.json").open("x") as stream:
            json.dump(manifest, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
    with publication_lock():
        latest = read_json(OUT / "manifest.json")
        if latest.get("generated_at", "") > generated_at:
            raise ValueError("refusing to replace latest export with an older generation")
        atomic_json(OUT / "manifest.json", manifest)
    return manifest


def _dataset(man, key):
    if key not in man["sets"] or key not in TITLES:
        raise ValueError("unknown dataset")
    expected = OUT / "generations" / man["generation"] / (key + ".json")
    item = man["sets"][key]
    if item["file"] != str(expected.relative_to(ROOT)) or expected.is_symlink():
        raise ValueError("unexpected dataset path")
    if hashlib.sha256(expected.read_bytes()).hexdigest() != item["sha256"]:
        raise ValueError("immutable export hash mismatch")
    return expected


def _update(key, receipt):
    return {"source": {"kind": "file", "url": receipt["url"], "name": f"{key}.json"},
            "updated": {"at": receipt["generated_at"], "by": "Lab exporter"}}


def docs():
    """Documents use acknowledged generations, not the most recent export clock."""
    with publication_lock():
        return _docs_locked()


def _docs_locked():
    receipts = read_json(OUT / "uploads.json")
    if not receipts and (OUT / "uploaded.json").exists():
        raise ValueError("legacy uploads lack generation receipts; acknowledge immutable exports first")
    directory = OUT / "docs"
    directory.mkdir(exist_ok=True)
    from lab.runtime import atomic_json
    for k, receipt in receipts.items():
        man = _generation(receipt["generation"])
        _dataset(man, k)
        if receipt["sha256"] != man["sets"][k]["sha256"] or receipt["generated_at"] != man["generated_at"]:
            raise ValueError("upload receipt disagrees with generation")
        title, desc = TITLES[k]
        document = {"title": title, "description": desc, **_update(k, receipt),
                    "schedule": "Explicit export and acknowledged upload", "staleAfterHours": 6}
        atomic_json(directory / f"{k}.json", document)
        atomic_json(directory / f"{k}.update.json", _update(k, receipt))
    atomic_json(directory / "index.html.json", {"text": (ROOT / "dashboard/index.html").read_text()})
    print(f"{len(receipts)} acknowledged dataset documents")


def changed(generation=None):
    man = _generation(generation)
    uploaded = read_json(OUT / "uploads.json")
    files = {k: str(_dataset(man, k)) for k, v in man["sets"].items()
             if uploaded.get(k, {}).get("sha256") != v["sha256"]}
    payload = {"generation": man["generation"], "files": files}
    print(json.dumps(payload))
    return payload


def record(pairs, generation=None):
    if generation is None:
        raise ValueError("--record requires --generation from --changed; latest is not an upload receipt")
    from lab.runtime import atomic_json
    man = _generation(generation)
    receipts = []
    for pair in pairs:
        k, url = pair.split("=", 1)
        _dataset(man, k)
        if not url or any(c.isspace() for c in url) or not (url.startswith("/_blob/") or url.startswith("https://")):
            raise ValueError("upload URL must be a returned blob path or HTTPS URL")
        receipts.append((k, {"url": url, "sha256": man["sets"][k]["sha256"],
                             "generation": generation, "generated_at": man["generated_at"]}))
    if len({k for k, _ in receipts}) != len(receipts):
        raise ValueError("duplicate upload acknowledgement")
    # One writer for the derived upload receipt, including concurrent generations.
    with publication_lock():
        uploaded = read_json(OUT / "uploads.json")
        for k, receipt in receipts:
            old = uploaded.get(k, {})
            if old.get("generated_at", "") > receipt["generated_at"]:
                raise ValueError("refusing acknowledgement older than the published generation")
        uploaded.update(receipts)
        atomic_json(OUT / "uploads.json", uploaded)
        directory = OUT / "docs"
        directory.mkdir(exist_ok=True)
        for k, receipt in receipts:
            atomic_json(directory / f"{k}.update.json", _update(k, receipt))
        # Compatibility views are derived from uploads.json; never read as authority.
        atomic_json(OUT / "uploaded.json", {k: v["url"] for k, v in uploaded.items()})
        atomic_json(OUT / "uploaded_sha.json", {k: v["sha256"] for k, v in uploaded.items()})
    print(f"recorded {len(receipts)} uploads for {generation}")


def main():
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="Export read-only control-room datasets; no paper runners execute.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--docs", action="store_true")
    action.add_argument("--changed", action="store_true")
    action.add_argument("--record", nargs="+")
    parser.add_argument("--generation", help="immutable export ID from --changed; required for --record")
    parser.add_argument("--jobs-state-dir", type=Path,
                        help="explicit external orchestrator status directory (read-only; optional)")
    args = parser.parse_args()
    if args.docs:
        return docs()
    if args.changed:
        return changed(args.generation)
    if args.record:
        return record(args.record, args.generation)
    sys.path.insert(0, str(ROOT))
    OUT.mkdir(parents=True, exist_ok=True)
    rnd = rounds()
    days = forward_days()
    sets = {"program": program(rnd), "rounds": rnd, "candidates": rows_csv(ROOT / "registry" / "candidates.csv"),
            "strategies": strategies(), "forward_lanes": forward_lanes(days), "forward_days": days,
            "event_tickets": event_tickets(), "methods": methods(), "data_sources": data_sources(), "jobs": jobs(args.jobs_state_dir)}
    from lab import registry
    from scripts import dashboard_perf as perf
    sets["tearsheets"], sets["equity"], sets["monthly"] = perf.tearsheets(
        days, registry.program_trials(str(ROOT / "registry" / "rounds.csv")))
    sets["leaderboard"] = perf.leaderboard(rnd, sets["strategies"])
    sets["coverage"] = perf.coverage()
    sets["funding_board"] = perf.funding_board()
    sets["factor_ic"] = perf.factor_ic()
    for r in sets["candidates"]:
        r["t"] = num(r["t"])
    manifest = publish_sets(sets, ISO(NOW))
    print("generation " + manifest["generation"] + " " +
          " ".join(f"{k} {v['rows']}" for k, v in manifest["sets"].items()))


if __name__ == "__main__":
    main()
