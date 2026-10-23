"""Offline mark-price contracts for a future registered M265 follow-up.

Binance USD-M mark klines use millisecond open/close stamps and twelve slots;
only OHLC and timestamps are meaningful here. The six other slots are Ignore,
not trading volume or freshness. Gate mark_ candles omit trade volume and use
second timestamps, but the reviewed official schema does not establish whether
t labels the open or close. Gate candles therefore remain unplaced observations
and cannot enter day_range until a later, independently justified conversion.

Day ranges require the exact full UTC grid of completed mark bars. Missing
bars never become zero risk or forward-filled prices. A mark-relative adverse
move additionally needs the immediately preceding mark close. This is price
arithmetic, not a fill, account, liquidation, or safe-leverage simulator. The
cutoff checks bar completion only; it proves neither original publication time
nor a historical point-in-time vintage. Hourly OHLC cannot locate intrabar
extremes across multiple legs on one common clock.

Primary contracts reviewed 2026-10-21 (no market/value request):
Binance OpenAPI1.0.0, selected markPriceKlines declaration SHA256
689f5a30654e9152140e5a29c7779486b1a103aa12f173473508edd34121aacc:
https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/1.0.0/schema.yaml
Gate REST v4.106.160; official model pinned at 759c91c06face05c0610b4a62661f7e23172d9cb,
whole-file SHA256 35907cc57731a086413a68fdad2fd125cc73a0b52a341c08e8c247ca6303315f:
https://github.com/gate/gateapi-python/blob/759c91c06face05c0610b4a62661f7e23172d9cb/docs/FuturesCandlestick.md
Only fixed intraday intervals through 1d are supported here. REST tuple
decoding does not validate an archive CSV schema or historical availability.

MEXC fair-price candles were checked 2026-10-23 (public documentation only):
https://www.mexc.co/api-docs/futures/market-endpoints/get-fair-price-candles
retrieved page SHA256 50ec4df33371641b11365036abfdc74cf36d13c34d3c7e9bd29d0d0b64414745.
The page declares second timestamps, parallel OHLC arrays and up to 2000 rows,
but does not say whether `time` labels the bar open or close. Its `real*` and
activity arrays are deliberately not treated as fair-price OHLC. The decoder
below preserves that unresolved clock role; its values cannot enter day_range
until a separate source check establishes a valid normalization.
"""

from dataclasses import dataclass
from decimal import Decimal, DecimalException
from math import isfinite
from numbers import Integral, Real
import re

DAY = 86_400_000
MINUTE = 60_000
BINANCE_INTERVALS = {n * MINUTE for n in (1, 3, 5, 15, 30, 60, 120, 240, 360, 480, 720, 1440)}
GATE_INTERVALS = {10_000} | {n * MINUTE for n in (1, 5, 15, 30, 60, 240, 480, 1440)}
MEXC_INTERVALS = {
    "Min1": 60_000, "Min5": 5 * MINUTE, "Min15": 15 * MINUTE,
    "Min30": 30 * MINUTE, "Min60": 60 * MINUTE,
    "Hour4": 4 * 60 * MINUTE, "Hour8": 8 * 60 * MINUTE,
    "Day1": DAY, "Week1": 7 * DAY,
}


