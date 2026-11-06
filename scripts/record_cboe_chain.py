"""Twice-daily snapshot of the Cboe delayed option chains for QQQ, SPY and SPX: open interest, volume, implied
volatility, delta, gamma, bid and ask of every listed option, from Cboe's free public delayed-quotes JSON (15 minutes
delayed, no key). For M486 and M300: the dealer gamma map as it stood before each US session. Cboe gives the current
chain only, so a pre-session map exists only if it is recorded.

Two sessions per New York weekday:
- `pre`: the first run between 08:00 and 09:29 New York time. Open interest is the prior close's, from the OCC, so this
  is the map a trader could see before the open.
- `post`: the first run between 16:20 and 18:59 New York time, after the close.

One file per session and underlying: data/recorders/cboe_chain/<YYYY-MM-DD>/<session>_<SYM>.parquet (gitignored; digests
committed by record_digest.py). A file that exists is never rewritten. An underlying that fails is skipped and named in
the log. Data collection only. `gex()` turns a snapshot into dollar gamma per 1% move by strike under a stated dealer
convention.

usage: python scripts/record_cboe_chain.py [--force SESSION]
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "recorders" / "cboe_chain"
URL = "https://cdn-api.cboe.com/api/global/delayed_quotes/options/{}.json"
SYMBOLS = {"QQQ": "QQQ", "SPY": "SPY", "SPX": "_SPX"}
NY = ZoneInfo("America/New_York")
WINDOWS = {"pre": ((8, 0), (9, 29)), "post": ((16, 20), (18, 59))}
COLS = ["ts", "underlying", "option", "expiry", "cp", "strike", "oi", "volume", "iv", "delta", "gamma", "bid", "ask",
        "spot"]
NAME = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def session(now_utc):
    """'pre' or 'post' if now is inside that New York window on a weekday, else None."""
    t = now_utc.astimezone(NY)
    if t.weekday() >= 5:
        return None
    hm = (t.hour, t.minute)
    for name, (lo, hi) in WINDOWS.items():
        if lo <= hm <= hi:
            return name
    return None


def http(code):
    req = urllib.request.Request(URL.format(code), headers={"User-Agent": "lab/1"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def table(doc, underlying):
    """One row per option. Options whose name does not parse are dropped and counted."""
    d = doc["data"]
    rows, bad = [], 0
    for o in d["options"]:
        m = NAME.match(o.get("option", ""))
        if not m:
            bad += 1
            continue
        rows.append({"option": o["option"], "expiry": pd.Timestamp(datetime.strptime(m.group(2), "%y%m%d")),
                     "cp": m.group(3), "strike": int(m.group(4)) / 1000.0, "oi": o.get("open_interest"),
                     "volume": o.get("volume"), "iv": o.get("iv"), "delta": o.get("delta"), "gamma": o.get("gamma"),
                     "bid": o.get("bid"), "ask": o.get("ask")})
    t = pd.DataFrame(rows)
    t.insert(0, "underlying", underlying)
    t.insert(0, "ts", pd.Timestamp(doc["timestamp"]))
    t["spot"] = float(d["current_price"])
    for c in ("oi", "volume", "iv", "delta", "gamma", "bid", "ask"):
        t[c] = pd.to_numeric(t[c], errors="coerce")
    return t[COLS], bad


def gex(t, sign=1):
    """Dollar gamma per 1% move by strike: gamma x OI x 100 x S^2 x 1%, calls +1 and puts -1 (dealers long calls,
    short puts, the common convention); sign=-1 flips it. Returns a Series indexed by strike."""
    s = t["spot"].astype(float)
    g = t["gamma"] * t["oi"] * 100 * s * s * 0.01 * t["cp"].map({"C": 1.0, "P": -1.0}) * sign
    return g.groupby(t["strike"]).sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", choices=sorted(WINDOWS), help="record this session now, outside its window")
    a = ap.parse_args()
    now = datetime.now(timezone.utc)
    sess = a.force or session(now)
    if sess is None:
        log("outside the pre/post windows; nothing to do")
        return
    day = now.astimezone(NY).strftime("%Y-%m-%d")
    out = OUT / day
    out.mkdir(parents=True, exist_ok=True)
    for name, code in SYMBOLS.items():
        p = out / f"{sess}_{name}.parquet"
        if p.exists():
            continue
        try:
            t, bad = table(http(code), name)
        except Exception as e:  # noqa: BLE001 - one failed underlying must not stop the others
            log(f"{name}: failed ({type(e).__name__}: {e})")
            continue
        tmp = p.with_suffix(".tmp")
        t.to_parquet(tmp, index=False, compression="zstd")
        tmp.rename(p)
        g = gex(t)
        log(f"{name} {sess}: {len(t)} options ({bad} unparsed), spot {t.spot.iloc[0]}, net GEX "
            f"{g.sum() / 1e9:+.2f} $bn per 1%, {p.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
