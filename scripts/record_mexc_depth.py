"""Record MEXC order-book costs for the R224 forward universe.

The legacy ``journal/depth.csv`` file is deliberately kept to its original
schema. Retry, receipt, contract-size and fill-denominator information is
written to ``journal/depth_attempts.jsonl`` instead. A half-hour slot is the
idempotency key for a source symbol and its MEXC contract: a successful legacy
row is never appended twice, while a failed request may be retried and each
attempt is retained in the sidecar.

This module only reads public market data. It never places an order.
"""
import json
import math
import sys
import time
import warnings
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import forward_tick as ft  # noqa: E402
from lab import engine, live, mexc, prereg  # noqa: E402

LANE = ROOT / "experiments" / "mexc_costs"
J = LANE / "journal"
TRADFI = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
SIZES = (1_000, 10_000, 50_000)
BAND, API_TAKER, LEVELS = 0.005, 0.0008, 50
MAX_RETRIES, RETRY_DELAY = 3, 0.25
SIDECAR = "depth_attempts.jsonl"
SLOT_MINUTES = 30
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

# This is the frozen R224 journal schema. Do not add sidecar fields here.
LEGACY_COLUMNS = (
    "run_at", "symbol", "contract", "signal_hour", "rank", "fee_taker", "fee_maker", "t", "bid", "ask",
    "half_spread_bp", "buy_1k", "sell_1k", "buy_10k", "sell_10k", "buy_50k", "sell_50k", "bid_depth_05",
    "bid_reach_bp", "ask_depth_05", "ask_reach_bp",
)
IMPACT_KEYS = tuple(f"{side}_{n // 1000}k" for n in SIZES for side in ("buy", "sell"))
STATUS_COLUMNS = (
    "half_spread_bp", "impact_1k", "impact_10k", "impact_50k", "web_10k", "api_10k", "web_50k", "api_50k",
    "bid_depth_05", "ask_depth_05",
)


def _finite_positive(value, name):
    """Return a finite positive float or reject a malformed venue value."""
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be finite and positive")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and positive") from exc
    if not np.isfinite(x) or x <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return x