def _integer(value, name, *, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if isinstance(value, Integral):
        result = int(value)
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        result = int(value)
    else:
        raise ValueError(f"{name} must be an integer")
    if result < (1 if positive else 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'}")
    return result


def _interval(value):
    value = _integer(value, "interval_ms", positive=True)
    if DAY % value:
        raise ValueError("interval_ms must divide a UTC day")
    return value


def _contract(value):
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ValueError("contract must be nonempty without whitespace")


def _gate_contract(value):
    _contract(value)
    if not value.startswith("mark_") or not value.endswith("_USDT") or not value[5:-5]:
        raise ValueError("Gate USDT mark identity requires mark_<base>_USDT")


def _gate_timestamp(value):
    """Gate declares seconds as number/double; keep exact millisecond precision."""
    if isinstance(value, bool) or not isinstance(value, (Real, str)):
        raise ValueError("Gate timestamp must be seconds representable in milliseconds")
    try:
        stamp = Decimal(str(value))
        if not stamp.is_finite() or stamp < 0:
            raise ValueError("invalid or sub-millisecond Gate timestamp")
        numerator, denominator = stamp.as_integer_ratio()
        milliseconds, remainder = divmod(numerator * 1000, denominator)
        if remainder:
            raise ValueError("sub-millisecond Gate timestamp")
        return milliseconds
    except (DecimalException, ValueError, OverflowError) as exc:
        raise ValueError("Gate timestamp must be seconds representable in milliseconds") from exc


def _ohlc(record):
    for field in ("open", "high", "low", "close"):
        value = getattr(record, field)
        if isinstance(value, bool) or not isinstance(value, (Real, str)):
            raise ValueError(f"{field} must be positive and finite")
        try:
            value = float(value)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"{field} must be positive and finite") from exc
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{field} must be positive and finite")
        object.__setattr__(record, field, value)
    if not record.low <= min(record.open, record.close) <= max(record.open, record.close) <= record.high:
        raise ValueError("OHLC must satisfy low <= open,close <= high")


@dataclass(frozen=True, slots=True)
class MarkBar:
    venue: str
    contract: str
    start_ms: int
    end_ms: int                    # exclusive, unlike Binance's inclusive close stamp
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        if self.venue not in {"binance_usdm", "gate_usdt"}:
            raise ValueError("unsupported mark venue")
        _contract(self.contract)
        if self.venue == "gate_usdt":
            _gate_contract(self.contract)
        for field in ("start_ms", "end_ms"):
            object.__setattr__(self, field, _integer(getattr(self, field), field))
        if self.end_ms <= self.start_ms:
            raise ValueError("bar end must follow its start")
        _ohlc(self)


@dataclass(frozen=True, slots=True)
class GateMarkCandle:
    contract: str
    timestamp_ms: int
    interval_ms: int
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        _gate_contract(self.contract)
        object.__setattr__(self, "timestamp_ms", _integer(self.timestamp_ms, "timestamp_ms"))
        object.__setattr__(self, "interval_ms", _interval(self.interval_ms))
        _ohlc(self)

    @property
    def venue(self):
        return "gate_usdt"

    @property
    def timestamp_role(self):
        return "unresolved"


def decode_binance(rows, *, symbol, interval_ms):
    """Decode the REST markPriceKlines schema; units are explicitly ms, never guessed."""
    _contract(symbol)
    if not symbol.endswith(("USDT", "USDC")):
        raise ValueError("this USD-M decoder requires a USDT/USDC symbol")
    interval_ms = _interval(interval_ms)
    if interval_ms not in BINANCE_INTERVALS:
        raise ValueError("unsupported fixed-duration Binance mark interval")
    if not isinstance(rows, (list, tuple)):
        raise ValueError("Binance payload must be an array")
    bars = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 12:
            raise ValueError("Binance mark row must contain twelve slots")
        start, end = _integer(row[0], "open_time"), _integer(row[6], "close_time") + 1
        if end - start != interval_ms:
            raise ValueError("Binance timestamp duration differs from interval_ms")
        bars.append(MarkBar("binance_usdm", symbol, start, end, *row[1:5]))
    return tuple(bars)


def decode_gate(rows, *, contract, interval_ms):
    """Decode Gate REST objects, preserving the unresolved timestamp role.

    This is not the t,v,c,h,l,o bulk-archive format. Prefix identity comes from
    the declared request; returned objects do not independently prove it.
    """
    _gate_contract(contract)
    interval_ms = _interval(interval_ms)
    if interval_ms not in GATE_INTERVALS:
        raise ValueError("unsupported fixed-duration Gate mark interval")
    if not isinstance(rows, (list, tuple)):
        raise ValueError("Gate payload must be an array")
    bars = []
    for row in rows:
        if not isinstance(row, dict) or not {"t", "o", "h", "l", "c"} <= row.keys():
            raise ValueError("Gate mark row requires t,o,h,l,c")
        stamp = _gate_timestamp(row["t"])
        bars.append(GateMarkCandle(contract, stamp, interval_ms, row["o"], row["h"], row["l"], row["c"]))
    return tuple(bars)


@dataclass(frozen=True, slots=True)
class MexcFairCandle:
    """Decoded MEXC fair-price candle whose timestamp role is still unresolved."""
    contract: str
    timestamp_s: int
    interval: str
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        _contract(self.contract)
        if not self.contract.endswith("_USDT") or not self.contract[:-5]:
            raise ValueError("MEXC USDT contract identity requires <base>_USDT")
        object.__setattr__(self, "timestamp_s", _integer(self.timestamp_s, "timestamp_s"))
        if self.interval not in MEXC_INTERVALS:
            raise ValueError("unsupported fixed-duration MEXC fair-price interval")
        _ohlc(self)

    @property
    def venue(self):
        return "mexc_usdt"

    @property
    def timestamp_role(self):
        return "unresolved"


def decode_mexc_fair(payload, *, contract, interval):
    """Decode the public MEXC fair-price REST shape without guessing its clock.

    Only `time/open/high/low/close` are consumed. Volume, amount and `real*`
    arrays are ignored. In particular, this does not turn timestamp seconds
    into normalized bar starts and cannot feed day_range until that role is
    established independently.
    """
    _contract(contract)
    if not contract.endswith("_USDT") or not contract[:-5]:
        raise ValueError("MEXC USDT contract identity requires <base>_USDT")
    if interval not in MEXC_INTERVALS:
        raise ValueError("unsupported fixed-duration MEXC fair-price interval")
    if not isinstance(payload, dict) or payload.get("success") is not True or type(payload.get("code")) is not int or payload["code"] != 0:
        raise ValueError("MEXC fair-price response must declare success and code 0")
    data = payload.get("data")
    names = ("time", "open", "high", "low", "close")
    if not isinstance(data, dict) or any(not isinstance(data.get(name), (list, tuple)) for name in names):
        raise ValueError("MEXC fair-price data requires parallel time/open/high/low/close arrays")
    columns = [data[name] for name in names]
    if any(len(column) != len(columns[0]) for column in columns[1:]):
        raise ValueError("MEXC fair-price arrays must have equal lengths")
    candles = []
    for row in zip(*columns):
        candles.append(MexcFairCandle(contract, row[0], interval, row[1], row[2], row[3], row[4]))
    return tuple(candles)


@dataclass(frozen=True, slots=True)
class DayRange:
    expected: int
    observed: int
    range_complete: bool
    anchor_close: float | None
    high: float | None
    low: float | None
    closing_mark: float | None

    @property
    def ready(self):
        return self.range_complete and self.anchor_close is not None


def day_range(bars, *, day_end_ms, interval_ms, as_of_ms):
    """Range over [day_end-DAY, day_end); the audit label is the UTC day end.

    Identical duplicates do not add coverage; conflicting duplicates fail.
    Invalid input or mixed identity fails even outside the requested window.
    Only bars with end <= as_of_ms can supply coverage or the preceding anchor.
    Unknown Gate time labels require a separately verified normalization first.
    """
    interval_ms = _interval(interval_ms)
    end = _integer(day_end_ms, "day_end_ms", positive=True)
    cutoff = _integer(as_of_ms, "as_of_ms")
    if end % DAY:
        raise ValueError("day_end_ms must be UTC midnight")
    start = end - DAY
    identity, by_start = None, {}
    for bar in bars:
        if not isinstance(bar, MarkBar):
            raise ValueError("day_range requires normalized MarkBar inputs")
        current = (bar.venue, bar.contract)
        if identity is not None and current != identity:
            raise ValueError("mixed mark identities")
        identity = current
        if bar.end_ms - bar.start_ms != interval_ms or bar.start_ms % interval_ms:
            raise ValueError("mark bar must match the requested UTC interval grid")
        previous = by_start.get(bar.start_ms)
        if previous is not None and previous != bar:
            raise ValueError("conflicting duplicate mark bar")
        by_start[bar.start_ms] = bar
    closed = {stamp: bar for stamp, bar in by_start.items() if bar.end_ms <= cutoff}
    expected = DAY // interval_ms
    selected = [closed[stamp] for stamp in range(start, end, interval_ms) if stamp in closed]
    complete = len(selected) == expected
    anchor = closed.get(start - interval_ms)
    return DayRange(expected, len(selected), complete, anchor.close if anchor else None,
                    max(bar.high for bar in selected) if complete else None,
                    min(bar.low for bar in selected) if complete else None,
                    selected[-1].close if complete else None)


def adverse(result, side):
    """Dimensionless mark-relative worst move; unknown coverage/anchor returns None."""
    if isinstance(side, bool) or not isinstance(side, Integral) or side not in (-1, 1):
        raise ValueError("side must be +1 or -1")
    if not result.ready:
        return None
    value = 1.0 - result.low / result.anchor_close if side == 1 else result.high / result.anchor_close - 1.0
    if not isfinite(value):
        raise ValueError("adverse mark move is outside finite float range")
    return max(0.0, value)
