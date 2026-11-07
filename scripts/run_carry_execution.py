"""R417: one offline, frozen depth/cash diagnostic; no network or forward tick."""
import argparse
from datetime import date
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, registry, stress  # noqa: E402
from lab.carry_execution import Book, number, pair_sweep, stress_replay  # noqa: E402

LANE = ROOT / "experiments/carry_execution_v1"
PARENT = ROOT / "experiments/pair_quotes_v1/evidence"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs():
    frozen = prereg.verify(LANE / "PREREG.md")
    manifest_path = LANE / "inputs.json"
    relative = manifest_path.relative_to(ROOT).as_posix()
    if f"{digest(manifest_path)}  {relative}" not in (LANE / "PREREG.md").read_text():
        raise ValueError("input manifest differs from the frozen PREREG")
    inputs = json.loads(manifest_path.read_text())["sha256"]
    for name, sha in inputs.items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or digest(path) != sha:
            raise ValueError(f"input mismatch: {name}")
    # A freeze in the working directory alone is insufficient: verify that
    # this exact closed input set was committed before measuring.
    for name in [*inputs, relative, "experiments/carry_execution_v1/PREREG.md",
                 "experiments/carry_execution_v1/PREREG.sha256"]:
        committed = subprocess.run(["git", "show", "HEAD:" + name], cwd=ROOT,
                                   check=True, capture_output=True).stdout
        if committed != (ROOT / name).read_bytes():
            raise ValueError("input is not committed: " + name)
    return frozen, inputs


def raw(name, records):
    r = records[name]
    if r["http_status"] != 200 or r["error"] is not None:
        raise ValueError("parent source did not succeed")
    body = gzip.decompress((PARENT / r["body"]).read_bytes())
    if hashlib.sha256(body).hexdigest() != r["sha256"]:
        raise ValueError("parent raw-body identity mismatch")
    return json.loads(body, parse_float=Decimal)


def aggregated(rows):
    levels = {}
    for price, size in rows:
        p, q = number(price, positive=True), number(size, positive=True)
        levels[p] = levels.get(p, Decimal(0)) + q
    return levels


def normalize_btc(records, observation):
    """Only the predeclared BTC control; never read other parent market bodies."""
    mm = raw("BTC_mexc_meta", records)
    if mm.get("success") is not True or mm.get("code") != 0:
        raise ValueError("MEXC metadata envelope")
    mm = mm["data"]
    if (mm["symbol"], mm["baseCoin"], mm["quoteCoin"], mm["settleCoin"], mm["type"]) != (
            "BTC_USDT", "BTC", "USDT", "USDT", 1):
        raise ValueError("MEXC BTC contract identity")
    lm = raw("BTC_lighter_meta", records)
    if lm.get("code") != 200:
        raise ValueError("Lighter metadata envelope")
    lm, = lm["order_book_details"]
    if (lm["symbol"], lm["market_id"], lm["status"]) != ("BTC", 1, "active"):
        raise ValueError("Lighter BTC identity")
    mb = raw(f"BTC_mexc_book_{observation}", records)
    lb = raw(f"BTC_lighter_book_{observation}", records)
    if mb.get("success") is not True or mb.get("code") != 0 or lb.get("code") != 200:
        raise ValueError("book envelope")
    mb = mb["data"]
    multiplier = number(mm["contractSize"], positive=True)
    max_levels = mm["marketOrderMaxLevel"]
    if type(max_levels) is not int or max_levels <= 0:
        raise ValueError("MEXC market-order level bound missing")
    normalized = []
    for venue, payload in (("mexc", mb), ("lighter", lb)):
        sides = {}
        for side in ("bids", "asks"):
            if venue == "mexc":
                values = []
                for p, q, count in payload[side]:
                    number(count, positive=True)
                    values.append((p, number(q, positive=True) * multiplier))
            else:
                values = [(o["price"], o["remaining_base_amount"]) for o in payload[side]]
            levels = aggregated(values)
            sides[side] = sorted(levels.items(), reverse=side == "bids")
            if venue == "mexc":
                sides[side] = sides[side][:max_levels]
        normalized.append(Book(**sides))
    lots = (multiplier * number(mm["volUnit"], positive=True),
            Decimal(10) ** -int(lm["supported_size_decimals"]))
    minima = (multiplier * number(mm["minVol"], positive=True), number(lm["min_base_amount"], positive=True))
    receipts = [records[f"BTC_{v}_book_{observation}"]["receipt"] for v in ("mexc", "lighter")]
    clocks = dict(received_utc_ns=[r["received_utc_ns"] for r in receipts],
                  receive_skew_ms=abs(receipts[0]["received_mono_ns"] - receipts[1]["received_mono_ns"]) / 1e6,
                  source_clock_authenticated=False, actual_arrival_or_fills_observed=False)
    return tuple(normalized), lots, minima, number(lm["min_quote_amount"], positive=True), clocks


