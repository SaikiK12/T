"""carryhurdle_v1 (R483, M478/M481, gate 0): do the lab's audited cross-venue carry books beat the passive stablecoin
yields that harvest the same payer (Ethena sUSDe) or lend the same dollars (Aave v3 Core USDC on Ethereum)?

Per book b, engine, cost level c and benchmark k, on the UTC dates D of the book's committed daily net:
    r_k(D) = daily rate from the benchmark row dated D - 1 (the last snapshot before D starts); D is dropped when
             that row is missing or its apyBase is null; never filled
    Aave (APR):      r = apyBase / 100 / 365
    sUSDe (weekly):  r = 52 x ((1 + apyBase / 100)^(1/52) - 1) / 365
    bill (4.13%/yr): r = 0.0413 / 365                          (report only, as R437/R438's hurdle)
    e(D) = net_c(b, D) - r_k(D)
Window: the book's dates from the benchmark's first usable date to 2026-09-30. Sub-windows 2025-01-01+ and
2025-04-09+ are reported. Statistics: annualised mean excess (x 365, points a year), Newey-West t with 10 calendar
lags (lab.stats.newey_west_t, R437/R438's rule; dropped days are NaN gaps), sd, max drawdown of the book, the
benchmark and the excess (cumulative sums), and the share of the book's sum from its 10 best days.
Deciders: the six forward books, engine v2, cost 2x, benchmark sUSDe (DECIDERS). BEATS if excess > 0 and t >= 2;
LOSES if excess < 0 and t <= -2; else TIES. Lane: PASS if at least half BEAT and none LOSE; NULL if at least half
LOSE; PARTIAL otherwise.

The run reads only the paths passed to run(); main() supplies the lane's paths.
usage: .venv/bin/python scripts/run_carryhurdle.py [--no-check]
"""
import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

REGISTRY = "R483"
LANE = ROOT / "experiments" / "carryhurdle_v1"
BOOK_FILES = (ROOT / "experiments" / "carry_v2_audit_v1" / "results" / "daily.csv",
              ROOT / "experiments" / "carry_v2_audit_kc_v1" / "results" / "daily.csv")
# pool -> (name, conversion, sealed sha256 from research/intake/websearch_wave_20261112.md)
POOLS = {
    "66985a81-9c51-46ca-9977-42b4fe7bc6df":
        ("susde", "weekly", "4ad057baa24c7d6b18b02d7b66ca8f6832405127017e7ab19832ca8635073d06"),
    "aa70268e-4b52-42bf-a116-608b370f9501":
        ("aave_usdc", "apr", "007e634e247ae349cd4c89b10b28a3b14b7f5a3a5229ed694adae1a377aaf87d"),
    "f981a304-bb6c-45b8-b0c5-fd2f515ad23a":
        ("aave_usdt", "apr", "40bfab15bfda45d6a1cb00dd2baef6b5f8c4d1e9779b60a2de627802204babc7"),
}
FIELD = "apyBase"
BILL_PCT = 4.13
DECIDE_BENCH, DECIDE_ENGINE, DECIDE_COST = "susde", "v2", 2
DECIDERS = {  # book label in the committed daily.csv -> forward lane
    "gate+hyperliquid L14d th5% K20": "R278 A",
    "binance+mexc L14d th10% K20": "R278 B",
    "gate+mexc L7d th10% K20": "R278 C",
    "binance+gate L14d th10% K20": "R390 A",
    "gate+kucoin L14d th5% K20": "R279 A",
    "binance+kucoin L14d th5% K20": "R279 B",
}
END = "2026-09-30"
SUBWINDOWS = {"2025+": "2025-01-01", "2025-04-09+": "2025-04-09"}
NW_LAG, T_BAR = 10, 2.0


class InputError(Exception):
    pass


