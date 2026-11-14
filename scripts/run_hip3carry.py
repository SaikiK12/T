"""R479 hip3carry_fwd, frozen in experiments/hip3carry_fwd/PREREG.md: R475-R477's funding carry, forward from
2026-11-16, read twice (futility after 13 weeks, final after 26).

Two books, each R475's frozen weekly rule (`scripts/run_hip3stock.py`: 5 slots of 1/5 of capital, enter at >= 12%/yr
trailing 28-day funding, exit below 6%/yr, M = 1/3, re-splits, liquidation on candle highs, split guard, bill on
slot capital, idle capital at the bill):
- S (stocks): every HIP-3 dex's US-stock perps (xyz, Paragon, EntropyIO, any other), short the perp and hold the
  stock. Marks at 16:00 New York: the stock's close and the open of the perp's 1-hour candle starting at 16:00.
  Changes from R475, all stated in the PREREG:
  - identity: the NaN in R475's check is dropped before correlating (posthoc/identity_nan.py of hip3stock_v1);
  - capacity: a name is eligible (and stays held) only while the median 24-hour perp notional of its last 7 marks is
    at least $150,000, so a $10,000 book's slot ($1,500 of perp) is at most 1% of a day's volume;
  - fee: each market's taker fee from its own growth mode and deployer fee scale (Hyperliquid's HIP-3 formula, as
    in R453) plus 2 bp of slippage; R475's 2.9 and 11 bp are this formula for xyz's settings.
- S_nofloor (reported only): S without the capacity floor.
- T (twins): R477's pairs, R477's book (`scripts/run_xyztwin.py`, 16:00 UTC marks on 4-hour candles, scaled twin),
  with the same NaN fix.
Each book is also run at measured costs: the fee from the recorded fee settings and the slippage of a $5,000 market
order from the hourly book snapshots (claude/xyz-books-data: books/ for xyz, hip3/books/ for Paragon and io).
The decision is the carry: funding + 85% of dividends - cost - bill, on slot capital. The total (with price) is
reported and must be positive for a PASS.

usage: python scripts/run_hip3carry.py --read futility|final [--books DIR] | --auto [--books DIR]
"""
import argparse
import contextlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
import run_hip3stock as hs  # noqa: E402  (frozen in R475)
import run_xyztwin as xt  # noqa: E402  (frozen in R477)
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "hip3carry_fwd"
DATA = ROOT / "data" / "hip3carry_fwd"
REGISTRY = "R479"
START = "2026-11-16"
READS = {"futility": {"last": "2027-02-12", "after": "2027-02-13", "min_active": 6},
         "final": {"last": "2027-05-14", "after": "2027-05-15", "min_active": 13}}
BASE_TAKER_BP, SLIP_BP, MEAS_SIZE, THIN_BP = 4.5, 2.0, 5000, 25.0
MIN_NTL_USD, NTL_MARKS = 150_000.0, 7
HURDLE, T_PASS, NW_LAG, WHT = 2.0, 2.0, 4, hs.WHT
STRESS = 0.05            # adverse settlement move on the perp leg of every trade that ended with its market gone
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def taker_fee_bp(growth, fee_scale):
    """One-way tier-0 taker fee of a HIP-3 perp in bp (R453's `taker_fee`)."""
    s = 1.0 if fee_scale is None or (isinstance(fee_scale, float) and math.isnan(fee_scale)) or fee_scale == "" \
        else float(fee_scale)
    scale = s + 1 if s < 1 else 2 * s
    return BASE_TAKER_BP * scale * (0.1 if str(growth).strip().lower() == "enabled" else 1.0)


@contextlib.contextmanager
def ny_marks():
    """R475's Market and book read the module's mark_ms at call time; point it at 16:00 New York."""
    old, hs.mark_ms = hs.mark_ms, hs.close_ms
    try:
        yield
    finally:
        hs.mark_ms = old


def corr_ok(perp, close, n=60):
    """Daily log returns over the last n marks, NaN dropped, correlated at >= R475's 0.5 (None if too short)."""
    a, b = np.log(perp).diff().tail(n - 1), np.log(close).diff().tail(n - 1)
    ok = a.notna() & b.notna()
    a, b = a[ok], b[ok]
    if len(a) < 19 or a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1]) >= hs.MIN_CORR


