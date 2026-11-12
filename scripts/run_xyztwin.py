"""R477 xyztwin_v1, frozen in experiments/xyztwin_v1/PREREG.md: R475's carry rule on xyz index, ETF and metal perps,
each hedged with a USD UCITS ETF or ETC twin on the London Stock Exchange.

R475's frozen book (`scripts/run_hip3stock.py`: 5 slots, enter at >= 12%/yr trailing 28-day funding, exit below
6%/yr, M = 1/3, costs, liquidation, split guard, samples and verdict) with three changes, all forced by the twin:
- Marks at 16:00 UTC (the open of that 4-hour candle), within 30 minutes of the LSE close (16:30 London), instead of
  20:00 UTC. The twin's calendar is the LSE's.
- The twin's prices are scaled by a constant k (median perp/twin ratio over the pair's first 20 marks) so that R475's
  entry guard (perp/close within 10%) compares like with like. Returns, and so the book, do not depend on k.
- Identity is checked by daily log-return correlation >= 0.5 over the last 60 marks, without R475's 3% price band:
  an accumulating ETF drifts away from a price-return perp by its yield.
A (weeks ending by 2026-07-22) decides; B (to 2026-11-06) is reported.

usage: python scripts/run_xyztwin.py [--data data/xyztwin]
"""
import argparse
import contextlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_hip3stock as hs  # noqa: E402  (frozen in R475)
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "xyztwin_v1"
DATA = ROOT / "data" / "xyztwin"
REGISTRY = "R477"
MARK_HOUR, K_MARKS, ID_MARKS = 16, 20, 60
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def mark_ms(day):
    """The perp mark of an LSE trading day: the open of the 4-hour candle starting at 16:00 UTC."""
    return hs.day_ms(day) + MARK_HOUR * hs.HOUR


@contextlib.contextmanager
def london_marks():
    """R475's Market and book read the module's mark_ms at call time; point it at 16:00 UTC while this lane runs."""
    old, hs.mark_ms = hs.mark_ms, mark_ms
    try:
        yield
    finally:
        hs.mark_ms = old


def correlated(mk):
    a, b = np.log(mk.perp).diff().tail(ID_MARKS - 1), np.log(mk.close).diff().tail(ID_MARKS - 1)
    if len(a) < 19 or a.std() == 0 or b.std() == 0:
        return False
    return float(np.corrcoef(a, b)[0, 1]) >= hs.MIN_CORR


def pair(twin, candles, funding, perp_bp, max_lev, name):
    raw = hs.Market(name, twin, candles, funding, perp_bp, max_lev)
    if len(raw.days) < K_MARKS:
        return None, float("nan")
    k = float((raw.perp / raw.close).head(K_MARKS).median())
    scaled = twin.assign(close=twin["close"] * k, adjclose=twin["adjclose"] * k)
    return hs.Market(name, scaled, candles, funding, perp_bp, max_lev), k


def load(data):
    uni = pd.read_csv(data / "universe.csv")
    markets, dropped, scale = {}, [], {}
    for _, r in uni.iterrows():
        t = r["ticker"]
        if not r["equity"]:
            dropped.append((t, "twin not in USD or no xyz market"))
            continue
        f, c = pd.read_csv(data / "xyz" / f"{t}_funding.csv"), pd.read_csv(data / "xyz" / f"{t}_4h.csv")
        if not len(f) or not len(c):
            dropped.append((t, "no funding or candles"))
            continue
        bp = hs.PERP_BP_GROWTH if str(r["growth"]) == "enabled" else hs.PERP_BP_FULL
        mk, k = pair(pd.read_parquet(data / "yahoo" / f"{t}.parquet"), c, f, bp, float(r["max_lev"]), t)
        if mk is None or not correlated(mk):
            dropped.append((t, "identity"))
            continue
        markets[t], scale[t] = mk, k
    bill = pd.read_parquet(data / "yahoo" / "IRX.parquet").set_index("date")["close"].sort_index()
    return markets, bill, dropped, scale


def run(lane=LANE, data=DATA, check=True):
    with london_marks():
        return _run(lane, data, check)


def _run(lane, data, check):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    log(f"data files verified: {hs.verify_data(data)}")
    markets, bill, dropped, scale = load(data)
    log(f"markets {len(markets)}; dropped {len(dropped)}: {dropped}")
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    out = {"registry": REGISTRY, "markets": sorted(markets), "dropped": dropped, "scale": scale, "variants": {}}
    first = max(min(d for mk in markets.values() for d in mk.days), hs.BOOK_START)
    for name, params in hs.VARIANTS.items():
        daily, trades = hs.book(markets, bill, params, first, hs.END)
        wk = hs.weekly(daily)
        a, b = wk[wk["last"] <= hs.A_END], wk[wk["last"] > hs.A_END]
        ta, tb = trades[trades["closed"] <= hs.A_END], trades[trades["closed"] > hs.A_END]
        out["variants"][name] = {"params": params, "A": hs.stats(a, ta), "B": hs.stats(b, tb),
                                 "all": hs.stats(wk, trades),
                                 "trades_by_name": {k: int(v) for k, v in trades["ticker"].value_counts().items()}}
        daily.to_csv(res / f"daily_{name}.csv", index=False)
        wk.to_csv(res / f"weekly_{name}.csv", index=False)
        trades.to_csv(res / f"trades_{name}.csv", index=False)
    state, text = hs.verdict(out["variants"]["decide"]["A"])
    out.update({"state": state, "text": text})
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    log(state, text)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args()
    run(data=Path(a.data))


if __name__ == "__main__":
    main()
