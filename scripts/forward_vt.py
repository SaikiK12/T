"""vt_fwd (R225): R217's volatility target (rule R1) applied forward to the MEXC flow books A and B (R215) and X2
(R218), warmed up on R217's archived daily nets, as set out in experiments/vt_fwd/PREREG.md. Reads the other lanes'
tickets (never writes them); appends to its own journal. Paper only.

usage: python scripts/forward_vt.py   (after scripts/forward_mexc.py and scripts/forward_mexc_sq.py)
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import panel, prereg, stats as lab_stats  # noqa: E402

LANE = ROOT / "experiments" / "vt_fwd"
J = LANE / "journal"
ARCHIVE = ROOT / "experiments" / "sizing_v1" / "results" / "daily.npz"
SOURCES = {"A": ("mexc_fwd", "A_C0"), "B": ("mexc_fwd", "B_C0"), "X2": ("mexc_fwd_sq", "X2")}
RESIZE = 0.0008
DECIDE_DAYS = 365
ARCHIVE_START, ARCHIVE_END = "2021-01-01", "2026-09-30"
ONTIME_START = panel.ms("2026-10-20")
ARCHIVE_RESULTS = ROOT / "experiments" / "sizing_v1" / "results" / "results.csv"
ARCHIVE_KEYS = tuple(dict.fromkeys(key for _, key in SOURCES.values()))
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def r1(n):
    """R217's R1 multiplier for every day of n and for the day after its last: m[d] uses n through d - 1."""
    past = pd.Series(np.append(n, np.nan)).shift(1)
    sig_hat = past.ewm(halflife=30, min_periods=90).std().values
    sig_star = past.expanding(min_periods=90).std().values
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.clip(sig_star / sig_hat, 0, 2)
    return np.where(np.isfinite(m), m, 1.0)


def stats(x):
    eq = np.cumsum(x)
    return {"total": float(x.sum()), "sharpe": float(x.mean() / x.std(ddof=1) * np.sqrt(365)) if len(x) > 1 and
            x.std() > 0 else None, "max_dd": float(np.max(np.maximum.accumulate(np.append(0.0, eq)) - np.append(0.0, eq)))}


def archive_summary(x):
    """R217's committed 1x statistics, used to reject a mismatched restored seed artifact."""
    windows = {"discovery": slice(0, 1095), "validation": slice(1095, 1642), "holdout": slice(1642, 2099)}
    out = {}
    for name, sl in windows.items():
        values = np.asarray(x[sl], dtype=float)
        eq = np.cumsum(values)
        out[name] = {"days": int(len(values)), "mean_bp_day": float(values.mean() * 1e4),
                     "t_nw10": float(lab_stats.newey_west_t(values, 10)[2]),
                     "sharpe": float(values.mean() / values.std() * np.sqrt(365)),
                     "max_dd": float(np.max(np.maximum.accumulate(eq) - eq))}
    return out


def load_archive(path=None, results_path=None):
    """Load and validate the frozen R217 daily series before any journal is touched."""
    path = Path(ARCHIVE if path is None else path)
    results_path = ARCHIVE_RESULTS if results_path is None else Path(results_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"R225 requires {path} (the frozen 2021-01-01..2026-09-30 R217 daily.npz); "
            "restore the owner's exact artifact before running. It is not in Git or the Actions artifacts."
        )
    days = len(pd.date_range(ARCHIVE_START, ARCHIVE_END, freq="D"))
    try:
        with np.load(path, allow_pickle=False) as z:
            absent = sorted(set(ARCHIVE_KEYS) - set(z.files))
            if absent:
                raise ValueError(f"R217 archive missing arrays {absent}")
            arrays = {}
            for key in ARCHIVE_KEYS:
                x = np.asarray(z[key])
                if x.ndim != 1 or len(x) != days or not np.issubdtype(x.dtype, np.number):
                    raise ValueError(f"R217 archive {key} must be a numeric 1D array of {days} days")
                x = x.astype(np.float64, copy=True)
                if not np.isfinite(x).all():
                    raise ValueError(f"R217 archive {key} contains non-finite daily returns")
                arrays[key] = x
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid R217 daily archive {path}: {e}") from e

    summary = pd.read_csv(results_path)
    for key in ARCHIVE_KEYS:
        observed = archive_summary(arrays[key])
        for window, values in observed.items():
            row = summary[(summary.run == key) & (summary.cmult == 1.0) & (summary.window == window)]
            if len(row) != 1 or int(row.iloc[0].days) != values["days"]:
                raise ValueError(f"R217 {key}/{window} does not match its committed results summary")
            for column in ("mean_bp_day", "t_nw10", "sharpe", "max_dd"):
                if not np.isclose(float(row.iloc[0][column]), values[column], rtol=2e-5, atol=2e-7):
                    raise ValueError(f"R217 {key}/{window}/{column} does not match its committed results summary")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return arrays, {"sha256": digest, "days": days, "start": ARCHIVE_START, "end": ARCHIVE_END}


