"""One GitHub Actions writer for the paper lab; default is a read-only operational plan."""
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
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.operations import forward_tasks  # noqa: E402
from lab.runtime_takeover import digest, restore, snapshot, health, run_child, single_writer  # noqa: E402
from lab.runtime_transport import fence, TransportStop, append  # noqa: E402

LANE = ROOT/"experiments/ops_takeover_v1"
OPS = "data/operations/quant_takeover_v1"


def verify(root=ROOT):
    lane = Path(root)/"experiments/ops_takeover_v1"
    sha = prereg.verify(lane/"PREREG.md")
    manifest = lane/"inputs.json"
    if digest(manifest)+"  experiments/ops_takeover_v1/inputs.json" not in (lane/"PREREG.md").read_text():
        raise ValueError("unfrozen operations input manifest")
    files = json.loads(manifest.read_text())["sha256"]
    for name, wanted in files.items():
        if digest(Path(root)/name) != wanted:
            raise ValueError("operations input drift: "+name)
    paths = [*files, "experiments/ops_takeover_v1/inputs.json", "experiments/ops_takeover_v1/PREREG.md",
             "experiments/ops_takeover_v1/PREREG.sha256"]
    tracked = set(subprocess.check_output(["git", "ls-files", "-z", "--", *paths], cwd=root).decode().split("\0"))
    if any(p not in tracked for p in paths):
        raise ValueError("operations closure is not committed")
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", *paths], cwd=root, check=True,
                   stdout=subprocess.DEVNULL)
    return sha, files


def inventory(config):
    active = {t["id"] for t in config["tasks"]}
    rows = []
    for t in forward_tasks():
        reason = config["blocked"].get(t.name)
        if t.name not in active and not reason:
            reason = "Not admitted to this bounded takeover; requires source/input qualification before activation"
        rows.append(dict(id=t.name, state="ADMITTED" if t.name in active else "BLOCKED", reason=reason))
    rows.append(dict(id="R419", state="ADMITTED", reason=None))
    return rows


def execute(config, state, run_id):
    with single_writer(ROOT):
        return execute_locked(config, state, run_id)


def restore_state(config, state):
    sha, frozen = verify()
    canonical = restore(ROOT, state, config, frozen)
    (Path(state)/"restore_ok.json").write_text(json.dumps(dict(source_commit=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()))+"\n")
    # A Git checkout is not a fresh FRED observation. Force a real refresh on bootstrap.
    if canonical.get("bootstrap"):
        for lane in ("lockcarry_fwd2", "boroslock_fwd"):
            p = ROOT/"experiments"/lane/"journal/tbill.csv"
            if p.exists():
                os.utime(p, ns=(0, 0))
    return sha


def dispatch_events():
    p = ROOT/OPS/"dispatch.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def prepare(config, state, run_id):
    """Checkpoint an hour before HTTP. A lost predecessor is never silently stolen."""
    with single_writer(ROOT):
        restore_state(config, state)
        now = datetime.now(timezone.utc)
        hour = now.strftime("%Y%m%dT%H")
        events = dispatch_events()
        if events and events[-1]["event"] != "FINISHED":
            raise ValueError("unfinished predecessor; unknown spend must be reconciled before another dispatch")
        folder = ROOT/OPS/"runs"/hour
        if folder.exists():
            return dict(state="HOUR_ALREADY_RESERVED", hour=hour)
        folder.mkdir(parents=True)
        reservation = dict(run_id=run_id, hour=hour, prepared_utc=now.isoformat(),
                           unknown_crash_spend="up to all remaining campaign ceilings; no automatic retry")
        (folder/"reservation.json").write_text(json.dumps(reservation, indent=2)+"\n")
        append(ROOT/OPS/"dispatch.jsonl", dict(event="PREPARED", **reservation))
        snapshot(ROOT, state, config, report=str((folder/"reservation.json").relative_to(ROOT)))
        return dict(state="PREPARED_NEEDS_REMOTE_COMMIT", **reservation)