class StockMarket(hs.Market):
    """R475's Market with the identity NaN dropped and the capacity floor on eligibility."""

    def __init__(self, ticker, stock, candles, funding, perp_bp, max_lev, min_ntl=MIN_NTL_USD):
        super().__init__(ticker, stock, candles, funding, perp_bp, max_lev)
        self.min_ntl = min_ntl
        self.at = {hs.mark_ms(d): i for i, d in enumerate(self.days)}

    def identity_ok(self):
        r = (self.perp / self.close).tail(60)
        c = corr_ok(self.perp, self.close)
        return len(r) >= 20 and 0.97 <= float(r.median()) <= 1.03 and c is not False

    def liquid(self, i):
        return float(self.ntl.iloc[max(0, i - NTL_MARKS + 1): i + 1].median()) >= self.min_ntl

    def trailing(self, t_ms):
        i = self.at.get(t_ms)
        if i is not None and not self.liquid(i):
            return math.nan
        return super().trailing(t_ms)


def twin_correlated(mk):
    return corr_ok(mk.perp, mk.close, xt.ID_MARKS) is True


def load_stocks(src, min_ntl=MIN_NTL_USD):
    """S's markets from <src>/stocks (call inside ny_marks); min_ntl 0 drops the capacity floor."""
    d = Path(src) / "stocks"
    uni = pd.read_csv(d / "universe.csv")
    markets, dropped = {}, []
    for _, r in uni[uni["equity"] == 1].iterrows():
        t = r["ticker"]
        f, c = pd.read_csv(d / "xyz" / f"{t}_funding.csv"), pd.read_csv(d / "xyz" / f"{t}_1h.csv")
        if not len(f) or not len(c):
            dropped.append((t, "no funding or candles"))
            continue
        bp = taker_fee_bp(r["growth"] if pd.notna(r["growth"]) else "", r.get("fee_scale")) + SLIP_BP
        mk = StockMarket(t, pd.read_parquet(d / "yahoo" / f"{r['stock']}.parquet"), c, f, bp, float(r["max_lev"]),
                         min_ntl)
        if len(mk.days) < 20 or not mk.identity_ok():
            dropped.append((t, "identity" if len(mk.days) >= 20 else "fewer than 20 marks"))
            continue
        mk.dex = r["dex"]
        markets[t] = mk
    bill = pd.read_parquet(d / "yahoo" / "IRX.parquet").set_index("date")["close"].sort_index()
    return markets, bill, dropped


def load_twins(src):
    """T's markets from <src>/twin, by R477's loader with the NaN fix (call inside xt.london_marks)."""
    old, xt.correlated = xt.correlated, twin_correlated
    try:
        markets, bill, dropped, _ = xt.load(Path(src) / "twin")
    finally:
        xt.correlated = old
    for mk in markets.values():
        mk.dex = "xyz"
    return markets, bill, dropped


def measured(books, first, last, size=MEAS_SIZE):
    """{ticker: (fee bp, slippage bp, snapshots)} from the recorded books and fee settings in [first, last].
    Tickers: <dex>_<stock> (S) and the bare xyz name (T). Slippage: the median over snapshots of the mean of the
    buy and sell cost of a `size` market order; THIN_BP where no snapshot had that depth."""
    out = {}
    if books is None:
        return out
    books = Path(books)
    for sub in (books, books / "hip3"):
        bf = sorted(p for p in (sub / "books").glob("*.csv") if first <= p.stem <= last)
        mf = sorted(p for p in (sub / "markets").glob("*.csv") if first <= p.stem <= last)
        if not bf:
            continue
        b = pd.concat([pd.read_csv(p) for p in bf], ignore_index=True)
        b["slip"] = (b[f"buy_{size}_bp"] + b[f"sell_{size}_bp"]) / 2
        m = pd.concat([pd.read_csv(p, dtype={"day": str}) for p in mf], ignore_index=True) if mf else None
        for coin, g in b.groupby("coin"):
            fee = math.nan
            if m is not None and (m["coin"] == coin).any():
                mm = m[m["coin"] == coin]
                fee = float(np.median([taker_fee_bp(gm if pd.notna(gm) else "", fs) for gm, fs in
                                       zip(mm["growthMode"], mm["deployerFeeScale"])]))
            s = g["slip"].dropna()
            slip = float(s.median()) if len(s) else THIN_BP
            dex, name = coin.split(":", 1)
            out[f"{dex}_{name}"] = (fee, slip, int(len(g)))
            if dex == "xyz":
                out[name] = (fee, slip, int(len(g)))
    return out


