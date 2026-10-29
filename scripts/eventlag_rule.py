"""R369 eventlag_fwd rule, frozen in experiments/eventlag_fwd/PREREG.md: when a scheduled EIA release moves a lead venue
by a lot, does a lagging venue still show the old price for long enough that a taker on it earns the catch-up?

Pure functions over quote arrays; nothing here reads a file. scripts/run_eventlag.py feeds it the recordings of
scripts/record_commodity_perps.py (Binance, Hyperliquid) and scripts/record_lighter_trades.py (Lighter).

Quotes of a venue are a dict of equal-length numpy arrays sorted by t: t (local receive time, microseconds), bid, ask,
bq, aq. Every lookup is "the last quote received at or before the time asked", so nothing sees the future.

One event, one follower, one latency L:
- reference  m0_v = the median, over the 51 one-second marks from T-60 s to T-10 s, of the mid carried forward from the
             last quote at each mark (a quote older than 300 s is missing; at least 25 marks must have one)
- crossing   t* = the first receive time at or after T (and within 60 s of it) at which a leader venue's mid is at least
             THETA bp from its own reference; the sign of that move is s, the venue the leader
- decision   t_d = t* + L, with L the seconds from the crossing to the order reaching the follower's book
- state      D = the largest s * displacement among the leader venues at t_d (they are all the venues but the follower)
             and c = s * (follower displacement at t_d) / D. Skip if D < THETA ("reverted").
             The lag filter keeps the trade when c <= LAG_FILTER (the follower has covered at most half of the move)
- entry      the follower's touch at t_d on the side of s (buy the ask if s > 0, sell the bid if s < 0); skipped if it
             shows less than MIN_USD of size
- exit       the opposite touch at T + HOLD_S
- gross      s * 1e4 * ln(exit / entry), in bp; net = gross - k * 2 * FEE_SIDE_BP[follower], k = 1, 2, 3
"""
import math

import numpy as np

US = 1_000_000
VENUES = ("binance", "hl", "lighter")
THETA = {"ng": 20.0, "wpsr": 8.0}             # bp
LAGS = (0.5, 1.0, 2.0, 5.0)                   # seconds
DECISION_L = 1.0
HOLD_S = 60.0
LAG_FILTER = 0.5
MIN_USD = 250.0
REF_FROM_S, REF_TO_S = 60, 10                 # reference marks T-60 .. T-10, one a second
REF_MIN_MARKS = 25
MAX_AGE_S = 300.0
CROSS_WINDOW_S = 60.0
FEE_SIDE_BP = {"lighter": 2.5, "hl": 9.0, "binance": 5.0}
COST_MULTS = (1, 2, 3)
MIN_VALID_EVENTS = 8      # valid events per type before the first read
MIN_FIRED = 6             # lag-filtered trades per type before a cell is decided on
ALPHA = 0.05
EXACT_MAX = 18
DRAWS = 200_000
SEED = 369
PRIMARY_FOLLOWER = "lighter"
REPORT_FOLLOWERS = ("hl", "binance")


def last_index(q, t_us):
    """Index of the last quote received at or before t_us, or -1."""
    return int(np.searchsorted(q["t"], t_us, side="right")) - 1


def mid(q, i):
    return 0.5 * (q["bid"][i] + q["ask"][i])


def reference(q, T_us):
    """Median of the carried-forward mid over the marks T-60 s .. T-10 s; NaN when too few marks have a fresh quote."""
    if len(q["t"]) == 0:
        return math.nan
    marks = T_us - np.arange(REF_TO_S, REF_FROM_S + 1) * US
    idx = np.searchsorted(q["t"], marks, side="right") - 1
    ok = (idx >= 0) & ((marks - q["t"][np.clip(idx, 0, None)]) <= MAX_AGE_S * US)
    if ok.sum() < REF_MIN_MARKS:
        return math.nan
    m = 0.5 * (q["bid"][idx[ok]] + q["ask"][idx[ok]])
    return float(np.median(m))


def displacement(q, ref, t_us):
    """bp of the venue's mid at t_us from its reference; NaN when it has no quote yet."""
    i = last_index(q, t_us)
    if i < 0 or not math.isfinite(ref):
        return math.nan
    return 1e4 * math.log(mid(q, i) / ref)


