"""Hourly recorder of order-book costs on Hyperliquid's HIP-3 markets (trade.xyz's `xyz` dex by default): what a
market order of a given size would pay against the book, by side. Public data, no key, no order. Stdlib only, so it
runs on a bare GitHub runner.

Why: R451 (experiments/flow_hlstock_v1) prices R200's stock-perp flow books on xyz at assumed costs (9 bp taker or the
lab's tier cost, whichever is higher). Whether a real order pays that is not known: xyz's depth was never measured.
These snapshots let a later, registered read put measured costs on the same tickets (real money equal to paper).

Writes under OUT (day-partitioned CSV, merged by key, so a re-run is idempotent):
- books/YYYY-MM-DD.csv: one row per market and snapshot (by the UTC day of the snapshot):
  dex, coin, ts (the book's own time, ms), bid, ask, spread_bp, depth_bid_usd and depth_ask_usd (the 20 levels the
  API returns), buy_<N>_bp and sell_<N>_bp (cost in bp from mid of a $N market order through those levels, blank if
  they are too thin), and from the same minute's market context: mark, oracle, funding (the current hourly rate),
  premium, open interest (base units) and 24 h notional volume.
- markets/YYYY-MM-DD.csv: each market's fee settings as listed that day (growthMode, deployerFeeScale,
  lastFeeScaleChangeTime, maxLeverage), merged by (dex, coin), so fee changes are dated.

usage: python scripts/record_xyz_books.py --out DIR [--dex xyz] [--sizes 1000,5000,10000,25000]
"""
import argparse
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_okx_xperp", ROOT / "scripts" / "record_okx_xperp.py")
okx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(okx)            # reuse merge_rows, day_of and walk_cost (not changed)

API = "https://api.hyperliquid.xyz/info"
PAUSE = 0.3                              # l2Book weighs 2 of 1,200 a minute per IP; 150 markets take under a minute
SIZES = (1_000, 5_000, 10_000, 25_000)
MARKET_COLS = ["dex", "coin", "day", "growthMode", "deployerFeeScale", "lastFeeScaleChangeTime", "maxLeverage"]
log = okx.log


def book_cols(sizes):
    return (["dex", "coin", "ts", "bid", "ask", "spread_bp", "depth_bid_usd", "depth_ask_usd"]
            + [f"{s}_{n}_bp" for n in sizes for s in ("buy", "sell")]
            + ["mark", "oracle", "funding", "premium", "open_interest", "day_ntl_vlm"])


def post(body, tries=4):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(API, json.dumps(body).encode(),
                                         {"Content-Type": "application/json", "User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            time.sleep(PAUSE)
            return d
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{body.get('type')} {body.get('coin', body.get('dex', ''))}: {err}")


def book_row(dex, book, ctx, sizes):
    """One CSV row from an l2Book response ({coin, time, levels: [bids, asks]}, each level {px, sz, n}) and the
    market's context from metaAndAssetCtxs. None if either side is empty."""
    bids = [[float(x["px"]), float(x["sz"])] for x in book["levels"][0]]
    asks = [[float(x["px"]), float(x["sz"])] for x in book["levels"][1]]
    if not bids or not asks:
        return None
    bid, ask = bids[0][0], asks[0][0]
    mid = (bid + ask) / 2
    usd = lambda px, sz: px * sz                                        # noqa: E731 (linear USD-margined perps)
    row = {"dex": dex, "coin": book["coin"], "ts": int(book["time"]), "bid": bid, "ask": ask,
           "spread_bp": round((ask / bid - 1) * 1e4, 3),
           "depth_bid_usd": round(sum(p * s for p, s in bids), 2),
           "depth_ask_usd": round(sum(p * s for p, s in asks), 2)}
    for n in sizes:
        row[f"buy_{n}_bp"] = okx.walk_cost(asks, n, mid, "buy", usd)
        row[f"sell_{n}_bp"] = okx.walk_cost(bids, n, mid, "sell", usd)
    row.update({"mark": ctx.get("markPx"), "oracle": ctx.get("oraclePx"), "funding": ctx.get("funding"),
                "premium": ctx.get("premium"), "open_interest": ctx.get("openInterest"),
                "day_ntl_vlm": ctx.get("dayNtlVlm")})
    return row


def record(out, dexes=("xyz",), sizes=SIZES, now_ms=None):
    """One snapshot of every listed (not delisted) market on each dex. Returns (books written, markets failed)."""
    out = Path(out)
    now_ms = now_ms or int(time.time() * 1000)
    day = okx.day_of(now_ms)
    cols = book_cols(sizes)
    rows, markets, failed = [], [], 0
    for dex in dexes:
        meta, ctxs = post({"type": "metaAndAssetCtxs", "dex": dex})
        for u, ctx in zip(meta["universe"], ctxs):
            if u.get("isDelisted"):
                continue
            markets.append({"dex": dex, "coin": u["name"], "day": day, "growthMode": u.get("growthMode", ""),
                            "deployerFeeScale": u.get("deployerFeeScale", ""),
                            "lastFeeScaleChangeTime": u.get("lastFeeScaleChangeTime", ""),
                            "maxLeverage": u.get("maxLeverage", "")})
            try:
                r = book_row(dex, post({"type": "l2Book", "coin": u["name"]}), ctx, sizes)
            except (RuntimeError, KeyError, IndexError, TypeError, ValueError) as e:
                log(f"{u['name']}: {e}")
                failed += 1
                continue
            if r:
                rows.append(r)
    for d, rs in okx.by_day(rows, "ts").items():
        okx.merge_rows(out / "books" / f"{d}.csv", rs, cols, ["dex", "coin", "ts"])
    okx.merge_rows(out / "markets" / f"{day}.csv", markets, MARKET_COLS, ["dex", "coin"])
    (out / "last_run.json").write_text(json.dumps(
        {"utc": datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat(timespec="seconds"),
         "dexes": list(dexes), "markets": len(markets), "books": len(rows), "failed": failed}, indent=1) + "\n")
    return len(rows), failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dex", action="append", help="HIP-3 dex name (repeatable; default xyz)")
    ap.add_argument("--sizes", default=",".join(str(s) for s in SIZES))
    a = ap.parse_args()
    sizes = tuple(int(s) for s in a.sizes.split(","))
    n, failed = record(a.out, tuple(a.dex or ["xyz"]), sizes)
    log(f"books {n}, failed {failed}")
    if n == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
