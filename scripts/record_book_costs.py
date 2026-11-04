"""book_costs_v1 (R404): what a taker order costs on dYdX v4, KuCoin futures and MEXC futures for every listed perp,
measured from the public order books, as set out in experiments/book_costs_v1/PREREG.md. It feeds M469 (the dYdX,
KuCoin and Lighter long-tail carry re-test), where more than half the trades are in coins under $50k a day and no
book was ever measured. Lighter is measured by scripts/record_lighter_book.py; Binance futures answer 451 here.

For each perp: best bid and ask, half-spread, and the cost per side of a market order of $1k, $5k and $10k walked
through the shown book (bp from the mid to the average fill; NaN when the shown book is too thin), USD shown and USD
within 1% of the mid per side, 24 h quote volume, open interest and the venue's listed fees.

One file per 3-hour UTC slot, data/recorders/book_costs/<YYYY-MM-DD>/<HH>.parquet (gitignored; record_digest.py
commits digests); a second run in the same slot writes nothing. Then experiments/book_costs_v1/journal/status.json
summarizes every file so far by venue and 24 h volume band. Paper only: public endpoints, no key, places nothing.

usage: python scripts/record_book_costs.py [--venue dydx kucoin mexc] [--limit N] [--force]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg  # noqa: E402

LANE = ROOT / "experiments" / "book_costs_v1"
J = LANE / "journal"
OUT = data.ROOT / "recorders" / "book_costs"
DYDX = "https://indexer.dydx.trade/v4"
KUCOIN = "https://api-futures.kucoin.com/api/v1"
MEXC = "https://contract.mexc.com/api/v1/contract"
SLOT_H = 3
SIZES = (1_000, 5_000, 10_000)
NEAR = 0.01                                    # USD shown within 1% of the mid
PACE = {"dydx": 0.25, "kucoin": 0.2, "mexc": 0.15}
BANDS = (0, 50_000, 500_000, 5_000_000, np.inf)
ALIAS = {"XBT": "BTC"}                         # KuCoin's base code
COLS = ["ts", "venue", "symbol", "base", "bid", "ask", "half_spread_bp"] + \
       [f"{s}_{n // 1000}k_bp" for n in SIZES for s in ("buy", "sell")] + \
       ["bid_usd_shown", "ask_usd_shown", "bid_usd_1pct", "ask_usd_1pct", "levels_bid", "levels_ask", "vol24_usd",
        "oi_usd", "taker_fee", "maker_fee"]
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def http(url, tries=3, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "lab/1", "Accept": "application/json"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or k == tries - 1:
                raise
            time.sleep(5.0 * (k + 1))         # rate limited: wait, then the same request once more


def impact(side, usd, mid):
    """bp between mid and the average fill of a market order of `usd` notional walked through `side`
    [(price, base), ...] best first; NaN when the shown book is too thin."""
    left, paid, qty = float(usd), 0.0, 0.0
    for p, q in side:
        take = min(left, p * q)
        paid += take
        qty += take / p
        left -= take
        if left <= 1e-9:
            return abs(paid / qty / mid - 1) * 1e4
    return np.nan


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return np.nan
    return v if np.isfinite(v) else np.nan


def row(ts, venue, symbol, base, bids, asks, **extra):
    """One cost row from bids and asks [(price, base quantity), ...] best first, or None for an empty or crossed book."""
    bids = [(p, q) for p, q in bids if p > 0 and q > 0]
    asks = [(p, q) for p, q in asks if p > 0 and q > 0]
    if not bids or not asks or asks[0][0] <= bids[0][0]:
        return None
    bid, ask = bids[0][0], asks[0][0]
    mid = (bid + ask) / 2
    out = {"ts": ts, "venue": venue, "symbol": symbol, "base": ALIAS.get(base, base), "bid": bid, "ask": ask,
           "half_spread_bp": (ask - bid) / mid / 2 * 1e4,
           "bid_usd_shown": sum(p * q for p, q in bids), "ask_usd_shown": sum(p * q for p, q in asks),
           "bid_usd_1pct": sum(p * q for p, q in bids if p >= mid * (1 - NEAR)),
           "ask_usd_1pct": sum(p * q for p, q in asks if p <= mid * (1 + NEAR)),
           "levels_bid": len(bids), "levels_ask": len(asks)}
    for n in SIZES:
        out[f"buy_{n // 1000}k_bp"] = impact(asks, n, mid)
        out[f"sell_{n // 1000}k_bp"] = impact(bids, n, mid)
    out.update({k: num(extra.get(k)) for k in ("vol24_usd", "oi_usd", "taker_fee", "maker_fee")})
    return out


def dydx_markets(get):
    """[(ticker, base, extra)] for dYdX v4 perps with status ACTIVE. Fees are not published by the indexer: NaN."""
    out = []
    for t, m in sorted(get(f"{DYDX}/perpetualMarkets")["markets"].items()):
        if m.get("status") != "ACTIVE":
            continue
        out.append((t, t.split("-")[0], {"vol24_usd": m.get("volume24H"),
                                         "oi_usd": num(m.get("openInterest")) * num(m.get("oraclePrice"))}))
    return out


def dydx_book(get, ticker):
    b = get(f"{DYDX}/orderbooks/perpetualMarket/{ticker}")
    lv = lambda xs: [(num(x["price"]), num(x["size"])) for x in xs or []]
    return lv(b.get("bids")), lv(b.get("asks"))


def kucoin_markets(get):
    """[(symbol, base, extra)] for KuCoin's open linear USDT perps; quantities are in contracts of `multiplier` base."""
    out = []
    for c in sorted(get(f"{KUCOIN}/contracts/active")["data"], key=lambda c: c["symbol"]):
        if c.get("status") != "Open" or c.get("isInverse") or c.get("quoteCurrency") != "USDT" or c.get("expireDate"):
            continue
        mult = num(c.get("multiplier"))
        out.append((c["symbol"], c.get("baseCurrency"), {
            "mult": mult, "vol24_usd": c.get("turnoverOf24h"),
            "oi_usd": num(c.get("openInterest")) * mult * num(c.get("markPrice")),
            "taker_fee": c.get("takerFeeRate"), "maker_fee": c.get("makerFeeRate")}))
    return out


