"""R422 priority paper runtime; immutable R420 state primitives, new frozen adapter."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.runtime_takeover import restore, snapshot, single_writer  # noqa: E402
from lab.runtime_transport import TransportStop  # noqa: E402
from lab.paper_transport import fence  # noqa: E402
from scripts import quant_runtime as previous  # noqa: E402

LANE = ROOT / "experiments/paper_priority_v1"
OPS = "data/operations/quant_priority_v1"
LEGACY = "data/operations/quant_takeover_v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(root=ROOT):
    root = Path(root)
    lane = root / "experiments/paper_priority_v1"
    sha = prereg.verify(lane / "PREREG.md")
    path = lane / "inputs.json"
    if digest(path) + "  experiments/paper_priority_v1/inputs.json" not in (lane / "PREREG.md").read_text():
        raise ValueError("unfrozen priority manifest")
    files = json.loads(path.read_text())["sha256"]
    for p, wanted in files.items():
        if digest(root / p) != wanted:
            raise ValueError("priority input drift: " + p)
    paths = [*files, "experiments/paper_priority_v1/inputs.json", "experiments/paper_priority_v1/PREREG.md",
             "experiments/paper_priority_v1/PREREG.sha256"]
    for p in paths:
        if subprocess.check_output(["git", "show", "HEAD:" + p], cwd=root) != (root / p).read_bytes():
            raise ValueError("priority input not committed: " + p)
    return sha, files


def run_child(root, script, args, policy_name, log, timeout, invoke):
    cmd = [sys.executable, str(Path(root) / "scripts/quant_runtime_v2.py"), "child", script, policy_name, "--", *args]
    with Path(log).open("x") as f:
        try:
            result = invoke(cmd, cwd=root, stdout=f, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            return dict(state="PROCESS_OK" if result.returncode == 0 else "FAILED", returncode=result.returncode)
        except subprocess.TimeoutExpired:
            return dict(state="FAILED_TIMEOUT")


def inherited_fence(folder, policy):
    return fence(folder, policy, baseline=ROOT / LEGACY / "network/aux/requests.jsonl",
                 frozen_baseline=LANE / "baseline_aux_requests.jsonl")


def compose():
    # New registered composition, no edit to the imported immutable source file.
    # Its state/checkpoint/restore algorithms remain the same; the lane, child
    # command, verifier and HTTP content transport are explicit R422 bindings.
    previous.OPS = OPS
    previous.LANE = LANE
    previous.verify = verify
    previous.run_child = run_child
    previous.fence = inherited_fence


def migrate(config, state, run_id):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("only the serialized Actions writer may migrate")
    with single_writer(ROOT):
        sha, frozen = verify()
        authority = restore(ROOT, state, config, frozen)
        if authority.get("active_contract") == "R422":
            return dict(state="ALREADY_ACTIVE", active_contract="R422")
        if authority.get("active_contract") != "R420":
            raise ValueError("unexpected previous active contract")
        events = [json.loads(x) for x in (ROOT / LEGACY / "dispatch.jsonl").read_text().splitlines()]
        if not events or events[-1]["event"] != "FINISHED":
            raise ValueError("unfinished legacy host; no migration/retry of unknown spend")
        raw = (ROOT / LEGACY / "network/aux/requests.jsonl").read_bytes()
        if not raw.startswith((LANE / "baseline_aux_requests.jsonl").read_bytes()):
            raise ValueError("legacy budget diverged from registered baseline")
        # No HTTP. Activate and publish this migration before preparing any hour.
        authority.update(active_contract="R422", previous_contract="R420",
                         priority_prereg_sha256=sha,
                         meaning="R422 selected; native task receipts, source stops and inherited budget determine health")
        (Path(state) / "manifest.json").write_text(json.dumps(authority, indent=2, sort_keys=True) + "\n")
        folder = ROOT / OPS / "migrations"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (run_id + ".json")
        record = dict(state="MIGRATED_NEEDS_REMOTE_COMMIT", previous_contract="R420", active_contract="R422",
                      utc=datetime.now(timezone.utc).isoformat(), prereg_sha256=sha,
                      legacy_budget_sha256=hashlib.sha256(raw).hexdigest(), source_http_requests=0)
        with path.open("x") as f:
            f.write(json.dumps(record, indent=2) + "\n")
        (Path(state) / "restore_ok.json").write_text(json.dumps(dict(source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())) + "\n")
        snapshot(ROOT, state, config, report=path.relative_to(ROOT).as_posix())
        return record


def child(script, policy, args, config):
    # Preserve an already successful legacy paper attempt in this UTC hour.
    # Native R419 itself enforces its source-hour guard and is never intercepted.
    if policy != "r419":
        old = ROOT / LEGACY / "latest.json"
        if old.exists():
            r = json.loads(old.read_text())
            hour = datetime.now(timezone.utc).strftime("%Y%m%dT%H")
            task = next((x for x in config["tasks"] if x["script"] == script and x["policy"] == policy
                         and x.get("args", []) == args), None)
            if task and r.get("hour") == hour and any(t["id"] == task["id"] and t["state"] == "PROCESS_OK"
                                                     for t in r.get("tasks", [])):
                print("LEGACY_PAPER_HOUR_ALREADY_ATTEMPTED; no HTTP or journal write")
                return
    previous.child(script, policy, args, config)


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
        if a.mode in ("migrate", "prepare", "run", "snapshot"):
            if os.environ.get("GITHUB_ACTIONS") != "true":
                raise ValueError("only the serialized Actions writer may write priority state")
            active = json.loads((a.state_dir / "manifest.json").read_text()).get("active_contract")
            if a.mode != "migrate" and active != "R422":
                print(json.dumps(dict(state="INACTIVE_CONTRACT", active_contract=active)))
                return 0
        if a.mode == "plan":
            result = dict(state="INACTIVE_PLAN", inventory=previous.inventory(config), tasks=config["tasks"])
        elif a.mode == "migrate":
            result = migrate(config, a.state_dir, a.run_id)
        elif a.mode == "child":
            if len(a.rest) < 2:
                raise ValueError("child requires script and policy")
            verify()
            if os.environ.get("GITHUB_ACTIONS") != "true":
                raise ValueError("only the serialized Actions writer may start children")
            child(a.rest[0], a.rest[1], a.rest[2:], config)
            return 0
        elif a.mode == "snapshot":
            verify()
            marker = json.loads((a.state_dir / "restore_ok.json").read_text())
            if marker["source_commit"] != subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip():
                raise ValueError("source changed after restoration")
            result = snapshot(ROOT, a.state_dir, config, report=OPS + "/latest.json")
        else:
            result = (previous.prepare if a.mode == "prepare" else previous.execute)(config, a.state_dir, a.run_id)
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
