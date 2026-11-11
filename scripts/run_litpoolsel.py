"""litpoolsel_v1 (R452, M507 on Lighter): Lighter's public pools picked by their past record. At each month end, among
operator pools at least 90 days old, deposit equally in the 5 with the best ratio of mean to sd of their daily
share-price returns over the past 90 days (past return above 0), for one month. Net of the operator's fee on gains
and a switching cost; an empty slot earns the hurdle. Read against the 4% hurdle. Rule, windows and decision are in
experiments/litpoolsel_v1/PREREG.md.

Data: Lighter's public API, no account or key: `publicPoolsMetadata` (every public pool, closed ones included) and
`account?by=index` (each pool's daily share prices since its start). Paper only: nothing here deposits or orders.

usage: python scripts/run_litpoolsel.py --window fetch|gate0
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LANE = ROOT / "experiments" / "litpoolsel_v1"
DATA = LANE / "data"
API = "https://mainnet.zklighter.elliot.ai/api/v1"
DAY = 86_400_000
# ---- the frozen rule (PREREG "Rule")
AUTO_MASTER = 4                      # Lighter's own 1x-3x long/short index pools (master account 4): excluded
PROTOCOL_TYPE = 3                    # LLP and XLP (account type 3): excluded, reported
MIN_AGE_DAYS = 90
LOOKBACK_DAYS = 90
MIN_POINTS = 60
TOP_N = 5
SWITCH_COST = 0.0010                 # withdrawal and deposit of one slot's capital, at 1x
HURDLE_ANN = 0.04
NW_LAG = 3
G0 = ("2025-11-30", "2026-09-30")    # formations; the last is held to 2026-10-31
POOL_COLS = ["account_index", "name", "account_type", "master_account_index", "created_at", "status", "operator_fee",
             "min_operator_share_rate", "total_asset_value", "operator_shares", "total_shares"]


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def month_ends(first, last):
    return [str(d.date()) for d in pd.date_range(first, last, freq="ME")]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- fetch (files only, no return)
def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lab"}), timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:                       # noqa: BLE001 - retried, then raised
            if i == tries - 1:
                raise
            log("retry", url, e)
            time.sleep(2 ** (i + 1))


def fetch():
    """pools.csv (the metadata of every public pool) and share_prices.csv (each pool's daily share prices)."""
    pools, idx = [], 2 ** 48 - 1
    while True:
        page = get(f"{API}/publicPoolsMetadata?index={idx}&limit=100&filter=all")["public_pools"]
        if not page:
            break
        pools += page
        idx = min(p["account_index"] for p in page)
        if len(page) < 100:
            break
        time.sleep(0.5)
    pools = sorted({p["account_index"]: p for p in pools}.values(), key=lambda p: p["account_index"])
    DATA.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, p in enumerate(pools):
        acc = get(f"{API}/account?by=index&value={p['account_index']}")["accounts"][0]
        pi = acc.get("pool_info") or {}
        p["min_operator_share_rate"] = pi.get("min_operator_share_rate", "")
        p["operator_shares"] = pi.get("operator_shares", "")
        for x in pi.get("share_prices") or []:
            rows.append((p["account_index"], int(x["timestamp"]), repr(float(x["share_price"]))))
        if k % 50 == 0:
            log(k, "of", len(pools))
        time.sleep(0.25)
    with open(DATA / "pools.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(POOL_COLS)
        for p in pools:
            w.writerow([p.get(c, "") for c in POOL_COLS])
    with open(DATA / "share_prices.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["account_index", "ts", "share_price"])
        w.writerows(sorted(set(rows)))
    log(len(pools), "pools,", len(rows), "share prices")


# ---------------------------------------------------------------- data
def universe(pools):
    """Operator pools: not Lighter's auto index pools, not the protocol pools."""
    return pools[(pools.master_account_index != AUTO_MASTER) & (pools.account_type != PROTOCOL_TYPE)]


def load(data=DATA):
    pools = pd.read_csv(data / "pools.csv")
    sp = pd.read_csv(data / "share_prices.csv")
    sp["ts"] = sp.ts * 1000
    hist = {int(a): (g.ts.to_numpy(np.int64), g.share_price.to_numpy(float))
            for a, g in sp.sort_values(["account_index", "ts"]).groupby("account_index")}
    return pools, hist


def at(h, t):
    """Index of the last share price at or before t, or None."""
    i = int(np.searchsorted(h[0], t, side="right")) - 1
    return i if i >= 0 else None


def score(h, t):
    """(mean over sd, sum) of the daily log share-price returns in (t - LOOKBACK, t]; None if too few points."""
    lo = int(np.searchsorted(h[0], t - LOOKBACK_DAYS * DAY, side="right"))
    i1 = at(h, t)
    if i1 is None or i1 - lo + 1 < MIN_POINTS:                    # prices after t - LOOKBACK, up to t
        return None
    p = h[1][max(lo - 1, 0):i1 + 1]
    if (p <= 0).any():
        return None
    r = np.diff(np.log(p))
    sd = r.std(ddof=1)
    if not np.isfinite(sd) or sd <= 0:
        return None
    return float(r.mean() / sd), float(r.sum())


def held_return(h, t0, t1):
    """Share price at the last point at or before t1 over the one at or before t0, minus 1. A pool whose prices end
    keeps its return to its last price."""
    i0, i1 = at(h, t0), at(h, t1)
    if i0 is None or i1 is None or i1 <= i0 or h[1][i0] <= 0:
        return 0.0
    return float(h[1][i1] / h[1][i0] - 1.0)


def bounds(f):
    t0 = ms(f) + DAY - 1                                              # the end of the formation day
    nxt = (pd.Timestamp(f) + pd.offsets.MonthEnd(1)).date()
    return t0, ms(str(nxt)) + DAY - 1, str(nxt)


# ---------------------------------------------------------------- book
def run(pools, hist, first, last):
    """One row per formation month end in [first, last]: picks, gross and net returns held to the next month end."""
    u = universe(pools)
    fee = {int(r.account_index): float(r.operator_fee) / 100 for r in u.itertuples()}
    born = {int(r.account_index): int(r.created_at) * 1000 for r in u.itertuples()}
    rows, prev = [], set()
    for f in month_ends(first, last):
        t0, t1, nxt = bounds(f)
        cand, elig = [], 0
        for a in fee:
            h = hist.get(a)
            if h is None or born[a] > t0 - MIN_AGE_DAYS * DAY or at(h, t0) is None or h[0][at(h, t0)] < t0 - 3 * DAY:
                continue                                              # too young, or no price in the last 3 days
            elig += 1
            sc = score(h, t0)
            if sc is not None and sc[1] > 0:
                cand.append((sc[0], a))
        picks = [a for _, a in sorted(cand, reverse=True)[:TOP_N]]
        gross = [held_return(hist[a], t0, t1) for a in picks]
        net = [g - fee[a] * max(g, 0.0) for g, a in zip(gross, picks)]
        new, gone = len(set(picks) - prev), len(prev - set(picks))
        cost = SWITCH_COST * max(new, gone) / TOP_N
        days = (t1 - t0) / DAY
        idle = HURDLE_ANN * days / 365 * (TOP_N - len(picks))         # an empty slot earns the hurdle (cash)
        book_net = (sum(net) + idle) / TOP_N
        rows.append({"formation": f, "held_to": nxt, "days": days, "eligible": elig, "candidates": len(cand),
                     "picks": len(picks), "new": new, "gross": (sum(gross) + idle) / TOP_N, "net_fee": book_net,
                     "cost_1x": cost, "net_1x": book_net - cost, "net_2x": book_net - 2 * cost,
                     "net_3x": book_net - 3 * cost, "pools": " ".join(map(str, picks))})
        prev = set(picks)
    return pd.DataFrame(rows)


def eligible_mean(pools, hist, first, last):
    """Reported only: the equal-weight return, net of fee, of every eligible pool (same filters, no signal)."""
    u = universe(pools)
    out = []
    for f in month_ends(first, last):
        t0, t1, _ = bounds(f)
        rs = []
        for r in u.itertuples():
            h = hist.get(int(r.account_index))
            i = None if h is None else at(h, t0)
            if i is None or int(r.created_at) * 1000 > t0 - MIN_AGE_DAYS * DAY or h[0][i] < t0 - 3 * DAY:
                continue
            g = held_return(h, t0, t1)
            rs.append(g - float(r.operator_fee) / 100 * max(g, 0.0))
        out.append(float(np.mean(rs)) if rs else 0.0)
    return out


def reference(pools, hist, first, last):
    """Reported only: LLP and XLP held over the same months (no fee; LLP needs a LIT stake)."""
    out = {}
    for r in pools[pools.account_type == PROTOCOL_TYPE].itertuples():
        h = hist.get(int(r.account_index))
        if h is None:
            continue
        rs = [held_return(h, *bounds(f)[:2]) for f in month_ends(first, last)]
        days = sum((bounds(f)[1] - bounds(f)[0]) / DAY for f in month_ends(first, last))
        out[r.name] = {"net_ann": float(np.sum(rs) / (days / 365)), "worst_month": float(np.min(rs))}
    return out


def summary(book):
    out = {"months": int(len(book))}
    if not len(book):
        return out
    hurdle = HURDLE_ANN * book.days.to_numpy() / 365
    years = book.days.sum() / 365
    for m in ("1x", "2x", "3x"):
        x = book[f"net_{m}"].to_numpy(float)
        _, _, t = newey_west_t(x - hurdle, NW_LAG)
        out[m] = {"net_ann": float(x.sum() / years), "excess_ann": float((x - hurdle).sum() / years),
                  "nw_t_excess": t}
    x = book.net_1x.to_numpy(float)
    cum = np.cumsum(x)
    out["max_dd"] = float((cum - np.maximum.accumulate(np.maximum(cum, 0))).min())
    out["worst_month"] = float(x.min())
    out["worst_month_formation"] = str(book.formation.iloc[int(x.argmin())])
    out["sd_month"] = float(np.std(x - hurdle, ddof=1)) if len(x) > 1 else float("nan")
    out["avg_picks"] = float(book.picks.mean())
    out["avg_new"] = float(book.new.mean())
    out["fee_ann"] = float((book.gross - book.net_fee).sum() / years)
    return out


def decide_gate0(s):
    """Gate 0 decides: EARNED (forward continues) or NULL."""
    e1, t1, e2 = s["1x"]["excess_ann"], s["1x"]["nw_t_excess"], s["2x"]["excess_ann"]
    ok = e1 >= 0.03 and np.isfinite(t1) and t1 >= 2.0 and e2 > 0
    return "EARNED (forward continues)" if ok else "NULL (stop)"


def capacity(pools, book):
    """Reported only: today's value of each pool picked in the last formation, and its operator share."""
    if not len(book):
        return []
    last = [int(a) for a in str(book.pools.iloc[-1]).split()]
    p = pools.set_index("account_index")
    return [{"pool": a, "tvl_today": float(p.at[a, "total_asset_value"]), "status_today": int(p.at[a, "status"])}
            for a in last]


def check_inputs(block_name):
    text = (LANE / "PREREG.md").read_text()
    block = re.search(r"```" + re.escape(block_name) + r"\n(.*?)```", text, re.S).group(1)
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(ROOT / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=("fetch", "gate0"), required=True)
    a = ap.parse_args()
    if a.window == "fetch":
        if (LANE / "PREREG.sha256").exists():
            raise SystemExit("frozen: gate-0 data are fixed")
        fetch()
        return
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs("inputs")
    check_inputs("inputs-gate0")
    pools, hist = load()
    book = run(pools, hist, *G0)
    s = summary(book)
    s["pools_universe"] = int(len(universe(pools)))
    s["eligible_mean_ann"] = float(np.sum(eligible_mean(pools, hist, *G0)) / (book.days.sum() / 365))
    s["reference"] = reference(pools, hist, *G0)
    s["last_picks_today"] = capacity(pools, book)
    s["decision"] = decide_gate0(s)
    out = LANE / "results" / "gate0"
    out.mkdir(parents=True, exist_ok=True)
    book.to_csv(out / "months.csv", index=False, lineterminator="\n")
    (out / "report.json").write_text(json.dumps({"window": "gate0", "formations": G0, **s}, indent=1,
                                                default=float) + "\n")
    print(json.dumps(s, indent=1, default=float))


if __name__ == "__main__":
    main()