def daily_rate(apy_base_pct, kind):
    """Daily simple rate from DefiLlama's apyBase (percent a year) under the frozen conversion."""
    a = np.asarray(apy_base_pct, float) / 100.0
    if kind == "apr":
        return a / 365.0
    if kind == "weekly":
        return 52.0 * (np.power(1.0 + a, 1.0 / 52.0) - 1.0) / 365.0
    raise ValueError(kind)


def chart_rates(body, kind):
    """Series of daily rates indexed by the UTC date the book uses: the row dated D-1 serves book date D."""
    js = json.loads(body) if isinstance(body, (bytes, str)) else body
    if js.get("status") != "success":
        raise InputError("chart body status is not success")
    df = pd.DataFrame(js["data"])
    df["row_date"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None).dt.normalize()
    if df["row_date"].duplicated().any():
        raise InputError("duplicate UTC dates in a chart body")
    df = df[df[FIELD].notna()]
    rate = pd.Series(daily_rate(df[FIELD].to_numpy(float), kind), index=df["row_date"] + pd.Timedelta(days=1))
    return rate.sort_index()


def bill_rates(dates):
    return pd.Series(BILL_PCT / 100.0 / 365.0, index=pd.DatetimeIndex(dates))


def max_dd(x):
    cum = np.cumsum(np.nan_to_num(x))
    return float((cum - np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]).min()) if len(cum) else math.nan


def excess_stats(net, rate):
    """net, rate: Series on dates. Aligns on the calendar from the first common date; missing rate days are NaN gaps."""
    net = net.dropna()
    rate = rate.dropna()
    common = net.index.intersection(rate.index)
    if len(common) < 2:
        return {"days": int(len(common))}
    cal = pd.date_range(common.min(), common.max(), freq="D")
    n = net.reindex(cal)
    r = rate.reindex(cal)
    e = (n - r).to_numpy(float)
    ok = ~np.isnan(e)
    obs, mu, t = newey_west_t(e, NW_LAG)
    nb, rb = n.to_numpy(float)[ok], r.to_numpy(float)[ok]
    srt = np.sort(nb)[::-1]
    tot = float(nb.sum())
    return {"days": int(obs), "first": str(cal[ok][0].date()), "last": str(cal[ok][-1].date()),
            "dropped_days": int((~ok).sum()),
            "book_ann_pct": float(nb.mean() * 365 * 100), "bench_ann_pct": float(rb.mean() * 365 * 100),
            "excess_ann_pct": float(mu * 365 * 100), "nw_t": float(t),
            "excess_sd_daily_bp": float(np.std(e[ok], ddof=1) * 1e4),
            "excess_sd_ann_pct": float(np.std(e[ok], ddof=1) * math.sqrt(365) * 100),
            "book_max_dd_pct": max_dd(nb) * 100, "bench_max_dd_pct": max_dd(rb) * 100,
            "excess_max_dd_pct": max_dd(e[ok]) * 100,
            "book_top10_share": float(srt[:10].sum()) / tot if tot > 0 else math.nan}


def classify(st):
    x, t = st.get("excess_ann_pct", math.nan), st.get("nw_t", math.nan)
    if x == x and t == t:
        if x > 0 and t >= T_BAR:
            return "BEATS"
        if x < 0 and t <= -T_BAR:
            return "LOSES"
    return "TIES"


def lane_verdict(calls):
    n = len(calls)
    beats = sum(c == "BEATS" for c in calls)
    loses = sum(c == "LOSES" for c in calls)
    if n and 2 * beats >= n and loses == 0:
        return "PASS"
    if n and 2 * loses >= n:
        return "NULL"
    return "PARTIAL"


REGISTRY_VERDICT = {"PASS": "CONFIRMED", "PARTIAL": "PARTIAL", "NULL": "NULL"}