def kucoin_book(get, symbol, mult):
    b = get(f"{KUCOIN}/level2/depth100?symbol={symbol}")["data"]
    lv = lambda xs: [(num(p), num(q) * mult) for p, q, *_ in xs or []]
    return lv(b.get("bids")), lv(b.get("asks"))


def mexc_markets(get):
    """[(symbol, base, extra)] for MEXC's enabled crypto USDT perps (type 1, state 0); quantities in contracts."""
    tick = {t["symbol"]: t for t in get(f"{MEXC}/ticker")["data"]}
    out = []
    for c in sorted(get(f"{MEXC}/detail")["data"], key=lambda c: c["symbol"]):
        if c.get("settleCoin") != "USDT" or c.get("type") != 1 or c.get("state") != 0:
            continue
        t = tick.get(c["symbol"], {})
        cs = num(c.get("contractSize"))
        out.append((c["symbol"], c.get("baseCoin"), {
            "mult": cs, "vol24_usd": t.get("amount24"), "oi_usd": num(t.get("holdVol")) * cs * num(t.get("fairPrice")),
            "taker_fee": c.get("takerFeeRate"), "maker_fee": c.get("makerFeeRate")}))
    return out


def mexc_book(get, symbol, mult):
    b = get(f"{MEXC}/depth/{symbol}?limit=100")["data"]
    lv = lambda xs: [(num(x[0]), num(x[1]) * mult) for x in xs or []]
    return lv(b.get("bids")), lv(b.get("asks"))


VENUES = {"dydx": (dydx_markets, lambda get, s, e: dydx_book(get, s)),
          "kucoin": (kucoin_markets, lambda get, s, e: kucoin_book(get, s, e["mult"])),
          "mexc": (mexc_markets, lambda get, s, e: mexc_book(get, s, e["mult"]))}


def venue_rows(venue, ts, get=http, pace=None, limit=None):
    """All rows of one venue, paced from the start of the previous request; one market failing does not stop it."""
    markets_fn, book_fn = VENUES[venue]
    pace = PACE[venue] if pace is None else pace
    rows, failed, last = [], [], time.monotonic()
    try:
        markets = markets_fn(get)
    except Exception as e:  # noqa: BLE001 - a venue down is recorded, not fatal
        return [], [f"{venue} market list: {e}"]
    for symbol, base, extra in markets[:limit]:
        time.sleep(max(0.0, pace - (time.monotonic() - last)))
        last = time.monotonic()
        try:
            bids, asks = book_fn(get, symbol, extra)
        except Exception as e:  # noqa: BLE001
            failed.append(f"{venue} {symbol}: {e}")
            continue
        r = row(ts, venue, symbol, base, bids, asks, **extra)
        if r:
            rows.append(r)
    return rows, failed