def validate_tickets(frame, book):
    """Validate one source book's append-only daily inputs and frozen date labels."""
    required = {"day", "book", "kind", "net", "net_2x", "net_3x", "gross_exposure"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{book} source tickets missing columns {missing}")
    x = frame[frame.book == book].copy()
    if x.empty:
        raise ValueError(f"{book} has no source tickets")
    if x.day.duplicated().any():
        raise ValueError(f"{book} source has duplicate days")
    days = pd.to_datetime(x.day, format="%Y-%m-%d", errors="raise", utc=True)
    if not days.dt.strftime("%Y-%m-%d").equals(x.day):
        raise ValueError(f"{book} source days must be canonical UTC dates")
    x["day"] = days.dt.strftime("%Y-%m-%d")
    x = x.sort_values("day").reset_index(drop=True)
    if x.day.iloc[0] != "2026-10-01":
        raise ValueError(f"{book} source must start at the frozen replay boundary 2026-10-01")
    observed = pd.DatetimeIndex(pd.to_datetime(x.day, utc=True))
    if not observed.equals(pd.date_range(observed[0], observed[-1], freq="D")):
        raise ValueError(f"{book} source has missing calendar days")
    expect_kind = np.where(observed.asi8 // 1_000_000 >= ONTIME_START, "ontime", "replay")
    if not np.array_equal(x.kind.to_numpy(), expect_kind):
        raise ValueError(f"{book} source kind disagrees with the frozen 2026-10-20 on-time boundary")
    columns = ["net", "net_2x", "net_3x", "gross_exposure"]
    for column in columns:
        x[column] = pd.to_numeric(x[column], errors="raise")
    values = x[columns].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (x.gross_exposure < 0).any():
        raise ValueError(f"{book} source has non-finite returns/cost inputs or negative gross exposure")
    return x


def verify_saved_journal(saved, calculated):
    """Refuse rewritten inputs, changed multipliers, gaps, or historical backfills."""
    if saved.empty:
        return
    required = {"day", "book", "kind", "m", "net", "net_vt", "net_vt_2x", "net_vt_3x", "resize_cost"}
    if required - set(saved.columns) or saved.duplicated(["day", "book"]).any():
        raise ValueError("R225 days journal is malformed or has duplicate keys")
    dates = pd.to_datetime(saved.day, format="%Y-%m-%d", errors="raise", utc=True)
    if not dates.dt.strftime("%Y-%m-%d").equals(saved.day):
        raise ValueError("R225 days journal has non-canonical dates")
    highwater = dates.max().strftime("%Y-%m-%d")
    prior = saved.set_index(["book", "day"])
    current = calculated.set_index(["book", "day"])
    for key, old in prior.iterrows():
        if key not in current.index:
            raise ValueError(f"R225 source removed saved historical day {key}")
        new = current.loc[key]
        if old.kind != new.kind or any(
                not np.isclose(float(old[col]), float(new[col]), rtol=1e-9, atol=1e-12)
                for col in ("m", "net", "net_vt", "net_vt_2x", "net_vt_3x", "resize_cost")):
            raise ValueError(f"R225 source or sizing result changed for saved day {key}")
    keys = set(prior.index)
    backfill = [key for key in current.index if key[1] <= highwater and key not in keys]
    if backfill:
        raise ValueError(f"R225 historical backfill at/before journal high-water {highwater}: {backfill[:5]}")


def calculate_book(archive, frame, book, key):
    """Compute the causal forward R1 series for one validated, date-contiguous source."""
    tickets = validate_tickets(frame, book)
    history = np.asarray(archive[key], dtype=float)
    m_all = r1(np.concatenate([history, tickets.net.values]))
    m = m_all[len(history):-1]
    prev = np.concatenate([[m_all[len(history) - 1]], m[:-1]])
    resize = np.abs(m - prev) * tickets.gross_exposure.values * RESIZE
    result = tickets.assign(m=m, resize_cost=resize, net_vt=m * tickets.net - resize,
                            net_vt_2x=m * tickets.net_2x - 2 * resize,
                            net_vt_3x=m * tickets.net_3x - 3 * resize)
    return result, float(m_all[-1])


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    try:
        arch, archive_meta = load_archive()
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise SystemExit(f"{e}; no R225 journal changes") from e
    p = J / "days.csv"
    try:
        have = pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame()
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise SystemExit(f"Malformed R225 journal {p}: {e}") from e
    status_path = J / "status.json"
    if status_path.exists():
        try:
            old_status = json.loads(status_path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            raise SystemExit(f"Malformed R225 status file {status_path}: {e}") from e
        old_hash = old_status.get("archive", {}).get("sha256")
        if old_hash and old_hash != archive_meta["sha256"]:
            raise SystemExit("R217 archive SHA256 changed since the previous R225 status; refusing to rewrite history")

    computed, next_multiplier = [], {}
    for book, (lane, key) in SOURCES.items():
        source_path = ROOT / "experiments" / lane / "journal" / "tickets.csv"
        if not source_path.is_file():
            raise SystemExit(f"R225 source journal missing: {source_path}")
        source = pd.read_csv(source_path)
        tk, next_multiplier[book] = calculate_book(arch, source, book, key)
        computed.append(tk)
    all_calculated = pd.concat(computed, ignore_index=True)
    try:
        verify_saved_journal(have, all_calculated)
    except (ValueError, KeyError, TypeError) as e:
        raise SystemExit(f"{e}; no R225 rows appended") from e

    done = set(zip(have.day, have.book)) if not have.empty else set()
    rows, status = [], {"archive": archive_meta}
    for (book, (lane, key)), tk in zip(SOURCES.items(), computed):
        rows += [r for r in tk[["day", "book", "kind", "m", "net", "net_vt", "net_vt_2x", "net_vt_3x",
                                "resize_cost"]].to_dict("records") if (r["day"], r["book"]) not in done]
        s = {"m_next": next_multiplier[book], "m_last": float(tk.m.iloc[-1]) if len(tk) else None,
             "source_last_day": tk.day.iloc[-1] if len(tk) else None}
        for kind in ("replay", "ontime"):
            x = tk[tk.kind == kind]
            if x.empty:
                continue
            s[kind] = {"days": int(len(x)), "mean_m": float(x.m.mean()),
                       "unscaled": {**stats(x.net.values), "total_2x": float(x.net_2x.sum()),
                                    "total_3x": float(x.net_3x.sum())},
                       "scaled": {**stats(x.net_vt.values), "total_2x": float(x.net_vt_2x.sum()),
                                  "total_3x": float(x.net_vt_3x.sum())}}
        first = tk[tk.kind == "ontime"].head(DECIDE_DAYS)
        if len(first) == DECIDE_DAYS:                  # the decision uses the first 365 on-time days only
            u, v = stats(first.net.values), stats(first.net_vt.values)
            ok = v["max_dd"] < u["max_dd"] and (v["sharpe"] or 0) >= (u["sharpe"] or 0) - 0.2
            s["verdict_at_365"] = "KEEPS ITS PROMISE" if ok else "DOES NOT"
        status[book] = s
    J.mkdir(parents=True, exist_ok=True)
    if rows:
        pd.DataFrame(rows).to_csv(p, mode="a", header=not p.exists() or p.stat().st_size == 0, index=False)
        log(f"journaled {len(rows)} rows")
    status_path.write_text(json.dumps(status, indent=1, default=float))
    log({b: (round(s["m_next"], 2), s.get("ontime", {}).get("days", 0)) for b, s in status.items()})


if __name__ == "__main__":
    main()
