"""R410 vrpexec_v1 (M477): the execution rule for R409's weekly short straddle with three cost levers, as set out in
experiments/vrpexec_v1/PREREG.md. Pure functions; the runner and the trade fetcher import them.

- **Strike (point in time):** for Friday D and expiry E = D + 7 d 08:00 UTC, the strike whose call and put both traded
  in the 24 hours before D 08:00 (`data/deribit_trades/<CUR>/flow`), nearest the perp price at D 08:00 (ties: lower).
- **Reference IV:** the mark IV of a leg at instant t, implied from the mark price of its last trade before t (Deribit
  trade records carry the mark price and the index), Black-Scholes with zero rates and forward = that index.
- **Taker sale:** both legs at D 09:00 at reference IV - m x half-spread, priced at the perp; the hedge starts there.
- **Maker sale:** each leg posts at D 08:00 a resting sell at the reference IV + one half-spread, rounded up to the
  tick, and keeps it unchanged. It fills at its limit if a taker buy prints strictly above the limit before D 12:00
  (a trade through the level). A leg still open at 12:00 sells at taker as above, at that time. The hedge starts at
  12:00. Under stress m >= 1 the filled price gives back (m - 1) times its distance from the mid.
- **Hedge:** hourly target 2N(d1) - 1 coins long on the perp at the hedge-start reference IV (mean of the legs).
  Hourly rebalances to the target, or with a band b only when |target - held| > b, to the band's near edge.
  Taker hedges pay the taker fee at the hour close. Maker-first hedges post at the hour close and fill at that price
  if any 1-minute bar in the next hour trades through it (low below for a buy, high above for a sell), paying the
  maker fee; otherwise they cross at the next hour close at the taker fee. The hedge is closed at E at taker.
- **Costs at m (1, 2, 3):** the half-spread on taker sales, the maker give-back, option and delivery fees and hedge
  fees are scaled; funding is not. m = 0 (reported) sells at the mid with no fees.
"""
from math import erf, log, sqrt

import numpy as np

HOUR, DAY, MIN = 3_600_000, 86_400_000, 60_000
YEAR_MS = 365.0 * DAY
HALF_SPREAD = {"BTC": 0.9, "ETH": 1.1}          # vol points, as R409 (costs_measured_20261105.json)
OPT_FEE = 3e-4                                   # Deribit option fee, maker = taker, of the underlying per leg
DEL_FEE = 1.5e-4                                 # delivery, of the underlying, on the leg that finishes in the money
CAP = 0.125                                      # both option fees capped at 12.5% of the leg price (or payoff)
TAKER, MAKER = 5e-4, 2e-4                        # hedge fees: Binance USDT-M VIP0 (Deribit perp lists 3.5 / 1.5 bp)
POST_H, TAKER_H, END_H = 8, 9, 12                # maker post, taker sale, maker deadline (hours after Friday 00:00)
LOOKBACK = 24 * HOUR                             # strike listing window before the post
TICK = ((0.005, 0.0005), (0.0, 0.0001))          # option tick in coin units: above 0.005 -> 0.0005, else 0.0001
HEDGES = {                                       # name -> (band in coins of delta, maker-first)
    "hourly": (0.0, False), "band10": (0.10, False), "band20": (0.20, False),
    "hourly_mk": (0.0, True), "band10_mk": (0.10, True), "band20_mk": (0.20, True),
}
SALES = ("taker", "maker")
PRIMARY = ("maker", "band10_mk")


def ncdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def bs(S, K, tau_y, sig):
    """(call, put, d1) under Black-Scholes with zero rates and forward S (as R409)."""
    if tau_y <= 0 or sig <= 0:
        return max(S - K, 0.0), max(K - S, 0.0), (np.inf if S > K else -np.inf)
    v = sig * sqrt(tau_y)
    d1 = (log(S / K) + 0.5 * v * v) / v
    c = S * ncdf(d1) - K * ncdf(d1 - v)
    return c, c - (S - K), d1


def leg(S, K, tau_y, sig, cp):
    c, p, _ = bs(S, K, tau_y, sig)
    return c if cp == "C" else p


