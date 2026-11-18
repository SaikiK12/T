"""xfund_eea_v1 (R508): R275's cross-venue funding carry book on Kraken + Hyperliquid, two venues reachable from France
whose funding rules differ.

- **Hyperliquid** (official funding docs): F = average premium + clamp(0.01%/8 h - premium, +-0.05%), paid hourly. Its
  interest term floors funding at 0.00125%/h (about 11%/yr) while premiums are small, as Binance's does.
- **Kraken Futures** linear perps (`PF_*`): an hourly time-weighted premium with no interest term in the public
  specifications, paid hourly; a positive rate is paid by longs (Kraken EEA product sheet).
- R507 found that a floor-against-no-floor pair (Binance + Bitfinex) carried +5.2%/yr at 1x over 2021-2026. This lane
  asks whether the same rule, unchanged, earns on the pair the owner could trade.

Held data only (no fetch): `data/kraken_hist/open` (funding: the API's last year only) and `data/hyperliquid`, both
rebuilt on 2026-11-17..18. Kraken's `reserved/` long tail is never read.

Steps:
1. `manifest` (before the freeze): the symbol table by the rule below and the sha256 of every data file it names, into
   the lane folder. It reads contract lists and file names only, never a price or a rate. Refuses once frozen.
2. `run` (once, after the freeze): verifies the PREREG, its pinned inputs and every data file against the manifest,
   then runs `lab.xfund` on kraken+hyperliquid with R275's spec values and decides by R391's rule.

**Symbol rule.** A Kraken `open` contract's `base` and a Hyperliquid coin pair up when their names match after
Hyperliquid's k-prefix becomes `1000` (`lab.venues.hl_base`) and a leading `1000000` or `1000` is removed from both.
When several Hyperliquid coins match, the one with no multiplier prefix wins, then the first by name. Bases in
`NOT_CRYPTO` (metals, energy, equities and ETFs, stablecoins, gold tokens) are left out. Both venues need a daily
candle file and a funding file. The engine's identity guard then decides, day by day, whether they trade the same coin.

usage: python scripts/run_xfund_eea.py manifest | run
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund  # noqa: E402
from lab.venues import hl_base  # noqa: E402
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507 runner: book, summarize, decide, trade_pnl)

LANE = ROOT / "experiments" / "xfund_eea_v1"
DATA = ROOT / "data"
START, END = "2025-11-17", "2026-11-15"          # inclusive days; Kraken's served funding starts 2025-11-17 09:00
PRIMARY = ("kraken+hyperliquid", 14, 0.05, 20)
SECONDARY = ("kraken+hyperliquid", 14, 0.10, 20)  # reported, not decided
NOT_CRYPTO = {"USDC", "PAXG", "XAUT", "XAU", "XAG", "NATGAS", "NBIS", "SKHY", "SAMSUNG", "SNDK", "SOXL", "SOXS",
              "INTC", "MU", "PONS", "EWY", "MRVL", "AMD", "PLTR", "EWZ"}
VENUES = [{"name": "kraken", "prices": "kraken_hist/open/candles_1d", "vol": "volume",
           "funding": "kraken_hist/open/funding"},
          {"name": "hyperliquid", "prices": "hyperliquid/candles_1d", "vol": "volume", "funding": "hyperliquid/funding"}]
BAR_H = 24                                         # both price files are daily candles


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


def norm(name):
    for p in ("1000000", "1000"):
        if name.startswith(p) and len(name) > len(p):
            return name[len(p):]
    return name


def symbol_table(kraken_contracts, hl_coins):
    """[{key, kraken, hyperliquid}] by the symbol rule; `kraken_contracts` rows have symbol, base, route."""
    hl = {}
    for c in sorted(hl_coins):
        hl.setdefault(norm(hl_base(c)), []).append(c)
    rows = []
    for r in kraken_contracts:
        if r["route"] != "open" or r["base"] in NOT_CRYPTO:
            continue
        cands = hl.get(norm(r["base"]))
        if not cands:
            continue
        pick = sorted(cands, key=lambda c: (hl_base(c) != norm(hl_base(c)), c))[0]
        rows.append({"key": norm(r["base"]), "kraken": r["symbol"], "hyperliquid": pick})
    return pd.DataFrame(rows, columns=["key", "kraken", "hyperliquid"]).drop_duplicates("key").reset_index(drop=True)


def files_for(sym, data=None):
    data = Path(data or DATA)
    out = []
    for _, r in sym.iterrows():
        for v in VENUES:
            for kind in ("prices", "funding"):
                out.append(data / v[kind] / f"{r[v['name']]}.parquet")
    return out


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_table(data=None):
    data = Path(data or DATA)
    k = pd.read_csv(data / "kraken_hist" / "contracts.csv", dtype=str)
    have_k = {p.stem for p in (data / "kraken_hist/open/candles_1d").glob("*.parquet")} & \
             {p.stem for p in (data / "kraken_hist/open/funding").glob("*.parquet")}
    k = k[k.symbol.isin(have_k)]
    hl = {p.stem for p in (data / "hyperliquid/candles_1d").glob("*.parquet")} & \
         {p.stem for p in (data / "hyperliquid/funding").glob("*.parquet")}
    return symbol_table(k.to_dict("records"), hl)


def manifest(lane=None, data=None):
    lane, data = Path(lane or LANE), Path(data or DATA)
    if (lane / "PREREG.sha256").exists():
        raise SystemExit("frozen: the manifest is written before the freeze only")
    sym = build_table(data)
    lane.mkdir(parents=True, exist_ok=True)
    sym.to_csv(lane / "symbols.csv", index=False)
    files = {str(p.relative_to(data)): sha256(p) for p in files_for(sym, data)}
    (lane / "data_manifest.json").write_text(json.dumps({"root": "data", "files": files}, indent=1, sort_keys=True))
    print(json.dumps({"symbols": len(sym), "files": len(files)}))
    return sym


def check_data(lane=None, data=None):
    lane, data = Path(lane or LANE), Path(data or DATA)
    m = json.loads((lane / "data_manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if not (data / p).exists() or sha256(data / p) != h]
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from the manifest, e.g. {bad[:3]}")
    return len(m)


def check_inputs(prereg=None):
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        got = sha256(ROOT / path)
        if got != digest:
            raise SystemExit(f"{path} changed since the freeze: {got} != {digest}")
    return pairs


def load_universe(sym, t0, nd, data=None):
    data = Path(data or DATA)
    series = [[xfund.load_daily(data / v["prices"] / f"{r[v['name']]}.parquet",
                                data / v["funding"] / f"{r[v['name']]}.parquet", v["vol"], BAR_H, t0, nd)
               for v in VENUES] for _, r in sym.iterrows()]
    return xfund.Universe(sym.key.tolist(), [v["name"] for v in VENUES], series, t0, nd, 30, 0.9, 20)


def funding_profile(sym, t0, t1, data=None):
    """Per coin, each venue's mean funding annualised over [t0, t1) (positive: paid by longs) and its hourly rows."""
    data = Path(data or DATA)
    out = {}
    for _, r in sym.iterrows():
        row = {}
        for v in VENUES:
            g = pd.read_parquet(data / v["funding"] / f"{r[v['name']]}.parquet", columns=["t", "rate"])
            g = g[(g.t >= t0) & (g.t < t1)]
            if g.empty:
                continue
            days = max((g.t.max() - g.t.min() + 3_600_000) / xfund.DAY, 1.0)
            row[f"{v['name']}_ann_pct"] = float(g.rate.sum() / days * 365 * 100)
            row[f"{v['name']}_hours"] = int(len(g))
        if row:
            out[r.key] = row
    return out


