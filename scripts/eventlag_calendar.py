"""EIA release calendar for R369 eventlag_fwd, from 2026-10-29 to 2026-12-31: the Weekly Natural Gas Storage Report
("ng", Thursdays) and the Weekly Petroleum Status Report ("wpsr", Wednesdays), as release instants in UTC. Built from the
two schedule pages read on 2026-10-28 and saved in full:

- https://ir.eia.gov/ngs/schedule.html   standard "10:30 a.m. eastern time on Thursdays"; alternate dates in the window:
  Friday 2026-11-13 10:30 a.m. (Veterans Day) and Wednesday 2026-11-25 12:00 p.m. (Thanksgiving Day). Nothing else is
  listed for 2026.
- https://www.eia.gov/petroleum/supply/weekly/schedule.php   standard Wednesday 10:30 a.m. eastern; alternate in the
  window: Thursday 2026-11-12 12:00 p.m. (Veterans Day). Nothing else is listed for 2026.

US clocks go back on 2026-11-01, so the release is 14:30 UTC on 2026-10-29 (daylight time) and 15:30 UTC from 2026-11-04
(10:30 EST); 12:00 p.m. EST is 17:00 UTC. The calendar never looks at a price. A corrected or extended calendar (2027
dates, or a changed EIA page) is a new lane.

usage: python scripts/eventlag_calendar.py [--first 2026-10-29] [--last 2026-12-31] [--out PATH]
"""
import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "eventlag_fwd" / "events.csv"
SOURCES = {
    "ng": "https://ir.eia.gov/ngs/schedule.html",
    "wpsr": "https://www.eia.gov/petroleum/supply/weekly/schedule.php",
}
WEEKDAY = {"ng": 3, "wpsr": 2}                       # Thursday, Wednesday
DST_END = dt.date(2026, 11, 1)                       # US clocks go back at 02:00 local on this Sunday
# standard date -> (alternate date, alternate hour in Eastern time, alternate minute)
EXCEPTIONS = {
    "ng": {dt.date(2026, 11, 12): (dt.date(2026, 11, 13), 10, 30), dt.date(2026, 11, 26): (dt.date(2026, 11, 25), 12, 0)},
    "wpsr": {dt.date(2026, 11, 11): (dt.date(2026, 11, 12), 12, 0)},
}


def utc(day, hour, minute):
    """The instant of an Eastern wall time on `day`: UTC-4 up to and including 2026-11-01, UTC-5 after."""
    offset = 4 if day <= DST_END else 5
    return dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=dt.timezone.utc) + dt.timedelta(hours=offset)


def events(first, last):
    out = []
    for name, wd in WEEKDAY.items():
        d = first
        while d <= last:
            if d.weekday() == wd or d in EXCEPTIONS[name]:
                if d in EXCEPTIONS[name]:
                    day, hour, minute = EXCEPTIONS[name][d]
                elif d.weekday() == wd:
                    day, hour, minute = d, 10, 30
                out.append((name, utc(day, hour, minute)))
            d += dt.timedelta(days=1)
    # a standard date that an exception moves is listed once, at its alternate; drop duplicates and out-of-window dates
    seen, keep = set(), []
    lo = dt.datetime.combine(first, dt.time(), tzinfo=dt.timezone.utc)
    hi = dt.datetime.combine(last + dt.timedelta(days=1), dt.time(), tzinfo=dt.timezone.utc)
    for e in sorted(out, key=lambda e: (e[1], e[0])):
        if e not in seen and lo <= e[1] < hi:
            seen.add(e)
            keep.append(e)
    return keep


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
    ap.add_argument("--first", default="2026-10-29")
    ap.add_argument("--last", default="2026-12-31")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    rows = write(Path(a.out), dt.date.fromisoformat(a.first), dt.date.fromisoformat(a.last))
    counts = {n: sum(1 for r in rows if r[0] == n) for n in WEEKDAY}
    print(f"{len(rows)} releases {counts} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
