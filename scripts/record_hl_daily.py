"""Daily recorder of Hyperliquid perps that match an OKX Europe crypto X-Perp: hourly funding prints and closed UTC
daily candles. Public data, no key, no order. Stdlib only, so it runs on a bare GitHub runner.

Why: a France-reachable cross-venue carry book (OKX Europe X-Perps against Hyperliquid perps, M502) needs both venues
on one data branch, recorded by the same run, so a gate can pin one commit.

Writes day-partitioned CSV files under OUT (merged by key, so a re-run is idempotent and a closed day never loses a row):
- funding/YYYY-MM-DD.csv: coin, time, rate (Hyperliquid's hourly funding prints, by the UTC day of `time`);
- candles_1d/YYYY-MM-DD.csv: coin, ts, o, h, l, c, vol_base (closed 1d candles, by the UTC day the candle opened);
- coins.json: the coins recorded this run and the OKX base each one matches (`k` coins are Hyperliquid's 1000x
  contracts: kPEPE matches PEPE; prices differ by the factor, returns and funding rates do not).
Coins: Hyperliquid's listed perps whose name, or name without the leading `k`, is the base (ctValCcy) of a crypto
X-Perp in the newest OKX listing under --okx (the layout of scripts/record_okx_xperp.py).

usage: python scripts/record_hl_daily.py --okx DIR --out DIR [--days N]
"""
import argparse
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_okx_xperp", ROOT / "scripts" / "record_okx_xperp.py")
okx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(okx)            # reuse merge_rows, by_day, last_held, day_of (not changed)

API = "https://api.hyperliquid.xyz/info"
PAUSE = 1.3                              # Hyperliquid weighs these calls at about 20 of 1200 a minute per IP
DAY = okx.DAY
FUND_COLS = ["coin", "time", "rate"]
CANDLE_COLS = ["coin", "ts", "o", "h", "l", "c", "vol_base"]
log = okx.log


def post(body, tries=5):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(API, json.dumps(body).encode(),
                                         {"Content-Type": "application/json", "User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            time.sleep(PAUSE)
            return d
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{body.get('type')}: {err}")


def match(hl_coins, okx_bases):
    """{hl coin: okx base} for coins equal to an OKX base, or equal to `k` + base (1000x contracts)."""
    out = {}
    for c in sorted(hl_coins):
        if c in okx_bases:
            out[c] = c
        elif c.startswith("k") and c[1:] in okx_bases and c[1:2].isupper():
            out[c] = c[1:]
    return out


def okx_bases(okx_dir):
    files = sorted((Path(okx_dir) / "instruments").glob("*.json"))
    if not files:
        return set()
    ins = json.loads(files[-1].read_text())["instruments"]
    return {i["ctValCcy"] for i in ins if str(i.get("instCategory")) == "1"}


def closed_candles(raw, coin, now_ms):
    return [{"coin": coin, "ts": int(x["t"]), "o": x["o"], "h": x["h"], "l": x["l"], "c": x["c"], "vol_base": x["v"]}
            for x in raw if int(x["t"]) + DAY <= now_ms]


def record(out, okx_dir, days_back=100, now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    stats = {"funding_rows": 0, "candle_rows": 0, "failed": []}
    meta = post({"type": "meta"})
    listed = {u["name"] for u in meta["universe"] if not u.get("isDelisted")}
    coins = match(listed, okx_bases(okx_dir))
    out.mkdir(parents=True, exist_ok=True)
    (out / "coins.json").write_text(json.dumps({"fetched_utc": datetime.now(timezone.utc).isoformat(),
                                                "coins": coins}, separators=(",", ":")) + "\n")
    held_f = okx.last_held(out / "funding", "time", "coin")
    held_c = okx.last_held(out / "candles_1d", "ts", "coin")
    for c in coins:
        try:
            s, rows = held_f.get(c, now_ms - days_back * DAY) + 1, []
            while s < now_ms:
                d = post({"type": "fundingHistory", "coin": c, "startTime": s, "endTime": now_ms})
                if not d:
                    break
                rows += [{"coin": c, "time": int(x["time"]), "rate": x["fundingRate"]} for x in d]
                last = int(d[-1]["time"])
                if last < s or len(d) < 500:
                    break
                s = last + 1
            for day, rs in okx.by_day(rows, "time").items():
                stats["funding_rows"] += okx.merge_rows(out / "funding" / f"{day}.csv", rs, FUND_COLS, ["coin", "time"])
        except Exception as e:      # noqa: BLE001 - one coin must not stop the others
            stats["failed"].append(f"{c} funding")
            log(f"{c} funding: {type(e).__name__}: {e}")
        try:
            start = held_c.get(c, now_ms - days_back * DAY)
            raw = post({"type": "candleSnapshot", "req": {"coin": c, "interval": "1d", "startTime": start,
                                                          "endTime": now_ms}})
            for day, rs in okx.by_day(closed_candles(raw or [], c, now_ms), "ts").items():
                stats["candle_rows"] += okx.merge_rows(out / "candles_1d" / f"{day}.csv", rs, CANDLE_COLS,
                                                       ["coin", "ts"])
        except Exception as e:      # noqa: BLE001
            stats["failed"].append(f"{c} candles")
            log(f"{c} candles: {type(e).__name__}: {e}")
    stats["coins"] = len(coins)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--okx", required=True, help="folder written by scripts/record_okx_xperp.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=100)
    a = ap.parse_args()
    t = time.time()
    s = record(Path(a.out), Path(a.okx), a.days)
    log(f"{s['coins']} Hyperliquid coins; rows written: funding {s['funding_rows']}, candles {s['candle_rows']}; "
        f"failed {len(s['failed'])} in {time.time() - t:.0f} s")
    (Path(a.out) / "last_run.json").write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **s}) + "\n")
    return 1 if len(s["failed"]) > 10 else 0


if __name__ == "__main__":
    sys.exit(main())
