"""R364 settlelit_fwd's rule, accounting and decision: constants and pure functions, fixed at the freeze.

scripts/forward_settlelit.py (websockets, journals, scheduling) imports this module and will not decide when its
sha256, or that of R355's scripts/settlehop_rule.py imported here, differs from the ```fixed block of
experiments/settlelit_fwd/PREREG.md. A change here is a new lane.

Times are UTC epoch milliseconds. Rates are fractions per settlement, positive when longs pay. d is the position on
Lighter: +1 long, -1 short; it is against the side that receives Binance's lump (R363's d).
"""
import math

import numpy as np

from settlehop_rule import canon, decide_stats, leave_two_coins_out, lighter_crypto, signal, trimmed  # noqa: F401

H, MIN, SEC = 3_600_000, 60_000, 1_000
STEP = 4 * H                    # settlements decided: T on a 4 h boundary (00/04/08/12/16/20 UTC)
WINDOW = 5 * MIN                # the decision window opens at T - 1 h - 5 min ...
DECIDE_AT = 20 * SEC            # ... and decides at T - 1 h + 20 s
SINCE_MARGIN = MIN              # Binance showed T as the coin's next funding time by T - 1 h - 60 s: no 1 h cycle
ON_TIME = 10 * MIN              # a decision later than T - 1 h + 10 min is late and enters nothing
THETA, THETA_HI = 0.003, 0.005  # the decided book |e| >= 0.3% (R363's events); 0.5% (R356's book) is reported
LOG_E = 0.002                   # candidates logged from this |e|
SLOTS = 5                       # hops selected per settlement, largest |e| first
USD = 1_000.0                   # paper notional: the base quantity is fixed at USD / Lighter's mid at the decision
H_LIVE = 2 * H                  # Lighter's last settlement at or before T - 1 h is at most this old
PRICE_TOL = 0.05                # identity: Lighter's mid within 5% of Binance's mark at the decision
MAX_RT = 0.0010                 # cost gate: q walked both ways on Lighter's book at the decision costs <= 10 bp
BOOK_FROM, BOOK_TO = -7 * MIN, 6 * MIN       # the book window around T
ENTRIES = (-300 * SEC, -10 * SEC)            # walks on the entry side; the primary enters at T - 10 s
EXITS = (60 * SEC, 120 * SEC, 300 * SEC)     # walks on the exit side; the primary exits at T + 60 s
PRIMARY = (-10 * SEC, 60 * SEC)
ENTRY_LATE = 5 * SEC            # an entry walk more than 5 s after its instant, or on a book not live, is not on time
SCORE_AFTER = 20 * MIN          # Lighter's settlement is read 20 min after the exit
FUND_WAIT = 24 * H              # after this with no settlement in the hold, the hop is scored with funding 0, flagged
FUTILITY = (20, 40)             # primary hops: a mean 1x net at or below 0 at either count stops the lane
LOOK1, FINAL = 40, 80           # primary hops at the interim and the final look
T_LOOK1, T_FINAL = 2.80, 1.98   # O'Brien-Fleming, two looks; size on R363's hops: scripts/calib_settlelit_fwd.py
END_MS = 1_824_681_600_000      # 2027-10-28 00:00 UTC: the final look on what is scored if 80 never come
NAMES = {-300 * SEC: "in300", -10 * SEC: "in10", 60 * SEC: "out60", 120 * SEC: "out120", 300 * SEC: "out300"}
VARIANTS = tuple((a, b) for a in ENTRIES for b in EXITS)     # R363's six trials, live; the primary decides


def binance_base(symbol):
    """The base of a Binance USDT-margined perpetual (KAITOUSDT -> KAITO); None for anything else (dated futures carry
    an underscore, USDC-margined perps end in USDC)."""
    s = str(symbol or "")
    return s[:-4] if s.endswith("USDT") and "_" not in s and len(s) > 4 else None


def eligible(T, seen):
    """Binance perps settling at T on a 4 h or 8 h cycle, from the decision window's markPrice stream.
    seen: {symbol: (next funding time, first event time it was seen, r, event time of r, mark)}. A coin qualifies
    when T is a 4 h boundary, its next funding time is T, and the stream showed that by T - 1 h - 60 s: a coin on a
    1 h cycle shows T - 1 h until it settles then. Returns [(symbol, r, r_E, first_E, mark)], sorted by symbol."""
    if T % STEP:
        return []
    out = []
    for s, (t_next, first, r, r_e, mark) in seen.items():
        if binance_base(s) and int(t_next) == T and int(first) <= T - H - SINCE_MARGIN:
            out.append((s, float(r), int(r_e), int(first), float(mark)))
    return sorted(out)


def lighter_h(stats, T):
    """Lighter's last hourly settlement at or before T - 1 h, from its market_stats row: (time, rate) or (None, NaN).
    Lighter stamps a settlement a few ms after the hour (14:00:00.003), so the stamp is floored to the second; it
    reports the rate in percent, signed (negative: shorts pay)."""
    try:
        t = int(stats["funding_timestamp"]) // SEC * SEC
        h = float(stats["funding_rate"]) / 100
    except (KeyError, TypeError, ValueError):
        return None, math.nan
    if not (T - H - H_LIVE <= t <= T - H) or not math.isfinite(h):
        return None, math.nan
    return t, h


def lighter_mid(stats):
    """Lighter's mid from market_stats, else its last trade; NaN when neither is a positive number."""
    for k in ("mid_price", "last_trade_price"):
        try:
            v = float(stats.get(k))
        except (TypeError, ValueError):
            continue
        if v > 0 and math.isfinite(v):
            return v
    return math.nan


