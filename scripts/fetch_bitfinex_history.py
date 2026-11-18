"""Bitfinex USDt-margined perpetuals (the `F0` pairs): hourly trade candles and the funding rate of every 8 h event.

Why: the carry plan's "weeks" replication (docs/reviews/plan_20261117.md section 9) needs a venue never read for carry.
Bitfinex is reachable from here and keeps derivatives history; Bybit and BitMEX refuse this container.

**Funding.** Bitfinex publishes no settled-funding history. Its derivatives status history
(`/v2/status/deriv/{key}/hist`, one row about every minute, at most 5,000 rows a request) carries, per row:
- `NEXT_FUNDING_EVT_MTS` (index 7): the end of the current 8 h period;
- `NEXT_FUNDING_ACCRUED` (8): the premium accrued so far in that period;
- `CURRENT_FUNDING` (11): "funding applied in the current 8 h period";
- `CLAMP_MIN` (21): the band of the average spread that needs no payment; `CLAMP_MAX` (22): the payment cap.
Checked on 2026-11-01..04 rows (after any window this lab reads): the rate shown in the period after event E equals
the period's accrual at E beyond the +-CLAMP_MIN band (BTC 6.10 bp -> 1.10; DOGE -6.70 -> -1.71), and 0 inside it.

The rows are reduced as they stream, one row per period (`funding/<BASE>.parquet`):
- `t`: the period's event time E (ms), where the rate is booked. The rate shown during (E - 8 h, E] is booked at E,
  never earlier, so a rate is never used before the exchange published it, whichever end of the period it is paid at;
- `rate`: `CURRENT_FUNDING` on the period's last row (a long pays a positive rate);
- `rows`, `first_ms`, `last_ms`, `rate_changes` (rows whose rate differs from the previous row's within the period),
  `acc_last`, `clamp_min`, `clamp_max`, `mark_last`, `deriv_last`, `spot_last`, `oi_last`.
A period with no row has no line: it is a gap, not a zero.

**Candles.** `/v2/candles/trade:1h:{key}/hist`, rows `[MTS, OPEN, CLOSE, HIGH, LOW, VOLUME]` (volume in the base coin);
an hour without a trade has no candle. Saved as `candles_1h/<BASE>.parquet` with `t, open, high, low, close, volume`.

**Resume.** Each pair's status pages are reduced into `progress/<BASE>.status.csv` (appended per page with the last
row's time), so a stopped run restarts from the next minute. A pair is finished when its `receipts/<BASE>.json`
exists; it records the request window, row and page counts and the sha256 of both parquet files. Only a pair with a
receipt is skipped.

**Pace.** Bitfinex allows 90 status requests a minute; this stays near 60 (`--pace` seconds between requests) and
sleeps 60 s on a rate-limit reply. Public endpoints only: no key, no account, no order. Data collection only.

usage: python scripts/fetch_bitfinex_history.py pairs [--out DIR]
       python scripts/fetch_bitfinex_history.py fetch --start 2021-01-01 --end 2026-10-01 [--only BTC,ETH] [--out DIR]
"""
import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "bitfinex_hist"
API = "https://api-pub.bitfinex.com/v2"
HEADERS = {"User-Agent": "curl/8.5.0", "Accept": "application/json"}   # the default Python agent is refused (403)
NOT_CRYPTO = ("IX", "EUR", "GBP", "JPY", "CHF", "XAU", "XAG", "XPD", "XPT", "UKOIL", "VIV", "TEST")
PAGE = 5000
CANDLE_PAGE = 10000
STATUS_COLS = ["evt", "rows", "first_ms", "last_ms", "rate_first", "rate_last", "rate_changes", "acc_last", "clamp_min",
               "clamp_max", "mark_last", "deriv_last", "spot_last", "oi_last"]


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def get(url, tries=6, pace=None):
    """JSON from a public endpoint; waits 60 s on a rate-limit reply, retries other failures with backoff."""
    delay = 5.0
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
                body = json.loads(r.read())
            if isinstance(body, list) and body[:1] == ["error"]:
                raise urllib.error.HTTPError(url, 429 if "ratelimit" in str(body).lower() else 500, str(body), None,
                                             None)
            return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504, 520, 522, 524) and i < tries - 1:
                time.sleep(60.0 if e.code == 429 else delay)
                delay *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            if i == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
        finally:
            if pace:
                time.sleep(pace)
    raise RuntimeError(url)


