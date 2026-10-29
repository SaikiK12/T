"""Strict single-page MEXC history parsing; preserves exact settlement times.

No network, file access or outcome calculation. Page one does not prove the
history is complete; a missing requested event is missing, never a zero rate.
"""
from dataclasses import dataclass
import hashlib
import json
import math

MAX_BODY = 1_000_000


@dataclass(frozen=True)
class Settlement:
    symbol: str
    settlement_ms: int
    rate: float


@dataclass(frozen=True)
class Page:
    raw_sha256: str
    total_pages: int
    settlements: tuple[Settlement, ...]


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _constant(_):
    raise ValueError("nonstandard numeric constant")


def _integer(value, label):
    if isinstance(value, bool):
        raise ValueError(f"invalid {label}")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    raise ValueError(f"invalid {label}")


def parse_page_one(raw, symbol):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BODY:
        raise ValueError("missing or oversized response")
    if not isinstance(symbol, str) or not symbol:
        raise ValueError("invalid symbol")
    try:
        body = json.loads(raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=_constant)
        if not isinstance(body, dict) or body.get("success") is not True:
            raise ValueError("unsuccessful history response")
        data = body["data"]
        current = _integer(data["currentPage"], "page")
        total = _integer(data["totalPage"], "total pages")
        entries = data["resultList"]
        if current != 1 or total < 0 or not isinstance(entries, list) or (entries and total < 1):
            raise ValueError("invalid page metadata")
        rows, seen = [], set()
        for row in entries:
            if not isinstance(row, dict) or row.get("symbol") != symbol:
                raise ValueError("settlement symbol mismatch")
            ts = _integer(row["settleTime"], "settlement time")
            if ts < 0 or ts in seen or isinstance(row["fundingRate"], bool):
                raise ValueError("invalid or duplicate settlement")
            rate = float(row["fundingRate"])
            if not math.isfinite(rate) or abs(rate) > 1:
                raise ValueError("invalid funding rate")
            seen.add(ts)
            rows.append(Settlement(symbol, ts, rate))
        if any(a.settlement_ms <= b.settlement_ms for a, b in zip(rows, rows[1:])):
            raise ValueError("history is not strictly descending")
        return Page(hashlib.sha256(raw).hexdigest(), total, tuple(rows))
    except (KeyError, TypeError, UnicodeError, OverflowError, json.JSONDecodeError) as exc:
        raise ValueError("malformed history response") from exc


def find_exact(page, settlement_ms):
    if not isinstance(page, Page) or isinstance(settlement_ms, bool) or not isinstance(settlement_ms, int):
        raise ValueError("invalid page or requested settlement")
    return next((row for row in page.settlements if row.settlement_ms == settlement_ms), None)