def snapshot(venues=tuple(VENUES), get=http, pace=None, limit=None):
    ts = int(time.time() * 1000)
    with ThreadPoolExecutor(len(venues)) as ex:                # one thread per venue: different hosts, own pace
        got = list(ex.map(lambda v: venue_rows(v, ts, get, pace, limit), venues))
    rows = [r for rs, _ in got for r in rs]
    failed = [f for _, fs in got for f in fs]
    return pd.DataFrame(rows, columns=COLS), failed


def slot_path(now=None, root=None):
    now = time.gmtime() if now is None else now
    h = now.tm_hour - now.tm_hour % SLOT_H
    return Path(root or OUT) / time.strftime("%Y-%m-%d", now) / f"{h:02d}.parquet"


def band(v):
    for lo, hi in zip(BANDS[:-1], BANDS[1:]):
        if lo <= v < hi:
            return f"{lo:g}-{hi:g}"
    return "unknown"


def summarize(frames):
    """status.json content: per venue and 24 h volume band (each symbol's median volume), the median over symbols of
    each symbol's median cost per side (mean of buy and sell) at each size, with an unfilled snapshot counted as
    infinite cost, and the share of symbols whose median is unfilled."""
    if not frames:
        return {"snapshots": 0}
    x = pd.concat(frames, ignore_index=True)
    for n in SIZES:
        k = f"{n // 1000}k"
        x[f"side_{k}"] = ((x[f"buy_{k}_bp"] + x[f"sell_{k}_bp"]) / 2).fillna(np.inf)
    g = x.groupby(["venue", "symbol"])
    per = g[[f"side_{n // 1000}k" for n in SIZES] + ["half_spread_bp"]].median()
    per["vol24_usd"] = g["vol24_usd"].median()
    per["snapshots"] = g.size()
    per["band"] = per["vol24_usd"].apply(lambda v: band(v) if np.isfinite(v) else "unknown")
    out = {"snapshots": int(x.ts.nunique()), "first_ms": int(x.ts.min()), "last_ms": int(x.ts.max()),
           "symbols": {v: int(n) for v, n in per.groupby(level=0).size().items()}, "by_venue_band": []}
    for (v, b), grp in per.groupby([per.index.get_level_values(0), "band"]):
        rec = {"venue": v, "band_usd": b, "symbols": int(len(grp)),
               "median_half_spread_bp": float(grp.half_spread_bp.median())}
        for n in SIZES:
            k = f"{n // 1000}k"
            med = float(np.median(grp[f"side_{k}"]))
            rec[f"median_side_{k}_bp"] = med if np.isfinite(med) else None
            rec[f"unfilled_share_{k}"] = float(np.isinf(grp[f"side_{k}"]).mean())
        out["by_venue_band"].append(rec)
    return out


def status(root=None):
    files = sorted(Path(root or OUT).glob("*/*.parquet"))
    out = summarize([pd.read_parquet(f) for f in files])
    out["files"] = len(files)
    J.mkdir(parents=True, exist_ok=True)
    (J / "status.json").write_text(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", nargs="+", default=list(VENUES), choices=list(VENUES))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true", help="write the slot even if its file exists (tests only)")
    a = ap.parse_args(argv)
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    path = slot_path()
    if path.exists() and not a.force:
        log(f"book costs: {path.relative_to(ROOT)} already written")
    else:
        df, failed = snapshot(tuple(a.venue), limit=a.limit)
        if failed:
            log(f"book costs: {len(failed)} failed, first: {failed[0]}")
        if df.empty:
            log("book costs: nothing read")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".part")          # record_digest.py skips .part files
            df.to_parquet(tmp, index=False)
            tmp.replace(path)
            log(f"book costs: {len(df)} books -> {path.relative_to(ROOT)}; "
                + ", ".join(f"{v} {int((df.venue == v).sum())}" for v in a.venue))
    s = status()
    log(f"book costs: {s.get('files', 0)} files, {s.get('snapshots', 0)} snapshots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
