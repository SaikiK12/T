"""Daily recorder for a Hyperliquid spot-against-perp carry (M503): the USDC spot pairs of HYPE and of the Unit-bridged
coins whose perp is listed under the same name, with the hourly funding of those perps and closed UTC daily candles
of both legs. Public data, no key, no order. Stdlib only, so it runs on a bare GitHub runner.

Pairs (rule, applied to each run's spotMeta and meta): a spot pair quoted in USDC whose base token is HYPE (the venue's
own token) or has a fullName starting with "Unit " (Unit's bridged coins: UBTC is Unit Bitcoin) and a name that,
without its leading U, is a listed perp (UBTC -> BTC). Hyperliquid spot names are first come, first served, so a
plain name match could pair a different asset; the Unit name and HYPE avoid that.

Writes under OUT (day files merged by key, so a re-run is idempotent and a closed day never loses a row):
- pairs.json: {spot pair (e.g. "@142"): {"token": "UBTC", "perp": "BTC"}} from this run;
- funding/YYYY-MM-DD.csv: coin, time, rate (hourly prints of the pairs' perps, by the UTC day of `time`);
- perp_1d/ and spot_1d/YYYY-MM-DD.csv: coin, ts, o, h, l, c, vol_base (closed 1d candles, by the day they opened;
  spot rows carry the pair name, e.g. "@142").
A coin with no held row starts at --since (default 2024-11-01); later runs start after the newest held row.

usage: python scripts/record_hl_spot.py --out DIR [--since YYYY-MM-DD]
"""
import argparse
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_hl_daily", ROOT / "scripts" / "record_hl_daily.py")
hl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hl)             # reuse post, closed_candles and the OKX recorder's file helpers (not changed)
okx = hl.okx
DAY = hl.DAY
FUND_COLS, CANDLE_COLS = hl.FUND_COLS, hl.CANDLE_COLS
log = hl.log


def ms_of(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def pairs(spot_meta, perp_names):
    """{spot pair: {"token", "perp"}} by the module rule; the first pair of a perp (lowest index) wins."""
    toks = {t["index"]: t for t in spot_meta["tokens"]}
    out, taken = {}, set()
    for u in sorted(spot_meta["universe"], key=lambda u: u["index"]):
        b, q = toks.get(u["tokens"][0]), toks.get(u["tokens"][1])
        if b is None or q is None or q["name"] != "USDC":
            continue
        name, full = b["name"], b.get("fullName") or ""
        if name == "HYPE":
            perp = "HYPE"
        elif full.startswith("Unit ") and name.startswith("U"):
            perp = name[1:]
        else:
            continue
        if perp in perp_names and perp not in taken:
            out[u["name"]] = {"token": name, "perp": perp}
            taken.add(perp)
    return out


def fetch_funding(coin, start, now_ms):
    rows, s = [], start
    while s < now_ms:
        d = hl.post({"type": "fundingHistory", "coin": coin, "startTime": s, "endTime": now_ms})
        if not d:
            break
        rows += [{"coin": coin, "time": int(x["time"]), "rate": x["fundingRate"]} for x in d]
        last = int(d[-1]["time"])
        if last < s or len(d) < 500:
            break
        s = last + 1
    return rows


def record(out, since="2024-11-01", now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    first = ms_of(since)
    stats = {"funding_rows": 0, "perp_rows": 0, "spot_rows": 0, "failed": []}
    meta = hl.post({"type": "meta"})
    perps = {u["name"] for u in meta["universe"] if not u.get("isDelisted")}
    pr = pairs(hl.post({"type": "spotMeta"}), perps)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pairs.json").write_text(json.dumps({"fetched_utc": datetime.now(timezone.utc).isoformat(), "pairs": pr},
                                               separators=(",", ":")) + "\n")
    held_f = okx.last_held(out / "funding", "time", "coin")
    held_p = okx.last_held(out / "perp_1d", "ts", "coin")
    held_s = okx.last_held(out / "spot_1d", "ts", "coin")
    for pair, v in pr.items():
        coin = v["perp"]
        try:
            rows = fetch_funding(coin, held_f.get(coin, first - 1) + 1, now_ms)
            for day, rs in okx.by_day(rows, "time").items():
                stats["funding_rows"] += okx.merge_rows(out / "funding" / f"{day}.csv", rs, FUND_COLS, ["coin", "time"])
        except Exception as e:      # noqa: BLE001 - one coin must not stop the others
            stats["failed"].append(f"{coin} funding")
            log(f"{coin} funding: {type(e).__name__}: {e}")
        for name, folder, held, key in ((coin, "perp_1d", held_p, "perp_rows"), (pair, "spot_1d", held_s, "spot_rows")):
            try:
                raw = hl.post({"type": "candleSnapshot", "req": {"coin": name, "interval": "1d",
                                                                 "startTime": held.get(name, first),
                                                                 "endTime": now_ms}})
                for day, rs in okx.by_day(hl.closed_candles(raw or [], name, now_ms), "ts").items():
                    stats[key] += okx.merge_rows(out / folder / f"{day}.csv", rs, CANDLE_COLS, ["coin", "ts"])
            except Exception as e:  # noqa: BLE001
                stats["failed"].append(f"{name} {folder}")
                log(f"{name} {folder}: {type(e).__name__}: {e}")
    stats["pairs"] = len(pr)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--since", default="2024-11-01", help="first day fetched for a coin with no held row")
    a = ap.parse_args()
    t = time.time()
    s = record(Path(a.out), a.since)
    log(f"{s['pairs']} Hyperliquid spot/perp pairs; rows written: funding {s['funding_rows']}, perp candles "
        f"{s['perp_rows']}, spot candles {s['spot_rows']}; failed {len(s['failed'])} in {time.time() - t:.0f} s")
    (Path(a.out) / "last_run.json").write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **s}) + "\n")
    return 1 if len(s["failed"]) > 5 else 0


if __name__ == "__main__":
    sys.exit(main())
