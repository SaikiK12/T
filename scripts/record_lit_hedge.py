"""Recorder for Lighter's LIT markets (R447): the LIT perp's hourly funding and daily candles, and the LIT/USDC spot
pair's daily candles. A real deposit in Lighter's LLP pool needs 1 LIT staked per 10 USDC; these are the series that
price a stake hedged with a short LIT perp. Public data, no key, no order. Stdlib only, so it runs on a bare runner.

Writes under OUT (each run re-reads the whole history and merges by time, so a re-run is idempotent):
- perp_funding/YYYY-MM-DD.csv: ts (ms), rate_pct, value, direction, rate. The API gives an unsigned percent `rate` and
  a `direction`; `rate` here is +rate_pct/100 when direction is 'long' (longs pay) and -rate_pct/100 otherwise, as in
  scripts/fetch_venue_history.py.
- perp_candles_1d/YYYY-MM-DD.csv and spot_candles_1d/YYYY-MM-DD.csv: ts (ms, bar open), open, high, low, close, volume,
  quote_volume. Finished bars only.
- meta.json, last_run.json.

usage: python scripts/record_lit_hedge.py --out DIR
"""
import argparse
import importlib.util
import json
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_dex_vaults", ROOT / "scripts" / "record_dex_vaults.py")
dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dv)            # reuse its Lighter GET and the OKX recorder's file helpers (not changed)
okx, log = dv.okx, dv.log

PERP, SPOT = 120, 2049                  # Lighter market ids: LIT perp, LIT/USDC spot
START_MS = 1_767_225_600_000            # 2026-01-01 00:00 UTC, before the LIT perp's first daily bar
DAY, HOUR = 86_400_000, 3_600_000
FUND_COLS = ["ts", "rate_pct", "value", "direction", "rate"]
CANDLE_COLS = ["ts", "open", "high", "low", "close", "volume", "quote_volume"]


def api(get, path, **q):
    return get(f"{dv.LIGHTER}/{path}?{urllib.parse.urlencode(q)}")


def funding_rows(get, start, now, step=700 * HOUR, pause=1.0):
    rows = []
    for a in range(start, now, step):
        b = min(a + step, now)
        for r in api(get, "fundings", market_id=PERP, resolution="1h", start_timestamp=a // 1000,
                     end_timestamp=b // 1000, count_back=0).get("fundings") or []:
            pct = float(r["rate"])
            rows.append({"ts": int(r["timestamp"]) * 1000, "rate_pct": r["rate"], "value": r["value"],
                         "direction": r["direction"], "rate": (pct if r["direction"] == "long" else -pct) / 100})
        time.sleep(pause)
    return rows


def candle_rows(get, market, start, now):
    rows = []
    for r in api(get, "candles", market_id=market, resolution="1d", start_timestamp=start, end_timestamp=now,
                 count_back=0).get("c") or []:
        if int(r["t"]) + DAY <= now:
            rows.append({"ts": int(r["t"]), "open": r["o"], "high": r["h"], "low": r["l"], "close": r["c"],
                         "volume": r.get("v", ""), "quote_volume": r.get("V", "")})
    return rows


def record(out, now_ms=None, get=None, pause=1.0):
    now_ms = now_ms or int(time.time() * 1000)
    get = get or dv.get
    stats = {"funding": 0, "perp_candles": 0, "spot_candles": 0, "failed": []}
    out.mkdir(parents=True, exist_ok=True)
    jobs = (("funding", "perp_funding", FUND_COLS, lambda: funding_rows(get, START_MS, now_ms, pause=pause)),
            ("perp_candles", "perp_candles_1d", CANDLE_COLS, lambda: candle_rows(get, PERP, START_MS, now_ms)),
            ("spot_candles", "spot_candles_1d", CANDLE_COLS, lambda: candle_rows(get, SPOT, START_MS, now_ms)))
    for key, folder, cols, fetch in jobs:
        try:
            for day, rs in okx.by_day(fetch(), "ts").items():
                stats[key] += okx.merge_rows(out / folder / f"{day}.csv", rs, cols, ["ts"])
        except Exception as e:      # noqa: BLE001 - one series must not stop the others
            stats["failed"].append(key)
            log(f"{key}: {type(e).__name__}: {e}")
    (out / "meta.json").write_text(json.dumps({"fetched_ms": now_ms, "perp_market_id": PERP, "spot_market_id": SPOT},
                                              separators=(",", ":")) + "\n")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t = time.time()
    s = record(Path(a.out))
    log(f"lit: funding rows changed {s['funding']}, perp candles {s['perp_candles']}, spot candles "
        f"{s['spot_candles']}; failed {s['failed']} in {time.time() - t:.0f} s")
    (Path(a.out) / "last_run.json").write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **s}) + "\n")
    return 1 if s["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
