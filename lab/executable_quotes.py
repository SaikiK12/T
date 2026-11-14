"""First-seen REST book contract and conditional two-venue crossing costs.

This supplements the existing MEXC decoder and microstructure types. It never
invents the exchange clock required by DepthSnapshot, equates a batch start to
first receipt, or turns displayed liquidity into a fill. Fees are explicit
scenario inputs, never inferred from absent account/public metadata.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from math import fsum, isfinite, lcm

from lab.mexc_depth import parse_depth_levels
from lab.microstructure import DepthLevel


def positive(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not a price/quantity")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("positive finite decimal required")
    return number


@dataclass(frozen=True)
class Receipt:
    """Request interval on UTC and one process's monotonic clock, in ns."""
    started_utc_ns: int
    received_utc_ns: int
    started_mono_ns: int
    received_mono_ns: int

    def __post_init__(self):
        values = tuple(vars(self).values())
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in values):
            raise ValueError("receipt clocks must be nonnegative integer ns")
        if self.received_mono_ns < self.started_mono_ns:
            raise ValueError("monotonic receive precedes request")

    @property
    def latency_ns(self):
        return self.received_mono_ns - self.started_mono_ns

    @property
    def clock_step_ns(self):
        return abs((self.received_utc_ns - self.started_utc_ns) - self.latency_ns)


@dataclass(frozen=True)
class RestBook:
    venue: str
    symbol: str
    receipt: Receipt
    bids: tuple[DepthLevel, ...]
    asks: tuple[DepthLevel, ...]
    reported_timestamp_ms: int | None
    timestamp_role: str
    version: int | None

    def __post_init__(self):
        if self.venue not in ("mexc", "lighter") or not self.symbol:
            raise ValueError("unknown venue or symbol")
        if not isinstance(self.receipt, Receipt):
            raise ValueError("validated receipt required")
        for side in (self.bids, self.asks):
            if not side or any(not isinstance(x, DepthLevel) for x in side):
                raise ValueError("validated nonempty depth required")
        if any(a.price <= b.price for a, b in zip(self.bids, self.bids[1:])):
            raise ValueError("distinct descending bids required")
        if any(a.price >= b.price for a, b in zip(self.asks, self.asks[1:])):
            raise ValueError("distinct ascending asks required")
        if self.bids[0].price >= self.asks[0].price:
            raise ValueError("crossed or locked book")
        for value in (self.reported_timestamp_ms, self.version):
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError("invalid provider timestamp/version")

    @property
    def mid(self):
        return self.bids[0].price / 2 + self.asks[0].price / 2


def _aggregate(rows, descending):
    sizes = {}
    for price, size in rows:
        # Decimal keys coalesce repeated orders at exactly the same price.
        price, size = positive(price), positive(size)
        sizes.setdefault(price, []).append(float(size))
    return tuple(DepthLevel(float(p), fsum(sizes[p])) for p in sorted(sizes, reverse=descending))


def mexc_book(symbol, payload, metadata, receipt):
    if payload.get("success") is not True or metadata.get("symbol") != symbol:
        raise ValueError("MEXC response/metadata identity mismatch")
    size = positive(metadata["contractSize"])
    source = payload["data"]
    sides = [_aggregate(((x.price, positive(x.quantity_contracts) * size)
                         for x in parse_depth_levels(source[name])), name == "bids")
             for name in ("bids", "asks")]
    # A deeper REST response cannot make an API market order sweep more
    # levels than the contract's own current market-order limit.
    limit = metadata.get("marketOrderMaxLevel")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("unknown MEXC market-order depth limit")
    sides = [side[:limit] for side in sides]
    return RestBook("mexc", symbol, receipt, *sides, source.get("timestamp"),
                    "provider_system_time_not_verified_book_event_time", source.get("version"))


def lighter_book(symbol, payload, receipt):
    if payload.get("code") != 200:
        raise ValueError("Lighter response is not successful")
    sides = [_aggregate(((r["price"], r["remaining_base_amount"]) for r in payload[name]), name == "bids")
             for name in ("bids", "asks")]
    # REST documentation defines no matching-engine timestamp. Preserve any
    # raw fields in the receipt evidence; do not guess their role or units.
    return RestBook("lighter", symbol, receipt, *sides, None, "not_documented_in_rest_contract", None)