def implied_vol(price, S, K, tau_y, cp, lo=0.005, hi=8.0):
    """Black-Scholes vol (fraction) that prices the leg at `price` (USD), by bisection; None if out of bounds."""
    if not (price > 0 and S > 0 and tau_y > 0):
        return None
    if not leg(S, K, tau_y, lo, cp) < price < leg(S, K, tau_y, hi, cp):
        return None
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if leg(S, K, tau_y, mid, cp) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def tick_up(p):
    """Round a coin price up to Deribit's option tick (sell limits are never below the computed price)."""
    for above, tick in TICK:
        if p > above:
            return float(np.ceil(p / tick - 1e-9) * tick)
    return float(TICK[-1][1])


def pick_strike(flow, D, PH, t0):
    """(strike, call instrument, put instrument) for Friday D, or None. `flow`: flow rows of expiry E with columns t,
    strike, cp, instrument. PH[k] = perp price at t0 + k h."""
    post = D + POST_H * HOUR
    w = flow[(flow.t >= post - LOOKBACK) & (flow.t < post)]
    calls = w[w.cp == "C"].groupby("strike").instrument.first()
    puts = w[w.cp == "P"].groupby("strike").instrument.first()
    both = sorted(set(calls.index) & set(puts.index))
    k = (post - t0) // HOUR
    if not both or not 0 <= k < len(PH) or not np.isfinite(PH[k]):
        return None
    K = min(both, key=lambda s: (abs(s - PH[k]), s))
    return float(K), calls[K], puts[K]


def mark_iv(tr, t, K, E, cp):
    """Reference IV (fraction) of one leg at instant t from its last trade before t; None if there is none."""
    before = tr[tr.timestamp < t]
    if before.empty:
        return None
    r = before.iloc[-1]
    return implied_vol(float(r.mark_price) * float(r.index_price), float(r.index_price), K,
                       (E - float(r.timestamp)) / YEAR_MS, cp)


def taker_leg(tr, t, S, K, E, cp, half, m):
    """USD price and fee of a taker sale of one leg at instant t (perp price S), or None."""
    iv = mark_iv(tr, t, K, E, cp)
    if iv is None:
        return None
    tau = (E - t) / YEAR_MS
    p = leg(S, K, tau, max(iv - m * half / 100.0, 1e-4), cp)
    return {"price": p, "fee": m * min(OPT_FEE * S, CAP * p), "iv_ref": iv, "filled": False, "t": t}


