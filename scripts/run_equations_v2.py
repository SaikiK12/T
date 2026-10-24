"""R311: exact R310 policy repeat after source-only Lighter page-seam recovery."""
from pathlib import Path
import argparse
import fcntl
import importlib.util
import json
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_equations as base  # noqa: E402
from lab import registry  # noqa: E402
from lab.equation_data import load_panel  # noqa: E402

LANE = ROOT/"experiments/equations_v2"


def verify_family():
    old = json.loads((ROOT/"experiments/equations_v1/settings.json").read_text())
    new = json.loads((LANE/"settings.json").read_text())
    if set(new) != set(old):
        raise ValueError("correction must retain the original settings schema")
    for key in old:
        if key not in {"registry_id", "program_trials_before"} and new[key] != old[key]:
            raise ValueError("economic parameter changed in source-only correction: "+key)
    if new["registry_id"] != "R311" or new["program_trials_before"] != old["program_trials_before"]+12:
        raise ValueError("incorrect corrective round lineage or trial count")


def register(out):
    verify_family()
    digest, _ = base.verify_inputs(ROOT, LANE)
    manifest = json.loads((out/"manifest.json").read_text())
    if manifest["prereg_sha256"] != digest:
        raise ValueError("result belongs to a different preregistration")
    for name, expected in manifest["outputs"].items():
        if base.sha(out/name) != expected:
            raise ValueError("changed result: "+name)
    v = json.loads((out/"verdict.json").read_text())
    expected = {"id": "R311", "lane": "equations_v2", "status": "DONE", "prereg_sha": digest,
                "trials": "12", "verdict": "PENDING" if v["verdict"] == "INCONCLUSIVE" else v["verdict"]}
    def landed():
        rows = [r for r in registry.rows(ROOT/"registry/rounds.csv") if r["id"] == "R311"]
        if len(rows) > 1 or (rows and any(rows[0][k] != value for k, value in expected.items())):
            raise ValueError("conflicting R311 registry row")
        return bool(rows)
    error = None
    if not landed():
        try:
            registry.append(ROOT/"registry/rounds.csv", id="R311", date=str(pd.Timestamp.now(tz="UTC").date()),
                            lane="equations_v2", title="Source-seam corrected repeat of twelve funding/basis policies",
                            status="DONE", verdict=expected["verdict"], trials=12, prereg_sha=digest,
                            path="experiments/equations_v2",
                            notes=f"M409; R310 source acquisition corrected only; same12 policies/gates; {v['verdict']}; selected {v['selected']}; gate0 close/funding-notional proxies, zero prospective days")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    confirmed = landed()
    receipt = LANE/"receipts"
    receipt.mkdir(exist_ok=True)
    base.write_json(receipt/f"registry_{time.time_ns()}.json", {"landed": confirmed, "observed_exception": error,
                    "result_manifest_sha256": base.sha(out/"manifest.json")})
    if not confirmed:
        raise RuntimeError("calculation retained; registry append unconfirmed: "+str(error))


def audit(out):
    digest, inputs = base.verify_inputs(ROOT, LANE)
    manifest = json.loads((out/"manifest.json").read_text())
    if manifest["prereg_sha256"] != digest:
        raise ValueError("audit result belongs to another specification")
    for name, expected in manifest["outputs"].items():
        if base.sha(out/name) != expected:
            raise ValueError("changed audit input: "+name)
    spec = importlib.util.spec_from_file_location("r310_cash", ROOT/"experiments/equations_v1/check_cash.py")
    cash = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cash)
    settings = json.loads((LANE/"settings.json").read_text())
    parse = lambda s: int(pd.Timestamp(s, tz="UTC").timestamp()*1000)
    panel, _ = load_panel(ROOT/inputs["data_root"], ROOT/inputs["symbols"],
                          parse(settings["start"]), parse(settings["end_exclusive"]))
    daily = pd.read_csv(out/"daily.csv.gz", float_precision="round_trip")
    tickets = pd.read_csv(out/"tickets.csv.gz", float_precision="round_trip")
    maximum, count = 0., 0
    for (split, label), rows in daily.groupby(["split", "label"], sort=True):
        rows = rows.sort_values("origin_ms")
        trades = tickets[tickets.split.eq(split) & tickets.label.eq(label)]
        actual = cash.reconstruct(panel, trades, rows.origin_ms, int(rows.origin_ms.iloc[0]))
        expected = np.stack([rows[[f"mexc_equity_{m}x", f"lighter_equity_{m}x"]].to_numpy()
                             for m in (1, 2, 3)], axis=1)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-6)
        maximum = max(maximum, float(np.max(abs(actual-expected))))
        count += len(rows)*6
    base.verify_inputs(ROOT, LANE)
    base.verify_inputs()
    return {"venue_day_tier_balances_checked": count, "max_abs_dollar_error": maximum,
            "proxy_arithmetic_only": True, "unknown_intervals_remain_unscored": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=LANE/"results")
    p.add_argument("--register", action="store_true")
    p.add_argument("--register-existing", action="store_true")
    p.add_argument("--audit-only", action="store_true")
    a = p.parse_args()
    lockpath = ROOT/".cache/equations_v2.lock"
    lockpath.parent.mkdir(exist_ok=True)
    with lockpath.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        base.verify_inputs()  # old source/result provenance stays intact
        verify_family()
        if a.audit_only:
            print(json.dumps(audit(a.out), sort_keys=True))
            return
        if not a.register_existing:
            base.run(a.out, lane=LANE, root=ROOT)
        base.verify_inputs()
        if a.register or a.register_existing:
            register(a.out)


if __name__ == "__main__":
    main()
