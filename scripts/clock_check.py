"""Local clock check against three public exchange clocks, and a gradual correction (data collection support only).

The recorders stamp recv_ms from this machine's wall clock. After the container restarts of 2026-10-29 the clock ran slow
(about 100 ppm, 1.8 s by 10:20 UTC) and nothing disciplined it, so every local receipt time and lag_ms was early by that
much. This script measures the offset and, on request, removes it with adjtime(), which slews at most 500 ppm and never
steps the clock, so no running recorder sees a jump.

offset = exchange time - local time at the request midpoint, so a positive offset means this clock is behind. Each venue
contributes its lowest-round-trip sample; the median over venues is used, and nothing is applied unless the venues agree.

A round trip is timed on the monotonic clock, and a sample whose wall-clock interval disagrees with it (a step of the wall
clock during the request) or whose interval is not positive is dropped. Two runs never overlap (lock file).

usage: python scripts/clock_check.py status | slew [--min-ms 250] [--max-ms 10000]
Every run appends one row to experiments/recorders/journal/clock_check_v2.csv (committed, so the offset at an event is on
record): local time, an estimated time, the median offset, which venues were used, half the longest round trip used
and each venue's offset and round trip. The legacy column name bound_ms is a network-delay diagnostic, not a verified
UTC error bound; server accuracy, caching, source disagreement and drift between samples are not certified. Rows before
2026-10-29 13:50 UTC are in clock_check.csv, which has
fewer columns and is no longer written. Only this script writes these files.
"""
import argparse
import ctypes
import fcntl
import json
import math
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "experiments" / "recorders" / "journal" / "clock_check_v2.csv"
LOCK = ROOT / "data" / "logs" / "clock_check.lock"
SAMPLES = 6
AGREE_MS = 500          # the venues' offsets must lie within this of each other
MAX_RTT_MS = 450        # a sample with a longer round trip is too noisy (error up to half of it) and is not used
PENDING_TOL_MS = 400    # a new offset this far from the adjustment still pending is taken as a bad measurement
STEP_TOL_MS = 25        # wall-clock and monotonic intervals of one request may differ by this much (slew is ~0.2 ms)
VENUES = {
    "mexc": ("https://contract.mexc.com/api/v1/contract/ping", lambda j: int(j["data"])),
    "deribit": ("https://www.deribit.com/api/v2/public/get_time", lambda j: int(j["result"])),
    "okx": ("https://www.okx.com/api/v5/public/time", lambda j: int(j["data"][0]["ts"])),
}


def wall_ms():
    return time.time_ns() / 1e6


def mono_ms():
    return time.monotonic_ns() / 1e6


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "T-clock-check/1", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def venue_offset(url, parse, samples=SAMPLES, get=fetch_json, clock_ms=wall_ms, mono=mono_ms):
    """(offset_ms, rtt_ms) of the lowest-round-trip sample; rtt is the monotonic elapsed time. A sample is dropped when
    the request failed, when its monotonic interval is not a positive finite number, or when the wall clock moved by a
    different amount (a step during the request). Raises when no sample is left."""
    best = None
    for _ in range(samples):
        t0, m0 = clock_ms(), mono()
        try:
            srv = parse(get(url))
        except Exception:
            continue
        t1, m1 = clock_ms(), mono()
        rtt = m1 - m0
        if (not isinstance(srv, (int, float)) or isinstance(srv, bool) or not math.isfinite(srv)
                or not math.isfinite(rtt) or rtt <= 0 or not math.isfinite(t1 - t0)
                or abs((t1 - t0) - rtt) > STEP_TOL_MS):
            continue
        cand = (srv - (t0 + rtt / 2), rtt)
        if best is None or cand[1] < best[1]:
            best = cand
    if best is None:
        raise RuntimeError(f"no sample from {url}")
    return best


def measure(venues=VENUES, **kw):
    """{venue: (offset_ms, rtt_ms)} for the venues that answer."""
    out = {}
    for name, (url, parse) in venues.items():
        try:
            out[name] = venue_offset(url, parse, **kw)
        except RuntimeError:
            pass
    return out


def usable(res, max_rtt_ms=MAX_RTT_MS):
    """The venues whose round trip is a positive, finite time of at most max_rtt_ms."""
    return {k: v for k, v in res.items()
            if all(math.isfinite(x) for x in v) and 0 < v[1] <= max_rtt_ms}


def consensus(res, agree_ms=AGREE_MS, max_rtt_ms=MAX_RTT_MS):
    """(median offset ms, ok): ok needs at least two venues with a round trip of at most max_rtt_ms, within agree_ms of
    each other."""
    use = usable(res, max_rtt_ms)
    if len(use) < 2:
        offs = [o for o, _ in res.values() if math.isfinite(o)]
        return (statistics.median(offs) if offs else float("nan")), False
    offs = [o for o, _ in use.values()]
    return statistics.median(offs), max(offs) - min(offs) <= agree_ms


