"""Export the lab's state as the dashboard's datasets: dashboard/data/<id>.json, one array of row objects each.

Read-only on the lab: the registry, the candidates watchlist, every family report and event-lane verdict, the forward
lanes' journals, the methods queue, the data folders and the loop's logs. It decides nothing; numbers are copied from
the files that hold them. The page (dashboard/index.html) is published to the Control Room artifact; each loop tick
re-runs this script and uploads the files whose hash changed (dashboard/data/manifest.json lists them).

usage: python scripts/dashboard_data.py            # export the datasets
       python scripts/dashboard_data.py --docs     # write the store documents (dashboard/data/docs/) for the
                                                  # urls in dashboard/data/uploaded.json and the page
"""
import csv
import hashlib
import json
import math
import os
import re
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"
OUT = ROOT / "dashboard" / "data"
NOW = time.time()
ISO = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
# forward lanes: (registry id, lane, what it trades, venue, mode, rows needed for its decision, decision rule)
FORWARD = [
    ("R215", "mexc_fwd", "flow books A and B, one bar late", "MEXC", "API", 90, "go_real at 90 on-time days"),
    ("R218", "mexc_fwd_sq", "flow book X2 (k squared)", "MEXC", "API", 90, "go_real at 90 on-time days"),
    ("R220", "carry_fwd", "funding carry (R191 rule)", "MEXC + Binance", "manual-web", 90, "go_real at 90 on-time days"),
    ("R200", "flow72_fwd2", "flow books A and B", "Binance", "API", 90, "go_real at 90 scored days, NW t >= 2"),
    ("R214", "flow72_fwd3", "A and B one bar late (delay check)", "Binance", "API", 90, "same days as R200"),
    ("R225", "vt_fwd", "volatility target on A, B, X2", "MEXC", "API", 90, "reported beside R215/R218"),
    ("R266", "unlocks_fwd", "unlock short, D-7 to unlock", "MEXC", "manual-web", 120, "120 scored tickets"),
    ("R268", "delist_fwd", "spot delisting-notice short +1 h", "MEXC", "API", 12, "12 scored notices"),
    ("R270", "montag_fwd", "Monitoring Tag short +24 h", "MEXC", "manual-web", 12, "12 scored notices"),
]


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
    return [{"generated_at": ISO(NOW), "program_trials": trials, "rounds": len(rnd), "null": count("NULL"),
             "partial": count("PARTIAL"), "confirmed": count("CONFIRMED"),
             "running": sum(r["status"] in ("RUNNING", "ARMED") for r in rnd),
             "strict_ontime_days": lag.get("strict_ontime_days", 0), "candidates": len(cand),
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


def strategies():
    """Every strategy with per-event stats on file: qx family reports and the event lanes' variants."""
    rids, out = rid_by_path(), []
    for rep_path in sorted(EXP.glob("*/results/report.json")):
        lane = rep_path.parent.parent.name
        rid = rids.get(f"experiments/{lane}")
        rep = read_json(rep_path)
        if not rid or "strategies" not in rep:
            continue
        for s in rep["strategies"]:
            st = s["stats"]
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
                ok = primary and v.get("verdict") not in ("NULL", None)
                out.append(stat_row(rid, lane, lane, re.sub(r"^\d+:\s*", "", k), var, None, null_p, ok, nv))
        elif isinstance(v.get("primary"), dict) and "1x" in v["primary"]:
            out.append(stat_row(rid, lane, lane, "primary", v["primary"], None, (v.get("null") or {}).get("p"),
                                v.get("verdict") in ("REPLICATES", "PASS", "CONFIRMED"), v.get("trials")))
    return out


def lane_age(lane):
    p = EXP / lane / "journal" / "status.json"
    return (round((NOW - p.stat().st_mtime) / 3600, 2), ISO(p.stat().st_mtime)) if p.exists() else (None, None)


def forward_days():
    """One row per lane, book and day: the daily books' paper net at 1x/2x/3x, replay or on-time."""
    out = []
    spec = {"flow72_fwd2": ("R200", "net", "Binance flow books"), "flow72_fwd3": ("R214", "net", "Binance flow books"),
            "mexc_fwd": ("R215", "net", "MEXC flow books"), "mexc_fwd_sq": ("R218", "net", "MEXC flow books"),
            "carry_fwd": ("R220", "net", "Funding carry")}
    for lane, (rid, col, group) in spec.items():
        for r in rows_csv(EXP / lane / "journal" / "tickets.csv"):
            kind = r.get("kind") or ("replay" if r.get("late") == "1" else "ontime")
            out.append({"key": f"{lane}|{r['book']}|{r['day']}", "day": r["day"], "round": rid, "lane": lane,
                        "book": r["book"], "series": f"{rid} {r['book']}", "group": group, "kind": kind,
                        "net": num(r[col]),
                        "net_2x": num(r.get("net_2x")), "net_3x": num(r.get("net_3x"))})
    for r in rows_csv(EXP / "vt_fwd" / "journal" / "days.csv"):
        out.append({"key": f"vt_fwd|{r['book']}|{r['day']}", "day": r["day"], "round": "R225", "lane": "vt_fwd",
                    "book": r["book"], "series": f"R225 {r['book']}", "group": "Volatility-targeted (MEXC)",
                    "kind": r["kind"],
                    "net": num(r["net_vt"]), "net_2x": num(r["net_vt_2x"]), "net_3x": num(r["net_vt_3x"])})
    return sorted(out, key=lambda r: (r["series"], r["day"]))


def forward_lanes(days):
    out = []
    for rid, lane, what, venue, mode, need, rule in FORWARD:
        s = read_json(EXP / lane / "journal" / "status.json")
        age, at = lane_age(lane)
        mine = [d for d in days if d["lane"] == lane]
        ontime = [d for d in mine if d["kind"] == "ontime"]
        if mine:
            books = sorted({d["book"] for d in mine})
            scored = len({d["day"] for d in ontime})
            unit = "on-time days"
            tickets, open_ = len({d["day"] for d in mine}), None
            net = sum(d["net"] or 0 for d in mine) / max(len(books), 1)
            net2 = sum(d["net_2x"] or 0 for d in mine) / max(len(books), 1)
            net3 = sum(d["net_3x"] or 0 for d in mine) / max(len(books), 1)
        else:
            books = []
            scored = s.get("scored", s.get("scored_notices", 0)) or 0
            unit = "scored tickets" if lane == "unlocks_fwd" else "scored notices"
            tickets, open_ = s.get("tickets", 0), s.get("open", 0)
            net = num(s.get("mean_net"))
            net2 = num(s.get("mean_net_2x"))
            net3 = None
        out.append({"round": rid, "lane": lane, "what": what, "venue": venue, "mode": mode,
                    "books": " ".join(books) or None, "kind": "daily book" if mine else "event",
                    "tickets": tickets, "open": open_, "scored": scored, "needed": need, "unit": unit,
                    "progress": round(min(scored / need, 1), 4), "net_pct": None if net is None else net * 100,
                    "net_2x_pct": None if net2 is None else net2 * 100,
                    "net_3x_pct": None if net3 is None else net3 * 100,
                    "decision": s.get("decision") or rule, "updated_at": at, "age_h": age})
    return out


def event_tickets():
    out = []
    u = read_json(EXP / "unlocks_fwd" / "journal" / "status.json")
    for r in rows_csv(EXP / "unlocks_fwd" / "journal" / "tickets.csv"):
        out.append({"key": r["ticket"], "round": "R266", "lane": "unlocks_fwd", "symbol": r["contract"],
                    "entry_at": ISO(int(r["entry_ms"]) / 1000), "exit_at": ISO(int(r["exit_ms"]) / 1000),
                    "state": "open" if int(r["entry_ms"]) / 1000 <= NOW else "frozen, not entered",
                    "size_pct_supply": num(r["frac_max_supply"]) * 100 if num(r["frac_max_supply"]) else None,
                    "net_pct": None})
    for e in u.get("next_entries", []):
        at, sym = e.split(" ", 1)
        key = f"next {sym} {at[:10]}"
        if not any(sym in t["symbol"] and t["entry_at"][:10] == at[:10] for t in out):
            out.append({"key": key, "round": "R266", "lane": "unlocks_fwd", "symbol": sym, "entry_at": at,
                        "exit_at": None, "state": "upcoming on the calendar", "size_pct_supply": None, "net_pct": None})
    for lane, rid in (("delist_fwd", "R268"), ("montag_fwd", "R270")):
        for r in rows_csv(EXP / lane / "journal" / "tickets.csv"):
            net = num(r.get("net_1x", r.get("net")))
            out.append({"key": r["ticket"], "round": rid, "lane": lane, "symbol": r.get("contract"),
                        "entry_at": ISO(int(r["entry_ms"]) / 1000), "exit_at": ISO(int(r["exit_ms"]) / 1000),
                        "state": "scored" if net is not None else "open", "size_pct_supply": None,
                        "net_pct": None if net is None else net * 100})
    return sorted(out, key=lambda r: r["entry_at"] or "")


def methods():
    out = []
    for r in rows_csv(ROOT / "registry" / "methods.csv"):
        out.append({"id": r["id"], "method": r["method"][:200], "status": r["status"], "data_held": r["data_held"],
                    "cheap": r["cheap"], "round": r.get("rid") or None, "source": r.get("source") or None})
    return out


def data_sources():
    prov = {p.stem for p in (ROOT / "docs" / "provenance").glob("*.json")}
    fresh_h = {"live": 2, "recorders": 2, "mexc": 2, "logs": 2, "hyperliquid": 26}
    out = []
    for d in sorted((ROOT / "data").iterdir()):
        if not d.is_dir():
            continue
        n = size = newest = 0
        for dp, _, fn in os.walk(d):
            for f in fn:
                st = os.stat(os.path.join(dp, f))
                n, size, newest = n + 1, size + st.st_size, max(newest, st.st_mtime)
        age = round((NOW - newest) / 3600, 1) if newest else None
        limit = fresh_h.get(d.name)
        out.append({"source": d.name, "files": n, "size_gb": round(size / 1e9, 3), "newest_at": ISO(newest) if newest else None,
                    "age_h": age, "kind": "recorded live" if limit else "archive download",
                    "stale": bool(limit and age is not None and age > limit), "provenance": d.name in prov})
    return out


def jobs():
    """What the loop and the background jobs are doing: running processes and each lane's last tick."""
    out = []
    try:
        procs = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        procs = []
    for p in procs:
        try:
            cmd = Path(f"/proc/{p}/cmdline").read_bytes().replace(b"\0", b" ").decode().strip()
            start = Path(f"/proc/{p}").stat().st_mtime
        except OSError:
            continue
        m = re.search(r"scripts/(\S+\.(?:py|sh))", cmd)
        if m and "dashboard_data" not in cmd:
            out.append({"key": f"{m.group(1)} pid {p}", "job": m.group(1), "kind": "background job", "state": "running",
                        "at": ISO(start), "age_h": round((NOW - start) / 3600, 2), "ok": True, "note": f"pid {p}"})
    for lane in sorted({f[1] for f in FORWARD}):
        log = EXP / lane / "tick.log"
        if not log.exists():
            continue
        tail = log.read_text(errors="replace").splitlines()[-30:]
        bad = [l for l in tail if re.search(r"Traceback|Error|FAILED", l)]
        age = round((NOW - log.stat().st_mtime) / 3600, 2)
        out.append({"key": lane, "job": lane, "kind": "forward tick",
                    "state": "error in last lines" if bad else "ticked", "at": ISO(log.stat().st_mtime), "age_h": age, "ok": not bad and age < 2,
                    "note": (bad[-1] if bad else (tail[-1] if tail else ""))[:160]})
    return out


TITLES = {
    "program": ("Lab program summary", "One row: program trials (lab.registry.program_trials), rounds by verdict, "
                "watchlist size, strict on-time paper days, the next due date and free disk."),
    "rounds": ("Registered rounds", "Every round in registry/rounds.csv with its verdict and trial count."),
    "candidates": ("Candidate watchlist", "registry/candidates.csv: each edge still alive, its best evidence, its "
                   "funnel stage and what decides it next."),
    "strategies": ("Tested event strategies", "Per-event stats at 1x/2x/3x cost for every strategy in a qx family "
                   "report or an event lane's verdict (experiments/*/results)."),
    "forward_lanes": ("Forward paper lanes", "Each forward paper lane's progress toward its decision and its paper net, "
                      "from its journal."),
    "forward_days": ("Daily paper returns", "Net return per day at 1x/2x/3x cost for each daily book, replayed or "
                     "traded on time, from the forward journals."),
    "event_tickets": ("Event tickets", "Unlock, delisting and Monitoring Tag paper tickets, and the unlocks next on "
                      "the recorded calendar."),
    "methods": ("Method queue", "registry/methods.csv: every method from the literature, old sessions and both AIs, "
                "with its status."),
    "data_sources": ("Data folders", "Size, newest file and provenance note of each folder under data/."),
    "jobs": ("Loop and jobs", "Running background processes and each forward lane's last tick."),
}


def docs():
    """The dashboard store's documents: one dataset per exported file, at the url its upload returned, and the page."""
    urls = json.loads((OUT / "uploaded.json").read_text())
    man = json.loads((OUT / "manifest.json").read_text())
    d = OUT / "docs"
    d.mkdir(exist_ok=True)
    for k, url in urls.items():
        title, desc = TITLES[k]
        doc = {"title": title, "description": desc + " Exported by scripts/dashboard_data.py from the lab's repository.",
               "source": {"kind": "file", "url": url, "name": f"{k}.json"},
               "updated": {"at": man["generated_at"], "by": "Claude (lab loop)"},
               "schedule": "Re-exported from the lab repository by the hourly loop tick", "staleAfterHours": 6}
        (d / f"{k}.json").write_text(json.dumps(doc))
    (d / "index.html.json").write_text(json.dumps({"text": (ROOT / "dashboard" / "index.html").read_text()}))
    print(f"{len(urls)} dataset docs and the page in {d.relative_to(ROOT)}")


def main():
    import sys
    if "--docs" in sys.argv:
        return docs()
    sys.path.insert(0, str(ROOT))
    OUT.mkdir(parents=True, exist_ok=True)
    rnd = rounds()
    days = forward_days()
    sets = {"program": program(rnd), "rounds": rnd, "candidates": rows_csv(ROOT / "registry" / "candidates.csv"),
            "strategies": strategies(), "forward_lanes": forward_lanes(days), "forward_days": days,
            "event_tickets": event_tickets(), "methods": methods(), "data_sources": data_sources(), "jobs": jobs()}
    for r in sets["candidates"]:
        r["t"] = num(r["t"])
    manifest = {}
    for k, rows in sets.items():
        p = OUT / f"{k}.json"
        body = json.dumps(rows, separators=(",", ":"), default=str)
        p.write_text(body)
        manifest[k] = {"file": str(p.relative_to(ROOT)), "rows": len(rows),
                       "sha256": hashlib.sha256(body.encode()).hexdigest()}
    (OUT / "manifest.json").write_text(json.dumps({"generated_at": ISO(NOW), "sets": manifest}, indent=1))
    print(" ".join(f"{k} {v['rows']}" for k, v in manifest.items()))


if __name__ == "__main__":
    main()
