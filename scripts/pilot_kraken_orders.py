"""Completeness pilot for Kraken Futures' public order-event history (M437): one short window, hard request cap.

The retention probe (probe_kraken_orders.py) shows events exist back to 2022 on PF_XBTUSD and PF_ETHUSD. This pilot
answers the next question before anything larger is asked for: inside one short window, is the history a complete,
ordered order lifecycle that joins the public executions? It pages the public order events and public executions for
[start, end), keeps them gzip-compressed under data/kraken_probe/, and prints data-quality counts only (no price or
return statistic). Public, no key, no order. A request cap bounds the download.

usage: python scripts/pilot_kraken_orders.py --start 2026-10-28T07:45:00 --seconds 120 [--tradeable PF_XBTUSD]
"""
import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://futures.kraken.com/api/history/v3/market"
PAUSE = 0.35
FILL_REASONS = ("partial_fill", "full_fill")


def get(tradeable, kind, params, headers_out=None, timeout=40):
    u = f"{BASE}/{urllib.parse.quote(tradeable)}/{kind}?{urllib.parse.urlencode(params)}"
    err = ""
    for _ in range(4):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "quant-lab-probe/1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read())
                if headers_out is not None:
                    headers_out["token"] = r.headers.get("Next-Continuation-Token") or body.get("continuationToken") or ""
                return body
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            err = repr(e)[:100]
            time.sleep(2)
    raise RuntimeError(f"{kind} request failed: {err}")


def page(tradeable, kind, start_ms, end_ms, max_pages, get_fn=get, pause=PAUSE):
    """All elements in [start, end) by ascending time, following the continuation token. Returns (elements, pages, capped)."""
    out, pages, token = [], 0, ""
    while pages < max_pages:
        params = {"since": start_ms, "before": end_ms, "sort": "asc", "count": 1000}
        if token:
            params["continuation_token"] = token
        h = {}
        body = get_fn(tradeable, kind, params, h)
        els = body.get("elements") or []
        out += els
        pages += 1
        token = h.get("token") or ""
        if len(els) < 1000 or not token:
            return out, pages, False
        time.sleep(pause)
    return out, pages, True


def order_uid(event):
    """(type, order uid, reason, timestamp) of one order-event element, or None for a shape not in the docs."""
    (kind, body), = event["event"].items()
    o = body.get("order") or body.get("newOrder") or body.get("oldOrder") or {}
    return kind, o.get("uid"), body.get("reason"), event["timestamp"]


def quality(orders, execs):
    """Counts that say whether the window is a complete lifecycle record. Nothing about price direction."""
    q = {"order_events": len(orders), "executions": len(execs)}
    q["event_types"] = dict(Counter(order_uid(e)[0] for e in orders))
    q["fill_updates_by_reason"] = dict(Counter(r for k, _, r, _ in map(order_uid, orders) if k == "OrderUpdated"))
    q["duplicate_event_uids"] = len(orders) - len({e["uid"] for e in orders})
    q["duplicate_execution_uids"] = len(execs) - len({e["uid"] for e in execs})
    ts = [e["timestamp"] for e in orders]
    q["timestamp_decreases"] = sum(b < a for a, b in zip(ts, ts[1:]))
    q["same_ms_ties"] = sum(b == a for a, b in zip(ts, ts[1:]))
    placed, cancelled, filled_full = set(), set(), set()
    fills = {}
    for e in orders:
        kind, uid, reason, t = order_uid(e)
        if kind == "OrderPlaced":
            placed.add(uid)
        elif kind == "OrderCancelled":
            cancelled.add(uid)
        elif kind == "OrderUpdated" and reason in FILL_REASONS:
            fills.setdefault(uid, []).append(t)
            if reason == "full_fill":
                filled_full.add(uid)
    q["placed_uids"] = len(placed)
    q["cancelled_uids"] = len(cancelled)
    q["cancelled_with_placement_in_window"] = len(cancelled & placed)
    q["placed_closed_in_window"] = len(placed & (cancelled | filled_full))
    q["placed_still_resting_at_end"] = len(placed - cancelled - filled_full)
    maker = [e["event"]["Execution"]["execution"] for e in execs]
    q["exec_maker_uid_has_fill_update"] = sum(m["makerOrder"]["uid"] in fills for m in maker)
    q["exec_taker_uid_placed_in_window"] = sum(m["takerOrder"]["uid"] in placed for m in maker)
    q["exec_maker_placed_in_window"] = sum(m["makerOrder"]["uid"] in placed for m in maker)
    q["exec_taker_orders_distinct"] = len({m["takerOrder"]["uid"] for m in maker})
    near = 0
    for m in maker:
        t = m["timestamp"]
        near += any(abs(f - t) <= 3 for f in fills.get(m["makerOrder"]["uid"], ()))
    q["exec_maker_fill_update_within_3ms"] = near
    q["exec_order_types"] = dict(Counter(m["takerOrder"].get("orderType") for m in maker))
    return q


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--start", required=True, help="UTC, e.g. 2026-10-28T07:45:00")
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--tradeable", default="PF_XBTUSD")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--out", default="data/kraken_probe")
    a = ap.parse_args(argv)
    start = datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc)
    s_ms = int(start.timestamp() * 1000)
    e_ms = s_ms + a.seconds * 1000
    t0 = time.time()
    orders, op, ocap = page(a.tradeable, "orders", s_ms, e_ms, a.max_pages)
    execs, ep, ecap = page(a.tradeable, "executions", s_ms, e_ms, a.max_pages)
    out = Path(a.out) / f"pilot_{a.tradeable}_{start:%Y%m%dT%H%M%S}_{a.seconds}s"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("orders", orders), ("executions", execs)):
        with gzip.open(out / f"{name}.jsonl.gz", "wt") as h:
            for r in rows:
                h.write(json.dumps(r, separators=(",", ":")) + "\n")
    q = quality(orders, execs)
    q.update(window_utc=[start.isoformat(), a.seconds], tradeable=a.tradeable, order_pages=op, execution_pages=ep,
             order_pages_capped=ocap, execution_pages_capped=ecap, seconds_taken=round(time.time() - t0, 1))
    (out / "quality.json").write_text(json.dumps(q, indent=1))
    print(json.dumps(q, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