def same_price(l_mid, b_mark, tol=PRICE_TOL):
    """The identity check: Lighter's mid within tol of Binance's mark. Two coins sharing a ticker, or a 1000x size
    prefix on one venue only, fail it."""
    return l_mid > 0 and b_mark > 0 and abs(l_mid / b_mark - 1) <= tol


def theta_book(e):
    """The largest book a hop belongs to, in percent: 0.5 when |e| >= 0.5%, else 0.3."""
    return 0.5 if abs(e) >= THETA_HI - 1e-15 else 0.3


def walk(levels, q):
    """Walk q base units through levels [(price, size)], best first: (average price, filled quantity, levels used).
    Nothing beyond the shown levels fills; the average is NaN when nothing does."""
    left, paid, got, used = float(q), 0.0, 0.0, 0
    for p, s in levels:
        if not (p > 0 and s > 0):                  # also skips a NaN level
            continue
        take = min(left, s)
        paid += take * p
        got += take
        left -= take
        used += 1
        if left <= q * 1e-9:
            break
    return (paid / got if got > 0 else math.nan), got, used


def round_trip(bids, asks, q):
    """The cost gate's measure: walking q both ways on a book, as a fraction of its mid, (buy average - sell average) /
    mid. bids / asks: [(price, size)] in any order. inf when a side is empty or cannot hold all of q."""
    bids = sorted(((p, s) for p, s in bids if p > 0 and s > 0), reverse=True)
    asks = sorted((p, s) for p, s in asks if p > 0 and s > 0)
    if not (bids and asks):
        return math.inf
    buy, got_b, _ = walk(asks, q)
    sell, got_s, _ = walk(bids, q)
    if min(got_b, got_s) < q * (1 - 1e-9):
        return math.inf
    return (buy - sell) / ((bids[0][0] + asks[0][0]) / 2)


def side(d, entry):
    """True when the walk buys: a long's entry and a short's exit take the asks."""
    return (d > 0) == bool(entry)


def leg(d, ent, ext, rates, fee_bp):
    """One position's accounting, as fractions of its entry notional at the mid (q x m0).
    ent / ext: {"ms", "mid", "fill"} of the entry and exit walks (a fill is the average price of the whole q).
    rates: Lighter's settlements [(ms, rate)]; the position holds those in (entry, exit] and pays d x rate.
    gross = d (m1 / m0 - 1); book = what both fills gave up against their mids; fee = Lighter's taker on both fills;
    net_k = gross + fund - k (book + fee)."""
    m0, m1, f0, f1 = (float(x) for x in (ent["mid"], ext["mid"], ent["fill"], ext["fill"]))
    a, b = int(ent["ms"]), int(ext["ms"])
    held = [r for t, r in rates if a < t <= b]
    gross = d * (m1 / m0 - 1)
    book = d * (f0 - m0) / m0 + d * (m1 - f1) / m0
    fee = float(fee_bp) / 1e4 * (f0 + f1) / m0
    fund = -d * sum(held)
    out = {"gross_mid": gross, "fund": fund, "n_fund": len(held), "book_cost": book, "fee": fee}
    for k in (1, 2, 3):
        out[f"net{k}"] = gross + fund - k * (book + fee)
    return out


def primary(scored):
    """The decided book: hops with |e| >= 0.3% whose decision and entry were on time, in entry order. The exit is
    whatever came first after T + 60 s, so no hop leaves the book for a late exit."""
    rows = [r for r in scored if str(r["on_time"]) == "True" and abs(float(r["e"])) >= THETA - 1e-15]
    return sorted(rows, key=lambda r: (int(r["entry_ms"]), r["hop"]))


def verdict(prim, now_ms, bounds=(T_LOOK1, T_FINAL)):
    """The PREREG's decision on the primary book's hops in entry order: (state, text). States: PENDING, PASS, NULL,
    INCONCLUSIVE. Only the first 20, 40 or 80 hops are read, so a later hop cannot change a verdict."""
    n = len(prim)
    mean = lambda rs, c: float(np.mean([float(r[c]) for r in rs]))
    for k in FUTILITY:
        if n >= k and mean(prim[:k], "net1") <= 0:
            return "NULL", f"futility at {k} hops: mean net {mean(prim[:k], 'net1') * 1e4:+.1f} bp a hop"

    def look(k, bound):
        rs = prim[:k]
        mu, t = decide_stats([float(r["net1"]) for r in rs], [r["T"] for r in rs])
        m2 = mean(rs, "net2")
        ok = math.isfinite(t) and t >= bound and m2 > 0
        return ok, f"{k} hops: mean net {mu * 1e4:+.1f} bp a hop, CR1 t {t:.2f} (bound {bound}), 2x {m2 * 1e4:+.1f} bp"

    if n >= LOOK1:
        ok, text = look(LOOK1, bounds[0])
        if ok:
            return "PASS", "interim look at " + text
    if n >= FINAL or now_ms >= END_MS:
        if n < FUTILITY[0]:
            return "INCONCLUSIVE", f"{n} primary hops by 2027-10-28, fewer than {FUTILITY[0]}"
        ok, text = look(min(n, FINAL), bounds[1])
        return ("PASS" if ok else "NULL"), "final look at " + text
    return "PENDING", f"{n} scored on-time primary hops; interim look at {LOOK1}, final at {FINAL} or 2027-10-28"
