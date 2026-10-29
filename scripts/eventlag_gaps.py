"""Websocket-gap check for R369 eventlag_fwd (a diagnostic; not one of the frozen inputs, it decides nothing).

The public websockets reached through this container's proxy drop every few minutes and reconnect 1-2 s later
(data/commodity_perps/sessions.csv, data/lighter_trades/sessions.csv). A drop of the follower's feed (Lighter) across a
release leaves its last quote on screen while the real book moves, which the frozen rule reads as "the follower has not
moved yet", i.e. a lag that is not there. A drop of a leader's feed makes t* later and the follower's c larger, so the
trade is skipped, the safe direction. This script marks, for every journaled release, which feed had a session boundary
(an end or a start) inside [T - 10 s, T + 65 s] (padded by 2 s, the file's resolution), and reports the decision cell on
the clean releases only next to the frozen all-release read.

usage: python scripts/eventlag_gaps.py [--lane experiments/eventlag_fwd]    writes <lane>/results/gaps.csv
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import eventlag_rule as rule  # noqa: E402

FEEDS = {"binance": ("data/commodity_perps/sessions.csv", "bn_public"),
         "hl": ("data/commodity_perps/sessions.csv", "hl"),
         "lighter": ("data/lighter_trades/sessions.csv", None)}
BEFORE_S, AFTER_S, PAD_S = 10, 65, 2


def stamp(x):
    return dt.datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def boundaries(path, venue=None):
    """Every session start and end time in the file (one venue of it if given), as datetimes."""
    p = Path(path)
    if not p.exists():
        return []
    df = pd.read_csv(p)
    if venue is not None:
        df = df[df.venue == venue]
    return [stamp(x) for x in list(df.start_utc) + list(df.end_utc)]


def gapped(times, T):
    """True when a session boundary falls inside the event window of release T (a datetime)."""
    lo = T - dt.timedelta(seconds=BEFORE_S + PAD_S)
    hi = T + dt.timedelta(seconds=AFTER_S + PAD_S)
    return any(lo <= t <= hi for t in times)


def flags(release_utc, root=ROOT):
    T = stamp(release_utc)
    out = {}
    for feed, (rel, venue) in FEEDS.items():
        out[feed] = gapped(boundaries(Path(root) / rel, venue), T)
    out["clean"] = not any(out.values())
    return out


def decision_cells(cells, clean):
    """Frozen decision cell (Lighter follower, L = DECISION_L, lag-filtered, a trade taken) on the given releases."""
    keep = cells[(cells.kind == "event") & (cells.follower == rule.PRIMARY_FOLLOWER) & (cells.lag_s == rule.DECISION_L)
                 & (cells.status == "ok") & (cells.lag_ok.astype(str) == "True")]
    keep = keep[keep.apply(lambda r: (r.event, r.release_utc) in clean, axis=1)]
    out = {}
    for name, g in keep.groupby("event"):
        x = g.gross.astype(float).to_numpy()
        out[name] = {"n": len(x), "mean_gross": float(x.mean()) if len(x) else float("nan"),
                     "mean_net_2x": float(np.mean([rule.net(v, rule.PRIMARY_FOLLOWER, 2) for v in x])) if len(x) else float("nan")}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lane", default=str(ROOT / "experiments" / "eventlag_fwd"))
    a = ap.parse_args(argv)
    lane = Path(a.lane)
    jev, jcells = lane / "journal" / "events.csv", lane / "journal" / "cells.csv"
    if not jev.exists():
        print("no journaled releases yet")
        return 0
    ev = pd.read_csv(jev)
    rows = [{"event": r.event, "release_utc": r.release_utc, "validity": r.validity, **flags(r.release_utc)}
            for r in ev.itertuples()]
    gaps = pd.DataFrame(rows)
    (lane / "results").mkdir(parents=True, exist_ok=True)
    gaps.to_csv(lane / "results" / "gaps.csv", index=False)
    print(gaps.to_string(index=False))
    if jcells.exists():
        cells = pd.read_csv(jcells)
        clean = {(r.event, r.release_utc) for r in gaps.itertuples() if r.clean and r.validity == "valid"}
        everyone = {(r.event, r.release_utc) for r in gaps.itertuples() if r.validity == "valid"}
        print("clean releases:", decision_cells(cells, clean))
        print("all valid releases:", decision_cells(cells, everyone))
    return 0


if __name__ == "__main__":
    sys.exit(main())
