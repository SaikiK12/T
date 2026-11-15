"""Price the two reserved-sample carry PASSes against R404's measured book costs.

R286 C14 and R391 both PASSED on reserved samples and both were blocked on the same sentence:
"measure those book costs ... before the lane is written". R404 `book_costs_v1` is now recording
those costs. This script joins its committed band medians to each book's assumed cost unit and
reports the multiple. No download, no strategy test, no new signal.

Limit: R404's per-symbol snapshots live in gitignored data/, so only the committed venue x ADV-band
medians in its journal status.json are available here. A band median is not the book's own cost;
the exact per-contract join needs the recorder's files and is left to the cost lane's owner.

usage: python scripts/reserved_cost_check.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "experiments/book_costs_v1/journal/status.json"
OUT = ROOT / "research/reserved_cost_check_20261115.json"

# Each book's frozen 1x cost unit, from its own lane (bp per leg per side).
BOOKS = {
    "R286_C14_binance_gate": {
        "lane": "experiments/reserved_batch1", "verdict": "PASS",
        "net_1x_pct_yr": 2.86, "net_2x_pct_yr": 1.86, "net_3x_pct_yr": 0.85,
        "cost_1x_bp_leg_side": 7.0, "venues": ("binance", "gate"),
        "cost_source": "experiments/reserved_batch1/carry.toml costs = [0.0007, 0.0014, 0.0021]",
        "note": "2020 sample; R390 xfund_bg_fwd is its earned forward lane (RUNNING)",
    },
    "R391_kucoin_dydx_lighter_mexc": {
        "lane": "experiments/reserved_batch2", "verdict": "PASS",
        "net_1x_pct_yr": 2.48, "net_2x_pct_yr": 1.93, "net_3x_pct_yr": 1.38,
        "cost_1x_bp_leg_side": 7.0, "venues": ("kucoin", "dydx", "lighter", "mexc"),
        "note": "526 days from 2025-05-12; 5.3 of 20 slots held; top 10 days 95% of the sum",
    },
    "R392_GLT_gate_mexc": {
        "lane": "experiments/reserved_batch3", "verdict": "PASS at 1x only",
        "net_1x_pct_yr": 0.73, "net_2x_pct_yr": 0.11, "net_3x_pct_yr": -0.51,
        "cost_1x_bp_leg_side": 7.0, "venues": ("gate", "mexc"),
        "note": "Gate long tail, 31 bases; already negative at 3x",
    },
}


def bands(status):
    return {(r["venue"], r["band_usd"]): r for r in status["by_venue_band"]}


def main():
    st = json.loads(STATUS.read_text())
    by = bands(st)
    out = {
        "source": str(STATUS.relative_to(ROOT)),
        "source_sha256": __import__("hashlib").sha256(STATUS.read_bytes()).hexdigest(),
        "recorder_snapshots": st["snapshots"],
        "recorder_symbols": st["symbols"],
        "recorder_last_ms": st["last_ms"],
        "limits": [
            "band medians, not the book's own per-contract cost: R404's per-symbol files are gitignored",
            "a venue with no recorded band (binance, gate, lighter) is NOT priced here",
            "no strategy test, no new signal, no reserved read; this prices already-published nets",
        ],
        "books": {},
    }
    for name, b in BOOKS.items():
        rows = []
        for venue in b["venues"]:
            for (v, band), r in sorted(by.items()):
                if v != venue:
                    continue
                rows.append({
                    "venue": v, "band_usd": band, "symbols": r["symbols"],
                    "median_half_spread_bp": r["median_half_spread_bp"],
                    "median_side_10k_bp": r["median_side_10k_bp"],
                    "unfilled_share_10k": r["unfilled_share_10k"],
                    "multiple_of_assumed_1x": r["median_side_10k_bp"] / b["cost_1x_bp_leg_side"],
                })
        priced = [r for r in rows if r["multiple_of_assumed_1x"] > 3.0]
        out["books"][name] = {
            **{k: v for k, v in b.items() if k != "venues"},
            "venues": list(b["venues"]),
            "bp_per_day_on_book_capital_1x": b["net_1x_pct_yr"] * 100 / 365,
            "measured_bands": rows,
            "bands_above_3x": len(priced),
            "bands_priced": len(rows),
            "survives_3x_on_every_priced_band": bool(rows) and not priced,
            "unpriced_venues": [v for v in b["venues"] if not any(r["venue"] == v for r in rows)],
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    for name, b in out["books"].items():
        print(f"\n{name}: {b['verdict']}, {b['net_1x_pct_yr']:+.2f}%/yr at 1x "
              f"({b['bp_per_day_on_book_capital_1x']:.3f} bp/day on book capital)")
        for r in b["measured_bands"]:
            print(f"  {r['venue']:8s} {r['band_usd']:16s} n={r['symbols']:3d} "
                  f"{r['median_side_10k_bp']:7.1f} bp/side = {r['multiple_of_assumed_1x']:5.1f}x assumed 1x")
        if b["unpriced_venues"]:
            print(f"  not recorded by R404: {', '.join(b['unpriced_venues'])}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
