"""Register O3b (docs/reviews/open_questions.md): is a one-day BTC option underpriced on some weekday, Sunday above
all? The registered read is in docs/reviews/reflection_20261125_greeks.md section 3, committed (428def4e) before the
refetched trades were opened. A measurement: no trade, no money, 0 trials.

For each date D (2022-01-01..2026-10-31):
- implied: amount-weighted IV of BTC options expiring D+1 08:00 UTC whose strike is within +-2% of the hour's index,
  pooled over the hours starting D 08:00 and D 09:00 (data/deribit_trades/BTC/flow); skip if under 5 BTC traded;
- premium: 0.7979 * IV * sqrt(23/8760), the at-the-money straddle from 09:00 to 08:00, in bp of spot;
- move: |ln P(D+1 08:00) / P(D 09:00)| from Binance BTCUSDT hourly closes (P(h) = close of the bar opening at h-1).
Reported by weekday of D: mean premium, mean move, their ratio, mean (move - premium) and a plain t; by year; and the
move to D+1 00:00 against the 15-hour premium (Sunday evening alone).

usage: python scripts/measure_daily_vrp.py [--out docs/reviews/o3b_daily_vrp.md]
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FLOW = ROOT / "data" / "deribit_trades" / "BTC" / "flow"
KLINES = ROOT / "data" / "klines_1h" / "BTCUSDT.parquet"
START, END = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2026-10-31", tz="UTC")
K_BAND, MIN_BTC, COST_BP = 0.02, 5.0, 16.0
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def straddle_bp(iv_pct, hours):
    return 0.7979 * iv_pct / 100 * math.sqrt(hours / 8760) * 1e4


def implied_by_day(flow):
    """{D (UTC midnight): (iv %, btc traded)} from hourly flow rows (columns t, expiry_ms, strike, index_price, buy,
    sell, iv)."""
    f = flow.copy()
    f["ts"] = pd.to_datetime(f["t"], unit="ms", utc=True)
    f["D"] = f["ts"].dt.floor("D")
    exp = pd.to_datetime(f["expiry_ms"], unit="ms", utc=True)
    keep = ((f["ts"].dt.hour.isin([8, 9])) & (exp == f["D"] + pd.Timedelta(hours=32))
            & ((f["strike"] / f["index_price"] - 1).abs() <= K_BAND) & f["iv"].notna())
    f = f[keep]
    f = f.assign(amt=f["buy"] + f["sell"])
    g = f.groupby("D").apply(lambda x: pd.Series({"iv": np.average(x["iv"], weights=x["amt"]) if x["amt"].sum() > 0
                                                  else np.nan, "btc": x["amt"].sum()}), include_groups=False)
    return g[g["btc"] >= MIN_BTC]


def moves(closes):
    """closes: Series of hourly closes indexed by bar open time (UTC). Returns DataFrame by D: move to D+1 08:00 and to
    D+1 00:00, in bp (absolute log moves from D 09:00)."""
    p = closes.copy()
    p.index = p.index + pd.Timedelta(hours=1)      # P(h) = close of the bar opening at h-1
    out = {}
    for D in pd.date_range(START, END, freq="D"):
        a = p.get(D + pd.Timedelta(hours=9))
        b = p.get(D + pd.Timedelta(hours=32))
        c = p.get(D + pd.Timedelta(hours=24))
        if a is None or b is None or not (a > 0 and b > 0):
            continue
        out[D] = {"move": abs(math.log(b / a)) * 1e4, "move_00": abs(math.log(c / a)) * 1e4 if c else np.nan}
    return pd.DataFrame.from_dict(out, orient="index")


def md(df, fmt="{:.2f}", index=False):
    """A Markdown table without the tabulate dependency."""
    d = df.reset_index() if index else df
    cell = lambda v: fmt.format(v) if isinstance(v, (float, np.floating)) and not np.isnan(v) else ("" if isinstance(  # noqa: E731
        v, (float, np.floating)) else str(v))
    head = "| " + " | ".join(str(c) for c in d.columns) + " |"
    sep = "|" + "---|" * len(d.columns)
    return "\n".join([head, sep] + ["| " + " | ".join(cell(v) for v in r) + " |" for r in d.itertuples(index=False)])


def table(df):
    rows = []
    for d in DAYS:
        x = df[df["wd"] == d]
        e = x["move"] - x["prem"]
        rows.append({"day": d, "n": len(x), "iv %": x["iv"].mean(), "premium bp": x["prem"].mean(),
                     "move bp": x["move"].mean(), "move/premium": x["move"].mean() / x["prem"].mean(),
                     "move - premium bp": e.mean(), "t": e.mean() / e.std(ddof=1) * math.sqrt(len(e)) if len(e) > 2
                     else np.nan,
                     "15h: move - premium bp": (x["move_00"] - x["prem15"]).mean()})
    return pd.DataFrame(rows)


def run(out):
    files = [f for f in sorted(FLOW.glob("*.parquet"))]
    flow = pd.concat([pd.read_parquet(f, columns=["t", "expiry_ms", "strike", "index_price", "buy", "sell", "iv"])
                      for f in files], ignore_index=True)
    imp = implied_by_day(flow)
    k = pd.read_parquet(KLINES)
    closes = pd.Series(k["close"].astype(float).values, index=pd.to_datetime(k["t"], unit="ms", utc=True))
    mv = moves(closes)
    df = imp.join(mv, how="inner")
    df = df[(df.index >= START) & (df.index <= END)]
    df["prem"] = straddle_bp(df["iv"], 23)
    df["prem15"] = straddle_bp(df["iv"], 15)
    df["wd"] = df.index.day_name().str[:3]
    t = table(df)
    by_year = df.assign(y=df.index.year, e=df["move"] - df["prem"]).pivot_table(index="y", columns="wd", values="e",
                                                                                aggfunc="mean")[DAYS]
    lines = ["# O3b read: one-day BTC option premium against the next day's move, by weekday (2022-01..2026-10)", "",
             f"Files: {len(files)} months of `data/deribit_trades/BTC/flow` ({files[0].stem}..{files[-1].stem}); "
             f"days kept: {len(df)}. Cost of a straddle round trip, for reference: about {COST_BP:.0f} bp.", "",
             md(t), "", "## Mean (move - premium) by year, bp", "",
             md(by_year, "{:.1f}", index=True)]
    Path(out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "reviews" / "o3b_daily_vrp.md"))
    a = ap.parse_args()
    if Path(a.out).exists():
        sys.exit(f"{a.out} exists: the registered read runs once")
    run(a.out)


if __name__ == "__main__":
    main()
