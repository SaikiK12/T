"""Unlock events for the unlock-short lane (E01, docs/OLD_SESSION_EDGES.md S1) from a DefiLlama emissions snapshot
(scripts/fetch_unlocks.py). Reads the calendar and, for the symbol check only, each mapped perp's last archived close.
No returns are computed here: the outputs are frozen with the lane's PREREG before any statistic.

Token -> perp map (symbol_map.csv):
- the ticker is the one DefiLlama's index prices the token under (tokenPrice[0].symbol);
- a Binance USD-M perp matches when <T>USDT, 1000<T>USDT or 1000000<T>USDT has an archive file (multiplier 1, 1e3, 1e6);
- otherwise a MEXC USDT perp from data/mexc_hist/contracts.json (base == T) makes the token MEXC-only (reserved);
- the old session's exclusions (GRAM, ETH, BNB, POL, FTM) are kept;
- check: the perp's last traded close (volume > 0) over (index price x multiplier) must lie in [1/3, 3] when the
  perp still trades on the archive's last day ("verified"); outside it, the pair is a ticker collision ("mismatch", dropped); a perp
  that stopped trading earlier cannot be checked ("unverified", kept, and reported apart in the lane) unless it
  traded before the token's first calendar event ("predates", another coin on the same ticker, dropped).
- two tokens on one perp: the verified one is kept; otherwise both are dropped ("collision").

Event rule (R179): cliff allocations in categories insiders or privateSale, summed per token and UTC day D; the day
qualifies when the sum is at least 1% of max supply; per perp, a qualifying day is kept when it is at least 14 days
after the last kept one. Window label by D: reserved_2020 (D-37 before 2021-01-01, as the lane reads no 2020 rows),
archive (close of D no later than the archive's last close), post_archive (after that, up to the snapshot day) and
forward (after the snapshot day); MEXC-only tokens get reserved_mexc (from 2025-04-01 + 37 days, the reserved
MEXC sample) or no_prices instead of archive/post_archive.

usage: python scripts/unlock_events.py [--snapshot data/unlocks/2026-10-20] [--out experiments/unlocks_v1]
"""
import argparse
import ast
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, panel  # noqa: E402

CATS = ("insiders", "privateSale")
MIN_FRAC, SPACING_DAYS = 0.01, 14
EXCLUDE = {"GRAM", "ETH", "BNB", "POL", "FTM"}
MEXC_START = "2025-04-01"
MULTS = ((1, ""), (1000, "1000"), (1_000_000, "1000000"))
DAY = 86_400_000


