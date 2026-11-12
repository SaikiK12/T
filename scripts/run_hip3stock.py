"""R475 hip3stock_v1, frozen in experiments/hip3stock_v1/PREREG.md: funding carry on trade.xyz's US-stock perps.

Each week, on the last US trading day, rank the xyz perps whose underlying is a US-listed stock by their trailing
28-day mean funding (prints up to that day's 20:00 UTC mark). Short the perp and buy the same stock at a broker in up
to 5 slots: enter at >= 12%/yr, exit below 6%/yr. A slot holds 1/5 of the capital: stock 3/4, perp margin 1/4 (M = 1/3).
Idle capital earns the 13-week bill, so the book's excess over the bill comes from the active slots.

Marks, daily: the stock's Yahoo close (dividends through adjclose) and the open of the perp's 4-hour candle starting
at 20:00 UTC that day (the US close in summer time, an hour before it in winter). Funding: every hourly print
between marks on the short's notional.
A slot is re-split when its margin leaves [M/2, 1.5 M] or the hedge drifts 10%; a perp whose candle high would
breach maintenance (half the initial margin at maximum leverage) is liquidated and its margin is lost.

The book starts on 2026-01-16, 28 days after trade.xyz halved its funding multiplier (2025-12-19), so every trailing
window is in the current regime. Samples: A (weeks ending by 2026-07-22, funding never run through a selection rule)
decides; B (later weeks to 2026-11-06, whose funding the author scanned on 2026-11-12) is reported.

usage: python scripts/run_hip3stock.py [--data data/hip3stock]
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "hip3stock_v1"
DATA = ROOT / "data" / "hip3stock"
REGISTRY = "R475"
HOUR, DAY = 3_600_000, 86_400_000
M = 1 / 3
BASE = {"slots": 5, "enter": 12.0, "exit": 6.0}
VARIANTS = {"decide": BASE, "slots10": {**BASE, "slots": 10}, "enter20": {**BASE, "enter": 20.0, "exit": 10.0}}
LOOKBACK_DAYS, MIN_AGE_DAYS, MIN_PRINT_SHARE = 28, 28, 0.8
STOCK_BP, PERP_BP_GROWTH, PERP_BP_FULL, XFER_BP = 5.0, 2.9, 11.0, 10.0
DRIFT, SPLIT_GUARD, MIN_CORR, WHT = 0.10, 0.15, 0.5, 0.15
BOOK_START, A_END, END = "2026-01-16", "2026-07-22", "2026-11-06"   # funding multiplier 0.5 from 2025-12-19
HURDLE, T_PASS, MIN_ACTIVE_WEEKS, NW_LAG = 2.0, 2.0, 20, 4
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def close_ms(day):
    """16:00 New York on a US trading day, in ms UTC."""
    t = pd.Timestamp(f"{day} 16:00").tz_localize("America/New_York").tz_convert("UTC")
    return int(t.value // 1_000_000)


def day_ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 1_000_000)


class Market:
    """One xyz market and its stock: daily marks, 4-hour highs, traded notional and the funding prints."""

    def __init__(self, ticker, stock, candles, funding, perp_bp, max_lev):
        self.ticker, self.perp_bp, self.maint = ticker, perp_bp, 1 / (2 * max_lev)
        c = candles.drop_duplicates("open_ms").set_index("open_ms").sort_index()
        s = stock.dropna(subset=["close", "adjclose"]).set_index("date")
        days = [d for d in s.index if mark_ms(d) in c.index]
        self.days = pd.Index(days)
        self.close = s.loc[days, "close"].astype(float)
        self.adj = s.loc[days, "adjclose"].astype(float)
        self.perp = pd.Series([float(c.at[mark_ms(d), "open"]) for d in days], index=days)
        self.c_open = c.index.to_numpy(np.int64)
        self.c_high = c["high"].astype(float).to_numpy()
        ntl = np.concatenate([[0.0], np.cumsum(c["volume"].astype(float).to_numpy() * c["close"].astype(float))])
        lo = np.searchsorted(self.c_open, [mark_ms(d) - DAY for d in days], side="left")
        hi = np.searchsorted(self.c_open, [mark_ms(d) for d in days], side="left")
        self.ntl = pd.Series(ntl[hi] - ntl[lo], index=days)
        self.f_t = funding["time"].to_numpy(np.int64)
        self.f_r = funding["fundingRate"].astype(float).to_numpy()
        self.f_cum = np.concatenate([[0.0], np.cumsum(self.f_r)])
        self.first = int(self.f_t[0]) if len(self.f_t) else None

    def trailing(self, t_ms):
        """Mean hourly funding over (t - 28 d, t], annualized in %; NaN if too few prints or too young."""
        if self.first is None or self.first > t_ms - MIN_AGE_DAYS * DAY:
            return math.nan
        lo = np.searchsorted(self.f_t, t_ms - LOOKBACK_DAYS * DAY, side="right")
        hi = np.searchsorted(self.f_t, t_ms, side="right")
        n = hi - lo
        if n < MIN_PRINT_SHARE * LOOKBACK_DAYS * 24:
            return math.nan
        return (self.f_cum[hi] - self.f_cum[lo]) / n * 8760 * 100

    def funding_sum(self, a_ms, b_ms):
        lo = np.searchsorted(self.f_t, a_ms, side="right")
        hi = np.searchsorted(self.f_t, b_ms, side="right")
        return float(self.f_cum[hi] - self.f_cum[lo])

    def high(self, a_ms, b_ms):
        """Highest perp price in candles opened in [a, b)."""
        lo = np.searchsorted(self.c_open, a_ms, side="left")
        hi = np.searchsorted(self.c_open, b_ms, side="left")
        return float(self.c_high[lo:hi].max()) if hi > lo else math.nan

    def identity_ok(self):
        """Ticker check over the last 60 marks: median perp/close within 3% and daily log returns correlated."""
        r = (self.perp / self.close).tail(60)
        a, b = np.log(self.perp).diff().tail(59), np.log(self.close).diff().tail(59)
        corr = float(np.corrcoef(a, b)[0, 1]) if len(a) >= 19 and a.std() > 0 and b.std() > 0 else 1.0
        return len(r) >= 20 and 0.97 <= float(r.median()) <= 1.03 and corr >= MIN_CORR


def mark_ms(day):
    """The perp mark of a day: the open of the 4-hour candle starting at 20:00 UTC."""
    return day_ms(day) + 20 * HOUR


def open_slot(mk, day, cap):
    v = cap / (1 + M)
    p, x = mk.adj[day], mk.perp[day]
    cost = (STOCK_BP * v + mk.perp_bp * v + XFER_BP * (cap - v)) / 1e4
    return {"q": v / p, "u": v / x, "usdc": cap - v, "cap": cap, "opened": day}, cost


def close_cost(mk, day, s):
    v, n = s["q"] * mk.adj[day], s["u"] * mk.perp[day]
    return (STOCK_BP * v + mk.perp_bp * n + XFER_BP * max(s["usdc"], 0.0)) / 1e4


def book(markets, bill, params, start, end):
    """Run the weekly-selection book; returns daily rows (portfolio) and a trade log."""
    cal = sorted({d for mk in markets.values() for d in mk.days if start <= d <= end})
    wk = pd.Series(pd.to_datetime(cal)).dt.strftime("%G-W%V").to_numpy()
    decide = {cal[i] for i in range(len(cal)) if i == len(cal) - 1 or wk[i + 1] != wk[i]}
    cap = 1.0 / params["slots"]
    held, rows, trades = {}, [], []
    for day in cal:
        fund = price = cost = billd = div = 0.0
        liq = flag = resplit = 0
        r_bill = float(bill[bill.index <= day].iloc[-1]) / 100 if (bill.index <= day).any() else 0.0
        for tick in list(held):
            mk, s = markets[tick], held[tick]
            if day not in mk.adj.index:
                continue
            last = s["last"]
            x0, x1, a0, a1 = mk.perp[last], mk.perp[day], mk.adj[last], mk.adj[day]
            dv = s["q"] * a0 * (a1 / a0 - mk.close[day] / mk.close[last])
            billd += s["cap"] * s["r"] * (day_ms(day) - day_ms(last)) / DAY / 365
            f = mk.funding_sum(mark_ms(last), mark_ms(day)) * s["u"] * x0
            sp, pp = s["q"] * (a1 - a0), -s["u"] * (x1 - x0)
            broke = abs((x1 / x0 - 1) - (a1 / a0 - 1)) > SPLIT_GUARD
            if broke:
                sp = pp = dv = 0.0
                s["q"], s["u"] = s["q"] * a0 / a1, s["u"] * x0 / x1
                flag += 1
            h = mk.high(mark_ms(last), mark_ms(day))
            if not broke and np.isfinite(h) and h > x0 and s["usdc"] - s["u"] * (h - x0) < mk.maint * s["u"] * h:
                v = s["q"] * a1
                c = STOCK_BP * v / 1e4
                fund += f
                price += sp - s["usdc"] - f
                cost += c
                liq += 1
                div += dv
                trades.append({"ticker": tick, "opened": s["opened"], "closed": day, "why": "liquidated",
                               "ntl_usd": float(mk.ntl[s["opened"]:day].median())})
                del held[tick]
                continue
            s["usdc"] += pp + f
            fund, price, div = fund + f, price + sp + pp, div + dv
            v, n = s["q"] * a1, s["u"] * x1
            m = s["usdc"] / n
            if abs(n - v) / v > DRIFT or not (M / 2 <= m <= 1.5 * M):
                e = v + s["usdc"]
                tgt = e / (1 + M)
                c = (STOCK_BP * abs(tgt - v) + mk.perp_bp * abs(tgt - n) + XFER_BP * abs(e - tgt - s["usdc"])) / 1e4
                s["q"], s["u"], s["usdc"] = tgt / a1, tgt / x1, e - tgt - c
                cost += c
                resplit += 1
            s["last"], s["r"] = day, r_bill
        if day in decide:
            t = mark_ms(day)
            score = {k: mk.trailing(t) for k, mk in markets.items() if day in mk.adj.index}
            for tick in list(held):
                mk, s = markets[tick], held[tick]
                gone = day not in mk.adj.index and mk.days[-1] < day   # no mark left: the perp or stock is gone
                if gone or (day in mk.adj.index and not (score.get(tick, math.nan) >= params["exit"])):
                    cost += close_cost(mk, s["last"], s)
                    trades.append({"ticker": tick, "opened": s["opened"], "closed": s["last"], "why": "gone" if gone
                                   else "exit", "ntl_usd": float(mk.ntl[s["opened"]:day].median())})
                    del held[tick]
            ratio_ok = {k: 0.9 <= markets[k].perp[day] / markets[k].close[day] <= 1.1 for k in score}
            cand = sorted((k for k, v in score.items() if v >= params["enter"] and k not in held and ratio_ok[k]),
                          key=lambda k: -score[k])
            for tick in cand[:max(params["slots"] - len(held), 0)]:
                s, c = open_slot(markets[tick], day, cap)
                s.update({"last": day, "r": r_bill})
                held[tick] = s
                cost += c
        if day == cal[-1]:
            for tick in list(held):
                mk, s = markets[tick], held[tick]
                cost += close_cost(mk, s["last"], s)
                trades.append({"ticker": tick, "opened": s["opened"], "closed": s["last"], "why": "end",
                               "ntl_usd": float(mk.ntl[s["opened"]:day].median())})
                del held[tick]
        rows.append({"date": day, "fund": fund, "price": price, "div": div, "cost": cost, "bill": billd,
                     "slots": len(held),
                     "liquidations": liq, "split_flags": flag, "resplits": resplit,
                     "excess": fund + price - cost - billd})
    return pd.DataFrame(rows), pd.DataFrame(trades, columns=["ticker", "opened", "closed", "why", "ntl_usd"])


def weekly(daily):
    d = daily.assign(wk=pd.to_datetime(daily["date"]).dt.strftime("%G-W%V"))
    g = d.groupby("wk", sort=True)
    out = g[["fund", "price", "div", "cost", "bill", "excess", "liquidations", "split_flags", "resplits"]].sum()
    out["last"] = g["date"].max()
    out["slots"] = g["slots"].mean()
    return out.reset_index()


def stats(wk, trades):
    if len(wk) < 2:
        return {"weeks": int(len(wk))}
    n, mu, t = newey_west_t(wk["excess"].to_numpy(float), NW_LAG)
    c = wk["cost"].mean()
    cum = wk["excess"].cumsum().to_numpy()
    hold = (pd.to_datetime(trades["closed"]) - pd.to_datetime(trades["opened"])).dt.days if len(trades) else []
    return {"weeks": int(n), "active_weeks": int((wk["slots"] > 0).sum()), "first": wk["last"].iloc[0],
            "last": wk["last"].iloc[-1], "ann_excess_pts": float(mu * 52 * 100), "nw_t": float(t),
            "ann_excess_2x_pts": float((mu - c) * 52 * 100), "ann_excess_3x_pts": float((mu - 2 * c) * 52 * 100),
            "ann_carry_only_pts": float((wk["excess"] - wk["price"]).mean() * 52 * 100),
            "ann_funding_pts": float(wk["fund"].mean() * 52 * 100),
            "ann_price_pts": float(wk["price"].mean() * 52 * 100),
            "ann_div_pts": float(wk["div"].mean() * 52 * 100),
            "ann_excess_wht15_pts": float((wk["excess"] - WHT * wk["div"]).mean() * 52 * 100),
            "ann_cost_pts": float(c * 52 * 100), "mean_slots": float(wk["slots"].mean()),
            "liquidations": int(wk["liquidations"].sum()), "split_flags": int(wk["split_flags"].sum()),
            "resplits": int(wk["resplits"].sum()), "max_dd_pts": float(np.max(np.maximum.accumulate(cum) - cum) * 100),
            "trades": int(len(trades)), "names": int(trades["ticker"].nunique()) if len(trades) else 0,
            "mean_hold_days": float(np.mean(hold)) if len(trades) else math.nan,
            "median_trade_ntl_usd": float(trades["ntl_usd"].median()) if len(trades) else math.nan}


def verdict(a):
    if a.get("active_weeks", 0) < MIN_ACTIVE_WEEKS:
        return "INCONCLUSIVE", f"A has {a.get('active_weeks', 0)} active weeks < {MIN_ACTIVE_WEEKS}"
    text = (f"A {a['weeks']} weeks: excess {a['ann_excess_pts']:+.2f} pts/yr (NW t {a['nw_t']:.2f}), 2x "
            f"{a['ann_excess_2x_pts']:+.2f}, 3x {a['ann_excess_3x_pts']:+.2f}; funding {a['ann_funding_pts']:+.2f}, "
            f"price {a['ann_price_pts']:+.2f}, cost {a['ann_cost_pts']:.2f}; {a['mean_slots']:.1f} slots")
    if a["ann_excess_pts"] >= HURDLE and a["nw_t"] >= T_PASS and a["ann_excess_2x_pts"] > 0:
        return "PASS", text
    return ("PARTIAL" if a["ann_excess_pts"] > 0 else "NULL"), text


def verify_data(data):
    man = json.loads((data / "manifest.json").read_text())
    for rel, meta in man["files"].items():
        if prereg.sha256_file(data / rel) != meta["sha256"]:
            raise SystemExit(f"manifest mismatch: {rel}")
    return len(man["files"])


def load(data):
    uni = pd.read_csv(data / "universe.csv")
    uni = uni[uni["equity"] == 1]
    markets, dropped = {}, []
    for _, r in uni.iterrows():
        t = r["ticker"]
        fpath, cpath = data / "xyz" / f"{t}_funding.csv", data / "xyz" / f"{t}_4h.csv"
        if not (fpath.exists() and cpath.exists() and (data / "yahoo" / f"{t}.parquet").exists()):
            dropped.append((t, "missing file"))
            continue
        f, c = pd.read_csv(fpath), pd.read_csv(cpath)
        if not len(f) or not len(c):
            dropped.append((t, "no funding or candles"))
            continue
        bp = PERP_BP_GROWTH if str(r["growth"]) == "enabled" else PERP_BP_FULL
        mk = Market(t, pd.read_parquet(data / "yahoo" / f"{t}.parquet"), c, f, bp, float(r["max_lev"]))
        if not mk.identity_ok():
            dropped.append((t, "identity"))
            continue
        markets[t] = mk
    bill = pd.read_parquet(data / "yahoo" / "IRX.parquet").set_index("date")["close"].sort_index()
    return markets, bill, dropped


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    log(f"data files verified: {verify_data(data)}")
    markets, bill, dropped = load(data)
    log(f"markets {len(markets)}; dropped {len(dropped)}: {dropped}")
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    first = max(min(d for mk in markets.values() for d in mk.days), BOOK_START)
    out = {"registry": REGISTRY, "markets": sorted(markets), "dropped": dropped, "variants": {}}
    for name, params in VARIANTS.items():
        daily, trades = book(markets, bill, params, first, END)
        wk = weekly(daily)
        a, b = wk[wk["last"] <= A_END], wk[wk["last"] > A_END]
        ta = trades[trades["closed"] <= A_END]
        tb = trades[trades["closed"] > A_END]
        out["variants"][name] = {"params": params, "A": stats(a, ta), "B": stats(b, tb), "all": stats(wk, trades)}
        daily.to_csv(res / f"daily_{name}.csv", index=False)
        wk.to_csv(res / f"weekly_{name}.csv", index=False)
        trades.to_csv(res / f"trades_{name}.csv", index=False)
    state, text = verdict(out["variants"]["decide"]["A"])
    out.update({"state": state, "text": text})
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    log(state, text)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args()
    run(data=Path(a.data))


if __name__ == "__main__":
    main()
