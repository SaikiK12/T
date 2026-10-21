"""One symbol map from each Binance USD-M perp to the same coin on every other venue and data source the lab holds.

Built from file names and the fetchers' contract lists only; no price is read here. Sources and their keys:

| source | folder | key | price files |
|---|---|---|---|
| gate | `gate_hist/open/` | contract (`BTC_USDT`), routed by `fetch_gate_history.py` | hourly candles, funding applies |
| hyperliquid | `hyperliquid/` | coin (`BTC`, `kPEPE`) | daily candles, funding |
| mexc | `mexc_hist/` | contract (`BTC_USDT`) | hourly klines, funding |
| kucoin, dydx, kraken | `<venue>_hist/open/` | symbol (`XBTUSDTM`, `BTC-USD`, `PF_XBTUSD`), from `contracts.csv` | candles, funding |
| upbit, bithumb | `<venue>_hist/open/` | market (`KRW-BTC`), spot | daily candles |
| coinmetrics | `coinmetrics/open/` | asset (`btc`) | daily market cap, on-chain |
| defillama | `defillama/open/` | the Binance perp itself (`mapping.csv`) | daily TVL, fees, revenue |

Every match uses R274's `binance_perp` name rule (plain, 1000 or 1000000 prefix). `mult` is the Binance price over the
venue price (1000 for PEPE on a venue that quotes 1 PEPE against Binance's 1000PEPEUSDT). When two keys of one source
map to one perp, the longer history (Gate: candle months) or the shorter name wins. The same ticker is not proof of
the same coin: a consumer checks identity on prices (`lab.daily` does, for every venue it prices).

Reserved samples are never listed: only `open/` folders are read, and only coins with a Binance perp exist here.
"""
import csv
import json
from pathlib import Path

from . import data

VENUE_FILES = {   # venue -> (folder, key column in contracts.csv, files that must exist under open/)
    "kucoin": ("kucoin_hist", "symbol", ("candles_1d", "funding")),
    "dydx": ("dydx_hist", "symbol", ("candles_1h", "funding")),
    "kraken": ("kraken_hist", "symbol", ("candles_1d", "funding")),
    "upbit": ("upbit_hist", "symbol", ("candles_1d",)),
    "bithumb": ("bithumb_hist", "symbol", ("candles_1d",)),
}
SOURCES = ("gate", "hyperliquid", "mexc", *VENUE_FILES, "coinmetrics", "defillama")
MULTS = ((1, ""), (1000, "1000"), (1_000_000, "1000000"))


def binance_perp(base, perps):
    """(Binance perp, Binance price / venue price) for a venue's base asset, or None (R274's name rule)."""
    for m, p in MULTS:
        if p + base + "USDT" in perps:
            return p + base + "USDT", m
    for m, p in MULTS[1:]:
        if base.startswith(p) and base[len(p):] + "USDT" in perps:
            return base[len(p):] + "USDT", 1 / m
    return None


def hl_base(coin):
    """Hyperliquid's k-coins are its 1000x contracts (kPEPE = 1000PEPE)."""
    return "1000" + coin[1:] if coin.startswith("k") and coin[1:2].isupper() else coin


def _stems(root, folder):
    return {p.stem for p in (root / folder).glob("*.parquet")}


def binance_perps(root=None):
    root = Path(root or data.ROOT)
    return {s for s in _stems(root, "klines_1h") if s.endswith("USDT")} & _stems(root, "fundingRate")


def table(root=None):
    """({perp: {source: (key, mult)}}, notes). Perps with no other source are left out."""
    root = Path(root or data.ROOT)
    perps = binance_perps(root)
    out, rank, notes = {}, {}, []

    def put(src, base, key, k):
        hit = binance_perp(base, perps)
        if not hit:
            return
        perp, mult = hit
        old = out.get(perp, {}).get(src)
        if old is None or k > rank[(src, perp)]:
            if old is not None:
                notes.append(f"{src}: {perp} keeps {key} over {old[0]}")
            out.setdefault(perp, {})[src], rank[(src, perp)] = (key, mult), k
        else:
            notes.append(f"{src}: {perp} keeps {old[0]} over {key}")

    gate = root / "gate_hist" / "contracts.csv"
    if gate.exists():
        have = _stems(root, "gate_hist/open/candlesticks_1h") & _stems(root, "gate_hist/open/funding_applies")
        with open(gate, newline="") as f:
            for r in csv.DictReader(f):
                if r["route"] == "open" and r["name"] in have:
                    put("gate", r["name"].rsplit("_USDT", 1)[0], r["name"],
                        (float(r.get("candlesticks_1h_months") or 0), -len(r["name"])))
    for coin in sorted(_stems(root, "hyperliquid/candles_1d") & _stems(root, "hyperliquid/funding")):
        put("hyperliquid", hl_base(coin), coin, (0, -len(coin)))
    mexc = root / "mexc_hist" / "contracts.json"
    if mexc.exists():
        have = _stems(root, "mexc_hist/klines_1h") & _stems(root, "mexc_hist/funding")
        for c in json.loads(mexc.read_text()):
            if c.get("settle") == "USDT" and c.get("type") == 1 and c["symbol"] in have:
                put("mexc", c["base"], c["symbol"], (0, -len(c["symbol"])))
    for src, (folder, col, kinds) in VENUE_FILES.items():
        path = root / folder / "contracts.csv"
        if not path.exists():
            continue
        have = set.intersection(*(_stems(root, f"{folder}/open/{k}") for k in kinds))
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                if r["route"] == "open" and r[col] in have:
                    put(src, r["base"], r[col], (0, -len(r[col])))
    for asset in sorted(_stems(root, "coinmetrics/open")):
        put("coinmetrics", asset.upper(), asset, (0, -len(asset)))
    for perp in sorted(_stems(root, "defillama/open") & perps):
        out.setdefault(perp, {})["defillama"] = (perp, 1)
    return out, notes


def rows(root=None):
    """One dict per perp: key, binance, and `<source>` / `<source>_mult` columns ('' where absent)."""
    t, _ = table(root)
    res = []
    for perp in sorted(t):
        r = {"key": perp, "binance": perp}
        for src in SOURCES:
            key, mult = t[perp].get(src, ("", ""))
            r[src], r[f"{src}_mult"] = key, mult
        res.append(r)
    return res
