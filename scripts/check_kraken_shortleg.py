"""Does the Kraken 1.5x stake rule survive the book's short legs? (descriptive, reflection cycle 11, 2026-11-25)

Replays R525's kraken+hyperliquid book (seen, in sample) with R525's engine, takes the Kraken leg of every position
(long +1 or short -1) and re-values the Kraken account within each day on Kraken's own hourly MARK candles (public charts
API): equal notional across the open Kraken legs (weight 1/n), path = sum of weight x side x (mark_h / mark at the day's
first hour - 1). Reports the worst hourly account loss per day (fraction of notional) and an upper bound from each leg's
own worst hourly high or low (not simultaneous), against the liquidation distance (1/L - mm)/(1 + mm).

usage: python scripts/check_kraken_shortleg.py
"""
import json
import sys
import time
import tomllib
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from lab import xfund as v1, xfund_v2 as v2  # noqa: E402
from scripts import run_carry_v2_audit as loader, run_gap_breadth as gb  # noqa: E402

H = 3_600_000


def kmark(sym, frm, end, cache={}):
    """Hourly Kraken mark candles (open time ms -> o, h, l, c)."""
    if sym in cache:
        return cache[sym]
    out, f = [], frm // 1000
    while f < end // 1000:
        try:
            req = urllib.request.Request(f"https://futures.kraken.com/api/charts/v1/mark/{sym}/1h?from={f}&to={end // 1000}",
                                         headers={"User-Agent": "lab-research-fetch/1.0"})
            d = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception:
            break
        c = d.get("candles", [])
        if not c:
            break
        out += c
        f = c[-1]["time"] // 1000 + 3600
        time.sleep(0.25)
        if not d.get("more_candles"):
            break
    df = pd.DataFrame([{"t": int(x["time"]), "o": float(x["open"]), "h": float(x["high"]), "l": float(x["low"]),
                        "c": float(x["close"])} for x in out]).drop_duplicates("t").set_index("t").sort_index() \
        if out else pd.DataFrame(columns=["o", "h", "l", "c"])
    cache[sym] = df
    return df


def main():
    sp = tomllib.loads(Path("experiments/gap_breadth_v1/spec.toml").read_text())
    u = loader.load(sp, v2, {"kraken", "hyperliquid"})
    sym = pd.read_csv("experiments/gap_breadth_v1/symbols.csv", dtype=str).fillna("").set_index("key")
    vs = [u.names.index("kraken"), u.names.index("hyperliquid")]
    _, trades = v2.replay(u, v2.Book(vs, *gb.BOOK), v2.window_start(u, vs, gb.BOOK[0]))
    rows = []
    for t in trades:
        coin = t["coin"]
        side = 1 if t["long"] == "kraken" else (-1 if t["short"] == "kraken" else 0)
        if side == 0:
            continue
        e = u.t0 + t["entry_day"] * v1.DAY
        x = u.t0 + (t["exit_day"] if t.get("exit_day") is not None else u.nd - 1) * v1.DAY
        rows.append({"coin": coin, "side": side, "entry": int(e), "exit": int(x)})
    P = pd.DataFrame(rows)
    print(f"Kraken legs: {len(P)} ({(P.side > 0).sum()} long, {(P.side < 0).sum()} short); "
          f"{pd.to_datetime(P.entry.min(), unit='ms').date()} .. {pd.to_datetime(P.exit.max(), unit='ms').date()}")
    frm, end = int(P.entry.min()) - v1.DAY, int(P.exit.max()) + v1.DAY
    marks = {}
    for c in sorted(P.coin.unique()):
        s = sym.loc[c, "kraken"] if c in sym.index and "kraken" in sym.columns else ""
        if not s:
            continue
        m = kmark(s, frm, end)
        if len(m):
            marks[c] = m
    print(f"marks fetched for {len(marks)} of {P.coin.nunique()} coins")
    days = pd.date_range(pd.to_datetime(frm, unit="ms").normalize(), pd.to_datetime(end, unit="ms").normalize(),
                         freq="D")
    out = []
    for d in days:
        d0 = int(d.value // 10**6)
        d1 = d0 + v1.DAY
        op = P[(P.entry <= d0) & (P.exit > d0) & P.coin.isin(marks)]
        if op.empty:
            continue
        w = 1.0 / len(op)
        path = np.zeros(24)
        ub = 0.0
        worst_leg = (0.0, "", 0)
        for r in op.itertuples():
            m = marks[r.coin]
            day = m[(m.index >= d0) & (m.index < d1)]
            if len(day) < 2:
                continue
            base = day.o.iloc[0]
            c = (day.c.to_numpy() / base - 1)[:24]
            path[:len(c)] += w * r.side * c
            adverse = (day.h.max() / base - 1) if r.side < 0 else (1 - day.l.min() / base)
            ub += w * adverse
            if adverse > worst_leg[0]:
                worst_leg = (adverse, r.coin, r.side)
        out.append({"day": d.date(), "n": len(op), "short_share": float((op.side < 0).mean()),
                    "worst_path": float(-path.min()), "upper_bound": ub, "worst_leg": worst_leg[0],
                    "worst_leg_coin": worst_leg[1], "worst_leg_side": worst_leg[2]})
    D = pd.DataFrame(out)
    print(f"days with an open Kraken account: {len(D)}; mean legs {D.n.mean():.1f}; mean short share "
          f"{D.short_share.mean():.0%}")
    print("worst intraday account loss (fraction of notional), on the simultaneous hourly path:")
    for q in (0.5, 0.95, 0.99, 1.0):
        print(f"  quantile {q:.2f}: {D.worst_path.quantile(q):.1%}")
    print("upper bound (each leg's own worst hourly extreme, not simultaneous):")
    for q in (0.5, 0.95, 0.99, 1.0):
        print(f"  quantile {q:.2f}: {D.upper_bound.quantile(q):.1%}")
    top = D.sort_values("worst_path", ascending=False).head(5)
    print("\nworst five days (path):")
    print(top[["day", "n", "short_share", "worst_path", "upper_bound", "worst_leg", "worst_leg_coin",
               "worst_leg_side"]].to_string(index=False))
    tl = D.sort_values("worst_leg", ascending=False).head(5)
    print("\nlargest single-leg adverse moves within a day:")
    print(tl[["day", "n", "worst_leg", "worst_leg_coin", "worst_leg_side"]].to_string(index=False))
    print("\nliquidation distance (1/L - mm)/(1 + mm):")
    for L in (1.0, 1.5, 2.0, 3.0):
        for mm in (0.05, 0.25):
            print(f"  L {L}, mm {mm:.0%}: {(1 / L - mm) / (1 + mm):.0%}")


if __name__ == "__main__":
    main()
