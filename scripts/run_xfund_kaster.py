"""xfund_kaster_v1 (R511): R275's cross-venue funding carry book on Kraken + Aster, a pair never read.

R508 found +24%/yr on Kraken + Hyperliquid, almost all on thin Kraken perps whose funding (premium only, no interest
term) runs to extremes. Aster (Binance-style funding with the 0.01%/8 h interest term; its perps terms do not name
France) lists many of Kraken's thin coins that Hyperliquid lacks. On those coins Kraken's funding has never been read.

Steps:
1. `manifest` (before the freeze): Aster's contract list (metadata only), the symbol table by the rule below, and the
   sha256 of every held Kraken and Hyperliquid file it names. Refuses once frozen.
2. `fetch` (after the freeze): Aster funding history and daily klines for the table's symbols into data/aster_hist/,
   with a receipt per symbol (both files' sha256). Resumable.
3. `run` (once): verifies the PREREG, its inputs, the manifest and the receipts, then runs `lab.xfund` and decides
   by R391's rule on the coins outside R508's table (Kraken funding never read there); the book on every coin and the
   three-venue book are reported.

**Symbol rule.** Aster contracts are USDT-quoted perpetuals with status TRADING or SETTLING (SETTLING: being delisted;
kept, so the universe holds some delisted history). A Kraken `open` contract's base pairs with an Aster base when
their names match after a leading `1000000` or `1000` is removed from both (Hyperliquid's k-prefix becomes `1000`
first). When several Aster symbols match, the one without a multiplier wins, then the first by name. Bases in R508's
`NOT_CRYPTO` are left out. A Hyperliquid coin is attached by R508's rule for the union book. `in_r508` marks the coins
of R508's table, whose Kraken funding was read.

usage: python scripts/run_xfund_kaster.py manifest | fetch | run
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund  # noqa: E402
from lab.venues import hl_base  # noqa: E402
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507 runner: book, decide)
from scripts import run_xfund_eea as eea  # noqa: E402  (frozen R508 runner: norm, NOT_CRYPTO, sha256)

LANE = ROOT / "experiments" / "xfund_kaster_v1"
DATA = ROOT / "data"
ASTER = "https://fapi.asterdex.com"
START, END = eea.START, eea.END                   # R508's window: 2025-11-17..2026-11-15
FETCH_FROM, FETCH_TO = "2025-11-01", "2026-11-16"  # [from, to): the window plus margin, nothing later
DECIDED = ("kraken+aster", 14, 0.05, 20)          # on the coins outside R508's table: Kraken funding never read
FULL = ("kraken+aster", 14, 0.05, 20)             # the same book on every coin of the table (reported)
UNION = ("kraken+hyperliquid+aster", 14, 0.05, 20) # the three venues together, every coin (reported)
VENUES = [{"name": "kraken", "prices": "kraken_hist/open/candles_1d", "vol": "volume",
           "funding": "kraken_hist/open/funding"},
          {"name": "hyperliquid", "prices": "hyperliquid/candles_1d", "vol": "volume", "funding": "hyperliquid/funding"},
          {"name": "aster", "prices": "aster_hist/candles_1d", "vol": "volume", "funding": "aster_hist/funding"}]
BAR_H = 24
PACE = 0.25


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


def get(url, tries=5):
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 429:
                time.sleep(60)
            elif e.code in (400, 404):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def aster_contracts(info):
    """[{symbol, base}] of USDT perpetuals that trade or are settling."""
    return [{"symbol": s["symbol"], "base": s["baseAsset"]} for s in info.get("symbols", [])
            if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
            and s.get("status") in ("TRADING", "SETTLING")]


def symbol_table(kraken_contracts, aster, hl_coins, r508_keys):
    """[{key, kraken, hyperliquid, aster, in_r508}] by the symbol rule."""
    a = {}
    for c in sorted(aster, key=lambda c: c["symbol"]):
        a.setdefault(eea.norm(c["base"]), []).append(c)
    h = {}
    for c in sorted(hl_coins):
        h.setdefault(eea.norm(hl_base(c)), []).append(c)
    rows = []
    for r in kraken_contracts:
        if r["route"] != "open" or r["base"] in eea.NOT_CRYPTO:
            continue
        k = eea.norm(r["base"])
        if k not in a:
            continue
        pick = sorted(a[k], key=lambda c: (c["base"] != eea.norm(c["base"]), c["symbol"]))[0]
        hl = sorted(h.get(k, []), key=lambda c: (hl_base(c) != eea.norm(hl_base(c)), c))
        rows.append({"key": k, "kraken": r["symbol"], "hyperliquid": hl[0] if hl else "", "aster": pick["symbol"],
                     "in_r508": k in r508_keys})
    return pd.DataFrame(rows, columns=["key", "kraken", "hyperliquid", "aster", "in_r508"]).drop_duplicates(
        "key").reset_index(drop=True)


def build_table(info, data=None):
    data = Path(data or DATA)
    k = pd.read_csv(data / "kraken_hist" / "contracts.csv", dtype=str)
    have_k = {p.stem for p in (data / "kraken_hist/open/candles_1d").glob("*.parquet")} & \
             {p.stem for p in (data / "kraken_hist/open/funding").glob("*.parquet")}
    k = k[k.symbol.isin(have_k)]
    hl = {p.stem for p in (data / "hyperliquid/candles_1d").glob("*.parquet")} & \
         {p.stem for p in (data / "hyperliquid/funding").glob("*.parquet")}
    r508 = set(pd.read_csv(ROOT / "experiments" / "xfund_eea_v1" / "symbols.csv").key)
    return symbol_table(k.to_dict("records"), aster_contracts(info), hl, r508)


def held_files(sym, data=None):
    data = Path(data or DATA)
    out = []
    for _, r in sym.iterrows():
        for v in VENUES[:2]:
            s = r[v["name"]]
            if isinstance(s, str) and s:
                out += [data / v["prices"] / f"{s}.parquet", data / v["funding"] / f"{s}.parquet"]
    return out


def manifest(lane=None, data=None, info=None):
    lane, data = Path(lane or LANE), Path(data or DATA)
    if (lane / "PREREG.sha256").exists():
        raise SystemExit("frozen: the manifest is written before the freeze only")
    info = info or get(f"{ASTER}/fapi/v1/exchangeInfo")
    sym = build_table(info, data)
    lane.mkdir(parents=True, exist_ok=True)
    sym.to_csv(lane / "symbols.csv", index=False)
    files = {str(p.relative_to(data)): eea.sha256(p) for p in held_files(sym, data)}
    (lane / "data_manifest.json").write_text(json.dumps({"root": "data", "files": files}, indent=1, sort_keys=True))
    print(json.dumps({"symbols": len(sym), "in_r508": int(sym.in_r508.sum()), "held_files": len(files)}))
    return sym


# ---------------------------------------------------------------- Aster history (after the freeze)

def aster_funding(sym, start, end):
    out, s = [], start
    while s < end:
        rows = get(f"{ASTER}/fapi/v1/fundingRate?symbol={sym}&startTime={s}&endTime={end - 1}&limit=1000")
        time.sleep(PACE)
        if not rows:
            break
        out += rows
        last = int(rows[-1]["fundingTime"])
        if last < s or len(rows) < 1000:
            break
        s = last + 1
    df = pd.DataFrame({"t": [int(r["fundingTime"]) for r in out], "rate": [float(r["fundingRate"]) for r in out]})
    df = df[(df.t >= start) & (df.t < end)] if len(df) else df
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def aster_klines(sym, start, end):
    rows = get(f"{ASTER}/fapi/v1/klines?symbol={sym}&interval=1d&startTime={start}&endTime={end - 1}&limit=1500")
    time.sleep(PACE)
    df = pd.DataFrame({"t": [int(r[0]) for r in rows or []], "close": [float(r[4]) for r in rows or []],
                       "volume": [float(r[5]) for r in rows or []]})
    df = df[(df.t >= start) & (df.t + xfund.DAY <= end)] if len(df) else df   # finished bars inside the fetch window
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def fetch(lane=None, data=None, log=print):
    from lab.prereg import verify
    lane, data = Path(lane or LANE), Path(data or DATA)
    verify(lane / "PREREG.md")
    check_inputs(lane / "PREREG.md")
    sym = pd.read_csv(lane / "symbols.csv", dtype=str)
    out = data / "aster_hist"
    for d in ("funding", "candles_1d", "receipts"):
        (out / d).mkdir(parents=True, exist_ok=True)
    a, b = ms(FETCH_FROM), ms(FETCH_TO)
    for i, s in enumerate(sym.aster):
        rec = out / "receipts" / f"{s}.json"
        if rec.exists():
            continue
        f, c = aster_funding(s, a, b), aster_klines(s, a, b)
        f.to_parquet(out / "funding" / f"{s}.parquet", index=False)
        c.to_parquet(out / "candles_1d" / f"{s}.parquet", index=False)
        rec.write_text(json.dumps({"symbol": s, "from": FETCH_FROM, "to_exclusive": FETCH_TO, "funding_rows": len(f),
                                   "candles": len(c),
                                   "funding_sha256": eea.sha256(out / "funding" / f"{s}.parquet"),
                                   "candles_sha256": eea.sha256(out / "candles_1d" / f"{s}.parquet"),
                                   "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1))
        if (i + 1) % 25 == 0:
            log(f"{i + 1}/{len(sym)} {s}")
    log("fetch done")


# ---------------------------------------------------------------- the read

def check_inputs(prereg=None):
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        if eea.sha256(ROOT / path) != digest:
            raise SystemExit(f"{path} changed since the freeze")
    return pairs


def check_data(lane, data, sym):
    m = json.loads((lane / "data_manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if not (data / p).exists() or eea.sha256(data / p) != h]
    for s in sym.aster:
        r = json.loads((data / "aster_hist" / "receipts" / f"{s}.json").read_text())
        for kind, key in (("funding", "funding_sha256"), ("candles_1d", "candles_sha256")):
            if eea.sha256(data / "aster_hist" / kind / f"{s}.parquet") != r[key]:
                bad.append(f"aster_hist/{kind}/{s}.parquet")
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from the manifest or receipts, e.g. {bad[:3]}")
    return len(m) + 2 * len(sym)


def load_universe(sym, t0, nd, data=None):
    data = Path(data or DATA)

    def one(row, v):
        s = row[v["name"]]
        if not isinstance(s, str) or not s:
            return None
        return xfund.load_daily(data / v["prices"] / f"{s}.parquet", data / v["funding"] / f"{s}.parquet", v["vol"],
                                BAR_H, t0, nd)

    series = [[one(r, v) for v in VENUES] for _, r in sym.iterrows()]
    return xfund.Universe(sym.key.tolist(), [v["name"] for v in VENUES], series, t0, nd, 30, 0.9, 20)


def funding_profile(sym, t0, t1, data=None):
    data = Path(data or DATA)
    out = {}
    for _, r in sym.iterrows():
        row = {"in_r508": bool(r.in_r508)}
        for v in (VENUES[0], VENUES[2]):
            g = pd.read_parquet(data / v["funding"] / f"{r[v['name']]}.parquet", columns=["t", "rate"])
            g = g[(g.t >= t0) & (g.t < t1)]
            if len(g):
                days = max((g.t.max() - g.t.min()) / xfund.DAY, 1.0)
                row[f"{v['name']}_ann_pct"] = float(g.rate.sum() / days * 365 * 100)
        out[r.key] = row
    return out


def run(lane=None, data=None):
    from lab.prereg import verify
    lane, data = Path(lane or LANE), Path(data or DATA)
    verify(lane / "PREREG.md")
    check_inputs(lane / "PREREG.md")
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    sym = pd.read_csv(lane / "symbols.csv", dtype=str).fillna("")
    sym["in_r508"] = sym.in_r508.astype(str) == "True"
    n_files = check_data(lane, data, sym)
    t0 = ms(START)
    nd = int((ms(END) + xfund.DAY - t0) // xfund.DAY + 1)
    u = load_universe(sym, t0, nd, data)
    unseen = sym[~sym.in_r508].reset_index(drop=True)
    rep = {"symbols": len(sym), "in_r508": int(sym.in_r508.sum()), "unseen_coins": int(len(unseen)),
           "data_files_verified": n_files, "window": [START, END]}
    prim, rows, tr = base.book(load_universe(unseen, t0, nd, data), DECIDED, t0)
    rep["primary"] = prim
    rep["verdict"], rep["checks"] = base.decide(prim)
    rep["full_book"], _, _ = base.book(u, FULL, t0)
    rep["union_book"], _, _ = base.book(u, UNION, t0)
    rep["funding_profile"] = funding_profile(sym, t0, ms(END) + xfund.DAY, data)
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(t0 + rows.day * xfund.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": xfund.net(rows, DECIDED[3], base.COST * m) for m in (1, 2, 3)},
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
    ap.add_argument("cmd", choices=("manifest", "fetch", "run"))
    a = ap.parse_args(argv)
    {"manifest": manifest, "fetch": fetch, "run": run}[a.cmd]()


if __name__ == "__main__":
    main()
