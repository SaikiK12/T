"""Inputs for R462 xyzwknd_v1 (trade.xyz US-equity perps over the weekend). Two steps, both public and keyless, with a
generic client name:

universe  -> experiments/xyzwknd_v1/universe.csv (run before the freeze; names and filings only, no price)
    - trade.xyz's documentation (https://docs.trade.xyz/llms-full.txt): the Specification Index rows whose external
      session is "24/5, from Sunday 8:05 PM ET to Friday 8:00 PM ET" (US stocks and US-listed funds). The listed
      ticker comes from the row's description ("(Nasdaq: XXX)"), etf = 1 when the description says ETF or fund.
    - Hyperliquid info API (meta, dex xyz): growthMode and deployerFeeScale of each market on the day of the fetch.
    - SEC EDGAR (company_tickers_exchange.json, submissions/CIK##########.json): the first 424B4 prospectus filed
      before any 10-K, 10-Q, 20-F or 40-F, taken as the IPO date of a company that listed recently (its earlier
      xyz history may be a Pre-IPO perp). Blank for funds, for companies already reporting, or when not found.
bars      -> data/xyz_wknd/ (run after the freeze; gitignored, recorded with scripts/data_provenance.py)
    - klines_1h/<COIN>.parquet: candleSnapshot 1 h (t open ms, T, o, h, l, c, v, n) over [--start, --end)
    - funding/<COIN>.parquet: fundingHistory (time ms, rate, premium) over the same window
    - receipts.jsonl (one sha256 per response) and manifest.json (per-file sha256)

usage: python scripts/fetch_xyz_wknd.py universe --docs <saved llms-full.txt>
       python scripts/fetch_xyz_wknd.py bars --start 2026-04-01T00:00:00Z --end 2026-11-10T00:00:00Z
"""
import argparse
import csv
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LANE = ROOT / "experiments" / "xyzwknd_v1"
OUT = ROOT / "data" / "xyz_wknd"
INFO = "https://api.hyperliquid.xyz/info"
UA = "lab-research-fetch/1.0"
US_SESSION = "24/5, from Sunday 8:05 PM ET to Friday 8:00 PM ET"
PERIODIC = {"10-K", "10-Q", "20-F", "40-F"}
COLS = ["coin", "us_ticker", "etf", "growth", "fee_scale", "cik", "ipo_424b4"]


def http(url, data=None, tries=5):
    head = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        head["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=head), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k == tries - 1:
                raise
        except Exception:
            if k == tries - 1:
                raise
        time.sleep(2 ** (k + 1))


def spec_rows(text):
    """[(coin, description, external session)] from the Specification Index table of llms-full.txt."""
    i = text.index("# Specification Index\n\nConsolidated")
    j = text.index("# Pre-IPO Specification Index")
    out = []
    for r in re.findall(r"<tr>(.*?)</tr>", text[i:j], re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(cells) >= 9:
            out.append((cells[0].split("/")[0].strip(), cells[1], cells[7]))
    return out


def ipo_date(sub):
    """First 424B4 filed before any periodic report, from a submissions JSON (recent block)."""
    rec = sub["filings"]["recent"]
    rows = sorted(zip(rec["filingDate"], rec["form"]))
    for d, f in rows:
        if f in PERIODIC:
            return ""
        if f == "424B4":
            return d
    return ""


def universe(docs):
    text = Path(docs).read_text()
    rows = [r for r in spec_rows(text) if r[2].startswith(US_SESSION)]
    meta = json.loads(http(INFO, {"type": "meta", "dex": "xyz"}))
    fee = {u["name"].split(":", 1)[1]: (u.get("growthMode", ""), u.get("deployerFeeScale", ""))
           for u in meta["universe"] if not u.get("isDelisted")}
    ex = json.loads(http("https://www.sec.gov/files/company_tickers_exchange.json"))
    cik = {r[2].upper(): int(r[0]) for r in ex["data"] if r[3] in ("Nasdaq", "NYSE", "CBOE")}
    out = []
    for coin, desc, _ in rows:
        m = re.search(r"\((?:Nasdaq|NYSE|NYSE Arca|NYSE American|Cboe BZX)[^:]*:\s*([A-Z.]+)\)", desc)
        tick = m.group(1) if m else coin
        etf = 1 if re.search(r"\bETF\b|\b[Ff]und\b", desc) else 0
        c = cik.get(tick.upper())
        ipo = ""
        if c and not etf:
            raw = http(f"https://data.sec.gov/submissions/CIK{c:010d}.json")
            time.sleep(0.2)
            ipo = ipo_date(json.loads(raw)) if raw else ""
        g, s = fee.get(coin, ("", ""))
        out.append({"coin": coin, "us_ticker": tick, "etf": etf, "growth": g or "", "fee_scale": s,
                    "cik": c or "", "ipo_424b4": ipo})
    LANE.mkdir(parents=True, exist_ok=True)
    with open(LANE / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(len(out), "markets;", sum(r["etf"] for r in out), "funds;", sum(1 for r in out if r["ipo_424b4"]),
          "recent IPOs; docs sha256", hashlib.sha256(text.encode()).hexdigest())


def epoch_ms(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)


def post(body, rec):
    raw = http(INFO, body)
    rec.write(json.dumps({"body": body, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                          "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    time.sleep(0.3)
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
