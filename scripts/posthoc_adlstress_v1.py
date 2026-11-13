"""Post hoc for adlstress_v1 (R487): the 21:00-24:00 UTC window check, the empty 1h series, the S1 pairs left
unstressed by the close-versus-open rule, and the 1x-to-3x cost spread. Decides nothing.

Written after the run, in answer to review 2026-11-13-122155. Reads the lane's raw/ bodies (sha256 checked through the
frozen runner's verify_raw) and results/{books,pairs}.csv, reuses the frozen runner's parsing and candle lookups
without changing them, and writes experiments/adlstress_v1/results/posthoc.json.

Window check (R278 A under S1, naked long on Gate, Gate 1h bars): loss = (H21 - L) / P_e + 2 x c x N, H21 = high of
the 21:00 UTC bar, L = lowest low of the 21:00-23:00 bars, P_e and N as in the frozen runner (N = H / P_e of the full
day). The variant with the re-hedge cost on the window notional H21 / P_e is reported too.

Unstressed under S1: pairs with a Hyperliquid short whose D close is above its open, so the rule calls the long
profitable and leaves the Hyperliquid short un-ADL'd. ADL ran at 21:16-21:21 UTC near the day's low, when such a
short could have been in profit. The bound they would add if their Hyperliquid short had been ADL'd instead is
computed with the runner's own formula for a naked long.

usage: python scripts/posthoc_adlstress_v1.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_adlstress as A  # noqa: E402

HOUR = A.DAY // 24
R278A = "gate+hyperliquid L14d th5% K20"


def empty_hourly(candles):
    out = {}
    for (v, _), c in candles.items():
        rec = out.setdefault(v, {"legs": 0, "empty_1h": 0})
        rec["legs"] += 1
        rec["empty_1h"] += int(not len(c["h"]))
    return out


def window_check(pairs, candles):
    t0 = A.ms(A.D)
    s = pairs[(pairs.scenario == "S1") & pairs.stressed & (pairs.book == R278A)]
    full = win = win_h21 = 0.0
    used, skipped = [], []
    for _, r in s.iterrows():
        c = candles.get(("gate", r.coin))
        h = c["h"] if c is not None else pd.DataFrame()
        b = h[(h.t >= t0 + 21 * HOUR) & (h.t < t0 + 24 * HOUR)] if len(h) else h
        if r.naked != "long" or not len(b) or not (b.t == t0 + 21 * HOUR).any():
            skipped.append(r.coin)
            continue
        pe = A.close_at(c, A.ms(r.entry_day))
        h21, lo = float(b[b.t == t0 + 21 * HOUR].h.iloc[0]), float(b.l.min())
        full += r.loss_2
        win += (h21 - lo) / pe + 2 * A.COSTS[2] * r.N
        win_h21 += (h21 - lo) / pe + 2 * A.COSTS[2] * h21 / pe
        used.append(r.coin)
    k = 100.0 / (2 * A.SLOTS)
    return {"book": R278A, "pairs": len(used), "skipped": skipped, "full_day_2x_pct": full * k,
            "window_2x_pct": win * k, "window_2x_pct_cost_on_window_notional": win_h21 * k}


def unstressed(pairs, candles):
    s = pairs[(pairs.scenario == "S1") & ~pairs.stressed & (pairs.short == "hyperliquid")
              & (pairs.profitable == "long")]
    rows, add = [], {}
    for _, r in s.iterrows():
        hl = A.day_ohlc(candles.get(("hyperliquid", r.coin)))
        c = candles.get((r.long, r.coin))
        lo = A.day_ohlc(c)
        pe = A.close_at(c, A.ms(r.entry_day))
        loss = None
        if lo is not None and pe:
            _, h, l, _, _ = lo
            loss = (h - l) / pe + 2 * A.COSTS[2] * h / pe
            add[r.book] = add.get(r.book, 0.0) + loss * 100.0 / (2 * A.SLOTS)
        rows.append({"book": r.book, "coin": r.coin, "long": r.long, "hl_open": hl[0], "hl_low": hl[2],
                     "hl_close": hl[3], "hl_low_vs_open": hl[2] / hl[0] - 1.0, "loss_2x_entry_notional_if_stressed": loss})
    return rows, add


def cost_spread(books):
    return {r.book: {sc: {"1x": r[f"{sc}_1x_pct"], "3x": r[f"{sc}_3x_pct"],
                          "spread_1x_3x": r[f"{sc}_3x_pct"] - r[f"{sc}_1x_pct"]} for sc in ("S1", "S2")}
            for _, r in books.iterrows()}


def main():
    raw = A.LANE / "raw"
    candles = A.load_candles(raw, A.verify_raw(raw))
    pairs = pd.read_csv(A.LANE / "results" / "pairs.csv")
    books = pd.read_csv(A.LANE / "results" / "books.csv")
    rows, add = unstressed(pairs, candles)
    out = {"label": "post hoc, decides nothing", "empty_1h_by_venue": empty_hourly(candles),
           "window_check": window_check(pairs, candles), "s1_unstressed_hl_shorts": rows,
           "s1_2x_pct_added_if_stressed": add, "cost_spread": cost_spread(books)}
    (A.LANE / "results" / "posthoc.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("empty_1h_by_venue", "window_check", "s1_2x_pct_added_if_stressed")},
                     indent=1))
    for r in rows:
        print(f"{r['book']}: {r['coin']} long {r['long']}, HL low {r['hl_low_vs_open']:+.1%} vs open, "
              f"close {r['hl_close'] / r['hl_open'] - 1:+.1%}, 2x loss if stressed {r['loss_2x_entry_notional_if_stressed']:.3f} entry notionals")


if __name__ == "__main__":
    main()
