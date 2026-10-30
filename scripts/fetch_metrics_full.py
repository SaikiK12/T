"""Complete Binance metrics for every day the daily panel's top-150 universe reads, reduced to hours by
lab.flow.reduce_metrics into data/metrics_full/metrics_1h/. data/metrics_1h stays as it is: it is a frozen input of
earlier lanes.

Why: data/metrics_1h was fetched by lab/flow.py with needed_days(). A coin's day was fetched only when the coin was in
the old research set's top 100 by volume at some hour in that day or the next 35 days. So, in the panel, a row with
metrics says the coin will be among the most traded within 35 days: a look-ahead. In the top 150 by rank_qvol30
(2022-26) only about 25% of rows ranked 51-100 and 7% of rows ranked 101-150 have metrics, against 99% of the top 50.
Binance's archive has the files.

The days fetched: for every panel row D whose perp is in the top 150 by rank_qvol30 (computed from klines only), the
ten calendar days D-10..D-1 (row D holds day D-1, and the features read up to seven rows back). Every row a feature
reads for a universe row is then fetched, so the presence of metrics no longer depends on the future for those rows.

Each perp's daily folder is listed once; a needed day with no file in the listing is recorded as missing from the
archive, a listed file that fails after retries as failed (a second pass retries those). Resumable: a perp with a
parquet is skipped.

usage: python scripts/fetch_metrics_full.py [--workers 48] [--symbols A,B]
"""
import argparse
import http.client
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, flow  # noqa: E402

OUT = ROOT / "data" / "metrics_full" / "metrics_1h"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
TOP, BACK = 150, 10
START, END = "2021-01-01", data.END
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def needed(panel=None, top=TOP, back=BACK):
    """{perp: sorted list of 'YYYY-MM-DD'}: the days D-back..D-1 of every row D in the top `top` by rank_qvol30."""
    d = panel if panel is not None else pd.read_parquet(PANEL, columns=["day", "perp", "rank_qvol30"])
    u = d.loc[d.rank_qvol30 <= top, ["day", "perp"]]
    day = pd.to_datetime(u.day)
    perp = u.perp.astype(str).to_numpy()
    out = {}
    for k in range(1, back + 1):
        for p, s in zip(perp, (day - pd.Timedelta(days=k)).dt.strftime("%Y-%m-%d")):
            if START <= s <= END:
                out.setdefault(p, set()).add(s)
    return {p: sorted(v) for p, v in sorted(out.items())}


def listed(symbol):
    """{'YYYY-MM-DD': key} of the symbol's daily metrics files in the archive."""
    out = {}
    for k in data.list_zips(f"{data.UM}/daily/metrics/{symbol}/"):
        m = data._DATE.search(k)
        if m and m.group(2):
            out[m.group(1) + m.group(2)] = k
    return out


def one_symbol(symbol, days, ex):
    have = listed(symbol)
    keys = [have[d] for d in days if d in have]
    parts = dict(zip(keys, ex.map(lambda k: flow._one(k, "metrics"), keys)))
    failed = [k for k, p in parts.items() if p is None]
    for k in failed:                                   # a second pass, one at a time
        parts[k] = flow._one(k, "metrics")
    got = [p for p in parts.values() if p is not None]
    info = {"needed": len(days), "listed": len(keys), "used": len(got),
            "missing": [d for d in days if d not in have],
            "failed": [k.rsplit("-metrics-", 1)[1][:10] for k, p in parts.items() if p is None]}
    if got:
        df = pd.concat(got, ignore_index=True).drop_duplicates("t", keep="last").sort_values("t")
        df.to_parquet(OUT / f"{symbol}.parquet", index=False)
        info.update(rows=len(df), first=int(df.t.iloc[0]), last=int(df.t.iloc[-1]))
    return info


def fetch_symbol(symbol, days, ex, tries=4):
    """one_symbol, retried whole when the archive's listing or a download breaks off mid-read: http.client raises
    IncompleteRead, which lab.data's retry does not catch (it stopped the first full run at perp 383 of 737)."""
    for k in range(tries):
        try:
            return one_symbol(symbol, days, ex)
        except (http.client.HTTPException, data.FetchError, OSError) as e:
            if k == tries - 1:
                raise
            log(f"{symbol}: {type(e).__name__}, retry {k + 1}")
            time.sleep(5 * 2 ** k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--symbols")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    need = needed()
    if a.symbols:
        need = {s: need[s] for s in a.symbols.split(",") if s in need}
    mpath = OUT / "manifest.json"
    man = json.loads(mpath.read_text())["symbols"] if mpath.exists() else {}
    log(f"{len(need)} perps, {sum(map(len, need.values()))} perp-days needed; {len(man)} done before")
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        for i, (s, days) in enumerate(need.items(), 1):
            if s in man and ((OUT / f"{s}.parquet").exists() or not man[s].get("used")):
                continue
            man[s] = fetch_symbol(s, days, ex)
            m = man[s]
            log(f"{i}/{len(need)} {s}: {m['used']}/{m['needed']} days (missing {len(m['missing'])}, failed "
                f"{len(m['failed'])}), {(time.time() - t0) / 60:.1f} min")
            if i % 20 == 0:
                mpath.write_text(json.dumps({"start": START, "end": END, "top": TOP, "back": BACK, "symbols": man}))
    mpath.write_text(json.dumps({"start": START, "end": END, "top": TOP, "back": BACK, "symbols": man}))
    tot = {k: sum(len(v[k]) if isinstance(v[k], list) else v[k] for v in man.values())
           for k in ("needed", "listed", "used", "missing", "failed")}
    log(f"done: {tot}")


if __name__ == "__main__":
    main()