def is_crypto(pair):
    base = pair.split(":")[0][:-2]
    return pair.endswith(":USTF0") and not any(x in base for x in NOT_CRYPTO)


def reduce_page(rows):
    """One aggregate per 8 h period present in a page of status rows (ascending by time)."""
    out = {}
    prev_rate = None
    for r in rows:
        if len(r) < 23 or r[0] is None or r[7] is None:
            continue
        evt, rate = int(r[7]), (float(r[11]) if r[11] is not None else float("nan"))
        a = out.get(evt)
        if a is None:
            a = out[evt] = {"evt": evt, "rows": 0, "first_ms": int(r[0]), "rate_first": rate, "rate_changes": 0}
            prev_rate = None
        a["rows"] += 1
        if prev_rate is not None and rate != prev_rate and not (rate != rate and prev_rate != prev_rate):
            a["rate_changes"] += 1
        prev_rate = rate
        a.update(last_ms=int(r[0]), rate_last=rate, acc_last=r[8], clamp_min=r[21], clamp_max=r[22], mark_last=r[14],
                 deriv_last=r[2], spot_last=r[3], oi_last=r[17])
    return [out[k] for k in sorted(out)]


def combine(parts):
    """Merge per-page aggregates of the same period (a period split across two pages) into one row per period."""
    df = pd.DataFrame(parts, columns=STATUS_COLS)
    if df.empty:
        return pd.DataFrame(columns=["t", "rate", "rows", "first_ms", "last_ms", "rate_changes", "acc_last", "clamp_min",
                                     "clamp_max", "mark_last", "deriv_last", "spot_last", "oi_last"])
    df = df.sort_values(["evt", "first_ms"], kind="mergesort")
    rows = []
    for evt, g in df.groupby("evt", sort=True):
        first, last = g.iloc[0], g.iloc[-1]
        changes = int(g.rate_changes.sum())
        # a change at the seam between two pages of the same period
        changes += int(sum(a != b and not (a != a and b != b) for a, b in zip(g.rate_last.iloc[:-1], g.rate_first.iloc[1:])))
        rows.append({"t": int(evt), "rate": float(last.rate_last), "rows": int(g.rows.sum()),
                     "first_ms": int(first.first_ms), "last_ms": int(last.last_ms), "rate_changes": changes,
                     **{k: last[k] for k in ("acc_last", "clamp_min", "clamp_max", "mark_last", "deriv_last", "spot_last",
                                             "oi_last")}})
    return pd.DataFrame(rows)


def candles_frame(rows):
    df = pd.DataFrame(rows, columns=["t", "open", "close", "high", "low", "volume"])
    df = df.astype({"t": "int64"}).drop_duplicates("t", keep="last").sort_values("t").reset_index(drop=True)
    return df[["t", "open", "high", "low", "close", "volume"]]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch_status(key, base, start, end, out, pace, log):
    prog = out / "progress" / f"{base}.status.csv"
    prog.parent.mkdir(parents=True, exist_ok=True)
    since, pages = start, 0
    if prog.exists():
        with prog.open() as f:
            lines = list(csv.DictReader(f))
        if lines:
            since = int(lines[-1]["page_last_ms"]) + 1
            pages = len({x["page"] for x in lines})
    while since < end:
        rows = get(f"{API}/status/deriv/{key}/hist?start={since}&end={end - 1}&limit={PAGE}&sort=1", pace=pace)
        if not rows:
            break
        rows = [r for r in rows if r and r[0] is not None and since <= r[0] < end]
        if not rows:
            break
        pages += 1
        new = not prog.exists()
        with prog.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["page", "page_last_ms", *STATUS_COLS], lineterminator="\n")
            if new:
                w.writeheader()
            for a in reduce_page(rows):
                w.writerow({"page": pages, "page_last_ms": int(rows[-1][0]), **{k: a.get(k) for k in STATUS_COLS}})
        since = int(rows[-1][0]) + 1
        if pages % 50 == 0:
            log(f"  {base} status page {pages} at {pd.Timestamp(since, unit='ms')}")
        if len(rows) < PAGE:
            break
    if not prog.exists():
        return combine([]), 0
    parts = pd.read_csv(prog)
    return combine(parts[STATUS_COLS].to_dict("records")), pages


