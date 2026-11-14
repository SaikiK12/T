"""Inputs for adlstress_v1 (R487, M534): public daily candles (and 1h candles of 2025-10-09/10) for every (venue, coin)
leg of the carry pairs open on 2025-10-10. Run once, after the PREREG freeze.

The legs come from the two committed trades_v2.csv files: pairs with entry_day <= 2025-10-10 <= exit_day (the inclusive
set, a superset of the exposed pairs the runner scores). Per (venue, coin) the daily range runs from two days before
the leg's earliest entry_day to 2025-10-12.

Keyless, public sources (symbols from experiments/xfund_v1/symbols.csv and experiments/xfund_kd_v1/symbols.csv):
- gate:        GET api.gateio.ws/api/v4/futures/usdt/candlesticks (interval 1d and 1h; from/to in seconds)
- kucoin:      GET api-futures.kucoin.com/api/v1/kline/query (granularity 1440 and 60; from/to in ms; paged by 180 days)
- mexc:        GET contract.mexc.com/api/v1/contract/kline/{symbol} (interval Day1 and Min60; start/end in seconds)
- hyperliquid: POST api.hyperliquid.xyz/info candleSnapshot (interval 1d and 1h; ms)
- binance:     data.binance.vision USD-M monthly 1d zips and daily 1h zips (fapi.binance.com answers 451 here)
Every body is saved byte-exact under raw/<venue>/; raw/manifest.json lists each request (URL or POST body, HTTP
status, error) and every file's sha256. A failed request is recorded, not retried beyond the backoff. No value is
printed. Data collection only: no order, no key.

usage: python scripts/fetch_adlstress.py [--out experiments/adlstress_v1/raw] [--pause 0.25]
"""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "adlstress_v1" / "raw"
TRADES = (ROOT / "experiments" / "carry_v2_audit_v1" / "results" / "trades_v2.csv",
          ROOT / "experiments" / "carry_v2_audit_kc_v1" / "results" / "trades_v2.csv")
SYMBOLS = (ROOT / "experiments" / "xfund_v1" / "symbols.csv", ROOT / "experiments" / "xfund_kd_v1" / "symbols.csv")
DAY_D = "2025-10-10"
END_D = "2025-10-12"                  # last daily bar fetched opens 2025-10-11 (end bound exclusive of 10-12 bars)
H1_FROM, H1_TO = "2025-10-09", "2025-10-11"
DAY = 86_400_000
UA = {"User-Agent": "Mozilla/5.0 (adlstress_v1 research fetch)"}


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def legs(trades=TRADES, symbols=SYMBOLS):
    """{(venue, coin): (symbol, earliest entry_day)} for every leg of a pair with entry_day <= DAY_D <= exit_day."""
    t = pd.concat([pd.read_csv(p) for p in trades], ignore_index=True)
    o = t[(t.entry_day <= DAY_D) & (t.exit_day >= DAY_D)]
    s1 = pd.read_csv(symbols[0], dtype=str).fillna("").set_index("key")
    s2 = pd.read_csv(symbols[1], dtype=str).fillna("").set_index("key")
    out = {}
    for _, r in o.iterrows():
        for v in (r.long, r.short):
            tab = s2 if v == "kucoin" else s1
            sym = tab.loc[r.coin, v] if r.coin in tab.index and v in tab.columns else ""
            k = (v, r.coin)
            first = min(out[k][1], r.entry_day) if k in out else r.entry_day
            out[k] = (sym, first)
    return dict(sorted(out.items()))


def request(url, body=None, tries=4):
    """(status, bytes or None, error)."""
    delay, err = 1.5, None
    for _ in range(tries):
        try:
            data = json.dumps(body).encode() if body is not None else None
            hdr = dict(UA, **({"Content-Type": "application/json"} if body is not None else {}))
            with urllib.request.urlopen(urllib.request.Request(url, data, hdr), timeout=30) as r:
                return r.status, r.read(), None
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404, 451):
                return e.code, None, str(e)
            err = str(e)
        except OSError as e:
            err = str(e)
        time.sleep(delay)
        delay *= 2
    return None, None, err


