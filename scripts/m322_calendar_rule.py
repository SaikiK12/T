"""Calendar coverage gate for a proposed M322 paper comparison.

This validates structure and readiness, not profitability or statistical
significance. Each source and mark must be authenticated by the future runner.
"""
from dataclasses import dataclass
import math
import re

from scripts.m322_signal_rule import DAY, ENTRY_DELAY, MAX_CLOCK_ERROR_MS

_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class Day:
    day_ms: int
    status: str  # trigger, no_trigger, or missing
    strategy_start: float | None
    strategy_end: float | None
    baseline_start: float | None
    baseline_end: float | None
    cash_start: float | None
    cash_end: float | None
    ticket_published_ms: int | None
    clock_error_ms: int | None
    evidence_sha256: str


def _positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def ready(days):
    """One final look needs 30 trigger days and complete, continuous accounts.

    A missing day is retained and blocks the look; it is never zero-filled.
    Full equity continuity cannot be established when a mark is missing.
    """
    days = list(days)
    if not days:
        return False
    if any(not isinstance(row, Day) for row in days):
        raise ValueError("invalid calendar record")
    previous = None
    complete = True
    triggers = 0
    for row in days:
        if (isinstance(row.day_ms, bool) or not isinstance(row.day_ms, int) or row.day_ms % DAY
                or row.status not in ("trigger", "no_trigger", "missing")
                or not isinstance(row.evidence_sha256, str) or not _SHA.fullmatch(row.evidence_sha256)):
            raise ValueError("invalid day, status or evidence")
        if previous is not None and row.day_ms != previous.day_ms + DAY:
            raise ValueError("calendar day is missing, duplicated or out of order")
        values = (row.strategy_start, row.strategy_end, row.baseline_start, row.baseline_end,
                  row.cash_start, row.cash_end)
        if row.status == "missing":
            if any(v is not None for v in values) or row.ticket_published_ms is not None or row.clock_error_ms is not None:
                raise ValueError("missing days cannot contain fabricated marks")
            complete = False
        else:
            if (any(isinstance(x, bool) or not isinstance(x, int)
                    for x in (row.ticket_published_ms, row.clock_error_ms))
                    or not 0 <= row.clock_error_ms <= MAX_CLOCK_ERROR_MS
                    or row.ticket_published_ms - row.clock_error_ms < row.day_ms
                    or row.ticket_published_ms + row.clock_error_ms >= row.day_ms + ENTRY_DELAY):
                raise ValueError("ticket was late or lacks a clock bound")
            if not all(_positive(v) for v in values):
                raise ValueError("invalid or insolvent daily account mark")
            if previous is not None and previous.status != "missing":
                for old, new in ((previous.strategy_end, row.strategy_start),
                                 (previous.baseline_end, row.baseline_start),
                                 (previous.cash_end, row.cash_start)):
                    if not math.isclose(old, new, rel_tol=1e-10, abs_tol=1e-8):
                        raise ValueError("account equity is discontinuous")
            triggers += row.status == "trigger"
        previous = row
    return complete and triggers >= 30
