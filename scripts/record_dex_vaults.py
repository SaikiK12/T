"""Recorder for two public liquidity vaults on perp DEXes that do not exclude France (M505): Hyperliquid's HLP vault and
Lighter's LLP pool. Public data, no key, no order, no deposit. Stdlib only, so it runs on a bare GitHub runner.

Writes under OUT:
- hlp/snap/<fetch ms>.csv: window, ts, account_value, pnl. One file per run with the vault's `week`, `month` and
  `allTime` portfolio windows as served (vaultDetails). Each window's pnl starts at 0 at that window's first point,
  so a return is only ever computed between two points of the same window in the same file.
- hlp/meta.json: name, leader, isClosed, allowDeposits and the fetch time of the last run.
- llp/share_prices/YYYY-MM-DD.csv: ts (ms), share_price; llp/daily_returns/YYYY-MM-DD.csv: ts (ms), daily_return.
  Both from the LLP account's pool_info, merged by ts (a re-run is idempotent).
- llp/meta.json: name, status, operator_fee, total_shares, operator_shares and the fetch time.
- last_run.json.

usage: python scripts/record_dex_vaults.py --out DIR
"""
import argparse
import csv
import importlib.util
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_hl_daily", ROOT / "scripts" / "record_hl_daily.py")
hl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hl)             # reuse post (Hyperliquid) and the OKX recorder's file helpers (not changed)
okx = hl.okx
log = hl.log

HLP = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
LLP_INDEX = 281474976710654
LIGHTER = "https://mainnet.zklighter.elliot.ai/api/v1"
HLP_WINDOWS = ("week", "month", "allTime")
SNAP_COLS = ["window", "ts", "account_value", "pnl"]
SP_COLS, DR_COLS = ["ts", "share_price"], ["ts", "daily_return"]


def get(url, tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paper-research-recorder"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:      # noqa: BLE001 - retried, then raised
            if k == tries - 1:
                raise
            log(f"GET retry {k + 1}: {type(e).__name__}")
            time.sleep(2 * (k + 1))


def hlp_rows(details):
    """Rows of the kept portfolio windows: window, ts, account_value, pnl."""
    rows = []
    for win, body in details.get("portfolio") or []:
        if win not in HLP_WINDOWS:
            continue
        av = {int(t): v for t, v in body.get("accountValueHistory") or []}
        for t, p in body.get("pnlHistory") or []:
            if int(t) in av:
                rows.append({"window": win, "ts": int(t), "account_value": av[int(t)], "pnl": p})
    return rows


def ms(t):
    t = int(t)
    return t if t > 10 ** 11 else t * 1000


def record(out, now_ms=None, hl_post=None, lighter_get=None):
    now_ms = now_ms or int(time.time() * 1000)
    hl_post = hl_post or hl.post
    lighter_get = lighter_get or get
    stats = {"hlp_points": 0, "llp_share_prices": 0, "llp_daily_returns": 0, "failed": []}
    out.mkdir(parents=True, exist_ok=True)
    try:
        d = hl_post({"type": "vaultDetails", "vaultAddress": HLP})
        rows = hlp_rows(d)
        snap = out / "hlp" / "snap" / f"{now_ms}.csv"
        snap.parent.mkdir(parents=True, exist_ok=True)
        with open(snap, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=SNAP_COLS, lineterminator="\n")
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: (r["window"], r["ts"])))
        stats["hlp_points"] = len(rows)
        (out / "hlp" / "meta.json").write_text(json.dumps(
            {"fetched_ms": now_ms, **{k: d.get(k) for k in ("name", "vaultAddress", "leader", "isClosed",
                                                           "allowDeposits")}}, separators=(",", ":")) + "\n")
    except Exception as e:          # noqa: BLE001 - one vault must not stop the other
        stats["failed"].append("hlp")
        log(f"hlp: {type(e).__name__}: {e}")
    try:
        acc = lighter_get(f"{LIGHTER}/account?by=index&value={LLP_INDEX}")["accounts"][0]
        pi = acc["pool_info"]
        sp = [{"ts": ms(x["timestamp"]), "share_price": x["share_price"]} for x in pi.get("share_prices") or []]
        dr = [{"ts": ms(x["timestamp"]), "daily_return": x["daily_return"]} for x in pi.get("daily_returns") or []]
        for day, rs in okx.by_day(sp, "ts").items():
            stats["llp_share_prices"] += okx.merge_rows(out / "llp" / "share_prices" / f"{day}.csv", rs, SP_COLS,
                                                        ["ts"])
        for day, rs in okx.by_day(dr, "ts").items():
            stats["llp_daily_returns"] += okx.merge_rows(out / "llp" / "daily_returns" / f"{day}.csv", rs, DR_COLS,
                                                         ["ts"])
        (out / "llp" / "meta.json").write_text(json.dumps(
            {"fetched_ms": now_ms, "name": acc.get("name"),
             **{k: pi.get(k) for k in ("status", "operator_fee", "total_shares", "operator_shares")}},
            separators=(",", ":")) + "\n")
    except Exception as e:          # noqa: BLE001
        stats["failed"].append("llp")
        log(f"llp: {type(e).__name__}: {e}")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t = time.time()
    s = record(Path(a.out))
    log(f"vaults: HLP points {s['hlp_points']}, LLP share prices changed {s['llp_share_prices']}, daily returns "
        f"changed {s['llp_daily_returns']}; failed {s['failed']} in {time.time() - t:.0f} s")
    (Path(a.out) / "last_run.json").write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **s}) + "\n")
    return 1 if s["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
