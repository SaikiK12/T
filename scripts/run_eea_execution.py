"""R421: one frozen packet, two explicit CDE size conventions, no new acquisition."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402
from lab.carry_execution import number  # noqa: E402
from lab.eea_execution import normalize, execution_case  # noqa: E402
from lab.eea_pair_capture import SOURCES, schema_counts  # noqa: E402

LANE = ROOT / "experiments/eea_execution_v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    sha = prereg.verify(LANE / "PREREG.md")
    path = LANE / "inputs.json"
    if digest(path) + "  experiments/eea_execution_v1/inputs.json" not in (LANE / "PREREG.md").read_text():
        raise ValueError("unfrozen input manifest")
    files = json.loads(path.read_text())["sha256"]
    for name, wanted in files.items():
        if digest(ROOT / name) != wanted:
            raise ValueError("input drift: " + name)
    names = [*files, path.relative_to(ROOT).as_posix(),
             "experiments/eea_execution_v1/PREREG.md", "experiments/eea_execution_v1/PREREG.sha256"]
    for name in names:
        committed = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=ROOT)
        if committed != (ROOT / name).read_bytes():
            raise ValueError("input not committed: " + name)
    return sha


def load_packet():
    source = LANE / "source"
    manifest = json.loads((LANE / "source_manifest.json").read_text())
    for name, sha in manifest["sha256"].items():
        if digest(source / name) != sha:
            raise ValueError("copied source drift")
    packet = json.loads((source / "packets/20261107T04/packet.json").read_text())
    if packet["state"] != "CAPTURED" or packet["hour"] != "20261107T04":
        raise ValueError("wrong/incomplete source packet")
    events = [json.loads(line) for line in (source / "requests.jsonl").read_text().splitlines()]
    starts = {r["request_id"].split("/", 1)[1]: r for r in events if r["event"] == "START"}
    ends = {r["request_id"].split("/", 1)[1]: r for r in events if r["event"] == "END"}
    bodies, clocks = {}, {}
    for p in sorted((source / "packets/20261107T04").glob("*.body.gz")):
        name = p.name.removesuffix(".body.gz")
        start, end = starts[name], ends[name]
        raw = gzip.decompress(p.read_bytes())
        if (start["url"] != SOURCES[name] or end["status"] != 200 or end["error"]
                or not end["response_complete"] or len(raw) != end["bytes_read"]
                or hashlib.sha256(raw).hexdigest() != end["body_sha256"]):
            raise ValueError("native source receipt mismatch: " + name)
        if end["received_mono_ns"] < start["started_mono_ns"]:
            raise ValueError("source monotonic clock reversed")
        bodies[name] = json.loads(raw, parse_float=str)
        schema_counts(name, bodies[name])
        clocks[name] = {k: end[k] for k in ("received_utc_ns", "received_mono_ns")}
    return bodies, clocks


def main():
    sha = verify()
    # Exclusive marker precedes decoding/measurement and is never removed.
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    with (out / "RUN_STARTED.json").open("x") as f:
        json.dump(dict(prereg_sha256=sha, started_utc=datetime.now(timezone.utc).isoformat(),
                       commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()), f)
        f.write("\n")
    try:
        cfg = json.loads((LANE / "cases.json").read_text())
        bodies, clocks = load_packet()
        rows = []
        for coin, spec in cfg["instruments"].items():
            instrument = next(x for x in bodies["kraken_metadata"]["instruments"] if x["symbol"] == spec["kraken"])
            precision = instrument["contractValueTradePrecision"]
            if type(precision) is not int or not 0 <= precision <= 12:
                raise ValueError("Kraken quantity precision")
            lot = number(10) ** -precision
            for unit in cfg["cde_size_units"]:
                for phase, suffix in (("initial", ""), ("delayed", "_delayed")):
                    raw_cde = bodies[coin + "_cde_book" + suffix]
                    raw_kraken = bodies[coin + "_kraken_book" + suffix]
                    # Malformed/empty/locked source remains unqualified. There is
                    # no later fallback depth or assumption of a zero cost.
                    try:
                        cde = normalize(raw_cde, "cde", unit, spec["contract_size"])
                        kraken = normalize(raw_kraken, "kraken", unit, spec["contract_size"])
                        error = None
                    except ValueError as exc:
                        error = str(exc)
                    for target in cfg["targets_per_leg"]:
                        for multiple in (1, 2, 3):
                            label = dict(coin=coin, cde_size_unit=unit, phase=phase,
                                         target_per_leg=target, cost_multiple=multiple)
                            if error:
                                rows.append(dict(**label, state="UNQUALIFIED_SOURCE", error=error, all_in_cost=None))
                                continue
                            try:
                                measured = execution_case(cde, kraken, target=target,
                                    contract_size=spec["contract_size"], kraken_lot=lot,
                                    multiple=multiple, **cfg["fees"])
                                rows.append({**label, **measured})
                            except ValueError as exc:
                                rows.append(dict(**label, state="UNQUALIFIED_UNIT", error=str(exc), all_in_cost=None))
        report = dict(round="R421", prereg_sha256=sha, program_trials=registry.program_trials(ROOT / "registry/rounds.csv"),
                      state="CONDITIONAL_DEPTH_COST_ONLY", predictive_trials=0, scenarios=rows, source_receipt_clocks=clocks,
                      source_state_commit=json.loads((LANE / "source_manifest.json").read_text())["source_commit"],
                      pnl=None, funding_cash=None, actual_fills=False, executable_capacity_admitted=False,
                      owner_access_verified=False, margin_admitted=False,
                      scope="One sequential packet; two raw CDE quantity hypotheses; instantaneous round trip is a cost proxy, not a future exit or a return")
        verify()
        with (out / "report.json").open("x") as f:
            f.write(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps(dict(round="R421", state=report["state"], scenarios=len(rows), report_sha256=digest(out / "report.json"))))
    except BaseException as exc:
        with (out / "ERROR.json").open("x") as f:
            json.dump(dict(error=type(exc).__name__ + ": " + str(exc)), f)
            f.write("\n")
        raise


if __name__ == "__main__":
    main()
