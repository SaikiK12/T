"""R355 settlehop_fwd's rule, accounting and decision: constants and pure functions, fixed at the freeze.

scripts/forward_settlehop.py (venue reads, journals, scheduling) imports this module and will not tick when its
sha256 differs from the one in the ```fixed block of experiments/settlehop_fwd/PREREG.md. A change here is a new lane.
"""
import math
import re

import numpy as np

H, DAY, MIN = 3_600_000, 86_400_000, 60_000
INTERVALS = (4, 8)                        # S's funding cycles taken, in hours
THETAS = (0.003, 0.005)                   # books: |e| >= theta; the primary is MEXC at 0.5%
PRIMARY = ("mexc", 0.005)
LOG_E = 0.002                             # candidates logged from this |e|
SLOTS = 5                                 # hops entered per venue and settlement, largest |e| first
USD = 1_000.0                             # paper notional of each leg
ON_TIME_S = 600                           # an entry or exit more than 10 min after its hour is late
H_LIVE = 2 * H                            # Lighter's last settlement at or before T - 1 h is at most this old
SCORE_AFTER = 20 * MIN                    # funding is read 20 min after the exit
CORR_DAYS, CORR_MIN, CORR_OBS = 30, 0.9, 20   # R353's identity check, on daily closes
FEE_API_BP = {"mexc": 8.0}                # MEXC API taker since 2026-06-01 (docs/VENUE_STRUCTURE.md); Gate: its own
FUTILITY = (20, 40)                       # primary hops: a mean net at or below 0 at either count stops the lane
LOOK1, FINAL = 40, 80                     # primary hops at the interim and the final look
T_LOOK1, T_FINAL = 2.97, 2.10             # O'Brien-Fleming-shaped (c1 = sqrt 2 c2), raised from 2.80 / 1.98 until
                                          # R354's hops, resampled by settlement with the mean removed, pass <= 2.5%
END_MS = 1_835_481_600_000                # 2028-03-01 00:00 UTC: the final look on what is scored if 80 never come


def canon(base):
    """A coin's base without a size prefix (1000000MOG, 1000BONK and kPEPE all lose theirs), upper case. Only a lower
    case k is a prefix: KAITO keeps its K."""
    return re.sub(r"^(1000000|1000|k)(?=[A-Z0-9])", "", str(base)).upper() if base else ""


def lighter_crypto(d):
    """Lighter funds its crypto perps with a premium multiplier of 100, and its stock, ETF, FX, commodity and pre-IPO
    perps with 50 or 1 (all 215 active markets on 2026-10-28). R354's books were crypto only."""
    try:
        return int(float(d.get("funding_premium_multiplier"))) == 100
    except (TypeError, ValueError):
        return False


def signal(F, h):
    """(e_signed, d): e = F - 2h; d = +1 shorts S and buys Lighter."""
    e = F - 2 * h
    return e, (1 if e > 0 else -1)


def walk(levels, usd):
    """A market order of `usd` notional walked through levels [(price, base qty)], best first: (average price, USD
    filled). The average is NaN when nothing fills."""
    left, paid, qty = float(usd), 0.0, 0.0
    for p, q in levels:
        if not (p > 0 and q > 0):                      # also skips a NaN level
            continue
        take = min(left, p * q)
        paid += take
        qty += take / p
        left -= take
        if left <= 1e-9:
            break
    return (paid / qty if qty > 0 else math.nan), paid


def side_fill(book, buy, usd=USD, complete=True):
    """Fill of one leg: buying walks the asks, selling the bids. With complete=False, an order larger than the shown
    book fills its rest at the last shown level (an exit must close). (price, USD filled, thin)."""
    levels = book["asks"] if buy else book["bids"]
    px, got = walk(levels, usd)
    thin = got < usd - 1e-6
    if thin and not complete and levels:
        last = levels[-1][0]
        qty = (got / px if got > 0 else 0.0) + (usd - got) / last
        px, got = usd / qty, usd
    return px, got, thin


def side_cost(fill, mid, buy):
    """What a fill gives up against the mid, as a fraction of notional (positive when worse than the mid)."""
    return (fill / mid - 1) if buy else (1 - fill / mid)


