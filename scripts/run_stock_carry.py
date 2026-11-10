"""R436 stock_carry_v1 (M493, gate 0): stock-perp funding carry across the crypto/TradFi barrier, as set out in
experiments/stock_carry_v1/PREREG.md.

Each Wednesday US close (first NYSE session on or after Wednesday), rank MEXC's 24/7 US-stock and US-ETF perps by
trailing realized funding (sum of settled rates over the lookback, annualized). Short the top K perps whose score
clears tau_in (keep a held name while it clears tau_out = tau_in / 2), and hedge each with the same notional of the
cash stock bought at the official close at an EEA broker. The short receives every settled funding print; the long
stock receives dividends net of 15% US withholding. P&L is marked at each rebalance close; costs are charged on
entries and exits.

Inputs (explicit paths, all hashed in the PREREG `inputs` block):
- data/mexc_tradfi/{funding,klines_1h}/<contract>.parquet and the contract snapshot runs/<id>/contracts.json;
- experiments/stock_carry_v1/inputs/cash_{daily,events}.parquet and cash_meta.json, built before the freeze by
  `build-cash` from raw Yahoo chart responses (receipts with their sha256 in cash_receipts.json);
- data/markets/yahoo/_IRX.parquet (13-week T-bill, the hurdle).
Paper only: no account, no order, no network in `run`.

usage: python scripts/run_stock_carry.py build-cash RAW_DIR | build-manifest | dry-run | run
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LANE = ROOT / "experiments" / "stock_carry_v1"
MEXC = ROOT / "data" / "mexc_tradfi"
CONTRACTS = MEXC / "runs" / "1792671203016652636" / "contracts.json"
INPUTS = LANE / "inputs"
IRX = ROOT / "data" / "markets" / "yahoo" / "_IRX.parquet"

H = 3_600_000
DAY = 86_400_000
US_EXCHANGES = {"NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS"}
TYPES = {"EQUITY", "ETF"}
EXPLICIT = {"BRKB": "BRK-B", "COINBASE": "COIN", "ROBINHOOD": "HOOD", "TESLA": "TSLA", "NVIDIA": "NVDA"}
NON_US = {"ALUMINUM", "NICKEL", "ZINC", "LEAD", "HK0700", "HK0992", "HK1810", "HK50", "JP225", "KOSPI", "KODEX200",
          "CSOPSAMSUNG2L", "CSOPSKHYNIX2L", "LGELECTRONICS", "UNITREE", "NAS100", "SPX500", "US30", "USOIL", "UKOIL",
          "NGAS"}
EARLY_CLOSE = {"2025-07-03", "2025-11-28", "2025-12-24", "2026-11-27", "2026-12-24"}   # 13:00 ET closes

LOOKBACKS = (7, 14)
KS = (3, 5, 10)
TAUS = (0.10, 0.20)
PRIMARY = (14, 5, 0.20)
MULTS = (1, 2, 3)
LEVERAGES = (1.0, 2.0, 3.0)
L_PRIMARY = 2.0
CAPITAL = 10_000.0
PERP_HALF_SPREAD = 5e-4          # per side at 1x (declared haircut; no measured MEXC stock-perp book)
STOCK_HALF_SPREAD = 5e-4         # per side at 1x
API_TAKER = 8e-4                 # MEXC API taker since 2026-06-01 (docs/MEXC_EDGES.md): cost view, not a trial
IBKR_PER_SHARE, IBKR_MIN, IBKR_MAX = 0.005, 1.0, 0.01
WHT = 0.15                       # US withholding on dividends for a French resident with a W-8BEN
PERP_VOL_MIN = 1e5               # trailing 7-day mean daily quote turnover on the perp, USDT
CASH_DV_MIN = 5e6                # trailing 20-session mean dollar volume of the cash stock
RATIO_BAND = (0.95, 1.05)        # perp close / cash close at the entry close
EXCESS_BAR = 0.02
RALLY_LIQ = 0.45                 # a perp high this far above entry liquidates an L = 2 short without top-up
MIN_WEEKS = 26
TOP_DROP = 5
BLOCK = 4
REPS = 10_000
SEED = 436
TBILL_LAG = 2 * DAY
WEEKS_PER_YEAR = 365.0 / 7.0
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)

GUARD = {"on": False}            # set by the dry-run: any file read raises


def _read_parquet(path):
    if GUARD["on"]:
        raise RuntimeError(f"guarded dry-run tried to read {path}")
    return pd.read_parquet(path)


def _read_json(path):
    if GUARD["on"]:
        raise RuntimeError(f"guarded dry-run tried to read {path}")
    return json.loads(Path(path).read_text())


def contracts(path=CONTRACTS):
    return _read_json(path)


def yahoo_symbol(base):
    """Yahoo ticker tried for a MEXC TradFi base, or None for non-US underlyings."""
    if base.endswith("STOCK"):
        b = base[:-5]
        return EXPLICIT.get(b, b)
    if base in NON_US:
        return None
    return EXPLICIT.get(base, base)


def commission(value, price):
    """IBKR Fixed, USD: 0.005 per share, at least 1.00, at most 1% of trade value."""
    if value <= 0:
        return 0.0
    return float(min(max(IBKR_PER_SHARE * value / price, IBKR_MIN), IBKR_MAX * value))


def ny_close_ms(date):
    """UTC ms of the NYSE close on a session date (16:00 ET, 13:00 on listed early closes)."""
    hour = 13 if str(date) in EARLY_CLOSE else 16
    return int(pd.Timestamp(f"{date} {hour:02d}:00", tz="America/New_York").tz_convert("UTC").value // 10**6)


# ---------------------------------------------------------------- inputs built before the freeze
def build_cash(raw_dir, out=INPUTS):
    """Raw Yahoo chart JSON per symbol -> cash_daily.parquet, cash_events.parquet, cash_meta.json, receipts."""
    raw_dir, out = Path(raw_dir), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    daily, events, meta, receipts = [], [], {}, {}
    for p in sorted(raw_dir.glob("*.json")):
        sym, body = p.stem, p.read_bytes()
        receipts[sym] = {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        try:
            res = json.loads(body)["chart"]["result"][0]
        except Exception:
            receipts[sym]["parsed"] = False
            continue
        m = res.get("meta", {})
        meta[sym] = {"currency": m.get("currency"), "exchange": m.get("exchangeName"),
                     "type": m.get("instrumentType"), "tz": m.get("exchangeTimezoneName")}
        receipts[sym]["parsed"] = True
        ts = res.get("timestamp") or []
        if not ts:
            continue
        q = res["indicators"]["quote"][0]
        tz = m.get("exchangeTimezoneName") or "America/New_York"
        dates = pd.to_datetime(ts, unit="s", utc=True).tz_convert(tz).strftime("%Y-%m-%d")
        d = pd.DataFrame({"sym": sym, "date": dates, "close": q.get("close"), "volume": q.get("volume")})
        daily.append(d.dropna(subset=["close"]).drop_duplicates("date", keep="last"))
        for kind, key in (("div", "amount"), ("split", None)):
            for e in ((res.get("events") or {}).get("dividends" if kind == "div" else "splits") or {}).values():
                v = e[key] if key else e["numerator"] / e["denominator"]
                dt = pd.Timestamp(e["date"], unit="s", tz="UTC").tz_convert(tz).strftime("%Y-%m-%d")
                events.append({"sym": sym, "date": dt, "kind": kind, "value": float(v)})
    pd.concat(daily, ignore_index=True).to_parquet(out / "cash_daily.parquet", index=False)
    pd.DataFrame(events, columns=["sym", "date", "kind", "value"]).to_parquet(out / "cash_events.parquet",
                                                                              index=False)
    (out / "cash_meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
    (out / "cash_receipts.json").write_text(json.dumps(receipts, indent=1, sort_keys=True))
    return len(meta), len(receipts)


def build_manifest(mexc=MEXC, out=INPUTS):
    """sha256 of every MEXC TradFi funding and klines_1h file, so the run can refuse a changed file."""
    files = {}
    for kind in ("funding", "klines_1h"):
        for p in sorted((Path(mexc) / kind).glob("*.parquet")):
            files[f"{kind}/{p.name}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "mexc_files.json").write_text(json.dumps(files, indent=0, sort_keys=True))
    return len(files)


def verify_manifest(mexc=MEXC, inputs=INPUTS):
    files = _read_json(Path(inputs) / "mexc_files.json")
    for rel, want in files.items():
        got = hashlib.sha256((Path(mexc) / rel).read_bytes()).hexdigest()
        if got != want:
            raise RuntimeError(f"{rel}: sha256 {got} != manifest {want}")
    return len(files)


# ---------------------------------------------------------------- data model
class Universe:
    """Everything the simulation needs, as plain arrays per contract. Built from files (load) or by hand (tests)."""

    def __init__(self, names, perp, funding, cash, events, sessions, taker, tbill):
        self.names = names              # list of contract symbols
        self.perp = perp                # sym -> DataFrame t(open ms), close, high, amount (sorted)
        self.funding = funding          # sym -> DataFrame t(ms), rate (sorted)
        self.cash = cash                # sym -> DataFrame date(str), close, volume (sorted by date)
        self.events = events            # sym -> {"div": {date: amount}, "split": set(dates)}
        self.sessions = sessions        # sorted list of NYSE session dates (str)
        self.taker = taker              # sym -> web taker fee
        self.tbill = tbill              # DataFrame t(ms), rate (annual fraction)


def load(contracts_path=CONTRACTS, mexc=MEXC, inputs=INPUTS, irx=IRX):
    con = contracts(contracts_path)
    meta = _read_json(Path(inputs) / "cash_meta.json")
    daily = _read_parquet(Path(inputs) / "cash_daily.parquet")
    ev = _read_parquet(Path(inputs) / "cash_events.parquet")
    names, perp, funding, cash, events, taker = [], {}, {}, {}, {}, {}
    by_sym = {s: g.sort_values("date").reset_index(drop=True) for s, g in daily.groupby("sym")}
    for c in sorted(con, key=lambda x: x["symbol"]):
        ys = yahoo_symbol(c["base"])
        m = meta.get(ys) if ys else None
        if not m or m["currency"] != "USD" or m["exchange"] not in US_EXCHANGES or m["type"] not in TYPES:
            continue
        if ys not in by_sym:
            continue
        s = c["symbol"]
        k = _read_parquet(Path(mexc) / "klines_1h" / f"{s}.parquet").sort_values("t").reset_index(drop=True)
        f = _read_parquet(Path(mexc) / "funding" / f"{s}.parquet").sort_values("t").reset_index(drop=True)
        names.append(s)
        perp[s] = k[["t", "close", "high", "amount"]]
        funding[s] = f[["t", "rate"]]
        cash[s] = by_sym[ys][["date", "close", "volume"]]
        e = ev[ev.sym == ys]
        events[s] = {"div": e[e.kind == "div"].groupby("date").value.sum().to_dict(),
                     "split": set(e[e.kind == "split"].date)}
        taker[s] = float(c["taker"])
    spy = by_sym.get("SPY")
    sessions = sorted(spy.date) if spy is not None else sorted(daily.date.unique())
    irxd = _read_parquet(irx)
    tb = pd.DataFrame({"t": irxd.index.astype("int64") // 10**6, "rate": irxd["close"].to_numpy() / 100.0})
    return Universe(names, perp, funding, cash, events, sessions, taker, tb.dropna())


def rebalance_dates(sessions, start, end):
    """First session on or after each Wednesday, per ISO week, within [start, end]."""
    out, seen = [], set()
    for d in sessions:
        ts = pd.Timestamp(d)
        wk = ts.isocalendar()[:2]
        if ts.dayofweek >= 2 and wk not in seen and start <= d <= end:
            seen.add(wk)
            out.append(d)
    return out


class Book:
    """Fast lookups for one contract."""

    def __init__(self, u, s):
        p, f, c = u.perp[s], u.funding[s], u.cash[s]
        self.pt, self.pc, self.ph, self.pa = (p.t.to_numpy(), p.close.to_numpy(), p.high.to_numpy(),
                                              p.amount.to_numpy())
        self.ft, self.fr = f.t.to_numpy(), f.rate.to_numpy()
        self.cd = {d: i for i, d in enumerate(c.date)}
        self.cc, self.cv = c.close.to_numpy(), c.volume.to_numpy()
        self.ev = u.events[s]
        self.first_funding = int(self.ft[0]) if len(self.ft) else None

    def perp_close(self, t):
        """Close of the hourly bar that ends at t (opens at t - 1 h), else NaN."""
        i = np.searchsorted(self.pt, t - H)
        return float(self.pc[i]) if i < len(self.pt) and self.pt[i] == t - H else np.nan

    def bar_close_before(self, t):
        i = np.searchsorted(self.pt, t - H, side="right") - 1
        return float(self.pc[i]) if i >= 0 else np.nan

    def cash_close(self, d):
        i = self.cd.get(d)
        return float(self.cc[i]) if i is not None else np.nan

    def score(self, t, lookback_days):
        lo, hi = np.searchsorted(self.ft, t - lookback_days * DAY, side="right"), np.searchsorted(self.ft, t,
                                                                                                    side="right")
        return float(self.fr[lo:hi].sum() * 365.0 / lookback_days)

    def perp_turnover(self, t):
        lo, hi = np.searchsorted(self.pt, t - 7 * DAY), np.searchsorted(self.pt, t - H, side="right")
        return float(np.nansum(self.pa[lo:hi]) / 7.0)

    def cash_dollar_volume(self, d):
        i = self.cd.get(d)
        if i is None or i < 19:
            return 0.0
        return float(np.nanmean(self.cc[i - 19:i + 1] * self.cv[i - 19:i + 1]))

    def funding_cash(self, q, a, b):
        """Funding received by a short of q contracts-units over settlements in (a, b]."""
        lo, hi = np.searchsorted(self.ft, a, side="right"), np.searchsorted(self.ft, b, side="right")
        return float(sum(self.fr[i] * q * self.bar_close_before(self.ft[i]) for i in range(lo, hi)))

    def max_high(self, a, b):
        lo, hi = np.searchsorted(self.pt, a), np.searchsorted(self.pt, b - H, side="right")
        return float(np.nanmax(self.ph[lo:hi])) if hi > lo else np.nan

    def dividends(self, d0, d1):
        return float(sum(v for d, v in self.ev["div"].items() if d0 < d <= d1))

    def split_in(self, d0, d1):
        return any(d0 < d <= d1 for d in self.ev["split"])


def simulate(u, dates, lookback, k, tau_in, mult=1, leverage=L_PRIMARY, fee_mode="web", books=None):
    """Weekly net P&L (USD, on CAPITAL) and the position log for one cell."""
    books = books or {s: Book(u, s) for s in u.names}
    n_i = CAPITAL * leverage / (leverage + 1.0) / k
    tau_out = tau_in / 2.0
    held, weekly, log_rows = {}, np.zeros(len(dates)), []
    parts = {"funding": 0.0, "perp": 0.0, "stock": 0.0, "div": 0.0, "cost": 0.0}

    def fee(s):
        return (u.taker[s] if fee_mode == "web" else API_TAKER) + PERP_HALF_SPREAD

    for w, d in enumerate(dates):
        t = ny_close_ms(d)
        nxt = dates[w + 1] if w + 1 < len(dates) else None
        px = {s: (b.perp_close(t), b.cash_close(d)) for s, b in books.items()}
        # mark held positions
        for s, h in held.items():
            p, c = px[s]
            if not (np.isfinite(p) and np.isfinite(c)):
                continue
            b = books[s]
            fund = b.funding_cash(h["q"], h["t"], t)
            perp_leg = -h["q"] * (p - h["p"])
            stock_leg = h["qs"] * (c - h["c"])
            div = h["qs"] * b.dividends(h["d"], d) * (1.0 - WHT)
            weekly[w] += fund + perp_leg + stock_leg + div
            for key, v in (("funding", fund), ("perp", perp_leg), ("stock", stock_leg), ("div", div)):
                parts[key] += v
            h["rally"] = max(h["rally"], b.max_high(h["t"], t) / h["p"] - 1.0)   # within-week rise over the mark
            h.update(p=p, c=c, t=t, d=d)

        def eligible(s):
            p, c = px[s]
            b = books[s]
            if not (np.isfinite(p) and np.isfinite(c)) or b.first_funding is None:
                return False
            if b.first_funding > t - lookback * DAY or nxt is None or b.split_in(d, nxt):
                return False
            if not (RATIO_BAND[0] <= p / c <= RATIO_BAND[1]):
                return False
            return b.perp_turnover(t) >= PERP_VOL_MIN and b.cash_dollar_volume(d) >= CASH_DV_MIN

        scores = {s: books[s].score(t, lookback) for s in books}
        keep = {s for s in held if eligible(s) and scores[s] >= tau_out}
        forced = {s for s in held if not all(np.isfinite(px[s]))}        # cannot trade without both prices
        keep |= forced
        exits = [s for s in held if s not in keep]
        cand = sorted((s for s in books if s not in held and eligible(s) and scores[s] >= tau_in),
                      key=lambda s: (-scores[s], s))
        enters = cand[:max(0, k - len(keep))]
        for s in exits:
            h, (p, c) = held.pop(s), px[s]
            cost = mult * (fee(s) * h["q"] * p + commission(h["qs"] * c, c) + STOCK_HALF_SPREAD * h["qs"] * c)
            weekly[w] -= cost
            parts["cost"] -= cost
            log_rows.append({"sym": s, "entry": h["d0"], "exit": d, "rally": h["rally"]})
        if nxt is None:              # last date: close everything still held at this close
            for s in list(held):
                h, (p, c) = held.pop(s), px[s]
                if np.isfinite(p) and np.isfinite(c):
                    cost = mult * (fee(s) * h["q"] * p + commission(h["qs"] * c, c)
                                   + STOCK_HALF_SPREAD * h["qs"] * c)
                    weekly[w] -= cost
                    parts["cost"] -= cost
                log_rows.append({"sym": s, "entry": h["d0"], "exit": d, "rally": h["rally"]})
            break
        for s in enters:
            p, c = px[s]
            q, qs = n_i / p, n_i / c
            cost = mult * (fee(s) * n_i + commission(n_i, c) + STOCK_HALF_SPREAD * n_i)
            weekly[w] -= cost
            parts["cost"] -= cost
            held[s] = {"q": q, "qs": qs, "p": p, "c": c, "t": t, "d": d, "p0": p, "d0": d, "rally": 0.0}
    held_weeks = _held_weeks(log_rows, dates)
    return {"weekly": weekly, "log": log_rows, "parts": parts, "held_weeks": held_weeks}


def _held_weeks(rows, dates):
    pos = {d: i for i, d in enumerate(dates)}
    mark = np.zeros(len(dates), bool)
    for r in rows:
        mark[pos[r["entry"]] + 1:pos[r["exit"]] + 1] = True
    return int(mark.sum())


def tbill_mean(u, dates):
    t = u.tbill.t.to_numpy()
    r = u.tbill.rate.to_numpy()
    vals = [r[np.searchsorted(t, ny_close_ms(d) - TBILL_LAG, side="right") - 1] for d in dates]
    return float(np.mean(vals))


def block_boot(x, rng, block=BLOCK, reps=REPS):
    """Circular block bootstrap of the mean: 2.5% and 97.5% points."""
    n = len(x)
    if n < 2:
        return {"lo": np.nan, "hi": np.nan}
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, -1)[:, :n] % n
    m = x[idx].mean(axis=1)
    return {"lo": float(np.percentile(m, 2.5)), "hi": float(np.percentile(m, 97.5))}


def nw_t(x, lag=4):
    """Newey-West t-statistic of the mean (Bartlett weights)."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return np.nan
    mu = x.mean()
    e = x - mu
    v = e @ e / n
    for j in range(1, lag + 1):
        v += 2 * (1 - j / (lag + 1)) * (e[j:] @ e[:-j]) / n
    return float(mu / np.sqrt(v / n)) if v > 0 else np.nan


