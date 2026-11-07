"""Raw Deribit trades of the two at-the-money legs R410 (vrpexec_v1) trades each Friday: for every Friday D of
2021-01-01..2026-09-18 and BTC/ETH, the call and the put of the strike `scripts/vrpexec_rule.pick_strike` names
(point in time, from the held flow files and the perp price at D 08:00), from D 00:00 to D 12:00 UTC, from Deribit's
public history server (one or a few small requests per leg; no login).

Writes data/deribit_trades/<CUR>/atm_windows.parquet (one row per trade: friday_ms, strike, expiry_ms, cp, instrument,
trade_id, timestamp, price, mark_price, iv, index_price, direction, amount) and docs/provenance/deribit_atm_windows.json
(file hashes, request counts, fetch time). It reads no outcome: only which strike was nearest at 08:00.

usage: python scripts/fetch_deribit_atm_windows.py
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg  # noqa: E402
from scripts import vrpexec_rule as R  # noqa: E402
from scripts.run_clockflow import T0, T1  # noqa: E402
from scripts.run_optflow import COINS, PROVENANCE, hourly_prices  # noqa: E402
from scripts.run_vrpsell2 import fridays  # noqa: E402

OUT = data.ROOT / "deribit_trades"
FLOW = data.ROOT / "deribit_trades"
PROV = ROOT / "docs" / "provenance" / "deribit_atm_windows.json"
URL = ("https://history.deribit.com/api/v2/public/get_last_trades_by_instrument_and_time?instrument_name={i}"
       "&start_timestamp={a}&end_timestamp={b}&count=1000&sorting=asc")
COLS = ["friday_ms", "strike", "expiry_ms", "cp", "instrument", "trade_id", "timestamp", "price", "mark_price", "iv",
        "index_price", "direction", "amount"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def http(url, tries=6):
    delay = 2.0
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab/1", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())["result"]
        except Exception:  # noqa: BLE001 - retried, then raised
            if i == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2


def window(inst, a, b, get=http):
    """Every trade of one instrument with a <= timestamp <= b, each once; and the number of requests."""
    out, seen, start, n = [], set(), a, 0
    while True:
        r = get(URL.format(i=inst, a=start, b=b))
        n += 1
        page = [x for x in r["trades"] if x["trade_id"] not in seen]
        out += page
        seen.update(x["trade_id"] for x in page)
        if not r.get("has_more") or not r["trades"]:
            return out, n
        last = r["trades"][-1]["timestamp"]
        if not page and last == start:
            raise RuntimeError(f"{inst}: more than one page of trades in millisecond {start}")
        start = last


def flow_rows(cur, hashes):
    """Hourly flow rows (t, expiry_ms, strike, cp, instrument) of one currency in [T0, T1), each file hash-checked."""
    lo, hi = pd.Timestamp(T0, unit="ms").strftime("%Y-%m"), pd.Timestamp(T1 - 1, unit="ms").strftime("%Y-%m")
    parts = []
    for p in sorted((FLOW / cur / "flow").glob("*.parquet")):
        if not lo <= p.stem <= hi:
            continue
        rel = p.relative_to(FLOW).as_posix()
        if hashes.get(rel) != prereg.sha256_file(p):
            raise prereg.PreregError(f"{rel}: not in the provenance record, or changed since it")
        f = pd.read_parquet(p, columns=["t", "expiry_ms", "strike", "cp", "instrument"])
        parts.append(f[(f.t >= T0) & (f.t < T1)])          # 2020 is reserved: never read
    return pd.concat(parts, ignore_index=True)


def picks(cur, hashes):
    """[(D, K, call instrument, put instrument)] for every Friday with a strike; and the skipped Fridays."""
    rows = flow_rows(cur, hashes)
    PH = hourly_prices(data.ROOT / "klines_1m" / f"{COINS[cur]}.parquet")
    out, skipped = [], []
    for D in fridays():
        E = D + 7 * R.DAY + 8 * R.HOUR
        p = R.pick_strike(rows[rows.expiry_ms == E], D, PH, T0)
        if p is None:
            skipped.append(D)
        else:
            out.append((D, *p))
    return out, skipped


def main():
    hashes = {h["path"]: h["sha256"] for h in json.loads(PROVENANCE.read_text())["file_hashes"]}
    prov = {"source": "history.deribit.com get_last_trades_by_instrument_and_time (public)", "window_utc": "Fri 00:00-12:00",
            "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "coins": {}, "file_hashes": []}
    for cur in COINS:
        sel, skipped = picks(cur, hashes)
        rows, n_req = [], 0
        for j, (D, K, ci, pi) in enumerate(sel):
            E = D + 7 * R.DAY + 8 * R.HOUR
            for inst, cp in ((ci, "C"), (pi, "P")):
                tr, n = window(inst, D, D + R.END_H * R.HOUR)
                n_req += n
                rows += [{"friday_ms": D, "strike": K, "expiry_ms": E, "cp": cp, "instrument": inst,
                          "trade_id": str(x["trade_id"]), "timestamp": int(x["timestamp"]), "price": float(x["price"]),
                          "mark_price": float(x["mark_price"]), "iv": float(x.get("iv") or float("nan")),
                          "index_price": float(x["index_price"]), "direction": x["direction"],
                          "amount": float(x["amount"])} for x in tr]
            if j % 50 == 0:
                log(f"{cur}: {j}/{len(sel)} Fridays, {len(rows)} trades, {n_req} requests")
        df = pd.DataFrame(rows, columns=COLS).sort_values(["friday_ms", "cp", "timestamp", "trade_id"])
        path = OUT / cur / "atm_windows.parquet"
        df.to_parquet(path, index=False)
        rel = path.relative_to(ROOT).as_posix()
        prov["coins"][cur] = {"fridays": len(fridays()), "picked": len(sel), "no_strike": len(skipped),
                              "trades": int(len(df)), "requests": n_req}
        prov["file_hashes"].append({"path": rel, "sha256": prereg.sha256_file(path), "rows": int(len(df))})
        log(f"{cur}: done, {len(sel)} Fridays, {len(df)} trades, {n_req} requests, {len(skipped)} without a strike")
    PROV.write_text(json.dumps(prov, indent=1) + "\n")


if __name__ == "__main__":
    main()
