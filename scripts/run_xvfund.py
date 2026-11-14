"""R470 xvfund_v1, frozen in experiments/xvfund_v1/PREREG.md: cross-venue funding carry on the same US stock perp,
trade.xyz (Hyperliquid HIP-3) against Lighter. R443's carry rule (7-day realized funding spread, enter at 10%/yr, exit
below 5%/yr, 10 slots, each leg margined at 2x) on R465's 50 pairs. Gate 0 on held history: A (days to 2026-08-31)
decides, B (2026-09-01 .. 2026-11-10) confirms. Paper only.

usage: python scripts/run_xvfund.py      the frozen run (verifies the PREREG, every input it lists and the manifest)
"""
import csv
import json
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "xvfund_v1"
DATA = ROOT / "data" / "xvfund"
PAIRS = ROOT / "experiments" / "ltwknd_v1" / "universe.csv"      # R465's frozen pairs
XYZ_UNIVERSE = ROOT / "experiments" / "xyzwknd_v1" / "universe.csv"  # R462's frozen growth flags
REGISTRY = "R470"
DAY, H = 86_400_000, 3_600_000
LOOKBACK_D = 7
ENTER, EXIT = 0.10, 0.05          # annualized spread, per year of notional
SLOTS = 10
MIN_QUOTE_VOL = 100_000.0         # USD on the day closing at D, each venue
SPLIT_GUARD = 0.20                # |r_xyz - r_lighter| over one day: booked at zero price P&L, forced exit
XYZ_TAKER_BP = {True: 0.9, False: 9.0}   # R462: growth mode is a tenth of xyz's 9 bp standard taker fee
LIGHTER_TAKER_BP = 0.0            # Lighter Standard account (R465)
FILL_SLIP_BP = 2.0                # per fill: R462's 4 bp round trip
HURDLE = 0.04
NW_LAG = 10
LAST_D = date(2026, 11, 10)
SPANS = {"A": (date(2000, 1, 1), date(2026, 8, 31)), "B": (date(2026, 9, 1), LAST_D)}
MIN_A_DAYS = 60
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def ms(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def verify_bars(data):
    man = json.loads((data / "manifest.json").read_text())
    for rel, meta in man["files"].items():
        if prereg.sha256_file(data / rel) != meta["sha256"]:
            raise SystemExit(f"manifest mismatch: {rel}")
    return len(man["files"])


class Funding:
    """Prints of one venue for one coin: sums over (a, b] in O(log n)."""

    def __init__(self, df):
        df = df.sort_values("t")
        self.t = df["t"].to_numpy(np.int64)
        self.cs = np.concatenate([[0.0], np.cumsum(df["rate"].to_numpy(float))])
        self.first = int(self.t[0]) if len(self.t) else None

    def sum(self, a, b):
        return float(self.cs[np.searchsorted(self.t, b, "right")] - self.cs[np.searchsorted(self.t, a, "right")])


def xyz_daily(df):
    """D (ms of 00:00 UTC) -> (close, quote volume) from 1d candles opened at D - 1 day."""
    return {int(t) + DAY: (float(c), float(v) * float(c)) for t, c, v in zip(df["t"], df["close"], df["volume"])}


def lighter_daily(df, days):
    """D -> (close, quote volume): the close of the last traded 1 h bar opened in [D - 3 h, D - 1 h], and the day's
    quote volume (base volume x close) over bars opened in [D - 24 h, D)."""
    df = df.sort_values("t")
    t, c, v = df["t"].to_numpy(np.int64), df["close"].to_numpy(float), df["volume"].to_numpy(float)
    qv = np.concatenate([[0.0], np.cumsum(v * c)])
    out = {}
    for D in days:
        lo, hi = np.searchsorted(t, D - 3 * H, "left"), np.searchsorted(t, D - H, "right")
        close = next((c[i] for i in range(hi - 1, lo - 1, -1) if v[i] > 0), None)
        a, b = np.searchsorted(t, D - DAY, "left"), np.searchsorted(t, D, "left")
        out[D] = (None if close is None else float(close), float(qv[b] - qv[a]))
    return out


def load(data, pairs=PAIRS, xyz_universe=XYZ_UNIVERSE):
    with open(pairs, newline="") as f:
        coins = [r["coin"] for r in csv.DictReader(f)]
    with open(xyz_universe, newline="") as f:
        growth = {r["coin"]: r["growth"].strip().lower() == "enabled" for r in csv.DictReader(f)}
    mk = {}
    for coin in coins:
        rd = lambda v, s: pd.read_parquet(data / v / s / f"{coin}.parquet")  # noqa: E731
        mk[coin] = {"fx": Funding(rd("xyz", "funding")), "fl": Funding(rd("lighter", "funding")),
                    "kx": rd("xyz", "klines_1d"), "kl": rd("lighter", "klines_1h"),
                    "cost_bp": XYZ_TAKER_BP[growth.get(coin, False)] + LIGHTER_TAKER_BP + 2 * FILL_SLIP_BP}
    return mk


def book(mk, last=LAST_D):
    """Run the book over every day D from the first day any pair has a spread to `last`. Returns (daily, trades)."""
    firsts = [max(m["fx"].first, m["fl"].first) for m in mk.values() if m["fx"].first and m["fl"].first]
    if not firsts:
        return pd.DataFrame(), pd.DataFrame()
    d0 = datetime.fromtimestamp((min(firsts) + LOOKBACK_D * DAY) / 1000, timezone.utc).date() + timedelta(days=1)
    days = [ms(d0 + timedelta(days=i)) for i in range((last - d0).days + 1)]
    px = {c: (xyz_daily(m["kx"]), lighter_daily(m["kl"], [D - DAY for D in days[:1]] + days)) for c, m in mk.items()}
    held, rows, trades = {}, [], []
    for D in days:
        fund = price = cost = 0.0
        forced = {}
        for coin, pos in held.items():
            m, (dx, dl) = mk[coin], px[coin]
            fx, fl = m["fx"].sum(D - DAY, D), m["fl"].sum(D - DAY, D)
            f = (fx - fl) if pos["dir"] > 0 else (fl - fx)
            x0, x1 = dx.get(D - DAY, (None, 0))[0], dx.get(D, (None, 0))[0]
            l0, l1 = dl.get(D - DAY, (None, 0))[0], dl.get(D, (None, 0))[0]
            p = 0.0
            if None in (x0, x1, l0, l1):
                forced[coin] = "missing_price"
            else:
                rx, rl = x1 / x0 - 1, l1 / l0 - 1
                if abs(rx - rl) > SPLIT_GUARD:
                    forced[coin] = "split_guard"
                else:
                    p = (rl - rx) if pos["dir"] > 0 else (rx - rl)
            fund += f / SLOTS
            price += p / SLOTS
            pos["fund"] += f
            pos["price"] += p
        spread = {}
        for coin, m in mk.items():
            if m["fx"].first is not None and m["fl"].first is not None and \
                    max(m["fx"].first, m["fl"].first) <= D - LOOKBACK_D * DAY:
                spread[coin] = (m["fx"].sum(D - LOOKBACK_D * DAY, D) - m["fl"].sum(D - LOOKBACK_D * DAY, D)) \
                    * 365 / LOOKBACK_D
        exited = set()
        for coin in list(held):
            pos, s = held[coin], spread.get(coin)
            reason = forced.get(coin) or ("no_spread" if s is None else ("spread" if s * pos["dir"] < EXIT else None))
            if reason:
                cost += mk[coin]["cost_bp"] / 1e4 / SLOTS
                trades.append({**{k: v for k, v in pos.items()}, "coin": coin, "exit": D, "reason": reason})
                del held[coin]
                exited.add(coin)
        free = SLOTS - len(held)
        cands = []
        for coin, s in spread.items():
            if coin in held or coin in exited or abs(s) < ENTER:
                continue
            (cx, vx), (cl, vl) = px[coin][0].get(D, (None, 0.0)), px[coin][1].get(D, (None, 0.0))
            if cx is None or cl is None or vx < MIN_QUOTE_VOL or vl < MIN_QUOTE_VOL:
                continue
            cands.append((abs(s), coin, s))
        for _, coin, s in sorted(cands, reverse=True)[:max(free, 0)]:
            held[coin] = {"dir": 1 if s > 0 else -1, "entry": D, "spread_in": s, "fund": 0.0, "price": 0.0}
            cost += mk[coin]["cost_bp"] / 1e4 / SLOTS
        rows.append({"D": D, "date": datetime.fromtimestamp(D / 1000, timezone.utc).date().isoformat(),
                     "held": len(held), "funding": fund, "price": price, "cost_1x": cost,
                     **{f"net_{k}x": fund + price - k * cost for k in (1, 2, 3)}})
    for coin, pos in held.items():
        trades.append({**pos, "coin": coin, "exit": None, "reason": "open"})
    return pd.DataFrame(rows), pd.DataFrame(trades)


def stats(daily, span):
    lo, hi = span
    d = daily[(daily["date"] >= lo.isoformat()) & (daily["date"] <= hi.isoformat())]
    out = {"days": int(len(d))}
    if not len(d):
        return out
    for k in (1, 2, 3):
        x = d[f"net_{k}x"].to_numpy(float) - HURDLE / 365
        n, mean, t = newey_west_t(x, NW_LAG)
        cum = np.cumsum(d[f"net_{k}x"].to_numpy(float))
        dd = float(np.min(cum - np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]))
        out[f"{k}x"] = {"net_pct": float(d[f"net_{k}x"].mean() * 365 * 100), "excess_pts": float(mean * 365 * 100),
                        "nw_t": float(t) if t == t else math.nan, "drawdown": dd}
    net = d["net_1x"].to_numpy(float)
    top = np.sort(net)[::-1][:10].sum()
    out.update({"funding_pct": float(d["funding"].mean() * 365 * 100),
                "price_pct": float(d["price"].mean() * 365 * 100),
                "cost_pct": float(-d["cost_1x"].mean() * 365 * 100), "avg_held": float(d["held"].mean()),
                "sd_excess_day": float(np.std(net, ddof=1)) if len(net) > 1 else math.nan,
                "top10_share": float(top / net.sum()) if net.sum() > 0 else math.nan})
    return out


