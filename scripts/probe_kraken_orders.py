"""Retention probe for Kraken Futures' public order-event history (M437). Public, unauthenticated, count-limited.

For each (tradeable, age) it asks for the first few events at or after `now - age` (sort=asc) and the last few
before it (sort=desc), and keeps only the metadata: HTTP status, how many events, the oldest and newest event time,
the event types, whether a continuation token came back, and how far the first event after the requested time is
from it. No event body is stored, nothing is paged, and nothing is downloaded in bulk. The result answers one
question: how far back do public order events go, and is the history dense at that depth?

usage: python scripts/probe_kraken_orders.py [--tradeable PF_XBTUSD ...] [--out data/kraken_probe]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://futures.kraken.com/api/history/v3/market"
AGES = (("1h", 3600), ("1d", 86400), ("7d", 7 * 86400), ("30d", 30 * 86400), ("180d", 180 * 86400),
        ("365d", 365 * 86400))
COUNT = 3
PAUSE = 0.6


def url(tradeable, sort, since=None, before=None, count=COUNT):
    q = {"sort": sort, "count": count}
    if since is not None:
        q["since"] = since
    if before is not None:
        q["before"] = before
    return f"{BASE}/{urllib.parse.quote(tradeable)}/orders?{urllib.parse.urlencode(q)}"


def fetch(u, timeout=20):
    """Returns (http status, parsed body or None, next-continuation-token header or '')."""
    req = urllib.request.Request(u, headers={"User-Agent": "quant-lab-probe/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), r.headers.get("Next-Continuation-Token") or ""
    except urllib.error.HTTPError as e:
        return e.code, None, ""
    except (urllib.error.URLError, TimeoutError, ValueError):
        return 0, None, ""


def summarize(requested_ms, status, body, token):
    """Metadata only: nothing from an event body except its time and its type name."""
    els = (body or {}).get("elements") or []
    times = [int(e["timestamp"]) for e in els if "timestamp" in e]
    types = sorted({k for e in els for k in (e.get("event") or {})})
    token = token or (body or {}).get("continuationToken") or ""
    return {
        "http": status,
        "requested_ms": requested_ms,
        "n": len(els),
        "oldest_ms": min(times) if times else None,
        "newest_ms": max(times) if times else None,
        "types": types,
        "token": bool(token),
        "first_minus_requested_s": round((min(times) - requested_ms) / 1000, 3) if times else None,
    }


def probe(tradeable, now_ms, ages=AGES, fetch_fn=fetch, pause=PAUSE):
    rows = []
    for label, seconds in ages:
        t = now_ms - seconds * 1000
        for direction, kwargs in (("after", dict(sort="asc", since=t)), ("before", dict(sort="desc", before=t))):
            status, body, token = fetch_fn(url(tradeable, **kwargs))
            row = summarize(t, status, body, token)
            row.update(tradeable=tradeable, age=label, direction=direction)
            rows.append(row)
            time.sleep(pause)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tradeable", nargs="+", default=["PF_XBTUSD", "PF_ETHUSD"])
    ap.add_argument("--out", default="data/kraken_probe")
    args = ap.parse_args(argv)
    now_ms = int(time.time() * 1000)
    rows = []
    for tradeable in args.tradeable:
        rows += probe(tradeable, now_ms)
    stamp = datetime.fromtimestamp(now_ms / 1000, timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"orders_retention_{stamp}.json"
    path.write_text(json.dumps({"probed_utc": stamp, "base": BASE, "count": COUNT, "rows": rows}, indent=1))
    for r in rows:
        gap = r["first_minus_requested_s"]
        print(f"{r['tradeable']:10s} {r['age']:>5s} {r['direction']:6s} http {r['http']} n {r['n']} "
              f"oldest {r['oldest_ms']} newest {r['newest_ms']} types {','.join(r['types']) or '-'} "
              f"token {int(r['token'])} first-after-request {gap}s")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
