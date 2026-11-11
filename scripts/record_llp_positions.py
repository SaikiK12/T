"""Hourly recorder of LLP's inventory on Lighter: the positions of Lighter's protocol liquidity pool (LLP, the
venue's market-making and liquidation pool) and each perp market's context. Public data, no key, no order. Stdlib only.

Why: LLP is to Lighter what HLP is to Hyperliquid; its net position in a market is roughly the other side of the
crowd's. Lighter's public `account` endpoint shows the pool's positions now but keeps no history, so any rule on
that inventory can only be read on snapshots recorded from now on, frozen before any is read.

Writes under OUT/llp (day-partitioned CSV, merged by key, so a re-run is idempotent):
- positions/YYYY-MM-DD.csv: ts (the run's time, ms), market_id, symbol, sign (1 long, -1 short), position (size),
  position_value, avg_entry_price, unrealized_pnl, realized_pnl, total_funding_paid_out, allocated_margin;
- accounts/YYYY-MM-DD.csv: ts, total_asset_value, collateral, available_balance, total_shares, positions;
- markets/YYYY-MM-DD.csv: ts, market_id, symbol, status, mark_price, index_price, last_trade_price, open_interest,
  open_interest_usd, daily_quote_token_volume, taker_fee, maker_fee, for every perp market listed.

usage: python scripts/record_llp_positions.py --out DIR
"""
import argparse
import importlib.util
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_xyz_books", ROOT / "scripts" / "record_xyz_books.py")
xb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xb)             # reuse the OKX recorder's file helpers and the log
okx = xb.okx
log = xb.log

API = "https://mainnet.zklighter.elliot.ai/api/v1"
LLP_INDEX = 281474976710654              # as scripts/record_dex_vaults.py
POS_COLS = ["ts", "market_id", "symbol", "sign", "position", "position_value", "avg_entry_price", "unrealized_pnl",
            "realized_pnl", "total_funding_paid_out", "allocated_margin"]
ACC_COLS = ["ts", "total_asset_value", "collateral", "available_balance", "total_shares", "positions"]
MKT_COLS = ["ts", "market_id", "symbol", "status", "mark_price", "index_price", "last_trade_price", "open_interest",
            "open_interest_usd", "daily_quote_token_volume", "taker_fee", "maker_fee"]


def get(path, tries=4):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:      # noqa: BLE001 - retried, then raised
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"lighter {path}: {err}")


def pool_rows(acct, ts):
    """Position rows (non-zero positions only) and one account row from an `account` response's account."""
    pos = []
    for p in acct.get("positions", []):
        if float(p.get("position") or 0) == 0:
            continue
        pos.append({"ts": ts, "market_id": p["market_id"], "symbol": p.get("symbol"), "sign": p.get("sign"),
                    **{k: p.get(k) for k in POS_COLS[4:]}})
    info = acct.get("pool_info") or {}
    acc = {"ts": ts, "total_asset_value": acct.get("total_asset_value"), "collateral": acct.get("collateral"),
           "available_balance": acct.get("available_balance"), "total_shares": info.get("total_shares"),
           "positions": len(pos)}
    return pos, acc


def market_rows(details, ts):
    return [{"ts": ts, **{k: m.get(k) for k in MKT_COLS[1:]}} for m in details.get("order_book_details", [])]


def record(out, now_ms=None):
    """One snapshot. Returns (positions written, markets written)."""
    root = Path(out) / "llp"
    ts = now_ms or int(time.time() * 1000)
    accts = get(f"account?by=index&value={LLP_INDEX}").get("accounts") or []
    if not accts:
        raise RuntimeError("lighter account: no LLP account in the response")
    pos, acc = pool_rows(accts[0], ts)
    mk = market_rows(get("orderBookDetails"), ts)
    for d, rs in okx.by_day(pos, "ts").items():
        okx.merge_rows(root / "positions" / f"{d}.csv", rs, POS_COLS, ["ts", "market_id"])
    for d, rs in okx.by_day([acc], "ts").items():
        okx.merge_rows(root / "accounts" / f"{d}.csv", rs, ACC_COLS, ["ts"])
    for d, rs in okx.by_day(mk, "ts").items():
        okx.merge_rows(root / "markets" / f"{d}.csv", rs, MKT_COLS, ["ts", "market_id"])
    return len(pos), len(mk)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n, m = record(a.out)
    log(f"LLP positions {n}, markets {m}")
    if m == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
