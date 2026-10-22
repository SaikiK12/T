"""Prop-firm economics: what a strategy's return stream is worth inside an evaluation and a funded account.

A firm sells an evaluation for a fee. The account passes when equity reaches the target before a drawdown rule breaks,
then trades funded, paying the trader a split of profits at each payout until a rule breaks. This module bootstraps a
return stream (daily, or hourly with steps_per_day=24 so intraday excursions count) under an exact rule set and returns
the pass probability, the expected payouts and the expected value of one challenge after the fee, for a range of sizes.

Equity is additive on the initial balance (fixed sizing): a step's PnL = scale x r x balance. Rules:
- daily loss: equity may not fall more than `daily_loss` below the day's start equity (or the initial balance, by
  `daily_base`), checked at every step;
- max drawdown: `static` (floor = 1 - max_dd), `trailing` (floor = peak - max_dd, peak updated at every step, or at day
  ends with trail_eod), or `trailing_lock` (trails until the floor reaches the initial balance, then stays there);
- target per phase; optional minimum days, maximum days and consistency (best day <= share x total profit).
Presets marked `illustrative` are not any firm's terms; firm presets cite the firm's own page and date.
"""
from dataclasses import dataclass, field, replace

import numpy as np


@dataclass(frozen=True)
class Rules:
    name: str
    account: float                       # USD
    fee: float                           # USD per attempt (NaN when unknown: then only the payout side is reported)
    targets: tuple = (0.10,)             # profit target per phase, fraction of the initial balance
    daily_loss: float = 0.05
    daily_base: str = "day_start"        # "day_start" | "initial"
    max_dd: float = 0.10
    dd_mode: str = "static"              # "static" | "trailing" | "trailing_lock"
    trail_eod: bool = False              # trailing peak updated at day ends only
    min_days: int = 0
    max_days: int = 0                    # 0 = unlimited (capped by horizon)
    consistency: float = 0.0             # best day <= this share of total profit at the target (0 = no rule)
    split: float = 0.8                   # trader's share of funded profits
    payout_days: int = 30
    refund_fee: bool = False             # fee refunded with the first payout
    activation: float = 0.0              # USD paid on passing, before funded trading
    payout_share: float = 1.0            # share of the profit above the initial balance withdrawn at a payout
    payout_cap: float = float("inf")     # USD cap on each withdrawal request, before the split
    payout_min: float = 0.0              # USD minimum gross withdrawal request, before split/fees; 0 disables
    payout_profit_required: float = 0.0  # USD earned since the last successful payout; 0 disables, first is exempt
    floor_after_payout: float = float("nan")  # equity floor (units of the initial balance) once one payout is made
    payout_deny: float = 0.0             # chance a payout request is refused and the account closed unpaid
    cost_side: float = 0.0               # firm's commission per side, fraction of notional (spread is the caller's)
    swap_day: float = 0.0                # firm's swap per day on the notional held, fraction
    source: str = "illustrative"


