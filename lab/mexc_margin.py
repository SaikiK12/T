"""Pure MEXC USDT-M margin arithmetic for explicit, caller-supplied risk tiers.

This module performs no requests, account access, orders or historical simulation.
It uses fair price for unrealized PnL, the entry notional and caller-supplied
maintenance rate for the fixed tier, and caller-supplied liquidation fees/cashflows.
The MEXC public risk-limit documentation identifies its endpoint as private and
requiring "View Order Details"; this code never fetches that account-specific data.

Official rules reviewed 2026-10-23:
- MEXC margin guide (position value, initial/maintenance margin, isolated price):
  https://www.mexc.com/support/article/mexc-margin-calculation-guide-312054740132052992
- MEXC liquidation FAQ (fair-price trigger and cross-margin equity condition):
  https://www.mexc.co/support/article/faq-on-liquidation-for-futures-trading-8123281969561
- Risk-limit endpoint permission and fields:
  https://www.mexc.co/api-docs/futures/account-and-trading-endpoints/get-risk-limits

These formulas are an accounting kernel, not a full exchange replica. The caller
must supply the applicable risk tier, position margin, liquidation fee and settled
cashflows. Tier transitions, open-order margin, auto-add, partial liquidation,
ADL, transfer delays and execution are not modelled. A cross snapshot must contain
only cross-margin positions from one MEXC account at one common fair-price timestamp;
it never nets collateral across venues. The cross-wallet input must already exclude
isolated-position margin and open-order margin, as in MEXC's published cross-equity
condition.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real
from typing import Sequence


def _finite(value, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


@dataclass(frozen=True, slots=True)
class MexcLinearPosition:
    """One signed-size linear USDT-M position with a fixed supplied risk tier.

    ``side`` is +1 for long and -1 for short. ``contracts`` is a positive
    contract count; ``contract_size`` is base units per contract. ``mmr`` is a
    rate for the position's selected tier, not a fee schedule lookup.
    """

    symbol: str
    side: int
    entry_price: float
    contracts: float
    contract_size: float
    mmr: float
    liquidation_fee_usdt: float = 0.0

    def __post_init__(self):
        if not isinstance(self.symbol, str) or not self.symbol.endswith("_USDT") or not self.symbol[:-5]:
            raise ValueError("symbol must be a MEXC USDT-M contract such as BTC_USDT")
        if isinstance(self.side, bool) or not isinstance(self.side, Integral) or int(self.side) not in (-1, 1):
            raise ValueError("side must be +1 (long) or -1 (short)")
        object.__setattr__(self, "side", int(self.side))
        for name, positive, nonnegative in (
            ("entry_price", True, False), ("contracts", True, False),
            ("contract_size", True, False), ("mmr", False, True),
            ("liquidation_fee_usdt", False, True),
        ):
            value = _finite(getattr(self, name), name, positive=positive, nonnegative=nonnegative)
            if name == "mmr" and value >= 1:
                raise ValueError("mmr must be below 1")
            object.__setattr__(self, name, value)
        derived = (self.base_quantity, self.entry_notional_usdt, self.maintenance_usdt)
        if (not math.isfinite(derived[0]) or derived[0] <= 0
                or not math.isfinite(derived[1]) or derived[1] <= 0
                or not math.isfinite(derived[2])):
            raise ValueError("position size, notional and maintenance margin must remain finite")

    @property
    def base_quantity(self) -> float:
        return self.contracts * self.contract_size

    @property
    def entry_notional_usdt(self) -> float:
        return self.entry_price * self.base_quantity

    @property
    def maintenance_usdt(self) -> float:
        # Matches the reviewed MEXC guide's entry-price × size × MMR formula.
        return self.entry_notional_usdt * self.mmr


@dataclass(frozen=True, slots=True)
class MarginState:
    equity_usdt: float
    maintenance_usdt: float
    liquidation_fee_usdt: float
    requirement_usdt: float
    margin_rate: float
    liquidated: bool
    unrealized_pnl_usdt: float
    cashflow_usdt: float


@dataclass(frozen=True, slots=True)
class CrossPath:
    timestamps_ms: tuple[int, ...]
    states: tuple[MarginState, ...]
    first_breach_index: int | None
    first_breach_ms: int | None


def isolated_state(position: MexcLinearPosition, fair_price: float, position_margin_usdt: float,
                   *, added_margin_usdt: float = 0.0, cashflow_usdt: float = 0.0) -> MarginState:
    """Evaluate an isolated position at one fair price using a fixed tier.

    ``cashflow_usdt`` is signed settled funding/fees since entry (+credit,
    -debit) that has not already been included in position margin; it is not a
    forecast. ``added_margin_usdt`` is explicit collateral added to this
    position. Equity at or below maintenance plus liquidation fee is treated as
    a breach, matching the conservative equality boundary. The liquidation fee
    is a fixed caller-supplied amount for this calculation; any fee schedule or
    price-dependent fee must be resolved by the caller.
    """
    fair = _finite(fair_price, "fair_price", positive=True)
    margin = _finite(position_margin_usdt, "position_margin_usdt", nonnegative=True)
    added = _finite(added_margin_usdt, "added_margin_usdt", nonnegative=True)
    cash = _finite(cashflow_usdt, "cashflow_usdt")
    upnl = position.side * position.base_quantity * (fair - position.entry_price)
    equity = margin + added + cash + upnl
    maintenance = position.maintenance_usdt
    fee = position.liquidation_fee_usdt
    requirement = maintenance + fee
    rate = requirement / equity if equity > 0 else math.inf
    values = (upnl, equity, maintenance, fee, requirement)
    if any(not math.isfinite(x) for x in values):
        raise ValueError("isolated margin arithmetic produced a non-finite result")
    return MarginState(equity, maintenance, fee, requirement, rate, equity <= requirement, upnl, cash)


def isolated_liquidation_price(position: MexcLinearPosition, position_margin_usdt: float,
                               *, added_margin_usdt: float = 0.0, cashflow_usdt: float = 0.0) -> float | None:
    """Solve the fixed-tier fair-price threshold; ``None`` means no positive long threshold.

    MMR is held at the supplied tier's entry-notional requirement. Risk-tier
    changes as notional moves are outside this equation and must be handled by
    a path simulator with the venue's tier schedule.
    """
    margin = _finite(position_margin_usdt, "position_margin_usdt", nonnegative=True)
    added = _finite(added_margin_usdt, "added_margin_usdt", nonnegative=True)
    cash = _finite(cashflow_usdt, "cashflow_usdt")
    qty = position.base_quantity
    threshold = position.maintenance_usdt + position.liquidation_fee_usdt
    if position.side == 1:
        price = position.entry_price + (threshold - margin - added - cash) / qty
    else:
        price = position.entry_price + (margin + added + cash - threshold) / qty
    if not math.isfinite(price):
        raise ValueError("isolated liquidation arithmetic produced a non-finite result")
    return price if price > 0 else None


def cross_state(wallet_balance_usdt: float, positions: Sequence[MexcLinearPosition],
                fair_prices: Sequence[float], *, cashflows_usdt: Sequence[float] | None = None) -> MarginState:
    """Evaluate all supplied positions on one MEXC cross-margin account snapshot.

    Fair prices and signed settled cashflows must align one-for-one with the
    positions at the same timestamp. ``wallet_balance_usdt`` is the cross-eligible
    wallet component after excluding isolated-position margin and open-order
    margin, but before the separate ``cashflows_usdt`` values. Cross-position
    initial margin is not subtracted a second time. This helper does not infer
    balances from leverage. No cross-venue collateral netting is possible here.
    """
    wallet = _finite(wallet_balance_usdt, "wallet_balance_usdt", nonnegative=True)
    positions = tuple(positions)
    marks = tuple(fair_prices)
    flows = (0.0,) * len(positions) if cashflows_usdt is None else tuple(cashflows_usdt)
    if len(marks) != len(positions) or len(flows) != len(positions):
        raise ValueError("positions, fair_prices and cashflows_usdt must have equal lengths")
    upnl = cash = maintenance = fees = 0.0
    for position, mark, flow in zip(positions, marks, flows):
        if not isinstance(position, MexcLinearPosition):
            raise ValueError("positions must contain MexcLinearPosition values")
        fair = _finite(mark, "fair_price", positive=True)
        cashflow = _finite(flow, "cashflow_usdt")
        upnl += position.side * position.base_quantity * (fair - position.entry_price)
        cash += cashflow
        maintenance += position.maintenance_usdt
        fees += position.liquidation_fee_usdt
    equity = wallet + upnl + cash
    requirement = maintenance + fees
    rate = requirement / equity if equity > 0 else math.inf
    if any(not math.isfinite(x) for x in (upnl, cash, maintenance, fees, requirement, equity)):
        raise ValueError("cross margin arithmetic produced a non-finite result")
    return MarginState(equity, maintenance, fees, requirement, rate, equity <= requirement, upnl, cash)


def cross_path(positions: Sequence[MexcLinearPosition], timestamps_ms: Sequence[int],
               wallet_balances_usdt: Sequence[float], fair_prices_by_time: Sequence[Sequence[float]]) -> CrossPath:
    """Replay one MEXC cross account at synchronized fair-price snapshots.

    Every row of ``fair_prices_by_time`` must contain one fair price per position
    from the same timestamp. ``wallet_balances_usdt`` must be the wallet cash at
    that timestamp, including settled funding/fees. Times must be strictly
    increasing; this function does not fill gaps, infer bar clocks, combine
    independent intraday extremes, or model event order between snapshots. The
    caller must establish source-time semantics and complete coverage before
    using the path as risk evidence.
    """
    positions = tuple(positions)
    if any(not isinstance(position, MexcLinearPosition) for position in positions):
        raise ValueError("positions must contain MexcLinearPosition values")
    times = tuple(timestamps_ms)
    balances = tuple(wallet_balances_usdt)
    marks = tuple(tuple(row) for row in fair_prices_by_time)
    if not (len(times) == len(balances) == len(marks)):
        raise ValueError("timestamps, wallet balances and mark rows must have equal lengths")
    normalized_times = []
    for value in times:
        if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
            raise ValueError("timestamps_ms must be nonnegative integers")
        normalized_times.append(int(value))
    if any(a >= b for a, b in zip(normalized_times, normalized_times[1:])):
        raise ValueError("timestamps_ms must be strictly increasing")
    states = []
    first = None
    for index, (balance, row) in enumerate(zip(balances, marks)):
        if len(row) != len(positions):
            raise ValueError("each fair-price row must contain one value per position")
        state = cross_state(balance, positions, row)
        states.append(state)
        if first is None and state.liquidated:
            first = index
    first_ms = normalized_times[first] if first is not None else None
    return CrossPath(tuple(normalized_times), tuple(states), first, first_ms)
