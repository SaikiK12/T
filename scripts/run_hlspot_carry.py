"""hlspot_carry_v1 (R444, M503): Hyperliquid spot-against-perp carry on one venue. Each slot is long a Hyperliquid
USDC spot pair (HYPE, or a Unit-bridged coin such as UBTC) and short the same coin's Hyperliquid perp, picked each day
by the perp's trailing realized funding. Rule, costs, windows and decision are in experiments/hlspot_carry_v1/PREREG.md.

The report and gate-1 decision are R441's, imported from the frozen scripts/run_xperp_carry.py. Data is the `hl_spot/`
folder of the data branch claude/okx-xperp-data (scripts/record_hl_spot.py). Paper only: it reads files and writes
results; no order.

usage: python scripts/run_hlspot_carry.py --data DIR --window gate0|forward [--until YYYY-MM-DD] [--out DIR]
       python scripts/run_hlspot_carry.py --data DIR --window forward --status      (no decision: a progress read)
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
_spec = importlib.util.spec_from_file_location("run_xperp_carry", ROOT / "scripts" / "run_xperp_carry.py")
rx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rx)

LANE = ROOT / "experiments" / "hlspot_carry_v1"
DAY = rx.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_hlspot_carry.py checks these against the PREREG text
LOOKBACK_D, ENTER_ANN, EXIT_ANN, SLOTS = rx.LOOKBACK_D, rx.ENTER_ANN, rx.EXIT_ANN, rx.SLOTS     # 7 d, 10%, 5%, 10
MIN_VOL_USD, HURDLE_ANN = rx.MIN_VOL_USD, rx.HURDLE_ANN                                       # $100k, 4%
LEVER = 2.0                    # perp margin N / 2; spot fully paid: capital = N (1 + 1/2)
FEE_BP = {"perp": 4.5, "spot": 7.0}         # Hyperliquid base-tier taker, per side
IMPACT_BP = {"perp": 5.0, "spot": 10.0}     # flat, per leg and side
WINDOWS = {"gate0": ("2025-01-01", "2026-11-10"), "forward": ("2026-11-11", None)}
LOOKS = {90: "2027-02-08", 180: "2027-05-09"}
DAILY_COLS = ["day", "held", "entries", "exits", "forced", "funding", "price", "gross", "net_1x", "net_2x", "net_3x"]
TRADE_COLS = ["day", "perp", "pair", "action", "forced", "signal_ann", "entered"]


def load(data):
    """Funding prints by perp, {(coin, close ms): close} and {(coin, close ms): quote volume} for both legs, pairs."""
    h = Path(data) / "hl_spot"
    f = rx.read_dir(h / "funding")
    f = pd.DataFrame({"coin": f.coin.astype(str), "t": f.time.astype(np.int64), "rate": f.rate.astype(float)}) \
        if len(f) else pd.DataFrame(columns=["coin", "t", "rate"])
    legs = {}
    for k in ("perp_1d", "spot_1d"):
        c = rx.read_dir(h / k)
        if not len(c):
            legs[k] = ({}, {})
            continue
        key = list(zip(c.coin.astype(str), c.ts.astype(np.int64) + DAY))
        legs[k] = (dict(zip(key, c.c.astype(float))), dict(zip(key, c.vol_base.astype(float) * c.c.astype(float))))
    pairs = json.loads((h / "pairs.json").read_text())["pairs"] if (h / "pairs.json").exists() else {}
    return f.drop_duplicates(["coin", "t"]), legs, {v["perp"]: p for p, v in pairs.items()}


def run(data, start, end):
    f, legs, perp_pair = load(data)
    (pclose, pvol), (sclose, svol) = legs["perp_1d"], legs["spot_1d"]
    by = {k: g.sort_values("t") for k, g in f.groupby("coin")}

    def trailing(coin, d):
        g = by.get(coin)
        if g is None or g.t.min() > d - LOOKBACK_D * DAY:          # needs a full lookback of prints
            return None
        w = g[(g.t > d - LOOKBACK_D * DAY) & (g.t <= d)]
        return float(w.rate.sum()) * 365 / LOOKBACK_D if len(w) else None

    def funding(coin, a, b):
        g = by.get(coin)
        return 0.0 if g is None else float(g[(g.t > a) & (g.t <= b)].rate.sum())

    per_trade_bp = sum(FEE_BP.values()) + sum(IMPACT_BP.values())   # both legs, one side each
    w = 1.0 / (SLOTS * (1 + 1 / LEVER))
    held, rows, trades = {}, [], []          # perp -> (spot pair, entered)
    for d in range(rx.ms(start), rx.ms(end) + DAY, DAY):
        # 1. book the interval d - 1 day -> d
        fund = price = 0.0
        forced = []
        for coin, (sp, _) in list(held.items()):
            a, b = d - DAY, d
            fund += w * funding(coin, a, b)
            p0, p1, s0, s1 = pclose.get((coin, a)), pclose.get((coin, b)), sclose.get((sp, a)), sclose.get((sp, b))
            if None in (p0, p1, s0, s1):
                forced.append(coin)
            else:
                price += w * (-(p1 / p0 - 1) + (s1 / s0 - 1))
        # 2. decide at d: exits, then entries
        sig = {c: trailing(c, d) for c in perp_pair}
        exits = [c for c in held if c in forced or sig.get(c) is None or sig[c] < EXIT_ANN]
        cost = {m: 0.0 for m in (1, 2, 3)}
        for c in exits:
            for m in cost:
                cost[m] += w * per_trade_bp * m / 1e4
            trades.append({"day": rx.day_label(d), "perp": c, "pair": held[c][0], "action": "exit",
                           "forced": c in forced, "signal_ann": sig.get(c), "entered": held[c][1]})
            del held[c]
        cands = []
        for c, s in sig.items():
            sp = perp_pair[c]
            if c in held or s is None or s < ENTER_ANN:
                continue
            if (c, d) not in pclose or (sp, d) not in sclose:
                continue
            if pvol.get((c, d), 0.0) < MIN_VOL_USD or svol.get((sp, d), 0.0) < MIN_VOL_USD:
                continue
            cands.append((-s, c, sp))
        entries = []
        for _, c, sp in sorted(cands)[: max(0, SLOTS - len(held))]:
            held[c] = (sp, rx.day_label(d))
            entries.append(c)
            for m in cost:
                cost[m] += w * per_trade_bp * m / 1e4
            trades.append({"day": rx.day_label(d), "perp": c, "pair": sp, "action": "enter", "forced": False,
                           "signal_ann": sig[c], "entered": rx.day_label(d)})
        gross = fund + price
        rows.append({"day": rx.day_label(d), "held": len(held), "entries": len(entries), "exits": len(exits),
                     "forced": len(forced), "funding": fund, "price": price, "gross": gross,
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
    daily, trades = run(a.data, start, end)
    rep = {"window": a.window, "start": start, "end": end, **rx.summary(daily)}
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
