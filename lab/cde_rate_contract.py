"""Exact sampled API-field identity, with no fitted scale/time shift or return."""
import calendar
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction


def hour(value):
    if not isinstance(value, str):
        raise ValueError("explicit source timestamp string required")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("source timestamp has no timezone")
    dt = dt.astimezone(timezone.utc)
    if dt.minute or dt.second or dt.microsecond:
        raise ValueError("source timestamp is not an exact hour")
    return calendar.timegm(dt.utctimetuple())


def rate(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("explicit source rate string required; missing is not0")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid source rate") from exc
    if not d.is_finite():
        raise ValueError("nonfinite source rate")
    return d


def evaluate(observations, history, *, symbol, required):
    final = {}
    for row in history:
        if row["symbol"] != symbol:
            raise ValueError("MDA instrument identity drift")
        t = hour(row["event_time"])
        if t in final:
            raise ValueError("duplicate MDA timestamp")
        rate(row["funding_rate"])
        final[t] = row
    rows = []
    for observation in observations:
        stamp = observation["funding_time"]
        t, a = hour(stamp), rate(observation["funding_rate"])
        received = observation["received_utc_ns"]
        if type(received) is not int or received <= 0:
            raise ValueError("explicit positive source receipt required")
        future = t * 10**9 > received
        other = final.get(t)
        b = rate(other["funding_rate"]) if other is not None else None
        equal = a == b if b is not None else None
        if b is not None and equal != (Fraction(observation["funding_rate"]) == Fraction(other["funding_rate"])):
            raise ValueError("independent decimal/rational comparison disagrees")
        rows.append(dict(source_hour=observation["source_hour"], funding_time=stamp,
                         received_utc_ns=received, future_timestamp=future,
                         advanced_raw=observation["funding_rate"],
                         mda_raw=other["funding_rate"] if other else None,
                         exact_numeric_equal=equal))
    missing = sum(r["exact_numeric_equal"] is None for r in rows)
    mismatches = sum(r["exact_numeric_equal"] is False for r in rows)
    nonzero = [rate(r["advanced_raw"]) for r in rows if r["exact_numeric_equal"] and rate(r["advanced_raw"]) != 0]
    if any(r["future_timestamp"] for r in rows):
        verdict = "UNQUALIFIED_FUTURE_TIMESTAMP"
    elif mismatches:
        verdict = "EXACT_FIELD_MISMATCH"
    elif missing or len(rows) != required:
        verdict = "INCONCLUSIVE_COVERAGE"
    elif len(nonzero) < 2 or len(set(nonzero)) < 2:
        verdict = "INCONCLUSIVE_VARIATION"
    else:
        verdict = "SAMPLED_FIELD_CONSISTENT"
    return dict(verdict=verdict, observations=len(rows), exact_matches=len(rows)-missing-mismatches,
                missing_final_rows=missing, mismatches=mismatches,
                nonzero_matching_points=len(nonzero), distinct_nonzero_values=len(set(nonzero)),
                rows=rows, fitted_scale=None, fitted_time_shift=None,
                historical_cash_or_revisions_certified=False, pnl=None)