def common_quantity(mexc, lighter, max_mid, leg_budget=250):
    """Exact common base lattice, rounded DOWN; never two independently sized legs."""
    if type(mexc.get("type")) is not int or mexc["type"] != 1 or mexc.get("settleCoin") != "USDT":
        raise ValueError("unsupported MEXC payout units")
    decimals = lighter["supported_size_decimals"]
    if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 12:
        raise ValueError("unsupported Lighter precision")
    a = positive(mexc["contractSize"]) * positive(mexc["volUnit"])
    b = Decimal(10) ** -decimals
    denominator = lcm(a.as_integer_ratio()[1], b.as_integer_ratio()[1])
    an = a.as_integer_ratio()[0] * (denominator // a.as_integer_ratio()[1])
    bn = b.as_integer_ratio()[0] * (denominator // b.as_integer_ratio()[1])
    step = Decimal(lcm(an, bn)) / Decimal(denominator)
    q = (positive(leg_budget) / positive(max_mid) / step).to_integral_value(rounding=ROUND_FLOOR) * step
    minimum = max(positive(mexc["minVol"]) * positive(mexc["contractSize"]),
                  positive(lighter["min_base_amount"]))
    min_quote = positive(lighter["min_quote_amount"])
    if q < minimum or q * positive(max_mid) < min_quote:
        raise ValueError("common lot below a venue's minimum")
    if "maxVol" in mexc and q > positive(mexc["maxVol"]) * positive(mexc["contractSize"]):
        raise ValueError("common lot above MEXC maxVol")
    return q, step


def walk(side, quantity):
    """Quote cash for exactly quantity BASE, or None for insufficient shown depth."""
    left = positive(quantity)
    cash = Decimal(0)
    for level in side:
        take = min(left, positive(level.size))
        cash += take * positive(level.price)
        left -= take
        if left == 0:
            return float(cash)
    return None


def pair_costs(mexc, lighter, quantity, fees_bp=(10., 4.), capital=10_000.):
    """Same-snapshot ENTRY+EXIT spread/depth+fees: a conditional cost, not PnL.

    No cross-venue cash netting. Capital remains $5k per venue; size is never
    increased to fit a fee scenario. The 1x/2x/3x multiplier stresses the whole
    displayed crossing plus the explicit charge reserve. R310's 10/4 bp values
    were total-cost assumptions, not verified exchange fees. Reusing them here
    as a reserve PLUS observed crossing is deliberately conservative, not an
    exact replay of its old all-in costs or a measured account fee schedule.
    One-leg bp denominator is q * mean(mid_M,mid_L); capital bp uses $10k.
    """
    if mexc.venue != "mexc" or lighter.venue != "lighter":
        raise ValueError("venue order must be MEXC then Lighter")
    if len(fees_bp) != 2 or any(not isfinite(f) or f < 0 for f in fees_bp):
        raise ValueError("explicit finite nonnegative fees required")
    capital = float(positive(capital))
    q = float(positive(quantity))
    result = {"quantity_base": q, "capital_usd": capital, "displayed_fillable": False}
    fills = [walk(side, quantity) for b in (mexc, lighter) for side in (b.asks, b.bids)]
    capacities = [min(fsum(x.size for x in b.asks), fsum(x.size for x in b.bids)) for b in (mexc, lighter)]
    result["shown_two_way_capacity_base"] = min(capacities)
    if any(x is None for x in fills):
        return result
    mbuy, msell, lbuy, lsell = fills
    notionals = [q * mexc.mid, q * lighter.mid]
    if any(n > capital / 2 for n in notionals):
        raise ValueError("leg exceeds its segregated capital")
    crossing = fsum((mbuy, -msell, lbuy, -lsell))
    fee = (mbuy + msell) * fees_bp[0] / 1e4 + (lbuy + lsell) * fees_bp[1] / 1e4
    leg_notional = fsum(notionals) / 2
    result.update(displayed_fillable=True, leg_mid_notional_usd=leg_notional,
                  long_mexc_entry_cost_usd=(mbuy-notionals[0]) + (notionals[1]-lsell)
                                            + mbuy*fees_bp[0]/1e4 + lsell*fees_bp[1]/1e4,
                  long_lighter_entry_cost_usd=(lbuy-notionals[1]) + (notionals[0]-msell)
                                               + msell*fees_bp[0]/1e4 + lbuy*fees_bp[1]/1e4,
                  crossing_usd=crossing, fee_usd=fee,
                  venue_margin_mid_notionals_usd=notionals,
                  scenarios=[{"multiple": k, "round_trip_cost_usd": k*(crossing+fee),
                              "break_even_leg_bp": k*(crossing+fee)/leg_notional*1e4,
                              "capital_cost_bp": k*(crossing+fee)/capital*1e4} for k in (1, 2, 3)])
    return result


def receipt_quality(books, asof_mono_ns, *, age_ns=5_000_000_000, skew_ns=1_000_000_000):
    """Local availability only. A good local clock does NOT certify a source book."""
    issues = []
    if len(books) != 2:
        raise ValueError("exactly two books required")
    for book in books:
        r = book.receipt
        if not 0 <= asof_mono_ns - r.received_mono_ns <= age_ns:
            issues.append(book.venue + ":first_seen_stale_or_future")
        if r.latency_ns > age_ns or r.clock_step_ns > 50_000_000:
            issues.append(book.venue + ":slow_request_or_clock_step")
    if abs(books[0].receipt.received_mono_ns - books[1].receipt.received_mono_ns) > skew_ns:
        issues.append("cross_venue_receipt_skew")
    return {"first_seen_pair_ok": not issues, "first_seen_flags": issues,
            "execution_ready": False,
            "execution_blockers": ["REST_book_event_age_unverified", "latency_and_fill_unverified"]}