def summarize(res, leverage, tb):
    w = res["weekly"]
    capital_ret = w / CAPITAL
    ann = float(capital_ret.mean() * WEEKS_PER_YEAR)
    return {"annual_on_capital": ann, "excess_over_tbill": ann - tb, "weeks": len(w),
            "held_weeks": res["held_weeks"], "positions": len(res["log"]),
            "max_rally": float(max([r["rally"] for r in res["log"]], default=0.0)),
            "net_usd": float(w.sum()), "parts_usd": {k: float(v) for k, v in res["parts"].items()},
            "worst_week_pct": float(capital_ret.min() * 100) if len(w) else np.nan,
            "best_week_pct": float(capital_ret.max() * 100) if len(w) else np.nan}


def verdict(primary_1x, primary_2x, ci, top_drop_sum, held_weeks):
    checks = {"excess_1x_ge_2pts": primary_1x["excess_over_tbill"] >= EXCESS_BAR,
              "excess_2x_gt_0": primary_2x["excess_over_tbill"] > 0,
              "boot_lo_gt_0": ci["lo"] > 0,
              f"net_without_top{TOP_DROP}_gt_0": top_drop_sum > 0,
              "no_l2_liquidation": primary_1x["max_rally"] < RALLY_LIQ}
    if held_weeks < MIN_WEEKS:
        return "INCONCLUSIVE", checks
    if all(checks.values()):
        return "PASS", checks
    if all(v for k, v in checks.items() if k != "no_l2_liquidation"):
        return "PARTIAL", checks
    return "NULL", checks


