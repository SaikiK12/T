"""lockcarry_fwd (R405) rule: the locked cash-and-carry of R335 priced on Deribit's live books. Pure functions only;
scripts/forward_lockcarry.py does the I/O. Frozen with the lane's PREREG.

A lock spends N dollars of USDC on the coin's spot book (walking the asks), then shorts the coin's inverse dated future
for Q = (coins held after fees) x F dollars (walking the bids, rounded down to whole contracts) and holds to delivery.
At delivery price P the account holds B + Q (1/P - 1/F) coins, worth B F dollars for any P when Q = B F; the coins are
then sold on the spot book. Nothing about P is forecast: the locked dollars are known at entry, up to contract rounding
and the exit cost.
"""
import math

DAY_MS = 86_400_000
NOTIONAL = 10_000.0          # dollars per paper lock
CAPACITY = 100_000.0         # reported only: does the book also fill this much?
MIN_DAYS = 7.0               # contracts closer to delivery than this are not eligible
DELIVERY_FEE = 0.00025       # assumed delivery fee per side of notional (conservative; to be checked against Deribit)
HURDLES = {"H0": 0.0, "H3": 0.03}   # annual excess over the T-bill needed to lock
PICK = {"H0": "shortest", "H3": "best"}
TBILL_LAG_MS = 2 * DAY_MS    # a FRED DTB3 value dated d is used from d + 2 days on, as in R335


def walk_buy(asks, usd):
    """(coins bought, average price) spending `usd` on asks [(price, coins), ...] best first; None if too thin."""
    left, coins = float(usd), 0.0
    for p, q in asks:
        take = min(left, p * q)
        coins += take / p
        left -= take
        if left <= 1e-9:
            return coins, usd / coins
    return None


def walk_sell_usd(bids, usd):
    """Average price selling `usd` dollars of an inverse future on bids [(price, usd amount), ...]; None if too thin."""
    left, coins = float(usd), 0.0
    for p, a in bids:
        take = min(left, a)
        coins += take / p
        left -= take
        if left <= 1e-9:
            return usd / coins
    return None


def tbill_asof(series, t_ms):
    """The latest DTB3 value (annual fraction) dated at least TBILL_LAG_MS before t_ms; series is [(t_ms, pct)] sorted."""
    known = [v for t, v in series if t <= t_ms - TBILL_LAG_MS]
    return known[-1] / 100.0 if known else None


def offer(spot_bids, spot_asks, fut_bids, contract_usd, expiry_ms, t_ms, spot_fee, fut_fee, usd=NOTIONAL):
    """The lock that `usd` dollars would buy now, or None when a book is too thin. Returns the locked dollars at
    delivery (after every cost) and the annualized locked yield."""
    tau = (expiry_ms - t_ms) / DAY_MS
    if tau <= 0 or not spot_bids or not spot_asks:
        return None
    got = walk_buy(spot_asks, usd)
    if got is None:
        return None
    coins, s_avg = got
    b = coins * (1 - spot_fee)                                   # spot taker fee taken in coin
    f_best = fut_bids[0][0] if fut_bids else None
    if not f_best:
        return None
    q = math.floor(b * f_best / contract_usd) * contract_usd     # whole contracts, never over-hedged at the best bid
    if q <= 0:
        return None
    f_avg = walk_sell_usd(fut_bids, q)
    if f_avg is None:
        return None
    b_net = b - q / f_avg * (fut_fee + DELIVERY_FEE)             # futures taker and delivery fees, in coin
    mid = (spot_bids[0][0] + spot_asks[0][0]) / 2
    exit_cost = spot_fee + (spot_asks[0][0] - spot_bids[0][0]) / 2 / mid   # exit at delivery: fee + entry half-spread
    # value at delivery for the hedged part (q / f_avg coins locked at f_avg) plus the unhedged rounding remainder
    # marked at f_avg: the remainder's exposure is reported separately and settled at the real delivery price.
    locked = (q + (b_net - q / f_avg) * f_avg) * (1 - exit_cost)
    ret = locked / usd - 1
    return {"tau_days": tau, "s_avg": s_avg, "f_avg": f_avg, "coins": b_net, "q_usd": q,
            "unhedged_coins": b_net - q / f_avg, "exit_cost": exit_cost, "locked_usd": locked,
            "locked_ret": ret, "locked_yield": ret * 365.0 / tau}


def settle(lock, delivery_price):
    """Dollars out at delivery for a lock: coins B + Q (1/P - 1/F) sold at P less the frozen exit cost."""
    b, q, f, p = lock["coins"], lock["q_usd"], lock["f_avg"], float(delivery_price)
    coins_end = b + q * (1.0 / p - 1.0 / f)
    usd = coins_end * p * (1 - lock["exit_cost"])
    return {"coins_end": coins_end, "usd_out": usd, "realized_ret": usd / NOTIONAL - 1,
            "diff_bp": (usd - lock["locked_usd"]) / NOTIONAL * 1e4}


def choose(offers, tbill, hurdle, pick):
    """The offer a book locks now: among offers whose excess over the T-bill is at least `hurdle`, the shortest
    (pick 'shortest') or the highest excess (pick 'best'); ties by contract name. None when nothing qualifies."""
    ok = [o for o in offers if o["tau_days"] >= MIN_DAYS and o["locked_yield"] - tbill >= hurdle]
    if not ok:
        return None
    if pick == "shortest":
        return min(ok, key=lambda o: (o["tau_days"], o["contract"]))
    return max(ok, key=lambda o: (o["locked_yield"] - tbill, o["contract"]))
