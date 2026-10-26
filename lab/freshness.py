"""Freshness of the lab's live streams: when each recorder, loop and forward lane last wrote, against its cadence.

Read-only. A file's modification time says that its writer ran, not that the data it wrote is complete or correct.
R200's row also carries the close of the newest hour it computed (experiments/flow72_fwd2/journal/ticks.csv), the
clock scripts/forward_lag.py judges: an hour computed more than 60 minutes after its close is late.

States, from a stream's age against the minutes between its writes (its cadence):
    FRESH    age <= 1.5 x cadence      (a write may land at any point of the next slot)
    LATE     age <= 4.5 x cadence      (one or two slots missed)
    STALE    older                     (its writer is down)
    MISSING  no file matches

usage: python -m lab.freshness          # the table, oldest first
"""
import calendar
import csv
import glob
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H_MS = 3_600_000

# (id, what it holds, how it is written, files relative to the checkout, minutes between writes)
STREAMS = (
    ("mexc_ticker", "MEXC funding and ticker snapshots", "recorder, hourly tick", "data/recorders/mexc_ticker/*/*", 60),
    ("funding_board", "Funding board, six venues", "recorder, hourly tick", "data/recorders/funding_board/*/*", 60),
    ("deribit_chain", "Deribit option chains", "recorder, hourly tick", "data/recorders/deribit_chain/*/*", 60),
    ("lighter_book", "Lighter order books", "recorder, hourly tick", "data/recorders/lighter_book/*/*", 60),
    ("wallets", "Deposit and withdrawal status, five venues", "recorder, hourly tick", "data/recorders/wallets/*/*", 60),
    ("unlocks", "Token unlock calendar", "recorder, daily", "data/recorders/unlocks/*", 1440),
    ("dex_prices", "DEX pool prices", "daemon, 5 minutes", "data/recorders/dex_prices/*/*", 5),
    ("notices", "Exchange notices, then R272 tickets", "loop, 5 minutes", "data/logs/notice_loop.log", 5),
    ("tape", "Order-flow tape: Binance, MEXC, Lighter", "daemon, 10-minute flush", "data/tape/status.json", 10),
    ("news", "Headlines", "daemon, 1-minute poll", "data/news/status.json", 5),
    ("copylead_hl", "Hyperliquid leaderboard and positions", "scrape, daily", "experiments/copylead_data/hyperliquid/*/*", 1440),
    ("copylead_cex", "Binance and OKX copy-trading boards", "scrape, daily", "experiments/copylead_data/snapshots/*/*", 1440),
    ("recorder_digest", "Recorder digests", "hourly tick", "experiments/recorders/journal/digests.csv", 60),
    ("R224", "MEXC order-book cost snapshots", "forward lane, hourly tick", "experiments/mexc_costs/journal/*", 60),
    ("R221", "Sequential review of the MEXC books", "forward lane, hourly tick", "experiments/mexc_seq/results/*", 60),
)
R200_TICKS = "experiments/flow72_fwd2/journal/ticks.csv"
LATE_MIN = 60


def state(age_min, cadence_min):
    if age_min is None:
        return "MISSING"
    return "FRESH" if age_min <= 1.5 * cadence_min else "LATE" if age_min <= 4.5 * cadence_min else "STALE"


def newest(root, pattern):
    """(mtime, path) of the newest regular file matching `pattern` under root, or (None, None)."""
    best = (None, None)
    for p in glob.glob(str(Path(root) / pattern)):
        try:
            if os.path.isfile(p) and not os.path.islink(p):
                m = os.stat(p).st_mtime
                if best[0] is None or m > best[0]:
                    best = (m, p)
        except OSError:                                # a writer can replace a file while we look
            continue
    return best


def lanes():
    """(id, what, journal glob) of every forward lane in lab.operations.LANES; each writes status.json each tick."""
    from lab.operations import LANES
    return tuple((lane.rid, lane.what, lane.status_path) for lane in LANES)


def r200_hour(root):
    """(close of the newest hour R200 computed in ms, minutes after that close it was computed), or (None, None)."""
    try:
        with open(Path(root) / R200_TICKS, newline="") as f:
            last = None
            for last in csv.DictReader(f):
                pass
    except OSError:
        return None, None
    if not last:
        return None, None
    close = int(last["t"]) + H_MS
    run = calendar.timegm(time.strptime(last["run_at"], "%Y-%m-%dT%H:%M:%SZ"))
    return close, round((run * 1000 - close) / 60_000, 1)


def rows(root=ROOT, now=None, lane_specs=None):
    now = time.time() if now is None else now
    iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
    specs = [(sid, what, how, pattern, cadence) for sid, what, how, pattern, cadence in STREAMS]
    specs += [(rid, what, "forward lane, hourly tick", path, 60) for rid, what, path in (lane_specs or lanes())]
    out = []
    for sid, what, how, pattern, cadence in specs:
        mtime, path = newest(root, pattern)
        age = None if mtime is None else round(max(0.0, now - mtime) / 60, 1)
        row = {"stream": sid, "what": what, "how": how, "cadence_min": cadence,
               "last_write": None if mtime is None else iso(mtime), "age_min": age, "state": state(age, cadence),
               "path": None if path is None else os.path.relpath(path, root), "data_at": None, "data_age_min": None,
               "lag_at_compute_min": None, "on_time": None}
        if sid == "R200":
            close, lag = r200_hour(root)
            if close is not None:
                row.update(data_at=iso(close / 1000), data_age_min=round((now * 1000 - close) / 60_000, 1),
                           lag_at_compute_min=lag, on_time=lag <= LATE_MIN)
        out.append(row)
    order = {"STALE": 0, "MISSING": 1, "LATE": 2, "FRESH": 3}
    return sorted(out, key=lambda r: (order[r["state"]], -(r["age_min"] or 0), r["stream"]))


def main():
    rs = rows()
    width = max(len(r["stream"]) for r in rs)
    for r in rs:
        age = "-" if r["age_min"] is None else f"{r['age_min']:.0f} min"
        extra = (f"  newest hour closed {r['data_at']}, computed {r['lag_at_compute_min']:.0f} min after"
                 if r["data_at"] else "")
        print(f"{r['state']:<8} {r['stream']:<{width}}  {age:>10} (every {r['cadence_min']} min)  {r['what']}{extra}")


if __name__ == "__main__":
    main()
