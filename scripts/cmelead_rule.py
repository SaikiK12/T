"""R370 cmelead_v1 rule, frozen in experiments/cmelead_v1/PREREG.md: when an EIA release moves CME's front-month crude or
natural-gas future by a lot, does Binance's TradFi perp still trade at the old price for long enough that a taker on
Binance earns the catch-up?

Pure functions over trade arrays; nothing here reads a file. scripts/run_cmelead.py feeds it Databento's CME Globex trades
(leader) and Binance USD-M aggregated trades (follower).

Both venues are read through trade prices only, so there is no quote to flicker and no book to model:
- leader   CME trades: dict of equal-length arrays sorted by t (UTC microseconds, the exchange's event time): t, price
- follower Binance aggTrades: t (microseconds from the millisecond stamp), price, buyer_maker (True when the seller was the
           aggressor), so a taker BUY is buyer_maker == False and prints at the ask

One event, one latency L:
- reference  p0 = the median, over the 51 one-second marks from T-60 s to T-10 s, of the last trade price at each mark
             (a trade older than 300 s is missing; at least 25 marks must have one), for the leader and the follower
- crossing   t* = the first CME trade at or after T (within 60 s of it) whose price is at least THETA bp from p0_leader;
             s = the sign of that move
- decision   t_d = t* + L, L the seconds from the CME trade to a Binance order reaching the book
- state      D = s * 1e4 * ln(last CME price at t_d / p0_leader); skip "reverted" if D < THETA.
             c = s * 1e4 * ln(last Binance price at t_d / p0_follower) / D; the lag filter keeps the trade when c <= LAG_FILTER
- entry      the first Binance taker print on the side of s (taker buy if s > 0, taker sell if s < 0) at or after t_d and
             within ENTRY_WAIT_S of it; none -> "no_fill"
- exit       the last Binance taker print on the opposite side at or before T + HOLD_S and not older than EXIT_STALE_S;
             none -> "no_exit"
- gross      s * 1e4 * ln(exit / entry), in bp (prints sit on the touch, so the spread is already in it);
             net = gross - k * 2 * FEE_SIDE_BP, k = 1, 2, 3
"""
import math

import numpy as np

US = 1_000_000
THETA = {"ngs": 20.0, "wpsr": 8.0}            # bp, R369's thresholds (they came from R368's minute bars)
LAGS = (0.5, 1.0, 2.0, 5.0)                   # seconds
DECISION_L = 1.0
HOLD_S = 60.0
LAG_FILTER = 0.5
ENTRY_WAIT_S = 1.0
EXIT_STALE_S = 10.0
REF_FROM_S, REF_TO_S = 60, 10
REF_MIN_MARKS = 25
MAX_AGE_S = 300.0
CROSS_WINDOW_S = 60.0
FEE_SIDE_BP = 5.0                             # Binance USD-M taker, an assumption (not read from the owner's account)
COST_MULTS = (1, 2, 3)
MIN_VALID_EVENTS = 10
MIN_FIRED = 6
ALPHA = 0.05
EXACT_MAX = 18
DRAWS = 200_000
SEED = 370


def last_index(t, t_us):
    """Index of the last trade at or before t_us, or -1."""
    return int(np.searchsorted(t, t_us, side="right")) - 1


def reference(tr, T_us):
    """Median of the carried-forward last trade price over the marks T-60 s .. T-10 s; NaN with too few fresh marks."""
    if len(tr["t"]) == 0:
        return math.nan
    marks = T_us - np.arange(REF_TO_S, REF_FROM_S + 1) * US
    idx = np.searchsorted(tr["t"], marks, side="right") - 1
    ok = (idx >= 0) & ((marks - tr["t"][np.clip(idx, 0, None)]) <= MAX_AGE_S * US)
    if ok.sum() < REF_MIN_MARKS:
        return math.nan
    return float(np.median(tr["price"][idx[ok]]))


def displacement(tr, ref, t_us):
    """bp of the last trade price at t_us from the reference; NaN when there is no trade yet."""
    i = last_index(tr["t"], t_us)
    if i < 0 or not math.isfinite(ref):
        return math.nan
    return 1e4 * math.log(tr["price"][i] / ref)


def first_crossing(lead, ref, T_us, theta):
    """(t*, s) of the first leader trade at or after T, within CROSS_WINDOW_S, at least theta bp from ref; or None."""
    lo = int(np.searchsorted(lead["t"], T_us, side="left"))
    hi = int(np.searchsorted(lead["t"], T_us + CROSS_WINDOW_S * US, side="right"))
    if hi <= lo:
        return None
    d = 1e4 * np.log(lead["price"][lo:hi] / ref)
    hit = np.flatnonzero(np.abs(d) >= theta)
    if not len(hit):
        return None
    return int(lead["t"][lo + hit[0]]), (1 if d[hit[0]] > 0 else -1)