def verdict(a, b):
    if a.get("days", 0) < MIN_A_DAYS:
        return "INCONCLUSIVE", "A below its 60 days"
    a1, a2 = a["1x"], a["2x"]
    a_ok = a1["excess_pts"] >= 3.0 and a1["nw_t"] >= 2.0 and a2["excess_pts"] > 0 and a1["drawdown"] > -0.05
    text = (f"A 1x excess {a1['excess_pts']:+.2f} pts (NW t {a1['nw_t']:.2f}, 2x {a2['excess_pts']:+.2f}, "
            f"dd {a1['drawdown'] * 100:.2f}%)")
    if b.get("days"):
        text += f"; B 1x excess {b['1x']['excess_pts']:+.2f} pts (NW t {b['1x']['nw_t']:.2f})"
    if not a_ok:
        return "NULL", text
    return ("PASS" if b.get("days") and b["1x"]["excess_pts"] > 0 else "PARTIAL"), text


def run(lane=LANE, data=DATA, check=True, pairs=PAIRS, xyz_universe=XYZ_UNIVERSE, last=LAST_D):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    log(f"bar files verified: {verify_bars(data)}")
    mk = load(data, pairs, xyz_universe)
    daily, trades = book(mk, last)
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    daily.to_csv(res / "daily.csv", index=False)
    trades.to_csv(res / "trades.csv", index=False)
    st = {k: stats(daily, v) for k, v in SPANS.items()}
    state, text = verdict(st["A"], st["B"])
    reasons = trades["reason"].value_counts().to_dict() if len(trades) else {}
    dirs = trades["dir"].value_counts().to_dict() if len(trades) else {}
    summary = {"registry": REGISTRY, "state": state, "text": text, "samples": st, "trades": int(len(trades)),
               "exit_reasons": {str(k): int(v) for k, v in reasons.items()},
               "entries_short_xyz": int(dirs.get(1, 0)), "entries_short_lighter": int(dirs.get(-1, 0)),
               "first_day": daily["date"].iloc[0] if len(daily) else None}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    run()