def daily_closes(bars):
    """{00:00 UTC in ms: the close of the hourly bar ending then} from [(open ms, close)]."""
    return {int(t) + H: float(c) for t, c in bars if (int(t) + H) % DAY == 0}


def same_coin(ca, cb, entry_ms):
    """R353's identity check on two {00:00 UTC ms: close} maps: the correlation of daily returns over the 31 closes up
    to the last 00:00 at or before the entry must reach 0.9 on at least 20 paired days."""
    days = entry_ms // DAY * DAY - DAY * np.arange(CORR_DAYS, -1, -1)
    a = np.array([ca.get(int(x), np.nan) for x in days], float)
    b = np.array([cb.get(int(x), np.nan) for x in days], float)
    ra, rb = a[1:] / a[:-1] - 1, b[1:] / b[:-1] - 1
    m = np.isfinite(ra) & np.isfinite(rb)
    if m.sum() < CORR_OBS or np.std(ra[m]) == 0 or np.std(rb[m]) == 0:
        return False, float("nan")
    c = float(np.corrcoef(ra[m], rb[m])[0, 1])
    return c >= CORR_MIN, c


def last_settled(fund, t_max):
    """Lighter's last settlement at or before t_max from [(ms, rate)]: (ms, rate), or (None, NaN)."""
    xs = [(t, r) for t, r in fund if t <= t_max]
    return max(xs) if xs else (None, math.nan)


def window(rates, a, b):
    """Settlements in (a, b] from [(ms, rate)]."""
    return [(t, r) for t, r in rates if a < t <= b]


def score(enter, exit_, s_rates, h_rates, path=()):
    """One hop's accounting from its two tickets, each venue's settlements and its minute path. Returns are fractions
    of one leg's notional. gross_mid is d (r_H - r_S) at the mids; book_cost is the four sides' fills against their
    mids; fees are four sides at each mode's taker rate; net_k = gross_mid + funding - k (book_cost + fees)."""
    d = int(enter["d"])
    f = lambda r, k: float(r[k])
    mid = lambda r, v: (f(r, f"{v}_bid") + f(r, f"{v}_ask")) / 2
    s0, s1, h0, h1 = mid(enter, "s"), mid(exit_, "s"), mid(enter, "h"), mid(exit_, "h")
    r_s, r_h = s1 / s0 - 1, h1 / h0 - 1
    gross = d * (r_h - r_s)
    s_buy0, h_buy0 = d < 0, d > 0                     # d = -1 buys S at entry; d = +1 buys Lighter
    book = (side_cost(f(enter, "s_fill"), s0, s_buy0) + side_cost(f(exit_, "s_fill"), s1, not s_buy0)
            + side_cost(f(enter, "h_fill"), h0, h_buy0) + side_cost(f(exit_, "h_fill"), h1, not h_buy0))
    a, b = int(enter["ms"]), int(exit_["ms"])
    ws, wh = window(s_rates, a, b), window(h_rates, a, b)
    fs, fh = sum(r for _, r in ws), sum(r for _, r in wh)
    fund = d * (fs - fh)
    fee_h = 2 * f(enter, "fee_h_bp") / 1e4
    fee_web = 2 * f(enter, "fee_s_bp") / 1e4 + fee_h
    fee_api = 2 * FEE_API_BP.get(enter["venue"], f(enter, "fee_s_bp")) / 1e4 + fee_h
    out = {"gross_mid": gross, "fund": fund, "fund_s": d * fs, "fund_h": -d * fh, "n_s": len(ws), "n_h": len(wh),
           "s_rates": " ".join(f"{r:.6g}" for _, r in ws), "h_rates": " ".join(f"{r:.6g}" for _, r in wh),
           "book_cost": book, "fee_web": fee_web, "fee_api": fee_api}
    for k in (1, 2, 3):
        out[f"net{k}_web"] = gross + fund - k * (book + fee_web)
        out[f"net{k}_api"] = gross + fund - k * (book + fee_api)
    # adverse excursion at the marks (venues liquidate on mark): the worst move against each leg, and the pair's
    pts = [(int(p["ms"]), float(p["s_mark"]), float(p["h_mark"])) for p in path
           if a <= int(p["ms"]) <= b and p.get("s_mark") not in ("", None) and p.get("h_mark") not in ("", None)]
    if pts:
        ms_ = np.array([x[1] for x in pts]) / s0 - 1
        mh_ = np.array([x[2] for x in pts]) / h0 - 1
        out.update({"mae_s": float(np.min(-d * ms_)), "mae_h": float(np.min(d * mh_)),
                    "mae_pair": float(np.min(d * (mh_ - ms_))), "path_n": len(pts)})
    else:
        out.update({"mae_s": "", "mae_h": "", "mae_pair": "", "path_n": 0})
    return out


