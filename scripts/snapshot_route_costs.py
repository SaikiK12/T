"""One descriptive snapshot of what a taker order costs on the zero-fee and low-fee perp routes, for every coin Paradex
lists: Paradex's retail (interactive) book, Paradex's public API book, Lighter and Hyperliquid's main dex.

It ranks routes for research/intake/fee_map_20261116.md. It is not a lane statistic and decides nothing; a recorder
lane is needed for a cost that a verdict can use.

Why two Paradex books: Paradex quotes Retail Price Improvement (RPI) orders that match only retail takers (orders sent
from the web app, or through the API with an interactive token), and its plain order-book endpoint leaves them out
(docs.paradex.trade/trading/rpi). The /interactive endpoint shows the book a retail taker meets.

Per book and coin: half-spread, the cost per side of a market order of $1k, $5k and $10k walked through the shown book
(bp from the mid to the average fill; NaN when the shown book is too thin), the taker fee assumed for that route, and
the all-in cost (walk plus fee). Fees: Paradex retail 0 and API 2 bp (the markets endpoint's fee_config), Lighter
Standard 0, Hyperliquid tier 0 4.5 bp.

Public endpoints, no key, no account, places nothing.

usage: python scripts/snapshot_route_costs.py OUT.csv
"""
import json
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

SIZES = (1_000, 5_000, 10_000)
PX = "https://api.prod.paradex.trade/v1"
LT = "https://mainnet.zklighter.elliot.ai/api/v1"
HL = "https://api.hyperliquid.xyz/info"
FEE_BP = {"paradex_interactive": 0.0, "paradex_api_public": 2.0, "lighter": 0.0, "hyperliquid": 4.5}
LIGHTER_ALIAS = {"kPEPE": "1000PEPE", "kSHIB": "1000SHIB"}


def get(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "lab/1", "Accept": "application/json",
                                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


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


def row(book, coin, bids, asks):
    """One cost row, or None for an empty or crossed book."""
    bids = [(p, q) for p, q in bids if p > 0 and q > 0]
    asks = [(p, q) for p, q in asks if p > 0 and q > 0]
    if not bids or not asks or asks[0][0] <= bids[0][0]:
        return None
    mid = (bids[0][0] + asks[0][0]) / 2
    out = {"book": book, "coin": coin, "half_spread_bp": (asks[0][0] - bids[0][0]) / mid / 2 * 1e4}
    for n in SIZES:
        out[f"side_{n // 1000}k_bp"] = (impact(asks, n, mid) + impact(bids, n, mid)) / 2
    return out


def snapshot(get=get, pause=time.sleep):
    rows, coins = [], []
    pairs = lambda xs: [(float(p), float(q)) for p, q in xs]
    for m in [m for m in get(f"{PX}/markets")["results"] if m.get("asset_kind") == "PERP"]:
        coin = m["base_currency"]
        coins.append(coin)
        for book, path in (("paradex_interactive", "/interactive"), ("paradex_api_public", "")):
            b = get(f"{PX}/orderbook/{m['symbol']}{path}?depth=100")
            pause(0.2)
            r = row(book, coin, pairs(b.get("bids") or []), pairs(b.get("asks") or []))
            if r:
                rows.append(r)
    det = {d["symbol"]: d for d in get(f"{LT}/orderBookDetails?filter=perp")["order_book_details"]
           if d.get("status") == "active"}
    for coin in coins:
        d = det.get(coin) or det.get(LIGHTER_ALIAS.get(coin, ""))
        if not d:
            continue
        pause(1.1)                                   # Lighter Standard: 60 requests a minute
        b = get(f"{LT}/orderBookOrders?market_id={int(d['market_id'])}&limit=100")
        lv = lambda xs: [(float(o["price"]), float(o["remaining_base_amount"])) for o in xs or []]
        r = row("lighter", coin, lv(b.get("bids")), lv(b.get("asks")))
        if r:
            rows.append(r)
    listed = {u["name"] for u in get(HL, {"type": "meta"})["universe"] if not u.get("isDelisted")}
    for coin in coins:
        if coin not in listed:
            continue
        pause(0.25)
        lv = lambda xs: [(float(x["px"]), float(x["sz"])) for x in xs]
        bids, asks = get(HL, {"type": "l2Book", "coin": coin})["levels"]
        r = row("hyperliquid", coin, lv(bids), lv(asks))
        if r:
            rows.append(r)
    x = pd.DataFrame(rows)
    x.insert(0, "ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    x["taker_fee_bp"] = x.book.map(FEE_BP)
    for n in SIZES:
        k = f"{n // 1000}k"
        x[f"allin_{k}_bp"] = x[f"side_{k}_bp"] + x.taker_fee_bp
    return x


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1])
        return 2
    x = snapshot()
    x.round(3).to_csv(argv[0], index=False)
    print(x.ts.iloc[0], x.book.value_counts().to_dict())
    print(x.groupby("book")[["half_spread_bp", "allin_1k_bp", "allin_5k_bp", "allin_10k_bp"]].median().round(2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
