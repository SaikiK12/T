"""hlspot_pm_v1 (R445, M504): R444's Hyperliquid spot-against-perp carry on the two pairs whose spot token has a listed
portfolio-margin LTV (HYPE and BTC), fully deployed: the book's capital is split equally across the pairs held, and
the spot, paid in full, backs the short perp's margin, with a USDC buffer for the perp's losses. Rule, costs, windows
and decision are in experiments/hlspot_pm_v1/PREREG.md.

R444's loader (scripts/run_hlspot_carry.py) reads the data; the report and gate-1 decision are R441's (the frozen
scripts/run_xperp_carry.py). Paper only: it reads files and writes results; no order.

usage: python scripts/run_hlspot_pm.py --data DIR --window gate0|forward [--until YYYY-MM-DD] [--out DIR]
       python scripts/run_hlspot_pm.py --data DIR --window forward --status      (no decision: a progress read)
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("run_hlspot_carry", ROOT / "scripts" / "run_hlspot_carry.py")
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)
rx = rs.rx

LANE = ROOT / "experiments" / "hlspot_pm_v1"
DAY = rx.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_hlspot_pm.py checks these against the PREREG text
PERPS = ("HYPE", "BTC")                      # spot tokens with a listed portfolio-margin LTV (0.65 and 0.5)
LOOKBACK_D, ENTER_ANN, EXIT_ANN = rs.LOOKBACK_D, rs.ENTER_ANN, rs.EXIT_ANN       # 7 d, 10%, 5% (R444's)
MIN_VOL_USD, HURDLE_ANN = rs.MIN_VOL_USD, rs.HURDLE_ANN                          # $100k, 4%
BUFFER = 0.10                                # USDC kept for the perp's losses, per unit of notional
CAPITAL_PER_NOTIONAL = {"pm": 1 + BUFFER, "no_pm": 1 + 1 / rs.LEVER}            # decision: "pm"; "no_pm" reported
FEE_BP, IMPACT_BP = rs.FEE_BP, rs.IMPACT_BP  # perp 4.5 + 5, spot 7.0 + 10 bp per side
WINDOWS = {"gate0": ("2025-01-01", "2026-11-10"), "forward": ("2026-11-11", None)}
LOOKS = {90: "2027-02-08", 180: "2027-05-09"}
DAILY_COLS = ["day", "held", "entries", "exits", "forced", "turnover", "funding", "price", "gross", "net_1x", "net_2x",
              "net_3x"]
TRADE_COLS = ["day", "perp", "pair", "action", "forced", "signal_ann", "entered"]


def run(data, start, end, capital="pm"):
    """Daily book on capital, per unit: each held pair carries notional 1 / (k x capital per notional), k = pairs held
    after the day's decisions. Weights change only on entry and exit days, and the change is costed on both legs."""
    f, legs, perp_pair = rs.load(data)
    perp_pair = {c: p for c, p in perp_pair.items() if c in PERPS}
    (pclose, pvol), (sclose, svol) = legs["perp_1d"], legs["spot_1d"]
    by = {k: g.sort_values("t") for k, g in f.groupby("coin")}
    cpn = CAPITAL_PER_NOTIONAL[capital]

    def trailing(coin, d):
        g = by.get(coin)
        if g is None or g.t.min() > d - LOOKBACK_D * DAY:          # needs a full lookback of prints
            return None
        w = g[(g.t > d - LOOKBACK_D * DAY) & (g.t <= d)]
        return float(w.rate.sum()) * 365 / LOOKBACK_D if len(w) else None

    def funding(coin, a, b):
        g = by.get(coin)
        return 0.0 if g is None else float(g[(g.t > a) & (g.t <= b)].rate.sum())

    per_unit_bp = sum(FEE_BP.values()) + sum(IMPACT_BP.values())   # both legs, one side each, per unit of notional
    held, wt, rows, trades = {}, {}, [], []      # perp -> (spot pair, entered); perp -> notional per unit capital
    for d in range(rx.ms(start), rx.ms(end) + DAY, DAY):
        # 1. book the interval d - 1 day -> d at yesterday's weights
        fund = price = 0.0
        forced = []
        for coin, (sp, _) in list(held.items()):
            a, b = d - DAY, d
            fund += wt[coin] * funding(coin, a, b)
            p0, p1, s0, s1 = pclose.get((coin, a)), pclose.get((coin, b)), sclose.get((sp, a)), sclose.get((sp, b))
            if None in (p0, p1, s0, s1):
                forced.append(coin)
            else:
                price += wt[coin] * (-(p1 / p0 - 1) + (s1 / s0 - 1))
        # 2. decide at d: exits, then entries (R444's rule; every eligible pair enters, no slot limit)
        sig = {c: trailing(c, d) for c in perp_pair}
        exits = [c for c in held if c in forced or sig.get(c) is None or sig[c] < EXIT_ANN]
        for c in exits:
            trades.append({"day": rx.day_label(d), "perp": c, "pair": held[c][0], "action": "exit",
                           "forced": c in forced, "signal_ann": sig.get(c), "entered": held[c][1]})
            del held[c]
        entries = []
        for c, s in sorted(sig.items(), key=lambda x: (-(x[1] or 0.0), x[0])):
            sp = perp_pair[c]
            if c in held or s is None or s < ENTER_ANN:
                continue
            if (c, d) not in pclose or (sp, d) not in sclose:
                continue
            if pvol.get((c, d), 0.0) < MIN_VOL_USD or svol.get((sp, d), 0.0) < MIN_VOL_USD:
                continue
            held[c] = (sp, rx.day_label(d))
            entries.append(c)
            trades.append({"day": rx.day_label(d), "perp": c, "pair": sp, "action": "enter", "forced": False,
                           "signal_ann": s, "entered": rx.day_label(d)})
        # 3. reweight: equal notional across the pairs held, costed on the change of each pair's notional
        new = {c: 1.0 / (len(held) * cpn) for c in held}
        turnover = sum(abs(new.get(c, 0.0) - wt.get(c, 0.0)) for c in set(new) | set(wt))
        wt = new
        gross = fund + price
        cost = {m: turnover * per_unit_bp * m / 1e4 for m in (1, 2, 3)}
        rows.append({"day": rx.day_label(d), "held": len(held), "entries": len(entries), "exits": len(exits),
                     "forced": len(forced), "turnover": turnover, "funding": fund, "price": price, "gross": gross,
                     "net_1x": gross - cost[1], "net_2x": gross - cost[2], "net_3x": gross - cost[3]})
    return pd.DataFrame(rows, columns=DAILY_COLS), pd.DataFrame(trades, columns=TRADE_COLS)