def theta_book(e):
    """The largest book a hop belongs to, in percent: 0.5 when |e| >= 0.5%, else 0.3."""
    return round(max(t for t in THETAS if abs(e) >= t - 1e-15) * 100, 3)


def decide_stats(nets, keys):
    """Mean and t of the hops' nets with the standard error clustered by settlement time (CR1)."""
    x = np.asarray(nets, float)
    n = len(x)
    if n < 2:
        return (float(x.mean()) if n else math.nan), math.nan
    mu = float(x.mean())
    u = x - mu
    groups = {}
    for k, v in zip(keys, u):
        groups[k] = groups.get(k, 0.0) + v
    g = len(groups)
    if g < 2:
        return mu, math.nan
    var = sum(v * v for v in groups.values()) / n ** 2 * g / (g - 1)
    return mu, (mu / math.sqrt(var) if var > 0 else math.nan)


def primary(scored):
    """The decided book: MEXC hops with |e| >= 0.5% whose entry and exit were both on time, in entry order."""
    rows = [r for r in scored if r["venue"] == PRIMARY[0] and float(r["theta_book"]) >= PRIMARY[1] * 100 - 1e-9
            and str(r["on_time"]) == "True"]
    return sorted(rows, key=lambda r: (int(r["entry_ms"]), r["hop"]))


def verdict(prim, now_ms):
    """The PREREG's decision on the primary book's hops in entry order: (state, text). States: PENDING, PASS, NULL,
    INCONCLUSIVE."""
    n = len(prim)
    mean = lambda rs, c: float(np.mean([float(r[c]) for r in rs]))
    for k in FUTILITY:
        if n >= k and mean(prim[:k], "net1_web") <= 0:
            return "NULL", f"futility at {k} hops: mean net {mean(prim[:k], 'net1_web') * 1e4:+.1f} bp a hop"

    def look(k, bound):
        rs = prim[:k]
        mu, t = decide_stats([float(r["net1_web"]) for r in rs], [r["T"] for r in rs])
        m2 = mean(rs, "net2_web")
        ok = math.isfinite(t) and t >= bound and m2 > 0
        return ok, f"{k} hops: mean net {mu * 1e4:+.1f} bp a hop, CR1 t {t:.2f} (bound {bound}), 2x {m2 * 1e4:+.1f} bp"

    if n >= LOOK1:
        ok, text = look(LOOK1, T_LOOK1)
        if ok:
            return "PASS", "interim look at " + text
    if n >= FINAL or now_ms >= END_MS:
        if n < FUTILITY[0]:
            return "INCONCLUSIVE", f"{n} primary hops by 2028-03-01, fewer than {FUTILITY[0]}"
        ok, text = look(min(n, FINAL), T_FINAL)
        return ("PASS" if ok else "NULL"), "final look at " + text
    return "PENDING", f"{n} scored on-time primary hops; interim look at {LOOK1}, final at {FINAL} or 2028-03-01"


def trimmed(nets, k=10):
    """GATES' trimmed mean, per hop: the mean net without the k best and the k worst hops (NaN with 2k or fewer)."""
    x = np.sort(np.asarray(nets, float))
    return float(x[k:-k].mean()) if len(x) > 2 * k else math.nan


def leave_two_coins_out(nets, coins):
    """GATES' leave-two-coins-out mean: the mean net without every hop of the two coins whose hops sum highest."""
    total = {}
    for v, c in zip(nets, coins):
        total[c] = total.get(c, 0.0) + float(v)
    drop = set(sorted(total, key=lambda c: -total[c])[:2])
    keep = [float(v) for v, c in zip(nets, coins) if c not in drop]
    return float(np.mean(keep)) if keep else math.nan
