"""Funding-onset event legs on the reserved 2020 rows, for reserved batch 1's R273 and R274 candidates (docs/GATES.md).

The rule is R273's (scripts/funding_events.py), applied to another window: an event is the onset of an extreme funding
settlement on a Binance USD-M perp, a settled rate at least L in one sign (L = 0.3%, 1%, 2%) with no settlement of the
same perp reaching L in that sign in the previous 72 h. Rows before `start` are dropped before anything is computed, so
events start 72 h after it, exactly as R273's start in 2021. R274's Binance kinds are R273's negative kinds renamed
bn_neg0.3 / bn_neg1 / bn_neg2 (scripts/squeeze_events.py), with an empty `mexc` column.

Two files, each in its lane's column layout, every row labelled `window` = the --window argument:
- fundext_legs.csv: notice, kind, ticker, perp, window, release_ms, rate (as experiments/fundext_v1/legs.csv);
- squeeze_legs.csv: notice, kind, ticker, perp, mexc, window, release_ms, rate (the Binance rows of
  experiments/squeeze_v1/legs.csv).

Rows before 2021 are the reserved sample: a start before 2021-01-01 needs --prereg, a frozen PREREG that declares
RESERVED-2020-READ (lab.panel.check_reserved). tests/test_reserved_legs.py checks that the 2021-26 output equals R273's
and R274's frozen Binance legs byte for byte, so the rule is the same one.

usage: python scripts/reserved_legs.py --out DIR --start 2020-01-01 --end 2021-01-01 --window reserved_2020
                                       --prereg experiments/reserved_batch1/PREREG.md
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, panel  # noqa: E402

SRC = data.ROOT / "fundingRate"
LEVELS = (0.003, 0.01, 0.02)
GAP_H = 72
H = 3_600_000


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def onsets(sym, t, r, first):
    """R273's onset events of one perp's settled funding (t ascending): (perp, kind, release_ms, rate)."""
    out = []
    for sign in (1, -1):
        for level in LEVELS:
            last = None
            for i in np.where(sign * r >= level)[0]:
                if t[i] >= first and (last is None or t[i] - t[last] >= GAP_H * H):
                    out.append((sym, f"{'pos' if sign > 0 else 'neg'}{level * 100:g}", int(t[i]), float(r[i])))
                last = i
    return out


def fundext_legs(start, end, window, src=SRC):
    lo, hi = ms(start), ms(end)
    rows = []
    for p in sorted(Path(src).glob("*.parquet")):
        f = pd.read_parquet(p, columns=["t", "rate"])
        f = f[(f.t >= lo) & (f.t < hi)].dropna().sort_values("t")      # earlier rows are dropped before any use
        rows += onsets(p.stem, f.t.values.astype(np.int64), f.rate.values.astype(float), lo + GAP_H * H)
    d = pd.DataFrame(rows, columns=["perp", "kind", "release_ms", "rate"])
    d = d.sort_values(["release_ms", "kind", "perp"]).reset_index(drop=True)
    d.insert(0, "notice", np.arange(1, len(d) + 1))
    d.insert(2, "ticker", d.perp)
    d["window"] = window
    return d[["notice", "kind", "ticker", "perp", "window", "release_ms", "rate"]]


def squeeze_legs(fx):
    bn = fx[fx.kind.str.startswith("neg")].copy()
    bn["kind"] = "bn_" + bn.kind
    bn["mexc"] = ""
    bn = bn.sort_values(["release_ms", "kind", "ticker"]).reset_index(drop=True)
    bn["notice"] = np.arange(1, len(bn) + 1)
    return bn[["notice", "kind", "ticker", "perp", "mexc", "window", "release_ms", "rate"]]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--window", required=True)
    ap.add_argument("--prereg", default=None)
    a = ap.parse_args(argv)
    panel.check_reserved(a.start, a.prereg)
    fx = fundext_legs(a.start, a.end, a.window)
    sq = squeeze_legs(fx)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fx.to_csv(out / "fundext_legs.csv", index=False, float_format="%.8g")
    sq.to_csv(out / "squeeze_legs.csv", index=False, float_format="%.8g")
    print(fx.groupby("kind").size().to_string())


if __name__ == "__main__":
    main()
