"""Minute snapshots of the Deribit BTC option chain around the 08:00 UTC expiry (M440). Public bulk request, no key,
paper only. record_deribit_chain.py keeps one snapshot an hour; a flow that unwinds in the hours around an expiry needs
the open interest, mark IV, bid/ask and the underlying every minute, and Deribit serves the current chain only, so it
exists only if recorded.

The window is 06:45-10:15 UTC every day (daily options expire at 08:00 UTC, weeklies on Fridays, monthlies on the last
Friday), fixed before any outcome was read. One file per snapshot, data/option_expiry/<YYYY-MM-DD>/<HHMMSS>.parquet
(gitignored), with the same columns as record_deribit_chain.py plus `t_done` (when the response arrived, ms) so the
latency of each snapshot is known. Dealer positioning is not in this file: public open interest does not say who is long
or short, so trade-side reconstruction needs Deribit's trade history, which its public API paginates.

A daemon: `ensure` (the default, called hourly from the orchestrator) starts it when none holds its lock. It stops
writing under MIN_FREE_GB free or MAX_MB stored. Data collection only.

usage: python scripts/record_option_expiry.py [ensure|run|once|status]
"""
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data  # noqa: E402
import record_deribit_chain as chain  # noqa: E402

OUT = data.ROOT / "option_expiry"
RUN = data.ROOT / "logs"
WINDOW = (6.75, 10.25)            # UTC hours, 06:45 to 10:15
EVERY_S = 60
MIN_FREE_GB = 2.5
MAX_MB = 600
COLS = chain.COLS + ["t_done"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def in_window(t_s, window=WINDOW):
    h = time.gmtime(t_s)
    x = h.tm_hour + h.tm_min / 60 + h.tm_sec / 3600
    return window[0] <= x < window[1]


def snapshot_path(t_s, out=OUT):
    t = time.gmtime(t_s)
    return out / time.strftime("%Y-%m-%d", t) / f"{time.strftime('%H%M%S', t)}.parquet"


def used_mb(out=OUT):
    return sum(f.stat().st_size for f in out.rglob("*.parquet")) / 1e6 if out.exists() else 0.0


def full(out=OUT, free_gb=None):
    free = shutil.disk_usage(ROOT).free / 1e9 if free_gb is None else free_gb
    if free < MIN_FREE_GB:
        return f"disk below {MIN_FREE_GB} GB free"
    if used_mb(out) >= MAX_MB:
        return f"data/option_expiry reached {MAX_MB} MB"
    return ""


def take(t_s, out=OUT, get=chain.http):
    """One BTC chain snapshot into its own file; returns the row count, or 0 when nothing was written."""
    path = snapshot_path(t_s, out)
    if path.exists():
        return 0
    ts = int(time.time() * 1000)
    result = get("BTC")
    done = int(time.time() * 1000)
    df = pd.DataFrame(chain.rows("BTC", result, ts), columns=chain.COLS)
    if df.empty:
        return 0
    df["t_done"] = done
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    df.to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(path)
    return len(df)


def run(stop, out=OUT, get=chain.http, every=EVERY_S, status=None, clock=time.time):
    n = rows = fails = 0
    why = ""
    while not stop.is_set():
        now = clock()
        if in_window(now):
            why = full(out)
            if why:
                log(f"option expiry: {why}")
            else:
                try:
                    k = take(now, out, get)
                    n += k > 0
                    rows += k
                except Exception as e:  # noqa: BLE001 - a bad request waits for the next minute
                    fails += 1
                    log(f"option expiry: snapshot failed: {e}")
        if status:
            tmp = status.with_name(status.name + ".tmp")
            tmp.write_text(json.dumps({"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                                       "pid": os.getpid(), "window_utc_hours": WINDOW, "snapshots": n, "rows": rows,
                                       "failed": fails, "in_window": in_window(now), "stopped": why}))
            tmp.replace(status)
        stop.wait(max(1.0, every - (clock() % every)))     # next minute boundary


def lock():
    RUN.mkdir(parents=True, exist_ok=True)
    f = open(RUN / "option_expiry.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = (argv or ["ensure"])[0]
    st = RUN / "option_expiry_status.json"
    if cmd == "status":
        print(st.read_text() if st.exists() else "no status yet")
        return 0
    if cmd == "once":
        k = take(time.time())
        print(f"{k} rows" if k else "nothing written")
        return 0
    if cmd == "ensure":
        held = lock()
        if held is None:
            log("option expiry: recorder running")
            return 0
        held.close()
        RUN.mkdir(parents=True, exist_ok=True)
        with open(RUN / "option_expiry.log", "a") as f:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=f,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        log("option expiry: recorder started")
        return 0
    held = lock()
    if held is None:
        log("option expiry: another recorder holds data/logs/option_expiry.lock")
        return 1
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    log(f"option expiry: snapshots every {EVERY_S} s from {WINDOW[0]} to {WINDOW[1]} UTC hours")
    run(stop, status=st)
    log("option expiry: stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
