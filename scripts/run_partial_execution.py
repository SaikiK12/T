#!/usr/bin/env python3
"""R231: pre-registered partial adjustment of the unchanged R229 spot target."""
from __future__ import annotations

import argparse
import csv
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
from lab import prereg  # noqa: E402
from scripts import run_slow_trend as base  # noqa: E402

LANE = ROOT / "experiments/partial_execution_v1"
FRACTIONS = {"full": 1.0, "half": 0.5, "quarter": 0.25}
ContractError = base.ContractError


def verify_registration(lane=LANE):
    digest = prereg.verify(lane / "PREREG.md")
    source = (lane / "PREREG.md").read_text()
    dependencies = {
        "Runner": Path(__file__),
        "R229 runner": Path(base.__file__),
        "R229 fetcher": Path(base.fetcher.__file__),
        "R229 specification": base.LANE / "PREREG.md",
        "Statistics": ROOT / "lab/stats.py",
        "Preregistration helper": ROOT / "lab/prereg.py",
        "R229 data manifest": base.LANE / "results/data_manifest.json",
        "R229 data lock": base.LANE / "DATA.sha256",
        "R229 archived daily": base.LANE / "results/daily.csv",
    }
    hashes = {}
    for label, path in dependencies.items():
        actual = base.sha(path.read_bytes())
        matches = re.findall(rf"^{re.escape(label)} SHA-256: ([0-9a-f]{{64}})$", source, re.M)
        if matches != [actual]:
            raise ContractError(f"frozen dependency mismatch: {label}")
        hashes[label] = actual
    base.verify_registration()
    return {"prereg_sha256": digest, "dependency_sha256": hashes}


def adjusted_weights(units, cash, prices, target, fraction, scale=1.0):
    """Convexly mix current drifted PRE-COST weights and an unchanged delayed target."""
    units, prices, target = (np.asarray(x, dtype=float) for x in (units, prices, target))
    if (units.shape != prices.shape or target.shape != prices.shape or
            not all(np.isfinite(x).all() for x in (units, prices, target)) or
            np.any(units < 0) or np.any(prices <= 0) or np.any(target < 0) or
            target.sum() > 1+1e-12 or not np.isfinite(cash) or cash < -1e-12 or
            not np.isfinite(fraction) or not 0 <= fraction <= 1 or
            not np.isfinite(scale) or not 0 <= scale <= 1):
        raise ContractError("invalid partial-adjustment account/target")
    nav = float(cash+units@prices)
    if nav <= 0:
        raise ContractError("nonpositive pre-trade NAV")
    drifted = units*prices/nav
    return (1-fraction)*drifted+fraction*scale*target


def simulate(close, dates, start, end, cost, targets, fraction=1.0, scale=1.0):
    close, targets = np.asarray(close, dtype=float), np.asarray(targets, dtype=float)
    if (close.ndim != 2 or targets.shape != close.shape or len(dates) != len(close) or
            not np.isfinite(close).all() or np.any(close <= 0) or
            start < 2 or not start < end <= len(close)):
        raise ContractError("invalid simulation calendar/prices/target shape")
    units, cash, previous = np.zeros(close.shape[1]), 1.0, 1.0
    rows = []
    for i in range(start, end):
        prices = close[i-1]
        before = float(cash+units@prices)
        drifted = units*prices/before
        delayed = targets[i-2]
        weights = adjusted_weights(units, cash, prices, delayed, fraction, scale)
        units, cash, fee, traded = base.rebalance(units, cash, prices, weights, cost)
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
            raise ContractError("daily gross-cost-net identity failed")
        rows.append({"date": dates[i], "net": net, "gross": gross/previous,
                     "cost_fraction": fee/previous, "cost_dollars": fee,
                     "turnover": traded/before, "exposure": exposure, "nav": nav,
                     "cash_end": cash, "held_units": held_units.tolist(),
                     "drifted_weights": drifted.tolist(),
                     "delayed_target": delayed.tolist(), "executed_weights": weights.tolist()})
        previous = nav
    return rows


def metrics(rows):
    result = base.metrics(rows)
    result.update({"mean_gross_bp_day": float(np.mean([r["gross"] for r in rows])*1e4),
                   "mean_cost_bp_day": float(np.mean([r["cost_fraction"] for r in rows])*1e4)})
    return result