def apply_measured(markets, meas):
    """Set each market's perp cost to fee + measured slippage; returns the share of markets with a measurement."""
    n = 0
    for t, mk in markets.items():
        if t in meas:
            fee, slip, _ = meas[t]
            fee = fee if np.isfinite(fee) else mk.perp_bp - SLIP_BP
            mk.perp_bp = fee + max(slip, 0.0)
            n += 1
    return n / len(markets) if markets else math.nan


def carry_stats(wk, trades):
    """R475's stats plus the carry (funding + 85% of dividends - cost - bill) and the total net of withholding."""
    st = hs.stats(wk, trades)
    if len(wk) < 2:
        return st
    c = (wk["excess"] - wk["price"] + (1 - WHT) * wk["div"]).to_numpy(float)
    tot = (wk["excess"] - WHT * wk["div"]).to_numpy(float)
    _, mu, t = newey_west_t(c, NW_LAG)
    cost = float(wk["cost"].mean())
    gone = int((trades["why"] == "gone").sum()) if len(trades) else 0
    slot_perp = 1 / hs.BASE["slots"] / (1 + hs.M)
    st.update({"carry_pts": float(mu * 5200), "carry_t": float(t), "carry_2x_pts": float((mu - cost) * 5200),
               "carry_3x_pts": float((mu - 2 * cost) * 5200), "total_pts": float(tot.mean() * 5200),
               "total_t": float(newey_west_t(tot, NW_LAG)[2]), "weekly_sd_carry_pct": float(np.std(c, ddof=1) * 100),
               "weekly_sd_total_pct": float(np.std(tot, ddof=1) * 100), "gone_exits": gone,
               "gone_stress_pts": float(-STRESS * slot_perp * gone / len(wk) * 5200)})
    return st


def verdict(read, st, st_meas):
    need = READS[read]["min_active"]
    if st.get("active_weeks", 0) < need:
        return "INCONCLUSIVE", f"{st.get('active_weeks', 0)} weeks with a slot held < {need}"
    text = (f"{st['weeks']} weeks ({st['active_weeks']} active): carry {st['carry_pts']:+.2f} pts/yr (NW t "
            f"{st['carry_t']:.2f}), 2x {st['carry_2x_pts']:+.2f}; total {st['total_pts']:+.2f} (t {st['total_t']:.2f}), "
            f"measured-cost total {st_meas.get('total_pts', math.nan):+.2f}; {st['mean_slots']:.1f} slots, "
            f"{st['trades']} trades, {st['liquidations']} liquidations")
    if read == "futility":
        return ("NULL" if st["carry_pts"] < 0 else "CONTINUE"), text
    if (st["carry_pts"] >= HURDLE and st["carry_t"] >= T_PASS and st["carry_2x_pts"] > 0 and st["total_pts"] > 0
            and st_meas.get("total_pts", -1.0) > 0):
        return "PASS", text
    return ("PARTIAL" if st["carry_pts"] > 0 else "NULL"), text


def run_book(markets, bill, last, meas, res, name):
    out = {"markets": len(markets), "by_dex": pd.Series([mk.dex for mk in markets.values()], dtype=object)
           .value_counts().to_dict()}
    weeks = {}
    if not markets:
        out.update({"assumed": {"weeks": 0}, "measured": {"weeks": 0}, "measured_share": math.nan,
                    "trades_by_dex": {}})
        return out, pd.DataFrame()
    for label in ("assumed", "measured"):
        if label == "measured":
            out["measured_share"] = apply_measured(markets, meas)
        daily, trades = hs.book(markets, bill, hs.BASE, START, last)
        wk = hs.weekly(daily)
        out[label] = carry_stats(wk, trades)
        weeks[label] = wk
        daily.to_csv(res / f"{name}_daily_{label}.csv", index=False)
        wk.to_csv(res / f"{name}_weekly_{label}.csv", index=False)
        trades.to_csv(res / f"{name}_trades_{label}.csv", index=False)
        if label == "assumed":
            out["trades_by_dex"] = (trades["ticker"].str.split("_").str[0].value_counts().to_dict()
                                    if len(trades) and name.startswith("S") else {"xyz": int(len(trades))})
    return out, weeks["assumed"]