def _level(level, side_name, index):
    if isinstance(level, (str, bytes)) or not hasattr(level, "__len__") or len(level) < 2:
        raise ValueError(f"{side_name}[{index}] must contain price and quantity")
    price = _finite_positive(level[0], f"{side_name}[{index}].price")
    try:
        quantity = float(level[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{side_name}[{index}].quantity must be nonnegative") from exc
    if not np.isfinite(quantity) or quantity < 0:
        raise ValueError(f"{side_name}[{index}].quantity must be nonnegative")
    return (price, quantity, *tuple(level[2:]))


def _validate_levels(levels, side_name, descending=None):
    if levels is None or isinstance(levels, (str, bytes)):
        raise ValueError(f"{side_name} levels are missing")
    try:
        levels = list(levels)
    except TypeError as exc:
        raise ValueError(f"{side_name} levels are not iterable") from exc
    if not levels:
        raise ValueError(f"{side_name} levels are empty")
    out = [_level(level, side_name, i) for i, level in enumerate(levels)]
    prices = [level[0] for level in out]
    ascending = all(a <= b for a, b in zip(prices, prices[1:]))
    descending_order = all(a >= b for a, b in zip(prices, prices[1:]))
    if descending is None:
        ordered = ascending or descending_order
    elif descending:
        ordered = descending_order
    else:
        ordered = ascending
    if not ordered:
        order = "descending" if descending else "ascending or descending"
        raise ValueError(f"{side_name} prices must be ordered {order}")
    return out


def validate_book(asks, bids):
    """Validate and normalize an order book before any impact calculation."""
    asks = _validate_levels(asks, "asks", descending=False)
    bids = _validate_levels(bids, "bids", descending=True)
    if bids[0][0] >= asks[0][0]:
        raise ValueError("book is crossed or locked")
    return asks, bids


def _walk_detail(levels, cs, notional, mid, descending=None):
    """Return (impact_bp, filled_usdt), preserving the historical impact formula."""
    cs = _finite_positive(cs, "contract_size")
    notional = _finite_positive(notional, "notional")
    mid = _finite_positive(mid, "mid")
    levels = _validate_levels(levels, "levels", descending=descending)
    left, cost, filled = float(notional), 0.0, 0.0
    for p, v, *_ in levels:
        take = min(left, p * v * cs)
        cost += take * abs(p / mid - 1)
        filled += take
        left -= take
        if left <= 0:
            return cost / notional * 1e4, filled
    return np.nan, filled


def walk(levels, cs, notional, mid, descending=None):
    """Impact in bp, walking ``[[price, contracts, ...], ...]``.

    ``descending`` can pin bid ordering; when omitted, either monotonic book
    direction is accepted for compatibility with the original helper.
    The result is NaN when the displayed levels are too thin to fill the
    requested notional. This retains the original R224 formula exactly.
    """
    return _walk_detail(levels, cs, notional, mid, descending=descending)[0]


def side(levels, cs, mid, descending=None):
    """USDT within BAND of mid, and how far the displayed levels reach."""
    cs = _finite_positive(cs, "contract_size")
    mid = _finite_positive(mid, "mid")
    levels = _validate_levels(levels, "levels", descending=descending)
    near = sum(p * v * cs for p, v, *_ in levels if abs(p / mid - 1) <= BAND)
    return near, abs(levels[-1][0] / mid - 1) * 1e4


def _receipt_ms(value):
    """Validate the API receipt timestamp and return it as an integer."""
    x = _finite_positive(value, "depth timestamp")
    return int(x)


def _timestamp(value=None):
    if value is None:
        return pd.Timestamp.now(tz="UTC")
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)):
        x = float(value)
        if not np.isfinite(x):
            raise ValueError("timestamp must be finite")
        return pd.Timestamp(x, unit="ms" if abs(x) >= 1e11 else "s", tz="UTC")
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _run_at(value=None):
    return _timestamp(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def slot_key(value=None):
    """UTC half-hour slot used for idempotency."""
    return _timestamp(value).floor(f"{SLOT_MINUTES}min").strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_ms(value):
    if value is None:
        return None
    try:
        ts = _timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return ts.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _local_ms():
    """Wall-clock milliseconds from the recorder host, sampled at the boundary."""
    return time.time_ns() // 1_000_000


def _timing_metadata(request_start_ms, receive_ms, exchange_ms=None):
    metadata = {"request_start_ms": request_start_ms, "receive_ms": receive_ms,
                "receive_time": _iso_ms(receive_ms), "age_ms": None, "clock_skew_ms": None}
    if exchange_ms is not None:
        metadata.update({"age_ms": receive_ms - exchange_ms,
                         "clock_skew_ms": exchange_ms - (request_start_ms + receive_ms) / 2.0})
    return metadata


def _attach_timing(exc, request_start_ms, receive_ms, exchange_ms=None):
    try:
        exc.depth_timing = _timing_metadata(request_start_ms, receive_ms, exchange_ms)
    except Exception:
        pass
    return exc


def _snapshot_details(c, cs):
    cs = _finite_positive(cs, "contract_size")
    request_start_ms = _local_ms()
    try:
        d = mexc.get(f"depth/{c}", {"limit": LEVELS})
    except Exception as exc:
        receive_ms = _local_ms()
        raise _attach_timing(exc, request_start_ms, receive_ms) from exc
    receive_ms = _local_ms()
    if not isinstance(d, dict):
        raise _attach_timing(ValueError("depth response must be an object"), request_start_ms, receive_ms)
    try:
        asks, bids = validate_book(d.get("asks"), d.get("bids"))
        receipt_ms = _receipt_ms(d.get("timestamp"))
    except Exception as exc:
        raise _attach_timing(exc, request_start_ms, receive_ms) from exc
    bid, ask = bids[0][0], asks[0][0]
    mid = _finite_positive((bid + ask) / 2, "mid")
    row = {"t": receipt_ms, "bid": bid, "ask": ask, "half_spread_bp": (ask - bid) / 2 / mid * 1e4}
    fills = {}
    for n in SIZES:
        buy, buy_filled = _walk_detail(asks, cs, n, mid)
        sell, sell_filled = _walk_detail(bids, cs, n, mid, descending=True)
        k = f"{n // 1000}k"
        row[f"buy_{k}"] = buy
        row[f"sell_{k}"] = sell
        fills[f"buy_{k}"] = {"requested_usdt": float(n), "filled_usdt": float(buy_filled),
                               "defined": bool(np.isfinite(buy))}
        fills[f"sell_{k}"] = {"requested_usdt": float(n), "filled_usdt": float(sell_filled),
                               "defined": bool(np.isfinite(sell))}
    (row["bid_depth_05"], row["bid_reach_bp"]) = side(bids, cs, mid, descending=True)
    (row["ask_depth_05"], row["ask_reach_bp"]) = side(asks, cs, mid)
    timing = _timing_metadata(request_start_ms, receive_ms, receipt_ms)
    return row, {"receipt_ms": receipt_ms, "receipt_time": _iso_ms(receipt_ms),
                 "exchange_timestamp_ms": receipt_ms, "exchange_time": _iso_ms(receipt_ms),
                 **timing, "fill_denominators": fills}


def snapshot(c, cs):
    """Read and validate one depth snapshot, returning the frozen row payload."""
    return _snapshot_details(c, cs)[0]


def _json_clean(value):
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, dict):
        return {str(k): _json_clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_clean(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _append_sidecar(events, path):
    if not events:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(_json_clean(event), sort_keys=True, allow_nan=False) + "\n")


def _sidecar_state(path, slot, symbol, contract):
    """Return (next_attempt, successful_before) for one slot/contract."""
    maximum, success = 0, False
    path = Path(path)
    if not path.exists():
        return 1, False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 1, False
    for line in lines:
        try:
            event = json.loads(line)
        except (TypeError, ValueError):
            continue
        if event.get("slot") != slot or event.get("symbol") != symbol or event.get("contract") != contract:
            continue
        try:
            maximum = max(maximum, int(event.get("attempt", 0)))
        except (TypeError, ValueError):
            pass
        success |= event.get("status") == "success"
    return maximum + 1, success


def _sidecar_key(event):
    if any(event.get(field) is None for field in ("slot", "symbol", "contract")):
        return None
    return tuple(str(event[field]) for field in ("slot", "symbol", "contract"))


def _empty_sidecar_summary():
    return {
        "attempts": 0, "unique_slot_contracts": 0,
        "succeeded": 0, "failed": 0, "recoveries": 0,
        "unrecovered_failures": 0, "rows_written": 0, "rows_failed": 0,
        "succeeded_unique_slot_contracts": 0, "failed_unique_slot_contracts": 0,
        "recovered_unique_slot_contracts": 0,
    }


def _sidecar_summary(path):
    """Summarize append-only attempt and legacy-row events without losing failures."""
    summary = _empty_sidecar_summary()
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return summary
    attempts, rows = [], []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return summary
    for line in lines:
        try:
            event = json.loads(line)
        except (TypeError, ValueError):
            continue
        if event.get("event_type") in ("legacy_row", "row"):
            rows.append(event)
        else:
            attempts.append(event)
    keys = {_sidecar_key(event) for event in attempts}
    keys.discard(None)
    succeeded = {_sidecar_key(event) for event in attempts if event.get("status") == "success"}
    failed = {_sidecar_key(event) for event in attempts if event.get("status") == "failed"}
    succeeded.discard(None)
    failed.discard(None)
    recoveries = succeeded & failed
    written = {_sidecar_key(event) for event in rows
               if event.get("status") == "written" or event.get("legacy_row_written") is True}
    written.update({_sidecar_key(event) for event in attempts if event.get("legacy_row_written") is True})
    written.discard(None)
    row_failed = {_sidecar_key(event) for event in rows if event.get("status") == "write_failed"}
    row_failed.discard(None)
    summary.update({
        "attempts": len(attempts), "unique_slot_contracts": len(keys),
        "succeeded": len(succeeded), "failed": len(failed), "recoveries": len(recoveries),
        "unrecovered_failures": len(failed - succeeded), "rows_written": len(written),
        "rows_failed": len(row_failed), "succeeded_unique_slot_contracts": len(succeeded),
        "failed_unique_slot_contracts": len(failed), "recovered_unique_slot_contracts": len(recoveries),
    })
    return summary


def _legacy_successes(path, slot):
    """Pairs already written to the legacy file in this half-hour slot."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return set()
    try:
        x = pd.read_csv(path, usecols=["run_at", "symbol", "contract"])
    except (OSError, ValueError, pd.errors.ParserError):
        return set()
    out = set()
    for row in x.itertuples(index=False):
        try:
            if slot_key(row.run_at) == slot:
                out.add((str(row.symbol), str(row.contract)))
        except (TypeError, ValueError, OverflowError):
            continue
    return out


def _rank_value(now, symbol):
    value = now[symbol]
    if isinstance(value, pd.Series):
        value = value.iloc[-1]
    try:
        return float(value) if np.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return None


def _metadata_value(info, contract, column):
    try:
        value = info.loc[contract, column]
    except (KeyError, TypeError, AttributeError):
        return None
    try:
        return float(value) if np.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return None


def _raw_metadata_value(info, contract, column):
    """Read one frozen contract-table field without losing categorical metadata."""
    try:
        value = info.loc[contract, column]
    except (KeyError, TypeError, AttributeError):
        return None
    if isinstance(value, pd.Series):
        if len(value) != 1:
            return None
        value = value.iloc[0]
    if value is pd.NA or value is pd.NaT:
        return None
    try:
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and missing:
            return None
    except (TypeError, ValueError):
        pass
    return _json_clean(value)


def _contract_metadata(info, contract):
    """Snapshot the available venue metadata alongside every attempt."""
    return {name: _raw_metadata_value(info, contract, name)
            for name in ("symbol", "contract_size", "type", "state", "settle", "taker", "maker")}


def _attempt_base(symbol, contract, signal_hour, rank, slot, run_at, attempt, metadata):
    return {
        "event_type": "attempt", "slot": slot, "run_at": run_at, "attempted_at": _run_at(),
        "attempt": attempt, "symbol": symbol, "contract": contract, "signal_hour": signal_hour,
        "rank": rank, "contract_size": metadata.get("contract_size"),
        "contract_metadata": metadata, "contract_type": metadata.get("type"),
        "contract_state": metadata.get("state"), "contract_settle": metadata.get("settle"),
        "type": metadata.get("type"), "state": metadata.get("state"), "settle": metadata.get("settle"),
        "fee_taker": metadata.get("taker"), "fee_maker": metadata.get("maker"),
        "receipt_ms": None, "receipt_time": None, "exchange_timestamp_ms": None,
        "exchange_time": None, "request_start_ms": None, "receive_ms": None,
        "receive_time": None, "age_ms": None, "clock_skew_ms": None,
        "fill_denominators": {}, "legacy_row_written": False,
    }


def _attempts_for(symbol, contract, cs, signal_hour, rank, slot, run_at, start_attempt, max_retries,
                  retry_delay, metadata):
    events, row = [], None
    count = max(1, int(max_retries))
    for n in range(start_attempt, start_attempt + count):
        base = _attempt_base(symbol, contract, signal_hour, rank, slot, run_at, n, metadata)
        try:
            snap, meta = _snapshot_details(contract, cs)
            event = {**base, "status": "success", **meta}
            events.append(event)
            row = {"run_at": run_at, "symbol": symbol, "contract": contract, "signal_hour": signal_hour,
                   "rank": rank, "fee_taker": None, "fee_maker": None, **snap}
            break
        except Exception as exc:  # one malformed/failed contract must not abort the universe
            events.append({**base, **getattr(exc, "depth_timing", {}), "status": "failed", "error_type": type(exc).__name__,
                           "error": str(exc)[:500]})
            if n + 1 < start_attempt + count and retry_delay:
                time.sleep(float(retry_delay))
    return row, events


def _empty_record_summary(slot, run_at, source=0, universe_resolved=None, universe_error=None):
    return {"slot": slot, "run_at": run_at, "source_symbols": int(source), "mapped_contracts": 0,
            "attempted": 0, "recorded": 0, "failed": 0, "skipped": 0, "write_failed": 0,
            "universe_resolved": universe_resolved, "universe_error": universe_error}


def record(sig=None, run_at=None, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY, workers=4,
           depth_path=None, sidecar_path=None):
    """Record one slot, safely tolerating empty inputs and failed contracts.

    Optional arguments are dependency-injection hooks for deterministic tests;
    the command-line behavior remains the original R224 invocation.
    """
    depth_path = Path(depth_path or J / "depth.csv")
    sidecar_path = Path(sidecar_path or J / SIDECAR)
    run_at = _run_at(run_at)
    slot = slot_key(run_at)
    if sig is None:
        sig = ft.read("signals.csv")
    if sig is None or not isinstance(sig, pd.DataFrame) or sig.empty:
        log("no signal source; no depth rows recorded")
        return _empty_record_summary(slot, run_at, 0)
    required = {"t", "symbol", "rank"}
    if not required.issubset(sig.columns):
        log("signal source lacks required columns; no depth rows recorded")
        return _empty_record_summary(slot, run_at, len(sig))
    times = pd.to_numeric(sig["t"], errors="coerce").dropna()
    if times.empty:
        log("signal source has no timestamp; no depth rows recorded")
        return _empty_record_summary(slot, run_at, len(sig))
    last = int(times.max())
    now_frame = sig[pd.to_numeric(sig["t"], errors="coerce") == last].drop_duplicates("symbol", keep="last")
    if now_frame.empty:
        return _empty_record_summary(slot, run_at, len(sig))
    now = now_frame.set_index("symbol")["rank"]
    symbols = [str(s) for s in now.index]
    try:
        table = mexc.contracts()
    except Exception as exc:
        log("contract source failed", exc)
        return _empty_record_summary(slot, run_at, len(symbols))
    if table is None or table.empty or "symbol" not in table.columns:
        log("empty contract source; no depth rows recorded")
        return _empty_record_summary(slot, run_at, len(symbols))
    mp = mexc.map_symbols(symbols, table)
    # This guard is mandatory: aliases such as PEPE and 1000PEPE cannot become
    # independent positions or duplicate depth observations.
    mexc.require_unique_mapping(mp)
    try:
        current_tradfi = set(live.tradfi())
    except Exception as exc:
        message = f"TradFi filter unavailable; universe unresolved: {exc}"
        log(message)
        return _empty_record_summary(slot, run_at, len(symbols), universe_resolved=False,
                                     universe_error=str(exc)[:500])
    excluded = TRADFI | current_tradfi
    for symbol in excluded & set(mp):
        mp[symbol] = None
    info = table.set_index("symbol", drop=False)
    existing = _legacy_successes(depth_path, slot)
    candidates = [(s, mp.get(s)) for s in symbols if mp.get(s)]
    rows, all_events = [], []
    summary = _empty_record_summary(slot, run_at, len(symbols))
    summary["universe_resolved"] = True
    summary["mapped_contracts"] = len(candidates)
    prepared = []
    for symbol, contract in candidates:
        if (symbol, contract) in existing:
            summary["skipped"] += 1
            continue
        metadata = _contract_metadata(info, contract)
        try:
            cs = _finite_positive(metadata.get("contract_size"), "contract_size")
        except Exception as exc:
            start_attempt, _ = _sidecar_state(sidecar_path, slot, symbol, contract)
            event = _attempt_base(symbol, contract, last, _rank_value(now, symbol), slot, run_at,
                                  start_attempt, metadata)
            event.update({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:500]})
            all_events.append(event)
            summary["attempted"] += 1
            summary["failed"] += 1
            continue
        start_attempt, _ = _sidecar_state(sidecar_path, slot, symbol, contract)
        prepared.append((symbol, contract, cs, _rank_value(now, symbol), start_attempt, metadata))
    summary["attempted"] += len(prepared)

    def run_job(item):
        symbol, contract, cs, rank, start_attempt, metadata = item
        return item, _attempts_for(symbol, contract, cs, last, rank, slot, run_at,
                                   start_attempt, max_retries, retry_delay, metadata)

    jobs = []
    if prepared:
        if workers is None or int(workers) <= 1:
            jobs = [run_job(item) for item in prepared]
        else:
            with ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
                jobs = list(ex.map(run_job, prepared))
    successful = []
    for item, (row, events) in jobs:
        symbol, contract, cs, rank, _, metadata = item
        all_events.extend(events)
        if row is None:
            summary["failed"] += 1
            continue
        row["fee_taker"] = metadata.get("taker")
        row["fee_maker"] = metadata.get("maker")
        success_event = next((event for event in events
                              if event.get("event_type") == "attempt" and event.get("status") == "success"), None)
        rows.append(row)
        successful.append((row, success_event, item))

    row_events = []
    write_error = None
    if rows:
        try:
            depth_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows, columns=LEGACY_COLUMNS).to_csv(
                depth_path, mode="a", header=not depth_path.exists() or depth_path.stat().st_size == 0, index=False)
        except Exception as exc:  # retain an explicit sidecar record if the legacy append fails
            write_error = exc

    for row, success_event, item in successful:
        symbol, contract, cs, rank, _, metadata = item
        if write_error is None:
            if success_event is not None:
                success_event["legacy_row_written"] = True
            summary["recorded"] += 1
            row_events.append({"event_type": "legacy_row", "status": "written", "legacy_row_written": True,
                               "slot": slot, "run_at": run_at, "attempt": success_event.get("attempt") if success_event else None,
                               "symbol": symbol, "contract": contract, "signal_hour": last, "rank": rank,
                               "contract_size": metadata.get("contract_size"), "contract_metadata": metadata,
                               "type": metadata.get("type"), "state": metadata.get("state"),
                               "settle": metadata.get("settle"),
                               "fee_taker": metadata.get("taker"), "fee_maker": metadata.get("maker"),
                               "error": None})
        else:
            summary["failed"] += 1
            summary.setdefault("write_failed", 0)
            summary["write_failed"] += 1
            if success_event is not None:
                success_event["legacy_row_written"] = False
            row_events.append({"event_type": "legacy_row", "status": "write_failed", "legacy_row_written": False,
                               "slot": slot, "run_at": run_at, "attempt": success_event.get("attempt") if success_event else None,
                               "symbol": symbol, "contract": contract, "signal_hour": last, "rank": rank,
                               "contract_size": metadata.get("contract_size"), "contract_metadata": metadata,
                               "type": metadata.get("type"), "state": metadata.get("state"),
                               "settle": metadata.get("settle"),
                               "fee_taker": metadata.get("taker"), "fee_maker": metadata.get("maker"),
                               "error_type": type(write_error).__name__, "error": str(write_error)[:500]})
    all_events.extend(row_events)
    _append_sidecar(all_events, sidecar_path)
    log(f"recorded {summary['recorded']} of {len(candidates)} contracts; skipped {summary['skipped']}; failed {summary['failed']}; "
        f"unmapped or TradFi: {sorted(s for s in symbols if not mp.get(s))}")
    return summary


def _impact_counts(x):
    out = {}
    for n in SIZES:
        k = f"{n // 1000}k"
        out[k] = {}
        for side_name in ("buy", "sell"):
            field = f"{side_name}_{k}"
            values = pd.to_numeric(x[field], errors="coerce") if field in x else pd.Series(dtype=float)
            observed = int(np.isfinite(values.to_numpy(dtype=float)).sum())
            total = int(len(values))
            out[k][side_name] = {"observed": observed, "undefined": total - observed, "total": total}
    return out


def _coverage(values):
    values = pd.to_numeric(values, errors="coerce")
    finite = np.isfinite(values.to_numpy(dtype=float))
    observed = int(finite.sum())
    total = int(len(finite))
    return {"observed": observed, "undefined": total - observed, "total": total}


def _none_or_float(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def _safe_median(values):
    """Median helper that keeps an all-undefined column quiet and explicit."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return values.median()


def _empty_status(status_path=None, sidecar_path=None):
    cols = {c: None for c in STATUS_COLUMNS + ("assumed_bp",)}
    den = {f"{n // 1000}k": {s: {"observed": 0, "undefined": 0, "total": 0} for s in ("buy", "sell")}
           for n in SIZES}
    zero = {"observed": 0, "undefined": 0, "total": 0}
    sidecar = _sidecar_summary(sidecar_path or J / SIDECAR)
    fee_coverage = {"taker": dict(zero), "maker": dict(zero),
                    "10k": {"web": dict(zero), "api": dict(zero)}}
    coin_den = {"web_10k": dict(zero), "api_10k": dict(zero)}
    out = {"snapshots": 0, "first": None, "last": None, "coins": 0, "report_from": "2026-11-03",
           "median_over_coins": cols, "impact_denominators": den, "impact_statistics": den,
           "share_web_10k_above_assumed": None, "share_api_10k_above_assumed": None,
           "share_web_10k_above_assumed_observed_only": None,
           "share_api_10k_above_assumed_observed_only": None,
           "coin_denominators": coin_den, "fee_coverage": fee_coverage,
           "fee_coverage_10k": fee_coverage["10k"],
           "fee_denominators_10k": fee_coverage["10k"],
           "cost_coverage_10k": {"web": dict(zero), "api": dict(zero)},
           "sidecar": sidecar, "attempts": sidecar["attempts"],
           "succeeded_unique_slot_contracts": sidecar["succeeded_unique_slot_contracts"],
           "failed_unique_slot_contracts": sidecar["failed_unique_slot_contracts"],
           "recoveries": sidecar["recoveries"], "coins_50k_unfilled_most_snapshots": [], "per_coin": []}
    if status_path is not None:
        status_path = Path(status_path)
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(_json_clean(out), indent=1, allow_nan=False) + "\n")
    return out


