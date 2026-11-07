"""Source-typed value observations and conservative funding-cash evidence.

A publication/system clock is not an effective-value or settlement clock.
Trade timestamps, estimated rates and unknown ownership cannot certify cash.
This module posts no orders and never treats missing evidence as zero funding.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from lab.executable_quotes import positive
from lab.stream_quotes import FrameClock, NS, ReferencePrice, StreamBook, freshness, source_ns


def signed(value):
    if isinstance(value,bool):
        raise ValueError("boolean numeric field")
    try:
        out = Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError) as exc:
        raise ValueError("finite signed decimal required") from exc
    if not out.is_finite():
        raise ValueError("finite signed decimal required")
    return out


@dataclass(frozen=True)
class ValuePacket:
    venue: str
    symbol: str
    kind: str                       # fair or index
    price: Decimal
    clock: FrameClock               # first seen, never an invented refresh
    source_time_ns: int             # publication/system clock, explicit role
    clock_role: str
    source_identity: str
    effective_value_ns: int | None = None
    settlement_event_id: str | None = None

    def __post_init__(self):
        if self.venue not in ("mexc","lighter") or self.kind not in ("fair","index"):
            raise ValueError("supported value identity required")
        if not self.symbol or not self.source_identity or not isinstance(self.clock,FrameClock):
            raise ValueError("symbol/source/receive clock required")
        if self.clock_role not in ("REST_system","WS_publication","trade_time","settlement_value"):
            raise ValueError("explicit source clock role required")
        object.__setattr__(self,"price",positive(self.price))
        source_ns(self.source_time_ns//1_000_000,"ms")
        if self.clock_role == "settlement_value":
            if type(self.effective_value_ns) is not int or not self.settlement_event_id:
                raise ValueError("bound settlement event/value time required")
            source_ns(self.effective_value_ns//1_000_000,"ms")
            if not self.effective_value_ns <= self.source_time_ns <= self.clock.utc_ns:
                raise ValueError("settlement value/publication cannot precede its economic value or follow receipt")
        elif self.effective_value_ns is not None or self.settlement_event_id is not None:
            raise ValueError("publication/trade packets cannot assert settlement value time")


def mexc_rest_fair(payload,symbol,clock,identity):
    if payload.get("success") is not True or payload.get("code") != 0:
        raise ValueError("failed MEXC fair response")
    data = payload["data"]
    if data["symbol"] != symbol+"_USDT":
        raise ValueError("MEXC fair identity mismatch")
    return ValuePacket("mexc",symbol,"fair",positive(data["fairPrice"]),clock,
        source_ns(data["timestamp"],"ms"),"REST_system",identity)


def streamed_value(item):
    if not isinstance(item,ReferencePrice):
        return None
    return ValuePacket(item.venue,item.symbol,"fair" if item.venue == "mexc" else "index",item.price,
        item.clock,item.source_time_ns,"WS_publication",item.source_role)


def value_flags(packet,target,anchor):
    if packet is None:
        return ["missing"]
    flags = freshness(packet,target,anchor)
    if packet.clock_role == "trade_time":
        flags.append("trade_time_is_not_value_publication")
    return flags


def paired_values(packets,quantity,books,target,anchor):
    """Observed quote-unit sensitivity, never an actual settled funding payment."""
    if len(packets) != 2 or len(books) != 2:
        raise ValueError("exactly two venue-ordered packets and books required")
    flags,observations = [],[]
    for venue,kind,packet,book in zip(("mexc","lighter"),("fair","index"),packets,books):
        ff = value_flags(packet,target,anchor)
        if packet is not None and (packet.venue != venue or packet.kind != kind):
            ff.append("value_identity_kind_mismatch")
        if not isinstance(book,StreamBook) or (packet is not None and (book.venue,book.symbol) != (packet.venue,packet.symbol)):
            ff.append("quote_value_identity_unavailable_or_mismatch")
        flags.extend(venue+":"+f for f in ff)
        observations.append({"venue":venue,"kind":kind,"price":str(packet.price) if packet else None,
            "publication_ns":packet.source_time_ns if packet else None,
            "receive_ns":packet.clock.mono_ns if packet else None,
            "clock_role":packet.clock_role if packet else None,"flags":ff,
            "effective_value_time_verified":False,"settlement_cash_verified":False})
    if all(p is not None for p in packets):
        if abs(packets[0].clock.mono_ns-packets[1].clock.mono_ns) > NS:
            flags.append("value_receive_skew_over_1s")
        if abs(packets[0].source_time_ns-packets[1].source_time_ns) > NS:
            flags.append("value_publication_skew_over_1s")
        if packets[0].symbol != packets[1].symbol:
            flags.append("paired_symbol_mismatch")
    products = None
    if quantity is not None and not flags:
        q = positive(quantity)
        products = []
        for packet,book in zip(packets,books):
            products.append({"venue":packet.venue,"reference_notional_quote_units":str(q*packet.price),
                "quote_units_per_one_bp":str(q*packet.price/Decimal(10000)),
                "reference_minus_book_mid_bp":float((packet.price/Decimal(str(book.mid))-1)*10000),
                "quote_asset":"USDT" if packet.venue == "mexc" else "USD_quote; settlement_asset_unverified"})
    return {"flags":flags,"observations":observations,"products":products,
            "cash_certified":False,"execution_ready":False}


@dataclass(frozen=True)
class FundingContract:
    venue: str
    symbol: str
    model: str                      # linear_base or inverse_contracts
    settlement_asset: str | None
    asset_verified: bool
    source_version: str
    base_asset: str
    price_quote_asset: str
    batch_delay_ns: int = 0
    contract_quote_value: Decimal | None = None

    def __post_init__(self):
        if self.venue not in ("mexc","lighter") or not self.symbol or not self.source_version:
            raise ValueError("funding contract identity/source required")
        if self.model not in ("linear_base","inverse_contracts") or (self.venue == "lighter" and self.model != "linear_base"):
            raise ValueError("unsupported funding notional convention")
        if self.asset_verified and not self.settlement_asset:
            raise ValueError("verified settlement asset required")
        if type(self.asset_verified) is not bool:
            raise ValueError("explicit asset verification boolean required")
        if not self.base_asset or not self.price_quote_asset:
            raise ValueError("explicit price/base asset units required")
        expected = self.price_quote_asset if self.model == "linear_base" else self.base_asset
        if self.asset_verified and self.settlement_asset != expected:
            raise ValueError("funding cash dimensional asset mismatch")
        if type(self.batch_delay_ns) is not int or self.batch_delay_ns < 0:
            raise ValueError("explicit nonnegative inclusion-window duration required")
        if self.venue == "mexc" and self.batch_delay_ns < 15*NS:
            raise ValueError("MEXC batch inclusion interval must preserve documented15s ambiguity")
        if self.model == "inverse_contracts":
            object.__setattr__(self,"contract_quote_value",positive(self.contract_quote_value))


@dataclass(frozen=True)
class FundingEvent:
    event_id: str
    venue: str
    symbol: str
    funding_ns: int
    rate: Decimal
    rate_unit: str
    stage: str
    clock: FrameClock

    def __post_init__(self):
        if self.venue not in ("mexc","lighter") or not self.symbol or not isinstance(self.clock,FrameClock):
            raise ValueError("event identity/receive clock required")
        if type(self.funding_ns) is not int or not isinstance(self.stage,str):
            raise ValueError("event clock/stage required")
        source_ns(self.funding_ns//1_000_000,"ms")
        object.__setattr__(self,"rate",signed(self.rate))
        if self.stage == "settled" and self.clock.utc_ns < self.funding_ns:
            raise ValueError("settled event cannot be first seen before economic event")

    def fraction(self):
        if self.rate_unit not in ("fraction","percent"):
            raise ValueError("source-specific rate unit unverified")
        return signed(self.rate)/(100 if self.rate_unit == "percent" else 1)


@dataclass(frozen=True)
class PositionSpan:
    start_ns: int
    end_ns: int
    quantity: Decimal
    clock: FrameClock              # observed coverage, not a planned future hold
    venue: str
    symbol: str
    quantity_unit: str

    def __post_init__(self):
        if (type(self.start_ns) is not int or type(self.end_ns) is not int or not isinstance(self.clock,FrameClock)
                or not 0 <= self.start_ns < self.end_ns <= self.clock.utc_ns):
            raise ValueError("completed, observed exposure coverage required")
        object.__setattr__(self,"quantity",signed(self.quantity))
        if self.venue not in ("mexc","lighter") or not self.symbol or self.quantity_unit not in ("base","contracts"):
            raise ValueError("contract-bound exposure quantity units required")


def clock_known(clock,asof,anchor):
    return clock.mono_ns <= asof and abs((clock.utc_ns-anchor.utc_ns)-(clock.mono_ns-anchor.mono_ns)) <= 50_000_000


def stable_exposure(spans,lo,hi,asof,anchor,contract):
    known = [s for s in spans if clock_known(s.clock,asof,anchor) and s.end_ns > lo and s.start_ns <= hi
             and (s.venue,s.symbol) == (contract.venue,contract.symbol)]
    unit = "base" if contract.model == "linear_base" else "contracts"
    if any(s.quantity_unit != unit for s in known):
        return None
    eligible = sorted(known,
                      key=lambda s:(s.start_ns,s.end_ns))
    if not eligible or eligible[0].start_ns >= lo:
        return None
    q,cursor = eligible[0].quantity,lo
    for s in eligible:
        if s.start_ns > cursor or s.quantity != q:
            return None
        cursor = max(cursor,s.end_ns)
    return q if cursor > hi else None


def assess_funding(contract,event,spans,packet,asof,anchor):
    """Confirmed model cash needs explicit event-bound value and whole-window q.

    No real account credit is asserted; the result is a public/paper contract
    calculation. Publication snapshots alone cannot satisfy value binding.
    """
    key = (contract.venue,contract.symbol,event.funding_ns)
    context = {"key":key,"event_id":event.event_id,"contract_source":contract.source_version,
               "rate_unit":event.rate_unit,"rate_stage":event.stage,"model":contract.model,
               "value_source":packet.source_identity if packet else None}
    flags = []
    if (event.venue,event.symbol) != (contract.venue,contract.symbol) or not event.event_id:
        flags.append("event_identity_mismatch")
    now = anchor.utc_ns+asof-anchor.mono_ns
    if not clock_known(event.clock,asof,anchor) or now < event.funding_ns+contract.batch_delay_ns:
        flags.append("event_or_inclusion_window_not_yet_known")
    q = stable_exposure(spans,event.funding_ns,event.funding_ns+contract.batch_delay_ns,asof,anchor,contract)
    if q is None:
        flags.append("position_inclusion_unverified_or_changed")
    if q == 0 and not flags:
        return {**context,"status":"inactive","cash_delta":Decimal(0),"asset":contract.settlement_asset,"flags":()}
    if event.stage != "settled":
        flags.append("estimated_or_unverified_rate_is_not_settled")
    try:
        rate = event.fraction()
    except ValueError:
        rate = None;flags.append("rate_unit_unverified")
    if not contract.asset_verified:
        flags.append("settlement_asset_unverified")
    kind = "fair" if contract.venue == "mexc" else "index"
    if (packet is None or (packet.venue,packet.symbol,packet.kind) != (contract.venue,contract.symbol,kind)
            or packet.clock_role != "settlement_value" or packet.settlement_event_id != event.event_id
            or packet.effective_value_ns is None or not event.funding_ns <= packet.effective_value_ns <= event.funding_ns+contract.batch_delay_ns):
        flags.append("value_not_bound_to_actual_funding_event")
    elif not clock_known(packet.clock,asof,anchor):
        flags.append("future_value_receipt")
    if flags:
        return {**context,"status":"unscored","cash_delta":None,"asset":contract.settlement_asset,"flags":tuple(flags)}
    notional = q*packet.price if contract.model == "linear_base" else q*contract.contract_quote_value/packet.price
    return {**context,"status":"model_cash","cash_delta":-notional*rate,"asset":contract.settlement_asset,
            "flags":(),"real_account_credit_verified":False}


class FundingLedger:
    """In-memory append-only assessments; cash totals stay segregated by venue/asset."""
    def __init__(self):
        self.attempts,self.posted,self.event_times,self.totals = [],{},{},{}

    def post(self,contract,event,spans,packet,asof,anchor):
        result = assess_funding(contract,event,spans,packet,asof,anchor)
        signature = (event.event_id,event.rate_unit,str(event.rate),contract.model,contract.settlement_asset,
                     result["cash_delta"])
        old = self.posted.get(result["key"])
        identity = (contract.venue,contract.symbol,event.event_id)
        if identity in self.event_times and self.event_times[identity] != event.funding_ns:
            result = {**result,"status":"conflicting_event_time","cash_delta":None}
        elif old is not None:
            result = {**result,"status":"duplicate" if old == signature else "conflicting_revision",
                      "cash_delta":Decimal(0) if old == signature else None}
        elif result["cash_delta"] is not None:
            self.posted[result["key"]] = signature
            k = (contract.venue,contract.settlement_asset)
            self.totals[k] = self.totals.get(k,Decimal(0))+result["cash_delta"]
        if (event.stage == "settled" and event.event_id and (event.venue,event.symbol) == (contract.venue,contract.symbol)
                and clock_known(event.clock,asof,anchor)):
            self.event_times.setdefault(identity,event.funding_ns)
        self.attempts.append(dict(result))
        return result