def combined(ws, wt):
    """Half the capital in each book: weekly carry and total, 0 where a book has no row."""
    cols = ["fund", "price", "div", "cost", "bill", "excess", "liquidations", "split_flags", "resplits", "slots"]
    s = ws.set_index("wk")[cols] * 0.5
    t = wt.set_index("wk")[cols] * 0.5
    c = s.add(t, fill_value=0.0)
    c["last"] = pd.concat([ws.set_index("wk")["last"], wt.set_index("wk")["last"]]).groupby(level=0).max()
    c = c.reset_index().sort_values("wk")
    return carry_stats(c, pd.DataFrame(columns=["ticker", "opened", "closed", "why", "ntl_usd"]))


def due(read, now):
    return now >= datetime.strptime(READS[read]["after"], "%Y-%m-%d").replace(tzinfo=timezone.utc)


def run(read, lane=LANE, data=DATA, books=None, check=True, now=None, fetcher="default"):
    cfg, res = READS[read], lane / "results" / read
    now = now or datetime.now(timezone.utc)
    if (res / "summary.json").exists():
        log(f"{read}: already read; nothing to do")
        return None
    if not due(read, now):
        log(f"{read}: refused before {cfg['after']} 00:00 UTC")
        return None
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    src = data / read
    if fetcher == "default":
        from fetch_hip3carry import fetch
        fetch(cfg["after"], src)
    elif fetcher is not None:
        fetcher(cfg["after"], src)
    log(f"{read}: data files verified: {hs.verify_data(src)}")
    res.mkdir(parents=True, exist_ok=True)
    meas = measured(books, START, cfg["last"])
    log(f"measured cost rows for {len(meas)} tickers")
    with ny_marks():
        sm, sbill, sdrop = load_stocks(src)
        log(f"S: markets {len(sm)}; dropped {len(sdrop)}")
        s_out, s_wk = run_book(sm, sbill, cfg["last"], meas, res, "S")
        s0, s0bill, _ = load_stocks(src, min_ntl=0.0)
        s0_out, _ = run_book(s0, s0bill, cfg["last"], meas, res, "S_nofloor")
    with xt.london_marks():
        tm, tbill, tdrop = load_twins(src)
        log(f"T: markets {len(tm)}; dropped {len(tdrop)}: {tdrop}")
        t_out, t_wk = run_book(tm, tbill, cfg["last"], meas, res, "T")
    summary = {"registry": REGISTRY, "read": read, "first": START, "last": cfg["last"],
               "S": {**s_out, "dropped": sdrop}, "S_nofloor": s0_out, "T": {**t_out, "dropped": tdrop},
               "combined": combined(s_wk, t_wk) if len(s_wk) and len(t_wk) else {}}
    fut = res.parent / "futility" / "summary.json"
    stopped = json.loads(fut.read_text()) if read == "final" and fut.exists() else {}
    for b in ("S", "T"):
        state, text = verdict(read, summary[b]["assumed"], summary[b]["measured"])
        if stopped.get(b, {}).get("state") == "NULL":
            state, text = "NULL", "stopped at the futility read; final numbers reported: " + text
        summary[b].update({"state": state, "text": text})
        log(read, b, state, text)
    (res / "manifest.json").write_text((src / "manifest.json").read_text())
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    return {b: summary[b]["state"] for b in ("S", "T")}


def auto(lane=LANE, data=DATA, books=None, now=None):
    """The workflow's entry: the futility read, then the final read (a book stopped at futility stays stopped)."""
    now = now or datetime.now(timezone.utc)
    run("futility", lane, data, books, now=now)
    run("final", lane, data, books, now=now)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--read", choices=sorted(READS))
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--books", default=None, help="checkout of claude/xyz-books-data (measured costs)")
    a = ap.parse_args()
    if a.auto:
        auto(books=a.books)
    else:
        run(a.read, books=a.books)


if __name__ == "__main__":
    main()