def status(depth_path=None, status_path=None, sidecar_path=None):
    """Summarize depth observations, retaining undefined impact denominators."""
    depth_path = Path(depth_path or J / "depth.csv")
    status_path = Path(status_path or J / "status.json")
    sidecar_path = Path(sidecar_path or J / SIDECAR)
    if not depth_path.exists() or depth_path.stat().st_size == 0:
        return _empty_status(status_path, sidecar_path)
    try:
        x = pd.read_csv(depth_path)
    except (OSError, ValueError, pd.errors.ParserError):
        return _empty_status(status_path, sidecar_path)
    if x.empty:
        return _empty_status(status_path, sidecar_path)
    if "symbol" not in x:
        return _empty_status(status_path, sidecar_path)
    for c in ("fee_taker", "fee_maker", "rank"):
        if c not in x:
            x[c] = np.nan
    for c in STATUS_COLUMNS:
        if c not in x:
            x[c] = np.nan
    for c in IMPACT_KEYS:
        if c not in x:
            x[c] = np.nan
    for c in ("fee_taker", "rank") + IMPACT_KEYS:
        if c in x:
            x[c] = pd.to_numeric(x[c], errors="coerce")
    for n in SIZES:
        k = f"{n // 1000}k"
        x[f"impact_{k}"] = (x[f"buy_{k}"] + x[f"sell_{k}"]) / 2
        x[f"web_{k}"] = x.fee_taker * 1e4 + x[f"impact_{k}"]
        x[f"api_{k}"] = API_TAKER * 1e4 + x[f"impact_{k}"]
    den = _impact_counts(x)
    fee_coverage = {
        "taker": _coverage(x["fee_taker"]), "maker": _coverage(x["fee_maker"]),
        "10k": {"web": _coverage(x["fee_taker"]),
                "api": _coverage(pd.Series(API_TAKER, index=x.index))},
    }
    cost_coverage_10k = {"web": _coverage(x["web_10k"]), "api": _coverage(x["api_10k"])}
    cols = list(STATUS_COLUMNS)
    g = x.groupby("symbol", dropna=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        per = g[cols].median()
    per["rank"] = g["rank"].median()
    rank_values = per["rank"].to_numpy(dtype=float)
    assumed_values = engine.cost_matrix(rank_values) * 1e4
    assumed_values[~np.isfinite(rank_values)] = np.nan
    per["assumed_bp"] = assumed_values
    per["snapshots"] = g.size()
    for n in SIZES:
        k = f"{n // 1000}k"
        values = g[f"impact_{k}"].apply(lambda v: int(np.isfinite(v.to_numpy(dtype=float)).sum()))
        per[f"impact_{k}_observed"] = values
        per[f"impact_{k}_undefined"] = per["snapshots"] - values
    per["unfilled_50k_share"] = g["impact_50k"].apply(
        lambda v: float((~np.isfinite(v.to_numpy(dtype=float))).mean()) if len(v) else 0.0)
    median = {c: _none_or_float(_safe_median(per[c])) if c in per else None for c in cols + ["assumed_bp"]}
    n_coins = int(len(per))
    assumed = per["assumed_bp"].to_numpy(dtype=float)
    web_values = per["web_10k"].to_numpy(dtype=float)
    api_values = per["api_10k"].to_numpy(dtype=float)
    web_observed = np.isfinite(web_values) & np.isfinite(assumed)
    api_observed = np.isfinite(api_values) & np.isfinite(assumed)
    web_count = int(web_observed.sum())
    api_count = int(api_observed.sum())
    web_above = float((web_values[web_observed] > assumed[web_observed]).mean()) if web_count else None
    api_above = float((api_values[api_observed] > assumed[api_observed]).mean()) if api_count else None
    coin_den = {
        "web_10k": {"observed": web_count, "undefined": n_coins - web_count, "total": n_coins},
        "api_10k": {"observed": api_count, "undefined": n_coins - api_count, "total": n_coins},
    }
    coin_den["share_web_10k_above_assumed"] = dict(coin_den["web_10k"])
    coin_den["share_api_10k_above_assumed"] = dict(coin_den["api_10k"])
    first = x["run_at"].min() if "run_at" in x else None
    last = x["run_at"].max() if "run_at" in x else None
    sidecar = _sidecar_summary(sidecar_path)
    per_records = per.round(3).reset_index().replace({np.nan: None}).to_dict("records")
    out = {"snapshots": int(x["run_at"].nunique()) if "run_at" in x else 0, "first": first, "last": last,
           "coins": n_coins, "report_from": "2026-11-03", "median_over_coins": median,
           "impact_denominators": den, "impact_statistics": den, "share_web_10k_above_assumed": web_above,
           "share_api_10k_above_assumed": api_above,
           "share_web_10k_above_assumed_observed_only": web_above,
           "share_api_10k_above_assumed_observed_only": api_above,
           "coin_denominators": coin_den, "fee_coverage": fee_coverage,
           "fee_coverage_10k": fee_coverage["10k"], "fee_denominators_10k": fee_coverage["10k"],
           "cost_coverage_10k": cost_coverage_10k,
           "sidecar": sidecar, "attempts": sidecar["attempts"],
           "succeeded_unique_slot_contracts": sidecar["succeeded_unique_slot_contracts"],
           "failed_unique_slot_contracts": sidecar["failed_unique_slot_contracts"],
           "recoveries": sidecar["recoveries"],
           "coins_50k_unfilled_most_snapshots": sorted(per.index[per.unfilled_50k_share > 0.5].tolist()),
           "per_coin": per_records}
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(_json_clean(out), indent=1, allow_nan=False) + "\n")
    m = out["median_over_coins"]
    log(f"{out['snapshots']} snapshots, {out['coins']} coins: median half-spread {m['half_spread_bp']!s} bp, "
        f"web $10k {m['web_10k']!s} bp, API $10k {m['api_10k']!s} bp, assumed {m['assumed_bp']!s} bp")
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    record()
    status()


if __name__ == "__main__":
    main()
