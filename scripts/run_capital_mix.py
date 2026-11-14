#!/usr/bin/env python3
"""R309: fixed initial-capital carry/spot comparison; archived inputs only, no trading."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lab import capital, prereg, stats  # noqa: E402

LANE = ROOT / "experiments/capital_mix_v1"
START, END = "2025-07-01", "2026-09-30"
CARRY_LABEL = "mexc+lighter L14d th5% K20"
SPOT_NAMES = ("trend_vol", "passive_matched", "trend_plain", "passive")
BOOKS = {
    "carry_trend": ("trend_vol", .5, .5),
    "carry_passive_matched": ("passive_matched", .5, .5),
    "carry_cash": ("trend_vol", 0., .5),
    "carry": ("trend_vol", 0., 1.),
    "trend": ("trend_vol", 1., 0.),
    "passive_matched": ("passive_matched", 1., 0.),
    "trend_plain": ("trend_plain", 1., 0.),
    "passive": ("passive", 1., 0.),
    "cash": ("trend_vol", 0., 0.),
}


class ContractError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_inputs(root=ROOT, lane=LANE):
    """Verify the frozen spec, source versions and runner before parsing any outcomes."""
    spec_sha = prereg.verify(lane / "PREREG.md")
    p = lane / "inputs.json"
    if f"Input manifest SHA-256: {digest(p)}" not in (lane / "PREREG.md").read_text():
        raise ContractError("input manifest differs from frozen specification")
    manifest = json.loads(p.read_text())
    for rel, expected in manifest["sha256"].items():
        path = root / rel
        if not path.is_file() or digest(path) != expected:
            raise ContractError(f"pinned input differs or missing: {rel}")
    return spec_sha, manifest


def _numeric(df, cols):
    try:
        a = df[list(cols)].to_numpy(dtype=float)
    except (ValueError, TypeError) as exc:
        raise ContractError("non-numeric archive field") from exc
    if not np.isfinite(a).all():
        raise ContractError("nonfinite archive field")


def validate_calendar(df, dates):
    if df["date"].duplicated().any() or list(df["date"]) != list(dates):
        raise ContractError("missing, duplicate or unordered date")


def align_carry_dates(df):
    """Carry labels the END midnight; spot labels the UTC candle's OPEN day."""
    out = df.copy()
    if not out["date"].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ContractError("invalid carry UTC date label")
    try:
        ending = pd.to_datetime(out["date"], format="%Y-%m-%d", utc=True, errors="raise")
    except ValueError as exc:
        raise ContractError("invalid carry UTC date label") from exc
    out["date"] = (ending - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    return out


def validate_spot(df, dates, multiple):
    validate_calendar(df, dates)
    _numeric(df, ("net", "gross", "cost_fraction", "nav", "cash_end", "turnover"))
    if not np.allclose(df.gross - df.cost_fraction, df.net, rtol=0, atol=1e-10):
        raise ContractError("spot gross/cost/net identity")
    if not np.allclose(np.cumprod(1 + df.net), df.nav, rtol=1e-9, atol=1e-11):
        raise ContractError("spot NAV does not start at cash=1 and compound net")
    if (np.any(df.cost_fraction < 0) or np.any(df.turnover < 0) or
            np.any(df.cash_end < -1e-10) or np.any(df.cash_end > df.nav + 1e-10)):
        raise ContractError("invalid spot costs or cash")
    if not np.allclose(df.cost_fraction, .0012 * multiple * df.turnover, rtol=0, atol=1e-10):
        raise ContractError("spot fee/turnover identity")
    # The archived split closes all holdings and already charges the terminal fee.
    if abs(float(df.iloc[-1].cash_end - df.iloc[-1].nav)) > 1e-10:
        raise ContractError("spot terminal liquidation missing")
    return df


def validate_carry(df, dates, multiple):
    validate_calendar(df, dates)
    _numeric(df, ("net", "gross", "funding", "legs", "held"))
    if (np.any(df.legs < 0) or np.any(df.legs != np.floor(df.legs)) or
            np.any(df.held < 0) or np.any(df.held > 20) or
            np.any(df.held != np.floor(df.held))):
        raise ContractError("invalid carry leg/pair counts")
    cost = .00055 * multiple * df.legs / 40
    # CSV gross/net are printed to 10 decimals: differencing allows 1e-10.
    if not np.allclose(df.gross - cost, df.net, rtol=0, atol=1.1e-10):
        raise ContractError("carry normalization or fee identity")
    return df


def load_inputs(root=ROOT):
    dates = pd.date_range(START, END).strftime("%Y-%m-%d").tolist()
    spot = pd.read_csv(root / "experiments/slow_trend_v1/results/daily.csv")
    carry = pd.read_csv(root / "experiments/xfund_lt_v1/results/daily.csv")
    inputs = {}
    for multiple in (1, 2, 3):
        s = spot[(spot.split == "known_holdout") & (spot.cost_multiple == multiple)]
        c = align_carry_dates(carry[(carry.strategy == CARRY_LABEL) & (carry.cost_multiple == multiple)])
        anchor = c[c.date == "2025-06-30"]
        if len(anchor) != 1:
            raise ContractError("carry preceding inventory anchor missing/duplicate")
        held = float(anchor.iloc[0].held)
        if not np.isfinite(held) or not 0 <= held <= 20 or held != int(held):
            raise ContractError("invalid carry preceding inventory anchor")
        c = c[(c.date >= START) & (c.date <= END)].reset_index(drop=True)
        validate_carry(c, dates, multiple)
        spots = {}
        for name in SPOT_NAMES:
            a = s[s.strategy == name].reset_index(drop=True)
            spots[name] = validate_spot(a, dates, multiple)
        inputs[multiple] = {"spot": spots, "carry": c,
                            "entry_cost": .00055 * multiple * held / 20}
    # Only costs change between carry tiers; never add the three copies of gross/funding.
    for multiple in (2, 3):
        for name in ("gross", "funding", "legs", "held"):
            if not np.array_equal(inputs[1]["carry"][name], inputs[multiple]["carry"][name]):
                raise ContractError("carry cost tiers have different underlying book")
    return dates, inputs


def replay(inputs):
    out = {}
    for multiple, data in inputs.items():
        c = data["carry"]
        for book, (spot_name, sw, cw) in BOOKS.items():
            s = data["spot"][spot_name]
            path = capital.segregated(s.net, s.gross, s.cost_fraction,
                                      c.gross, c.funding, .00055 * multiple * c.legs / 40,
                                      spot_weight=sw, carry_weight=cw,
                                      carry_entry_cost=data["entry_cost"])
            out[multiple, book] = path
    return out


def sharpe(x, axis=None):
    a = np.asarray(x)
    sd = a.std(axis=axis, ddof=1)
    mu = a.mean(axis=axis)
    return np.divide(mu * np.sqrt(365), sd, out=np.zeros_like(mu, dtype=float), where=sd > 1e-15)


def metrics(path):
    r, eq = path["net"], np.r_[1., path["equity"]]
    return {"days": len(r), "ending_equity": float(eq[-1]),
            "pnl_per_10000": float((eq[-1] - 1) * 10000),
            "annual_profit_on_initial_pct": float((eq[-1] - 1) * 365 / len(r) * 100),
            "cagr_pct": float((eq[-1] ** (365 / len(r)) - 1) * 100),
            "mean_bp": float(r.mean() * 10000),
            "vol_pct": float(r.std(ddof=1) * np.sqrt(365) * 100),
            "sharpe": float(sharpe(r)), "nw_t": float(stats.newey_west_t(r, 10)[2]),
            "max_drawdown_pct": float(np.max(1 - eq / np.maximum.accumulate(eq)) * 100),
            "gross_pnl_per_10000": float(path["dollar_gross"].sum() * 10000),
            "funding_pnl_per_10000": float(path["dollar_funding"].sum() * 10000),
            "cost_per_10000": float(path["dollar_cost"].sum() * 10000),
            "min_spot_equity": float(path["spot_equity"].min()),
            "min_carry_equity": float(path["carry_equity"].min())}


def paired_bootstrap(paths, block, reps=5000):
    """Joint circular-block uncertainty on observed portfolio returns, not simulated fills."""
    candidate = paths[1, "carry_trend"]
    n = len(candidate["net"])
    rng = np.random.default_rng(20261023309 + block)
    starts = rng.integers(0, n, size=(reps, (n + block - 1) // block))
    ix = ((starts[:, :, None] + np.arange(block)) % n).reshape(reps, -1)[:, :n]
    cand = candidate["net"][ix]
    out = []
    for comparator in ("carry", "trend", "carry_passive_matched", "carry_cash"):
        base = paths[1, comparator]
        d = sharpe(cand, axis=1) - sharpe(base["net"][ix], axis=1)
        profit = (candidate["dollar_net"] - base["dollar_net"])[ix].mean(axis=1) * 10000
        ci = np.quantile(d, [.025, .975])
        pci = np.quantile(profit, [.025, .975])
        out.append({"block": block, "comparator": comparator,
                    "sharpe_difference": float(sharpe(candidate["net"]) - sharpe(base["net"])),
                    "sharpe_ci_low": float(ci[0]), "sharpe_ci_high": float(ci[1]),
                    "paired_initial_capital_mean_bp": float(np.mean(candidate["dollar_net"] - base["dollar_net"]) * 10000),
                    "profit_ci_low_bp": float(pci[0]), "profit_ci_high_bp": float(pci[1])})
    return out


def decide(rows, intervals):
    at = {(r["cost_multiple"], r["book"]): r for r in rows}
    main = {r["comparator"]: r for r in intervals if r["block"] == 30}
    p = at[1, "carry_trend"]
    gates = {
        "sharpe_above_both_parents_by_015": all(p["sharpe"] >= at[1, b]["sharpe"] + .15 for b in ("carry", "trend")),
        "paired_sharpe_lower_ci_above_zero_both_parents": all(main[b]["sharpe_ci_low"] > 0 for b in ("carry", "trend")),
        "sharpe_above_carry_passive_matched": p["sharpe"] > at[1, "carry_passive_matched"]["sharpe"],
        "drawdown_no_worse_than_trend": p["max_drawdown_pct"] <= at[1, "trend"]["max_drawdown_pct"],
        "positive_profit_at_2x_and_3x": all(at[m, "carry_trend"]["ending_equity"] > 1 for m in (2, 3)),
    }
    return {"verdict": "PARTIAL" if all(gates.values()) else "NULL", "gates": gates,
            "trials": 1, "fresh_out_of_sample": False, "execution_and_margin_verified": False}


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def run(out, root=ROOT, lane=LANE):
    spec_sha, manifest = verify_inputs(root, lane)
    out = Path(out)
    if out.exists():
        raise ContractError("output directory exists; use a fresh directory")
    try:
        dates, inputs = load_inputs(root)
        paths = replay(inputs)
        rows = [{"cost_multiple": multiple, "book": book, **metrics(path)}
                for (multiple, book), path in paths.items()]
        intervals = sum((paired_bootstrap(paths, b) for b in (10, 30, 60)), [])
        verdict = decide(rows, intervals)
    except (ValueError, KeyError, OSError, ArithmeticError) as exc:
        # The spec/code/input bytes passed verification, but their data contract did not.
        # Preserve this failure as INCONCLUSIVE; never write partial economic tables.
        out.mkdir(parents=True)
        verdict = {"verdict": "INCONCLUSIVE", "failure": f"{type(exc).__name__}: {exc}",
                   "prereg_sha256": spec_sha, "trials": 1,
                   "fresh_out_of_sample": False, "execution_and_margin_verified": False}
        (out / "verdict.json").write_text(json.dumps(verdict, indent=2, allow_nan=False) + "\n")
        return verdict
    out.mkdir(parents=True)
    write_csv(out / "metrics.csv", rows)
    write_csv(out / "paired.csv", intervals)
    daily = []
    for (multiple, book), path in paths.items():
        for i, day in enumerate(dates):
            daily.append({"cost_multiple": multiple, "book": book, "date": day,
                          **{k: float(v[i]) for k, v in path.items()}})
    # Compressed deterministic CSV, avoiding duplicate large text artifacts.
    pd.DataFrame(daily).to_csv(out / "daily.csv.gz", index=False, float_format="%.12g",
                               compression={"method": "gzip", "mtime": 0}, lineterminator="\n")
    (out / "verdict.json").write_text(json.dumps(verdict, indent=2, allow_nan=False) + "\n")
    receipt = {"prereg_sha256": spec_sha, "inputs": manifest["sha256"],
               "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
               "start": START, "end": END, "days": len(dates),
               "carry_entry_cost_by_tier": {str(m): x["entry_cost"] for m, x in inputs.items()},
               "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir())}}
    (out / "manifest.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return verdict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=LANE / "results")
    args = parser.parse_args()
    print(json.dumps(run(args.out), indent=2))
