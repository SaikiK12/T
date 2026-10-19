"""Daily snapshots of public copy-trading leaderboards (Binance, OKX) for a forward persistence test (docs/CLAIMS.md
C02, C21, C22). Data collection only: no statistic. One file per venue per UTC day; a day already written is skipped,
so running it every tick is harmless. Snapshots are small gzipped CSVs, committed, because the lists keep no history.

usage: python scripts/scrape_leaderboards.py [--venues binance,okx]
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import live  # noqa: E402

OUT = ROOT / "experiments" / "copylead_data" / "snapshots"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
BN_LIST = "bapi/futures/v1/friendly/future/copy-trade/home-page/query-list"
BN_KEEP = ("leadPortfolioId", "nickname", "currentCopyCount", "maxCopyCount", "roi", "pnl", "aum", "mdd", "winRate",
           "copierPnl", "sharpRatio", "portfolioType", "startTime", "apiKeyTag", "tradFiTag")


def post(path, body, tries=4):
    data = json.dumps(body).encode()
    delay = 2.0
    for attempt in range(tries):
        try:
            req = urllib.request.Request(f"{live.BASE}/{path}", data=data, method="POST",
                                         headers={"Content-Type": "application/json", "clienttype": "web",
                                                  "User-Agent": "lab-paper/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise live.LiveError(f"{path}: {err}")


def binance(time_range):
    rows, page = [], 1
    while True:
        d = post(BN_LIST, {"pageNumber": page, "pageSize": 30, "timeRange": time_range, "dataType": "PNL",
                           "favoriteOnly": False, "hideFull": False, "nickname": "", "order": "DESC", "userAsset": 0,
                           "portfolioType": "PUBLIC"})["data"]
        lst = d.get("list") or []
        rows += [{k: x.get(k) for k in BN_KEEP} for x in lst]
        if not lst or page * 30 >= int(d.get("total") or 0):
            break
        page += 1
        time.sleep(0.4)
    df = pd.DataFrame(rows).drop_duplicates("leadPortfolioId")
    return df.assign(timeRange=time_range)


def okx():
    rows, page, pages = [], 1, 1
    while page <= pages:
        with urllib.request.urlopen(f"https://www.okx.com/api/v5/copytrading/public-lead-traders?instType=SWAP"
                                    f"&sortType=pnl&limit=20&page={page}", timeout=30) as r:
            d = json.loads(r.read())["data"][0]
        pages = int(d.get("totalPage") or 1)
        for x in d["ranks"]:
            rows.append({k: x.get(k) for k in ("uniqueCode", "nickName", "pnl", "pnlRatio", "aum", "winRatio",
                                               "leadDays", "copyTraderNum", "accCopyTraderNum", "copyState")}
                        | {"insts": ",".join(x.get("traderInsts") or [])})
        page += 1
        time.sleep(0.3)
    return pd.DataFrame(rows).drop_duplicates("uniqueCode")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", default="binance,okx")
    a = ap.parse_args()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {"binance": lambda: pd.concat([binance("30D"), binance("90D")], ignore_index=True), "okx": okx}
    for venue in a.venues.split(","):
        path = OUT / venue / f"{day}.csv.gz"
        if path.exists():
            continue
        try:
            df = jobs[venue]().assign(snapshot_utc=stamp)
        except Exception as e:                       # a venue that fails today is retried on the next tick
            log(venue, "failed:", e)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, compression="gzip")
        log(venue, len(df), "rows ->", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
