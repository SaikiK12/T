"""Recorder for Hyperliquid's vaults, closed ones included (M507): the list of every vault and each vault's whole
account-value and pnl history. A vault deposit is reachable from France with no account; a rule that picks vaults by
their past record needs every vault that existed, not only today's survivors. Public data, no key, no order, no
deposit. Stdlib only, so it runs on a bare GitHub runner.

Writes under OUT:
- index.csv: address, name, leader, created_ms, is_closed, relationship, first_seen_ms. Every vault in the public stats
  list (stats-data.hyperliquid.xyz/Mainnet/vaults). Its apr and pnl summaries are not kept.
- meta.csv: address, fetched_ms, is_closed, allow_deposits, leader_commission, leader_fraction, points, peak_av. One row
  per vault fetched, replaced on each fetch.
- hist/<first 4 hex>/<address>.csv: ts (ms), account_value, pnl from vaultDetails' `allTime` window, merged by ts
  across runs. `allTime` pnl starts at 0 at the vault's first point, so its baseline holds from run to run. Kept only
  for vaults whose account value ever reached MIN_PEAK_AV (far below any size a rule would invest in).
- last_run.json.

A closed vault already on file is not fetched again. Child vaults (HLP's) are skipped; HLP itself is a protocol vault
recorded by scripts/record_dex_vaults.py. Each run fetches vaults never fetched first, then the stalest, until its time
budget ends, so a few runs complete the first fill and a weekly run then refreshes the open vaults.

usage: python scripts/record_hl_vaults.py --out DIR [--limit N] [--pause S] [--budget-min M]
"""
import argparse
import csv
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("record_dex_vaults", ROOT / "scripts" / "record_dex_vaults.py")
dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dv)            # reuse its GET, Hyperliquid's post and the OKX recorder's merge (not changed)
hl, okx, log = dv.hl, dv.okx, dv.log

STATS = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
MIN_PEAK_AV = 10_000.0
INDEX_COLS = ["address", "name", "leader", "created_ms", "is_closed", "relationship", "first_seen_ms"]
META_COLS = ["address", "fetched_ms", "is_closed", "allow_deposits", "leader_commission", "leader_fraction", "points",
             "peak_av"]
HIST_COLS = ["ts", "account_value", "pnl"]


def post(body, tries=5):
    """Hyperliquid info call with backoff; the caller paces (vaultDetails weighs 20 of 1200 a minute per IP)."""
    delay, err = 5.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(hl.API, json.dumps(body).encode(),
                                         {"Content-Type": "application/json", "User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404, 422):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{body.get('type')}: {err}")


def read_csv(p):
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def vault_list(raw, now_ms, old):
    """Index rows from the stats list; first_seen_ms keeps the earliest run that saw each vault."""
    seen = {r["address"]: r.get("first_seen_ms") or str(now_ms) for r in old}
    rows = []
    for v in raw:
        s = v.get("summary") or {}
        a = str(s.get("vaultAddress", "")).lower()
        if not a:
            continue
        rows.append({"address": a, "name": s.get("name", ""), "leader": str(s.get("leader", "")).lower(),
                     "created_ms": s.get("createTimeMillis", ""), "is_closed": int(bool(s.get("isClosed"))),
                     "relationship": (s.get("relationship") or {}).get("type", ""),
                     "first_seen_ms": seen.get(a, str(now_ms))})
    return sorted(rows, key=lambda r: r["address"])


def all_time(details):
    """allTime rows (ts, account_value, pnl) at the points both series share."""
    port = dict(details.get("portfolio") or [])
    w = port.get("allTime") or {}
    av = {int(t): v for t, v in w.get("accountValueHistory") or []}
    return [{"ts": int(t), "account_value": av[int(t)], "pnl": p} for t, p in w.get("pnlHistory") or [] if int(t) in av]


def hist_path(out, a):
    return out / "hist" / a[2:6] / f"{a}.csv"


def record(out, now_ms=None, stats_get=None, hl_post=None, pause=0.5, limit=None, budget_s=None):
    now_ms = now_ms or int(time.time() * 1000)
    stats_get = stats_get or dv.get
    hl_post = hl_post or post
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    s = {"vaults": 0, "fetched": 0, "kept": 0, "skipped_closed": 0, "skipped_child": 0, "rows_changed": 0, "failed": 0,
         "left": 0}
    index = vault_list(stats_get(STATS), now_ms, read_csv(out / "index.csv"))
    write_csv(out / "index.csv", INDEX_COLS, index)
    s["vaults"] = len(index)
    meta = {r["address"]: r for r in read_csv(out / "meta.csv")}
    todo = []
    for r in index:
        if r["relationship"] == "child":
            s["skipped_child"] += 1
        elif r["is_closed"] and r["address"] in meta and int(meta[r["address"]]["is_closed"] or 0):
            s["skipped_closed"] += 1                   # closed and already fetched after closing: nothing changes
        else:
            todo.append(r["address"])
    todo.sort(key=lambda a: (a in meta, int(float(meta[a]["fetched_ms"])) if a in meta else 0, a))
    todo = todo[:limit] if limit else todo
    for k, a in enumerate(todo):
        if budget_s is not None and time.time() - t0 > budget_s:
            s["left"] = len(todo) - k
            break
        try:
            d = hl_post({"type": "vaultDetails", "vaultAddress": a})
            rows = all_time(d)
            peak = max((float(x["account_value"]) for x in rows), default=0.0)
            meta[a] = {"address": a, "fetched_ms": now_ms, "is_closed": int(bool(d.get("isClosed"))),
                       "allow_deposits": int(bool(d.get("allowDeposits"))),
                       "leader_commission": d.get("leaderCommission", ""),
                       "leader_fraction": d.get("leaderFraction", ""),
                       "points": len(rows), "peak_av": peak}
            s["fetched"] += 1
            if peak >= MIN_PEAK_AV:
                s["rows_changed"] += okx.merge_rows(hist_path(out, a), rows, HIST_COLS, ["ts"])
                s["kept"] += 1
        except Exception as e:      # noqa: BLE001 - one vault must not stop the run
            s["failed"] += 1
            log(f"{a}: {type(e).__name__}: {e}")
        if (k + 1) % 500 == 0:
            write_csv(out / "meta.csv", META_COLS, sorted(meta.values(), key=lambda r: r["address"]))
            log(f"progress {k + 1}/{len(todo)}: kept {s['kept']}, failed {s['failed']}")
        time.sleep(pause)
    write_csv(out / "meta.csv", META_COLS, sorted(meta.values(), key=lambda r: r["address"]))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, help="fetch at most N vaults this run (tests and smoke runs)")
    ap.add_argument("--pause", type=float, default=0.5, help="seconds after each vaultDetails call")
    ap.add_argument("--budget-min", type=float, help="stop fetching after this many minutes (the rest waits)")
    a = ap.parse_args()
    t = time.time()
    s = record(Path(a.out), pause=a.pause, limit=a.limit, budget_s=a.budget_min * 60 if a.budget_min else None)
    log(f"hl vaults: {s} in {time.time() - t:.0f} s")
    (Path(a.out) / "last_run.json").write_text(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **s}) + "\n")
    return 1 if s["failed"] > max(20, s["fetched"] // 50) else 0


if __name__ == "__main__":
    sys.exit(main())
