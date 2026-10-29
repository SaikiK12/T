"""Causal long-only OR30 component and funded bar-account comparison.

This is an independent adaptation, not TradingView execution or a perp margin
engine. Historical bars, fair-price opens and fixed adverse cost scenarios are
proxies. Missing outcomes stay unknown; no performance inference is done here.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import math
from zoneinfo import ZoneInfo

MINUTE = 60_000
ARMS = ("parent", "vwap", "volume", "joint")
NY = ZoneInfo("America/New_York")


def finite(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("numeric input required")
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError("finite positive input required" if positive else "finite input required")
    return value


def timestamp(value):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative integer epoch milliseconds required")
    return value


@dataclass(frozen=True)
class Bar:
    t: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        timestamp(self.t)
        if self.t % MINUTE:
            raise ValueError("bar must start on a minute")
        for x in (self.open, self.high, self.low, self.close):
            finite(x, positive=True)
        finite(self.volume)
        if self.volume < 0 or not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("invalid OHLC/volume")


@dataclass(frozen=True)
class Session:
    day: str
    open_ms: int
    close_ms: int

    def __post_init__(self):
        date.fromisoformat(self.day)
        for t in (self.open_ms, self.close_ms):
            timestamp(t)
            if t % MINUTE:
                raise ValueError("unaligned session")
        a, b = (datetime.fromtimestamp(t / 1000, timezone.utc).astimezone(NY)
                for t in (self.open_ms, self.close_ms))
        if (a.date().isoformat() != self.day or b.date() != a.date()
                or a.weekday() >= 5 or (a.hour, a.minute) != (9, 30)
                or (b.hour, b.minute) not in ((13, 0), (16, 0))):
            raise ValueError("explicit NYSE-date session required")


@dataclass(frozen=True)
class Contract:
    size: float
    lot: float
    min_lots: float
    max_lots: float
    price_tick: float

    def __post_init__(self):
        for value in (self.size, self.lot, self.min_lots, self.max_lots, self.price_tick):
            finite(value, positive=True)
        if self.min_lots > self.max_lots:
            raise ValueError("invalid contract limits")


@dataclass(frozen=True)
class Cost:
    scale: int
    fee: float = 0.0008
    slippage: float = 0.0002

    def __post_init__(self):
        if type(self.scale) is not int or self.scale not in (1, 2, 3):
            raise ValueError("cost scale must be 1, 2 or 3")
        for x in (self.fee, self.slippage):
            finite(x)
            if x < 0 or x * self.scale >= 1:
                raise ValueError("invalid cost")


@dataclass(frozen=True)
class Funding:
    t: int
    rate: float

    def __post_init__(self):
        timestamp(self.t)
        finite(self.rate)


def index_bars(bars):
    """Reject duplicates and disorder rather than choosing a favorable revision."""
    out, prior = {}, -1
    for b in bars:
        if not isinstance(b, Bar) or b.t <= prior:
            raise ValueError("bars must be typed, unique and strictly ordered")
        out[b.t], prior = b, b.t
    return out


def decision(bars, session):
    """First parent ticket, using only complete bars through its decision.

    The OR is [09:30,10:00); eligible closes are strictly before 11:30.
    Entry is delayed one full minute after the signal bar closes.
    """
    first, end = session.open_ms, session.open_ms + 120 * MINUTE
    opening = []
    for t in range(first, first + 30 * MINUTE, MINUTE):
        if t not in bars:
            return {"status": "missing", "reason": "opening_bar", "t": t}
        opening.append(bars[t])
    hi, lo = max(b.high for b in opening), min(b.low for b in opening)
    total_v = math.fsum(b.volume for b in opening)
    pv = math.fsum((b.high + b.low + b.close) / 3 * b.volume for b in opening)
    mean_v = total_v / 30
    for t in range(first + 30 * MINUTE, min(end, session.close_ms) - MINUTE, MINUTE):
        if t not in bars:
            return {"status": "missing", "reason": "predecision_bar", "t": t}
        b = bars[t]
        total_v += b.volume
        pv += (b.high + b.low + b.close) / 3 * b.volume
        if b.close > hi:
            if total_v <= 0 or mean_v <= 0:
                return {"status": "missing", "reason": "volume_feature", "t": t}
            vw = pv / total_v
            vwap_ok, volume_ok = b.close > vw, b.volume >= 1.5 * mean_v
            return {"status": "ticket", "day": session.day, "decision_ms": t + MINUTE,
                    "entry_ms": t + 2 * MINUTE, "range_high": hi, "stop": lo,
                    "vwap": vw, "volume": b.volume, "opening_mean_volume": mean_v,
                    "accept": dict(parent=True, vwap=vwap_ok, volume=volume_ok,
                                   joint=vwap_ok and volume_ok)}
    return {"status": "cash", "reason": "no_parent"}


def path_exit(bars, ticket, session):
    """Bar proxy: touched stop exits next minute at worse of stop/next open.

    The scheduled exit is 16:01 (or 13:01), one minute after the cash close.
    This is an adverse fill convention, not proof an order could execute there.
    """
    entry = ticket["entry_ms"]
    end = session.close_ms + MINUTE
    if entry >= end or entry not in bars:
        return {"status": "missing", "reason": "entry_bar"}
    if bars[entry].volume <= 0:
        return {"status": "missing", "reason": "untraded_entry"}
    if bars[entry].open <= ticket["stop"]:
        return {"status": "cash", "reason": "entry_below_stop"}
    for t in range(entry, end, MINUTE):
        if t not in bars:
            return {"status": "missing", "reason": "held_bar", "t": t}
        b = bars[t]
        if b.volume <= 0:
            return {"status": "missing", "reason": "untraded_held_bar", "t": t}
        if b.low <= ticket["stop"]:
            if t + MINUTE not in bars:
                return {"status": "missing", "reason": "stop_exit_bar", "t": t + MINUTE}
            if bars[t + MINUTE].volume <= 0:
                return {"status": "missing", "reason": "untraded_stop_exit"}
            return {"status": "exit", "reason": "stop", "t": t + MINUTE,
                    "price": min(ticket["stop"], bars[t + MINUTE].open)}
    if end not in bars:
        return {"status": "missing", "reason": "scheduled_exit_bar", "t": end}
    if bars[end].volume <= 0:
        return {"status": "missing", "reason": "untraded_scheduled_exit"}
    return {"status": "exit", "reason": "scheduled", "t": end, "price": bars[end].open}


def _round_price(price, tick, buy):
    p, step = Decimal(str(price)), Decimal(str(tick))
    return float((p / step).to_integral_value(rounding=ROUND_CEILING if buy else ROUND_FLOOR) * step)


def account_trade(bars, fair, funding, ticket, exit_, contract, cost, equity, cap=1000.0):
    """One funded inventory-proxy trade, fair-open funding and adverse costs.

    Lot rounding is Decimal-based. Cash cannot borrow. Funding uses base units
    times the reported exact-event fair-price bar open, not entry notional.
    Caller must separately establish the coverage of the funding history.
    """
    finite(equity)
    finite(cap, positive=True)
    if exit_["status"] != "exit":
        raise ValueError("resolved exit required")
    start, end = ticket["entry_ms"], exit_["t"]
    relevant = [f for f in funding if start <= f.t <= end]
    if any(f.t in (start, end) for f in relevant):
        return {"status": "missing", "reason": "funding_boundary", "pnl": None}
    fmarks = []
    for f in relevant:
        if f.t not in fair:
            return {"status": "missing", "reason": "funding_fair_open", "pnl": None}
        fmarks.append((f.t, f.rate, fair[f.t].open))
    fee = cost.fee * cost.scale
    e = _round_price(bars[start].open * (1 + cost.slippage * cost.scale), contract.price_tick, True)
    x = _round_price(exit_["price"] * (1 - cost.slippage * cost.scale), contract.price_tick, False)
    if x <= 0:
        raise ValueError("cost-adjusted price is nonpositive")
    budget = min(cap, max(0.0, equity) / (1 + 2 * fee))
    lots = (Decimal(str(budget)) / (Decimal(str(e)) * Decimal(str(contract.size)))
            / Decimal(str(contract.lot))).to_integral_value(rounding=ROUND_FLOOR) * Decimal(str(contract.lot))
    lots = min(lots, (Decimal(str(contract.max_lots)) / Decimal(str(contract.lot))).to_integral_value(
        rounding=ROUND_FLOOR) * Decimal(str(contract.lot)))
    if lots < Decimal(str(contract.min_lots)):
        return {"status": "cash", "reason": "min_lot", "pnl": 0.0, "lots": 0.0}
    quantity = float(lots * Decimal(str(contract.size)))
    entry_fee, exit_fee = quantity * e * fee, quantity * x * fee
    cash = equity - quantity * e - entry_fee
    paid = 0.0
    by_time = {t: (rate, mark) for t, rate, mark in fmarks}
    for t in range(start, end, MINUTE):
        if t in by_time:
            rate, mark = by_time[t]
            charge = quantity * mark * rate
            cash -= charge
            paid += charge
        if cash < -1e-9 or cash + quantity * bars[t].low <= 0:
            return {"status": "insolvent", "reason": "cash_or_mark", "pnl": None,
                    "t": t, "funding": paid}
    gross = quantity * (x - e)
    pnl = gross - entry_fee - exit_fee - paid
    return {"status": "trade", "pnl": pnl, "lots": float(lots), "quantity": quantity,
            "entry_ms": start, "exit_ms": end, "entry": e, "exit": x,
            "raw_entry": bars[start].open, "raw_exit": exit_["price"],
            "gross_before_costs": quantity * (exit_["price"] - bars[start].open),
            "raw_turnover": quantity * (exit_["price"] + bars[start].open),
            "price_pnl_after_slippage": gross, "fees": entry_fee + exit_fee, "funding": paid,
            "exit_reason": exit_["reason"], "equity_after": equity + pnl}


def run_family(bars, fair, funding, sessions, calendar, contract, initial=2000.0, closed_days=()):
    """All four arms and all three cost tiers; no selecting or deleting days.

    Once an account has an unknown outcome it remains unknown on later days.
    Cash outcomes remain known when their own rule rejected the shared ticket.
    """
    finite(initial, positive=True)
    bars, fair = index_bars(bars), index_bars(fair)
    if any(not isinstance(f, Funding) for f in funding) or any(a.t >= b.t for a, b in zip(funding, funding[1:])):
        raise ValueError("funding must be typed, unique and ordered")
    if not calendar or calendar != sorted(set(calendar)) or any(date.fromisoformat(d).isoformat() != d for d in calendar):
        raise ValueError("unique ordered ISO calendar required")
    a, b = date.fromisoformat(calendar[0]), date.fromisoformat(calendar[-1])
    if calendar != [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]:
        raise ValueError("complete calendar required")
    session_map = {s.day: s for s in sessions}
    if len(session_map) != len(sessions) or not set(session_map) <= set(calendar):
        raise ValueError("duplicate or out-of-calendar session")
    if len(set(closed_days)) != len(closed_days) or not set(closed_days) <= set(calendar) or set(closed_days) & set(session_map):
        raise ValueError("invalid closed-date declaration")
    if any(date.fromisoformat(d).weekday() < 5 and d not in session_map and d not in closed_days for d in calendar):
        raise ValueError("weekday missing explicit session/holiday")
    keys = [f"{a}_{s}x" for s in (1, 2, 3) for a in ARMS]
    equities = dict.fromkeys(keys, initial)
    rows = []
    for day in calendar:
        session = session_map.get(day)
        dec = decision(bars, session) if session else {"status": "cash", "reason": "calendar_closed"}
        ex = path_exit(bars, dec, session) if dec["status"] == "ticket" else None
        accounts = {}
        for scale in (1, 2, 3):
            for arm in ARMS:
                key = f"{arm}_{scale}x"
                equity = equities[key]
                if equity is None:
                    r = {"status": "missing", "reason": "prior_unknown", "pnl": None}
                elif dec["status"] == "missing":
                    r = {"status": "missing", "reason": dec["reason"], "pnl": None}
                elif dec["status"] == "cash" or not dec["accept"][arm]:
                    r = {"status": "cash", "reason": dec.get("reason", "filter"), "pnl": 0.0}
                elif ex["status"] != "exit":
                    r = {"status": ex["status"], "reason": ex["reason"],
                         "pnl": 0.0 if ex["status"] == "cash" else None}
                else:
                    r = account_trade(bars, fair, funding, dec, ex, contract, Cost(scale), equity)
                equities[key] = None if r["pnl"] is None else equity + r["pnl"]
                accounts[key] = r
        rows.append({"day": day, "decision": dec, "exit": ex, "accounts": accounts})
    complete = all(v is not None for v in equities.values())
    return {"complete": complete, "initial_equity_each": initial, "equity": equities, "days": rows,
            "scope": "conditional funded bar-account proxy; no order, margin engine or verified fills"}
