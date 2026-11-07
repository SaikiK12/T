"""R427 one-run recorded trade-role qualification, without prices, markouts or returns."""
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
from lab.lighter_trade_contract import evaluate  # noqa: E402

LANE = ROOT / "experiments/lighter_trade_contract_v1"
COLUMNS = ["trade_id", "t", "T", "tx_us", "ask_acct", "bid_acct", "maker_ask", "liq", "sz", "tpos", "mpos"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    frozen = prereg.verify(LANE / "PREREG.md")
    manifest = LANE / "inputs.json"
    if sha(manifest) + "  experiments/lighter_trade_contract_v1/inputs.json" not in (LANE / "PREREG.md").read_text():
        raise ValueError("unfrozen role-contract manifest")
    files = json.loads(manifest.read_text())["sha256"]
    for path, wanted in files.items():
        if sha(ROOT / path) != wanted:
            raise ValueError("frozen input drift: " + path)
    for path in [*files, "experiments/lighter_trade_contract_v1/inputs.json",
                 "experiments/lighter_trade_contract_v1/PREREG.md", "experiments/lighter_trade_contract_v1/PREREG.sha256"]:
        if subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT) != (ROOT / path).read_bytes():
            raise ValueError("role-contract input not committed: " + path)
    return frozen


def main():
    frozen = verify()
    folder = LANE / "results"
    folder.mkdir(exist_ok=True)
    with (folder / "RUN_STARTED.json").open("x") as f:
        f.write(json.dumps(dict(prereg_sha256=frozen, started_utc=datetime.now(timezone.utc).isoformat(),
                               commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())) + "\n")
    try:
        import pyarrow.parquet as pq
        cfg = json.loads((LANE / "cases.json").read_text())
        for receipt in json.loads((ROOT / cfg["static_receipts"]).read_text()):
            data = gzip.decompress((ROOT / receipt["body"]).read_bytes())
            if len(data) != receipt["bytes"] or hashlib.sha256(data).hexdigest() != receipt["sha256"]:
                raise ValueError("static source receipt mismatch")
        markets = {}
        for market, case in cfg["markets"].items():
            rows = pq.read_table(ROOT / case["file"], columns=COLUMNS).to_pylist()
            if len(rows) != case["expected_rows"]:
                raise ValueError("registered source count changed")
            markets[market] = evaluate(rows, case["size_decimals"], **cfg["coverage"])
        supported = {x["supported_hypothesis"] for x in markets.values()}
        passed = (all(x["verdict"] == "SAMPLED_ROLE_CONTRACT_PASS" for x in markets.values())
                  and len(supported) == 1 and None not in supported)
        result = dict(round="R427", prereg_sha256=frozen, predictive_trials=0,
                      program_trials=registry.program_trials(ROOT / "registry/rounds.csv"), markets=markets,
                      verdict="SAMPLED_ROLE_CONTRACT_PASS" if passed else "UNQUALIFIED_SAMPLED_ROLE_CONTRACT",
                      supported_hypothesis=next(iter(supported)) if passed else None,
                      costs={"1x": "N/A", "2x": "N/A", "3x": "N/A"}, pnl=None, funding_cash=None,
                      actual_fills=False, complete_feed_certified=False,
                      scope="Exact signed base-position identities under two predeclared role mappings, no prices or PnL")
        verify()
        with (folder / "report.json").open("x") as f:
            f.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps(dict(verdict=result["verdict"], supported_hypothesis=result["supported_hypothesis"],
                              markets={k: {"verdict": v["verdict"], "hypotheses": {h: {a: x[a] for a in
                              ("verdict", "transitions", "accounts", "exact_matches", "mismatches")}
                              for h, x in v["hypotheses"].items()}} for k, v in markets.items()},
                              report_sha256=sha(folder / "report.json"))))
    except BaseException as exc:
        with (folder / "ERROR.json").open("x") as f:
            f.write(json.dumps(dict(error=type(exc).__name__ + ": " + str(exc))) + "\n")
        raise


if __name__ == "__main__":
    main()
