"""R428 serialized participant-source composition; preserve old paper journals, budgets and windows."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.paper_transport import fence  # noqa: E402
from lab.runtime_takeover import restore, snapshot, single_writer  # noqa: E402
from lab.runtime_transport import TransportStop  # noqa: E402
from scripts import quant_runtime as base  # noqa: E402

LANE = ROOT / "experiments/participant_capture_v1"
OPS = "data/operations/quant_participant_v1"
OLD_OPS = "data/operations/quant_priority_v1"
LEGACY = "data/operations/quant_takeover_v1"
NATIVE_CHILD = base.child
NATIVE_INVENTORY = base.inventory


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(root=ROOT):
    root = Path(root)
    lane = root / "experiments/participant_capture_v1"
    sha = prereg.verify(lane / "PREREG.md")
    manifest = lane / "inputs.json"
    if digest(manifest) + "  experiments/participant_capture_v1/inputs.json" not in (lane / "PREREG.md").read_text():
        raise ValueError("unfrozen participant-runtime manifest")
    files = json.loads(manifest.read_text())["sha256"]
    for name, wanted in files.items():
        if digest(root / name) != wanted:
            raise ValueError("participant-runtime frozen input drift: " + name)
    paths = [*files, "experiments/participant_capture_v1/inputs.json", "experiments/participant_capture_v1/PREREG.md",
             "experiments/participant_capture_v1/PREREG.sha256"]
    for name in paths:
        if subprocess.check_output(["git", "show", "HEAD:" + name], cwd=root) != (root / name).read_bytes():
            raise ValueError("participant-runtime input not committed: " + name)
    return sha, files


def combined_baseline(legacy, priority, frozen_legacy, frozen_priority):
    if legacy != frozen_legacy:
        raise ValueError("inactive R420 ledger changed; reconcile before migration")
    if not priority.startswith(frozen_priority):
        raise ValueError("R422 ledger diverged from the frozen prefix")
    for raw in (legacy, priority, frozen_legacy, frozen_priority):
        if not raw or not raw.endswith(b"\n"):
            raise ValueError("missing/cut inherited ledger; no reset")
        for line in raw.splitlines():
            json.loads(line)
    joined = legacy + priority
    starts = [str(x["id"]) for x in map(json.loads, joined.splitlines()) if x.get("event") == "START"]
    if len(set(starts)) != len(starts):
        raise ValueError("overlapping inherited source request IDs")
    return joined


def inherited_fence(folder, policy):
    return fence(folder, policy, baseline=ROOT / OPS / "aux_baseline.jsonl",
                 frozen_baseline=LANE / "aux_baseline_at_registration.jsonl")


def run_child(root, script, args, policy_name, log, timeout, invoke):
    cmd = [sys.executable, str(Path(root) / "scripts/quant_runtime_v3.py"), "child", script, policy_name, "--", *args]
    with Path(log).open("x") as f:
        try:
            result = invoke(cmd, cwd=root, stdout=f, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            return dict(state="PROCESS_OK" if result.returncode == 0 else "FAILED", returncode=result.returncode)
        except subprocess.TimeoutExpired:
            return dict(state="FAILED_TIMEOUT")


def inventory(config):
    return NATIVE_INVENTORY(config) + [dict(id="R428", state="ADMITTED", reason="Finite counts-only participant windows")]


def compose():
    # Explicit new frozen bindings; no file in the old contracts is edited.
    base.OPS, base.LANE = OPS, LANE
    base.verify, base.run_child, base.fence, base.inventory = verify, run_child, inherited_fence, inventory


def paper_already_attempted(report, task_id, hour):
    for task in report.get("tasks", []):
        if task["id"] != task_id or task["state"] != "PROCESS_OK":
            continue
        stamp = task.get("started_utc")
        previous_hour = (datetime.fromisoformat(stamp).astimezone(timezone.utc).strftime("%Y%m%dT%H")
                         if stamp else report.get("hour"))
        if previous_hour == hour:
            return True
    return False


def migrate(config, state, run_id):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("only the selected serialized Actions writer may migrate")
    with single_writer(ROOT):
        sha, frozen = verify()
        authority = restore(ROOT, state, config, frozen)
        if authority.get("active_contract") == "R428":
            return dict(state="ALREADY_ACTIVE", active_contract="R428")
        if authority.get("active_contract") != "R422":
            raise ValueError("unexpected previous active contract")
        events = [json.loads(x) for x in (ROOT / OLD_OPS / "dispatch.jsonl").read_text().splitlines()]
        if not events or events[-1]["event"] != "FINISHED":
            raise ValueError("unfinished previous host; no migration of unknown spend")
        raw = combined_baseline((ROOT / LEGACY / "network/aux/requests.jsonl").read_bytes(),
                                (ROOT / OLD_OPS / "network/aux/requests.jsonl").read_bytes(),
                                (LANE / "legacy_aux_at_registration.jsonl").read_bytes(),
                                (LANE / "priority_aux_at_registration.jsonl").read_bytes())
        folder = ROOT / OPS
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "aux_baseline.jsonl").open("xb") as f:
            f.write(raw)
        authority.update(active_contract="R428", previous_contract="R422", participant_prereg_sha256=sha,
                         meaning="R428 selected; inherited paper spend plus a finite original-budget participant campaign")
        (Path(state) / "manifest.json").write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n")
        record = dict(state="MIGRATED_NEEDS_REMOTE_COMMIT", previous_contract="R422", active_contract="R428",
                      utc=datetime.now(timezone.utc).isoformat(), prereg_sha256=sha,
                      inherited_aux_baseline_sha256=hashlib.sha256(raw).hexdigest(), source_http_requests=0,
                      historical_campaign_reservation=json.loads((LANE / "acquisition_reservation.json").read_text()))
        path = folder / "migrations" / (run_id + ".json")
        path.parent.mkdir(exist_ok=True)
        with path.open("x") as f:
            f.write(json.dumps(record, indent=2) + "\n")
        (Path(state) / "restore_ok.json").write_text(json.dumps(dict(source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())) + "\n")
        snapshot(ROOT, state, config, report=path.relative_to(ROOT).as_posix())
        return record


def child(script, policy, args, config):
    matches = [t for t in config["tasks"] if t["script"] == script and t["policy"] == policy and t.get("args", []) == args]
    if len(matches) != 1:
        raise ValueError("child outside frozen allowlist")
    if policy == "participant":
        verify()
        sys.path.insert(0, str(ROOT / "scripts"))
        sys.argv = [str(ROOT / script), *args]
        runpy.run_path(str(ROOT / script), run_name="__main__")
        return
    if policy != "r419":
        hour = datetime.now(timezone.utc).strftime("%Y%m%dT%H")
        for old in (OPS, OLD_OPS, LEGACY):
            path = ROOT / old / "latest.json"
            if path.exists():
                report = json.loads(path.read_text())
                if paper_already_attempted(report, matches[0]["id"], hour):
                    print("PREDECESSOR_PAPER_HOUR_ALREADY_ATTEMPTED; no HTTP/journal write")
                    return
    NATIVE_CHILD(script, policy, args, config)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", nargs="?", choices=("plan", "migrate", "prepare", "run", "snapshot", "child"), default="plan")
    p.add_argument("rest", nargs="*")
    p.add_argument("--state-dir", type=Path, default=ROOT / ".runtime-state")
    p.add_argument("--run-id", default="manual")
    a = p.parse_args(argv)
    config = json.loads((LANE / "config.json").read_text())
    compose()
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", a.run_id):
            raise ValueError("invalid run id")
        if a.mode != "plan":
            if os.environ.get("GITHUB_ACTIONS") != "true":
                raise ValueError("only the selected serialized Actions writer may write participant/runtime state")
            active = json.loads((a.state_dir / "manifest.json").read_text()).get("active_contract")
            if a.mode != "migrate" and active != "R428":
                print(json.dumps(dict(state="INACTIVE_CONTRACT", active_contract=active)))
                return 0
        if a.mode == "plan":
            result = dict(state="INACTIVE_PLAN", inventory=inventory(config), tasks=config["tasks"])
        elif a.mode == "migrate":
            result = migrate(config, a.state_dir, a.run_id)
        elif a.mode == "child":
            if len(a.rest) < 2:
                raise ValueError("child needs script and policy")
            verify()
            child(a.rest[0], a.rest[1], a.rest[2:], config)
            return 0
        elif a.mode == "snapshot":
            verify()
            marker = json.loads((a.state_dir / "restore_ok.json").read_text())
            if marker["source_commit"] != subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip():
                raise ValueError("source changed after restoration")
            result = snapshot(ROOT, a.state_dir, config, report=OPS + "/latest.json")
        else:
            result = (base.prepare if a.mode == "prepare" else base.execute)(config, a.state_dir, a.run_id)
        print(json.dumps(result, indent=2, default=str))
        return 0
    except TransportStop as exc:
        print("TRANSPORT_STOP: " + str(exc), file=sys.stderr)
        return 42
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
