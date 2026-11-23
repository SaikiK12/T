"""Stress for a levered Deribit + Hyperliquid design-gap book (R520's coins): worst 24-hour and 72-hour moves from
Deribit's hourly closes, per coin and for an equal-weight basket, and the leverage at which each venue's cross-margin
account would have survived them, with once-a-day rebalancing (lab.margin). Descriptive; no trade, no order.

usage: python scripts/stress_dhl.py   (prints JSON)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import margin  # noqa: E402

START = "2023-06-01"
OLD = ["BTC", "ETH", "SOL", "XRP", "AVAX", "ADA", "DOT", "ALGO", "BCH", "DOGE", "LINK", "LTC", "NEAR", "TRX", "UNI"]
MM = {"BTC": 0.0125, "ETH": 0.02}           # Hyperliquid: half the initial margin at max leverage (BTC 40x, ETH 25x)
MM_ALT = 0.05                               # 10x alts; assumed the same on Deribit (not read from its docs)


def hourly(base):
    p = pd.read_parquet(ROOT / "data" / "deribit_perps" / "prices_1h" / f"{base}.parquet")
    s = pd.Series(p.close.to_numpy(float), index=pd.to_datetime(p.t, unit="ms"))
    return s[s.index >= START].resample("1h").last().ffill()


def worst(s, hours):
    r = s / s.shift(hours) - 1
    return float(r.min()), float(r.max())


def main():
    px = {b: hourly(b) for b in OLD}
    per = {b: {f"{h}h": worst(px[b], h) for h in (24, 72)} for b in OLD}
    basket = pd.concat(px, axis=1).pct_change().mean(axis=1).fillna(0).add(1).cumprod()
    bw = {f"{h}h": worst(basket, h) for h in (24, 72)}
    rows = []
    for lev in (1, 2, 3, 4, 5):                   # total notional (both legs) / capital
        n = lev / 2                               # notional per leg per unit of capital
        for name, mm in (("BTC", MM["BTC"]), ("alt", MM_ALT)):
            e_l, e_s = margin.split(1.0, n, mm, mm)
            rows.append({"leverage": lev, "coins": name, "liq_move_long_pct": 100 * margin.liq_move(e_l, [(n, mm)]),
                         "liq_move_short_pct": 100 * margin.liq_move(e_s, [(-n, mm)])})
    out = {"window": [START, str(basket.index[-1].date())], "coins": OLD,
           "basket_worst_pct": {k: [round(100 * v[0], 1), round(100 * v[1], 1)] for k, v in bw.items()},
           "per_coin_worst_24h_pct": {b: [round(100 * per[b]["24h"][0], 1), round(100 * per[b]["24h"][1], 1)]
                                      for b in OLD},
           "liquidation_moves": rows}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
