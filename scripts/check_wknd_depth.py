"""Weekend book depth of 24/7 stock perps: capacity of the closed-market fade class (descriptive, costs only).

Reads the hourly book snapshots recorded on `claude/xyz-books-data` (`scripts/record_xyz_books.py`): for trade.xyz
(`books/`) the walked cost from mid of a $1k/$5k/$10k/$25k market order, and for Lighter (`lighter/books/`) of $1k/$10k.

It never reads a mid over time, a weekend move or a return, so the sealed forward lanes R463/R467 stay sealed (their
journals are not opened). Universes: R462's 76 xyz stock markets and R465's 50 Lighter stock markets.

Windows (New York time): SunE = Sunday 18:30-19:30 (R462's entry), SunX = Sunday 21:30-22:30 (its exit),
WKND = Friday 20:00 to Sunday 18:00, RTH = Monday-Friday 09:30-16:00.

    python scripts/check_wknd_depth.py [--ref origin/claude/xyz-books-data]
"""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[1]


def window(ts_ms: int) -> str | None:
    t = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone(NY)
    wd, hm = t.weekday(), t.hour + t.minute / 60  # Monday = 0
    if wd == 6 and 18.5 <= hm < 19.5:
        return "SunE"
    if wd == 6 and 21.5 <= hm < 22.5:
        return "SunX"
    if (wd == 4 and hm >= 20) or wd == 5 or (wd == 6 and hm < 18):
        return "WKND"
    if wd < 5 and 9.5 <= hm < 16:
        return "RTH"
    return None


def git_lines(ref: str, prefix: str) -> list[str]:
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout.split()
    return sorted(p for p in out if p.startswith(prefix) and p.endswith(".csv") and p.count("/") == prefix.count("/"))


def read(ref: str, path: str) -> list[dict]:
    txt = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout
    return list(csv.DictReader(io.StringIO(txt)))


def fnum(x: str) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def round_trip(row: dict, n: str, buy: str = "buy_{}_bp", sell: str = "sell_{}_bp") -> float:
    b, s = fnum(row.get(buy.format(n))), fnum(row.get(sell.format(n)))
    return float("inf") if b is None or s is None else b + s


def summarise(costs: dict, sizes: list[str], label: str) -> list[str]:
    """costs[(window, market)][size] -> list of round-trip bp. Median per market, then the distribution."""
    lines = [f"## {label}", "", "| window | markets | snapshots | " + " | ".join(
        f"median RT ${s} | share ≤10 bp ${s}" for s in sizes) + " |",
             "|---|---|---|" + "---|---|" * len(sizes)]
    for w in ("SunE", "SunX", "WKND", "RTH"):
        mk = [m for (ww, m) in costs if ww == w]
        if not mk:
            continue
        snaps = sum(len(costs[(w, m)][sizes[0]]) for m in mk)
        cells = []
        for s in sizes:
            per = [median(costs[(w, m)][s]) for m in mk]
            med = median(per) if per else float("nan")
            share = sum(1 for p in per if p <= 10) / len(per)
            cells.append(f"{med:.1f}" if med != float("inf") else "unfilled")
            cells.append(f"{share:.0%}")
        lines.append(f"| {w} | {len(mk)} | {snaps} | " + " | ".join(cells) + " |")
    return lines


def capacity(costs: dict, sizes: dict[str, float], w: str, budget: float) -> dict[str, float]:
    """Largest size (USD) per market whose median round trip in window w is within budget (0 if none)."""
    cap = {}
    for (ww, m), by in costs.items():
        if ww != w:
            continue
        cap[m] = max([usd for s, usd in sizes.items() if median(by[s]) <= budget], default=0.0)
    return cap


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/claude/xyz-books-data")
    a = ap.parse_args()

    xyz_u = {f"xyz:{r['coin']}" for r in csv.DictReader(open(ROOT / "experiments/xyzwknd_v1/universe.csv"))}
    lt_u = {r["coin"] for r in csv.DictReader(open(ROOT / "experiments/ltwknd_v1/universe.csv"))}

    xs = ["1000", "5000", "10000", "25000"]
    xc: dict = defaultdict(lambda: defaultdict(list))
    for p in git_lines(a.ref, "books/"):
        for r in read(a.ref, p):
            if r.get("coin") not in xyz_u:
                continue
            w = window(int(r["ts"]))
            if w:
                for s in xs:
                    xc[(w, r["coin"])][s].append(round_trip(r, s))

    ls = ["1k", "10k"]
    lc: dict = defaultdict(lambda: defaultdict(list))
    for p in git_lines(a.ref, "lighter/books/"):
        for r in read(a.ref, p):
            if r.get("symbol") not in lt_u:
                continue
            w = window(int(r["ts"]))
            if w:
                for s in ls:
                    lc[(w, r["symbol"])][s].append(round_trip(r, s))

    out = summarise(xc, xs, "trade.xyz, R462's universe: round-trip cost from mid (bp), before fees")
    out += [""] + summarise(lc, ls, "Lighter, R465's universe: round-trip cost from mid (bp), zero fee")
    out += ["", "## Capacity on Sunday evening (largest size per market within a round-trip budget, entry window)", ""]
    for name, costs, sizes in (("xyz", xc, {s: float(s) for s in xs}), ("Lighter", lc, {"1k": 1e3, "10k": 1e4})):
        for budget in (10.0, 20.0):
            for w in ("SunE", "SunX"):
                v = sorted(capacity(costs, sizes, w, budget).values())
                if v:
                    out.append(f"- {name}, {w}, budget {budget:.0f} bp: {len(v)} markets; median size "
                               f"${median(v):,.0f}; sum over markets ${sum(v):,.0f}; markets at 0: "
                               f"{sum(1 for x in v if x == 0)}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