def maker_leg(tr, D, PH, t0, K, E, cp, half, m):
    """One leg of the maker sale: posted at D 08:00, filled on a trade through before 12:00, else taker at 12:00."""
    post, end = D + POST_H * HOUR, D + END_H * HOUR
    S_post, S_end = PH[(post - t0) // HOUR], PH[(end - t0) // HOUR]
    iv = mark_iv(tr, post, K, E, cp)
    if iv is None or not (np.isfinite(S_post) and np.isfinite(S_end)):
        return None
    tau = (E - post) / YEAR_MS
    mid_c = leg(S_post, K, tau, iv, cp) / S_post
    lim_c = tick_up(leg(S_post, K, tau, iv + half / 100.0, cp) / S_post)
    hit = tr[(tr.timestamp > post) & (tr.timestamp < end) & (tr.direction == "buy") & (tr.price > lim_c + 1e-12)]
    if hit.empty:
        out = taker_leg(tr, end, S_end, K, E, cp, half, m)
        if out is not None:
            out.update(iv_post=iv, lim_c=lim_c)
        return out
    f = hit.iloc[0]
    coin = mid_c if m == 0 else lim_c - (m - 1) * (lim_c - mid_c)
    idx = float(f.index_price)
    p = coin * idx
    return {"price": p, "fee": m * min(OPT_FEE * idx, CAP * p), "iv_ref": iv, "iv_post": iv, "lim_c": lim_c,
            "filled": True, "t": int(f.timestamp)}


def hourly_extremes(lo_1m, hi_1m, t0, n_hours):
    """LO[k], HI[k]: lowest low and highest high of the 1-minute bars that open in [t0 + k h, t0 + (k + 1) h)."""
    n = n_hours * 60
    lo = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    m = min(n, len(lo_1m))
    lo[:m], hi[:m] = lo_1m[:m], hi_1m[:m]
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmin(lo.reshape(n_hours, 60), axis=1), np.nanmax(hi.reshape(n_hours, 60), axis=1)


def hedge(path, LO, HI, K, sig, band, maker, m, F_t, F_r, te, E):
    """Hedge P&L, fees, funding and turnover of the long-perp hedge of one short straddle over [te, E].
    path[i] = perp price at te + i h (i = 0..n); LO/HI[i] = extremes of the hour after te + i h."""
    n = len(path) - 1
    held = np.zeros(n)                              # coins held over hour i
    H, fee, traded, pending = 0.0, 0.0, 0.0, None   # pending: a maker order that did not fill in the past hour
    n_post = n_fill = 0
    for i in range(n):
        S = float(path[i])
        if pending is not None:                     # cross the unfilled order at this close, at taker
            fee += m * TAKER * abs(pending - H) * S
            traded += abs(pending - H) * S
            H, pending = pending, None
        _, _, d1 = bs(S, K, (n - i) * HOUR / YEAR_MS, sig)
        tgt = 2.0 * ncdf(d1) - 1.0 if np.isfinite(d1) else (1.0 if d1 > 0 else -1.0)
        gap = tgt - H
        if abs(gap) > band and gap != 0.0:
            want = tgt - np.sign(gap) * band
            if not maker:
                fee += m * TAKER * abs(want - H) * S
                traded += abs(want - H) * S
                H = want
            else:
                n_post += 1
                ext = LO[i] if want > H else HI[i]
                through = np.isfinite(ext) and (ext < S if want > H else ext > S)
                if through:
                    n_fill += 1
                    fee += m * MAKER * abs(want - H) * S
                    traded += abs(want - H) * S
                    H = want
                else:
                    pending = want
        held[i] = H
    ST = float(path[-1])
    if pending is not None:
        fee += m * TAKER * abs(pending - H) * ST
        traded += abs(pending - H) * ST
        H = pending
    fee += m * TAKER * abs(H) * ST                  # close at E
    traded += abs(H) * ST
    pnl = float(np.sum(held * np.diff(path)))
    fund = 0.0
    sel = (F_t > te) & (F_t <= E)
    for ft, fr in zip(F_t[sel], F_r[sel]):
        i = min(int((ft - te) // HOUR) - (1 if (ft - te) % HOUR == 0 else 0), n - 1)
        fund += held[i] * float(path[i + 1]) * fr  # a long hedge pays a positive rate (as R409)
    return {"pnl": pnl, "fee": fee, "funding": fund, "turnover": traded / float(path[0]), "posts": n_post,
            "fills": n_fill}


def week(legs, path, LO, HI, K, sig, hedge_name, m, F_t, F_r, te, E, S0):
    """Net P&L (fraction of S0) of one week from its two sold legs and one hedge scheme."""
    band, maker = HEDGES[hedge_name]
    h = hedge(path, LO, HI, K, sig, band, maker, m, F_t, F_r, te, E)
    ST = float(path[-1])
    payoff = abs(ST - K)
    delivery = m * min(DEL_FEE * ST, CAP * payoff) if payoff > 0 else 0.0
    premium = sum(x["price"] for x in legs)
    opt_fee = sum(x["fee"] for x in legs)
    net = premium - payoff + h["pnl"] - opt_fee - h["fee"] - h["funding"] - delivery
    return {"r": net / S0, "premium": premium / S0, "payoff": payoff / S0, "hedge_pnl": h["pnl"] / S0,
            "opt_fee": opt_fee / S0, "hedge_fee": h["fee"] / S0, "funding": h["funding"] / S0,
            "delivery": delivery / S0, "turnover": h["turnover"], "posts": h["posts"], "fills": h["fills"]}