def plan(venue, coin, sym, first):
    """[(file name, url, post body)] for one leg."""
    a, b = ms(pd.Timestamp(first) - pd.Timedelta(days=2)), ms(END_D)
    h0, h1 = ms(H1_FROM), ms(H1_TO)
    f = f"{venue}/{coin}"
    if venue == "gate":
        base = "https://api.gateio.ws/api/v4/futures/usdt/candlesticks?contract="
        return [(f"{f}_1d.json", f"{base}{sym}&interval=1d&from={a // 1000}&to={b // 1000 - 1}", None),
                (f"{f}_1h.json", f"{base}{sym}&interval=1h&from={h0 // 1000}&to={h1 // 1000 - 1}", None)]
    if venue == "kucoin":
        base = "https://api-futures.kucoin.com/api/v1/kline/query?symbol="
        out, s, i = [], a, 0
        while s < b:
            e = min(b, s + 180 * DAY)
            out.append((f"{f}_1d_{i:02d}.json", f"{base}{sym}&granularity=1440&from={s}&to={e - 1}", None))
            s, i = e, i + 1
        return out + [(f"{f}_1h.json", f"{base}{sym}&granularity=60&from={h0}&to={h1 - 1}", None)]
    if venue == "mexc":
        base = f"https://contract.mexc.com/api/v1/contract/kline/{sym}?interval="
        return [(f"{f}_1d.json", f"{base}Day1&start={a // 1000}&end={b // 1000 - 1}", None),
                (f"{f}_1h.json", f"{base}Min60&start={h0 // 1000}&end={h1 // 1000 - 1}", None)]
    if venue == "hyperliquid":
        api = "https://api.hyperliquid.xyz/info"
        return [(f"{f}_1d.json", api, {"type": "candleSnapshot",
                                       "req": {"coin": sym, "interval": "1d", "startTime": a, "endTime": b - 1}}),
                (f"{f}_1h.json", api, {"type": "candleSnapshot",
                                       "req": {"coin": sym, "interval": "1h", "startTime": h0, "endTime": h1 - 1}})]
    if venue == "binance":
        base = "https://data.binance.vision/data/futures/um"
        months = pd.period_range(pd.Timestamp(first) - pd.Timedelta(days=2), "2025-10", freq="M")
        out = [(f"binance/{sym}-1d-{m}.zip", f"{base}/monthly/klines/{sym}/1d/{sym}-1d-{m}.zip", None)
               for m in months]
        return out + [(f"binance/{sym}-1h-{d}.zip", f"{base}/daily/klines/{sym}/1h/{sym}-1h-{d}.zip", None)
                      for d in ("2025-10-09", "2025-10-10")]
    raise ValueError(venue)


def fetch(out=OUT, pause=0.25):
    out = Path(out)
    man = {"fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "day": DAY_D, "legs": {},
           "requests": [], "files": {}}
    for (venue, coin), (sym, first) in legs().items():
        man["legs"][f"{venue}/{coin}"] = {"symbol": sym, "first_entry": first}
        if not sym:
            continue
        for name, url, body in plan(venue, coin, sym, first):
            st, raw, err = request(url, body)
            rec = {"file": name, "url": url, "status": st, "error": err}
            if body is not None:
                rec["body"] = body
            if raw is not None:
                (out / name).parent.mkdir(parents=True, exist_ok=True)
                (out / name).write_bytes(raw)
            else:
                rec["file"] = None
            man["requests"].append(rec)
            time.sleep(pause if venue != "binance" else 0.05)
    for p in sorted(x for x in out.rglob("*") if x.is_file() and x.name != "manifest.json"):
        man["files"][str(p.relative_to(out))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--pause", type=float, default=0.25)
    a = ap.parse_args()
    out = fetch(a.out, a.pause)
    man = json.loads((out / "manifest.json").read_text())
    bad = sum(1 for r in man["requests"] if r["file"] is None)
    print(f"{len(man['files'])} bodies written to {out}; {bad} requests without a body")   # counts only


if __name__ == "__main__":
    main()
