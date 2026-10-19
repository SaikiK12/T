"""Point-in-time availability checks for Hyperliquid position snapshots.

``scripts.scrape_hyperliquid`` keeps the original change-log reconstruction
semantics.  The helpers here are deliberately opt-in: they filter rows by an
explicit server-time cutoff and return an availability report so a caller can
fail closed when an hour or account snapshot is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Iterable

import pandas as pd


ACCOUNT_KEY = ("address", "account")
POSITION_KEY = ("address", "account", "coin")
_MS = 1_000_000


@dataclass(frozen=True)
class SnapshotAvailability:
    """Evidence that a reconstructed state is current at a requested cutoff.

    ``available`` is intentionally fail-closed.  It is true only when the
    caller supplied an expected account universe and every expected account
    has a non-ambiguous snapshot for the requested hour whose server timestamp
    is at or before ``cutoff_ms``.
    """

    requested_hour: str
    cutoff_ms: int
    expected_accounts: tuple[tuple[str, str], ...]
    observed_accounts: tuple[tuple[str, str], ...]
    missing_accounts: tuple[tuple[str, str], ...]
    late_accounts: tuple[tuple[str, str], ...]
    stale_accounts: tuple[tuple[str, str], ...]
    duplicate_accounts: tuple[tuple[str, str], ...]
    hour_present: bool
    future_account_rows: int
    future_position_rows: int
    untimed_position_rows: int
    available: bool
    reason: str


@dataclass(frozen=True)
class StrictSnapshot:
    """A reconstructed position table and the conditions under which it is valid."""

    positions: pd.DataFrame
    availability: SnapshotAvailability


def _hour(value) -> pd.Timestamp:
    """Parse a UTC hour without allowing a naive local-time interpretation."""

    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.floor("h")


def _millis(value) -> int:
    """Parse a UTC cutoff as integer milliseconds since epoch."""

    if isinstance(value, Real) and not isinstance(value, bool):
        return int(value)
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return int(ts.value // _MS)


def _hour_text(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%dT%H:00:00Z")


def _keys(values: Iterable[tuple[str, str]] | None) -> tuple[tuple[str, str], ...]:
    if values is None:
        return ()
    out = set()
    for value in values:
        if len(value) != 2:
            raise ValueError("expected account keys are (address, account) pairs")
        out.add((str(value[0]).lower(), str(value[1]).lower()))
    return tuple(sorted(out))


def _require_columns(frame: pd.DataFrame, required: Iterable[str], name: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {', '.join(missing)}")


def _prepare_accounts(accounts: pd.DataFrame) -> pd.DataFrame:
    _require_columns(accounts, ("hour_utc", *ACCOUNT_KEY, "time_ms"), "accounts")
    out = accounts.copy()
    out["_event_hour"] = pd.to_datetime(out["hour_utc"], utc=True, errors="coerce").dt.floor("h")
    out["address"] = out["address"].astype(str).str.lower()
    out["account"] = out["account"].astype(str).str.lower()
    out["_server_ms"] = pd.to_numeric(out["time_ms"], errors="coerce")
    return out


def _prepare_positions(positions: pd.DataFrame, accounts: pd.DataFrame | None) -> pd.DataFrame:
    _require_columns(positions, ("hour_utc", *POSITION_KEY, "szi"), "positions")
    out = positions.copy()
    out["_event_hour"] = pd.to_datetime(out["hour_utc"], utc=True, errors="coerce").dt.floor("h")
    out["address"] = out["address"].astype(str).str.lower()
    out["account"] = out["account"].astype(str).str.lower()
    out["_row_order"] = range(len(out))
    if "time_ms" in out:
        out["_server_ms"] = pd.to_numeric(out["time_ms"], errors="coerce")
    else:
        out["_server_ms"] = float("nan")

    # Close rows intentionally have NaN in all fields except szi=0.  The
    # account snapshot at the same hour is their only recorded server time.
    if accounts is not None:
        times = accounts[["_event_hour", "address", "account", "_server_ms"]].copy()
        times = times.drop_duplicates(["_event_hour", "address", "account"], keep="last")
        # Give the account timestamp a unique name before merging.  Relying
        # on pandas' suffixes here is brittle because the existing position
        # timestamp is also named ``_server_ms``; pandas consequently creates
        # ``_server_ms_account_ms``, not the shorter name callers might infer.
        times = times.rename(columns={"_server_ms": "_account_server_ms"})
        out = out.merge(times, on=["_event_hour", "address", "account"], how="left")
        out["_server_ms"] = out["_server_ms"].fillna(out["_account_server_ms"])
        out = out.drop(columns=["_account_server_ms"])
    return out


def _empty_with_flags(columns: Iterable[str]) -> pd.DataFrame:
    out = pd.DataFrame(columns=list(columns))
    for name, dtype in (("source_hour_utc", "object"), ("source_time_ms", "float64"),
                        ("state_fresh", "boolean"), ("state_stale", "boolean")):
        out[name] = pd.Series(dtype=dtype)
    return out


def strict_rebuild(
    positions: pd.DataFrame,
    hour,
    *,
    accounts: pd.DataFrame | None,
    expected_accounts: Iterable[tuple[str, str]] | None,
    cutoff_ms=None,
    max_age_ms: int | None = None,
) -> StrictSnapshot:
    """Rebuild a state without using observations after an explicit cutoff.

    ``hour`` is the state label being requested.  By default the server-time
    cutoff is the start of that hour; pass a later cutoff only when that
    receipt time is part of the registered information set.  Rows labelled
    after ``hour`` or observed after the cutoff are excluded.  Carried rows
    remain visible for diagnostics, but are marked ``state_stale`` whenever
    the expected account was not observed freshly at the requested hour.

    ``accounts`` and ``expected_accounts`` are required for a fail-closed
    availability decision.  Passing ``None`` for either preserves useful
    reconstruction output but makes ``availability.available`` false.
    """

    requested = _hour(hour)
    cutoff = requested.value // _MS if cutoff_ms is None else _millis(cutoff_ms)
    if max_age_ms is not None and max_age_ms < 0:
        raise ValueError("max_age_ms must be non-negative")

    account_frame = _prepare_accounts(accounts) if accounts is not None else None
    position_frame = _prepare_positions(positions, account_frame)
    expected = _keys(expected_accounts)
    expected_set = set(expected)

    if account_frame is not None:
        exact = account_frame[account_frame["_event_hour"] == requested]
        observed = set(zip(exact["address"], exact["account"]))
        duplicate_frame = exact[exact.duplicated(["address", "account"], keep=False)]
        duplicate = set(zip(duplicate_frame["address"], duplicate_frame["account"]))
        exact_time = {
            (address, account): server_ms
            for address, account, server_ms in zip(
                exact["address"], exact["account"], exact["_server_ms"]
            )
        }
    else:
        exact = pd.DataFrame()
        observed, duplicate, exact_time = set(), set(), {}

    missing = expected_set - observed
    late = set()
    stale = set()
    for key in expected_set & observed:
        server_ms = exact_time.get(key)
        if pd.isna(server_ms) or float(server_ms) > cutoff:
            late.add(key)
            continue
        if max_age_ms is not None and cutoff - int(server_ms) > max_age_ms:
            stale.add(key)

    if account_frame is None:
        future_accounts = 0
    else:
        # A row is outside the information set when either its label is after
        # the requested hour or its observed server time is after the cutoff.
        # Counting both cases makes a missing hour visible even when the only
        # available account row is the following hour's snapshot.
        future_accounts = int(((account_frame["_event_hour"] > requested)
                               | (account_frame["_server_ms"] > cutoff)).sum())

    valid_label = position_frame["_event_hour"] <= requested
    finite_time = position_frame["_server_ms"].notna()
    future_positions = int(((position_frame["_event_hour"] > requested)
                            | (finite_time & (position_frame["_server_ms"] > cutoff))).sum())
    untimed = int((valid_label & ~finite_time).sum())
    known = position_frame[valid_label & finite_time & (position_frame["_server_ms"] <= cutoff)].copy()

    # Stable order means a same-time close/change is resolved in file order,
    # just as the scraper's existing rebuild does for its hour labels.
    known = known.sort_values(["_event_hour", "_server_ms", "_row_order"], kind="stable")
    if len(known):
        last = known.drop_duplicates(list(POSITION_KEY), keep="last")
        open_rows = last[pd.to_numeric(last["szi"], errors="coerce") != 0].copy()
    else:
        open_rows = _empty_with_flags(position_frame.columns)

    fresh_accounts = {
        key: (key in observed and key not in duplicate and key not in late and key not in stale
              and key in expected_set)
        for key in expected_set
    }
    if len(open_rows):
        state_fresh = [bool(fresh_accounts.get((a, c), False)) for a, c in
                        zip(open_rows["address"], open_rows["account"])]
        open_rows["state_fresh"] = state_fresh
        open_rows["state_stale"] = [not x for x in state_fresh]
        open_rows["source_hour_utc"] = open_rows["_event_hour"].map(_hour_text)
        open_rows["source_time_ms"] = open_rows["_server_ms"].astype(float)
    else:
        open_rows = _empty_with_flags(position_frame.columns)

    # Internal columns are implementation details; the source hour/time and
    # freshness flags are the deliberately exposed diagnostic contract.
    drop = [c for c in ("_event_hour", "_server_ms", "_row_order") if c in open_rows]
    open_rows = open_rows.drop(columns=drop)

    if accounts is None:
        reason = "accounts_source_required"
    elif expected_accounts is None:
        reason = "expected_accounts_required"
    elif not expected:
        reason = "expected_accounts_empty"
    elif duplicate:
        reason = "duplicate_account_rows"
    elif not len(exact):
        reason = "missing_hour"
    elif missing:
        reason = "missing_accounts"
    elif late:
        reason = "late_server_time"
    elif stale:
        reason = "stale_state"
    else:
        reason = "ok"

    available = reason == "ok"
    report = SnapshotAvailability(
        requested_hour=_hour_text(requested),
        cutoff_ms=cutoff,
        expected_accounts=tuple(sorted(expected_set)),
        observed_accounts=tuple(sorted(observed)),
        missing_accounts=tuple(sorted(missing)),
        late_accounts=tuple(sorted(late)),
        stale_accounts=tuple(sorted(stale)),
        duplicate_accounts=tuple(sorted(duplicate)),
        hour_present=bool(len(exact)),
        future_account_rows=future_accounts,
        future_position_rows=future_positions,
        untimed_position_rows=untimed,
        available=available,
        reason=reason,
    )
    return StrictSnapshot(open_rows.reset_index(drop=True), report)


def strict_positions_at(
    day: str,
    hour,
    *,
    root: str | Path | None = None,
    expected_accounts: Iterable[tuple[str, str]] | None,
    cutoff_ms=None,
    max_age_ms: int | None = None,
) -> StrictSnapshot:
    """Read one day's files and apply :func:`strict_rebuild`.

    Unlike ``scripts.scrape_hyperliquid.positions_at``, ``hour`` is required;
    an implicit latest hour is unsafe for a point-in-time consumer.  An
    integer hour is accepted for convenience (0--23).
    """

    if isinstance(hour, int):
        if not 0 <= hour <= 23:
            raise ValueError("hour must be in 0..23")
        hour = f"{day}T{hour:02d}:00:00Z"
    base = (Path(root) if root is not None else
            Path(__file__).resolve().parents[1] / "experiments" / "copylead_data" / "hyperliquid")
    position_path = base / "positions" / f"{day}.csv.gz"
    account_path = base / "accounts" / f"{day}.csv.gz"
    positions = pd.read_csv(position_path, compression="infer", float_precision="round_trip")
    accounts = pd.read_csv(account_path, compression="infer", float_precision="round_trip")
    return strict_rebuild(positions, hour, accounts=accounts, expected_accounts=expected_accounts,
                          cutoff_ms=cutoff_ms, max_age_ms=max_age_ms)
