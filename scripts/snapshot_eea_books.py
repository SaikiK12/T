"""R508 diagnostic (after the frozen read): one snapshot of Kraken Futures and Hyperliquid order books for R508's
111 coins. Cost per side of a market order of $500 / $1,000 / $2,500 (half-spread plus walk, bp vs mid, fees
excluded), plus Kraken's current relative funding (per hour) and 24 h volume. Public, keyless.
Written for experiments/xfund_eea_v1/diagnostics/books_20261118.json; not an input of any frozen lane.

usage: python scripts/snapshot_eea_books.py OUT.json"""
import json
import sys
import time
import urllib.request

import pandas as pd

SYM = "/home/user/T/experiments/xfund_eea_v1/symbols.csv"
UA = {"User-Agent": "curl/8.5.0", "Content-Type": "application/json"}
SIZES = (500, 1000, 2500)


def get(url, body=None):
    for i in range(4):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def walk(levels, usd, mid):
    """Average fill price vs mid, bp, for a market order of `usd` notional; None if the book is too thin."""
    left, cost_q, got = usd, 0.0, 0.0
    for px, q in levels:
        take = min(q, left / px)
        got += take
        cost_q += take * px
        left -= take * px
        if left <= 1e-9:
            return abs(cost_q / got - mid) / mid * 1e4
    return None


def side_costs(bids, asks):
    if not bids or not asks:
        return None
    mid = (bids[0][0] + asks[0][0]) / 2
    out = {"spread_bp": (asks[0][0] - bids[0][0]) / mid * 1e4}
    for s in SIZES:
        b, a = walk(bids, s, mid), walk(asks, s, mid)
        out[f"cost_{s}_bp"] = None if b is None or a is None else (a + b) / 2
    return out


def main(out):
    sym = pd.read_csv(SYM)
    tick = {t["symbol"]: t for t in (get("https://futures.kraken.com/derivatives/api/v3/tickers") or {}).get("tickers", [])}
    res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "coins": {}}
    for _, r in sym.iterrows():
        row = {}
        ob = (get(f"https://futures.kraken.com/derivatives/api/v3/orderbook?symbol={r.kraken}") or {}).get("orderBook")
        if ob:
            bids = sorted(([float(p), float(q)] for p, q in ob.get("bids", [])), key=lambda x: -x[0])
            asks = sorted(([float(p), float(q)] for p, q in ob.get("asks", [])), key=lambda x: x[0])
            row["kraken"] = side_costs(bids, asks)
        t = tick.get(r.kraken, {})
        row["kraken_funding_rel_h"] = t.get("relativeFundingRate")
        row["kraken_vol24h_usd"] = t.get("volumeQuote")
        l2 = get("https://api.hyperliquid.xyz/info", {"type": "l2Book", "coin": r.hyperliquid})
        if l2 and l2.get("levels"):
            bids = [[float(x["px"]), float(x["sz"])] for x in l2["levels"][0]]
            asks = [[float(x["px"]), float(x["sz"])] for x in l2["levels"][1]]
            row["hyperliquid"] = side_costs(bids, asks)
        res["coins"][r.key] = row
        time.sleep(0.3)
    open(out, "w").write(json.dumps(res, indent=1))
    print(len(res["coins"]), res["utc"])


if __name__ == "__main__":
    main(sys.argv[1])