def frozen_inputs(prereg_path, root):
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S)
    if not block:
        raise prereg.PreregError(f"{prereg_path}: no inputs block")
    rows = [ln.split() for ln in block.group(1).strip().splitlines() if ln.strip()]
    for want, rel in rows:
        got = prereg.sha256_file(Path(root) / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
    return rows


def verify_raw(raw, pools):
    """Every body must match both the import receipt and the sealed hash; returns {pool: bytes}."""
    raw = Path(raw)
    rec_path = raw / "import_receipt.json"
    if not rec_path.is_file():
        raise InputError(f"{rec_path} missing: run the importer first")
    rec = json.loads(rec_path.read_text())["files"]
    out = {}
    for pool, (_, _, sealed) in pools.items():
        body = (raw / f"{pool}.json").read_bytes()
        got = hashlib.sha256(body).hexdigest()
        if got != sealed or rec.get(f"{pool}.json", {}).get("sha256") != sealed:
            raise InputError(f"{pool}.json: sha256 {got} differs from the sealed hash or the import receipt")
        out[pool] = body
    return out


def load_books(paths):
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    if df.duplicated(["book", "engine", "date"]).any():
        raise InputError("duplicate book/engine/date rows")
    return df[df["date"] <= END]


def run(lane, raw, book_files, pools, root, check=True, out=None):
    lane, out = Path(lane), Path(out) if out else Path(lane)
    lines = []

    def log(*a):
        s = " ".join(str(x) for x in a)
        lines.append(s)
        print(time.strftime("%H:%M:%S"), s, flush=True)

    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md', root))} inputs match")
    bodies = verify_raw(raw, pools)
    log(f"raw bodies verified: {len(bodies)}")
    rates = {pools[p][0]: chart_rates(b, pools[p][1]) for p, b in bodies.items()}
    books = load_books(book_files)
    rates["bill"] = bill_rates(pd.date_range(books["date"].min(), END, freq="D"))
    rows = []
    for (book, eng), g in books.groupby(["book", "engine"], sort=True):
        g = g.set_index("date").sort_index()
        for c in (1, 2, 3):
            net = g[f"net_{c}x"]
            for k, r in rates.items():
                for win, start in [("full", None)] + list(SUBWINDOWS.items()):
                    nn = net if start is None else net[net.index >= start]
                    st = excess_stats(nn, r)
                    rows.append({"book": book, "forward": DECIDERS.get(book, ""), "engine": eng, "cost": c,
                                 "bench": k, "window": win, **st, "call": classify(st)})
    tab = pd.DataFrame(rows)
    dec = tab[(tab.bench == DECIDE_BENCH) & (tab.engine == DECIDE_ENGINE) & (tab.cost == DECIDE_COST)
              & (tab.window == "full") & tab.book.isin(list(DECIDERS))]
    if len(dec) != len(DECIDERS):
        raise InputError(f"{len(dec)} decider rows, expected {len(DECIDERS)}")
    calls = dec.set_index("book")["call"].to_dict()
    verdict = lane_verdict(list(calls.values()))
    for b, row in dec.set_index("book").iterrows():
        log(f"{DECIDERS[b]} {b}: excess {row.excess_ann_pct:+.2f} pts/yr (NW t {row.nw_t:.2f}) over "
            f"{row.days} days -> {row.call}")
    log(f"verdict: {verdict} (registry {REGISTRY_VERDICT[verdict]})")
    res = out / "results"
    res.mkdir(parents=True, exist_ok=True)
    tab.to_csv(res / "table.csv", index=False, float_format="%.6f")
    summ = {"registry": REGISTRY, "decides": {"bench": DECIDE_BENCH, "engine": DECIDE_ENGINE, "cost": DECIDE_COST},
            "deciders": {b: {"forward": DECIDERS[b], "call": calls[b]} for b in DECIDERS},
            "verdict": verdict, "registry_verdict": REGISTRY_VERDICT[verdict]}
    (res / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    (out / "run.log").write_text("\n".join(lines) + "\n")
    return summ, tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-check", action="store_true", help="skip the PREREG check (tests only)")
    a = ap.parse_args()
    run(LANE, LANE / "raw", BOOK_FILES, POOLS, ROOT, check=not a.no_check)


if __name__ == "__main__":
    main()
