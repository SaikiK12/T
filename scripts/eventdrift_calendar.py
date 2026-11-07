"""EIA release calendar for R368 eventdrift_v1: the Weekly Petroleum Status Report (crude) and the Weekly Natural Gas
Storage Report, as release instants in UTC. Built from the rules on EIA's two schedule pages, read on 2026-10-28:

- https://www.eia.gov/petroleum/supply/weekly/schedule.php   "10:30 a.m. eastern time on Wednesday" with the listed
  holiday exceptions (2026: Thursday 12:00 p.m. on January 22, February 19, May 28, September 10, October 15,
  November 12).
- https://ir.eia.gov/ngs/schedule.html   "10:30 a.m. eastern time on Thursdays" with the listed exceptions (2026:
  Friday November 13, Wednesday November 25 12:00 p.m.; none between April and October).

US daylight time runs 2026-03-08 to 2026-11-01, so every release in April-October is 10:30 EDT = 14:30 UTC and 12:00 EDT
= 16:00 UTC. The calendar never looks at a price. It is a frozen input of the lane; a corrected calendar is a new lane.

usage: python scripts/eventdrift_calendar.py [--first 2026-04-01] [--last 2026-10-22] [--out PATH]
"""
import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "eventdrift_v1" / "events.csv"
SOURCES = {
    "wpsr": "https://www.eia.gov/petroleum/supply/weekly/schedule.php",
    "ngs": "https://ir.eia.gov/ngs/schedule.html",
}
# (standard date, alternate date, alternate hour in UTC) for the exceptions that fall inside April-October 2026
EXCEPTIONS = {
    "wpsr": {dt.date(2026, 5, 27): (dt.date(2026, 5, 28), 16), dt.date(2026, 9, 9): (dt.date(2026, 9, 10), 16),
             dt.date(2026, 10, 14): (dt.date(2026, 10, 15), 16)},
    "ngs": {},
}
WEEKDAY = {"wpsr": 2, "ngs": 3}          # Wednesday, Thursday
STANDARD_UTC = (14, 30)                  # 10:30 EDT


def events(first, last):
    """[(event, instant UTC)] for the standard weekday of each report in [first, last], exceptions applied."""
    out = []
    for name, wd in WEEKDAY.items():
        d = first
        while d <= last:
            if d.weekday() == wd:
                alt, hour = EXCEPTIONS[name].get(d, (d, None))
                t = dt.datetime(alt.year, alt.month, alt.day, *(STANDARD_UTC if hour is None else (hour, 0)),
                                tzinfo=dt.timezone.utc)
                out.append((name, t))
            d += dt.timedelta(days=1)
    # an exception can move a release past `last`; keep only releases inside the window
    lo = dt.datetime.combine(first, dt.time(), tzinfo=dt.timezone.utc)
    hi = dt.datetime.combine(last + dt.timedelta(days=1), dt.time(), tzinfo=dt.timezone.utc)
    return sorted((e for e in out if lo <= e[1] < hi), key=lambda e: (e[1], e[0]))


def write(path, first, last):
    rows = events(first, last)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["event", "release_utc", "release_ms", "source"])
        for name, t in rows:
            w.writerow([name, t.strftime("%Y-%m-%dT%H:%M:%SZ"), int(t.timestamp() * 1000), SOURCES[name]])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--first", default="2026-04-01")
    ap.add_argument("--last", default="2026-10-22")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    rows = write(Path(a.out), dt.date.fromisoformat(a.first), dt.date.fromisoformat(a.last))
    counts = {n: sum(1 for r in rows if r[0] == n) for n in WEEKDAY}
    print(f"{len(rows)} releases {counts} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