def measure(spec):
    records = {r["name"]: r for r in json.loads((PARENT / "receipts.json").read_text())["records"]}
    market = []
    for observation in (0, 1):
        books, lots, minima, quote_min, clocks = normalize_btc(records, observation)
        for target in spec["notionals_per_leg"]:
            for multiple in (1, 2, 3):
                out = pair_sweep(target, books, lots, minima, spec["snapshot_fee_scenarios"], multiple=multiple)
                if out["quantity"] * books[1].bids[0][0] < quote_min:
                    out = dict(state="BLOCKED_QUOTE_MINIMUM", quantity=out["quantity"], directions=[])
                market.append(dict(observation=observation, target_per_leg=target, cost_multiple=multiple,
                                   clocks=clocks, **out))
    synthetic = []
    name = "2025-10-10 liquidations"
    start, end = stress.EPISODES[name]
    for case in spec["synthetic_cases"]:
        if not start <= case["episode_date"] <= end:
            raise ValueError("synthetic case outside the named stress window")
        # Dates and the outage duration anchor the scenario to the named case;
        # none of the price path, depth or tier parameters is historical data.
        date.fromisoformat(case["episode_date"])
        for capital in spec["account_capitals"]:
            n = number(capital, positive=True) / 2
            for multiple in (1, 2, 3):
                synthetic.append(dict(case=case["name"], account_capital=capital, notional_per_leg=str(n), cost_multiple=multiple,
                                      **stress_replay(case, n, multiple=multiple)))
    return dict(registry_id="R417", predictive_trials=0, prospective_days=0,
                program_trials=registry.program_trials(ROOT / "registry/rounds.csv"),
                measured_scope="two old BTC MEXC/Lighter snapshots only; new sizes are gate-0 diagnostics",
                fee_scope="published-rate scenarios, not owner entitlement",
                quote_conversion="USDT = USDC = USD assumed, not measured",
                current_capacity=None, expected_return=None, historical_stress_pnl=None,
                snapshot_sweeps=market, synthetic_stress=synthetic)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("--run required; the protocol and all inputs must already be committed")
    frozen, inputs = verify_inputs()
    out = LANE / "results"
    out.mkdir(exist_ok=False)  # also preserves a failed sole attempt
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (out / "started.json").write_text(json.dumps(dict(prereg_sha256=frozen, commit=head), indent=2) + "\n")
    report = measure(json.loads((LANE / "cases.json").read_text()))
    verify_inputs()
    report["prereg_sha256"] = frozen
    report["frozen_commit"] = head
    report["inputs"] = inputs
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps(dict(registry_id="R417", snapshot_groups=len(report["snapshot_sweeps"]),
                         synthetic_worlds=len(report["synthetic_stress"]), predictive_trials=0,
                         program_trials=report["program_trials"]), sort_keys=True))


if __name__ == "__main__":
    main()
