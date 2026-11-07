"""Conditional depth sweeps and segregated linear-perp cash accounting.

Only supplied depth exists. Fixed base inventory is never rebalanced or reopened
after a forced close. Venue tiers, fees, funding cash and forced-close prices
must be supplied explicitly; these calculations do not certify actual fills,
venue access, collateral conversion or a historical liquidation algorithm.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from math import gcd, lcm


ZERO = Decimal(0)


def number(value, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or value is None:
        raise ValueError("explicit finite number required")
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid number") from exc
    if not out.is_finite() or abs(out) > Decimal("1e30"):
        raise ValueError("number outside supported range")
    if positive and out <= 0 or nonnegative and out < 0:
        raise ValueError("number has invalid sign")
    return out


@dataclass(frozen=True)
class Book:
    bids: tuple
    asks: tuple

    def __post_init__(self):
        for name in ("bids", "asks"):
            rows = tuple((number(p, positive=True), number(q, positive=True))
                         for p, q in getattr(self, name))
            if not rows or len(rows) > 10000:
                raise ValueError("bounded nonempty depth required")
            if any((p <= r if name == "bids" else p >= r)
                   for (p, _), (r, _) in zip(rows, rows[1:])):
                raise ValueError("depth must be unique and ordered best first")
            object.__setattr__(self, name, rows)
        if self.bids[0][0] >= self.asks[0][0]:
            raise ValueError("crossed or locked book")

    @property
    def mid(self):
        return (self.bids[0][0] + self.asks[0][0]) / 2


@dataclass(frozen=True)
class Tier:
    """Explicit notional ceiling and rates, with a maintenance deduction.

    Exact boundary belongs to the lower tier. Beyond the largest supplied tier
    is unknown. Provider-specific tier construction belongs in an input adapter.
    """
    ceiling: Decimal
    initial: Decimal
    maintenance: Decimal
    deduction: Decimal = ZERO

    def __post_init__(self):
        for name in ("ceiling", "initial", "maintenance", "deduction"):
            object.__setattr__(self, name, number(getattr(self, name), nonnegative=True))
        if not self.ceiling or not 0 < self.maintenance <= self.initial <= 1:
            raise ValueError("invalid tier rates or ceiling")
        if self.deduction > self.ceiling * self.maintenance:
            raise ValueError("maintenance deduction exceeds tier requirement")


def requirement(tiers, notional, *, initial=False):
    n = number(notional, nonnegative=True)
    if not n:
        return ZERO
    if not tiers:
        return None
    if any(a.ceiling >= b.ceiling for a, b in zip(tiers, tiers[1:])):
        raise ValueError("tiers must have increasing ceilings")
    for tier in tiers:
        if n <= tier.ceiling:
            return n * tier.initial if initial else max(ZERO, n * tier.maintenance - tier.deduction)
    return None


def sweep(book, side, quantity, *, fee_rate=None, multiple=1):
    """Base-quantity sweep; keep partial fills and missing fees explicit.

    Sensitivity scales spread/impact relative to the supplied mid and the fee
    rate, holding inventory and displayed depth fixed. It is a cost scenario,
    not a claim that a 2x/3x synthetic price appeared in the recorded book.
    """
    q = number(quantity, positive=True)
    m = number(multiple, positive=True)
    if side not in ("buy", "sell") or m not in (1, 2, 3):
        raise ValueError("explicit side and 1x/2x/3x cost required")
    fee = None if fee_rate is None else number(fee_rate, nonnegative=True)
    if fee is not None and fee > 1:
        raise ValueError("fee fraction above one")
    left, quote = q, ZERO
    for price, available in book.asks if side == "buy" else book.bids:
        take = min(left, available)
        stressed_price = book.mid + m * (price - book.mid)
        if stressed_price <= 0:
            raise ValueError("cost sensitivity implies nonpositive price")
        quote += take * stressed_price
        left -= take
        if not left:
            break
    filled = q - left
    drag = quote - filled * book.mid if side == "buy" else filled * book.mid - quote
    return dict(requested=q, filled=filled, complete=not left, quote=quote,
                vwap=quote / filled if filled else None, book_cost=drag,
                fee=None if fee is None else quote * fee * m)


def common_quantity(target, books, lots):
    a, b = (Fraction(number(x, positive=True)) for x in lots)
    common = Fraction(lcm(a.numerator, b.numerator), gcd(a.denominator, b.denominator))
    step = Decimal(common.numerator) / Decimal(common.denominator)
    q = number(target, positive=True) // (max(x.mid for x in books) * step) * step
    return q, step


def pair_sweep(target, books, lots, minima, fees, *, multiple=1):
    """Both directions, same lot-matched quantity, no basis profit or future exit.

    The target is MID notional per leg, not total account capital. Cross-venue
    quote parity and common economic identity must be established by the caller.
    """
    if any(len(x) != 2 for x in (books, lots, minima, fees)):
        raise ValueError("exactly two legs required")
    q, step = common_quantity(target, books, lots)
    if q <= 0 or any(q < number(x, positive=True) for x in minima):
        return dict(state="BLOCKED_MINIMUM", quantity=q, common_lot=step, directions=[])
    out = []
    for buyer, seller in ((0, 1), (1, 0)):
        buy = sweep(books[buyer], "buy", q, fee_rate=fees[buyer], multiple=multiple)
        sell = sweep(books[seller], "sell", q, fee_rate=fees[seller], multiple=multiple)
        complete = buy["complete"] and sell["complete"]
        fee = None if buy["fee"] is None or sell["fee"] is None else buy["fee"] + sell["fee"]
        cost = buy["book_cost"] + sell["book_cost"]
        out.append(dict(buyer=buyer, seller=seller, state="SHOWN_DEPTH" if complete else "PARTIAL_PAIR",
                        buy=buy, sell=sell, unmatched_base=buy["filled"] - sell["filled"],
                        book_cost=cost, fee=fee,
                        complete_entry_cost=cost + fee if complete and fee is not None else None))
    return dict(state="CONDITIONAL_SNAPSHOT", quantity=q, common_lot=step, directions=out)


@dataclass
class Wallet:
    quantity: Decimal
    entry: Decimal
    cash: Decimal
    tiers: tuple
    fee_rate: Decimal
    liquidation_fee: Decimal
    fees: Decimal = ZERO
    funding: Decimal = ZERO
    realized: Decimal = ZERO
    ever_insolvent: bool = False

    def equity(self, mark):
        return self.cash + self.quantity * (mark - self.entry)

    def close(self, fill, *, penalty=ZERO):
        sign = 1 if self.quantity > 0 else -1
        qty = fill["filled"]
        if qty > abs(self.quantity) or fill["fee"] is None:
            raise ValueError("close exceeds inventory or has unknown fee")
        pnl = sign * qty * (fill["vwap"] - self.entry)
        charge = fill["fee"] + penalty * fill["quote"]
        self.cash += pnl - charge
        self.realized += pnl
        self.fees += charge
        self.quantity -= sign * qty
        # Preserve cash deficits. The other venue never recapitalizes this one
        # implicitly, and a later recovery never reopens this quantity.
        self.ever_insolvent |= self.cash < 0


def stress_replay(case, notional, *, multiple=1):
    """Replay an explicit, already normalized two-linear-perp scenario.

    Each leg starts with cash equal to the requested MID notional (1x per leg;
    total funded capital 2N). Funding is explicit cash, including explicit zero.
    Tiers and liquidation trigger are supplied scenario assumptions. This is
    discrete marked solvency, not an exchange's continuous liquidation engine.
    """
    n, m = number(notional, positive=True), number(multiple, positive=True)
    if m not in (1, 2, 3):
        raise ValueError("1x/2x/3x costs required")
    keys = ("long", "short")
    books = tuple(Book(**case["entry_books"][k]) for k in keys)
    q, _ = common_quantity(n, books, (case["lot"], case["lot"]))
    if q <= 0:
        raise ValueError("zero entry quantity")
    wallets = {}
    for key, book, side in zip(keys, books, ("buy", "sell")):
        conf = case["legs"][key]
        tiers = tuple(Tier(**x) for x in conf["tiers"]) if conf["tiers"] is not None else ()
        fill = sweep(book, side, q, fee_rate=conf["fee_rate"], multiple=m)
        if not fill["complete"] or fill["fee"] is None:
            return dict(state="ENTRY_UNFILLED_OR_FEE_UNKNOWN", final_net=None, rows=[])
        w = Wallet(q if key == "long" else -q, fill["vwap"], n - fill["fee"], tiers,
                   number(conf["fee_rate"], nonnegative=True),
                   number(conf["liquidation_fee"], nonnegative=True), fees=fill["fee"])
        im = requirement(tiers, q * book.mid, initial=True)
        if im is not None and w.equity(book.mid) < im:
            return dict(state="ENTRY_MARGIN_BLOCK", final_net=None, rows=[])
        wallets[key] = w
    rows, margin_unknown, prev = [], False, None
    for event in case["events"]:
        t = event["time_ms"]
        if type(t) is not int or prev is not None and t <= prev:
            raise ValueError("strictly increasing integer event times required")
        prev = t
        marks, actions = {}, []
        for key, w in wallets.items():
            if key not in event["marks"] or w.quantity and key not in event["funding_cash_per_notional"]:
                return dict(state="UNKNOWN_MARK_OR_FUNDING", final_net=None, rows=rows)
            marks[key] = number(event["marks"][key], positive=True)
            if w.quantity:
                cash = n * number(event["funding_cash_per_notional"][key])
                w.cash += cash
                w.funding += cash
        if "transfer" in event:
            src, dst, share = event["transfer"]
            if src not in wallets or dst not in wallets or src == dst:
                raise ValueError("distinct source/destination wallets required")
            value = n * number(share, positive=True)
            w = wallets[src]
            reserve = requirement(w.tiers, abs(w.quantity) * marks[src], initial=True)
            if t < case["transfer_outage_until_ms"]:
                actions.append("TRANSFER_BLOCKED_OUTAGE")
            elif reserve is None or w.cash - value < reserve:
                actions.append("TRANSFER_BLOCKED_COLLATERAL")
            else:
                w.cash -= value
                wallets[dst].cash += value
                actions.append("TRANSFER_COMPLETED")
        for key, w in wallets.items():
            if not w.quantity:
                continue
            eq = w.equity(marks[key])
            w.ever_insolvent |= eq < 0
            mm = requirement(w.tiers, abs(w.quantity) * marks[key])
            margin_unknown |= mm is None
            forced = event.get("forced", {}).get(key)
            if forced:
                if forced["kind"] != "ADL":
                    raise ValueError("only explicit ADL prices use the forced settlement path")
                price = number(forced["price"], positive=True)
                fee = number(forced["fee_rate"], nonnegative=True)
                w.close(dict(filled=abs(w.quantity), vwap=price, quote=abs(w.quantity) * price,
                             fee=abs(w.quantity) * price * fee * m))
                actions.append(key + "_ADL_CLOSED")
            elif (mm is not None and eq <= mm) or event.get("close_all", False):
                if key not in event["books"]:
                    return dict(state="UNKNOWN_EXIT_BOOK", final_net=None, rows=rows)
                liquidating = mm is not None and eq <= mm
                fill = sweep(Book(**event["books"][key]), "sell" if w.quantity > 0 else "buy",
                             abs(w.quantity), fee_rate=w.fee_rate, multiple=m)
                w.close(fill, penalty=w.liquidation_fee * m if liquidating else ZERO)
                actions.append(key + ("_LIQUIDATED" if liquidating else "_CLOSED")
                               + ("_PARTIAL" if w.quantity else ""))
        equity = sum(w.equity(marks[k]) for k, w in wallets.items())
        rows.append(dict(time_ms=t, label=event["label"], equity=equity, net=equity - 2 * n,
                         actions=actions, wallets={k: dict(quantity=w.quantity, cash=w.cash,
                             equity=w.equity(marks[k]), fees=w.fees, funding=w.funding,
                             realized=w.realized, ever_insolvent=w.ever_insolvent)
                             for k, w in wallets.items()}))
    closed = all(not w.quantity for w in wallets.values())
    state = "CONDITIONAL_CLOSED" if closed and not margin_unknown else "UNKNOWN_MARGIN" if margin_unknown else "OPEN"
    return dict(state=state, initial_quantity=q, initial_capital=2 * n,
                final_net=rows[-1]["net"] if rows and closed and not margin_unknown else None,
                loss_before_recovery=next((r["net"] for r in rows if r["label"] == "before_recovery"), None),
                rows=rows)