def first_crossing(quotes, refs, leaders, T_us, theta):
    """(t*, venue, s) of the first leader quote at or after T whose displacement reaches theta, or None."""
    best = None
    for v in leaders:
        q, ref = quotes[v], refs[v]
        if not math.isfinite(ref):
            continue
        lo = int(np.searchsorted(q["t"], T_us, side="left"))
        hi = int(np.searchsorted(q["t"], T_us + CROSS_WINDOW_S * US, side="right"))
        if hi <= lo:
            continue
        d = 1e4 * np.log(0.5 * (q["bid"][lo:hi] + q["ask"][lo:hi]) / ref)
        hit = np.flatnonzero(np.abs(d) >= theta)
        if len(hit):
            t = int(q["t"][lo + hit[0]])
            if best is None or t < best[0]:
                best = (t, v, 1 if d[hit[0]] > 0 else -1)
    return best


def evaluate(quotes, T_us, etype, follower, lag_s):
    """One event for one follower and latency. Returns a dict; `status` says why there is no trade, and `gross` is set
    when there is one (with `lag_ok` saying whether the lag filter keeps it)."""
    theta = THETA[etype]
    leaders = [v for v in VENUES if v != follower]
    refs = {v: reference(quotes[v], T_us) for v in VENUES}
    out = {"status": "no_ref", "lead": "", "s": 0, "t_star_s": math.nan, "D": math.nan, "c": math.nan,
           "lag_ok": False, "entry": math.nan, "exit": math.nan, "size_usd": math.nan, "gross": math.nan}
    if not all(math.isfinite(refs[v]) for v in VENUES):
        return out
    cross = first_crossing(quotes, refs, leaders, T_us, theta)
    if cross is None:
        out["status"] = "no_cross"
        return out
    t_star, lead, s = cross
    t_d = t_star + int(round(lag_s * US))
    out.update(lead=lead, s=s, t_star_s=(t_star - T_us) / US)
    moves = [s * displacement(quotes[v], refs[v], t_d) for v in leaders]
    moves = [m for m in moves if math.isfinite(m)]
    D = max(moves) if moves else math.nan
    f_disp = displacement(quotes[follower], refs[follower], t_d)
    out["D"] = D
    if not math.isfinite(D) or D < theta:
        out["status"] = "reverted"
        return out
    out["c"] = s * f_disp / D
    qf = quotes[follower]
    i_in, i_out = last_index(qf, t_d), last_index(qf, T_us + int(HOLD_S * US))
    if i_in < 0 or i_out < 0:
        out["status"] = "no_quote"
        return out
    entry = qf["ask"][i_in] if s > 0 else qf["bid"][i_in]
    size = (qf["aq"][i_in] if s > 0 else qf["bq"][i_in]) * entry
    exit_ = qf["bid"][i_out] if s > 0 else qf["ask"][i_out]
    out.update(entry=float(entry), exit=float(exit_), size_usd=float(size))
    if size < MIN_USD:
        out["status"] = "no_size"
        return out
    out["status"] = "ok"
    out["lag_ok"] = bool(out["c"] <= LAG_FILTER)
    out["gross"] = float(s * 1e4 * math.log(exit_ / entry))
    return out


def net(gross, follower, k):
    return gross - k * 2 * FEE_SIDE_BP[follower]


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
    """cells: one dict per decision cell (event type, Lighter, L = DECISION_L, lag-filtered) with n (fired trades),
    valid (valid events), gross mean `mean`, `p_holm`. PASS: n >= MIN_FIRED, p_holm <= ALPHA and the mean above 2 cost
    units (4 * FEE_SIDE_BP of Lighter, i.e. the 2x net is positive). PARTIAL: significant and above 1 cost unit only.
    INCONCLUSIVE: no type has MIN_VALID_EVENTS valid events and MIN_FIRED trades. NULL otherwise."""
    unit = 2 * FEE_SIDE_BP[PRIMARY_FOLLOWER]
    live = [c for c in cells if c["valid"] >= MIN_VALID_EVENTS and c["n"] >= MIN_FIRED]
    if not live:
        return "INCONCLUSIVE", f"no type has {MIN_VALID_EVENTS} valid events and {MIN_FIRED} lag-filtered trades yet"
    sig = [c for c in live if c["p_holm"] <= ALPHA]
    if any(c["mean"] > 2 * unit for c in sig):
        return "PASS", "a decision cell is significant after Holm and clears 2 cost units"
    if any(c["mean"] > unit for c in sig):
        return "PARTIAL", "a decision cell is significant after Holm and clears 1 cost unit but not 2"
    return "NULL", "no decision cell is significant and above cost"
