"""xfund_kokx_v1 (R515): R275's cross-venue funding carry book on Kraken + OKX Europe X-Perps, both MiFID-regulated venues
open to EEA retail.

- Kraken's linear perps have no interest term in their funding.
- OKX Europe's X-Perps carry the 0.01%/8 h interest term ("withRate"). Their median funding was about 10%/yr in R430's
  snapshot.
- So the pair has R507/R508's design gap without an unregulated venue. Gate 0 on the short history the lab holds: the
  OKX recordings (data branch `claude/okx-xperp-data`, from 2026-08-10) and Kraken's served year.

Steps:
1. `manifest` (before the freeze): the symbol table by R508's name rule, and the sha256 of every Kraken file and every
   OKX day file it uses. It reads contract lists and file names only. Refuses once frozen.
2. `run` (once): verifies the PREREG, its inputs and the manifest; builds per-instrument OKX series from the day
   files (trade_1d closes, funding prints); runs `lab.xfund` on kraken+okx with R275's spec values; decides by
   R391's rule.

**Symbol rule.**
- An OKX crypto X-Perp's base is its instId before the first '-'.
- A Kraken `open` contract pairs with it when their names match after a leading `1000000` or `1000` is dropped.
- R508's `NOT_CRYPTO` bases are left out.
- When several OKX instIds share a base, the one listed latest wins.

usage: python scripts/run_xfund_kokx.py manifest | run
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund  # noqa: E402
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507 runner: book, decide)
from scripts import run_xfund_eea as eea  # noqa: E402  (frozen R508 runner: norm, NOT_CRYPTO, sha256)

LANE = ROOT / "experiments" / "xfund_kokx_v1"
DATA = ROOT / "data"
OKX = DATA / "okx_branch_20261120"           # `git archive` of claude/okx-xperp-data at 4d5d5c0 (2026-11-20 10:42 UTC)
START, END = "2026-08-10", "2026-11-15"       # inclusive days
PRIMARY = ("kraken+okx", 14, 0.05, 20)
SECONDARY = ("kraken+okx", 14, 0.10, 20)      # reported, not decided
BAR_H = 24


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


def okx_bases(okx=None):
    """{base: instId} from the latest instruments file: crypto X-Perps (instFamily *-USD_UM_XPERP)."""
    okx = Path(okx or OKX)
    f = sorted((okx / "instruments").glob("*.json"))[-1]
    out = {}
    for i in json.loads(f.read_text())["instruments"]:
        inst = i.get("instId", "")
        if "_UM_XPERP" not in inst or i.get("instCategory") not in ("1", None):
            continue
        out.setdefault(inst.split("-")[0], []).append((i.get("listTime") or "0", inst))
    return {b: sorted(v)[-1][1] for b, v in out.items()}


def symbol_table(kraken_contracts, bases):
    by = {}
    for b, inst in sorted(bases.items()):
        by.setdefault(eea.norm(b), []).append((b != eea.norm(b), inst))
    rows = []
    for r in kraken_contracts:
        if r["route"] != "open" or r["base"] in eea.NOT_CRYPTO:
            continue
        c = by.get(eea.norm(r["base"]))
        if c:
            rows.append({"key": eea.norm(r["base"]), "kraken": r["symbol"], "okx": sorted(c)[0][1]})
    return pd.DataFrame(rows, columns=["key", "kraken", "okx"]).drop_duplicates("key").reset_index(drop=True)


def okx_files(okx=None):
    okx = Path(okx or OKX)
    return sorted(list((okx / "funding").glob("*.csv")) + list((okx / "trade_1d").glob("*.csv")) +
                  list((okx / "instruments").glob("*.json")))


def manifest(lane=None, data=None):
    lane, data = Path(lane or LANE), Path(data or DATA)
    if (lane / "PREREG.sha256").exists():
        raise SystemExit("frozen: the manifest is written before the freeze only")
    k = pd.read_csv(data / "kraken_hist" / "contracts.csv", dtype=str)
    have = {p.stem for p in (data / "kraken_hist/open/candles_1d").glob("*.parquet")} & \
           {p.stem for p in (data / "kraken_hist/open/funding").glob("*.parquet")}
    sym = symbol_table(k[k.symbol.isin(have)].to_dict("records"), okx_bases(data / OKX.name))
    lane.mkdir(parents=True, exist_ok=True)
    sym.to_csv(lane / "symbols.csv", index=False)
    files = {}
    for s in sym.kraken:
        for kind in ("candles_1d", "funding"):
            p = data / "kraken_hist" / "open" / kind / f"{s}.parquet"
            files[str(p.relative_to(data))] = eea.sha256(p)
    for p in okx_files(data / OKX.name):
        files[str(p.relative_to(data))] = eea.sha256(p)
    (lane / "data_manifest.json").write_text(json.dumps({"root": "data", "files": files}, indent=1, sort_keys=True))
    print(json.dumps({"symbols": len(sym), "files": len(files)}))
    return sym


def check_inputs(prereg=None):
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        if eea.sha256(ROOT / path) != digest:
            raise SystemExit(f"{path} changed since the freeze")


def check_data(lane, data):
    m = json.loads((lane / "data_manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if not (data / p).exists() or eea.sha256(data / p) != h]
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from the manifest, e.g. {bad[:3]}")
    return len(m)


def build_okx(sym, okx, out):
    """Per-instrument parquet files from the day files: prices (t, close, volume) and funding (t, rate)."""
    want = set(sym.okx)
    f = pd.concat([pd.read_csv(p) for p in sorted((okx / "funding").glob("*.csv"))], ignore_index=True)
    c = pd.concat([pd.read_csv(p) for p in sorted((okx / "trade_1d").glob("*.csv"))], ignore_index=True)
    (out / "prices").mkdir(parents=True, exist_ok=True)
    (out / "funding").mkdir(parents=True, exist_ok=True)
    for inst in want:
        ff = f[f.instId == inst].drop_duplicates("fundingTime").sort_values("fundingTime")
        pd.DataFrame({"t": ff.fundingTime.astype("int64"), "rate": ff.fundingRate.astype(float)}).to_parquet(
            out / "funding" / f"{inst}.parquet", index=False)
        cc = c[c.instId == inst].drop_duplicates("ts").sort_values("ts")
        pd.DataFrame({"t": cc.ts.astype("int64"), "close": cc.c.astype(float), "volume": cc.vol_quote.astype(float)}
                     ).to_parquet(out / "prices" / f"{inst}.parquet", index=False)


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
    built = data / "okx_kokx_v1"
    build_okx(sym, data / OKX.name, built)
    t0 = ms(START)
    nd = int((ms(END) + xfund.DAY - t0) // xfund.DAY + 1)
    series = [[xfund.load_daily(data / "kraken_hist/open/candles_1d" / f"{r.kraken}.parquet",
                                data / "kraken_hist/open/funding" / f"{r.kraken}.parquet", "volume", BAR_H, t0, nd),
               xfund.load_daily(built / "prices" / f"{r.okx}.parquet", built / "funding" / f"{r.okx}.parquet",
                                "volume", BAR_H, t0, nd)] for _, r in sym.iterrows()]
    u = xfund.Universe(sym.key.tolist(), ["kraken", "okx"], series, t0, nd, 30, 0.9, 20)
    rep = {"symbols": len(sym), "data_files_verified": n_files, "window": [START, END]}
    prim, rows, tr = base.book(u, PRIMARY, t0)
    rep["primary"] = prim
    rep["verdict"], rep["checks"] = base.decide(prim)
    rep["secondary_th10"], _, _ = base.book(u, SECONDARY, t0)
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
