"""Hourly recorder of HLP's inventory on Hyperliquid: the positions of HLP's child vaults (the protocol's market-making
and liquidation vaults) and each perp's market context. Public data, no key, no order. Stdlib only.

Why: HLP is the venue's market maker; its net position in a coin is the other side of the crowd's net flow against
it. Hyperliquid keeps no history of a vault's positions, so a rule on that inventory (method M510) can only be read
on snapshots recorded from now on, frozen before any is read.

Writes under OUT/hlp (day-partitioned CSV, merged by key, so a re-run is idempotent):
- positions/YYYY-MM-DD.csv: ts (the response's time, ms), vault, coin, szi (signed size), entry_px, position_value,
  unrealized_pnl, margin_used, for every child vault holding positions;
- accounts/YYYY-MM-DD.csv: ts, vault, account_value, total_ntl_pos, total_margin_used;
- ctx/YYYY-MM-DD.csv: ts (the run's time), coin, mark, oracle, mid, funding, premium, open_interest,
  day_ntl_vlm, for every listed perp on Hyperliquid's main dex.
- children.json: HLP's child vault addresses as listed this run.

usage: python scripts/record_hlp_positions.py --out DIR
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_xyz_books", ROOT / "scripts" / "record_xyz_books.py")
xb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xb)             # reuse post (Hyperliquid info API) and the OKX recorder's file helpers
okx = xb.okx
log = xb.log

HLP = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
POS_COLS = ["ts", "vault", "coin", "szi", "entry_px", "position_value", "unrealized_pnl", "margin_used"]
ACC_COLS = ["ts", "vault", "account_value", "total_ntl_pos", "total_margin_used"]
CTX_COLS = ["ts", "coin", "mark", "oracle", "mid", "funding", "premium", "open_interest", "day_ntl_vlm"]


def children(details):
    rel = details.get("relationship") or {}
    return list((rel.get("data") or {}).get("childAddresses") or [])


def vault_rows(vault, state):
    """Position and account rows from one clearinghouseState response."""
    ts = int(state["time"])
    pos = []
    for p in state.get("assetPositions", []):
        q = p["position"]
        pos.append({"ts": ts, "vault": vault, "coin": q["coin"], "szi": q["szi"], "entry_px": q.get("entryPx"),
                    "position_value": q.get("positionValue"), "unrealized_pnl": q.get("unrealizedPnl"),
                    "margin_used": q.get("marginUsed")})
    m = state.get("marginSummary") or {}
    acc = {"ts": ts, "vault": vault, "account_value": m.get("accountValue"), "total_ntl_pos": m.get("totalNtlPos"),
           "total_margin_used": m.get("totalMarginUsed")}
    return pos, acc


def ctx_rows(meta, ctxs, ts):
    out = []
    for u, c in zip(meta["universe"], ctxs):
        if u.get("isDelisted"):
            continue
        out.append({"ts": ts, "coin": u["name"], "mark": c.get("markPx"), "oracle": c.get("oraclePx"),
                    "mid": c.get("midPx"), "funding": c.get("funding"), "premium": c.get("premium"),
                    "open_interest": c.get("openInterest"), "day_ntl_vlm": c.get("dayNtlVlm")})
    return out


def record(out, now_ms=None):
    """One snapshot. Returns (positions written, vaults read)."""
    root = Path(out) / "hlp"
    now_ms = now_ms or int(time.time() * 1000)
    kids = children(xb.post({"type": "vaultDetails", "vaultAddress": HLP}))
    pos, acc = [], []
    for a in kids:
        p, ac = vault_rows(a, xb.post({"type": "clearinghouseState", "user": a}))
        pos += p
        acc.append(ac)
    meta, ctxs = xb.post({"type": "metaAndAssetCtxs"})
    ctx = ctx_rows(meta, ctxs, now_ms)
    for d, rs in okx.by_day(pos, "ts").items():
        okx.merge_rows(root / "positions" / f"{d}.csv", rs, POS_COLS, ["ts", "vault", "coin"])
    for d, rs in okx.by_day(acc, "ts").items():
        okx.merge_rows(root / "accounts" / f"{d}.csv", rs, ACC_COLS, ["ts", "vault"])
    for d, rs in okx.by_day(ctx, "ts").items():
        okx.merge_rows(root / "ctx" / f"{d}.csv", rs, CTX_COLS, ["ts", "coin"])
    root.mkdir(parents=True, exist_ok=True)
    (root / "children.json").write_text(json.dumps(kids, indent=0) + "\n")
    return len(pos), len(kids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n, k = record(a.out)
    log(f"HLP positions {n} from {k} child vaults")
    if k == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
