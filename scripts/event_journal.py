"""Shared engine of the point-in-time event recorders (record_listings.py, record_tradfi_calendar.py). Not run itself.

A source is polled on a fixed interval; its parsed items (key -> flat dict of raw string fields) are compared with the
state replayed from the journal, and only differences are appended to <folder>/events.csv:

    baseline  first sight of a key in a source's first poll (NOT a true first-seen time: the key may be older)
    new       key absent from the replayed state, source already had a baseline
    gone      key present before and missing now (only if the source tracks it and the poll covers that key)
    back      key returns after `gone`
    change    one row per field whose raw value differs (old, new, and the source's own field name in src_field)

Event poll_utc/poll_ms record the local observation time after fetch/parse, never the start of a slow request.
These local times are NOT a verified UTC clock or durable-publication/deadline evidence. Rows produced before this
fix used pass-start time and must not be reinterpreted as response-availability times; old rows are never rewritten.
Poll-attempt rows are stamped on completion; bucket and monthly file still identify the scheduled poll interval.
Every row carries the source's own field name (src_field), the source's own event
time as given (event_time_field/event_time_raw) with a derived UTC column where the clock is unambiguous, and the raw
field values (snapshot) for rows that open or close a key. The journal is the only state: nothing else has to survive
for the diff to be right, and a repeated poll writes nothing.

<folder>/polls_<YYYYMM>.csv holds one row per attempt (ok or error) so a quiet stretch can be told from a dead recorder;
the poll bucket (floor(time / interval)) makes a second run in the same interval a no-op without a request.
Append-only; one writer at a time (recorder.lock). Data collection only: public GETs, no key, no login, no contact data.
"""
import csv
import fcntl
import gzip
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

EVENT_COLS = ("poll_utc", "poll_ms", "source", "key", "event", "field", "old", "new", "src_field",
              "event_time_field", "event_time_raw", "event_time_utc", "snapshot")
POLL_COLS = ("poll_utc", "poll_ms", "source", "bucket", "interval_s", "ok", "items", "baseline", "new", "back", "gone",
             "change", "elapsed_ms", "error")
