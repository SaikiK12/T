#!/usr/bin/env python3
"""R229: frozen, bounded daily spot trend screen. Importing reads no prices."""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import prereg, stats  # noqa: E402
from scripts import fetch_trend_daily as fetcher  # noqa: E402

LANE = ROOT / "experiments/slow_trend_v1"
HORIZONS = (5, 10, 20, 30, 60, 90, 150, 250, 360)
SPLITS = {"discovery": ("2022-01-01", "2024-01-01"),
          "validation": ("2024-01-01", "2025-07-01"),
          "known_holdout": ("2025-07-01", "2026-10-01")}
DAY_MS = 86_400_000
HEADERS = {
    ("open_time", "open", "high", "low", "close", "volume", "close_time",
     "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"),
    ("open_time", "open", "high", "low", "close", "volume", "close_time",
     "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume",
     "taker_buy_quote_asset_volume", "ignore"),
}


class ContractError(ValueError):
    """The frozen data or calculation contract cannot be satisfied."""


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def date_range(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    return tuple((first + timedelta(days=i)).isoformat() for i in range((last-first).days))


def parse_archive(payload, name):
    """Validate one complete source month; normalize its documented timestamp unit."""
    match = re.fullmatch(r"([A-Z]+)-1d-(\d{4})-(\d{2})\.zip", name)
    if match is None:
        raise ContractError("invalid archive basename")
    year, month = int(match[2]), int(match[3])
    first = date(year, month, 1)
    expected = [(first + timedelta(days=d)).isoformat()
                for d in range(calendar.monthrange(year, month)[1])]
    if not payload or len(payload) > fetcher.MAX_ZIP:
        raise ContractError("archive outside size limit")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != name[:-4] + ".csv":
            raise ContractError("unexpected ZIP members")
        member = members[0]
        if (member.file_size > fetcher.MAX_ZIP or member.flag_bits & 1 or
                member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
            raise ContractError("unsupported ZIP member")
        content = archive.read(member).decode("utf-8")
    rows = list(csv.reader(io.StringIO(content)))
    if rows and tuple(rows[0]) in HEADERS:
        rows.pop(0)
    if len(rows) != len(expected):
        raise ContractError(f"incomplete month {name}")
    out = []
    divisor = 1000 if year >= 2025 else 1
    for row, day in zip(rows, expected):
        if len(row) != 12:
            raise ContractError("expected exactly twelve kline columns")
        if not re.fullmatch(r"\d+", row[0]) or not re.fullmatch(r"\d+", row[6]):
            raise ContractError("timestamp must be an integer")
        opening, closing = int(row[0]), int(row[6])
        expected_ms = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)
        if opening != expected_ms*divisor or closing//divisor != expected_ms+DAY_MS-1:
            raise ContractError(f"timestamp/calendar mismatch on {day}")
        try:
            values = np.asarray([float(x) for x in row], dtype=float)
        except ValueError as exc:
            raise ContractError("nonnumeric kline field") from exc
        if not np.isfinite(values).all():
            raise ContractError("nonfinite kline field")
        op, hi, lo, cl = values[1:5]
        if min(op, hi, lo, cl) <= 0 or hi < max(op, cl) or lo > min(op, cl) or hi < lo:
            raise ContractError("invalid OHLC")
        if min(values[5], values[7], values[8], values[9], values[10]) < 0 or values[8] != int(values[8]):
            raise ContractError("invalid volume/trade count")
        out.append((day, float(cl)))
    return out


def verify_registration(lane=LANE):
    spec = lane / "PREREG.md"
    spec_sha = prereg.verify(spec)
    source = spec.read_text()
    code_sha = sha(Path(__file__).read_bytes())
    fetcher_sha = sha(Path(fetcher.__file__).read_bytes())
    for label, actual in (("Runner", code_sha), ("Fetcher", fetcher_sha)):
        values = re.findall(rf"{label} SHA-256: `?([0-9a-f]{{64}})`?", source)
        if values != [actual]:
            raise ContractError(f"frozen specification does not bind this {label.lower()}")
    return spec_sha, code_sha, fetcher_sha


def load_prices(manifest_path, raw, lane=LANE):
    """Verify frozen spec, code, manifest lock and every archive before parsing prices."""
    spec_sha, code_sha, fetcher_sha = verify_registration(lane)
    locked = (lane / "DATA.sha256").read_text().strip()
    payload = fetcher.read_bounded(manifest_path, fetcher.MAX_TOTAL)
    if not re.fullmatch(r"[0-9a-f]{64}", locked) or sha(payload) != locked:
        raise ContractError("source manifest does not match DATA.sha256")
    manifest = fetcher.verify_manifest(manifest_path, raw, spec_sha, fetcher_sha)
    dates = date_range("2021-01-01", "2026-10-01")
    by_symbol = {symbol: [] for symbol in fetcher.SYMBOLS}
    for record in manifest["archives"]:
        content = fetcher.read_bounded(raw / record["path"], fetcher.MAX_ZIP)
        if sha(content) != record["sha256"]:
            raise ContractError("archive changed after manifest verification")
        symbol = record["path"].split("-", 1)[0]
        by_symbol[symbol].extend(parse_archive(content, record["path"]))
    columns = []
    for symbol in fetcher.SYMBOLS:
        records = by_symbol[symbol]
        if tuple(x[0] for x in records) != dates:
            raise ContractError(f"incomplete or duplicated fixed calendar for {symbol}")
        columns.append([x[1] for x in records])
    return dates, np.asarray(columns, dtype=float).T, {
        "prereg_sha256": spec_sha, "runner_sha256": code_sha,
        "fetcher_sha256": fetcher_sha, "data_manifest_sha256": locked,
        "source_archives": manifest["archives"], "source_created_utc": manifest["created_utc"]}


def component_positions(close, horizon):
    close = np.asarray(close, dtype=float)
    if close.ndim != 1 or not np.isfinite(close).all() or np.any(close <= 0) or horizon < 2:
        raise ContractError("invalid close series/horizon")
    positions = np.zeros(len(close), dtype=float)
    active, stop = False, np.nan
    for t in range(horizon-1, len(close)):
        window = close[t-horizon+1:t+1]
        upper, lower = float(window.max()), float(window.min())
        midpoint = (upper+lower)/2
        # Entry precedes exit. An already-long channel touch does not reset its stop.
        if close[t] == upper:
            if not active:
                active, stop = True, midpoint
            else:
                stop = max(stop, midpoint)
        elif active and close[t] <= stop:
            active, stop = False, np.nan
        elif active:
            stop = max(stop, midpoint)
        positions[t] = float(active)
    return positions


def trend_targets(close):
    close = np.asarray(close, dtype=float)
    if close.ndim != 2 or close.shape[1] != len(fetcher.SYMBOLS):
        raise ContractError("fixed six-coin close matrix required")
    signals = np.mean([np.column_stack([component_positions(close[:, j], h)
                        for j in range(close.shape[1])]) for h in HORIZONS], axis=0)
    returns = close[1:]/close[:-1]-1
    multiplier = np.zeros_like(close)
    for t in range(90, len(close)):
        vol = np.std(returns[t-90:t], axis=0, ddof=1)*np.sqrt(365)
        multiplier[t] = np.divide(0.25, vol, out=np.ones_like(vol), where=vol>0).clip(0, 1)
    return {"trend_plain": signals/6, "trend_vol": signals*multiplier/6}


def rebalance(units, cash, prices, weights, cost):
    """Solve post-cost weights against drifted units/cash, without borrowing."""
    units, prices, weights = (np.asarray(x, dtype=float) for x in (units, prices, weights))
    if (units.shape != prices.shape or weights.shape != prices.shape or
            not all(np.isfinite(x).all() for x in (units, prices, weights)) or
            np.any(units < -1e-14) or np.any(prices <= 0) or np.any(weights < 0) or
            weights.sum() > 1+1e-12 or not np.isfinite(cash) or cash < -1e-12 or not 0 <= cost < 1):
        raise ContractError("invalid long-only account/target")
    dollars = units*prices
    before = float(cash+dollars.sum())
    if before <= 0:
        raise ContractError("account NAV must be positive")
    lo, hi = 0.0, before
    for _ in range(70):
        after = (lo+hi)/2
        value = after+cost*np.abs(weights*after-dollars).sum()
        if value > before:
            hi = after
        else:
            lo = after
    after = (lo+hi)/2
    traded = float(np.abs(weights*after-dollars).sum())
    fee = cost*traded
    new_dollars = weights*after
    new_cash = float(after-new_dollars.sum())
    if new_cash < -1e-12*before or abs(after+fee-before) > 1e-11*before:
        raise ContractError("self-financing equation failed")
    return new_dollars/prices, max(0.0, new_cash), fee, traded


def simulate(close, dates, start, end, cost, targets=None, passive_scale=1.0):
    """Each row i trades at C[i-1]; a trend uses only target[i-2]."""
    close = np.asarray(close, dtype=float)
    if (close.ndim != 2 or len(dates) != len(close) or not np.isfinite(close).all() or
            np.any(close <= 0) or start < 2 or not start < end <= len(close)):
        raise ContractError("invalid simulation calendar/prices")
    if targets is not None and np.asarray(targets).shape != close.shape:
        raise ContractError("target shape mismatch")
    if not 0 <= passive_scale <= 1:
        raise ContractError("invalid passive scale")
    units, cash, previous = np.zeros(close.shape[1]), 1.0, 1.0
    records = []
    for i in range(start, end):
        prices = close[i-1]
        before = float(cash+units@prices)
        fee = traded = 0.0
        if targets is not None or i == start or dates[i][8:10] == "01":
            weights = targets[i-2] if targets is not None else np.full(close.shape[1], passive_scale/close.shape[1])
            units, cash, fee, traded = rebalance(units, cash, prices, weights, cost)
        held_units = units.copy()
        post_cost = float(cash+units@prices)
        exposure = float(units@prices/post_cost)
        gross = float(units@(close[i]-prices))
        nav = float(cash+units@close[i])
        if i == end-1:
            exit_turnover = float(units@close[i])
            exit_fee = cost*exit_turnover
            fee += exit_fee
            traded += exit_turnover
            cash, units = nav-exit_fee, np.zeros_like(units)
            nav = cash
        if nav <= 0 or cash < -1e-12:
            raise ContractError("negative cash or nonpositive NAV")
        net = nav/previous-1
        if abs(net-(gross-fee)/previous) > 1e-11:
            raise ContractError("daily accounting decomposition failed")
        records.append({"date": dates[i], "net": net, "gross": gross/previous,
                        "cost_fraction": fee/previous, "cost_dollars": fee,
                        "turnover": traded/before, "exposure": exposure, "nav": nav,
                        "cash_end": cash, "held_units": held_units.tolist()})
        previous = nav
    return records


def discovery_scale(trend_net, passive_net):
    a, b = (np.asarray(x, dtype=float) for x in (trend_net, passive_net))
    if len(a) < 2 or a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ContractError("invalid discovery risk sample")
    numerator, denominator = float(a.std(ddof=1)), float(b.std(ddof=1))
    if numerator <= 0 or denominator <= 0:
        raise ContractError("undefined discovery risk scale")
    return min(1.0, numerator/denominator)


def metrics(records):
    net = np.asarray([r["net"] for r in records])
    nav = np.r_[1.0, [r["nav"] for r in records]]
    sd = float(net.std(ddof=0))
    return {"days": len(net), "mean_bp_day": float(net.mean()*1e4),
            "annual_arithmetic": float(net.mean()*365),
            "annual_vol": sd*np.sqrt(365),
            "sharpe": float(net.mean()/sd*np.sqrt(365)) if sd > 0 else None,
            "nw10_t": float(stats.newey_west_t(net, 10)[2]),
            "max_drawdown": float(np.max(1-nav/np.maximum.accumulate(nav))),
            "total_cost_dollars": sum(r["cost_dollars"] for r in records),
            "turnover": sum(r["turnover"] for r in records),
            "mean_exposure": float(np.mean([r["exposure"] for r in records])),
            "ending_nav": float(nav[-1]), "coverage_fraction": 1.0}


def paired_bootstrap(differences, block, replicates=5000):
    x = np.asarray(differences, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all() or block < 1:
        raise ContractError("invalid bootstrap series")
    rng = np.random.default_rng(20261019229+block)
    count = (len(x)+block-1)//block
    values = np.empty(replicates)
    for offset in range(0, replicates, 250):
        size = min(250, replicates-offset)
        starts = rng.integers(0, len(x), size=(size, count))
        indices = ((starts[:, :, None]+np.arange(block)) % len(x)).reshape(size, -1)[:, :len(x)]
        values[offset:offset+size] = x[indices].mean(axis=1)
    low, high = np.quantile(values, [0.025, 0.975])
    return {"block_days": block, "replicates": replicates,
            "seed": 20261019229+block, "mean": float(x.mean()),
            "lower95": float(low), "upper95": float(high)}


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def write_json(path, value):
    with path.open("x") as handle:
        handle.write(json.dumps(clean_json(value), indent=2, sort_keys=True, allow_nan=False)+"\n")


def verify_fresh_output(output):
    """A source manifest may preexist; research outputs are never overwritten."""
    if output.is_symlink():
        raise ContractError("output directory must not be a symlink")
    if output.exists():
        if not output.is_dir():
            raise ContractError("output path is not a directory")
        for child in output.iterdir():
            if child.name != "data_manifest.json" or not child.is_file() or child.is_symlink():
                raise ContractError(f"output is not fresh; use --out with a new directory: {child}")


def run(manifest_path, raw, lane=LANE, output=None):
    output = lane / "results" if output is None else Path(output)
    verify_fresh_output(output)
    dates, close, provenance = load_prices(manifest_path, raw, lane)
    targets = trend_targets(close)
    bounds = {key: (dates.index(a), len(dates) if b == "2026-10-01" else dates.index(b))
              for key, (a, b) in SPLITS.items()}
    a, b = bounds["discovery"]
    primary = simulate(close, dates, a, b, .0012, targets["trend_vol"])
    passive = simulate(close, dates, a, b, .0012)
    k = discovery_scale([r["net"] for r in primary], [r["net"] for r in passive])
    all_rows, all_metrics, accounts = [], [], {}
    for split, (a, b) in bounds.items():
        for tier in (1, 2, 3):
            for strategy in ("trend_vol", "trend_plain", "passive", "passive_matched"):
                rows = simulate(close, dates, a, b, .0012*tier, targets.get(strategy),
                                k if strategy == "passive_matched" else 1.0)
                accounts[split, tier, strategy] = rows
                all_rows.extend({"split": split, "cost_multiple": tier, "strategy": strategy, **r} for r in rows)
                all_metrics.append({"split": split, "cost_multiple": tier, "strategy": strategy, **metrics(rows)})
    lookup = {(r["split"], r["cost_multiple"], r["strategy"]): r for r in all_metrics}
    validation = lookup["validation", 1, "trend_vol"]
    matched = lookup["validation", 1, "passive_matched"]
    if validation["sharpe"] is None or matched["sharpe"] is None:
        raise ContractError("undefined validation Sharpe")
    differences, paired_rows = {}, []
    for split in bounds:
        for tier in (1, 2, 3):
            left, right = (accounts[split, tier, name] for name in ("trend_vol", "passive_matched"))
            differences[split, tier] = np.asarray([x["net"]-y["net"] for x, y in zip(left, right)])
            paired_rows.extend({"date": x["date"], "split": split, "cost_multiple": tier,
                                "net_difference": float(d)} for x, d in zip(left, differences[split, tier]))
    bootstrap = [paired_bootstrap(differences["validation", 1], block) for block in (30, 10, 60)]
    checks = {"sharpe_improvement_at_least_015": validation["sharpe"] >= matched["sharpe"]+.15,
              "positive_2x_mean": lookup["validation", 2, "trend_vol"]["mean_bp_day"] > 0,
              "drawdown_no_worse": validation["max_drawdown"] <= matched["max_drawdown"],
              "paired_mean_lower95_positive": bootstrap[0]["lower95"] > 0}
    verdict = {"verdict": "PARTIAL" if all(checks.values()) else "NULL",
               "evidence": "exploratory, selected surviving-coin spot adaptation",
               "trials": 2, "discovery_risk_scale": k, "checks": checks,
               "validation_bootstrap": bootstrap}
    provenance.update({"python": platform.python_version(), "numpy": np.__version__,
                       "symbols": list(fetcher.SYMBOLS), "calendar_rows_per_coin": len(dates),
                       "splits": SPLITS, "cost_one_way": [.0012, .0024, .0036],
                       "discovery_risk_scale": k,
                       "risk_realized": [{"split": split,
                           "trend_vol": lookup[split, 1, "trend_vol"]["annual_vol"],
                           "matched_passive": lookup[split, 1, "passive_matched"]["annual_vol"]}
                           for split in bounds]})
    output.mkdir(parents=True, exist_ok=True)
    daily_fields = ["split", "cost_multiple", "strategy", "date", "net", "gross", "cost_fraction",
                    "cost_dollars", "turnover", "exposure", "nav", "cash_end"]
    with (output / "daily.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=daily_fields+["units_"+s for s in fetcher.SYMBOLS],
                                lineterminator="\n")
        writer.writeheader()
        for record in all_rows:
            row = {key: record[key] for key in daily_fields}
            row.update(zip(("units_"+s for s in fetcher.SYMBOLS), record["held_units"]))
            writer.writerow(row)
    for filename, records in (("metrics.csv", all_metrics), ("paired_differences.csv", paired_rows)):
        with (output / filename).open("x", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
    write_json(output / "verdict.json", verdict)
    provenance["output_sha256"] = {name: sha((output / name).read_bytes())
        for name in ("daily.csv", "metrics.csv", "paired_differences.csv", "verdict.json")}
    write_json(output / "run_manifest.json", provenance)
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=fetcher.DEFAULT_RAW)
    parser.add_argument("--manifest", type=Path, default=LANE / "results/data_manifest.json")
    parser.add_argument("--out", type=Path, default=LANE / "results",
                        help="Fresh output directory; default permits only the fetched data manifest")
    args = parser.parse_args()
    # Registration errors stop without fabricating a result for an unfrozen lane.
    verify_registration()
    # This must remain outside the exception that writes an INCONCLUSIVE verdict.
    verify_fresh_output(args.out)
    try:
        result = run(args.manifest, args.raw_dir, output=args.out)
    except (ContractError, ValueError, OSError, zipfile.BadZipFile) as exc:
        result = {"verdict": "INCONCLUSIVE", "reason": str(exc)}
        args.out.mkdir(parents=True, exist_ok=True)
        write_json(args.out / "verdict.json", result)
    print(json.dumps(clean_json(result), sort_keys=True))


if __name__ == "__main__":
    main()
