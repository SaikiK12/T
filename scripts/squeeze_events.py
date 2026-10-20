"""Negative-funding onsets on two venues, as event legs for the qx engine (R274 squeeze_v1).

Binance: R273's frozen legs (experiments/fundext_v1/legs.csv), negative kinds only, renamed bn_neg0.3 / bn_neg1 /
bn_neg2. They are priced on the Binance perp (column `perp`).

MEXC: the same onset rule on MEXC's settled funding (data/mexc_hist/funding), kinds mx_neg0.3 / mx_neg1 / mx_neg2,
priced on the MEXC perp (column `mexc`). An onset is a settlement whose rate is at or below -L with no settlement of the
same contract at or below -L in the previous 72 h. History starts 2025-04-01, so events start 72 h later.

The reserved MEXC-only coins (docs/GATES.md) are never read. A MEXC contract is used only if its base maps to a Binance
perp in the archive (data/klines_1h: BASEUSDT, 1000BASEUSDT or 1000000BASEUSDT, or the MEXC base itself with its
1000 prefix) and the two are the same coin: the median close of the Binance perp over the overlap, divided by the
multiplier, is within 3x of the MEXC perp's median close. The check reads price levels, not returns; contracts that
fail it are counted and dropped before their funding is read.

usage: python scripts/squeeze_events.py [--out DIR]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

BN_LEGS = ROOT / "experiments" / "fundext_v1" / "legs.csv"
MX = data.ROOT / "mexc_hist"
BN_KLINES = data.ROOT / "klines_1h"
MX_START, END = "2025-04-01", "2026-10-01"
LEVELS = (0.003, 0.01, 0.02)
GAP_H = 72
H = 3_600_000
MULTS = ((1, ""), (1000, "1000"), (1_000_000, "1000000"))


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def onsets(sym, t, r, first):
    """Negative-funding onsets of one contract (t ascending), kinds neg0.3 / neg1 / neg2."""
    out = []
    for level in LEVELS:
        last = None
        for i in np.where(-r >= level)[0]:
            if t[i] >= first and (last is None or t[i] - t[last] >= GAP_H * H):
                out.append((sym, f"neg{level * 100:g}", int(t[i]), float(r[i])))
            last = i
    return out


def binance_perp(base, perps):
    """(Binance perp, multiplier = Binance price / MEXC price) for a MEXC base, or None."""
    for m, p in MULTS:
        if p + base + "USDT" in perps:
            return p + base + "USDT", m
    for m, p in MULTS[1:]:
        if base.startswith(p) and base[len(p):] + "USDT" in perps:
            return base[len(p):] + "USDT", 1 / m
    return None


def mapping(lo, hi):
    """MEXC contracts that are Binance-listed coins, with the identity check. Returns (DataFrame, counts)."""
    perps = {p.stem for p in BN_KLINES.glob("*.parquet")}
    rows, n = [], {"contracts": 0, "no_binance_perp": 0, "mismatch": 0, "no_overlap": 0, "kept": 0}
    for c in json.loads((MX / "contracts.json").read_text()):
        if c.get("settle") != "USDT" or c.get("type") != 1:
            continue
        n["contracts"] += 1
        hit = binance_perp(c["base"], perps)
        if hit is None:
            n["no_binance_perp"] += 1          # MEXC-only: reserved, never read
            continue
        perp, mult = hit
        mk = MX / "klines_1h" / f"{c['symbol']}.parquet"
        if not mk.exists():
            n["no_overlap"] += 1
            continue
        a = pd.read_parquet(mk, columns=["t", "close"])
        b = pd.read_parquet(BN_KLINES / f"{perp}.parquet", columns=["t", "close"])
        a, b = a[(a.t >= lo) & (a.t < hi)], b[(b.t >= lo) & (b.t < hi)]
        both = a.merge(b, on="t", suffixes=("_m", "_b"))
        if len(both) < 24:
            n["no_overlap"] += 1
            continue
        ratio = float(both.close_b.median() / mult / both.close_m.median())
        if not 1 / 3 <= ratio <= 3:
            n["mismatch"] += 1
            continue
        n["kept"] += 1
        rows.append({"mexc": c["symbol"], "perp": perp, "mult": mult, "ratio": ratio})
    return pd.DataFrame(rows), n


def legs():
    bn = pd.read_csv(BN_LEGS)
    bn = bn[bn.kind.str.startswith("neg")].copy()
    bn["kind"] = "bn_" + bn.kind
    bn["mexc"] = ""
    lo, hi = ms(MX_START), ms(END)
    m, counts = mapping(lo, hi)
    rows = []
    for x in m.itertuples():
        f = pd.read_parquet(MX / "funding" / f"{x.mexc}.parquet", columns=["t", "rate"])
        f = f[(f.t >= lo) & (f.t < hi)].dropna().sort_values("t")
        rows += [(x.mexc, k, t, r) for _, k, t, r in onsets(x.mexc, f.t.values.astype(np.int64),
                                                             f.rate.values.astype(float), lo + GAP_H * H)]
    mx = pd.DataFrame(rows, columns=["mexc", "kind", "release_ms", "rate"])
    mx["kind"] = "mx_" + mx.kind
    mx["ticker"] = mx.mexc.str.replace("_USDT", "", regex=False)
    mx["perp"] = ""
    mx["window"] = "archive"
    cols = ["kind", "ticker", "perp", "mexc", "window", "release_ms", "rate"]
    d = pd.concat([bn[cols], mx[cols]], ignore_index=True)
    d = d.sort_values(["release_ms", "kind", "ticker"]).reset_index(drop=True)
    d.insert(0, "notice", np.arange(1, len(d) + 1))
    return d, m, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "experiments" / "squeeze_v1"))
    a = ap.parse_args()
    d, m, counts = legs()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / "legs.csv", index=False, float_format="%.8g")
    m.to_csv(out / "mexc_map.csv", index=False, float_format="%.6g")
    print(json.dumps(counts))
    y = pd.to_datetime(d.release_ms, unit="ms").dt.year
    print(pd.crosstab(d.kind, y).to_string())


if __name__ == "__main__":
    main()