UA = "lab/1"                      # no contact data, no browser disguise
MIN_FREE_GB = 2.0                 # stop (and `ensure` will not start) below this
MAX_FOLDER_MB = 400.0             # hard cap for one recorder folder; far above the expected few MB a day
PACE_S = 1.5                      # pause between two sources of one pass
LOOP_S = 20.0                     # the daemon looks for due sources this often
MAX_TRIES = 3                     # attempts per source and bucket when the request fails
RETRY_S = 60.0                    # wait after a failed attempt in the same bucket
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def utc(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def text(v):
    """Raw value as stored: strings as given, None -> '', bool -> true/false, lists/dicts -> compact JSON."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return str(v)


def epoch_utc(raw, unit_ms=True):
    """UTC string for an epoch (ms or s) as the source gave it, '' when it is empty, zero or not a number."""
    try:
        x = float(raw)
    except (TypeError, ValueError):
        return ""
    if x <= 0:
        return ""
    return utc(x / 1000 if unit_ms else x)


def http_get(url, body=None, timeout=30, headers=None):
    """One public request (POST with a JSON body when `body` is given); gzip accepted. Returns the raw bytes."""
    h = {"User-Agent": UA, "Accept-Encoding": "gzip", "Accept": "application/json, */*"}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw


@dataclass
class Source:
    """name; interval_s; fetch(now_s) -> (items, covered) with items = {key: {"fields": {name: str}, "etime":
    (field, raw, utc)}} and covered(fields) -> bool (None: every known key is covered by this poll);
    key_field: the source's own name for the key; src_map: field name -> the source's own key for it."""
    name: str
    interval_s: int
    fetch: Callable
    key_field: str = ""
    src_map: Optional[dict] = None
    track_gone: bool = True
    guard: bool = True            # refuse `gone` rows when the list shrank below half (a failed or truncated reply)


class Suspicious(Exception):
    pass


def snap(fields):
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Journal:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.events = self.folder / "events.csv"

    def polls_path(self, t):
        return self.folder / f"polls_{time.strftime('%Y%m', time.gmtime(t))}.csv"

    # ---- state: replay of the journal -------------------------------------------------------------------------
    def state(self):
        st = {}
        if not self.events.exists():
            return st
        with open(self.events, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                s = st.setdefault(r["source"], {})
                k, ev = r["key"], r["event"]
                if ev in ("baseline", "new", "back"):
                    s[k] = {"present": True, "fields": json.loads(r["snapshot"] or "{}")}
                elif ev == "gone":
                    s.setdefault(k, {"present": False, "fields": {}})["present"] = False
                elif ev == "change":
                    e = s.setdefault(k, {"present": True, "fields": {}})
                    e["fields"][r["field"]] = r["new"]
        return st

    def attempts(self, source, bucket, now_s):
        """(ok_seen, failures, last_failure_s) for this source and bucket, from the tail of this month's polls file."""
        p = self.polls_path(now_s)
        ok, fails, last = False, 0, 0.0
        if not p.exists():
            return ok, fails, last
        with open(p, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 200_000))
            tail = f.read().decode("utf-8", "replace").splitlines()
        for line in tail:
            try:
                r = next(csv.reader([line]))
            except (csv.Error, StopIteration):
                continue
            if len(r) != len(POLL_COLS) or r[2] != source or r[3] != str(bucket):
                continue
            if r[5] == "1":
                ok = True
            else:
                fails += 1
                last = max(last, float(r[1]) / 1000)
        return ok, fails, last

    # ---- diff -------------------------------------------------------------------------------------------------
    def diff(self, src, items, covered, known, now_s):
        """Rows (EVENT_COLS dicts) that turn `known` (one source's replayed state) into `items`."""
        ts, ms = utc(now_s), int(now_s * 1000)
        smap = src.src_map or {}
        rows = []

        def row(key, event, et, field="", old="", new="", src_field="", snapshot=""):
            return {"poll_utc": ts, "poll_ms": ms, "source": src.name, "key": key, "event": event, "field": field,
                    "old": old, "new": new, "src_field": src_field, "event_time_field": et[0],
                    "event_time_raw": et[1], "event_time_utc": et[2], "snapshot": snapshot}

        first = not known
        for key, it in items.items():
            et = it.get("etime") or ("", "", "")
            fields = it["fields"]
            cur = known.get(key)
            if cur is None:
                rows.append(row(key, "baseline" if first else "new", et, src_field=src.key_field, snapshot=snap(fields)))
            elif not cur["present"]:
                rows.append(row(key, "back", et, src_field=src.key_field, snapshot=snap(fields)))
            else:
                for f in sorted(set(cur["fields"]) | set(fields)):
                    o, n = cur["fields"].get(f, ""), fields.get(f, "")
                    if o != n:
                        rows.append(row(key, "change", et, f, o, n, smap.get(f, f)))
        if src.track_gone:
            for key, cur in known.items():
                if cur["present"] and key not in items and (covered is None or covered(cur["fields"])):
                    rows.append(row(key, "gone", ("", "", ""), src_field=src.key_field, snapshot=snap(cur["fields"])))
        return rows

    # ---- append (single writer) --------------------------------------------------------------------------------
    def _append(self, path, cols, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        w = csv.DictWriter(buf, cols, lineterminator="\n")
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            if os.fstat(fd).st_size == 0:
                w.writeheader()
            w.writerows(rows)
            os.write(fd, buf.getvalue().encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def append_events(self, rows):
        if rows:
            self._append(self.events, EVENT_COLS, rows)

    def append_poll(self, row, now_s):
        self._append(self.polls_path(now_s), POLL_COLS, [row])

    def size_mb(self):
        return sum(p.stat().st_size for p in self.folder.glob("*.csv")) / 1e6 if self.folder.exists() else 0.0


def disk_problem(folder, journal):
    ancestor = Path(folder)
    while not ancestor.exists():
        ancestor = ancestor.parent
    free = shutil.disk_usage(ancestor).free / 1e9
    if free < MIN_FREE_GB:
        return f"free disk {free:.1f} GB < {MIN_FREE_GB} GB"
    if journal.size_mb() > MAX_FOLDER_MB:
        return f"{journal.folder} holds {journal.size_mb():.0f} MB > {MAX_FOLDER_MB:.0f} MB"
    return ""


def poll_one(journal, src, now_s, force=False, state=None):
    """One poll of one source. Returns a summary dict; never raises for a source error (it is logged in polls)."""
    bucket = int(now_s // src.interval_s)
    if not force:
        ok, fails, last = journal.attempts(src.name, bucket, now_s)
        if ok:
            return {"source": src.name, "status": "skip", "why": "polled this interval"}
        if fails >= MAX_TRIES or (fails and now_s - last < RETRY_S):
            return {"source": src.name, "status": "skip", "why": f"{fails} failed tries this interval"}
    t0, mono0 = time.time(), time.monotonic()
    counts = {k: 0 for k in ("baseline", "new", "back", "gone", "change")}
    try:
        items, covered = src.fetch(now_s)
        if not items and src.guard:
            raise Suspicious("empty list")
        known = (state if state is not None else journal.state()).get(src.name, {})
        if src.track_gone and src.guard:
            prev = [k for k, v in known.items() if v["present"] and (covered is None or covered(v["fields"]))]
            if len(prev) >= 5 and len(items) < len(prev) / 2:
                raise Suspicious(f"list shrank {len(prev)} -> {len(items)}")
        observed_s = time.time()
        if observed_s < t0:
            raise Suspicious("local wall clock moved backwards during poll")
        rows = journal.diff(src, items, covered, known, observed_s)
        journal.append_events(rows)
        for r in rows:
            counts[r["event"]] += 1
        err = ""
    except Exception as e:  # noqa: BLE001  (one bad source must not stop the others)
        rows, items, err = [], {}, f"{type(e).__name__}: {e}"[:200].replace("\n", " ")
    finished_s = time.time()
    journal.append_poll({"poll_utc": utc(finished_s), "poll_ms": int(finished_s * 1000), "source": src.name, "bucket": bucket,
                         "interval_s": src.interval_s, "ok": 0 if err else 1, "items": len(items), **counts,
                         "elapsed_ms": int((time.monotonic() - mono0) * 1000), "error": err}, now_s)
    return {"source": src.name, "status": "error" if err else "ok", "items": len(items), "error": err, **counts}


def poll_all(journal, sources, now_s=None, force=False, only=None, pace=None):
    """One pass: every due source once, in order, `pace` seconds apart. Returns the summaries."""
    now_s = time.time() if now_s is None else now_s
    pace = PACE_S if pace is None else pace
    why = disk_problem(journal.folder, journal)
    if why:
        log("not recording:", why)
        return [{"source": "*", "status": "stopped", "why": why}]
    out, fetched = [], 0
    state = journal.state()
    for src in sources:
        if only and src.name not in only:
            continue
        if fetched and pace:
            time.sleep(pace)
        s = poll_one(journal, src, now_s, force, state)
        if s["status"] != "skip":
            fetched += 1
            state = journal.state()           # the next source may share nothing, but keep the replay honest
        out.append(s)
    write_status(journal, sources, out, now_s)
    return out


def write_status(journal, sources, summaries, now_s):
    p = journal.folder / "status.json"
    try:
        cur = json.loads(p.read_text()) if p.exists() else {}
    except (OSError, json.JSONDecodeError):
        cur = {}
    cur["updated_utc"] = utc(now_s)
    cur["pid"] = os.getpid()
    src = cur.setdefault("sources", {})
    for s in summaries:
        if s["source"] == "*" or s["status"] == "skip":
            continue
        d = src.setdefault(s["source"], {})
        d["last_poll_utc"] = utc(now_s)
        d["last_status"] = s["status"]
        if s["status"] == "ok":
            d["last_ok_utc"] = utc(now_s)
            d["items"] = s["items"]
        else:
            d["last_error"] = s["error"]
    journal.folder.mkdir(parents=True, exist_ok=True)
    tmp = journal.folder / "status.json.tmp"
    tmp.write_text(json.dumps(cur, indent=1, sort_keys=True))
    tmp.replace(p)


def lock(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)
    f = open(Path(folder) / "recorder.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def cli(name, folder, sources, script, argv=None):
    """usage: <script> [ensure|run [--once] [--force] [--only a,b]|status]   (default: ensure)

    ensure  start the daemon (`run`) if none holds the lock; does nothing if one does or the disk is short
    run     poll every due source each LOOP_S forever; --once: one pass and exit; --force: ignore the per-interval
            skip (the diff still writes nothing twice); --only: comma list of sources
    status  print status.json
    """
    argv = list(sys.argv[1:] if argv is None else argv) or ["ensure"]
    cmd, rest = argv[0], argv[1:]
    folder = Path(folder)
    j = Journal(folder)
    if cmd == "status":
        p = folder / "status.json"
        print(p.read_text() if p.exists() else "no status yet")
        return 0
    if cmd == "ensure":
        why = disk_problem(folder, j)
        if why:
            log(f"{name} recorder not started:", why)
            return 1
        held = lock(folder)
        if held is None:
            log(f"{name} recorder running")
            return 0
        held.close()
        logf = open(folder / "recorder.log", "a")
        subprocess.Popen([sys.executable, str(Path(script).resolve()), "run"], cwd=Path(script).resolve().parent.parent,
                         stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        log(f"{name} recorder started")
        return 0
    if cmd != "run":
        print(cli.__doc__)
        return 2
    only = set(rest[rest.index("--only") + 1].split(",")) if "--only" in rest else None
    held = lock(folder)
    if held is None:
        log(f"another {name} recorder holds {folder}/recorder.lock")
        return 1
    if "--once" in rest:
        for s in poll_all(j, sources, force="--force" in rest, only=only):
            log(name, json.dumps(s, sort_keys=True))
        return 0
    stop = {"now": False}
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.update(now=True))
    log(f"recording {len(sources)} sources, due ones every {LOOP_S:.0f} s")
    while not stop["now"]:
        for s in poll_all(j, sources, only=only):
            if s["status"] in ("ok", "error", "stopped"):
                log(name, json.dumps(s, sort_keys=True))
            if s["status"] == "stopped":
                return 1
        t_end = time.time() + LOOP_S
        while time.time() < t_end and not stop["now"]:
            time.sleep(1.0)
    return 0
