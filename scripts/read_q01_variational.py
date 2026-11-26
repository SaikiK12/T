"""Register Q01's read (docs/reviews/open_questions.md; event defined in registry/forecasts.csv row F034 before the first
recorded weekend): does Variational hold its US-equity perps near the frozen index over a weekend, and how far do they
sit from trade.xyz's books?

Inputs: a checkout of the data branch claude/xyz-books-data (written hourly by .github/workflows/claude-xyz-books.yml):
- variational/stats/YYYY-MM-DD.csv (scripts/record_variational.py): ts (ms), ticker, mark_price, bid_1k, ask_1k, ...
- books/YYYY-MM-DD.csv (scripts/record_xyz_books.py): dex, coin (xyz:TICKER), ts (ms), bid, ask, ...
Universe: trade.xyz's 76 US-stock markets (experiments/xyzwknd_v1/universe.csv); a Variational ticker is TICKER-PERP.

For the weekend whose Friday is F:
- reference: each listing's Variational mark_price at the snapshot nearest Friday 16:00 New York (within 90 minutes);
- probe: Variational's $1k mid (bid_1k + ask_1k) / 2 and xyz's book mid at the snapshots nearest Sunday 18:00 New York
  (within 90 minutes);
- F034's event: the median over matched listings of |Variational $1k mid / Friday mark - 1| is below 25 bp;
- Q01's question: the gap |Variational mid / xyz mid - 1| in bp, its median and the share of listings above 100 bp.

usage: python scripts/read_q01_variational.py --data DIR --friday 2026-11-27 [--out FILE]
"""
import argparse
import csv
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
NY = ZoneInfo("America/New_York")
UNIVERSE = ROOT / "experiments" / "xyzwknd_v1" / "universe.csv"
TOL_MS = 90 * 60 * 1000


def ny_ms(day, hour):
    """Milliseconds UTC of `hour`:00 New York time on date `day` (YYYY-MM-DD)."""
    d = datetime.fromisoformat(day).replace(hour=hour, tzinfo=NY)
    return int(d.timestamp() * 1000)


def rows(paths):
    out = []
    for p in paths:
        if Path(p).exists():
            with open(p, newline="") as f:
                out.extend(csv.DictReader(f))
    return out


def nearest(rs, key, target, tol=TOL_MS):
    """{key value: row nearest to target ms within tol}."""
    best = {}
    for r in rs:
        try:
            t = int(float(r["ts"]))
        except (KeyError, ValueError):
            continue
        dt = abs(t - target)
        if dt > tol:
            continue
        k = r[key]
        if k not in best or dt < best[k][0]:
            best[k] = (dt, r)
    return {k: v[1] for k, v in best.items()}


def num(x):
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def read(var_rows, book_rows, coins, friday):
    sunday = (datetime.fromisoformat(friday) + timedelta(days=2)).date().isoformat()
    ref = nearest(var_rows, "ticker", ny_ms(friday, 16))
    probe = nearest(var_rows, "ticker", ny_ms(sunday, 18))
    xyz = nearest([r for r in book_rows if r.get("dex") == "xyz"], "coin", ny_ms(sunday, 18))
    per = []
    for c in coins:
        t = f"{c}-PERP"
        if t not in ref or t not in probe:
            continue
        mark = num(ref[t].get("mark_price"))
        b, a = num(probe[t].get("bid_1k")), num(probe[t].get("ask_1k"))
        if not mark or not b or not a:
            continue
        mid = (a + b) / 2
        row = {"coin": c, "frozen_dev_bp": abs(mid / mark - 1) * 1e4}
        x = xyz.get(f"xyz:{c}")
        if x and num(x.get("bid")) and num(x.get("ask")):
            row["xyz_gap_bp"] = abs(mid / ((num(x["bid"]) + num(x["ask"])) / 2) - 1) * 1e4
        per.append(row)
    dev = [r["frozen_dev_bp"] for r in per]
    gap = [r["xyz_gap_bp"] for r in per if "xyz_gap_bp" in r]
    return {"friday": friday, "sunday": sunday, "matched": len(per),
            "median_frozen_dev_bp": statistics.median(dev) if dev else None,
            "f034_event": (statistics.median(dev) < 25) if dev else None,
            "with_xyz": len(gap), "median_xyz_gap_bp": statistics.median(gap) if gap else None,
            "share_xyz_gap_over_100bp": (sum(g > 100 for g in gap) / len(gap)) if gap else None, "per": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="checkout of the data branch")
    ap.add_argument("--friday", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    fri = datetime.fromisoformat(a.friday).date()
    days = [(fri + timedelta(days=i)).isoformat() for i in range(0, 3)]
    d = Path(a.data)
    var_rows = rows([d / "variational" / "stats" / f"{x}.csv" for x in days])
    book_rows = rows([d / "books" / f"{x}.csv" for x in days])
    with open(UNIVERSE, newline="") as f:
        coins = [r["coin"] for r in csv.DictReader(f)]
    r = read(var_rows, book_rows, coins, a.friday)
    lines = [f"# Q01 read, weekend of {r['friday']}", "",
             f"- Matched Variational US-equity listings: {r['matched']} (of {len(coins)} xyz markets).",
             f"- Median |Variational $1k mid on Sunday 18:00 NY / Friday 16:00 NY mark - 1|: "
             f"{r['median_frozen_dev_bp']} bp; F034 event (below 25 bp): {r['f034_event']}.",
             f"- With an xyz mid: {r['with_xyz']}; median gap to xyz {r['median_xyz_gap_bp']} bp; share above 100 bp "
             f"{r['share_xyz_gap_over_100bp']}.", "", "| coin | frozen dev bp | xyz gap bp |", "|---|---|---|"]
    lines += [f"| {p['coin']} | {p['frozen_dev_bp']:.1f} | {p.get('xyz_gap_bp', float('nan')):.1f} |" for p in r["per"]]
    text = "\n".join(lines) + "\n"
    if a.out:
        if Path(a.out).exists():
            sys.exit(f"{a.out} exists: the read runs once")
        Path(a.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