def run(u, out_dir=None):
    start = min(u.sessions)
    dates = rebalance_dates(u.sessions, start, max(u.sessions))
    books = {s: Book(u, s) for s in u.names}
    # keep only dates whose close is inside the perp data (between the first and the last bar close)
    first_t = min(int(b.pt[0]) for b in books.values()) + H
    last_t = max(int(b.pt[-1]) for b in books.values()) + H
    dates = [d for d in dates if first_t <= ny_close_ms(d) <= last_t]
    tb = tbill_mean(u, dates)
    out = {"dates": [dates[0], dates[-1]], "n_dates": len(dates), "n_contracts": len(u.names), "tbill": tb,
           "cells": [], "primary": {}}
    for lb in LOOKBACKS:
        for k in KS:
            for tau in TAUS:
                row = {"lookback": lb, "k": k, "tau_in": tau}
                for m in MULTS:
                    s = summarize(simulate(u, dates, lb, k, tau, mult=m, books=books), L_PRIMARY, tb)
                    row[f"excess_{m}x"] = s["excess_over_tbill"]
                    row[f"annual_{m}x"] = s["annual_on_capital"]
                    if m == 1:
                        row.update(held_weeks=s["held_weeks"], positions=s["positions"], max_rally=s["max_rally"])
                out["cells"].append(row)
    lb, k, tau = PRIMARY
    r1 = simulate(u, dates, lb, k, tau, mult=1, books=books)
    s1, s2, s3 = (summarize(r1, L_PRIMARY, tb),
                  summarize(simulate(u, dates, lb, k, tau, mult=2, books=books), L_PRIMARY, tb),
                  summarize(simulate(u, dates, lb, k, tau, mult=3, books=books), L_PRIMARY, tb))
    w = r1["weekly"] / CAPITAL
    ci = block_boot(w, np.random.default_rng(SEED))
    top_drop_sum = float(np.sort(w)[:-TOP_DROP].sum()) if len(w) > TOP_DROP else np.nan
    v, checks = verdict(s1, s2, ci, top_drop_sum, r1["held_weeks"])
    views = {"api_fee_1x": summarize(simulate(u, dates, lb, k, tau, mult=1, fee_mode="api", books=books),
                                     L_PRIMARY, tb)}
    for lev in LEVERAGES:
        views[f"L{lev:g}_1x"] = summarize(simulate(u, dates, lb, k, tau, mult=1, leverage=lev, books=books), lev, tb)
    per_name = pd.DataFrame(r1["log"])
    out["primary"] = {"cell": PRIMARY, "1x": s1, "2x": s2, "3x": s3, "boot_ci_weekly_mean": ci,
                      "weekly_mean_pct": float(w.mean() * 100), "nw_t_lag4": nw_t(w),
                      f"sum_without_top{TOP_DROP}_pct": top_drop_sum * 100 if np.isfinite(top_drop_sum) else None,
                      "positive_weeks_share": float((w > 0).mean()), "verdict": v, "checks": checks,
                      "views": views,
                      "names_held": int(per_name.sym.nunique()) if len(per_name) else 0}
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(out["cells"]).to_csv(out_dir / "cells.csv", index=False)
        per_name.to_csv(out_dir / "positions_primary.csv", index=False)
        pd.DataFrame({"date": dates, "net_pct_of_capital": w * 100}).to_csv(out_dir / "weekly_primary.csv",
                                                                             index=False)
        (out_dir / "summary.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ---------------------------------------------------------------- synthetic world (no file is read)
def synthetic(n=12, weeks=40, seed=1):
    rng = np.random.default_rng(seed)
    sessions = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2026-01-05", periods=weeks * 5)]
    t0 = ny_close_ms(sessions[0]) - 30 * DAY
    t1 = ny_close_ms(sessions[-1]) + 2 * H
    hours = np.arange(t0 - (t0 % H), t1, H)
    names, perp, funding, cash, events, taker = [], {}, {}, {}, {}, {}
    for i in range(n):
        s = f"S{i:02d}STOCK_USDT"
        price = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.002, len(hours))))
        perp[s] = pd.DataFrame({"t": hours, "close": price, "high": price * 1.001, "amount": 5e5})
        ft = np.arange(t0 - (t0 % (8 * H)), t1, 8 * H)
        rate = np.full(len(ft), 1e-4 * (i + 1))                   # name i pays (i + 1) bp per 8 h to shorts
        funding[s] = pd.DataFrame({"t": ft, "rate": rate})
        closes = [price[np.searchsorted(hours, ny_close_ms(d) - H)] for d in sessions]
        cash[s] = pd.DataFrame({"date": sessions, "close": closes, "volume": 1e6})
        events[s] = {"div": {}, "split": set()}
        taker[s] = 2e-4
        names.append(s)
    tb = pd.DataFrame({"t": hours[::24], "rate": 0.04})
    return Universe(names, perp, funding, cash, events, sessions, taker, tb)


