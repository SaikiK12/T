"""The project's one panel: docs/PANEL.md, rebuilt from the registry, the methods queue and the forward lanes' status
files at the end of every tick. Read-only on everything else; it never decides anything a lane's PREREG decides.

usage: python scripts/panel.py
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import registry  # noqa: E402

OUT = ROOT / "docs" / "PANEL.md"
EXP = ROOT / "experiments"
from lab.operations import OBJECTIVE
# forward lanes: (registry id, lane, status file, {book key: label}, what decides it)
from lab.operations import LANES

FORWARD = [(l.rid, l.path, "journal/status.json", dict(l.books) or {"summary": l.what}, l.rule)
           for l in LANES]
WAITING = [
    "Answered 2026-10-20: every public download approved (\"we need all data possible\"); execution mode both"
    " (manual-web and API, labelled per lane); tiny live calibration orders: not yet; R263 runs once offline.",
    "Install PyTorch CPU and the Kronos-small weights (about 300 MB): R227 Kronos lane (PR #9).",
    "Rotate the two Coinalyze API keys pasted into the old session's chat (`docs/OLD_SESSION_EDGES.md`, security note).",
    "Set the stake and max loss for gate 4 (`docs/GATES.md`; the lab only proposes 2% of trading capital per book and a"
    " stop at 25% of the stake).",
    "Review and integration: [current open PRs](https://github.com/SaikiK12/T/pulls); check each dependency and blocker.",
]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def read_json(p):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def pct(x):
    return "-" if x is None else f"{x * 100:+.1f}%"


def forward_rows():
    from lab.operations import forward_days, forward_lanes
    rows = forward_lanes(ROOT, forward_days(ROOT), time.time())
    return pd.DataFrame([{"lane": f"{r['round']} {r['lane']}", "scope": r["what"],
                          "observations": f"{r['scored'] if r['scored'] is not None else 'unknown'} / {r['needed']} {r['unit']}",
                          "on-time 1x": pct(None if r["net_pct"] is None else r["net_pct"] / 100),
                          "2x / 3x": f"{pct(None if r['net_2x_pct'] is None else r['net_2x_pct']/100)} / "
                                     f"{pct(None if r['net_3x_pct'] is None else r['net_3x_pct']/100)}",
                          "decided by": r["decision"], "gate": r["gate_eligibility"]} for r in rows])


def methods():
    p = ROOT / "registry" / "methods.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, keep_default_na=False, dtype=str)


def table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(v).replace("|", "/") for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-state-dir", type=Path)
    args = parser.parse_args(argv)
    reg = pd.read_csv(ROOT / "registry" / "rounds.csv", keep_default_na=False)
    trials = registry.program_trials(ROOT / "registry" / "rounds.csv")
    verdicts = reg.verdict.value_counts().to_dict()
    lag = read_json(EXP / "forward_lag" / "status.json")
    m = methods()
    L = [f"# Panel", "", f"Rebuilt {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} by `scripts/panel.py` at the end "
         "of each tick. Do not edit by hand.", "", f"**Objective.** {OBJECTIVE}", "",
         "## How we proceed (owner-approved direction, 2026-10-20: [DIRECTION](DIRECTION.md))", "",
         "Configured workflow (actual completion is reported separately):",
         "1. `scripts/forward_all.sh` delegates to `scripts/orchestrate_forward.py` with the shared catalog in "
         "`lab/operations.py`: point-in-time recorders (MEXC funding and ticker, notices, unlock"
         " calendar), every forward paper lane, the lag report, this panel and the recorder digests.",
         "2. Background jobs (family runs, downloads) are checked; a finished one gets FINDINGS at 1x/2x/3x of its"
         " execution mode's cost and a registry row with its full trial count.",
         "3. Breadth through families: strategies from the queue and the quant literature run as one frozen PREREG per"
         " family (all variants, reality check or SPA, random null), in the background. A null is evidence.",
         "4. Family survivors go to scheduled batch reads of the reserved samples (2020 crypto, MEXC-only coins; GATES"
         " \"Reserved samples\"). A batch pass becomes one frozen forward paper lane (gate 1), labelled manual-web or API."
         " Real money only after gates 1-3, placed by the owner (gate 4).",
         "5. Read the room (issue #7), commit and push.", "",
         "Writers: fresh claims in [room #7](https://github.com/SaikiK12/T/issues/7) determine ownership. "
         "A registry status or running process does not establish complete prospective evidence.", "",
         "## 1. The funnel", "",
         "Screen (gate 0, exploratory) → research on unseen days (gate 1) → execution on MEXC (gate 2, `go_real` here) →"
         " account risk (gate 3) → the owner (gate 4). Rules and dates: [GATES](GATES.md); what the critics found:"
         " [CRITIQUE](CRITIQUE.md).", ""]
    funnel = [("Ideas in the queue, untested", "-" if m is None else str((m.status == "UNTESTED").sum())),
              ("Ideas partly tested", "-" if m is None else str((m.status == "PARTIAL").sum())),
              ("Ideas blocked (data, download, compute)", "-" if m is None else str((m.status == "BLOCKED").sum())),
              ("Rounds in the registry", f"{len(reg)} ({', '.join(f'{k} {v}' for k, v in verdicts.items())})"),
              ("Program trials", f"{trials:,}"),
              ("Paper lanes registered RUNNING/ARMED (process activity unverified)",
               str(reg[reg.id.isin([l.rid for l in LANES])].status.isin(["RUNNING", "ARMED"]).sum())),
              ("Strict on-time paper days so far", str(lag.get("strict_ontime_days", "unknown"))),
              ("Gate eligibility", "not assessed by this panel; see frozen lane evidence and GATES"),
              ("Next decision", "observation-count dependent; each frozen lane specifies its looks")]
    L += [table(pd.DataFrame(funnel, columns=["stage", "now"])), ""]
    L += ["## 2. Forward paper lanes (the only road to money)", "",
          "Replay, late and on-time observations remain distinct. Lane-native decisions do not establish current gate eligibility.", "",
          table(forward_rows()), ""]
    if lag:
        h = lag.get("ontime_hour_lag_min", {})
        L += [f"Processing lag of on-time hours: {h.get('n', 0)} hours, median {h.get('median', '-')} min, max "
              f"{h.get('max', '-')} min; days with late hours: {', '.join(lag.get('ontime_days_with_late_hours', [])) or 'none'}.",
              ""]
    from scripts.dashboard_jobs import build_jobs
    jobs = build_jobs(ROOT, state_dir=args.jobs_state_dir)
    L += ["### Execution receipts", "", "Process state, declared data checks and statistical eligibility are separate.", "",
          table(pd.DataFrame([{k: r.get(k) for k in ("task_id", "category", "state", "data_state", "run_id")}
                              for r in jobs])), ""]
    L += ["## 3. Next in the queue", ""]
    if m is None:
        L += ["`registry/methods.csv` is not built yet.", ""]
    else:
        todo = m[m.status.isin(["UNTESTED", "PARTIAL", "QUEUED"])].head(12)
        L += [table(todo[[c for c in ("id", "method", "data_held", "status", "cheap", "note") if c in todo.columns]]), ""]
    L += ["## 4. Waiting on the owner", ""] + [f"- {w}" for w in WAITING] + [""]
    last = reg.tail(8)[["id", "lane", "status", "verdict", "trials"]]
    L += ["## 5. Latest rounds", "", table(last), "",
          "Details: [MAP](MAP.md), [EDGE_SCOREBOARD](EDGE_SCOREBOARD.md), [METHODS_QUEUE](METHODS_QUEUE.md), "
          "[GATES](GATES.md), [CRITIQUE](CRITIQUE.md), "
          "[room #7](https://github.com/SaikiK12/T/issues/7).", ""]
    OUT.write_text("\n".join(L))
    log(f"panel: {len(reg)} rounds, {trials:,} trials, queue {'-' if m is None else len(m)}")


if __name__ == "__main__":
    main()