def fetch_candles(key, start, end, pace):
    rows, since = [], start
    while since < end:
        page = get(f"{API}/candles/trade:1h:{key}/hist?start={since}&end={end - 1}&limit={CANDLE_PAGE}&sort=1",
                   pace=pace)
        page = [r for r in page if r and since <= r[0] < end]
        if not page:
            break
        rows += page
        since = int(page[-1][0]) + 1
        if len(page) < CANDLE_PAGE:
            break
    return candles_frame(rows)


def pairs(out):
    conf = get(f"{API}/conf/pub:list:pair:futures")[0]
    keep = sorted(p for p in conf if is_crypto(p))
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"pair": keep, "base": [p.split(":")[0][:-2] for p in keep]}).to_csv(out / "pairs.csv", index=False)
    (out / "pairs_raw.json").write_text(json.dumps(conf))
    print(f"{len(conf)} futures pairs, {len(keep)} crypto USDt pairs -> {out / 'pairs.csv'}")


def fetch(start, end, only, out, pace, log=print, pairs_file=None):
    pl = pd.read_csv(pairs_file or out / "pairs.csv")
    if only:
        pl = pl[pl.base.isin(only)]
    (out / "funding").mkdir(parents=True, exist_ok=True)
    (out / "candles_1h").mkdir(parents=True, exist_ok=True)
    (out / "receipts").mkdir(parents=True, exist_ok=True)
    t0, t1 = ms(start), ms(end)
    for i, (pair, base) in enumerate(zip(pl.pair, pl.base), 1):
        rec = out / "receipts" / f"{base}.json"
        if rec.exists():
            continue
        key = f"t{pair}"
        fund, pages = fetch_status(key, base, t0, t1, out, pace, log)
        cand = fetch_candles(key, t0, t1, pace * 2)
        fp, cp = out / "funding" / f"{base}.parquet", out / "candles_1h" / f"{base}.parquet"
        fund.to_parquet(fp, index=False)
        cand.to_parquet(cp, index=False)
        receipt = {"pair": pair, "base": base, "start": start, "end_exclusive": end, "status_pages": pages,
                   "periods": len(fund), "candles": len(cand),
                   "first_period": int(fund.t.min()) if len(fund) else None,
                   "last_period": int(fund.t.max()) if len(fund) else None,
                   "funding_sha256": sha256(fp), "candles_sha256": sha256(cp),
                   "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        rec.write_text(json.dumps(receipt, indent=1))
        log(f"{time.strftime('%H:%M:%S')} {i}/{len(pl)} {base}: {len(fund)} periods, {len(cand)} candles, "
            f"{pages} status pages")
    log("done")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("pairs", "fetch"))
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default="2026-10-01", help="exclusive UTC day")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--pace", type=float, default=0.9)
    a = ap.parse_args(argv)
    if a.cmd == "pairs":
        return pairs(a.out)
    return fetch(a.start, a.end, [x for x in a.only.split(",") if x], a.out, a.pace,
                 log=lambda *x: print(*x, flush=True))


if __name__ == "__main__":
    sys.exit(main() or 0)