def select_fraction(discovery):
    """Only the two new candidates compete; exact Sharpe ties favor the larger step."""
    candidates = []
    for name in ("half", "quarter"):
        score = metrics(discovery[name])["sharpe"]
        if score is None or not np.isfinite(score):
            raise ContractError("undefined discovery candidate Sharpe")
        candidates.append((score, FRACTIONS[name], name))
    return max(candidates)[2]


def paired_bootstrap(difference, block, replicates=5000):
    x = np.asarray(difference, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all() or block < 1:
        raise ContractError("invalid paired bootstrap input")
    rng = np.random.default_rng(20261020231+block)
    count = (len(x)+block-1)//block
    means = np.empty(replicates)
    for offset in range(0, replicates, 250):
        size = min(250, replicates-offset)
        starts = rng.integers(0, len(x), size=(size, count))
        indices = ((starts[:, :, None]+np.arange(block)) % len(x)).reshape(size, -1)[:, :len(x)]
        means[offset:offset+size] = x[indices].mean(axis=1)
    lower, upper = np.quantile(means, [.025, .975])
    return {"block_days": block, "replicates": replicates, "seed": 20261020231+block,
            "mean": float(x.mean()), "lower95": float(lower), "upper95": float(upper)}


def fresh_output(output):
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ContractError("research output must be a fresh empty directory")


def verify_archived_control(accounts, path):
    """Every full-adjustment day must reproduce the frozen R229 trend_vol result."""
    maximum, count = 0.0, 0
    with path.open() as handle:
        for old in csv.DictReader(handle):
            if old["strategy"] != "trend_vol":
                continue
            key = (old["split"], int(old["cost_multiple"]), old["date"])
            if key not in accounts:
                raise ContractError("archived control calendar mismatch")
            row = accounts[key]
            for field in ("net", "gross", "cost_fraction", "cost_dollars", "turnover", "exposure", "nav", "cash_end"):
                maximum = max(maximum, abs(row[field]-float(old[field])))
            for j, symbol in enumerate(base.fetcher.SYMBOLS):
                maximum = max(maximum, abs(row["held_units"][j]-float(old["units_"+symbol])))
            count += 1
    if count != len(accounts) or maximum > 1e-11:
        raise ContractError("full-adjustment control differs from frozen R229")
    return {"checked_daily_rows": count, "maximum_absolute_discrepancy": maximum}


def write_csv(path, rows):
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(raw, output, lane=LANE):
    output = Path(output)
    fresh_output(output)
    registration = verify_registration(lane)
    dates, close, source = base.load_prices(base.LANE / "results/data_manifest.json", raw)
    target = base.trend_targets(close)["trend_vol"]
    bounds = {key: (dates.index(a), len(dates) if b == "2026-10-01" else dates.index(b))
              for key, (a, b) in base.SPLITS.items()}
    a, b = bounds["discovery"]
    discovery_2x = {name: simulate(close, dates, a, b, .0024, target, fraction)
                    for name, fraction in FRACTIONS.items()}
    selected = select_fraction(discovery_2x)
    discovery_1x = {name: simulate(close, dates, a, b, .0012, target, FRACTIONS[name])
                    for name in ("full", selected)}
    k = base.discovery_scale([r["net"] for r in discovery_1x[selected]],
                             [r["net"] for r in discovery_1x["full"]])
    accounts, summary, daily = {}, [], []
    for split, (a, b) in bounds.items():
        for tier in (1, 2, 3):
            for name in ("full", "half", "quarter", "full_matched"):
                fraction = FRACTIONS.get(name, 1.0)
                scale = k if name == "full_matched" else 1.0
                rows = simulate(close, dates, a, b, .0012*tier, target, fraction, scale)
                accounts[split, tier, name] = rows
                summary.append({"split": split, "cost_multiple": tier, "policy": name,
                                "fraction": fraction, "target_scale": scale, **metrics(rows)})
                for row in rows:
                    item = {"split": split, "cost_multiple": tier, "policy": name,
                            **{key: value for key, value in row.items() if not isinstance(value, list)}}
                    for key in ("held_units", "drifted_weights", "delayed_target", "executed_weights"):
                        item.update({key+"_"+symbol: value
                                     for symbol, value in zip(base.fetcher.SYMBOLS, row[key])})
                    daily.append(item)
    control_rows = {(split, tier, row["date"]): row for (split, tier, name), rows in accounts.items()
                    if name == "full" for row in rows}
    reproduction = verify_archived_control(control_rows, base.LANE / "results/daily.csv")
    paired, decompositions = [], []
    for split in bounds:
        for tier in (1, 2, 3):
            for name in ("half", "quarter"):
                for control in ("full", "full_matched"):
                    for x, y in zip(accounts[split, tier, name], accounts[split, tier, control]):
                        delta_net = x["net"]-y["net"]
                        gross_delta = x["gross"]-y["gross"]
                        cost_saving = y["cost_fraction"]-x["cost_fraction"]
                        if abs(delta_net-gross_delta-cost_saving) > 3e-11:
                            raise ContractError("paired gross-cost decomposition failed")
                        paired.append({"split": split, "cost_multiple": tier, "policy": name,
                                       "control": control, "date": x["date"],
                                       "net_difference": delta_net, "gross_difference": gross_delta,
                                       "cost_saving": cost_saving, "foregone_gross": -gross_delta})
                    sample = [r for r in paired if r["split"] == split and r["cost_multiple"] == tier
                              and r["policy"] == name and r["control"] == control]
                    decompositions.append({"split": split, "cost_multiple": tier, "policy": name,
                                           "control": control,
                                           **{key+"_bp_day": float(np.mean([r[key] for r in sample])*1e4)
                                              for key in ("net_difference", "gross_difference", "cost_saving", "foregone_gross")}})
    lookup = {(r["split"], r["cost_multiple"], r["policy"]): r for r in summary}
    primary, control = (lookup["validation", 1, name] for name in (selected, "full_matched"))
    if primary["sharpe"] is None or control["sharpe"] is None:
        raise ContractError("undefined validation Sharpe")
    differences = [r["net_difference"] for r in paired if r["split"] == "validation"
                   and r["cost_multiple"] == 1 and r["policy"] == selected and r["control"] == "full_matched"]
    bootstrap = [paired_bootstrap(differences, block) for block in (30, 10, 60)]
    checks = {"sharpe_improvement_at_least_015": primary["sharpe"] >= control["sharpe"]+.15,
              "positive_2x_mean": lookup["validation", 2, selected]["mean_bp_day"] > 0,
              "drawdown_no_worse": primary["max_drawdown"] <= control["max_drawdown"],
              "paired_mean_lower95_positive": bootstrap[0]["lower95"] > 0}
    verdict = {"verdict": "PARTIAL" if all(checks.values()) else "NULL", "trials": 2,
               "selected_policy": selected, "selected_fraction": FRACTIONS[selected],
               "discovery_risk_scale": k,
               "evidence": "exploratory historical reuse; selected six-surviving-coin spot adaptation",
               "checks": checks, "validation_bootstrap": bootstrap,
               "archived_control_reproduction": reproduction}
    manifest = {**registration, "source": source, "python": platform.python_version(),
                "numpy": np.__version__, "selection_split": "discovery", "selection_cost_multiple": 2,
                "discovery_2x_sharpe": {name: metrics(discovery_2x[name])["sharpe"] for name in FRACTIONS},
                "selected_policy": selected, "discovery_risk_scale": k,
                "archived_control_reproduction": reproduction, "split_dates": base.SPLITS,
                "cost_one_way": [.0012, .0024, .0036]}
    output.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("daily.csv", daily), ("metrics.csv", summary),
                           ("paired_differences.csv", paired), ("decomposition.csv", decompositions)):
        write_csv(output / filename, rows)
    base.write_json(output / "verdict.json", verdict)
    manifest["output_sha256"] = {name: base.sha((output/name).read_bytes()) for name in
        ("daily.csv", "metrics.csv", "paired_differences.csv", "decomposition.csv", "verdict.json")}
    base.write_json(output / "run_manifest.json", manifest)
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=base.fetcher.DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=LANE / "results")
    args = parser.parse_args()
    verify_registration()
    fresh_output(args.out)
    try:
        result = run(args.raw_dir, args.out)
    except (ContractError, ValueError, OSError, zipfile.BadZipFile) as exc:
        result = {"verdict": "INCONCLUSIVE", "reason": str(exc)}
        args.out.mkdir(parents=True, exist_ok=True)
        base.write_json(args.out / "verdict.json", result)
    print(json.dumps(base.clean_json(result), sort_keys=True))


if __name__ == "__main__":
    main()
