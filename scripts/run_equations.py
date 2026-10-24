"""R310: one frozen 12-policy funding/basis family, offline only.

No network, accounts or orders. A run requires immutable inputs and a fresh result
directory. All historical estimates are gate 0 on already inspected calendar dates.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import fcntl
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg, registry, inference, stats  # noqa: E402
from lab.equations import LABELS, COSTS, build_forecasts, simulate  # noqa: E402
from lab.equation_data import load_panel, parent_states  # noqa: E402

LANE = ROOT / "experiments/equations_v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.integer, np.bool_)):
        return x.item()
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    return x


def write_json(path, obj):
    path.write_text(json.dumps(clean(obj), sort_keys=True, indent=2, allow_nan=False) + "\n")


def verify_inputs(root=ROOT, lane=LANE):
    digest = prereg.verify(lane / "PREREG.md")
    manifest = lane / "inputs.json"
    if f"Input manifest SHA-256: {sha(manifest)}" not in (lane / "PREREG.md").read_text():
        raise ValueError("frozen input manifest mismatch")
    data = json.loads(manifest.read_text())
    for rel, expected in data["sha256"].items():
        p = root / rel
        if p.is_symlink() or not p.is_file() or sha(p) != expected:
            raise ValueError(f"changed/missing pinned input: {rel}")
    folder = root / data["data_root"]
    found = {str(p.relative_to(root)) for p in folder.rglob("*.parquet")}
    wanted = {x for x in data["sha256"] if x.endswith(".parquet")}
    if found != wanted:
        raise ValueError("data folder inventory changed")
    state = json.loads((folder / "acquisition_status.json").read_text())
    if not state.get("complete") or state.get("errors"):
        raise ValueError("public acquisition is incomplete; no outcomes permitted")
    return digest, data


def compressed_csv(path, rows, fields):
    text = io.StringIO(newline="")
    w = csv.DictWriter(text, fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_bytes(gzip.compress(text.getvalue().encode(), mtime=0))


def deterministic_npz(path, **arrays):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.lib.format.write_array(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(key + ".npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, b.getvalue())


def metrics(result, multiple):
    j = multiple-1
    good = result["scored"] & ~result["insolvent"][:, j] & np.isfinite(result["return"][:, j])
    r = result["return"][good, j]
    cash = result["net"][good, j]
    sd = float(r.std(ddof=1)) if len(r) > 1 else np.nan
    full = np.r_[10000., result["equity"][:, j]]
    drawdown = 1-full/np.maximum.accumulate(full)
    return {"scored_days": int(good.sum()), "calendar_days": len(good),
            "active_days": int(np.count_nonzero(result["held"][good])),
            "observed_pnl": float(result["net"][:, j].sum()),
            "scored_mean_dollar": float(cash.mean()) if len(cash) else np.nan,
            "mean_return": float(r.mean()) if len(r) else np.nan, "sd_return": sd,
            "ann_net_pct": float(r.mean()*36500) if len(r) else np.nan,
            "sharpe": float(r.mean()/sd*np.sqrt(365)) if sd > 0 else np.nan,
            "nw_t": float(stats.newey_west_t(np.where(good, result["return"][:, j], np.nan), 10)[2])
                    if len(r) > 10 and sd > 0 else np.nan,
            "max_drawdown_pct": float(drawdown.max()*100),
            "funding": float(result["funding"][:, j].sum()), "price": float(result["price"][:, j].sum()),
            "cost": float(result["cost"][:, j].sum()), "entries": result["entries"],
            "turnover": float(result["turnover"].sum()),
            "unscored_days": int((~result["scored"]).sum()),
            "gross_breach_days": int(result["gross_breach"].sum()),
            "insolvent_days": int(result["insolvent"][:, j].sum()),
            "unclosed_legs": int(np.count_nonzero(result["final_quantity"]))}


def calibration_scales(accounts):
    """One common nonzero training risk, only downsizing. No validation input."""
    eligible, vol = [], {}
    for label, a in accounts.items():
        m = metrics(a, 2)
        if m["scored_days"] >= 60 and m["active_days"] >= 60 and m["sd_return"] > 1e-12:
            eligible.append(label)
            vol[label] = m["sd_return"]
    if "reference" not in eligible or not any(x != "reference" for x in eligible):
        return {k: 1. for k in accounts}, [], None
    target = min(vol.values())
    scales = {k: min(1., target/vol[k]) if k in vol else 1. for k in accounts}
    return scales, [k for k in eligible if k != "reference"], target


def select_primary(accounts, eligible):
    if not eligible:
        return None
    # Highest 2x mean initial-capital dollar PnL; no validation reselection.
    return sorted(eligible, key=lambda k: (-metrics(accounts[k], 2)["scored_mean_dollar"],
                                           accounts[k]["turnover"].sum(), LABELS.index(k)))[0]


def evaluate(accounts, selected, settings):
    ref = accounts["reference"]
    common = ref["scored"] & ~ref["insolvent"][:, 1] & np.isfinite(ref["return"][:, 1])
    for x in LABELS:
        common &= (accounts[x]["scored"] & ~accounts[x]["insolvent"][:, 1] &
                   np.isfinite(accounts[x]["return"][:, 1]))
    n = int(common.sum())
    report = {"selected": selected, "common_validation_days": n, "verdict": "INCONCLUSIVE",
              "gate": 0, "paper_candidate": None,
              "historical_status": "spent dates/current-survivor universe/current contract rules/close-price proxies",
              "conditional_inference_only": True, "gates": {}}
    if selected is None or n < 60 or n != len(common):
        report["reason"] = ("fewer than 60 common validation days, unknown intervals, or no risk-comparable calibration candidate; "
                            "missing calendar days are not compressed into adjacent bootstrap observations")
        return report
    diff = np.column_stack([accounts[x]["return"][common, 1]-ref["return"][common, 1] for x in LABELS])
    varying = diff.std(axis=0, ddof=1) > 1e-14
    d = diff[:, LABELS.index(selected)]
    if d.std(ddof=1) <= 1e-14:
        report["reason"] = "selected paired stream has no estimable dependent-null variance"
        return report
    result = inference.spa(diff[:, varying], n_boot=settings["spa_reps"], block=10,
                           rng=np.random.default_rng(settings["seed"]))
    result["included_labels"] = [LABELS[k] for k in np.flatnonzero(varying)]
    bm = inference.boot_means(d[:, None], n_boot=settings["paired_reps"], block=10,
                              rng=np.random.default_rng(settings["seed"]+1)).ravel().astype(float)
    p = (1+np.count_nonzero(bm-d.mean() >= d.mean()))/(len(bm)+1)
    interval = np.quantile(bm, [.025, .975])
    a = accounts[selected]
    x = a["return"][common, 1]
    r = ref["return"][common, 1]
    net = a["net"][common, 1]
    contribution = a["coin_net"][common, :, 1].sum(axis=0)
    top = np.argsort(-contribution, kind="stable")[:2]
    leave = (net-a["coin_net"][common][:, top, 1].sum(axis=1)).mean()
    halves = (float(d[:n//2].mean()), float(d[n//2:].mean()))
    trimmed_x = np.sort(x)[10:-10].mean()
    trimmed_d = np.sort(d)[10:-10].mean()
    gates = {"family_spa": result["consistent"] <= .05,
             "selected_bonferroni": p <= .05/12 and interval[0] > 0,
             "mean_net_2x": x.mean() > 0, "both_halves_gain": min(halves) > 0,
             "net_3x": a["return"][common, 2].mean() > 0,
             "leave_two_coins": leave > 0, "trimmed": trimmed_x > 0 and trimmed_d > 0,
             "comparable_risk": x.std(ddof=1) <= 1.1*r.std(ddof=1),
             "complete_accounting": bool(a["scored"].all() and ref["scored"].all() and
                                          not a["gross_breach"].any() and not ref["gross_breach"].any() and
                                          not a["insolvent"].any() and not ref["insolvent"].any() and
                                          not np.any(a["final_quantity"]) and not np.any(ref["final_quantity"]))}
    passed = all(gates.values())
    report.update({"verdict": "PARTIAL" if passed else "NULL", "gates": gates, "spa": result,
                   "selected_one_sided_p": p, "paired_95_interval": interval, "gain_halves": halves,
                   "leave_two_mean_dollar": float(leave), "removed_coin_indices": top,
                   "trimmed_mean_return": float(trimmed_x), "trimmed_gain": float(trimmed_d),
                   "paper_candidate": selected if passed else None})
    return report


def run(out, lane=LANE, root=ROOT):
    psha, inputs = verify_inputs(root, lane)
    settings = json.loads((lane / "settings.json").read_text())
    if tuple(settings["labels"]) != LABELS or settings["trials"] != 12:
        raise ValueError("candidate family differs from frozen implementation")
    if not np.array_equal(settings["one_way_costs"], COSTS):
        raise ValueError("cost specification differs from implementation")
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("outcome directory must be fresh and empty")
    out.mkdir(parents=True, exist_ok=True)
    data = root / inputs["data_root"]
    parse = lambda s: int(pd.Timestamp(s, tz="UTC").timestamp()*1000)
    panel, coverage = load_panel(data, root / inputs["symbols"], parse(settings["start"]), parse(settings["end_exclusive"]))
    train_start, val_start, val_end = parse(settings["start"]), parse(settings["validation_start"]), parse(settings["end_exclusive"])
    stop = int((val_start-panel.times[0])//3_600_000)+1
    training_panel = replace(panel, times=panel.times[:stop], prices=panel.prices[:stop],
                             fresh=panel.fresh[:stop], rates=panel.rates[:stop],
                             funding_ok=panel.funding_ok[:stop],
                             settlement=panel.settlement[:stop] if panel.settlement is not None else None)
    forecasts = build_forecasts(training_panel)
    reference_train, legacy_train = parent_states(panel, train_start, val_start)
    reference_val = None
    labels = ("reference",) + LABELS

    def simulation(label, start, end, scale=1.):
        state = reference_train if start == train_start else reference_val
        return simulate(panel, forecasts, label, start, end, scale=scale,
                        baseline_states=state if label == "reference" else None)

    train = {}
    for label in labels:
        print("calibration", label, flush=True)
        train[label] = simulation(label, train_start, val_start)
    scales, eligible, risk = calibration_scales(train)
    base_metrics = {k: metrics(v, 2) for k, v in train.items()}
    for label in labels:
        if scales[label] < 1:
            print("risk-matched calibration", label, scales[label], flush=True)
            train[label] = simulation(label, train_start, val_start, scales[label])
    primary = select_primary(train, eligible)
    selected_before_validation = {"selected": primary, "scales": scales, "eligible": eligible,
                                  "common_training_sd": risk, "unscaled_2x_metrics": base_metrics,
                                  "criterion": "calibration-only 2x mean dollar PnL; turnover then fixed-label ties"}
    # Persist the training choice BEFORE any validation simulation is called.
    write_json(out / "selection.json", selected_before_validation)
    forecasts = build_forecasts(panel)
    reference_val, legacy_val = parent_states(panel, val_start, val_end)
    validation = {}
    for label in labels:
        print("validation", label, flush=True)
        validation[label] = simulation(label, val_start, val_end, scales[label])
    verdict = evaluate(validation, primary, settings)
    verdict["program_trials_before"] = settings["program_trials_before"]
    verdict["new_trials"] = 12
    verdict["prospective_days"] = 0
    verdict["risk_scales"] = scales
    write_json(out / "verdict.json", verdict)
    write_json(out / "coverage.json", coverage)
    deterministic_npz(out / "forecasts.npz", funding=forecasts.funding, basis=forecasts.basis,
                      phi=forecasts.phi, beta=forecasts.beta, basis_training_dates=forecasts.basis_training_dates,
                      eligible=forecasts.eligible, keys=np.array(panel.keys),
                      origin_ms=panel.times[::24], labels=np.array(LABELS))
    write_json(out / "forecast_schema.json", {
        "funding_axes": ["model F0/F1", "horizon1/7/14d", "as_of_UTC_midnight", "frozen_coin", "MEXC/Lighter"],
        "basis_axes": ["horizon1/7/14d", "as_of_UTC_midnight", "frozen_coin"],
        "funding_units": "sum of predicted signed settlement fractions per venue, positive longs pay",
        "basis_units": "equal-underlying-quantity price PnL divided by larger entry leg price",
        "prediction_clock": "midnight closed history only; price labels end strictly before it",
        "allocation_clock": "01:00 UTC, using then-known closing prices for economic costs/quantities",
        "fill_model": "immediate 01:00 closing-price proxy after same-clock funding; not BBO/fill evidence",
        "missing": "NaN/unavailable, never substituted with predicted zero",
        "rule_vintage": "current metadata only, historical venue rules not verified"})
    summaries, daily, tickets, attr = [], [], [], {}
    for split, start, group in (("calibration", train_start, train), ("validation", val_start, validation)):
        for label, result in group.items():
            for multiple in (1, 2, 3):
                summaries.append({"split": split, "label": label, "cost_multiple": multiple,
                                  **metrics(result, multiple)})
            for d in range(len(result["net"])):
                row = {"split": split, "label": label, "origin_ms": start+d*86_400_000,
                       "scored": int(result["scored"][d]), "held": result["held"][d],
                       "turnover": result["turnover"][d], "forced": result["forced"][d],
                       "gross_breach": int(result["gross_breach"][d])}
                for m in (1, 2, 3):
                    for field in ("net", "price", "funding", "cost", "equity", "return"):
                        row[f"{field}_{m}x"] = float(result[field][d, m-1])
                    for v, venue in enumerate(("mexc", "lighter")):
                        row[f"{venue}_equity_{m}x"] = float(result["venue_equity"][d, m-1, v])
                daily.append(row)
            tickets.extend({"split": split, "label": label, **ticket} for ticket in result["tickets"])
            attr[split+"__"+label.replace("+", "plus")] = result["coin_net"]
    with (out / "summary.csv").open("w", newline="") as h:
        w = csv.DictWriter(h, list(summaries[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(summaries)
    compressed_csv(out / "daily.csv.gz", daily, list(daily[0]))
    ticket_fields = ["split", "label", "time_ms", "coin", "reason", "old_mexc", "old_lighter", "new_mexc", "new_lighter",
                     "mexc_price_proxy", "lighter_price_proxy", "mexc_cost_1x", "lighter_cost_1x"]
    compressed_csv(out / "tickets.csv.gz", tickets, ticket_fields)
    deterministic_npz(out / "coin_pnl.npz", **attr)
    old = [{"split": split, **row} for split, rows in (("calibration", legacy_train), ("validation", legacy_val)) for row in rows]
    compressed_csv(out / "legacy_rule_replay.csv.gz", old, list(old[0]))
    # Mandatory post-run source verification, before any successful receipt.
    verify_inputs(root, lane)
    files = {p.name: sha(p) for p in out.iterdir() if p.is_file()}
    write_json(out / "manifest.json", {"prereg_sha256": psha, "inputs_sha256": sha(lane / "inputs.json"),
                                       "python": platform.python_version(), "numpy": np.__version__,
                                       "pandas": pd.__version__, "outputs": files,
                                       "market_mode": "historical close-price/funding-notional proxy; no gate admission"})
    print("verdict", verdict["verdict"], "selected", primary, flush=True)
    return verdict, psha


def register_result(out, *, root=ROOT, lane=LANE):
    """Reconcile an append that may have landed even when its caller saw a failure."""
    digest, _ = verify_inputs(root, lane)
    out = Path(out)
    manifest = json.loads((out / "manifest.json").read_text())
    if manifest["prereg_sha256"] != digest:
        raise ValueError("result receipt belongs to a different specification")
    for name, expected in manifest["outputs"].items():
        if sha(out / name) != expected:
            raise ValueError("result changed before registration: " + name)
    v = json.loads((out / "verdict.json").read_text())
    rid = json.loads((lane / "settings.json").read_text())["registry_id"]
    expected = {"id": rid, "prereg_sha": digest, "trials": "12", "lane": "equations_v1", "status": "DONE",
                "verdict": "PENDING" if v["verdict"] == "INCONCLUSIVE" else v["verdict"]}

    def existing():
        rows = [r for r in registry.rows(root / "registry/rounds.csv") if r["id"] == rid]
        if rows and any(rows[0][k] != value for k, value in expected.items()):
            raise ValueError("conflicting registry id; no append authorized")
        return bool(rows)

    error = None
    if not existing():
        try:
            registry.append(root / "registry/rounds.csv", id=rid, date="2026-10-24", lane="equations_v1",
                            title="Twelve cost-aware funding/basis equations on the fixed R288 MEXC/Lighter universe",
                            status="DONE", verdict="PENDING" if v["verdict"] == "INCONCLUSIVE" else v["verdict"], trials=12,
                            prereg_sha=digest, path="experiments/equations_v1",
                            notes=f"M409; {v['verdict']}; selected {v['selected']}; close/funding-notional proxies, current survivors/rules, spent calendar; zero prospective evidence")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    landed = existing()
    receipts = lane / "receipts"
    receipts.mkdir(exist_ok=True)
    write_json(receipts / f"registry_{time.time_ns()}.json", {"registry_id": rid, "landed": landed,
               "observed_exception": error, "result_manifest_sha256": sha(out / "manifest.json")})
    if not landed:
        raise RuntimeError("calculation succeeded; registry append remains unconfirmed: " + str(error))
    return rid


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=LANE / "results")
    p.add_argument("--register", action="store_true")
    p.add_argument("--register-existing", action="store_true")
    a = p.parse_args()
    lockpath = ROOT / ".cache/equations_v1.lock"
    lockpath.parent.mkdir(exist_ok=True)
    with lockpath.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("another equation lane writer is active")
        if not a.register_existing:
            run(a.out)
        if a.register or a.register_existing:
            register_result(a.out)


if __name__ == "__main__":
    main()
