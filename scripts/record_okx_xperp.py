"""Daily recorder of OKX Europe X-Perps (MiFID, 5-year expiry, funding-like payments; M484/M490): public data, no key.

Why: OKX's public API serves only about three months of funding prints, and X-Perps are the one perp route found open to
a French resident (docs/reviews/venue_access_fr_20261110.md). A test of M490 needs more history and measured costs.

Each run, for every X-Perp listed (crypto, stocks and commodities), writes day-partitioned CSV files under OUT:
- instruments/YYYY-MM-DD.json: the day's listing (keeps delisted names visible later);
- funding/YYYY-MM-DD.csv: funding prints by the UTC day of fundingTime (instId, fundingTime, fundingRate, realizedRate,
  method, formulaType);
- mark_1d/, trade_1d/, index_1d/, spot_1d/YYYY-MM-DD.csv: closed UTC daily candles (bar 1Dutc: instId, ts, o, h, l,
  c, vol_quote) of each X-Perp's mark price and last trades, its underlying index (`uly`) and, for crypto, the OKX
  EEA spot pair {base}-USDC (else {base}-EUR) that would hold the hedge leg. vol_quote (quote-currency volume) is
  blank for mark and index candles;
- books/YYYY-MM-DDTHHMM.csv: one snapshot per run of each crypto X-Perp and its spot pair: best bid and ask, and the
  cost in bp from mid of a $1k and a $10k market order on each side (blank when the shown book is too thin).
Existing day files are merged by key, so a re-run is idempotent and a closed day never loses a row.

Paper only: no account, no order. Pace: one request per 0.21 s (OKX allows 10 per 2 s on the funding history).

usage: python scripts/record_okx_xperp.py [--out DIR] [--days N]
       (--days: how far back candle pages go on a first run; default 100)
"""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://eea.okx.com/api/v5/"
PAUSE = 0.21
DAY = 86_400_000
FUND_COLS = ["instId", "fundingTime", "fundingRate", "realizedRate", "method", "formulaType"]
CANDLE_COLS = ["instId", "ts", "o", "h", "l", "c", "vol_quote"]
BOOK_COLS = ["instId", "kind", "ts", "bid", "ask", "buy_1k_bp", "sell_1k_bp", "buy_10k_bp", "sell_10k_bp"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
day_of = lambda t: datetime.fromtimestamp(int(t) / 1000, timezone.utc).strftime("%Y-%m-%d")


def get(path, tries=4):
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(API + path, headers={"User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            time.sleep(PAUSE)
            if d.get("code") == "0":
                return d["data"]
            err = RuntimeError(f"code {d.get('code')} {d.get('msg')}")
            if d.get("code") not in ("50011", "50013"):        # rate limit / busy: retry; anything else: give up
                break
        except (urllib.error.URLError, OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{path}: {err}")


# ---------------------------------------------------------------- pure helpers (tested offline)

def merge_rows(path, rows, cols, keys):
    """Merge rows into one CSV file by key (new rows win), sorted; returns the number of rows added or changed."""
    old = {}
    if path.exists():
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                old[tuple(r[k] for k in keys)] = r
    n = 0
    for r in rows:
        r = {c: "" if r.get(c) is None else str(r.get(c)) for c in cols}
        k = tuple(r[c] for c in keys)
        if old.get(k) != r:
            n += 1
            old[k] = r
    if n:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(old[k] for k in sorted(old))
        tmp.replace(path)
    return n


def by_day(rows, tkey):
    out = {}
    for r in rows:
        out.setdefault(day_of(r[tkey]), []).append(r)
    return out


def closed_candles(raw, inst, now_ms):
    """OKX candle rows [ts, o, h, l, c, ...] to dicts, keeping only days whose 24 h have passed. Trade candles carry
    [.., vol, volCcy, volCcyQuote, confirm]; mark and index candles [.., confirm], so they get no volume."""
    return [{"instId": inst, "ts": int(x[0]), "o": x[1], "h": x[2], "l": x[3], "c": x[4],
             "vol_quote": x[7] if len(x) >= 9 else ""}
            for x in raw if int(x[0]) + DAY <= now_ms]


def walk_cost(levels, usd, mid, side, ct_usd):
    """Cost in bp from mid of taking `usd` of notional through book levels [[px, size, ...], ...]; None if too thin.
    ct_usd(px, size) turns one level's size into USD notional."""
    left, cost = usd, 0.0
    for lv in levels:
        px, sz = float(lv[0]), float(lv[1])
        take = min(left, ct_usd(px, sz))
        cost += take * (px / mid - 1) * (1 if side == "buy" else -1)
        left -= take
        if left <= 1e-9:
            return round(cost / usd * 1e4, 3)
    return None


def spot_pair(base, spot_ids):
    for q in ("USDC", "EUR"):
        if f"{base}-{q}" in spot_ids:
            return f"{base}-{q}"
    return None


# ---------------------------------------------------------------- recording

def last_held(folder, key_col, inst_col="instId"):
    """{instId: newest key} over the folder's day files (to stop paging once the API reaches held rows)."""
    out = {}
    for p in sorted(folder.glob("*.csv"))[-8:]:
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                out[r[inst_col]] = max(out.get(r[inst_col], 0), int(r[key_col]))
    return out


def pages(path, key, stop_at, max_pages):
    rows, after = [], ""
    for _ in range(max_pages):
        d = get(path + (f"&after={after}" if after else ""))
        if not d:
            break
        rows += d
        oldest = int(d[-1][key] if isinstance(d[-1], dict) else d[-1][0])
        if oldest <= stop_at:
            break
        after = oldest
    return rows


def record(out, days_back=100, now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    today = day_of(now_ms)
    stats = {"funding_rows": 0, "candle_rows": 0, "book_rows": 0, "failed": []}
    inst = [i for i in get("public/instruments?instType=FUTURES") if "_XPERP-" in i["instId"]]
    (out / "instruments").mkdir(parents=True, exist_ok=True)
    (out / "instruments" / f"{today}.json").write_text(json.dumps(
        {"fetched_utc": datetime.now(timezone.utc).isoformat(), "instruments": inst}, separators=(",", ":")) + "\n")
    spot_ids = {s["instId"] for s in get("public/instruments?instType=SPOT")}

    held_f = last_held(out / "funding", "fundingTime")
    for i in inst:
        x = i["instId"]
        try:
            rows = pages(f"public/funding-rate-history?instId={x}&limit=100", "fundingTime", held_f.get(x, 0), 20)
            for d, rs in by_day(rows, "fundingTime").items():
                stats["funding_rows"] += merge_rows(out / "funding" / f"{d}.csv", rs, FUND_COLS, ["instId", "fundingTime"])
        except Exception as e:      # noqa: BLE001 - one instrument must not stop the others
            stats["failed"].append(f"{x} funding")
            log(f"{x} funding: {type(e).__name__}: {e}")

    jobs = [("mark_1d", i["instId"], f"market/history-mark-price-candles?instId={i['instId']}") for i in inst]
    jobs += [("trade_1d", i["instId"], f"market/history-candles?instId={i['instId']}") for i in inst]
    jobs += [("index_1d", u, f"market/history-index-candles?instId={u}") for u in sorted({i["uly"] for i in inst})]
    pairs = {}
    for i in inst:
        if str(i.get("instCategory")) == "1":
            sp = spot_pair(i["ctValCcy"], spot_ids)
            if sp:
                pairs[i["instId"]] = sp
    jobs += [("spot_1d", s, f"market/history-candles?instId={s}") for s in sorted(set(pairs.values()))]
    held_c = {k: last_held(out / k, "ts") for k in ("mark_1d", "trade_1d", "index_1d", "spot_1d")}
    for kind, name, path in jobs:
        try:
            stop = held_c[kind].get(name, now_ms - days_back * DAY)
            raw = pages(f"{path}&bar=1Dutc&limit=100", None, stop, max(2, days_back // 100 + 2))
            for d, rs in by_day(closed_candles(raw, name, now_ms), "ts").items():
                stats["candle_rows"] += merge_rows(out / kind / f"{d}.csv", rs, CANDLE_COLS, ["instId", "ts"])
        except Exception as e:      # noqa: BLE001
            stats["failed"].append(f"{name} {kind}")
            log(f"{name} {kind}: {type(e).__name__}: {e}")

    snap = []
    ct = {i["instId"]: float(i["ctVal"]) * float(i.get("ctMult") or 1) for i in inst}
    for x, sp in pairs.items():
        for kind, iid, conv in (("xperp", x, lambda px, sz, c=ct[x]: px * sz * c), ("spot", sp, lambda px, sz: px * sz)):
            try:
                b = get(f"market/books?instId={iid}&sz=100")[0]
                bid, ask = float(b["bids"][0][0]), float(b["asks"][0][0])
                mid = (bid + ask) / 2
                snap.append({"instId": iid, "kind": kind, "ts": b["ts"], "bid": bid, "ask": ask,
                             "buy_1k_bp": walk_cost(b["asks"], 1e3, mid, "buy", conv),
                             "sell_1k_bp": walk_cost(b["bids"], 1e3, mid, "sell", conv),
                             "buy_10k_bp": walk_cost(b["asks"], 1e4, mid, "buy", conv),
                             "sell_10k_bp": walk_cost(b["bids"], 1e4, mid, "sell", conv)})
            except Exception as e:  # noqa: BLE001
                stats["failed"].append(f"{iid} book")
                log(f"{iid} book: {type(e).__name__}: {e}")
    stamp = datetime.fromtimestamp(now_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H%M")
    stats["book_rows"] = merge_rows(out / "books" / f"{stamp}.csv", snap, BOOK_COLS, ["instId", "kind"])
    stats["instruments"] = len(inst)
    stats["spot_pairs"] = len(pairs)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "okx_xperp_rec"))
    ap.add_argument("--days", type=int, default=100)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()
    s = record(out, a.days)
    log(f"{s['instruments']} X-Perps, {s['spot_pairs']} spot pairs; rows written: funding {s['funding_rows']}, "
        f"candles {s['candle_rows']}, books {s['book_rows']}; failed {len(s['failed'])} in {time.time() - t:.0f} s")
    (out / "last_run.json").write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **s}) + "\n")
    return 1 if len(s["failed"]) > 10 else 0


if __name__ == "__main__":
    sys.exit(main())