NAN = float("nan")
# From docs/SOURCES.md section 3 (firms' own pages, 2026-10-19, unless marked third-party). Where a rule was not stated
# the assumption is in the comment. Daily loss is measured from the day's starting equity in units of the initial
# balance, as HyroTrader and FTMO describe it.
PRESETS = {
    # HyroTrader: max drawdown type not stated (static assumed); "no day > 40% of target" approximated by consistency
    # 0.4 of profit at the target; payouts on demand (weekly assumed); fee per size not captured
    "hyro_2step": Rules("hyro_2step", 100_000, NAN, targets=(0.10, 0.05), daily_loss=0.05, max_dd=0.10, min_days=5,
                        consistency=0.4, split=0.8, payout_days=7, refund_fee=True, source="hyrotrader.com"),
    "hyro_1step": Rules("hyro_1step", 100_000, NAN, targets=(0.10,), daily_loss=0.04, max_dd=0.06, min_days=5,
                        consistency=0.4, split=0.8, payout_days=7, refund_fee=True, source="hyrotrader.com"),
    # FTMO: EUR 540 for 100k (third-party price) taken as USD 620; split 80% assumed for the first payouts
    "ftmo_2step": Rules("ftmo_2step", 100_000, 620, targets=(0.10, 0.05), daily_loss=0.05, max_dd=0.10, min_days=4,
                        split=0.8, payout_days=14, refund_fee=True, source="ftmo.com/en/trading-objectives"),
    "ftmo_1step": Rules("ftmo_1step", 100_000, NAN, targets=(0.10,), daily_loss=0.03, max_dd=0.10, dd_mode="trailing",
                        trail_eod=True, consistency=0.5, split=0.8, payout_days=14, source="ftmo.com"),
    # Crypto Fund Trader: trailing assumed intraday; prices not captured
    "cft_1phase": Rules("cft_1phase", 100_000, NAN, targets=(0.10,), daily_loss=0.04, max_dd=0.06, dd_mode="trailing",
                        split=0.8, payout_days=14, source="cryptofundtrader.com"),
    "cft_2phase": Rules("cft_2phase", 100_000, NAN, targets=(0.08, 0.05), daily_loss=0.05, max_dd=0.10, split=0.8,
                        payout_days=14, source="cryptofundtrader.com"),
    # Breakout Pro: third-party review (site blocked from here); 0.04% per side and 0.033% a day swap from
    # cryptoslate.com's Breakout review (third-party), charged only when evaluate() is given turnover or exposure
    "breakout_pro": Rules("breakout_pro", 100_000, NAN, targets=(0.12,), daily_loss=0.03, max_dd=0.05, split=0.8,
                          payout_days=14, cost_side=0.0004, swap_day=0.00033,
                          source="third-party: proptradingvibes.com, cryptoslate.com"),
    # Topstep 50K Combine (CME futures; a benchmark, our crypto books cannot trade there): USD 3,000 target, USD 2,000
    # end-of-day trailing locking at the start, best day < 55% of target; USD 49 a month, USD 149 activation (third-party)
    # funded (help.topstep.com payout policy, checked 2026-10-20): each request at most 50% of the balance and USD 2,000
    # (50K Standard path; 3,000 on the Consistency path); after the first payout the loss limit resets to the starting
    # balance. The payout condition is 5 winning days of USD 150+, restarting after each request; payout_days=14
    # approximates it.
    # Minimum gross request is USD 125: topstep.com/instant-payouts FAQ calls it a "payout request";
    # help.topstep.com/en/articles/8284233-topstep-payout-policy distinguishes the request from net cash received.
    "topstep_50k": Rules("topstep_50k", 50_000, 49, targets=(0.06,), daily_loss=0.0, max_dd=0.04,
                         dd_mode="trailing_lock", trail_eod=True, consistency=0.55, split=0.9, payout_days=14,
                         activation=149, payout_share=0.5, payout_cap=2_000, payout_min=125,
                         payout_profit_required=0.01,
                         floor_after_payout=1.0, source="help.topstep.com (rules), third-party (prices)"),
    "illustrative_2step": Rules("illustrative_2step", 100_000, 500, targets=(0.08, 0.05), daily_loss=0.05,
                                max_dd=0.10, split=0.8, refund_fee=True),
}


@dataclass
class Outcome:
    passed: np.ndarray                   # [n] bool
    days: np.ndarray                     # [n] days used (to pass or to fail)
    reason: np.ndarray                   # [n] 0 pass, 1 daily loss, 2 max drawdown, 3 out of time
    extra: dict = field(default_factory=dict)