def execute_locked(config, state, run_id):
    sha = restore_state(config, state)
    now = datetime.now(timezone.utc)
    hour = now.strftime("%Y%m%dT%H")
    folder = ROOT/OPS/"runs"/hour
    if (folder/"report.json").exists():
        return dict(state="HOUR_ALREADY_RESERVED", hour=hour, previous=str(folder.relative_to(ROOT)))
    reservation_path = folder/"reservation.json"
    reservation = json.loads(reservation_path.read_text())
    events = dispatch_events()
    if (reservation["run_id"] != run_id or not events or events[-1]["event"] != "PREPARED"
            or events[-1]["run_id"] != run_id):
        raise ValueError("missing own prepared checkpoint")
    committed = subprocess.check_output(["git", "show", "HEAD:state/"+reservation_path.relative_to(ROOT).as_posix()], cwd=state)
    if committed != reservation_path.read_bytes():
        raise ValueError("reservation must be committed and published before HTTP")
    append(ROOT/OPS/"dispatch.jsonl", dict(event="RUNNING", run_id=run_id, hour=hour))
    report = dict(state="RUNNING", run_id=run_id, hour=hour, started_utc=now.isoformat(),
                  prereg_sha256=sha, code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  inventory=inventory(config), tasks=[], real_orders_allowed=False,
                  predictive_trials=0, costs={"1x": "N/A", "2x": "N/A", "3x": "N/A"})
    path = folder/"report.json"
    path.write_text(json.dumps(report, indent=2)+"\n")
    try:
        for t in config["tasks"]:
            if not config["start"] <= now.isoformat() < config["end"]:
                report["tasks"].append(dict(id=t["id"], state="WINDOW_CLOSED"))
                continue
            if t["id"] == "R419" and now >= datetime(2026, 11, 14, tzinfo=timezone.utc):
                report["tasks"].append(dict(id=t["id"], state="NATIVE_WINDOW_CLOSED"))
                continue
            started = datetime.now(timezone.utc).isoformat()
            result = run_child(ROOT, t["script"], t.get("args", []), t["policy"], folder/(t["id"]+".log"),
                               t["timeout"], subprocess.run)
            verify()
            report["tasks"].append(dict(id=t["id"], started_utc=started, **result))
            path.write_text(json.dumps(report, indent=2)+"\n")
    finally:
        report.update(state="FINISHED_WITH_RESEARCH_BLOCKERS", finished_utc=datetime.now(timezone.utc).isoformat(),
                      health=health(ROOT, config["health_lanes"]), all_project_lanes_running=False,
                      meaning="Process results and receipt freshness only; no new profitability/gate verdict")
        path.write_text(json.dumps(report, indent=2)+"\n")
        (ROOT/OPS/"latest.json").write_text(json.dumps(report, indent=2)+"\n")
        append(ROOT/OPS/"dispatch.jsonl", dict(event="FINISHED", run_id=run_id, hour=hour))
        snapshot(ROOT, state, config, report=str(path.relative_to(ROOT)))
    return report


def child(script, policy_name, args, config):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("Only the serialized GitHub Actions writer may start a live child")
    matches = [t for t in config["tasks"] if t["script"] == script and t["policy"] == policy_name and t.get("args", []) == args]
    if len(matches) != 1:
        raise ValueError("child outside frozen public task allowlist")
    verify()
    sys.path.insert(0, str(ROOT/"scripts"))
    sys.argv = [str(ROOT/script), *args]
    if policy_name == "r419":
        # R419 already has its frozen transport, stops, raw failure bodies and
        # cumulative budgets. Delegate intact instead of intercepting it.
        native = json.loads((ROOT/"experiments/eea_pair_capture_v1/capture.json").read_text())
        ceiling = config["policies"]["r419"]
        for k in ("max_requests", "max_body_bytes"):
            if native[k] > ceiling[k]:
                raise ValueError("R419 native limit exceeds admitted ceiling")
        if max(native["response_cap"], native["metadata_response_cap"]) > ceiling["response_cap"]:
            raise ValueError("R419 response limit exceeds admitted ceiling")
        runpy.run_path(str(ROOT/script), run_name="__main__")
        return
    policy = dict(config["policies"][policy_name], start=config["start"], end=config["end"])
    with fence(ROOT/OPS/"network"/policy_name, policy):
        runpy.run_path(str(ROOT/script), run_name="__main__")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", nargs="?", choices=("plan", "prepare", "run", "snapshot", "child"), default="plan")
    p.add_argument("rest", nargs="*")
    p.add_argument("--state-dir", type=Path, default=ROOT/".runtime-state")
    p.add_argument("--run-id", default="manual")
    a = p.parse_args(argv)
    config = json.loads((LANE/"config.json").read_text())
    try:
        if a.mode in ("prepare", "run", "snapshot"):
            authority = json.loads((a.state_dir/"manifest.json").read_text())
            if authority.get("active_contract") != "R420":
                print(json.dumps(dict(state="INACTIVE_CONTRACT", active_contract=authority.get("active_contract"))))
                return 0
        if a.mode == "plan":
            report = dict(state="INACTIVE_PLAN", inventory=inventory(config), tasks=config["tasks"])
        elif a.mode == "child":
            if len(a.rest) < 2:
                raise ValueError("child requires script and policy")
            child(a.rest[0], a.rest[1], a.rest[2:], config)
            return 0
        elif a.mode == "snapshot":
            verify()
            marker = json.loads((a.state_dir/"restore_ok.json").read_text())
            if marker["source_commit"] != subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip():
                raise ValueError("source changed after canonical restore")
            report = snapshot(ROOT, a.state_dir, config, report=OPS+"/latest.json")
        else:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", a.run_id):
                raise ValueError("invalid workflow run id")
            if os.environ.get("GITHUB_ACTIONS") != "true":
                raise ValueError("Only the serialized GitHub Actions writer may run the takeover")
            report = prepare(config, a.state_dir, a.run_id) if a.mode == "prepare" else execute(config, a.state_dir, a.run_id)
        print(json.dumps(report, indent=2, default=str))
        return 0
    except TransportStop as e:
        print("TRANSPORT_STOP: "+str(e), file=sys.stderr)
        return 42
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as e:
        print(type(e).__name__+": "+str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