def load(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def index_rows(snap):
    """gecko_id -> (ticker, price, maxSupply) from the emissions index (some fields arrive as strings)."""
    out = {}
    for r in load(snap / "emissionsIndex.json.gz")["data"]:
        tp = r.get("tokenPrice") or []
        if isinstance(tp, str):
            try:
                tp = ast.literal_eval(tp)
            except (ValueError, SyntaxError):
                tp = []
        sym = tp[0].get("symbol") if tp else None
        price = tp[0].get("price") if tp else None
        ms = float(r["maxSupply"]) if r.get("maxSupply") not in (None, "", "None") else np.nan
        if r.get("gecko_id"):
            out[r["gecko_id"]] = (sym.upper() if sym else None, price, ms)
    return out


def traded(sym, root):
    """First and last open time with volume, and the last such close: after a delisting the archive keeps flat
    zero-volume bars."""
    df = pd.read_parquet(root / "klines_1h" / f"{sym}.parquet", columns=["t", "close", "volume"])
    df = df[df.volume > 0]
    return int(df.t.iloc[0]), int(df.t.iloc[-1]), float(df.close.iloc[-1])


def calendar_start(x):
    ts = [int(e["timestamp"]) for e in (x.get("metadata") or {}).get("unlockEvents") or []]
    return min(ts) * 1000 if ts else None


def symbol_map(snap, root=None):
    root = Path(root or data.ROOT)
    idx = index_rows(snap)
    perps = {p.stem for p in (root / "klines_1h").glob("*.parquet")}
    mexc = {c["base"].upper(): c["symbol"] for c in json.loads((root / "mexc_hist" / "contracts.json").read_text())}
    end_ms = panel.ms(data.END)                       # traded on the archive's last day counts as still trading
    rows = []
    for f in sorted((snap / "protocols").glob("*.json.gz")):
        x = load(f)
        gid = x.get("gecko_id")
        sym, price, ms_idx = idx.get(gid, (None, None, np.nan))
        ms_file = (x.get("supplyMetrics") or {}).get("maxSupply")
        max_supply = float(ms_file) if ms_file else ms_idx
        row = {"slug": f.name[:-8], "gecko_id": gid, "ticker": sym, "max_supply": max_supply, "index_price": price,
               "perp": "", "mult": np.nan, "venue": "", "check": "unmapped", "price_ratio": np.nan}
        if sym and sym in EXCLUDE:
            row["check"] = "excluded"
        elif sym:
            hit = next(((m, p + sym + "USDT") for m, p in MULTS if p + sym + "USDT" in perps), None)
            if hit:
                m, perp = hit
                t_first, t_last, c_last = traded(perp, root)
                start = calendar_start(x)
                row.update(perp=perp, mult=m, venue="binance")
                if t_last < end_ms:
                    row["check"] = "predates" if start and t_first < start else "unverified"
                elif price:
                    ratio = c_last / (price * m)
                    row.update(price_ratio=ratio, check="verified" if 1 / 3 <= ratio <= 3 else "mismatch")
                else:
                    row["check"] = "unverified"
            elif sym in mexc:
                row.update(perp=mexc[sym], mult=1, venue="mexc_only", check="mexc_only")
        rows.append(row)
    m = pd.DataFrame(rows)
    live = m.check.isin(["verified", "unverified"])
    for perp, g in m[live].groupby("perp"):
        if len(g) > 1:
            ok = g.index[g.check == "verified"]
            drop = g.index.difference(ok) if len(ok) == 1 else g.index
            m.loc[drop, "check"] = "collision"
    return m


def cliff_days(x, max_supply):
    """UTC day (ms) -> (tokens, fraction of max supply) for insiders + privateSale cliffs."""
    acc = {}
    for e in (x.get("metadata") or {}).get("unlockEvents") or []:
        amt = sum(float(c.get("amount") or 0) for c in e.get("cliffAllocations") or [] if c.get("category") in CATS)
        if amt > 0:
            d = int(e["timestamp"]) * 1000 // DAY * DAY
            acc[d] = acc.get(d, 0.0) + amt
    return {d: (a, a / max_supply) for d, a in sorted(acc.items())}


def events(snap, smap, snapshot_day):
    keep = smap[smap.check.isin(["verified", "unverified", "mexc_only"])]
    archive_last = panel.ms(data.END)                       # day D whose close (00:00 of D+1) is the archive's last
    first_ok = panel.ms(panel.START) + 37 * DAY
    snap_ms = panel.ms(snapshot_day)
    raw = []
    for r in keep.itertuples():
        if not (r.max_supply and np.isfinite(r.max_supply) and r.max_supply > 0):
            continue
        x = load(snap / "protocols" / f"{r.slug}.json.gz")
        for d, (amt, frac) in cliff_days(x, r.max_supply).items():
            if frac >= MIN_FRAC:
                raw.append({"perp": r.perp, "venue": r.venue, "check": r.check, "slug": r.slug, "ticker": r.ticker,
                            "mult": r.mult, "day_ms": d, "tokens": amt, "frac_max_supply": frac})
    ev = pd.DataFrame(raw).sort_values(["perp", "day_ms"]).reset_index(drop=True)
    kept, last = [], {}
    for i, r in ev.iterrows():
        if r.perp in last and r.day_ms - last[r.perp] < SPACING_DAYS * DAY:
            continue
        kept.append(i)
        last[r.perp] = r.day_ms
    ev = ev.loc[kept].reset_index(drop=True)
    ev.insert(0, "day", pd.to_datetime(ev.day_ms, unit="ms", utc=True).dt.strftime("%Y-%m-%d"))
    ev["window"] = np.select([ev.day_ms < first_ok, ev.day_ms <= archive_last, ev.day_ms <= snap_ms],
                             ["reserved_2020", "archive", "post_archive"], "forward")
    past = (ev.venue == "mexc_only") & (ev.window != "forward")   # MEXC history starts 2025-04-01
    ev.loc[past, "window"] = np.where(ev.day_ms[past] >= panel.ms(MEXC_START) + 37 * DAY, "reserved_mexc", "no_prices")
    return ev.sort_values(["day_ms", "perp"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(data.ROOT / "unlocks" / "2026-10-20"))
    ap.add_argument("--out", default=str(ROOT / "experiments" / "unlocks_v1"))
    a = ap.parse_args()
    snap, out = Path(a.snapshot), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    smap = symbol_map(snap)
    smap.to_csv(out / "symbol_map.csv", index=False)
    ev = events(snap, smap, snap.name)
    ev.to_csv(out / "events.csv", index=False)
    print(smap.check.value_counts().to_string())
    print(ev.groupby(["venue", "window"]).size().to_string())


if __name__ == "__main__":
    main()
