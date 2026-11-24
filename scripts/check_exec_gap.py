"""Post hoc diagnostic (2026-11-24, reflection cycle 3): the entry price gap of R525's kraken+hyperliquid trades, re-measured on
executable prices (Kraken hourly mark, Hyperliquid hourly close), against the engine's daily last-trade valuation.

usage: python scripts/check_exec_gap.py
"""
# Post hoc diagnostic: does the entry price gap converge when measured on executable prices?
# Kraken: hourly MARK close (index-anchored); Hyperliquid: hourly trade close (held, from 2026-04-24). R525's kraken+HL trades
# entered from 2026-04-26 are re-valued from the entry instant to the exit instant on these prices.
import sys, json, math, time, tomllib, urllib.request
sys.path.insert(0, ".")
import numpy as np, pandas as pd
from pathlib import Path
from lab import xfund as v1, xfund_v2 as v2
from scripts import run_carry_v2_audit as loader, run_gap_breadth as gb
sp = tomllib.loads(Path("experiments/gap_breadth_v1/spec.toml").read_text())
u = loader.load(sp, v2, {"kraken", "hyperliquid"})
sym = pd.read_csv("experiments/gap_breadth_v1/symbols.csv", dtype=str).fillna("").set_index("key")
vs = [u.names.index("kraken"), u.names.index("hyperliquid")]
_, trades = v2.replay(u, v2.Book(vs, *gb.BOOK), v2.window_start(u, vs, gb.BOOK[0]))
t_start = pd.Timestamp("2026-04-26").value // 10**6
trades = [t for t in trades if u.t0 + t["entry_day"] * v1.DAY >= t_start]
cache = {}
def kmark(s):
    if s in cache: return cache[s]
    out, frm, end = [], 1777161600, 1790812800
    while frm < end:
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(f"https://futures.kraken.com/api/charts/v1/mark/{s}/1h?from={frm}&to={end}", headers={"User-Agent": "lab"}), timeout=30))
        except Exception:
            break
        c = d.get("candles", [])
        if not c: break
        out += c; frm = c[-1]["time"] // 1000 + 3600; time.sleep(0.25)
        if not d.get("more_candles"): break
    s_ = pd.Series({x["time"] + 3600000: float(x["close"]) for x in out}).sort_index()   # stamp = candle close
    cache[s] = s_; return s_
def hl(s):
    p = Path(f"data/hyperliquid/candles_1h/{s}.parquet")
    if not p.exists(): return None
    d = pd.read_parquet(p, columns=["t", "close"]); return pd.Series(d.close.values, index=d.t.values + 3600000).sort_index()
def at(s, ms):
    s = s[s.index <= ms]; return float(s.iloc[-1]) if len(s) else None
def gap(a, b):
    r = math.log10(a / b); return (r - round(r)) * math.log(10)
rows = []
for t in trades:
    k, h = sym.at[t["coin"], "kraken"], sym.at[t["coin"], "hyperliquid"]
    if not k or not h: continue
    km, hs = kmark(k), hl(h)
    if hs is None or not len(km): continue
    e0, e1 = u.t0 + t["entry_day"] * v1.DAY, u.t0 + t["exit_day"] * v1.DAY
    a0, a1, b0, b1 = at(km, e0), at(km, e1), at(hs, e0), at(hs, e1)
    if None in (a0, a1, b0, b1): continue
    lo_is_k = t["long"] == "kraken"
    pl0, pl1, ps0, ps1 = (a0, a1, b0, b1) if lo_is_k else (b0, b1, a0, a1)
    rows.append({"coin": t["coin"], "g_in": gap(pl0, ps0), "price_exec": (pl1 / pl0 - 1) - (ps1 / ps0 - 1), "price_engine": t["price_pnl"]})
df = pd.DataFrame(rows); df = df[df.g_in.abs() < 0.05]
print("trades with executable prices:", len(df))
b = np.polyfit(df.g_in, df.price_exec, 1); be = np.polyfit(df.g_in, df.price_engine, 1)
print("slope on executable prices %.2f (corr %.2f); on the engine's daily last trades, same trades: %.2f" % (b[0], np.corrcoef(df.g_in, df.price_exec)[0, 1], be[0]))
q = pd.qcut(df.g_in, 4, labels=False, duplicates="drop")
print((df.groupby(q)[["g_in", "price_exec", "price_engine"]].mean() * 100).round(2).to_string())
print("mean |gap| at entry on executable prices: %.2f%%" % (df.g_in.abs().mean() * 100))