def run(lane=None, data=None):
    from lab.prereg import verify
    lane, data = Path(lane or LANE), Path(data or DATA)
    verify(lane / "PREREG.md")
    check_inputs(lane / "PREREG.md")
    n_files = check_data(lane, data)
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    sym = pd.read_csv(lane / "symbols.csv", dtype=str)
    t0 = ms(START)
    nd = int((ms(END) + xfund.DAY - t0) // xfund.DAY + 1)
    u = load_universe(sym, t0, nd, data)
    rep = {"symbols": len(sym), "data_files_verified": n_files, "window": [START, END]}
    prim, rows, tr = base.book(u, PRIMARY, t0)
    rep["primary"] = prim
    rep["verdict"], rep["checks"] = base.decide(prim)
    rep["secondary_th10"], _, _ = base.book(u, SECONDARY, t0)
    rep["funding_profile"] = funding_profile(sym, t0, ms(END) + xfund.DAY, data)
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(t0 + rows.day * xfund.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": xfund.net(rows, PRIMARY[3], base.COST * m) for m in (1, 2, 3)},
                  "gross": rows.gross, "funding": rows.funding, "legs": rows.legs,
                  "held": rows.held}).to_csv(res / "daily.csv", index=False)
    tr.to_csv(res / "trades.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"],
                      **{k: prim.get(k) for k in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x",
                                                  "avg_held", "trades")}}, default=str))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("manifest", "run"))
    a = ap.parse_args(argv)
    manifest() if a.cmd == "manifest" else run()


if __name__ == "__main__":
    main()
