"""R425 single source-qualification record; prior plumbing status is disclosed, no network."""
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

LANE = ROOT / "experiments/atomic_v2_routes_v1"


def main():
    frozen = prereg.verify(LANE / "PREREG.md")
    files = json.loads((LANE / "inputs.json").read_text())["sha256"]
    manifest_sha = hashlib.sha256((LANE / "inputs.json").read_bytes()).hexdigest()
    if manifest_sha + "  experiments/atomic_v2_routes_v1/inputs.json" not in (LANE / "PREREG.md").read_text():
        raise ValueError("unfrozen source manifest")
    for p in [*files, "experiments/atomic_v2_routes_v1/inputs.json", "experiments/atomic_v2_routes_v1/PREREG.md", "experiments/atomic_v2_routes_v1/PREREG.sha256"]:
        raw = (ROOT / p).read_bytes()
        if p in files and hashlib.sha256(raw).hexdigest() != files[p]:
            raise ValueError("frozen input drift")
        if subprocess.check_output(["git", "show", "HEAD:" + p], cwd=ROOT) != raw:
            raise ValueError("uncommitted source input")
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    with (out / "RUN_STARTED.json").open("x") as f:
        f.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(), prereg_sha256=frozen)) + "\n")
    source = ROOT / "research/intake/atomic_v2_20261107"
    r = json.loads((source / "chain_id.receipt.json").read_text())
    raw = gzip.decompress((source / r["body"]).read_bytes())
    if hashlib.sha256(raw).hexdigest() != r["sha256"] or len(raw) != r["bytes_read"]:
        raise ValueError("probe receipt drift")
    result = dict(round="R425", status="BLOCKED_ACCESS" if r["status"] != 200 or r["error"] else "IDENTITY_ONLY_NOT_MARKET_DATA",
                  prereg_sha256=frozen, original_probe_status_known_before_freeze=True,
                  source_status=r["status"], public_chain_identity_qualified=False,
                  market_reserve_rows=0, net_pnl=None, costs={"1x": "N/A", "2x": "N/A", "3x": "N/A"},
                  program_trials=registry.program_trials(ROOT / "registry/rounds.csv"), predictive_trials=0,
                  source_calls_during_this_verification=0, no_denial_retry=True,
                  meaning="Integrity/classification of the disclosed earlier metadata-only denial, not a blinded market experiment or economic NULL")
    with (out / "report.json").open("x") as f:
        f.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
