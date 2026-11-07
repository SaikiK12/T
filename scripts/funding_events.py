"""Extreme-funding events on every Binance USD-M perp, as event legs for the qx engine (R273 fundext_v1).

An event is the onset of an extreme funding settlement: settlement t of perp S where the settled rate is at least a
level L in one sign (pos: longs pay, neg: shorts pay), and no settlement of S in the previous 72 h reached L in that
sign. Kinds: pos0.3, pos1, pos2, neg0.3, neg1, neg2 (L = 0.3%, 1%, 2%; nested, so a 2% onset can also be a 0.3%
onset). release_ms is the settlement time: qx enters at the close of the hour that opens at the settlement.

Reads only data/fundingRate rows from 2021-01-01 on: the 2020 rows are the reserved sample (docs/GATES.md) and are
dropped before anything is computed, so events start on 2021-01-04 (72 h of lookback). No price is read.

usage: python scripts/funding_events.py [--out DIR]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

SRC = data.ROOT / "fundingRate"
START, END = "2021-01-01", "2026-10-01"
LEVELS = (0.003, 0.01, 0.02)
GAP_H = 72
H = 3_600_000


def kind(sign, level):
    return f"{'pos' if sign > 0 else 'neg'}{level * 100:g}"


def events(sym, f):
    """Onset events of one perp's settled funding (t ascending, rows from START on)."""
    t, r = f.t.values.astype(np.int64), f.rate.values.astype(float)
    first = int(pd.Timestamp(START, tz="UTC").value // 10**6) + GAP_H * H
    out = []
    for sign in (1, -1):
        for level in LEVELS:
            hit = np.where(sign * r >= level)[0]
            last = None
            for i in hit:
                if t[i] >= first and (last is None or t[i] - t[last] >= GAP_H * H):
                    out.append((sym, kind(sign, level), int(t[i]), float(r[i])))
                last = i
    return out


def legs(src=SRC):
    lo = int(pd.Timestamp(START, tz="UTC").value // 10**6)
    hi = int(pd.Timestamp(END, tz="UTC").value // 10**6)
    rows = []
    for p in sorted(Path(src).glob("*.parquet")):
        f = pd.read_parquet(p, columns=["t", "rate"])
        f = f[(f.t >= lo) & (f.t < hi)].dropna().sort_values("t")       # 2020 is dropped before any use
        rows += events(p.stem, f)
    d = pd.DataFrame(rows, columns=["perp", "kind", "release_ms", "rate"])
    d = d.sort_values(["release_ms", "kind", "perp"]).reset_index(drop=True)
    d.insert(0, "notice", np.arange(1, len(d) + 1))
    d.insert(2, "ticker", d.perp)
    d["window"] = "archive"
    return d[["notice", "kind", "ticker", "perp", "window", "release_ms", "rate"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "experiments" / "fundext_v1"))
    a = ap.parse_args()
    d = legs()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / "legs.csv", index=False, float_format="%.8g")
    print(d.groupby("kind").size().to_string())


if __name__ == "__main__":
    main()
