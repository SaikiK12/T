"""Hourly snapshot of the Deribit option chains (BTC, ETH, and the USDC-settled ones such as SOL and XRP): open
interest, mark implied volatility, prices and the underlying of every listed option, from one public bulk request per
currency. For M289 (expiry pinning toward the largest strike) and M300 (dealer gamma exposure, the "GEX levels" of
the owner's reels, docs/REELS_TRANSCRIPT.md). Deribit's public API gives the current chain only, so open interest by
strike over time exists only if recorded.

One file per UTC hour, data/recorders/deribit_chain/<YYYY-MM-DD>/<HH>.parquet (gitignored, digests committed by
record_digest.py); a second run in the same hour writes nothing. A currency that fails is skipped and named in the log.
Data collection only. `gex()` turns a snapshot into gamma notional per strike under a stated dealer convention.

usage: python scripts/record_deribit_chain.py
"""
import json
import math
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "recorders" / "deribit_chain"
URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={}&kind=option"
CURRENCIES = ("BTC", "ETH", "USDC")
COLS = ["ts", "currency", "base", "instrument", "expiry_ms", "strike", "cp", "oi", "volume_usd", "mark_iv",
        "mark_price", "bid", "ask", "underlying_price", "underlying_index", "index_price"]
NAME = re.compile(r"^([A-Z0-9_]+)-(\d{1,2}[A-Z]{3}\d{2})-([0-9d.]+)-([CP])$")
MONTHS = {m: i for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV",
                                      "DEC"), 1)}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def http(currency):
    req = urllib.request.Request(URL.format(currency), headers={"User-Agent": "lab/1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["result"]


def parse(name):
    """(base, expiry at 08:00 UTC in ms, strike, 'C' or 'P') from e.g. BTC-27NOV26-73000-P or SOL_USDC-5DEC26-1d5-C
    ('d' is Deribit's decimal point); None for anything else."""
    m = NAME.match(name)
    if not m:
        return None
    base, day, strike, cp = m.groups()
    d = re.match(r"(\d{1,2})([A-Z]{3})(\d{2})", day)
    ts = pd.Timestamp(year=2000 + int(d.group(3)), month=MONTHS[d.group(2)], day=int(d.group(1)), hour=8, tz="UTC")
    return base.split("_")[0], int(ts.value // 10**6), float(strike.replace("d", ".")), cp


def rows(currency, result, ts):
    out = []
    for o in result:
        p = parse(o.get("instrument_name", ""))
        if p is None:
            continue
        base, exp, k, cp = p
        out.append({"ts": ts, "currency": currency, "base": base, "instrument": o["instrument_name"],
                    "expiry_ms": exp, "strike": k, "cp": cp, "oi": o.get("open_interest"),
                    "volume_usd": o.get("volume_usd"), "mark_iv": o.get("mark_iv"), "mark_price": o.get("mark_price"),
                    "bid": o.get("bid_price"), "ask": o.get("ask_price"), "underlying_price": o.get("underlying_price"),
                    "underlying_index": o.get("underlying_index"), "index_price": o.get("estimated_delivery_price")})
    return out


def gex(df, sign_calls=1.0, sign_puts=-1.0):
    """Gamma notional per (base, strike) in USD per 1% move of the underlying: OI x Black-76 gamma x F^2 x 0.01,
    summed over expiries. The default signs are the common equity convention (dealers long calls, short puts): an
    assumption about who holds the other side, not something the data shows; call_gex and put_gex are returned apart
    so another convention can be applied."""
    x = df[(df.oi > 0) & (df.mark_iv > 0) & (df.expiry_ms > df.ts)].copy()
    T = (x.expiry_ms - x.ts) / (365.25 * 86_400_000)
    F, K, s = x.underlying_price.astype(float), x.strike.astype(float), x.mark_iv.astype(float) / 100
    d1 = (np.log(F / K) + 0.5 * s * s * T) / (s * np.sqrt(T))
    gamma = np.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (F * s * np.sqrt(T))
    x["g"] = x.oi * gamma * F * F * 0.01
    out = x.pivot_table(index=["base", "strike"], columns="cp", values="g", aggfunc="sum", fill_value=0.0)
    out = out.reindex(columns=["C", "P"], fill_value=0.0).rename(columns={"C": "call_gex", "P": "put_gex"})
    out["net_gex"] = sign_calls * out.call_gex + sign_puts * out.put_gex
    return out.reset_index()


def main(get=http):
    now = time.gmtime()
    path = OUT / time.strftime("%Y-%m-%d", now) / f"{time.strftime('%H', now)}.parquet"
    if path.exists():
        log(f"deribit chain: {path.relative_to(ROOT)} already written")
        return path
    ts, out = int(time.time() * 1000), []
    for c in CURRENCIES:
        try:
            out += rows(c, get(c), ts)
        except Exception as e:  # noqa: BLE001 - one currency failing does not stop the others
            log(f"deribit chain: {c} failed: {e}")
    if not out:
        log("deribit chain: nothing read")
        return None
    df = pd.DataFrame(out, columns=COLS)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")              # record_digest.py skips .part files
    df.to_parquet(tmp, index=False)
    tmp.replace(path)
    log(f"deribit chain: {len(df)} options ({', '.join(f'{b} {n}' for b, n in df.base.value_counts().items())}) "
        f"-> {path.relative_to(ROOT)}")
    return path


if __name__ == "__main__":
    main()
