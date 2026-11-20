"""passive_kraken_v1 (R513): what a passive entry costs on Kraken's perps, against a taker entry, at the carry book's
decision time.

R508-R512's books pay a taker walk on each leg. Kraken's thin perps quote spreads of 18-23 bp, and the carry book holds
pairs for weeks, so it can wait for a resting order. Gate 0, cost measurement: no return is tested.

Per Kraken contract of R511's table (132 coins), per day D of the window and per side (buy, sell):
- t = D 00:00 UTC, the carry book's decision time. mid_t = Kraken's mark price at t (the 1 h mark candle opening at t).
- hs = half the quoted spread of the contract in the session's book snapshot (2026-11-18 for R508's coins, 2026-11-19
  for R511's other 31): one spread per coin, held constant.
- taker cost now = the snapshot's $1,000 book walk (cost_1000_bp) + the taker fee (5 bp, Kraken tier 1).
- **Passive order:** a limit at mid_t x (1 - hs) to buy, mid_t x (1 + hs) to sell, resting from t.
  - **Conservative fill:** a 5-minute trade candle with volume > 0 inside (t, t + H] trades strictly through the limit
    (low < limit to buy, high > limit to sell). A print through the level means the level was cleared, so the
    order is filled in full at its limit.
  - Filled: cost = -hs + the maker fee (2 bp).
  - Not filled by t + H: a taker order at t + H, cost = side x (mid_{t+H} / mid_t - 1) + cost_1000_bp + 5 bp, where
    mid_{t+H} is the mark at t + H. This charges the drift that kept the order from filling.
- saving = taker cost now - passive cost, in bp of notional per leg-side.
- **Optimistic fill (reported):** touching the limit (low <= limit) counts.

Decided: H = 6 h, conservative fill, on Kraken's thin coins (median daily volume under $100k, from R508's and R511's
diagnostics). The series is each day's mean saving across those coins and both sides; the test is its Newey-West t
(lag 5).

usage: python scripts/run_passive_kraken.py fetch | run
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "passive_kraken_v1"
DATA = ROOT / "data" / "kraken_passive"
CHARTS = "https://futures.kraken.com/api/charts/v1"
START, END = "2026-08-17", "2026-11-15"          # decision days, inclusive
FETCH_FROM, FETCH_TO = "2026-08-17", "2026-11-17"  # [from, to): one day past the last horizon
HORIZONS_H = (1, 6, 24)
PRIMARY_H = 6
MAKER_BP, TAKER_BP = 2.0, 5.0                     # Kraken Pro futures tier 1 (July 2026 table)
THIN_USD = 100_000
PACE = 0.35
H_MS, M5_MS, DAY = 3_600_000, 300_000, 86_400_000


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get(url, tries=5):
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 429:
                time.sleep(30)
            elif e.code in (400, 404):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def candles(tick, sym, res, start, end, step_ms):
    """All candles of `tick` (trade or mark) at resolution `res` with time in [start, end), paged forwards."""
    out, s = [], start
    while s < end:
        d = get(f"{CHARTS}/{tick}/{sym}/{res}?from={s // 1000}&to={(end - 1) // 1000}")
        time.sleep(PACE)
        c = d.get("candles") or []
        if not c:
            break
        out += c
        last = int(c[-1]["time"])
        if last < s or not d.get("more_candles"):
            break
        s = last + step_ms
    if not out:
        return pd.DataFrame(columns=["t", "open", "high", "low", "close", "volume"])
    df = pd.DataFrame({"t": [int(x["time"]) for x in out],
                       **{k: [float(x[k]) for x in out] for k in ("open", "high", "low", "close", "volume")}})
    return df[(df.t >= start) & (df.t < end)].drop_duplicates("t").sort_values("t", ignore_index=True)


# ---------------------------------------------------------------- inputs fixed before any fetch

def coin_table():
    """key, kraken symbol, hs_bp, cost_1000_bp, median daily USD volume, thin flag: from the frozen diagnostics."""
    sym = pd.read_csv(ROOT / "experiments" / "xfund_kaster_v1" / "symbols.csv")
    books = {**json.loads((ROOT / "experiments/xfund_eea_v1/diagnostics/books_20261118.json").read_text())["coins"],
             **json.loads((ROOT / "experiments/xfund_kaster_v1/diagnostics/books_20261119.json").read_text())["coins"]}
    v1 = pd.read_csv(ROOT / "experiments/xfund_eea_v1/diagnostics/kraken_volume.csv").set_index("key")
    v2 = pd.read_csv(ROOT / "experiments/xfund_kaster_v1/diagnostics/volume.csv").set_index("key")
    vol = {**v1.kraken_median_daily_usd.to_dict(), **v2.kraken_median_daily_usd.to_dict()}
    rows = []
    for _, r in sym.iterrows():
        k = (books.get(r.key) or {}).get("kraken") or {}
        if k.get("spread_bp") is None or k.get("cost_1000_bp") is None or r.key not in vol:
            continue
        rows.append({"key": r.key, "kraken": r.kraken, "hs_bp": k["spread_bp"] / 2, "cost_1000_bp": k["cost_1000_bp"],
                     "volume_usd": vol[r.key], "thin": vol[r.key] < THIN_USD})
    return pd.DataFrame(rows)


def check_inputs(prereg=None):
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        if sha256(ROOT / path) != digest:
            raise SystemExit(f"{path} changed since the freeze")


def fetch(log=print):
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    t = coin_table()
    a, b = ms(FETCH_FROM), ms(FETCH_TO)
    for d in ("trade5m", "mark1h", "receipts"):
        (DATA / d).mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(t.kraken):
        rec = DATA / "receipts" / f"{s}.json"
        if rec.exists():
            continue
        tr = candles("trade", s, "5m", a, b, M5_MS)
        mk = candles("mark", s, "1h", a, b, H_MS)
        tr.to_parquet(DATA / "trade5m" / f"{s}.parquet", index=False)
        mk.to_parquet(DATA / "mark1h" / f"{s}.parquet", index=False)
        rec.write_text(json.dumps({"symbol": s, "from": FETCH_FROM, "to_exclusive": FETCH_TO,
                                   "trade5m": len(tr), "mark1h": len(mk),
                                   "trade5m_sha256": sha256(DATA / "trade5m" / f"{s}.parquet"),
                                   "mark1h_sha256": sha256(DATA / "mark1h" / f"{s}.parquet"),
                                   "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1))
        if (i + 1) % 20 == 0:
            log(f"{i + 1}/{len(t)} {s}")
    log("fetch done")


# ---------------------------------------------------------------- the simulation

def simulate(trade, mark, hs_bp, cost_bp, days, horizons=HORIZONS_H):
    """Rows per (day, side, horizon): filled (conservative, optimistic), passive cost, taker cost, saving, bp."""
    m = dict(zip(mark.t, mark.open))
    tr = trade[trade.volume > 0]
    tt, lo, hi = tr.t.to_numpy(), tr.low.to_numpy(), tr.high.to_numpy()
    hs, taker = hs_bp / 1e4, cost_bp + TAKER_BP
    out = []
    for d in days:
        t0 = d
        mid = m.get(t0)
        if mid is None or not mid > 0:
            continue
        for side, sgn in (("buy", 1), ("sell", -1)):
            limit = mid * (1 - sgn * hs)
            for h in horizons:
                end = t0 + h * H_MS
                mid_h = m.get(end)
                if mid_h is None or not mid_h > 0:
                    continue
                k = (tt >= t0) & (tt + M5_MS <= end)      # candles that close inside (t0, t0 + H]
                if sgn == 1:
                    cons, opt = bool((lo[k] < limit).any()), bool((lo[k] <= limit).any())
                else:
                    cons, opt = bool((hi[k] > limit).any()), bool((hi[k] >= limit).any())
                miss = sgn * (mid_h / mid - 1) * 1e4 + taker
                p_cons = -hs_bp + MAKER_BP if cons else miss
                p_opt = -hs_bp + MAKER_BP if opt else miss
                out.append({"t": t0, "side": side, "h": h, "fill_cons": cons, "fill_opt": opt,
                            "passive_bp": p_cons, "passive_opt_bp": p_opt, "taker_bp": taker,
                            "saving_bp": taker - p_cons, "saving_opt_bp": taker - p_opt})
    return pd.DataFrame(out)


def check_data(t):
    bad = []
    for s in t.kraken:
        r = json.loads((DATA / "receipts" / f"{s}.json").read_text())
        for kind in ("trade5m", "mark1h"):
            if sha256(DATA / kind / f"{s}.parquet") != r[f"{kind}_sha256"]:
                bad.append(f"{kind}/{s}")
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from their receipts, e.g. {bad[:3]}")


def daily_test(rows, col="saving_bp"):
    g = rows.groupby("t")[col].mean().sort_index()
    x = g.to_numpy(float)
    if len(x) < 10:
        return {"days": int(len(x))}
    _, mu, t = newey_west_t(x, 5)
    return {"days": int(len(x)), "mean_bp": float(mu), "nw_t": float(t), "share_days_positive": float((x > 0).mean())}


def run():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    res = LANE / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    t = coin_table()
    check_data(t)
    days = list(range(ms(START), ms(END) + DAY, DAY))
    parts = []
    for _, r in t.iterrows():
        tr = pd.read_parquet(DATA / "trade5m" / f"{r.kraken}.parquet")
        mk = pd.read_parquet(DATA / "mark1h" / f"{r.kraken}.parquet")
        df = simulate(tr, mk, r.hs_bp, r.cost_1000_bp, days)
        if len(df):
            parts.append(df.assign(key=r.key, thin=r.thin, volume_usd=r.volume_usd, hs_bp=r.hs_bp))
    rows = pd.concat(parts, ignore_index=True)
    prim = rows[(rows.h == PRIMARY_H) & rows.thin]
    rep = {"coins": int(t.shape[0]), "thin_coins": int(t.thin.sum()), "window": [START, END],
           "decided": daily_test(prim)}
    d = rep["decided"]
    rep["verdict"] = ("UNREADABLE" if d.get("days", 0) < 30 else
                      "PASS" if d["mean_bp"] > 0 and d["nw_t"] >= 2.0 else "FAIL")
    buckets = pd.cut(rows.volume_usd, [-1, 1e4, 1e5, 1e6, 1e13], labels=["<10k", "10k-100k", "100k-1M", ">1M"])
    rep["by_bucket"] = {}
    for (b, h), g in rows.groupby([buckets, "h"], observed=True):
        rep["by_bucket"][f"{b} H{h}"] = {
            "coin_days": int(len(g) // 2), "fill_cons": float(g.fill_cons.mean()), "fill_opt": float(g.fill_opt.mean()),
            "taker_bp": float(g.taker_bp.mean()), "passive_bp": float(g.passive_bp.mean()),
            "passive_opt_bp": float(g.passive_opt_bp.mean()), "saving_bp": float(g.saving_bp.mean()),
            "saving_opt_bp": float(g.saving_opt_bp.mean())}
    rep["thin_by_h"] = {f"H{h}": daily_test(rows[(rows.h == h) & rows.thin]) for h in HORIZONS_H}
    rep["thin_optimistic_H6"] = daily_test(prim, "saving_opt_bp")
    res.mkdir(parents=True, exist_ok=True)
    rows.to_parquet(res / "rows.parquet", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], **rep["decided"]}, default=str))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("fetch", "run"))
    a = ap.parse_args(argv)
    fetch() if a.cmd == "fetch" else run()


if __name__ == "__main__":
    main()
