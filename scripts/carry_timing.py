"""Timing budget of the forward carry books: how many more `late` days each can take before its frozen read is
labelled "degraded timing".

Read-only, and blind to results: it opens only `journal/decisions.csv` (columns run, day, book, kind) of each lane.
It never opens days.csv, tickets.csv or status.json, so it prints no return, t-statistic or drawdown.

The rule it counts against is each lane's own frozen PREREG ("Timing quality"): if more than 20% of the scored days
are `late`, the verdict is labelled degraded timing. A label, not a FAIL; it weakens the evidence because a late day
has no live mid and books the close. Lanes, looks and dates below are copied from those PREREGs.

    python scripts/carry_timing.py            # table to stdout
    python scripts/carry_timing.py --today 2026-11-17
"""
import argparse
import csv
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# lane folder: (round, look 1 scored days, look 1 date, look 2 scored days, look 2 date). Copied from each PREREG.
LANES = {
    "xfund_fwd": ("R278", 90, "2027-01-20", 180, "2027-04-20"),
    "xfund_kc_fwd": ("R279", 90, "2027-01-20", 180, "2027-04-20"),
    "xfund_lt_fwd": ("R294", 90, "2027-01-21", 180, "2027-04-21"),
    "xfund_bg_fwd": ("R390", 90, "2027-02-02", 180, "2027-05-03"),
    "xfund5_fwd": ("R440", 90, "2027-02-09", 180, "2027-05-10"),
}
LATE_SHARE = 0.20  # "more than 20% of the scored days are late"


def allowed_late(scored_days, share=LATE_SHARE):
    """Most late days that keep a read of `scored_days` days out of the degraded label (late / scored <= share)."""
    return math.floor(share * scored_days + 1e-9)


def book_counts(rows):
    """Per book: live decision days, late days, and the first and last live day. Replay rows are not live."""
    out = {}
    for r in rows:
        if r["kind"] == "replay":
            continue
        b = out.setdefault(r["book"], {"live": 0, "late": 0, "days": set(), "last_run": ""})
        if r["day"] in b["days"]:
            continue
        b["days"].add(r["day"])
        b["live"] += 1
        b["late"] += r["kind"] == "late"
        b["last_run"] = max(b["last_run"], r["run"])
    return out


def missing_days(days):
    """Calendar days between the first and last live decision with no decision at all."""
    if not days:
        return 0
    ds = sorted(date.fromisoformat(d) for d in days)
    return (ds[-1] - ds[0]).days + 1 - len(ds)


def table(root=ROOT, today=None):
    today = today or datetime.now(timezone.utc).date()
    lines = [
        "| lane | round | book | live days | late | late share | late left before look 1 | before look 2 | "
        "missing days | last decision run |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for lane, (rid, n1, d1, n2, d2) in LANES.items():
        path = root / "experiments" / lane / "journal" / "decisions.csv"
        if not path.exists():
            lines.append(f"| {lane} | {rid} | - | no journal | | | | | | |")
            continue
        with path.open(newline="") as f:
            rows = [{k: r[k] for k in ("run", "day", "book", "kind")} for r in csv.DictReader(f)]
        for book, c in sorted(book_counts(rows).items()):
            left1 = allowed_late(n1) - c["late"]
            left2 = allowed_late(n2) - c["late"]
            share = c["late"] / c["live"] if c["live"] else float("nan")
            lines.append(
                f"| {lane} | {rid} | {book} | {c['live']} | {c['late']} | {share:.0%} | "
                f"{left1} (look 1, {d1}) | {left2} (look 2, {d2}) | {missing_days(c['days'])} | {c['last_run']} |"
            )
    lines.append("")
    lines.append(
        f"As of {today.isoformat()}. A negative 'late left' means that look's verdict will carry the degraded-timing "
        "label whatever happens next. Counts are decision days; the frozen read counts scored days, which trail them "
        "by at most one."
    )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--today", type=date.fromisoformat, default=None)
    args = ap.parse_args(argv)
    print(table(today=args.today))
    return 0


if __name__ == "__main__":
    sys.exit(main())
