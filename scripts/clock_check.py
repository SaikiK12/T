"""Local clock check against three public exchange clocks, and a gradual correction (data collection support only).

The recorders stamp recv_ms from this machine's wall clock. After the container restarts of 2026-10-29 the clock ran slow
(about 100 ppm, 1.8 s by 10:20 UTC) and nothing disciplined it, so every local receipt time and lag_ms was early by that
much. This script measures the offset and, on request, removes it with adjtime(), which slews at most 500 ppm and never
steps the clock, so no running recorder sees a jump.

offset = exchange time - local time at the request midpoint, so a positive offset means this clock is behind. Each venue
contributes its lowest-round-trip sample; the median over venues is used, and nothing is applied unless the venues agree.

usage: python scripts/clock_check.py status | slew [--min-ms 250] [--max-ms 10000]
Every run appends one row to experiments/recorders/journal/clock_check.csv (committed, so the offset at an event is on
record). Only this script writes that file.
"""
import argparse
import ctypes
import statistics
import sys
import time
from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "experiments" / "recorders" / "journal" / "clock_check.csv"
SAMPLES = 6
AGREE_MS = 500          # the venues' offsets must lie within this of each other
MAX_RTT_MS = 450        # a sample with a longer round trip is too noisy (error up to half of it) and is not used
PENDING_TOL_MS = 400    # a new offset this far from the adjustment still pending is taken as a bad measurement
VENUES = {
    "mexc": ("https://contract.mexc.com/api/v1/contract/ping", lambda j: int(j["data"])),
    "deribit": ("https://www.deribit.com/api/v2/public/get_time", lambda j: int(j["result"])),
    "okx": ("https://www.okx.com/api/v5/public/time", lambda j: int(j["data"][0]["ts"])),
}


def wall_ms():
    return time.time_ns() / 1e6


def fetch_json(url):
    import requests
    return requests.get(url, timeout=10).json()


def venue_offset(url, parse, samples=SAMPLES, get=fetch_json, clock_ms=wall_ms):
    """(offset_ms, rtt_ms) of the lowest-round-trip sample. Raises when no sample succeeds."""
    best = None
    for _ in range(samples):
        t0 = clock_ms()
        try:
            srv = parse(get(url))
        except Exception:
            continue
        t1 = clock_ms()
        cand = (srv - (t0 + t1) / 2, t1 - t0)
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


def consensus(res, agree_ms=AGREE_MS, max_rtt_ms=MAX_RTT_MS):
    """(median offset ms, ok): ok needs at least two venues with a round trip of at most max_rtt_ms, within agree_ms of
    each other."""
    use = {k: v for k, v in res.items() if v[1] <= max_rtt_ms}
    if len(use) < 2:
        return (statistics.median(o for o, _ in res.values()) if res else float("nan")), False
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


def log_row(res, med, ok, path=LOG, applied="", pending=""):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    cells = [time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), f"{med:.0f}", str(ok), str(applied),
             f"{pending:.0f}" if pending != "" else ""]
    for name in VENUES:
        cells.append(f"{res[name][0]:.0f}" if name in res else "")
    with path.open("a") as f:
        if new:
            f.write("utc,median_offset_ms,agree,slewed_ms,pending_ms," + ",".join(f"{n}_ms" for n in VENUES) + "\n")
        f.write(",".join(cells) + "\n")


def report(res, med, ok):
    for name, (o, r) in res.items():
        print(f"{name:8s} server - local {o:+7.0f} ms   rtt {r:4.0f} ms")
    print(f"median {med:+.0f} ms (positive: this clock is behind); venues agree within {AGREE_MS} ms: {ok}")


def main(argv=None, measure_fn=measure, adjust=adjtime_ms, pending_fn=pending_ms):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["status", "slew"])
    ap.add_argument("--min-ms", type=float, default=250)
    ap.add_argument("--max-ms", type=float, default=10_000)
    a = ap.parse_args(argv)
    res = measure_fn()
    med, ok = consensus(res)
    report(res, med, ok)
    try:
        pend = pending_fn()
    except OSError:
        pend = ""
    if pend != "":
        print(f"still pending from an earlier slew: {pend:+.0f} ms")
    applied = ""
    if a.cmd == "slew":
        if not ok:
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
