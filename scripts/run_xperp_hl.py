"""xperp_hl_v1 (R443, M502): cross-venue funding carry between OKX Europe crypto X-Perps and Hyperliquid perps, the
two perp venues found reachable from France. Each slot is short the venue paying more trailing funding and long the
other. Rule, costs, windows and decision are in experiments/xperp_hl_v1/PREREG.md.

The OKX side and the book's report (summary, gate-1 decision) are R441's, imported from the frozen
scripts/run_xperp_carry.py. Hyperliquid data is the `hl/` folder of the same data branch
(scripts/record_hl_daily.py). Paper only: it reads files and writes results; no order.

usage: python scripts/run_xperp_hl.py --data DIR --window gate0|forward [--until YYYY-MM-DD] [--out DIR]
       python scripts/run_xperp_hl.py --data DIR --window forward --status      (no decision: a progress read)
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

LANE = ROOT / "experiments" / "xperp_hl_v1"
DAY = rx.DAY
# ---- the frozen rule (PREREG "Rule"); tests/test_run_xperp_hl.py checks these against the PREREG text
LOOKBACK_D, ENTER_ANN, EXIT_ANN, SLOTS = rx.LOOKBACK_D, rx.ENTER_ANN, rx.EXIT_ANN, rx.SLOTS     # 7 d, 10%, 5%, 10
MIN_VOL_USD, HURDLE_ANN = rx.MIN_VOL_USD, rx.HURDLE_ANN                                       # $100k, 4%
LEVER = 2.0                    # each leg margined at 2x: capital = N (1/2 + 1/2)
FEE_BP = {"okx": 5.0, "hl": 4.5}      # taker, per side: OKX EEA regular; Hyperliquid base tier
DEFAULT_IMPACT_BP = 5.0        # per leg and side: Hyperliquid always, OKX when no snapshot of the last 24 h is held
WINDOWS = {"gate0": ("2026-08-20", "2026-11-10"), "forward": ("2026-11-11", None)}
LOOKS = {90: "2027-02-08", 180: "2027-05-09"}
DAILY_COLS = ["day", "held", "entries", "exits", "forced", "funding", "price", "gross", "net_1x", "net_2x",
              "net_3x"]
TRADE_COLS = ["day", "instId", "coin", "direction", "action", "forced", "spread_ann", "entered"]


def load_hl(data):
    """Hyperliquid funding prints, daily closes and quote volumes, and the coin -> OKX base map."""
    h = Path(data) / "hl"
    f = rx.read_dir(h / "funding")
    f = pd.DataFrame({"coin": f.coin.astype(str), "t": f.time.astype(np.int64), "rate": f.rate.astype(float)}) \
        if len(f) else pd.DataFrame(columns=["coin", "t", "rate"])
    c = rx.read_dir(h / "candles_1d")
    close = dict(zip(zip(c.coin.astype(str), c.ts.astype(np.int64) + DAY), c.c.astype(float))) if len(c) else {}
    vol = dict(zip(zip(c.coin.astype(str), c.ts.astype(np.int64) + DAY), c.vol_base.astype(float) * c.c.astype(float))) \
        if len(c) else {}
    coins = json.loads((h / "coins.json").read_text())["coins"] if (h / "coins.json").exists() else {}
    return f.drop_duplicates(["coin", "t"]), close, vol, coins


def run(data, start, end, books_ok=True):
    f, cd, books, listings = rx.load(data)
    hf, hclose, hvol, coins = load_hl(data)
    base_to_hl = {b: c for c, b in coins.items()}
    mark = rx.closes(cd["mark_1d"])
    vol = rx.closes(cd["trade_1d"], "vol_quote") if len(cd["trade_1d"]) else {}
    okx_f = {k: g.sort_values("t") for k, g in f.groupby("instId")}
    hl_f = {k: g.sort_values("t") for k, g in hf.groupby("coin")}
    first_listing = listings[min(listings)] if listings else {}
    if not books_ok:
        books = pd.DataFrame()

    def listed(d):
        lab = rx.day_label(d)
        keys = [k for k in listings if k <= lab]
        return listings[max(keys)] if keys else first_listing

    def trailing(g, d):
        if g is None or g.t.min() > d - LOOKBACK_D * DAY:
            return None
        w = g[(g.t > d - LOOKBACK_D * DAY) & (g.t <= d)]
        return float(w.rate.sum()) * 365 / LOOKBACK_D if len(w) else None

    def summed(g, a, b):
        return 0.0 if g is None else float(g[(g.t > a) & (g.t <= b)].rate.sum())

    def cost_bp(inst, side_okx, action, d, m):
        """side_okx: the OKX leg's position ("short" or "long")."""
        okx_side = {("enter", "short"): "sell", ("enter", "long"): "buy",
                    ("exit", "short"): "buy", ("exit", "long"): "sell"}[(action, side_okx)]
        imp = rx.impact(books, inst, "xperp", okx_side, d)
        tot = FEE_BP["okx"] + (DEFAULT_IMPACT_BP if imp is None else max(imp, 0.0))
        tot += FEE_BP["hl"] + DEFAULT_IMPACT_BP
        return tot * m

    w = 1.0 / (SLOTS * (1 / LEVER + 1 / LEVER))
    held, rows, trades = {}, [], []          # inst -> (hl coin, direction, entered); direction: "hl_short"/"okx_short"
    t0, t1 = rx.ms(start), rx.ms(end)
    for d in range(t0, t1 + DAY, DAY):
        lst = listed(d)
        # 1. book the interval d - 1 day -> d
        fund = price = 0.0
        forced = []
        for inst, (coin, dirn, _) in list(held.items()):
            a, b = d - DAY, d
            fo, fh = summed(okx_f.get(inst), a, b), summed(hl_f.get(coin), a, b)
            fund += w * ((fh - fo) if dirn == "hl_short" else (fo - fh))
            m0, m1, h0, h1 = mark.get((inst, a)), mark.get((inst, b)), hclose.get((coin, a)), hclose.get((coin, b))
            if None in (m0, m1, h0, h1):
                forced.append(inst)
            else:
                ro, rh = m1 / m0 - 1, h1 / h0 - 1
                price += w * ((ro - rh) if dirn == "hl_short" else (rh - ro))
        # 2. decide at d: exits, then entries
        spread = {}
        for inst, base in lst.items():
            coin = base_to_hl.get(base)
            if coin is None:
                continue
            so, sh = trailing(okx_f.get(inst), d), trailing(hl_f.get(coin), d)
            spread[inst] = (coin, None if so is None or sh is None else sh - so)
        exits = []
        for inst, (coin, dirn, _) in held.items():
            s = spread.get(inst, (coin, None))[1]
            held_s = None if s is None else (s if dirn == "hl_short" else -s)
            if inst in forced or inst not in lst or held_s is None or held_s < EXIT_ANN:
                exits.append(inst)
        cost = {m: 0.0 for m in (1, 2, 3)}
        for inst in exits:
            coin, dirn, ent = held[inst]
            for m in cost:
                cost[m] += w * cost_bp(inst, "short" if dirn == "okx_short" else "long", "exit", d, m) / 1e4
            trades.append({"day": rx.day_label(d), "instId": inst, "coin": coin, "direction": dirn, "action": "exit",
                           "forced": inst in forced, "spread_ann": spread.get(inst, (coin, None))[1], "entered": ent})
            del held[inst]
        cands = []
        for inst, (coin, s) in spread.items():
            if inst in held or s is None or abs(s) < ENTER_ANN:
                continue
            if (inst, d) not in mark or (coin, d) not in hclose:
                continue
            if vol.get((inst, d), 0.0) < MIN_VOL_USD or hvol.get((coin, d), 0.0) < MIN_VOL_USD:
                continue
            cands.append((-abs(s), inst, coin, "hl_short" if s > 0 else "okx_short"))
        entries = []
        for _, inst, coin, dirn in sorted(cands)[: max(0, SLOTS - len(held))]:
            held[inst] = (coin, dirn, rx.day_label(d))
            entries.append(inst)
            for m in cost:
                cost[m] += w * cost_bp(inst, "short" if dirn == "okx_short" else "long", "enter", d, m) / 1e4
            trades.append({"day": rx.day_label(d), "instId": inst, "coin": coin, "direction": dirn, "action": "enter",
                           "forced": False, "spread_ann": spread[inst][1], "entered": rx.day_label(d)})
        gross = fund + price
        rows.append({"day": rx.day_label(d), "held": len(held), "entries": len(entries), "exits": len(exits),
                     "forced": len(forced), "funding": fund, "price": price, "gross": gross,
                     "net_1x": gross - cost[1], "net_2x": gross - cost[2], "net_3x": gross - cost[3]})
    # explicit columns: a forward read before its first scored day gives an empty, still summarizable table
    return pd.DataFrame(rows, columns=DAILY_COLS), pd.DataFrame(trades, columns=TRADE_COLS)


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
        _, cd, _, _ = rx.load(a.data)
        last = rx.day_label(int(cd["mark_1d"].ts.max()) + DAY) if len(cd["mark_1d"]) else start
        end = a.until or last
    daily, trades = run(a.data, start, end, books_ok=(a.window == "forward"))
    rep = {"window": a.window, "start": start, "end": end, **rx.summary(daily)}
    if a.window == "forward" and not a.status:
        n = rep["days"]
        look = max((k for k in LOOKS if n >= k), default=None)
        rep["decision"] = rx.decide(rep, look) if look else f"no look reached ({n} scored days)"
    out = Path(a.out) if a.out else LANE / "results" / (a.window + ("_status" if a.status else ""))
    rx.write(out, daily, trades, rep)
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