def dry_run():
    GUARD["on"] = True
    try:
        u = synthetic()
        out = run(u)
    finally:
        GUARD["on"] = False
    p = out["primary"]
    log(f"synthetic: {out['n_dates']} dates, {len(out['cells'])} cells, primary verdict {p['verdict']}, "
        f"annual {p['1x']['annual_on_capital']:.4f}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build-cash", "build-manifest", "dry-run", "run"])
    ap.add_argument("raw", nargs="?")
    a = ap.parse_args()
    if a.cmd == "build-cash":
        log("build-cash", build_cash(a.raw))
        return
    if a.cmd == "build-manifest":
        log("build-manifest", build_manifest())
        return
    if a.cmd == "dry-run":
        dry_run()
        return
    from lab import prereg
    from scripts.run_clockflow import check_inputs
    prereg.verify(LANE / "PREREG.md")
    check_inputs(LANE / "PREREG.md")
    log("inputs verified;", verify_manifest(), "MEXC files match the lane manifest")
    u = load()
    log(f"universe {len(u.names)} contracts")
    out = run(u, LANE / "results")
    p = out["primary"]
    log("primary", p["verdict"], json.dumps(p["checks"]), f"1x excess {p['1x']['excess_over_tbill']:.4f}")


if __name__ == "__main__":
    main()
