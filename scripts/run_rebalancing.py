#!/usr/bin/env python3
"""R232: fixed equal-weight rebalance cadences versus unchanged buy-and-hold units."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import gzip
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
from lab import prereg  # noqa: E402
from scripts import run_slow_trend as base  # noqa: E402

LANE = ROOT / "experiments/rebalancing_v1"
CADENCES = ("daily", "weekly", "monthly")
ContractError = base.ContractError


def verify_registration(lane=LANE):
    digest = prereg.verify(lane / "PREREG.md")
    spec = (lane / "PREREG.md").read_text()
    paths = {"Runner": Path(__file__), "R229 runner": Path(base.__file__),
             "R229 fetcher": Path(base.fetcher.__file__), "Statistics": ROOT / "lab/stats.py",
             "Preregistration helper": ROOT / "lab/prereg.py",
             "R229 specification": base.LANE / "PREREG.md",
             "R229 data manifest": base.LANE / "results/data_manifest.json",
             "R229 data lock": base.LANE / "DATA.sha256",
             "R229 archived daily": base.LANE / "results/daily.csv"}
    hashes = {}
    for label, path in paths.items():
        digest_actual = base.sha(path.read_bytes())
        declared = re.findall(rf"^{re.escape(label)} SHA-256: ([0-9a-f]{{64}})$", spec, re.M)
        if declared != [digest_actual]:
            raise ContractError(f"frozen dependency mismatch: {label}")
        hashes[label] = digest_actual
    base.verify_registration()
    return {"prereg_sha256": digest, "dependency_sha256": hashes}


def scheduled(day, cadence):
    if cadence not in (*CADENCES, "buyhold"):
        raise ContractError("unregistered rebalance cadence")
    current = date.fromisoformat(day)
    return (cadence == "daily" or cadence == "weekly" and current.weekday() == 0
            or cadence == "monthly" and current.day == 1)


def simulate(close, dates, start, end, cost, cadence, scale=1.0):
    close = np.asarray(close, dtype=float)
    if (close.ndim != 2 or close.shape[1] != 6 or len(dates) != len(close) or
            not np.isfinite(close).all() or np.any(close <= 0) or
            not 2 <= start < end <= len(close) or cadence not in (*CADENCES, "buyhold") or
            not np.isfinite(scale) or not 0 <= scale <= 1 or not 0 <= cost < 1):
        raise ContractError("invalid fixed-universe cash account contract")
    units, cash, previous = np.zeros(6), 1.0, 1.0
    rows = []
    for i in range(start, end):
        prices = close[i-1]
        before = float(cash+units@prices)
        fee = traded = 0.
        rebalance = i == start or scheduled(dates[i], cadence)
        if rebalance:
            units, cash, fee, traded = base.rebalance(units, cash, prices, np.full(6, scale/6), cost)
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
            cash, units = nav-exit_fee, np.zeros(6)
            nav = cash
        if nav <= 0 or cash < -1e-12:
            raise ContractError("negative cash/nonpositive NAV")
        net = nav/previous-1
        if abs(net-(gross-fee)/previous) > 1e-11:
            raise ContractError("gross-cost-net identity failed")
        rows.append({"date": dates[i], "rebalance": rebalance, "net": net,
                     "gross": gross/previous, "cost_fraction": fee/previous,
                     "cost_dollars": fee, "turnover": traded/before, "exposure": exposure,
                     "nav": nav, "cash_end": cash, "held_units": held_units.tolist()})
        previous = nav
    return rows


def metrics(rows):
    return {**base.metrics(rows),
            "mean_gross_bp_day": float(np.mean([r["gross"] for r in rows])*1e4),
            "mean_cost_bp_day": float(np.mean([r["cost_fraction"] for r in rows])*1e4),
            "rebalance_count": sum(r["rebalance"] for r in rows)}


def select_cadence(accounts):
    candidates = []
    for priority, name in enumerate(CADENCES):
        value = metrics(accounts[name])["sharpe"]
        if value is None or not np.isfinite(value):
            raise ContractError("undefined discovery candidate Sharpe")
        candidates.append((value, priority, name))
    return max(candidates)[2]  # Exact ties: monthly, then weekly, then daily.


def symmetric_scales(winner, control):
    a, b = (np.asarray(x, dtype=float) for x in (winner, control))
    if (a.ndim != 1 or len(a) < 2 or a.shape != b.shape or
            not np.isfinite(a).all() or not np.isfinite(b).all()):
        raise ContractError("invalid discovery risk sample")
    left, right = a.std(ddof=1), b.std(ddof=1)
    if min(left, right) <= 0:
        raise ContractError("undefined discovery risk scale")
    return min(1., float(right/left)), min(1., float(left/right))


def paired_bootstrap(differences, block, replicates=5000):
    x = np.asarray(differences, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all() or block < 1:
        raise ContractError("invalid paired bootstrap input")
    seed = 20261020232+block
    rng = np.random.default_rng(seed)
    count = (len(x)+block-1)//block
    means = np.empty(replicates)
    for offset in range(0, replicates, 250):
        size = min(250, replicates-offset)
        starts = rng.integers(0, len(x), size=(size, count))
        indices = ((starts[:, :, None]+np.arange(block)) % len(x)).reshape(size, -1)[:, :len(x)]
        means[offset:offset+size] = x[indices].mean(axis=1)
    lower, upper = np.quantile(means, [.025, .975])
    return {"block_days": block, "replicates": replicates, "seed": seed,
            "mean": float(x.mean()), "lower95": float(lower), "upper95": float(upper)}


def fresh_output(output):
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ContractError("research output must be a fresh empty directory")


def write_csv(path, rows):
    if path.suffix == ".gz":
        # Empty gzip filename and zero mtime bind results to content, not host path/time.
        with path.open("xb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
                    writer.writeheader()
                    writer.writerows(rows)
    else:
        with path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def verify_monthly(accounts):
    rows_by_key = {(split, tier, row["date"]): row for (split, tier, name), rows in accounts.items()
                   if name == "monthly" for row in rows}
    count, maximum = 0, 0.
    with (base.LANE / "results/daily.csv").open() as handle:
        for old in csv.DictReader(handle):
            if old["strategy"] != "passive":
                continue
            row = rows_by_key.get((old["split"], int(old["cost_multiple"]), old["date"]))
            if row is None:
                raise ContractError("R229 monthly comparator calendar mismatch")
            for key in ("net", "gross", "cost_fraction", "cost_dollars", "turnover", "exposure", "nav", "cash_end"):
                maximum = max(maximum, abs(row[key]-float(old[key])))
            for j, symbol in enumerate(base.fetcher.SYMBOLS):
                maximum = max(maximum, abs(row["held_units"][j]-float(old["units_"+symbol])))
            count += 1
    if count != len(rows_by_key) or maximum > 1e-11:
        raise ContractError("monthly control differs from frozen R229 passive")
    return {"daily_rows": count, "maximum_absolute_discrepancy": maximum}


def run(raw, output, lane=LANE):
    output = Path(output)
    fresh_output(output)
    registration = verify_registration(lane)
    dates, close, source = base.load_prices(base.LANE / "results/data_manifest.json", raw)
    bounds = {name: (dates.index(a), len(dates) if b == "2026-10-01" else dates.index(b))
              for name, (a, b) in base.SPLITS.items()}
    a, b = bounds["discovery"]
    discovery2 = {name: simulate(close, dates, a, b, .0024, name) for name in CADENCES}
    selected = select_cadence(discovery2)
    discovery1 = {name: simulate(close, dates, a, b, .0012, name) for name in (selected, "buyhold")}
    scale_winner, scale_control = symmetric_scales([r["net"] for r in discovery1[selected]],
                                                  [r["net"] for r in discovery1["buyhold"]])
    policies = {**{name: (name, 1.) for name in (*CADENCES, "buyhold")},
                "selected_matched": (selected, scale_winner), "buyhold_matched": ("buyhold", scale_control)}
    accounts, summary, daily = {}, [], []
    for split, (a, b) in bounds.items():
        for tier in (1, 2, 3):
            for policy, (cadence, scale) in policies.items():
                rows = simulate(close, dates, a, b, .0012*tier, cadence, scale)
                accounts[split, tier, policy] = rows
                summary.append({"split": split, "cost_multiple": tier, "policy": policy,
                                "cadence": cadence, "capital_scale": scale, **metrics(rows)})
                for row in rows:
                    flat = {"split": split, "cost_multiple": tier, "policy": policy,
                            **{key: value for key, value in row.items() if key != "held_units"}}
                    flat.update({"units_"+symbol: value for symbol, value in zip(base.fetcher.SYMBOLS, row["held_units"])})
                    daily.append(flat)
    reproduced = verify_monthly(accounts)
    paired, decomposition = [], []
    for split in bounds:
        for tier in (1, 2, 3):
            comparisons = [(name, "buyhold") for name in CADENCES]+[("selected_matched", "buyhold_matched")]
            for policy, control in comparisons:
                sample = []
                for x, y in zip(accounts[split, tier, policy], accounts[split, tier, control]):
                    net = x["net"]-y["net"]
                    gross = x["gross"]-y["gross"]
                    extra_cost = x["cost_fraction"]-y["cost_fraction"]
                    if abs(net-gross+extra_cost) > 3e-11:
                        raise ContractError("paired decomposition failed")
                    sample.append({"split": split, "cost_multiple": tier, "policy": policy,
                                   "control": control, "date": x["date"], "net_difference": net,
                                   "gross_difference": gross, "extra_cost": extra_cost})
                paired.extend(sample)
                decomposition.append({"split": split, "cost_multiple": tier, "policy": policy,
                                      "control": control, **{key+"_bp_day": float(np.mean([r[key] for r in sample])*1e4)
                                      for key in ("net_difference", "gross_difference", "extra_cost")}})
    lookup = {(r["split"], r["cost_multiple"], r["policy"]): r for r in summary}
    primary, control = (lookup["validation", 1, name] for name in ("selected_matched", "buyhold_matched"))
    if primary["sharpe"] is None or control["sharpe"] is None:
        raise ContractError("undefined validation Sharpe")
    difference = [r["net_difference"] for r in paired if r["split"] == "validation"
                  and r["cost_multiple"] == 1 and r["policy"] == "selected_matched"]
    bootstrap = [paired_bootstrap(difference, block) for block in (30, 10, 60)]
    checks = {"sharpe_improvement_at_least_015": primary["sharpe"] >= control["sharpe"]+.15,
              "positive_2x_mean": lookup["validation", 2, "selected_matched"]["mean_bp_day"] > 0,
              "drawdown_no_worse": primary["max_drawdown"] <= control["max_drawdown"],
              "paired_mean_lower95_positive": bootstrap[0]["lower95"] > 0}
    verdict = {"verdict": "PARTIAL" if all(checks.values()) else "NULL", "trials": 3,
               "selected_cadence": selected, "discovery_winner_scale": scale_winner,
               "discovery_buyhold_scale": scale_control, "checks": checks,
               "validation_bootstrap": bootstrap, "monthly_r229_reproduction": reproduced,
               "evidence": "exploratory historical reuse; fixed six surviving spot coins; no hedge"}
    manifest = {**registration, "source": source, "python": platform.python_version(), "numpy": np.__version__,
                "discovery_2x_sharpe": {name: metrics(rows)["sharpe"] for name, rows in discovery2.items()},
                "selected_cadence": selected, "winner_scale": scale_winner, "buyhold_scale": scale_control,
                "split_dates": base.SPLITS, "cost_one_way": [.0012, .0024, .0036],
                "monthly_r229_reproduction": reproduced, "policies": policies}
    output.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("daily.csv.gz", daily), ("metrics.csv", summary),
                           ("paired_differences.csv.gz", paired), ("decomposition.csv", decomposition)):
        write_csv(output / filename, rows)
    base.write_json(output / "verdict.json", verdict)
    manifest["output_sha256"] = {name: base.sha((output/name).read_bytes()) for name in
        ("daily.csv.gz", "metrics.csv", "paired_differences.csv.gz", "decomposition.csv", "verdict.json")}
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
