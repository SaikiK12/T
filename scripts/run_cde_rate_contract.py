"""R423 one-run exact Advanced/MDA field qualification; no return or rate summary."""
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
from lab.cde_rate_contract import evaluate  # noqa: E402
from lab.eea_pair_capture import SOURCES, schema_counts  # noqa: E402

LANE = ROOT / "experiments/cde_rate_contract_v1"
INTAKE = ROOT / "research/intake/funding_notional_20261103/cde_rate_contract_20261107"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    frozen = prereg.verify(LANE / "PREREG.md")
    manifest = LANE / "inputs.json"
    if sha(manifest) + "  experiments/cde_rate_contract_v1/inputs.json" not in (LANE / "PREREG.md").read_text():
        raise ValueError("unfrozen rate-contract manifest")
    files = json.loads(manifest.read_text())["sha256"]
    for path, wanted in files.items():
        if sha(ROOT / path) != wanted:
            raise ValueError("frozen input drift: " + path)
    for path in [*files, "experiments/cde_rate_contract_v1/inputs.json",
                 "experiments/cde_rate_contract_v1/PREREG.md", "experiments/cde_rate_contract_v1/PREREG.sha256"]:
        if subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT) != (ROOT / path).read_bytes():
            raise ValueError("rate-contract input not committed")
    return frozen


def inputs(cfg):
    source = LANE / "source"
    manifest = json.loads((LANE / "source_manifest.json").read_text())
    if manifest["hours"] != cfg["hours"]:
        raise ValueError("fixed source-hour selection drift")
    for path, wanted in manifest["sha256"].items():
        if sha(source / path) != wanted:
            raise ValueError("original source copy changed")
    events = [json.loads(x) for x in (source / "requests.jsonl").read_text().splitlines()]
    starts = {r["request_id"]: r for r in events if r["event"] == "START"}
    ends = {r["request_id"]: r for r in events if r["event"] == "END"}
    observations, histories = {}, {}
    for coin, instrument in cfg["instruments"].items():
        observations[coin] = []
        for stamp in cfg["hours"]:
            packet = json.loads((source / "packets" / stamp / "packet.json").read_text())
            if packet["state"] != "CAPTURED" or packet["hour"] != stamp:
                raise ValueError("incomplete/wrong native packet")
            name = coin + "_cde_product"
            start, end = starts[stamp + "/" + name], ends[stamp + "/" + name]
            raw = gzip.decompress((source / "packets" / stamp / (name + ".body.gz")).read_bytes())
            if (start["url"] != SOURCES[name] or end["status"] != 200 or end["error"]
                    or not end["response_complete"] or len(raw) != end["bytes_read"]
                    or hashlib.sha256(raw).hexdigest() != end["body_sha256"]):
                raise ValueError("native metadata receipt mismatch")
            obj = json.loads(raw, parse_float=str)
            schema_counts(name, obj)
            f = obj["future_product_details"]
            observations[coin].append(dict(source_hour=stamp, funding_time=f["funding_time"],
                                           funding_rate=f["funding_rate"], received_utc_ns=end["received_utc_ns"]))
        receipt = json.loads((INTAKE / (coin + ".receipt.json")).read_text())
        raw = gzip.decompress((INTAKE / receipt["body"]).read_bytes())
        expected_url = f"https://www.coinbase.com/api/mda/v1/instruments/CDE/{instrument['mda']}/funding?result_limit=32"
        if (receipt["url"] != expected_url or receipt["status"] != 200 or receipt["error"]
                or not receipt["response_complete"] or len(raw) != receipt["bytes_read"]
                or hashlib.sha256(raw).hexdigest() != receipt["sha256"]):
            raise ValueError("public MDA tail receipt mismatch")
        histories[coin] = json.loads(raw, parse_float=str)["results"]
    return observations, histories


def main():
    frozen = verify()
    folder = LANE / "results"
    folder.mkdir(exist_ok=True)
    with (folder / "RUN_STARTED.json").open("x") as f:
        f.write(json.dumps(dict(prereg_sha256=frozen, started_utc=datetime.now(timezone.utc).isoformat(),
                               commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())) + "\n")
    try:
        cfg = json.loads((LANE / "cases.json").read_text())
        observations, histories = inputs(cfg)
        assets = {coin: evaluate(observations[coin], histories[coin], symbol=s["mda"], required=len(cfg["hours"]))
                  for coin, s in cfg["instruments"].items()}
        result = dict(round="R423", prereg_sha256=frozen, predictive_trials=0,
                      program_trials=registry.program_trials(ROOT / "registry/rounds.csv"), assets=assets,
                      verdict="SAMPLED_CONTRACT_PASS" if all(x["verdict"] == "SAMPLED_FIELD_CONSISTENT" for x in assets.values())
                      else "UNQUALIFIED_SAMPLED_CONTRACT", pnl=None, funding_cash=None,
                      historic_or_broker_cash_certified=False, actual_fills=False,
                      scope="Exact same-time raw-field identity on fixed eight source hours; no fitted scale/time shift")
        verify()
        with (folder / "report.json").open("x") as f:
            f.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps(dict(verdict=result["verdict"], assets={k: {a: v[a] for a in
                         ['verdict', 'observations', 'exact_matches', 'missing_final_rows', 'mismatches']}
                         for k, v in assets.items()}, report_sha256=sha(folder / "report.json"))))
    except BaseException as exc:
        with (folder / "ERROR.json").open("x") as f:
            f.write(json.dumps(dict(error=type(exc).__name__ + ": " + str(exc))) + "\n")
        raise


if __name__ == "__main__":
    main()
