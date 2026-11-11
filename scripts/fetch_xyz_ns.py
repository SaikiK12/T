"""Inputs for R464 xyzns_wknd_v1 (trade.xyz index, commodity and FX perps over the weekend). Two steps, both public
and keyless, with a generic client name:

universe  -> experiments/xyzns_wknd_v1/universe.csv (run before the freeze; names and sessions only, no price)
    - trade.xyz's documentation (https://docs.trade.xyz/llms-full.txt): the Specification Index rows of the 14 US
      equity-index, commodity and FX markets below, with their external session ("From Sunday 6PM ET to Friday 5PM
      ET"). The Friday close and the Sunday reopen come from that text.
    - Hyperliquid info API (meta, dex xyz): the API coin name (WTIOIL is `xyz:CL`, DIESEL is `xyz:HO`), growthMode
      and deployerFeeScale on the day of the fetch.
bars      -> data/xyz_ns/ (run after the freeze; gitignored, recorded with scripts/data_provenance.py)
    - klines_1h/<COIN>.parquet: candleSnapshot 1 h (t open ms, T, o, h, l, c, v, n) over [--start, --end)
    - funding/<COIN>.parquet: fundingHistory (time ms, rate, premium) over the same window
    - receipts.jsonl (one sha256 per response) and manifest.json (per-file sha256)

usage: python scripts/fetch_xyz_ns.py universe --docs <saved llms-full.txt>
       python scripts/fetch_xyz_ns.py bars --start 2026-04-01T00:00:00Z --end 2026-11-10T00:00:00Z
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_xyz_wknd import INFO, http, spec_rows  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "xyzns_wknd_v1"
OUT = ROOT / "data" / "xyz_ns"
CLASSES = {"SP500": "index", "XYZ100": "index",
           "GOLD": "metal", "SILVER": "metal", "PLATINUM": "metal", "PALLADIUM": "metal", "COPPER": "metal",
           "WTIOIL": "energy", "BRENTOIL": "energy", "NATGAS": "energy", "DIESEL": "energy",
           "EUR": "fx", "GBP": "fx", "JPY": "fx"}
API_NAME = {"WTIOIL": "CL", "DIESEL": "HO"}
COLS = ["coin", "spec", "cls", "close_et", "reopen_et", "growth", "fee_scale"]
SESSION = re.compile(r"From Sunday (\d{1,2})(?::(\d\d))? ?PM ET to Friday (\d{1,2})(?::(\d\d))? ?PM ET")


def session_times(text):
    """('HH:MM' Friday close, 'HH:MM' Sunday reopen) from 'From Sunday 6:00 PM ET to Friday 5:00 PM ET'."""
    m = SESSION.search(text)
    if not m:
        raise ValueError(f"no weekly session in {text!r}")
    reopen = f"{int(m.group(1)) + 12:02d}:{m.group(2) or '00'}"
    close = f"{int(m.group(3)) + 12:02d}:{m.group(4) or '00'}"
    return close, reopen


def universe(docs):
    text = Path(docs).read_text()
    rows = {c: s for c, _, s in spec_rows(text) if c in CLASSES}
    missing = sorted(set(CLASSES) - set(rows))
    if missing:
        raise SystemExit(f"spec rows missing: {missing}")
    meta = json.loads(http(INFO, {"type": "meta", "dex": "xyz"}))
    live = {u["name"].split(":", 1)[1]: u for u in meta["universe"] if not u.get("isDelisted")}
    out = []
    for spec, cls in CLASSES.items():
        coin = API_NAME.get(spec, spec)
        if coin not in live:
            raise SystemExit(f"xyz:{coin} not in meta")
        close, reopen = session_times(rows[spec])
        u = live[coin]
        out.append({"coin": coin, "spec": spec, "cls": cls, "close_et": close, "reopen_et": reopen,
                    "growth": u.get("growthMode", "") or "", "fee_scale": u.get("deployerFeeScale", "")})
    LANE.mkdir(parents=True, exist_ok=True)
    with open(LANE / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(len(out), "markets;", sum(r["growth"] == "enabled" for r in out), "in growth mode; docs sha256",
          hashlib.sha256(text.encode()).hexdigest())


def epoch_ms(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)


def post(body, rec):
    raw = http(INFO, body)
    rec.write(json.dumps({"body": body, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                          "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    time.sleep(0.5)
    return json.loads(raw)


def bars(start, end):
    with open(LANE / "universe.csv", newline="") as f:
        coins = [r["coin"] for r in csv.DictReader(f)]
    s0, s1 = epoch_ms(start), epoch_ms(end)
    (OUT / "klines_1h").mkdir(parents=True, exist_ok=True)
    (OUT / "funding").mkdir(parents=True, exist_ok=True)
    man = {"kind": "hyperliquid_xyz_1h_and_funding", "start": start, "end_exclusive": end, "files": {},
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(OUT / "receipts.jsonl", "a") as rec:
        for coin in coins:
            name = "xyz:" + coin
            k = post({"type": "candleSnapshot", "req": {"coin": name, "interval": "1h", "startTime": s0,
                                                        "endTime": s1}}, rec)
            kd = pd.DataFrame([{"t": int(x["t"]), "T": int(x["T"]), "o": float(x["o"]), "h": float(x["h"]),
                                "l": float(x["l"]), "c": float(x["c"]), "v": float(x["v"]), "n": int(x["n"])}
                               for x in k if s0 <= int(x["t"]) < s1],
                              columns=["t", "T", "o", "h", "l", "c", "v", "n"]).drop_duplicates("t").sort_values("t")
            fr, s = [], s0
            while s < s1:
                page = post({"type": "fundingHistory", "coin": name, "startTime": s, "endTime": s1}, rec)
                if not page:
                    break
                fr += [{"time": int(x["time"]), "rate": float(x["fundingRate"]), "premium": float(x["premium"])}
                       for x in page if int(x["time"]) < s1]
                s = int(page[-1]["time"]) + 1
                if len(page) < 500:
                    break
            fd = pd.DataFrame(fr, columns=["time", "rate", "premium"]).drop_duplicates("time").sort_values("time")
            for sub, df in (("klines_1h", kd), ("funding", fd)):
                p = OUT / sub / f"{coin}.parquet"
                df.to_parquet(p, index=False)
                man["files"][f"{sub}/{coin}.parquet"] = {"rows": len(df), "sha256": hashlib.sha256(
                    p.read_bytes()).hexdigest()}
            print(coin, len(kd), "candles", len(fd), "funding", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(len(coins), "markets")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("universe")
    u.add_argument("--docs", required=True)
    b = sub.add_parser("bars")
    b.add_argument("--start", required=True)
    b.add_argument("--end", required=True)
    a = ap.parse_args()
    if a.cmd == "universe":
        universe(a.docs)
    else:
        bars(a.start, a.end)


if __name__ == "__main__":
    main()
