"""Strict decoding of MEXC Futures depth level rows.

The live Futures REST and WebSocket payloads observed on 2026-10-23 use
``[price, contract_quantity, order_count]``. This is also the order in MEXC's
legacy contract docs. The current REST/WS prose labels the last two values in
the opposite order; see ``experiments/mexc_costs/REVIEW.md`` for the bounded
primary-source cross-check. ``contract_quantity`` is denominated in contracts;
multiply it by the contract's ``contractSize`` before using it as base-coin
quantity.

This helper handles full depth snapshots (whose levels must have positive
quantity). Incremental depth updates have separate delete semantics and must
be applied by a sequence-aware book builder before constructing a snapshot.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from numbers import Real


def _number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (Real, str)):
        raise ValueError(f"{name} must be a finite number")
    try:
        out = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not isfinite(out):
        raise ValueError(f"{name} must be a finite number")
    return out


def parse_mexc_depth_level(level: object) -> tuple[float, float]:
    """Parse one raw MEXC row as ``(price, contract_quantity)``."""
    if not isinstance(level, (list, tuple)) or len(level) != 3:
        raise ValueError("MEXC depth level must be a three-field list or tuple")
    price = _number("price", level[0])
    quantity = _number("contract_quantity", level[1])
    order_count = _number("order_count", level[2])
    if price <= 0:
        raise ValueError("price must be positive")
    if order_count < 0 or not order_count.is_integer():
        raise ValueError("order_count must be a nonnegative integer")
    if quantity < 0:
        raise ValueError("contract_quantity must be nonnegative")
    return price, quantity


@dataclass(frozen=True, slots=True)
class MexcDepthLevel:
    """One validated MEXC depth level; quantity is in contracts."""

    price: float
    order_count: int
    quantity_contracts: float

    def __post_init__(self) -> None:
        price = _number("price", self.price)
        count = _number("order_count", self.order_count)
        quantity = _number("contract_quantity", self.quantity_contracts)
        if price <= 0:
            raise ValueError("price must be positive")
        if count <= 0 or not count.is_integer():
            raise ValueError("snapshot order_count must be a positive integer")
        if quantity <= 0:
            raise ValueError("snapshot contract_quantity must be positive")
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "order_count", int(count))
        object.__setattr__(self, "quantity_contracts", quantity)

    def base_quantity(self, contract_size: float) -> float:
        """Return base-coin units after applying the contract size."""
        size = _number("contract_size", contract_size)
        if size <= 0:
            raise ValueError("contract_size must be positive")
        quantity = self.quantity_contracts * size
        if not isfinite(quantity):
            raise ValueError("base quantity must be finite")
        return quantity

    def bookwalk_row(self) -> tuple[float, float, int]:
        """Compatibility projection ``(price, quantity, order_count)`` for R224's helpers.

        The frozen recorder's walk helpers read the first value after price as
        quantity, so raw MEXC rows must never be passed directly.
        """
        return self.price, self.quantity_contracts, self.order_count


def parse_depth_levels(rows: Iterable[object]) -> tuple[MexcDepthLevel, ...]:
    """Decode a nonempty full-depth side and fail closed on malformed rows."""
    if isinstance(rows, (str, bytes, bytearray)):
        raise ValueError("depth rows must be an iterable of three-field levels")
    try:
        source = iter(rows)
    except TypeError as exc:
        raise ValueError("depth rows must be an iterable of three-field levels") from exc
    out = []
    for i, raw in enumerate(source):
        price, quantity = parse_mexc_depth_level(raw)
        count = int(_number(f"depth level {i} order_count", raw[2]))
        if quantity <= 0:
            raise ValueError(f"depth level {i} snapshot quantity must be positive")
        out.append(MexcDepthLevel(price, count, quantity))
    if not out:
        raise ValueError("depth side must contain at least one level")
    return tuple(out)
