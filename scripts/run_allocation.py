"""R228: a frozen, descriptive allocation diagnostic on previously seen books.

Importing this module never reads project outcomes. The executable verifies its
preregistration, its own source hash, and all source hashes before loading data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import sys
from dataclasses import dataclass

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import prereg, stats  # noqa: E402

SOURCES = ("A_C0", "B_C0", "X2")
WINDOWS = {"discovery": (0, 1095), "validation": (1095, 1642), "holdout": (1642, 2099)}
N_DAYS = 2099
TOL_BP = 1e-6
REPLICATES = 5000
BLOCKS = (30, 10, 60)
BOOT_SEED = 20261019228
NA = "NA"


class ContractError(ValueError):
    """Frozen inputs or the declared calculation are unavailable/inconsistent."""


@dataclass(frozen=True)
class Candidate:
    identifier: str
    weights: tuple[float, float, float]

    @property
    def interior(self):
        return sum(w > 0 for w in self.weights) == 2


def candidates():
    """Three endpoints plus nine interior weights for each unordered pair."""
    out = []
    for j, name in enumerate(SOURCES):
        w = [0.0] * 3
        w[j] = 1.0
        out.append(Candidate(f"{len(out):02d}_{name}", tuple(w)))
    for j in range(3):
        for k in range(j + 1, 3):
            for tenth in range(1, 10):
                w = [0.0] * 3
                w[j], w[k] = tenth / 10.0, (10 - tenth) / 10.0
                out.append(Candidate(f"{len(out):02d}_{SOURCES[j]}__{SOURCES[k]}__w{tenth:02d}", tuple(w)))
    assert len(out) == 30
    return tuple(out)


def sha256(path):
    h = hashlib.sha256()
    try:
        with Path(path).open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
    except OSError as exc:
        raise ContractError(f"Missing/unreadable input: {path}") from exc
    return h.hexdigest()


def verify_guards(root, runner_path=None):
    """Verify frozen specs/self/input bytes before parsing any outcome value."""
    root = Path(root)
    lane_spec = root / "experiments/allocation_v1/PREREG.md"
    spec_hash = prereg.verify(lane_spec)
    text = lane_spec.read_text()
    runner = Path(runner_path) if runner_path else Path(__file__).resolve()
    found = re.search(r"Runner SHA-256:\s*`([a-f0-9]{64})`", text)
    actual_runner = sha256(runner)
    if found is None or actual_runner != found.group(1):
        raise ContractError("Runner hash absent or different from frozen specification")
    old_spec = root / "experiments/sizing_v1/PREREG.md"
    old_hash = prereg.verify(old_spec)
    declarations = (
        ("Archive SHA-256", "experiments/sizing_v1/results/daily.npz"),
        ("Summary `experiments/sizing_v1/results/results.csv` SHA-256", "experiments/sizing_v1/results/results.csv"),
        ("Source `scripts/run_sizing.py` SHA-256", "scripts/run_sizing.py"),
    )
    hashes = {}
    for label, relative in declarations:
        match = re.search(re.escape(label) + r":\s*`([a-f0-9]{64})`", text)
        actual = sha256(root / relative)
        if match is None or actual != match.group(1):
            raise ContractError(f"Source hash mismatch or missing declaration: {relative}")
        hashes[relative] = actual
    return {
        "spec_sha256": spec_hash,
        "source_prereg_sha256": old_hash,
        "runner_sha256": actual_runner,
        "inputs_sha256": hashes,
        "support_code_sha256": {f"lab/{name}.py": sha256(root / f"lab/{name}.py") for name in ("stats", "prereg")},
        "software": {"python": platform.python_version(), "numpy": np.__version__,
                     "platform": platform.platform(), "byteorder": sys.byteorder},
        "dates": {"first": "2021-01-01", "last": "2026-09-30", "source": "reconstructed from frozen source"},
        "windows": WINDOWS,
        "bootstrap": {"replicates": REPLICATES, "blocks": BLOCKS, "seed": "20261019228 + block_length",
                      "method": "paired circular moving-block, ordinary percentile"},
        "trials": 30,
        "claims": "exploratory spent-sample diagnostic; no fresh holdout or execution claim",
    }


def read_inputs(root):
    """Called only after verify_guards; load and check the fixed data contract."""
    root = Path(root)
    archive = root / "experiments/sizing_v1/results/daily.npz"
    summary_file = root / "experiments/sizing_v1/results/results.csv"
    try:
        with np.load(archive, allow_pickle=False) as z:
            arrays = {}
            for name in SOURCES:
                if name not in z.files:
                    raise ContractError(f"Missing archive source: {name}")
                raw = z[name]
                if raw.shape != (N_DAYS,) or raw.dtype.kind not in "fi":
                    raise ContractError(f"Invalid source shape/dtype: {name}")
                arrays[name] = np.array(raw, dtype=float, copy=True)
        summaries = {}
        with summary_file.open(newline="") as f:
            for row in csv.DictReader(f):
                if row.get("run") not in SOURCES or row.get("window") not in WINDOWS:
                    continue
                cm = float(row["cmult"])
                if cm not in (1.0, 2.0, 3.0):
                    continue
                key = (row["run"], row["window"], int(cm))
                if key in summaries:
                    raise ContractError(f"Duplicate summary row: {key}")
                summaries[key] = {"days": int(row["days"]), "mean_bp_day": float(row["mean_bp_day"]),
                                  "gross_exposure": float(row["gross_exposure"])}
    except ContractError:
        raise
    except (OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        raise ContractError(f"Cannot load declared inputs: {exc}") from exc
    validate_inputs(arrays, summaries)
    return arrays, summaries


def validate_inputs(arrays, summaries):
    for name in SOURCES:
        if name not in arrays:
            raise ContractError(f"Missing source: {name}")
        x = np.asarray(arrays[name])
        if x.shape != (N_DAYS,) or not np.isfinite(x).all():
            raise ContractError(f"Wrong length or non-finite source: {name}")
        for window, (a, b) in WINDOWS.items():
            rows = []
            for cm in (1, 2, 3):
                key = (name, window, cm)
                if key not in summaries:
                    raise ContractError(f"Missing summary: {key}")
                row = summaries[key]
                if row["days"] != b - a or not np.isfinite([row["mean_bp_day"], row["gross_exposure"]]).all():
                    raise ContractError(f"Invalid summary count/value: {key}")
                if row["gross_exposure"] < 0:
                    raise ContractError(f"Negative exposure: {key}")
                rows.append(row)
            if abs(float(x[a:b].mean()) * 1e4 - rows[0]["mean_bp_day"]) > TOL_BP:
                raise ContractError(f"1x daily/summary mean mismatch: {name}/{window}")
            cost12 = rows[0]["mean_bp_day"] - rows[1]["mean_bp_day"]
            cost23 = rows[1]["mean_bp_day"] - rows[2]["mean_bp_day"]
            if min(cost12, cost23) < -TOL_BP or abs(cost12 - cost23) > TOL_BP:
                raise ContractError(f"Nonlinear or negative summary costs: {name}/{window}")
            if any(abs(r["gross_exposure"] - rows[0]["gross_exposure"]) > 1e-10 for r in rows[1:]):
                raise ContractError(f"Exposure depends on cost multiple: {name}/{window}")


def mixture(matrix, candidate):
    return np.asarray(matrix) @ np.asarray(candidate.weights)


def sharpe(x, axis=None):
    x = np.asarray(x, dtype=float)
    sd = x.std(axis=axis, ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = x.mean(axis=axis) / sd * math.sqrt(365)
    return np.where(sd > 0, value, np.nan)


def max_drawdown(x):
    equity = np.concatenate(([0.0], np.cumsum(np.asarray(x, dtype=float))))
    return float(np.max(np.maximum.accumulate(equity) - equity))


def choose_discovery(matrix, family=None):
    """No validation/holdout value can enter either selection or the risk scale."""
    family = candidates() if family is None else family
    a, b = WINDOWS["discovery"]
    train = np.asarray(matrix)[a:b]
    scored = [(c, float(sharpe(mixture(train, c)))) for c in family]
    if not all(np.isfinite(score) for _, score in scored):
        raise ContractError("Undefined discovery Sharpe")
    ordered = sorted(scored, key=lambda cs: cs[0].identifier)
    selected = max(ordered, key=lambda cs: cs[1])[0]
    control = max((cs for cs in ordered if not cs[0].interior), key=lambda cs: cs[1])[0]
    sd_selected = mixture(train, selected).std(ddof=0)
    sd_control = mixture(train, control).std(ddof=0)
    scale = float(sd_selected / sd_control) if sd_control > 0 else float("nan")
    if not np.isfinite(scale) or scale <= 0:
        raise ContractError("Undefined discovery risk-match scale")
    return {"selected": selected, "control": control, "control_scale": scale,
            "selected_discovery_sharpe": float(sharpe(mixture(train, selected))),
            "control_discovery_sharpe": float(sharpe(mixture(train, control)))}


def circular_indices(n, block_length, replicates, seed):
    if n < 2 or block_length < 1 or replicates < 1:
        raise ContractError("Invalid circular bootstrap dimensions")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(replicates, math.ceil(n / block_length)))
    return ((starts[:, :, None] + np.arange(block_length)) % n).reshape(replicates, -1)[:, :n]


def paired_bootstrap(x, y, block_length, replicates=REPLICATES, seed=None):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 1 or y.shape != x.shape or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ContractError("Invalid paired bootstrap paths")
    idx = circular_indices(len(x), block_length, replicates, BOOT_SEED + block_length if seed is None else seed)
    differences = sharpe(x[idx], axis=1) - sharpe(y[idx], axis=1)
    if not np.isfinite(differences).all():
        raise ContractError("Undefined bootstrap Sharpe; no replicates may be discarded")
    lo, hi = np.percentile(differences, [2.5, 97.5])
    return {"block_length": block_length, "replicates": replicates,
            "seed": BOOT_SEED + block_length if seed is None else seed,
            "observed_sharpe_difference": float(sharpe(x) - sharpe(y)),
            "lower_95": float(lo), "upper_95": float(hi),
            "interpretation": "conditional descriptive interval on spent validation dates"}


def candidate_rows(matrix, summaries, family=None):
    rows = []
    for candidate in candidates() if family is None else family:
        for window, (a, b) in WINDOWS.items():
            path = mixture(matrix[a:b], candidate)
            exposure = sum(w * summaries[(name, window, 1)]["gross_exposure"]
                           for name, w in zip(SOURCES, candidate.weights))
            for cm in (1, 2, 3):
                mean_bp = sum(w * summaries[(name, window, cm)]["mean_bp_day"]
                              for name, w in zip(SOURCES, candidate.weights))
                rows.append({"candidate": candidate.identifier, "window": window, "cost_multiple": cm,
                             **{f"weight_{name}": w for name, w in zip(SOURCES, candidate.weights)},
                             "days": b - a, "mean_bp_day": float(path.mean() * 1e4) if cm == 1 else float(mean_bp),
                             "annualized_sharpe": float(sharpe(path)) if cm == 1 else NA,
                             "t_nw10": float(stats.newey_west_t(path, 10)[2]) if cm == 1 else NA,
                             "max_additive_drawdown": max_drawdown(path) if cm == 1 else NA,
                             "gross_exposure": float(exposure), "daily_path_available": cm == 1,
                             "bootstrap_interval": NA})
    return rows


def selection_record(selection):
    return {"selected_candidate": selection["selected"].identifier,
            "selected_weights": dict(zip(SOURCES, selection["selected"].weights)),
            "control_candidate": selection["control"].identifier,
            "control_weights": dict(zip(SOURCES, selection["control"].weights)),
            "control_scale_fixed_on_discovery": selection["control_scale"],
            "selected_discovery_sharpe": selection["selected_discovery_sharpe"],
            "control_discovery_sharpe": selection["control_discovery_sharpe"],
            "selection_window": "discovery only", "candidate_count": 30}


def analyze(matrix, summaries, selection):
    selected, control = selection["selected"], selection["control"]
    a, b = WINDOWS["validation"]
    x, y = mixture(matrix[a:b], selected), mixture(matrix[a:b], control)
    bootstrap = {str(block): paired_bootstrap(x, y, block) for block in BLOCKS}
    improvement = float(sharpe(x) - sharpe(y))
    mean2 = sum(w * summaries[(name, "validation", 2)]["mean_bp_day"] for name, w in zip(SOURCES, selected.weights))
    checks = {"selected_is_interior": selected.interior,
              "validation_sharpe_gain_at_least_0_15": improvement >= 0.15,
              "validation_mean_1x_positive": float(x.mean()) > 0,
              "validation_mean_2x_positive": mean2 > 0,
              "primary_bootstrap_lower_above_zero": bootstrap["30"]["lower_95"] > 0}
    verdict = {"verdict": "PARTIAL" if all(checks.values()) else "NULL", "checks": checks,
               "validation_sharpe_difference": improvement,
               "interpretation": "exploratory spent-sample screen; cannot confirm an edge"}
    risk = []
    correlation = []
    for window, (a, b) in WINDOWS.items():
        x = mixture(matrix[a:b], selected)
        y = mixture(matrix[a:b], control)
        risk.append({"window": window, "control_scale": selection["control_scale"],
                     "selected_max_additive_drawdown": max_drawdown(x),
                     "control_max_additive_drawdown": max_drawdown(y),
                     "risk_matched_control_max_additive_drawdown": max_drawdown(y * selection["control_scale"])})
        corr = np.corrcoef(matrix[a:b], rowvar=False)
        if not np.isfinite(corr).all():
            raise ContractError(f"Undefined source correlation in {window}")
        for j, name in enumerate(SOURCES):
            for k, other in enumerate(SOURCES):
                correlation.append({"window": window, "source_a": name, "source_b": other,
                                    "correlation": float(corr[j, k])})
    return candidate_rows(matrix, summaries), correlation, bootstrap, risk, verdict


def clean_json(value):
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean_json(v) for v in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return NA
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(clean_json(value), indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_csv(path, rows):
    if not rows:
        raise ContractError("Empty output table")
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows([{k: NA if isinstance(v, (float, np.floating)) and not np.isfinite(v) else v
                          for k, v in row.items()} for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "experiments/allocation_v1/results")
    args = parser.parse_args()
    # Guard failures precede data parsing and produce no research artifacts.
    try:
        manifest = verify_guards(ROOT)
    except (ContractError, prereg.PreregError) as exc:
        raise SystemExit(f"INCONCLUSIVE / PREFLIGHT: {exc}") from exc
    output = args.out
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Refusing to overwrite existing study outputs; use --out with a fresh directory")
    output.mkdir(parents=True, exist_ok=True)
    try:
        arrays, summaries = read_inputs(ROOT)
        matrix = np.column_stack([arrays[name] for name in SOURCES])
        choice = choose_discovery(matrix)
        # Persist immutable logical choices before any validation comparison.
        write_json(output / "selection.json", selection_record(choice))
        rows, correlations, bootstrap, risk, verdict = analyze(matrix, summaries, choice)
        write_csv(output / "candidates.csv", rows)
        write_csv(output / "correlations.csv", correlations)
        write_csv(output / "risk_matched.csv", risk)
        write_json(output / "bootstrap.json", bootstrap)
        write_json(output / "verdict.json", verdict)
        manifest["outputs_sha256"] = {p.name: sha256(p) for p in sorted(output.iterdir())
                                     if p.is_file() and p.name != "manifest.json"}
        write_json(output / "manifest.json", manifest)
        print(json.dumps(verdict, sort_keys=True))
    except ContractError as exc:
        verdict = {"verdict": "INCONCLUSIVE", "reason": str(exc), "repair_or_alternate_input": False}
        write_json(output / "verdict.json", verdict)
        write_json(output / "manifest.json", manifest)
        raise SystemExit(json.dumps(verdict, sort_keys=True)) from exc


if __name__ == "__main__":
    main()
