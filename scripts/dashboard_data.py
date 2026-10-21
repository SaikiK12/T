"""Export the lab's state as the dashboard's datasets: dashboard/data/<id>.json, one array of row objects each.

Read-only on the lab: the registry, the candidates watchlist, every family report and event-lane verdict, the forward
lanes' journals, the methods queue, the data folders and the loop's logs. It decides nothing; numbers are copied from
the files that hold them. The page (dashboard/index.html) is published to the Control Room artifact; each loop tick
re-runs this script and uploads the files whose hash changed (dashboard/data/manifest.json lists them).

usage: python scripts/dashboard_data.py            # export the datasets
       python scripts/dashboard_data.py --docs     # write the store documents (dashboard/data/docs/) for the
                                                  # urls in dashboard/data/uploaded.json and the page
       python scripts/dashboard_data.py --changed  # the datasets whose export differs from the uploaded copy
       python scripts/dashboard_data.py --record program=/_blob/<id> ...   # after uploading: remember the urls
                                                  # and write docs/<id>.update.json ({source, updated}) for each
Refresh in a loop tick: --changed, upload each listed file (Artifact publish, asset), --record the urls, then one
ArtifactData batch of `update` writes from docs/<id>.update.json pinned to the versions a `list datasets` shows.
"""
import csv
import hashlib
import json
import math
import os
import re
import shutil
import stat
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"
OUT = ROOT / "dashboard" / "data"
NOW = time.time()
ISO = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
# forward lanes: (registry id, lane, what it trades, venue, mode, rows needed for its decision, decision rule)
FORWARD = [
    ("R215", "mexc_fwd", "flow books A and B, one bar late", "MEXC", "API", 90,
     "R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate"),
    ("R218", "mexc_fwd_sq", "flow book X2 (k squared)", "MEXC", "API", 90,
     "R221: day 90 futility only; efficacy at 182/365 days; owner approval remains separate"),
    ("R220", "carry_fwd", "funding carry (R191 rule)", "MEXC + Binance", "manual-web", 90,
     "go_real at 90 on-time days"),
    ("R200", "flow72_fwd2", "flow books A and B", "Binance", "API", 90, "go_real at 90 scored days, NW t >= 2"),
    ("R214", "flow72_fwd3", "A and B one bar late (delay check)", "Binance", "API", 90, "same days as R200"),
    ("R225", "vt_fwd", "volatility target on A, B, X2", "MEXC", "API", 365,
     "risk-only decision at 365 on-time days; reported beside R215/R218"),
    ("R266", "unlocks_fwd", "unlock short, D-7 to unlock", "MEXC", "manual-web", 120, "120 scored tickets"),
    ("R268", "delist_fwd", "spot delisting-notice short +1 h", "MEXC", "API", 12, "12 scored notices"),
    ("R270", "montag_fwd", "Monitoring Tag short +24 h", "MEXC", "manual-web", 12, "12 scored notices"),
    ("R272", "announce_fwd", "funding-frequency long 1 h; pre-listing short 168 h", "MEXC", "API + manual-web", 12,
     "12 scored notices per book"),
    ("R278", "xfund_fwd", "cross-venue funding carry, books A, B, C", "Gate, Hyperliquid, Binance, MEXC",
     "manual-web", 90, "NW t >= 2.5 at 90 / 180 scored days, 2x > 0, drawdown above -3%"),
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
    sets = {"A": "Gate + Hyperliquid", "B": "Binance + MEXC", "C": "Gate + MEXC (post hoc)"}
    done = {(r["book"], r["day"], r["run"]) for r in rows_csv(EXP / "xfund_fwd" / "journal" / "decisions.csv")}
    for r in rows_csv(EXP / "xfund_fwd" / "journal" / "days.csv"):
        if (r["book"], r["day"], r["run"]) not in done:   # a run cut short; the lane ignores its rows too
            continue
        out.append({"key": f"xfund_fwd|{r['book']}|{r['day']}|{r['run']}", "day": r["day"], "round": "R278",
                    "lane": "xfund_fwd", "book": r["book"], "series": f"R278 {r['book']} {sets.get(r['book'], '')}",
                    "group": "Cross-venue funding carry", "kind": "ontime" if r["kind"] == "late" else r["kind"],
                    "net": num(r["net"]), "net_2x": num(r["net_2x"]), "net_3x": num(r["net_3x"])})
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
        daily = lane in {"mexc_fwd", "mexc_fwd_sq", "carry_fwd", "flow72_fwd2", "flow72_fwd3", "vt_fwd", "xfund_fwd"}
        by_book, progress_note = {}, None
        if daily:
            books = sorted({d["book"] for d in mine})
            scored = len({d["day"] for d in ontime})
            unit = "on-time days"
            tickets, open_ = len({d["day"] for d in mine}), None
            # Preserve unknown returns: no observations or any missing cost row means unknown aggregate.
            def total(column):
                values = [num(d.get(column)) for d in mine]
                return sum(values) / len(books) if values and all(v is not None for v in values) else None
            net, net2, net3 = (total(col) for col in ("net", "net_2x", "net_3x"))
        else:
            books = []
            scored = s.get("scored", s.get("scored_notices", 0)) or 0
            unit = "scored tickets" if lane == "unlocks_fwd" else "scored notices"
            tickets, open_ = s.get("tickets", 0), s.get("open", 0)
            net = num(s.get("mean_net"))
            net2 = num(s.get("mean_net_2x"))
            net3 = None
        if lane == "announce_fwd":
            books = ["FF", "PL"]
            for book in books:
                count = num((s.get("books", {}).get(book) or {}).get("scored_notices"))
                by_book[book] = int(count) if count is not None and count >= 0 and count.is_integer() else None
            # Two separate frozen decisions: 12 FF notices must not stand in for 12 PL notices.
            scored = min(by_book.values()) if all(v is not None for v in by_book.values()) else None
            unit = "scored notices per book (least observed book)"
            progress_note = "FF and PL each require 12 scored notices; progress is unknown if either count is absent."
        out.append({"round": rid, "lane": lane, "display_name": f"{what[:1].upper()}{what[1:]} · {venue}",
                    "what": what, "venue": venue, "mode": mode,
                    "books": " ".join(books) or None, "kind": "daily book" if daily else "event",
                    "tickets": tickets, "open": open_, "scored": scored, "needed": need, "unit": unit,
                    "progress": round(min(scored / need, 1), 4) if scored is not None else None,
                    "scored_by_book": by_book or None, "progress_note": progress_note,
                    "net_pct": None if net is None else net * 100,
                    "net_2x_pct": None if net2 is None else net2 * 100,
                    "net_3x_pct": None if net3 is None else net3 * 100,
                    "decision": s.get("decision") or rule, "updated_at": at, "age_h": age})
    return out


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
    fresh_h = {"live": 2, "recorders": 2, "mexc": 2, "logs": 2, "hyperliquid": 26}
    labels = {
        "mexc": ("MEXC forward-data cache", "Prospective collection"),
        "mexc_hist": ("MEXC historical futures", "Historical market data"),
        "recorders": ("Point-in-time exchange and event snapshots", "Prospective collection"),
        "live": ("Live market observations", "Prospective collection"),
        "logs": ("Collector and scheduler logs", "Operational logs"),
        "hyperliquid": ("Hyperliquid observations", "Prospective collection"),
        "klines_1h": ("Binance hourly perpetual candles", "Historical market data"),
        "fundingRate": ("Binance settled funding", "Historical market data"),
        "metrics_1h": ("Binance hourly positioning metrics", "Historical market data"),
        "spot_1h": ("Hourly spot candles", "Historical market data"),
        "coinm_1h": ("Coin-margined futures candles", "Historical market data"),
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


def docs():
    """The dashboard store's documents: one dataset per exported file, at the url its upload returned, and the page."""
    urls = json.loads((OUT / "uploaded.json").read_text())
    man = json.loads((OUT / "manifest.json").read_text())
    d = OUT / "docs"
    d.mkdir(exist_ok=True)
    for k, url in urls.items():
        title, desc = TITLES[k]
        doc = {"title": title,
               "description": desc + " Exported by scripts/dashboard_data.py from the lab's repository.",
               "source": {"kind": "file", "url": url, "name": f"{k}.json"},
               "updated": {"at": man["generated_at"], "by": "Claude (lab loop)"},
               "schedule": "Re-exported from the lab repository by the hourly loop tick", "staleAfterHours": 6}
        (d / f"{k}.json").write_text(json.dumps(doc))
    (d / "index.html.json").write_text(json.dumps({"text": (ROOT / "dashboard" / "index.html").read_text()}))
    print(f"{len(urls)} dataset docs and the page in {d.relative_to(ROOT)}")


def changed():
    man = json.loads((OUT / "manifest.json").read_text())["sets"]
    up = read_json(OUT / "uploaded_sha.json")
    print(json.dumps({k: str(ROOT / v["file"]) for k, v in man.items() if up.get(k) != v["sha256"]}))


def record(pairs):
    man = json.loads((OUT / "manifest.json").read_text())
    urls, shas = read_json(OUT / "uploaded.json"), read_json(OUT / "uploaded_sha.json")
    (OUT / "docs").mkdir(exist_ok=True)
    for pair in pairs:
        k, url = pair.split("=", 1)
        urls[k], shas[k] = url, man["sets"][k]["sha256"]
        upd = {"source": {"kind": "file", "url": url, "name": f"{k}.json"},
               "updated": {"at": man["generated_at"], "by": "Claude (lab loop)"}}
        (OUT / "docs" / f"{k}.update.json").write_text(json.dumps(upd))
    (OUT / "uploaded.json").write_text(json.dumps(urls, indent=1))
    (OUT / "uploaded_sha.json").write_text(json.dumps(shas, indent=1))
    print(f"recorded {len(pairs)} uploads")


def main():
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="Export read-only control-room datasets; no paper runners execute.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--docs", action="store_true")
    action.add_argument("--changed", action="store_true")
    action.add_argument("--record", nargs="+")
    parser.add_argument("--jobs-state-dir", type=Path,
                        help="explicit external orchestrator status directory (read-only; optional)")
    args = parser.parse_args()
    if args.docs:
        return docs()
    if args.changed:
        return changed()
    if args.record:
        return record(args.record)
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
