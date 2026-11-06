"""The rule of R413 boroslock_fwd: Boros funding locks on paper, priced from the live order book (pure functions only).

A lock: short the venue's perp and sell YU on Boros, walking the order book's bids for NOTIONAL_USD. Its locked APR is
the fill minus Boros's taker and settlement fees. Settlement compares, over the lock's life, the venue's funding with
Boros's floating settlements; with an exact oracle they cancel and the lock earns what it locked.
"""
YEAR_S = 365 * 86400
NOTIONAL_USD = 10_000.0
CAPACITY_USD = 100_000.0
TICK = 1e-4                      # the order book is requested at tickSize 0.0001
MIN_DAYS = 7
HEDGE_RT = 0.0030                # indicative spot + perp round trip (Binance VIP0 taker, 2 x (10 + 5) bp); not measured
MATCH_S = 600                    # a Boros settlement copies the venue event at most 10 minutes before it
BOOKS = {"K0": 0.0, "K1": 0.01}  # carry floor of each paper book (annual fraction)
VENUES = ("BINANCE", "HYPERLIQUID")
COINS = ("BTC", "ETH")


def levels(side):
    """[(apr, yu)] from one side of the order book. ia arrives as tick counts or as decimals; both are read."""
    ia = [float(x) for x in side.get("ia") or []]
    sz = [int(x) / 1e18 for x in side.get("sz") or []]
    scale = TICK if ia and max(abs(x) for x in ia) > 1.0 else 1.0
    return [(a * scale, s) for a, s in zip(ia, sz) if s > 0]


def walk(bids, yu):
    """Size-weighted APR of selling `yu` into the bids (best first), or None if the bids are too thin."""
    left, cost = yu, 0.0
    for apr, s in bids:
        take = min(left, s)
        cost += take * apr
        left -= take
        if left <= 1e-12:
            return cost / yu
    return None


def offer(mk, bids, usd_price, now_s, tbill):
    """The lock NOTIONAL_USD would sell now in market `mk` (dict with maturity, taker, settle), or None."""
    tau = (mk["maturity"] - now_s) / YEAR_S
    if tau * 365 < MIN_DAYS or not usd_price or tbill is None:
        return None
    fill = walk(bids, NOTIONAL_USD / usd_price)
    if fill is None:
        return None
    locked = fill - mk["taker"] - mk["settle"]
    return {"tau_days": tau * 365, "fill_apr": fill, "locked": locked, "excess": locked - tbill,
            "carry": locked - HEDGE_RT / tau - tbill,
            "fills_capacity": walk(bids, CAPACITY_USD / usd_price) is not None}


def choose(offers, floor):
    """The eligible offer with the highest carry, if that carry is at least `floor`."""
    ok = [o for o in offers if o["carry"] >= floor]
    return max(ok, key=lambda o: o["carry"]) if ok else None


def settle(lock, boros, venue):
    """Settle one paper lock. boros: [(ts s, settlementApr)]; venue: [(ts s, rate per period)].
    Returns the funding legs, their difference and the oracle misses over [t0, maturity]."""
    t0, T, period = int(lock["t0"]), int(lock["maturity"]), int(lock["period"])
    tau = (T - t0) / YEAR_S
    V = sum(r for t, r in venue if t0 <= t <= T)
    B = sum(a * period / YEAR_S for t, a in boros if t0 < t <= T + MATCH_S)
    bts = sorted(t for t, _ in boros)
    misses = sum(1 for t, _ in venue if t0 <= t <= T and not any(t <= b <= t + MATCH_S for b in bts))
    fid = (V - B) / tau
    return {"venue_sum": V, "boros_sum": B, "diff_bp": (V - B) * 1e4, "fidelity_apr": fid,
            "realized": float(lock["locked"]) + fid, "misses": misses}


def excess_ann(realized, fee, tbill_paid_ann, tau_days, m=1):
    """Realized lock APR at m x costs (Boros fees, already in `realized` once, and the indicative hedge round trip,
    annualized), minus the T-bill paid over the lock's life."""
    return realized - (m - 1) * fee - m * HEDGE_RT * 365 / tau_days - tbill_paid_ann
