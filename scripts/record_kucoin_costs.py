"""capsizing_v1 (R496): measure KuCoin and dYdX cost curves, the two venues R495 did not cover.

Every R277 carry trade touches KuCoin or dYdX, so scoring them against R495's binance/gate curves
was a venue mismatch. This measures the right venues. Public, keyless, places nothing.

KuCoin `bids/asks` are [price, size] with size in CONTRACTS -> scale by the contract `multiplier`.
dYdX sizes are in base units (coins). Reuses R495's tested cost walk (scripts/record_bg_costs.py).

usage: python scripts/record_kucoin_costs.py [--limit N]
"""
import argparse
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

_spec = importlib.util.spec_from_file_location("bg", ROOT / "scripts/record_bg_costs.py")
_bg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bg)
measure, SIZES, PAUSE = _bg.measure, _bg.SIZES, _bg.PAUSE

LANE = ROOT / "experiments/capsizing_v1"
TRADES = ROOT / "experiments/xfund_kd_v1/results/trades.csv"
KUCOIN = "https://api-futures.kucoin.com/api/v1"
DYDX = "https://indexer.dydx.trade/v4"
UA = {"User-Agent": "Mozilla/5.0"}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=2):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 418):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(PAUSE * (k + 1))
    raise last


def kucoin_symbol(coin):
    """R277 keys are Binance-style (BTCUSDT, 1000PEPEUSDT). KuCoin uses XBT and its own prefixes."""
    base = coin[:-4] if coin.endswith("USDT") else coin
    if base == "BTC":
        base = "XBT"
    return base + "USDTM"


def dydx_symbol(coin):
    base = coin[:-4] if coin.endswith("USDT") else coin
    return base + "-USD"


def kucoin_book(sym):
    meta = get(f"{KUCOIN}/contracts/{sym}")["data"]
    mult = float(meta.get("multiplier") or 0)
    if mult <= 0:
        raise ValueError("no multiplier")
    d = get(f"{KUCOIN}/level2/snapshot?symbol={sym}")["data"]
    bids = [(float(p), float(s) * mult * float(p)) for p, s in d["bids"]]
    asks = [(float(p), float(s) * mult * float(p)) for p, s in d["asks"]]
    m = measure(bids, asks)
    if m:
        m.update(quanto_multiplier=mult, taker_fee_rate=float(meta.get("takerFeeRate") or "nan"))
    return m


def dydx_book(sym):
    d = get(f"{DYDX}/orderbooks/perpetualMarket/{sym}")
    bids = [(float(x["price"]), float(x["size"]) * float(x["price"])) for x in d["bids"]]
    asks = [(float(x["price"]), float(x["size"]) * float(x["price"])) for x in d["asks"]]
    return measure(bids, asks)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    frozen = prereg.verify(LANE / "PREREG.md")
    coins = sorted(pd.read_csv(TRADES).coin.unique())
    if a.limit:
        coins = coins[:a.limit]
    log(f"{len(coins)} coins x 2 venues, PREREG {frozen[:12]}")
    rows, errors = [], []

    def one(coin):
        out = []
        for venue, fn, sym in (("kucoin", kucoin_book, kucoin_symbol(coin)),
                               ("dydx", dydx_book, dydx_symbol(coin))):
            try:
                time.sleep(PAUSE)
                m = fn(sym)
                if m:
                    out.append({"coin": coin, "venue": venue, "symbol": sym, **m})
            except Exception as e:
                errors.append({"venue": venue, "symbol": sym, "error": f"{type(e).__name__}: {e}"[:110]})
        return out

    with ThreadPoolExecutor(2) as ex:
        for i, got in enumerate(ex.map(one, coins), 1):
            rows.extend(got)
            if i % 50 == 0:
                log(f"  {i}/{len(coins)} coins, {len(rows)} rows, {len(errors)} errors")
    if not rows:
        raise SystemExit("nothing measured")
    t = pd.DataFrame(rows)
    bands = []
    for v, g in t.groupby("venue"):
        bands.append({"venue": v, "contracts": int(len(g)),
                      "median_half_spread_bp": float(g.half_spread_bp.median()),
                      **{f"median_side_{n//1000}k_bp": float(g[f"side_{n//1000}k_bp"].median()) for n in SIZES},
                      "median_depth_ask_usd": float(g.usd_ask_1pct.median())})
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    t.to_csv(out / "books_kd.csv", index=False)
    (out / "curves_kd.json").write_text(json.dumps(
        {"prereg_sha256": frozen, "utc": datetime.now(timezone.utc).isoformat(),
         "coins_requested": len(coins), "rows": len(t), "by_venue": bands,
         "error_count": len(errors), "errors": errors[:40]}, indent=1) + "\n")
    print(json.dumps(bands, indent=1))


if __name__ == "__main__":
    main()
