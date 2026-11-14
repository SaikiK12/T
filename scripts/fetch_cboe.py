"""Cboe volatility index history (free daily CSVs, no key): the term structure (VIX1D, VIX9D, VIX, VIX3M, VIX6M,
VIX1Y), vol of vol (VVIX), tail pricing (SKEW) and the other asset classes' vol indices (VXN, RVX, VXD, OVX, GVZ).

Why: the VIX term structure and VVIX are the classic "panic" gauges. When VIX trades above VIX3M (backwardation) or VVIX
spikes, hedgers are paying up for near-term protection, and practitioners read that as a sign of a short-term bottom
(docs/VIDEO_DIG.md, method M277). The lab already holds FRED's VIX close; this adds the rest of the curve.

Each series goes to data/cboe/<NAME>.parquet with columns day (YYYY-MM-DD), t (ms at 00:00 UTC of that day), open,
high, low, close (VVIX and SKEW have close only, in `close`). A day's close is the 16:15 ET settlement, so it is public
from about 21:15 UTC that day: a lane must not act on day D's close before then. Raw responses are kept in
data/cboe/raw/ with their sha256 in data/cboe/manifest.json. Re-running replaces both (Cboe revises nothing in history,
but the latest day appears each evening).

usage: python scripts/fetch_cboe.py
"""
import hashlib
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "cboe"
URL = "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/{}_History.csv"
SERIES = ("VIX1D", "VIX9D", "VIX", "VIX3M", "VIX6M", "VIX1Y", "VVIX", "SKEW", "VXN", "RVX", "VXD", "OVX", "GVZ")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; lab)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001  (network: retry, then give up on this series)
            if k == tries - 1:
                raise
            log(f"retry {url}: {e}")
            time.sleep(2 ** k)


def parse(raw):
    """A Cboe history CSV to (day, t, open, high, low, close), one row per day, the last row kept for a repeated day."""
    df = pd.read_csv(io.BytesIO(raw))
    df.columns = [c.strip().lower() for c in df.columns]
    if "close" not in df.columns:                      # VVIX and SKEW: DATE,<NAME>
        df = df.rename(columns={df.columns[1]: "close"})
    for c in ("open", "high", "low"):
        if c not in df.columns:
            df[c] = float("nan")
    d = pd.to_datetime(df["date"], format="%m/%d/%Y")
    out = pd.DataFrame({"day": d.dt.strftime("%Y-%m-%d"), "t": (d - pd.Timestamp("1970-01-01")) // pd.Timedelta("1ms")})
    for c in ("open", "high", "low", "close"):
        out[c] = pd.to_numeric(df[c], errors="coerce")
    out = out.dropna(subset=["close"]).drop_duplicates("day", keep="last").sort_values("t").reset_index(drop=True)
    return out


def main():
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in SERIES:
        try:
            raw = get(URL.format(name))
        except Exception as e:  # noqa: BLE001
            log(f"{name}: failed ({e})")
            continue
        (OUT / "raw" / f"{name}_History.csv").write_bytes(raw)
        df = parse(raw)
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        manifest[name] = {"url": URL.format(name), "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(df),
                          "first": df.day.iloc[0], "last": df.day.iloc[-1]}
        log(f"{name}: {len(df)} days {df.day.iloc[0]}..{df.day.iloc[-1]}")
    (OUT / "manifest.json").write_text(json.dumps({"fetched_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
                                                   "series": manifest}, indent=1))
    return 0 if manifest else 1


if __name__ == "__main__":
    sys.exit(main())