def adjtime_ms(delta_ms):
    """Slew the system clock by delta_ms (positive: advance it). Replaces any adjustment still pending."""
    class Timeval(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]
    sec, usec = divmod(int(round(delta_ms * 1000)), 1_000_000)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.adjtime(ctypes.byref(Timeval(sec, usec)), None) != 0:
        err = ctypes.get_errno()
        raise OSError(err, "adjtime failed")


def pending_ms():
    """What the kernel still has to slew from an earlier adjtime(), in ms (positive: advance)."""
    class Timeval(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]
    old = Timeval()
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.adjtime(None, ctypes.byref(old)) != 0:
        raise OSError(ctypes.get_errno(), "adjtime read failed")
    return old.tv_sec * 1000 + old.tv_usec / 1000


def iso_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def log_row(res, med, ok, path=LOG, applied="", pending="", now_ms=None):
    """One row: local time, estimated true time (local + median offset, when the venues agree), the median, whether they
    agree, the venues used, bound_ms (a half-RTT diagnostic, not a UTC certificate) and spread_ms (their widest
    disagreement), what was slewed or still pending, then every venue's offset and round trip."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    now_ms = wall_ms() if now_ms is None else now_ms
    use = usable(res)
    members = "+".join(sorted(use)) if ok else ""
    bound = f"{max(r for _, r in use.values()) / 2:.0f}" if ok else ""
    spread = f"{max(o for o, _ in use.values()) - min(o for o, _ in use.values()):.0f}" if ok else ""
    cells = [iso_ms(now_ms), iso_ms(now_ms + med) if ok else "", f"{med:.0f}", str(ok), members, bound, spread,
             str(applied), f"{pending:.0f}" if pending != "" else ""]
    for name in VENUES:
        cells += [f"{res[name][0]:.0f}", f"{res[name][1]:.0f}"] if name in res else ["", ""]
    with path.open("a") as f:
        if new:
            f.write("utc_local,utc_est_true,median_offset_ms,agree,used,bound_ms,spread_ms,slewed_ms,pending_ms,"
                    + ",".join(f"{n}_ms,{n}_rtt_ms" for n in VENUES) + "\n")
        f.write(",".join(cells) + "\n")


def report(res, med, ok):
    for name, (o, r) in res.items():
        print(f"{name:8s} server - local {o:+7.0f} ms   rtt {r:4.0f} ms")
    print(f"median {med:+.0f} ms (positive: this clock is behind); venues agree within {AGREE_MS} ms: {ok}")


def main(argv=None, measure_fn=measure, adjust=adjtime_ms, pending_fn=pending_ms, lock_path=LOCK):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["status", "slew"])
    ap.add_argument("--min-ms", type=float, default=250)
    ap.add_argument("--max-ms", type=float, default=10_000)
    a = ap.parse_args(argv)
    if not (math.isfinite(a.min_ms) and math.isfinite(a.max_ms)
            and 0 <= a.min_ms <= a.max_ms and a.max_ms > 0):
        ap.error("limits must be finite, with 0 <= --min-ms <= --max-ms and --max-ms > 0")
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("another clock check is running; nothing measured")
            return 0
        return run(a, measure_fn, adjust, pending_fn)


def run(a, measure_fn, adjust, pending_fn):
    res = measure_fn()
    med, ok = consensus(res)
    report(res, med, ok)
    try:
        pend = pending_fn()
    except OSError:
        pend = ""
    if not isinstance(pend, (int, float)) or isinstance(pend, bool) or not math.isfinite(pend):
        pend = ""
    if pend != "":
        print(f"still pending from an earlier slew: {pend:+.0f} ms")
    applied = ""
    exit_code = 0
    if a.cmd == "slew":
        if pend == "":
            print("not applied: pending clock correction could not be read; existing correction is unknown")
            exit_code = 1
        elif not ok:
            print(f"not applied: fewer than two venues within {MAX_RTT_MS} ms round trip, or they disagree")
        elif pend not in ("", 0) and abs(med - pend) > PENDING_TOL_MS:
            print(f"not applied: the offset is {abs(med - pend):.0f} ms from the pending slew; measure again")
        elif abs(med) < a.min_ms:
            print(f"not applied: |offset| below {a.min_ms:.0f} ms")
        elif abs(med) > a.max_ms:
            print(f"not applied: |offset| above {a.max_ms:.0f} ms; check by hand")
        else:
            adjust(med)
            applied = f"{med:.0f}"
            print(f"slewing by {med:+.0f} ms (at most 0.5 ms per second: about {abs(med) / 0.5 / 60:.0f} min)")
    log_row(res, med, ok, path=LOG, applied=applied, pending=pend)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