def decide_gate0(s):
    """Gate 0 decides only a stop."""
    e1 = s["1x"]["excess_ann"]
    return "NULL (stop)" if e1 is None or e1 < 0 else "CONTINUE to gate 1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--window", choices=sorted(WINDOWS), required=True)
    ap.add_argument("--until", help="last day of a forward read (default: the last day the data covers)")
    ap.add_argument("--status", action="store_true", help="forward progress read: no decision")
    ap.add_argument("--out")
    a = ap.parse_args()
    from lab import prereg
    prereg.verify(LANE / "PREREG.md")
    pinned = rx.check_inputs(LANE / "PREREG.md")
    if a.window == "gate0" and rx.data_head(a.data) != pinned:
        raise SystemExit(f"gate 0 reads the data branch at {pinned} only; {a.data} is at {rx.data_head(a.data)}")
    start, end = WINDOWS[a.window]
    if a.window == "forward":
        c = rx.read_dir(Path(a.data) / "hl_spot" / "perp_1d")
        last = rx.day_label(int(c.ts.astype(np.int64).max()) + DAY) if len(c) else start
        end = a.until or last
    daily, trades = run(a.data, start, end, "pm")
    rep = {"window": a.window, "start": start, "end": end, **rx.summary(daily)}
    nd, _ = run(a.data, start, end, "no_pm")
    rep["reported_no_pm"] = rx.summary(nd)
    if a.window == "gate0":
        rep["decision"] = decide_gate0(rep)
    elif not a.status:
        n = rep["days"]
        look = max((k for k in LOOKS if n >= k), default=None)
        rep["decision"] = rx.decide(rep, look) if look else f"no look reached ({n} scored days)"
    out = Path(a.out) if a.out else LANE / "results" / (a.window + ("_status" if a.status else ""))
    rx.write(out, daily, trades, rep)
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