def evaluate(lead, fol, T_us, etype, lag_s):
    """One event at one latency. `status` says why there is no trade; `gross` is set when there is one, and `lag_ok` says
    whether the lag filter keeps it."""
    theta = THETA[etype]
    out = {"status": "no_ref", "s": 0, "t_star_s": math.nan, "D": math.nan, "c": math.nan, "lag_ok": False,
           "entry": math.nan, "exit": math.nan, "entry_wait_s": math.nan, "gross": math.nan}
    ref_l, ref_f = reference(lead, T_us), reference(fol, T_us)
    if not (math.isfinite(ref_l) and math.isfinite(ref_f)):
        return out
    cross = first_crossing(lead, ref_l, T_us, theta)
    if cross is None:
        out["status"] = "no_cross"
        return out
    t_star, s = cross
    t_d = t_star + int(round(lag_s * US))
    out.update(s=s, t_star_s=(t_star - T_us) / US)
    D = s * displacement(lead, ref_l, t_d)
    out["D"] = D
    if not math.isfinite(D) or D < theta:
        out["status"] = "reverted"
        return out
    f = s * displacement(fol, ref_f, t_d)
    out["c"] = f / D if math.isfinite(f) else math.nan
    taker_buy = ~fol["buyer_maker"]
    want = taker_buy if s > 0 else ~taker_buy
    i0 = int(np.searchsorted(fol["t"], t_d, side="left"))
    i1 = int(np.searchsorted(fol["t"], t_d + int(ENTRY_WAIT_S * US), side="right"))
    ent = np.flatnonzero(want[i0:i1])
    if not len(ent):
        out["status"] = "no_fill"
        return out
    i_in = i0 + int(ent[0])
    j1 = last_index(fol["t"], T_us + int(HOLD_S * US))
    j0 = int(np.searchsorted(fol["t"], T_us + int(HOLD_S * US) - int(EXIT_STALE_S * US), side="left"))
    ext = np.flatnonzero(~want[j0:j1 + 1]) if j1 >= j0 else []
    if not len(ext):
        out["status"] = "no_exit"
        return out
    i_out = j0 + int(ext[-1])
    if i_out <= i_in:
        out["status"] = "no_exit"
        return out
    entry, exit_ = float(fol["price"][i_in]), float(fol["price"][i_out])
    out.update(entry=entry, exit=exit_, entry_wait_s=(int(fol["t"][i_in]) - t_d) / US)
    out["status"] = "ok"
    out["lag_ok"] = bool(math.isfinite(out["c"]) and out["c"] <= LAG_FILTER)
    out["gross"] = float(s * 1e4 * math.log(exit_ / entry))
    return out


def net(gross, k):
    return gross - k * 2 * FEE_SIDE_BP


def sign_flip_p(x, rng, draws=DRAWS, exact_max=EXACT_MAX):
    """One-sided p that the mean of x is above 0 if each trade were as likely to go either way."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return math.nan
    obs = x.sum()
    tol = 1e-9 * max(1.0, float(np.abs(x).sum()))
    if n <= exact_max:
        bits = (np.arange(2 ** n)[:, None] >> np.arange(n)) & 1
        return float((((2 * bits - 1) @ x) >= obs - tol).mean())
    signs = rng.integers(0, 2, size=(draws, n)) * 2 - 1
    return float((1 + ((signs @ x) >= obs - tol).sum()) / (1 + draws))


def holm(p):
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = run
    return adj


def summarize(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    mean = float(x.mean()) if n else math.nan
    sd = float(x.std(ddof=1)) if n > 1 else math.nan
    return {"n": n, "mean": mean, "sd": sd, "t": mean / (sd / math.sqrt(n)) if n > 1 and sd > 0 else math.nan,
            "hit": float((x > 0).mean()) if n else math.nan}


def verdict(cells):
    """cells: one dict per decision cell (event type, L = DECISION_L, lag-filtered) with n (trades taken), valid (valid
    events), gross mean `mean`, `p_holm`. PASS: n >= MIN_FIRED, p_holm <= ALPHA and the mean above 2 cost units
    (4 * FEE_SIDE_BP, i.e. the 2x net is positive). PARTIAL: significant and above 1 cost unit only. INCONCLUSIVE: no
    type has MIN_VALID_EVENTS valid events and MIN_FIRED trades. NULL otherwise."""
    unit = 2 * FEE_SIDE_BP
    live = [c for c in cells if c["valid"] >= MIN_VALID_EVENTS and c["n"] >= MIN_FIRED]
    if not live:
        return "INCONCLUSIVE", f"no type has {MIN_VALID_EVENTS} valid events and {MIN_FIRED} lag-filtered trades"
    sig = [c for c in live if c["p_holm"] <= ALPHA]
    if any(c["mean"] > 2 * unit for c in sig):
        return "PASS", "a decision cell is significant after Holm and clears 2 cost units"
    if any(c["mean"] > unit for c in sig):
        return "PARTIAL", "a decision cell is significant after Holm and clears 1 cost unit but not 2"
    return "NULL", "no decision cell is significant and above cost"
