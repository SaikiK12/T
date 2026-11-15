"""bgcosts_v1 (R495, M543): measured taker cost on Binance and Gate for the C14 carry universe.

Measurement only. Public order books, no key, places nothing. R404's recorder is NOT touched: its
frozen PREREG says the recorder is not changed, so this is a separate lane with its own outputs.

Binance sizes are in coins; Gate's `s` is in CONTRACTS and must be scaled by quanto_multiplier,
which differs per contract (BTC_USDT is 0.0001). Getting that wrong moves the cost by orders of
magnitude, so the multiplier is fetched per contract and a contract without one is skipped.

usage: python scripts/record_bg_costs.py [--limit N] [--dry]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments/bgcosts_v1"
SYMBOLS = ROOT / "experiments/xfund_v1/symbols.csv"
BINANCE = "https://www.binance.com/fapi/v1"      # fapi.binance.com is 451 here; lab/live.py's path
GATE = "https://api.gateio.ws/api/v4/futures/usdt"
SIZES = (1_000, 5_000, 10_000)
NEAR = 0.01
DEPTH = 100
PAUSE = 0.2
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
                raise                                   # never retry-storm a rate limit
            last = e
        except Exception as e:
            last = e
        time.sleep(PAUSE * (k + 1))
    raise last


def side_cost(levels, mid, usd, buy):
    """bp from mid to the average fill of a `usd` market order; NaN if the book cannot fill it."""
    got = 0.0
    cost = 0.0
    for px, qty_usd in levels:
        take = min(qty_usd, usd - got)
        cost += take * px
        got += take
        if got >= usd - 1e-9:
            avg = cost / got
            return (avg / mid - 1.0) * 1e4 if buy else (1.0 - avg / mid) * 1e4
    return float("nan")


def measure(bids, asks):
    """bids/asks are lists of (price, usd_notional_at_that_level), best first."""
    if not bids or not asks:
        return None
    bp, ap = bids[0][0], asks[0][0]
    if bp <= 0 or ap <= 0 or ap < bp:
        return None
    mid = (bp + ap) / 2.0
    out = {"best_bid": bp, "best_ask": ap, "mid": mid,
           "half_spread_bp": (ap - bp) / 2.0 / mid * 1e4,
           "usd_bid_1pct": sum(q for p, q in bids if p >= mid * (1 - NEAR)),
           "usd_ask_1pct": sum(q for p, q in asks if p <= mid * (1 + NEAR))}
    for n in SIZES:
        b = side_cost(bids, mid, n, False)
        a = side_cost(asks, mid, n, True)
        out[f"side_{n//1000}k_bp"] = (b + a) / 2.0 if np.isfinite(b) and np.isfinite(a) else float("nan")
        out[f"unfilled_{n//1000}k"] = not (np.isfinite(b) and np.isfinite(a))
    return out


def binance_book(sym):
    d = get(f"{BINANCE}/depth?symbol={sym}&limit={DEPTH}")
    bids = [(float(p), float(q) * float(p)) for p, q in d["bids"]]   # q is in coins
    asks = [(float(p), float(q) * float(p)) for p, q in d["asks"]]
    return measure(bids, asks)


def gate_book(sym, mult):
    d = get(f"{GATE}/order_book?contract={sym}&limit={DEPTH}")
    bids = [(float(x["p"]), float(x["s"]) * mult * float(x["p"])) for x in d["bids"]]
    asks = [(float(x["p"]), float(x["s"]) * mult * float(x["p"])) for x in d["asks"]]
    return measure(bids, asks)


def gate_meta(sym):
    d = get(f"{GATE}/contracts/{sym}")
    m = float(d.get("quanto_multiplier") or 0)
    return (m if m > 0 else None), float(d.get("taker_fee_rate") or "nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="first N contracts, for a bounded smoke run")
    ap.add_argument("--dry", action="store_true", help="parse and report, write nothing")
    a = ap.parse_args()
    frozen = prereg.verify(LANE / "PREREG.md")
    df = pd.read_csv(SYMBOLS)
    df = df[df.binance.notna() & df.gate.notna()]
    if a.limit:
        df = df.head(a.limit)
    pairs = list(df[["key", "binance", "gate"]].itertuples(index=False, name=None))
    log(f"{len(pairs)} contracts, 2 venues, PREREG {frozen[:12]}")

    rows, errors = [], []
    started = datetime.now(timezone.utc).isoformat()

    def one(pair):
        key, bsym, gsym = pair
        out = []
        try:
            time.sleep(PAUSE)
            m = binance_book(bsym)
            if m:
                out.append({"key": key, "venue": "binance", "symbol": bsym, **m})
        except Exception as e:
            errors.append({"venue": "binance", "symbol": bsym, "error": f"{type(e).__name__}: {e}"[:120]})
        try:
            time.sleep(PAUSE)
            mult, fee = gate_meta(gsym)
            if mult is None:
                errors.append({"venue": "gate", "symbol": gsym, "error": "no quanto_multiplier"})
            else:
                m = gate_book(gsym, mult)
                if m:
                    out.append({"key": key, "venue": "gate", "symbol": gsym,
                                 "quanto_multiplier": mult, "taker_fee_rate": fee, **m})
        except Exception as e:
            errors.append({"venue": "gate", "symbol": gsym, "error": f"{type(e).__name__}: {e}"[:120]})
        return out

    with ThreadPoolExecutor(2) as ex:
        for i, got in enumerate(ex.map(one, pairs), 1):
            rows.extend(got)
            if i % 100 == 0:
                log(f"  {i}/{len(pairs)} contracts, {len(rows)} rows, {len(errors)} errors")
    if not rows:
        raise SystemExit("no book measured; nothing written")
    t = pd.DataFrame(rows)
    bands = []
    for venue, g in t.groupby("venue"):
        bands.append({
            "venue": venue, "contracts": int(len(g)),
            "median_half_spread_bp": float(g.half_spread_bp.median()),
            **{f"median_side_{n//1000}k_bp": float(g[f"side_{n//1000}k_bp"].median()) for n in SIZES},
            **{f"unfilled_share_{n//1000}k": float(g[f"unfilled_{n//1000}k"].mean()) for n in SIZES},
        })
    both = {v: int(t[(t.venue == v) & t.side_10k_bp.notna()].shape[0]) for v in ("binance", "gate")}
    priceable = both["binance"] >= 60 and both["gate"] >= 60
    rep = {
        "round": "R495", "method": "M543", "lane": "bgcosts_v1",
        "prereg_sha256": frozen, "started_utc": started,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "trials": 0, "contracts_requested": len(pairs), "rows": len(t),
        "finite_10k_by_venue": both,
        "verdict": "PRICEABLE" if priceable else "NOT PRICEABLE",
        "c14_cost_1x_bp_leg_side": 7.0,
        "multiple_of_c14_1x": {b["venue"]: b["median_side_10k_bp"] / 7.0 for b in bands},
        "by_venue": bands,
        "errors": errors[:50], "error_count": len(errors),
        "limits": [
            "one snapshot; R224 needed 102 to call a cost surface stable",
            "current listings only: delisted contracts cannot be measured",
            "shown book only: no queue, no latency, no impact beyond the displayed levels",
            "no strategy test and no reserved read; C14's and R390's frozen rules are unchanged",
        ],
    }
    if a.dry:
        log("dry run, nothing written")
    else:
        out = LANE / "results"
        out.mkdir(exist_ok=True)
        t.to_csv(out / "books.csv", index=False)
        (out / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("verdict", "finite_10k_by_venue", "by_venue",
                                          "multiple_of_c14_1x", "error_count")}, indent=1))


if __name__ == "__main__":
    main()
