"""R428 counts-only native participant windows; no local recorder or PnL reader."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.participant_capture import capture, choose_slot, inherited_source_block, SourceStop  # noqa: E402
from scripts.quant_runtime_v3 import OPS, verify  # noqa: E402

LANE = ROOT / "experiments/participant_capture_v1"
FOLDER = ROOT / "data/recorders/participant_windows_v1"


def guard():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("only selected serialized Actions may record these windows")
    verify()
    state = ROOT / ".runtime-state"
    authority = json.loads((state / "manifest.json").read_text())
    if authority.get("active_contract") != "R428":
        raise ValueError("participant source is not the selected contract")
    if inherited_source_block((ROOT / OPS / "aux_baseline.jsonl").read_bytes()):
        raise SourceStop("inherited Lighter denial; new composition cannot retry it")
    run_id = "gha_" + os.environ["GITHUB_RUN_ID"] + "_" + os.environ["GITHUB_RUN_ATTEMPT"]
    events = [json.loads(x) for x in (ROOT / OPS / "dispatch.jsonl").read_text().splitlines()]
    if not events or events[-1]["event"] != "RUNNING" or events[-1]["run_id"] != run_id:
        raise ValueError("no selected running writer")
    # Paper work can finish after an hour boundary; the published reservation
    # remains the parent run's checkpoint, never an invented new-hour slot.
    hour = events[-1]["hour"]
    path = ROOT / OPS / "runs" / hour / "reservation.json"
    raw = path.read_bytes()
    if json.loads(raw)["run_id"] != run_id:
        raise ValueError("no own prepared source checkpoint")
    remote = subprocess.check_output(["git", "show", "HEAD:state/" + path.relative_to(ROOT).as_posix()], cwd=state)
    if remote != raw:
        raise ValueError("source reservation not published before HTTP/WS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = json.loads((LANE / "capture.json").read_text())
    now = datetime.now(timezone.utc)
    slot = choose_slot(config, now)
    if not args.execute:
        print(json.dumps(dict(state="INACTIVE_PLAN", eligible_slot=slot, source_calls=0, pnl=None)))
        return 0
    try:
        guard()
        if slot is None:
            print(json.dumps(dict(state="OUTSIDE_FROZEN_WINDOWS", source_calls=0, pnl=None)))
            return 0
        result = asyncio.run(capture(FOLDER, config, slot))
    except SourceStop as exc:
        print(json.dumps(dict(state="SOURCE_BLOCKED_OR_UNKNOWN", reason=str(exc), source_calls=0)))
        return 42
    print(json.dumps(result))
    return 42 if result["state"] == "SOURCE_STOP" else 0


if __name__ == "__main__":
    raise SystemExit(main())