def bootstrap(r, n, length, block, steps_per_day=1, rng=None):
    """[n, length * steps_per_day] paths of circular block-bootstrapped days of r (len(r) a multiple of steps)."""
    rng = rng or np.random.default_rng(0)
    r = np.asarray(r, float)
    D = len(r) // steps_per_day
    days = r[: D * steps_per_day].reshape(D, steps_per_day)
    nb = -(-length // block)
    starts = rng.integers(0, D, (n, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :length] % D
    return days[idx].reshape(n, length * steps_per_day)


def run_phase(paths, rules, target, steps_per_day=1, check_target=True, eq0=None, peak0=None, floor_min=None):
    """Simulate one phase on [n, steps] paths of scaled returns, from equity eq0 and peak peak0 (default 1); an
    optional per-path floor_min raises the drawdown floor. Returns Outcome with the final equity, peak and alive mask
    in `extra`."""
    n, L = paths.shape
    spd = steps_per_day
    eq = np.ones(n) if eq0 is None else np.array(eq0, float)
    peak = np.ones(n) if peak0 is None else np.array(peak0, float)
    day_start = np.ones(n)
    best_day = np.zeros(n)
    alive = np.ones(n, bool)
    passed = np.zeros(n, bool)
    reason = np.full(n, 3, np.int8)
    days = np.full(n, L // spd, np.int32)
    max_days = rules.max_days or L // spd
    for k in range(min(L, max_days * spd)):
        d = k // spd
        if k % spd == 0:
            day_start = eq.copy()
        eq = np.where(alive, eq + paths[:, k], eq)
        if rules.dd_mode != "static" and not rules.trail_eod:
            peak = np.maximum(peak, eq)
        if rules.dd_mode == "static":
            floor = 1 - rules.max_dd
        elif rules.dd_mode == "trailing":
            floor = peak - rules.max_dd
        else:
            floor = np.minimum(peak - rules.max_dd, 1.0)
        if floor_min is not None:
            floor = np.maximum(floor, floor_min)
        base = day_start if rules.daily_base == "day_start" else 1.0
        hit_daily = alive & (rules.daily_loss > 0) & (eq <= base - rules.daily_loss)
        hit_dd = alive & ~hit_daily & (eq <= floor)
        for hit, why in ((hit_daily, 1), (hit_dd, 2)):
            reason[hit] = why
            days[hit] = d + 1
            alive &= ~hit
        if (k + 1) % spd == 0:
            best_day = np.where(alive, np.maximum(best_day, eq - day_start), best_day)
            if rules.dd_mode != "static" and rules.trail_eod:
                peak = np.maximum(peak, np.where(alive, eq, peak))
            if check_target:
                profit = eq - 1
                ok = alive & (profit >= target) & (d + 1 >= rules.min_days)
                if rules.consistency > 0:
                    ok &= best_day <= rules.consistency * profit
                passed |= ok
                reason[ok] = 0
                days[ok] = d + 1
                alive &= ~ok
        if not alive.any():
            break
    if max_days * spd < L:
        days[alive] = max_days
    return Outcome(passed, days, reason, {"equity": eq, "peak": peak, "alive": alive})


def net_of_costs(r, rules, turnover=0.0, exposure=0.0, steps_per_day=1):
    """Step returns of a gross stream r after the firm's charges: r - turnover x cost_side - exposure x swap_day /
    steps_per_day. turnover is the notional traded in the step (a 1x book opened and closed is 2) and exposure the
    notional held through it, both per unit of the book, so the charges scale with size as r does. Scalars or arrays
    aligned with r; the bootstrap then resamples each step's return and its charges together."""
    return (np.asarray(r, float) - np.asarray(turnover, float) * rules.cost_side
            - np.asarray(exposure, float) * rules.swap_day / steps_per_day)


def evaluate(r, rules, scale, n=4000, horizon=365, funded_days=180, block=5, steps_per_day=1, seed=0,
             turnover=None, exposure=None):
    """Pass probability across all phases, expected payouts in USD, and the expected value of one attempt. With
    turnover or exposure given, r is gross and the firm's cost_side and swap_day are charged (net_of_costs); without
    them r is taken as already net of the firm's charges."""
    if turnover is not None or exposure is not None:
        r = net_of_costs(r, rules, 0.0 if turnover is None else turnover, 0.0 if exposure is None else exposure,
                         steps_per_day)
    rng = np.random.default_rng(seed)
    passed = np.ones(n, bool)
    used = np.zeros(n, np.int32)
    reasons = np.zeros(4, int)
    for target in rules.targets:
        paths = scale * bootstrap(r, n, horizon, block, steps_per_day, rng)
        o = run_phase(paths, rules, target, steps_per_day)
        fail = passed & ~o.passed
        reasons += np.bincount(o.reason[fail], minlength=4)
        passed &= o.passed
        used += o.days
    pay = np.zeros(n)
    if passed.any() and funded_days:
        pay[passed] = funded_payouts(r, rules, scale, int(passed.sum()), funded_days, block, steps_per_day, rng)
    p = float(passed.mean())
    exp_pay = float(pay.mean())                          # over all attempts (zero when not passed)
    p_paid = float((passed & (pay > 0)).mean())
    refund = rules.fee * p_paid if rules.refund_fee else 0.0
    return {"scale": scale, "p_pass": p, "p_paid": p_paid,
            "days_to_pass": float(np.median(used[passed])) if passed.any() else None,
            "fail_daily": int(reasons[1]), "fail_dd": int(reasons[2]), "fail_time": int(reasons[3]),
            "exp_payout": exp_pay, "ev": exp_pay + refund - rules.fee - p * rules.activation,
            "breakeven_fee": (exp_pay - p * rules.activation) / (1 - (p_paid if rules.refund_fee else 0.0)),
            "payout_if_passed": float(pay[passed].mean()) if passed.any() else 0.0}


def funded_payouts(r, rules, scale, n, days, block, steps_per_day, rng):
    """USD paid to the trader over `days` funded days. At each payout date, if equity is above the initial balance,
    payout_share of that profit (each request capped at payout_cap USD before the split) is withdrawn and split; the rest
    stays as cushion and the trailing peak restarts from the new balance. A loss carries over. When
    payout_profit_required > 0, later payouts require that much new USD profit relative to the balance immediately
    after the last successful withdrawal. The first payout is exempt; rejected cycles do not reset that reference.
    A request below payout_min USD is not made: neither money nor the payout reference/floor changes. The minimum
    applies before the profit split and any bank fees. With probability payout_deny an eligible request is refused
    and the account closed unpaid. Once one payout is made, the floor rises to
    floor_after_payout when that is set. A broken rule ends the account."""
    total = np.zeros(n)
    alive = np.ones(n, bool)
    paid = np.zeros(n, bool)
    eq, peak = np.ones(n), np.ones(n)
    last_payout_balance = np.ones(n)
    cycle = rules.payout_days
    cap = rules.payout_cap / rules.account
    after = rules.floor_after_payout
    for start in range(0, days, cycle):
        L = min(cycle, days - start)
        paths = scale * bootstrap(r, n, L, block, steps_per_day, rng)
        fmin = np.where(paid, after, -np.inf) if np.isfinite(after) else None
        o = run_phase(paths, replace(rules, min_days=0, consistency=0.0, max_days=L), np.inf, steps_per_day,
                      check_target=False, eq0=eq, peak0=peak, floor_min=fmin)
        alive = alive & o.extra["alive"]
        eq, peak = o.extra["equity"], o.extra["peak"]
        win = alive & (eq > 1)
        if rules.payout_profit_required > 0:
            # USD tolerance is far below one cent and absorbs normalized-equity rounding.
            new_profit = (eq - last_payout_balance) * rules.account
            win &= ~paid | (new_profit >= rules.payout_profit_required - 1e-8)
        request = np.minimum(rules.payout_share * (eq - 1), cap)
        if rules.payout_min > 0:
            win &= request * rules.account >= rules.payout_min - 1e-8
        if rules.payout_deny > 0:
            denied = win & (rng.random(n) < rules.payout_deny)
            alive &= ~denied
            win &= ~denied
        out = np.where(win, request, 0.0)
        total += out * rules.split * rules.account
        eq = eq - out
        last_payout_balance = np.where(win, eq, last_payout_balance)
        peak = np.where(win, eq, peak)
        paid |= win
    return total


def optimize(r, rules, scales=(0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4), **kw):
    """evaluate() over sizes; returns the rows and the one with the highest expected value."""
    rows = [evaluate(r, rules, s, **kw) for s in scales]
    key = "ev" if np.isfinite(rules.fee) else "breakeven_fee"
    return rows, max(rows, key=lambda x: x[key])
