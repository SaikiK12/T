"""Causal funding/basis forecasts and a fixed-quantity, segregated pair-PnL model.

All values are in quote-currency units (USD-stablecoin parity is an explicit
historical scenario). A positive state means long MEXC, short Lighter. Prices at
funding times are traded-close proxies, NOT historical fair/mark prices. This is
gate-0 accounting; it cannot establish execution or liquidation feasibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

HOUR = 3_600_000
DAY = 24 * HOUR
HORIZONS = (1, 7, 14)
MODELS = ("F0", "F1", "F0+B", "F1+B")
LABELS = tuple(f"{m}_h{h}" for m in MODELS for h in HORIZONS)
FORMULA_VERSION = "equations_v1_settled_funding_basis"
COSTS = np.array([.0010, .0004])


@dataclass
class Panel:
    times: np.ndarray                 # hourly close instants, including END
    keys: tuple[str, ...]
    prices: np.ndarray                # [hour, coin, venue], complete raw grid with NaN holes
    fresh: np.ndarray                 # positive traded volume at this close
    rates: np.ndarray                 # exact settlement rate, 0 only on a certified non-event hour
    funding_ok: np.ndarray            # known settlement/no-settlement, NOT inferred from absent row
    steps: np.ndarray                 # [coin, venue], underlying quote-unit step
    minima: np.ndarray                # minimum underlying quantity
    min_quote: np.ndarray             # minimum quote notional
    metadata_ok: np.ndarray           # current rule capture usable; historical vintage remains unknown
    settlement: np.ndarray | None = None

    def validate(self):
        t = np.asarray(self.times)
        n = len(self.keys)
        if t.ndim != 1 or len(t) < 25 or len(set(self.keys)) != n or not n:
            raise ValueError("invalid hourly axis or symbols")
        if not np.all(np.diff(t) == HOUR) or t[0] % DAY:
            raise ValueError("expected a complete UTC hourly grid starting at midnight")
        shape = (len(t), n, 2)
        if any(np.shape(x) != shape for x in (self.prices, self.fresh, self.rates, self.funding_ok)):
            raise ValueError("misaligned hourly arrays")
        if self.settlement is not None and np.shape(self.settlement) != shape:
            raise ValueError("misaligned settlement flags")
        for x in (self.steps, self.minima, self.min_quote):
            if np.shape(x) != (n, 2) or not np.isfinite(x).all() or np.any(x < 0):
                raise ValueError("invalid current rule metadata")
        if np.any(self.steps <= 0) or np.shape(self.metadata_ok) != (n,):
            raise ValueError("invalid quantity steps or metadata flags")
        if np.any(self.fresh & (~np.isfinite(self.prices) | (self.prices <= 0))):
            raise ValueError("fresh price must be finite and positive")
        if np.any(self.funding_ok & ~np.isfinite(self.rates)):
            raise ValueError("certified funding cannot be nonfinite")
        return self


@dataclass
class Forecasts:
    labels: tuple[str, ...]
    funding: np.ndarray               # [2 F models, 3 horizons, day, coin, venue]
    basis: np.ndarray                 # [3 horizons, day, coin]
    eligible: np.ndarray              # [day, coin], source and identity guard
    phi: np.ndarray                   # [day, venue]
    beta: np.ndarray                  # [3 horizons, day]
    basis_training_dates: np.ndarray
    basis_feature: np.ndarray


def _mean_complete(x, axis=0):
    good = np.isfinite(x).all(axis=axis)
    return np.where(good, np.where(np.isfinite(x), x, 0).mean(axis=axis), np.nan)


def pooled_ar1(x):
    """OLS on within-series centered 30-day training values; stable clipped AR(1)."""
    x = np.asarray(x, float)
    if x.ndim != 2 or x.shape[0] < 20:
        return np.nan
    good = np.isfinite(x).all(axis=0)
    if not good.any():
        return np.nan
    z = x[:, good] - x[:, good].mean(axis=0)
    denominator = float(np.sum(z[:-1] ** 2))
    if denominator <= 1e-30:
        return 0.0
    return float(np.clip(np.sum(z[:-1] * z[1:]) / denominator, -.99, .99))


def daily_features(panel):
    panel.validate()
    nd = (len(panel.times) - 1) // 24 + 1
    n = len(panel.keys)
    close = panel.prices[np.arange(nd) * 24]
    fresh = panel.fresh[np.arange(nd) * 24]
    fund = np.full((nd, n, 2), np.nan)
    for d in range(1, nd):
        a, b = (d - 1) * 24 + 1, d * 24 + 1
        good = panel.funding_ok[a:b].all(axis=0)
        fund[d] = np.where(good, panel.rates[a:b].sum(axis=0), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        b = np.log(close[:, :, 1] / close[:, :, 0])
        returns = np.diff(np.log(close), axis=0, prepend=np.full((1, n, 2), np.nan))
    feature = np.full_like(b, np.nan)
    eligible = np.zeros((nd, n), bool)
    for d in range(30, nd):
        history = b[d-29:d+1]
        feature[d] = b[d] - _mean_complete(history)
        for i in range(n):
            rr = returns[d-29:d+1, i]
            fr = (fresh[d-29:d+1, i] & fresh[d-30:d, i]).all(axis=1)
            ok = fr & np.isfinite(rr).all(axis=1)
            if ok.sum() < 20 or not fresh[d, i].all() or not panel.metadata_ok[i]:
                continue
            a, c = rr[ok, 0], rr[ok, 1]
            if a.std() <= 0 or c.std() <= 0:
                continue
            ratio = close[d, i, 0] / close[d, i, 1]
            eligible[d, i] = (.95 <= ratio <= 1.05 and np.corrcoef(a, c)[0, 1] >= .9 and
                               np.isfinite(fund[d-13:d+1, i]).all())
    return close, fresh, fund, feature, eligible


def build_forecasts(panel):
    close, fresh, fund, feature, eligible = daily_features(panel)
    nd, n, _ = fund.shape
    F = np.full((2, 3, nd, n, 2), np.nan)
    B = np.full((3, nd, n), np.nan)
    phi = np.full((nd, 2), np.nan)
    beta = np.full((3, nd), np.nan)
    dates = np.zeros((3, nd), int)
    # Price labels use equal UNDERLYING quantity, normalized by the larger entry
    # leg price. Entry and exit are at 01:00 UTC, one hour after the signal.
    for d in range(30, nd):
        mean14 = _mean_complete(fund[d-13:d+1])
        mean30 = _mean_complete(fund[d-29:d+1])
        for v in range(2):
            phi[d, v] = pooled_ar1(fund[d-29:d+1, :, v])
        for k, horizon in enumerate(HORIZONS):
            F[0, k, d] = horizon * mean14
            for v in range(2):
                if np.isfinite(phi[d, v]):
                    persistence = sum(phi[d, v] ** j for j in range(1, horizon + 1))
                    F[1, k, d, :, v] = (horizon * mean30[:, v] +
                                        (fund[d, :, v] - mean30[:, v]) * persistence)
            # Last admitted label ends at (j+H) 01:00, strictly before d 00:00.
            numerator = denominator = 0.0
            count_dates = 0
            for j in range(max(30, d-horizon-30), d-horizon):
                entry, end = 24*j+1, 24*(j+horizon)+1
                if end >= 24*d or end >= len(panel.times):
                    raise AssertionError("noncausal price training label")
                p0, p1 = panel.prices[entry], panel.prices[end]
                x = feature[j]
                valid = (np.isfinite(x) & np.isfinite(p0).all(axis=1) & np.isfinite(p1).all(axis=1) &
                         panel.fresh[entry].all(axis=1) & panel.fresh[end].all(axis=1) & eligible[j])
                if valid.any():
                    y = ((p1[valid, 0] - p0[valid, 0]) - (p1[valid, 1] - p0[valid, 1])) / p0[valid].max(axis=1)
                    numerator += float(x[valid] @ y)
                    denominator += float(x[valid] @ x[valid])
                    count_dates += 1
            dates[k, d] = count_dates
            if count_dates >= 20:
                beta[k, d] = numerator / denominator if denominator > 1e-30 else 0.0
                B[k, d] = beta[k, d] * feature[d]
    return Forecasts(LABELS, F, B, eligible, phi, beta, dates, feature)


def choose_states(scores, current, slots=20):
    """Exact additive equal-slot optimum over flat/long-MEXC/short-MEXC states.

    scores[:,0] includes any immediate exit cost of going flat. Impossible
    nonflat states have -inf scores. Ties retain inventory, then flat, then the
    canonical input order. Tested against exhaustive independent enumeration.
    """
    scores = np.asarray(scores, float)
    current = np.asarray(current, int)
    if scores.shape != (len(current), 3) or not np.isfinite(scores[:, 0]).all() or np.isnan(scores).any():
        raise ValueError("invalid state score matrix")
    if slots < 0 or np.any(~np.isin(current, (-1, 0, 1))):
        raise ValueError("invalid capacity or current state")
    out = np.zeros(len(current), int)
    candidates = []
    for i in range(len(current)):
        mx = max(scores[i, 1:])
        gain = mx - scores[i, 0]
        choices = [s for s in (1, -1) if scores[i, 1 if s == 1 else 2] == mx]
        best = current[i] if current[i] in choices else choices[0]
        if gain > 0 or (gain == 0 and best == current[i] != 0):
            candidates.append((gain, best == current[i], i, best))
    candidates.sort(key=lambda z: (-z[0], -int(z[1]), z[2]))
    for _, _, i, state in candidates[:slots]:
        out[i] = state
    return out


def hedge_quantity(prices, steps, minima, min_quote, budget):
    """Conservative two-venue lot rounding. No leg above budget; <=1% unit mismatch."""
    p, step, mn, mq = (np.asarray(x, float) for x in (prices, steps, minima, min_quote))
    if not all(x.shape == (2,) for x in (p, step, mn, mq)):
        raise ValueError("two-venue quantities required")
    if not all(np.isfinite(x).all() for x in (p, step, mn, mq)) or np.any(p <= 0) or np.any(step <= 0):
        return np.zeros(2)
    if not np.isfinite(budget) or budget <= 0:
        return np.zeros(2)
    q0 = math.floor(budget / max(p) / step[0] + 1e-12) * step[0]
    q1 = math.floor(q0 / step[1] + 1e-12) * step[1]
    q = np.array([q0, q1])
    if (np.any(q <= 0) or np.any(q < mn) or np.any(q*p < mq) or np.any(q*p > budget + 1e-8) or
            abs(q0-q1) > .01 * max(q0, q1)):
        return np.zeros(2)
    return q


def simulate(panel, forecasts, label, start_ms, end_ms, *, scale=1., capital=10000., slots=20,
             costs=COSTS, baseline_states=None):
    """Same quantities at all cost tiers; 2x cash drives one-venue gross admission.

    Events at a shared clock: mark old positions -> funding old positions -> fills.
    A 01:00 entry never earns 00:00 or 01:00 funding. Unknown held observations
    flag the day unscored, bridge price PnL at the next actual observation, and
    request a paired exit when both prices are fresh. No zero-return hole repair.
    """
    panel.validate()
    if not 0 < scale <= 1 or capital <= 0 or slots <= 0:
        raise ValueError("invalid scale/capital/capacity")
    cost = np.asarray(costs, float)
    if cost.shape != (2,) or not np.isfinite(cost).all() or np.any(cost < 0):
        raise ValueError("invalid per-venue one-way costs")
    where = {int(t): i for i, t in enumerate(panel.times)}
    if start_ms not in where or end_ms not in where or start_ms % DAY or end_ms % DAY or end_ms <= start_ms:
        raise ValueError("split must use existing increasing UTC midnight boundaries")
    first, last = where[start_ms], where[end_ms]
    days, n = (last-first)//24, len(panel.keys)
    if baseline_states is None:
        if label not in LABELS:
            raise ValueError("unregistered equation label")
        model, hs = label.rsplit("_h", 1)
        k = HORIZONS.index(int(hs))
        fmodel = 1 if model.startswith("F1") else 0
        add_basis = "+B" in model
    else:
        model, k, fmodel, add_basis = "reference", 0, 0, False
    qty = np.zeros((n, 2))
    last_price = np.full((n, 2), np.nan)
    nav = np.full((3, 2), capital/2)
    start_nav = nav.sum(axis=1).copy()
    out = {name: np.zeros((days, 3)) for name in ("net", "price", "funding", "cost", "equity", "return")}
    out.update({"scored": np.ones(days, bool), "held": np.zeros(days, int),
                "turnover": np.zeros(days), "forced": np.zeros(days, int),
                "coin_net": np.zeros((days, n, 3)), "venue_equity": np.zeros((days, 3, 2)),
                "gross_breach": np.zeros(days, bool), "insolvent": np.zeros((days, 3), bool)})
    out["tickets"] = []
    decision_count = 0
    pending_exit = np.zeros(n, bool)

    def trade(i, target, px, dd, reason="decision"):
        nonlocal qty, nav
        delta = target - qty[i]
        charge = np.abs(delta) * px * cost
        out["tickets"].append({"time_ms": int(panel.times[h]), "coin": panel.keys[i], "reason": reason,
                               "old_mexc": float(qty[i, 0]), "old_lighter": float(qty[i, 1]),
                               "new_mexc": float(target[0]), "new_lighter": float(target[1]),
                               "mexc_price_proxy": float(px[0]), "lighter_price_proxy": float(px[1]),
                               "mexc_cost_1x": float(charge[0]), "lighter_cost_1x": float(charge[1])})
        for m in range(3):
            amount = (m+1) * charge
            nav[m] -= amount
            out["cost"][dd, m] += amount.sum()
            out["coin_net"][dd, i, m] -= amount.sum()
        out["turnover"][dd] += float(np.sum(np.abs(delta)*px)) / capital
        qty[i] = target

    for h in range(first, last+1):
        dd = min(max((h-first-1)//24, 0), days-1)
        px = panel.prices[h]
        valid = np.isfinite(px) & (px > 0)
        held = np.any(qty != 0, axis=1)
        forced_this_hour = np.zeros(n, bool)
        # A known zero-trade candle is a known LAST-TRADE price proxy, not a
        # missing feed row. It cannot support a fill, but need not liquidate a
        # held position every quiet hour. Fair/mark valuation remains unverified.
        bad = held & (~valid.all(axis=1) | ~panel.funding_ok[h].all(axis=1))
        pending_exit |= bad
        if pending_exit.any():
            out["scored"][dd] = False
        mark = np.where(valid, px, last_price)
        known = valid & np.isfinite(last_price)
        profit = np.where(known, qty * (px-last_price), 0.)
        pay = np.where(np.isfinite(mark) & panel.funding_ok[h], -qty * mark * panel.rates[h], 0.)
        for m in range(3):
            nav[m] += profit.sum(axis=0) + pay.sum(axis=0)
            out["price"][dd, m] += profit.sum()
            out["funding"][dd, m] += pay.sum()
            out["coin_net"][dd, :, m] += (profit+pay).sum(axis=1)
        last_price = np.where(valid, px, last_price)

        # A missing held observation never produces a profitable admission. Exit
        # at the next tradable paired quote; preserve the unknown-day flags.
        if h > first:
            for i in np.flatnonzero(pending_exit & panel.fresh[h].all(axis=1)):
                trade(i, np.zeros(2), px[i], dd, "data_exit")
                out["forced"][dd] += 1
                pending_exit[i] = False
                forced_this_hour[i] = True
        exposure = np.nansum(np.abs(qty) * mark, axis=0)
        breach = np.any(exposure > nav[1] + 1e-8) or np.any(nav[1] <= 0)
        if breach and held.any():
            out["gross_breach"][dd] = True
            out["scored"][dd] = False
            pending_exit |= np.any(qty != 0, axis=1)
            for i in np.flatnonzero(np.any(qty != 0, axis=1) & panel.fresh[h].all(axis=1)):
                trade(i, np.zeros(2), px[i], dd, "gross_exit")
                out["forced"][dd] += 1
                pending_exit[i] = False
                forced_this_hour[i] = True

        out["insolvent"][dd] |= np.any(nav <= 0, axis=1)
        if h < last and not breach and (h-first) % 24 == 1 and np.all(nav[1] > 0):
            d = (h-1)//24
            current = np.sign(qty[:, 0]).astype(int)
            can_fill = (panel.fresh[h].all(axis=1) & panel.funding_ok[h].all(axis=1) &
                        forecasts.eligible[d] & ~forced_this_hour & ~pending_exit)
            budget = capital * scale / (2*slots)
            qnew = np.array([hedge_quantity(px[i], panel.steps[i], panel.minima[i], panel.min_quote[i], budget)
                             if can_fill[i] else np.zeros(2) for i in range(n)])
            if baseline_states is not None:
                wanted = np.asarray(baseline_states[d], int).copy()
                wanted[~can_fill] = 0
            else:
                f = forecasts.funding[fmodel, k, d]
                b = forecasts.basis[k, d] if add_basis else np.zeros(n)
                scores = np.full((n, 3), -np.inf)
                for i in range(n):
                    p = px[i] if valid[i].all() else last_price[i]
                    # No trade can be modelled without a tradable paired price.
                    if not np.isfinite(p).all() or not panel.fresh[h, i].all():
                        scores[i, 0] = 0
                        continue
                    scores[i, 0] = -2 * np.sum(np.abs(qty[i]) * p * cost)
                    if not can_fill[i] or not np.isfinite(f[i]).all() or not np.isfinite(b[i]):
                        continue
                    for column, state in ((1, 1), (2, -1)):
                        target = qty[i].copy() if current[i] == state else qnew[i] * [state, -state]
                        if not np.any(target):
                            continue
                        expected_funding = -np.sum(target * p * f[i])
                        expected_price = state * min(abs(target)) * max(p) * b[i]
                        immediate = 2 * np.sum(np.abs(target-qty[i]) * p * cost)
                        terminal = 2 * np.sum(np.abs(target) * p * cost)
                        scores[i, column] = expected_funding + expected_price - immediate - terminal
                wanted = choose_states(scores, current, slots)

            # Exits/flip-cover first. Constant underlying quantities are retained
            # while the selected state is unchanged (no hidden daily rebalancing).
            for i in np.flatnonzero((wanted != current) & (current != 0)):
                if panel.fresh[h, i].all():
                    trade(i, np.zeros(2), px[i], dd, "decision_exit")
                else:
                    out["scored"][dd] = False
                    pending_exit[i] = True
            for i in np.flatnonzero((wanted != 0) & ~np.any(qty != 0, axis=1)):
                if np.count_nonzero(qty[:, 0]) >= slots:
                    break
                target = qnew[i] * [wanted[i], -wanted[i]]
                if not np.any(target):
                    continue
                notionals = np.abs(target) * px[i]
                current_exposure = np.nansum(np.abs(qty) * mark, axis=0)
                fees = 2 * notionals * cost
                if np.all(current_exposure + notionals <= nav[1] - fees + 1e-8):
                    trade(i, target, px[i], dd, "decision_entry")
                    decision_count += 1

        if h == last:
            for i in np.flatnonzero(np.any(qty != 0, axis=1)):
                if panel.fresh[h, i].all():
                    trade(i, np.zeros(2), px[i], dd, "terminal")
                else:
                    out["scored"][dd] = False
        if h > first and (h-first) % 24 == 0:
            dd = (h-first)//24-1
            total = nav.sum(axis=1)
            out["equity"][dd] = total
            out["net"][dd] = total - start_nav
            out["return"][dd] = np.where(start_nav > 0, total/start_nav-1, np.nan)
            out["venue_equity"][dd] = nav
            out["held"][dd] = np.count_nonzero(qty[:, 0])
            out["insolvent"][dd] |= np.any(nav <= 0, axis=1)
            start_nav = total.copy()
    if not np.allclose(out["net"], out["price"]+out["funding"]-out["cost"], rtol=0, atol=1e-7):
        raise AssertionError("segregated cash/PnL identity failed")
    if not np.allclose(out["coin_net"].sum(axis=1), out["net"], rtol=0, atol=1e-7):
        raise AssertionError("coin attribution identity failed")
    out["entries"] = decision_count
    out["final_quantity"] = qty
    return out


def vix_put_cash_pnl(settlement, strike, premium_points, contracts=1, *, multiplier=100., fees=0.):
    """Cash payoff only, VRO settlement; financing/opportunity cost is separate."""
    values = (settlement, strike, premium_points, contracts, multiplier, fees)
    if not all(np.isfinite(x) for x in values) or min(values) < 0 or multiplier <= 0:
        raise ValueError("invalid cash-settled put inputs")
    return multiplier * contracts * (max(strike-settlement, 0.)-premium_points) - fees
