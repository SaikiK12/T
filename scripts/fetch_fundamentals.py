"""Protocol fundamentals from DefiLlama's free API for every token that has a Binance perp: daily TVL, fees and revenue.

The crypto "value" axis: what a protocol earns against what its token is worth (price-to-fees, price-to-revenue,
market cap over TVL). Few open crypto quant projects carry it.

- Protocols come from `/protocols`. A protocol with a parent (Aave V3 under Aave) is counted under its parent, whose
  endpoint aggregates every version and carries the token (`gecko_id`, symbol).
- A token maps to a Binance perp by symbol (R274's `binance_perp` name rule). A perp claimed by two different
  `gecko_id`s is ambiguous and dropped (listed in `mapping.csv` as `ambiguous`). The same ticker is not proof of the
  same coin: a lane checks identity on prices.
- Series: TVL (`/protocol/<slug>`, `tvl`), fees and revenue (`/summary/fees/<slug>?dataType=dailyFees|dailyRevenue`).
  A protocol without a fee adapter has no fee columns.

Not point-in-time: DefiLlama serves its latest vintage and backfills adapters, so a lane lags these series and says
so. Rows before 2021-01-01 go to `reserved/` (docs/GATES.md). Saved in data/defillama/{open,reserved}/<PERP>.parquet
(t = 00:00 UTC of the day, tvl, fees, revenue) with `mapping.csv` and `manifest.json`. A perp whose file exists is
skipped, so it resumes. Data collection only.

usage: python scripts/fetch_fundamentals.py [--pause 0.3]
"""
import argparse
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402
from scripts.fetch_venue_history import OPEN_FROM_MS  # noqa: E402
from scripts.squeeze_events import binance_perp  # noqa: E402

API = "https://api.llama.fi"
OUT = data.ROOT / "defillama"
DAY = 86_400_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=5):
    delay = 2.0
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):                # no such adapter: not an error worth retrying
                return None
            err = e
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def candidates(protocols):
    """{slug: {symbol, gecko_id, parent}}: parents for children, standalone protocols as themselves."""
    out = {}
    for p in protocols:
        sym = (p.get("symbol") or "").upper()
        if not sym or sym == "-":
            continue
        if p.get("parentProtocol"):
            slug = p["parentProtocol"].split("#", 1)[1]
            out.setdefault(slug, {"symbol": sym, "gecko_id": None, "parent": True})
        elif p.get("gecko_id"):
            out[p["slug"]] = {"symbol": sym, "gecko_id": p["gecko_id"], "parent": False}
    return out


def mapping(cands, perps, gecko_of):
    """[(perp, slug, gecko_id, symbol, status)]: one slug per perp; perps two tokens claim are ambiguous."""
    by = {}
    for slug, c in cands.items():
        gid = c["gecko_id"] or gecko_of.get(slug)
        hit = binance_perp(c["symbol"], perps)
        if hit and gid:
            by.setdefault(hit[0], {}).setdefault(gid, []).append((slug, c["symbol"]))
    rows = []
    for perp, g in sorted(by.items()):
        if len(g) > 1:
            rows += [(perp, s, gid, sym, "ambiguous") for gid, v in g.items() for s, sym in v]
            continue
        (gid, v), = g.items()
        slug, sym = sorted(v, key=lambda x: (len(x[0]), x[0]))[0]   # the shortest slug: the parent or main one
        rows.append((perp, slug, gid, sym, "ok"))
    return rows


def day_series(points):
    s = pd.Series({int(t) // 86400 * DAY: float(v) for t, v in points}, dtype=float)
    return s[~s.index.duplicated(keep="last")].sort_index()


def fetch(slug, pause):
    cols = {}
    d = get(f"{API}/protocol/{slug}")
    time.sleep(pause)
    if d and d.get("tvl"):
        cols["tvl"] = day_series((x["date"], x["totalLiquidityUSD"]) for x in d["tvl"])
    for name, kind in (("fees", "dailyFees"), ("revenue", "dailyRevenue")):
        f = get(f"{API}/summary/fees/{slug}?dataType={kind}")
        time.sleep(pause)
        if f and f.get("totalDataChart"):
            cols[name] = day_series(f["totalDataChart"])
    if not cols:
        return pd.DataFrame(columns=["t", "tvl", "fees", "revenue"])
    df = pd.DataFrame(cols).reindex(columns=["tvl", "fees", "revenue"])
    df.index.name = "t"
    return df.reset_index().astype({"t": "int64"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pause", type=float, default=0.3)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    protocols = get(f"{API}/protocols")
    (OUT / "protocols.json").write_text(json.dumps(protocols))
    perps = {p.stem for p in (data.ROOT / "klines_1h").glob("*.parquet")}
    cands = candidates(protocols)
    gecko_of = {}
    for slug, c in cands.items():                 # parents carry their token only on their own endpoint
        if c["parent"] and binance_perp(c["symbol"], perps):
            d = get(f"{API}/protocol/{slug}")
            time.sleep(a.pause)
            if d and d.get("gecko_id"):
                gecko_of[slug] = d["gecko_id"]
    rows = mapping(cands, perps, gecko_of)
    with open(OUT / "mapping.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["binance_perp", "slug", "gecko_id", "symbol", "status"])
        w.writerows(rows)
    ok = [r for r in rows if r[4] == "ok"]
    log(f"{len(cands)} candidate protocols; {len(ok)} perps mapped, "
        f"{len({r[0] for r in rows if r[4] == 'ambiguous'})} ambiguous dropped")
    status = {}
    for i, (perp, slug, *_rest) in enumerate(ok, 1):
        if (OUT / "open" / f"{perp}.parquet").exists() or (OUT / "reserved" / f"{perp}.parquet").exists():
            status[perp] = "skip"
            continue
        try:
            df = fetch(slug, a.pause)
        except RuntimeError as e:
            status[perp] = f"error {e}"
            continue
        for where, part in (("open", df[df.t >= OPEN_FROM_MS]), ("reserved", df[df.t < OPEN_FROM_MS])):
            if len(part):
                (OUT / where).mkdir(exist_ok=True)
                part.to_parquet(OUT / where / f"{perp}.parquet", index=False)
        status[perp] = {"slug": slug, "days": len(df), "columns": [c for c in ("tvl", "fees", "revenue")
                                                                    if c in df and df[c].notna().any()]}
        if i % 25 == 0 or i == len(ok):
            log(f"{i}/{len(ok)} {perp} ({slug}): {status[perp]}")
    (OUT / "reserved").mkdir(exist_ok=True)
    (OUT / "reserved" / "README.md").write_text(
        "Reserved 2020 window (docs/GATES.md). Do not read: only a frozen batch PREREG declaring RESERVED-2020-READ "
        "may.\n")
    (OUT / "manifest.json").write_text(json.dumps({
        "source": API, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "errors": {k: v for k, v in status.items() if str(v).startswith("error")}, "perps": status}, indent=1))
    log("done")


if __name__ == "__main__":
    main()
