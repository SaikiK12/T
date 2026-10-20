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
OBJECTIVE = ("The best net PnL from any method in any market the owner can trade: MEXC perpetuals first, then spot, "
             "prop challenges, forex and index futures as data allows. Search wide (every method is tested, a null is "
             "evidence); trust narrow (only days nobody had seen when the rule was frozen count). Money moves only "
             "through the four gates in `docs/GATES.md`, at stakes the owner sets.")
# forward lanes: (registry id, lane, status file, {book key: label}, what decides it)
FORWARD = [
    ("R215", "mexc_fwd", "journal/status.json", {"A": "flow book A on MEXC", "B": "top-vs-crowd on MEXC"},
     "R221 looks at 90 / 182 / 365 on-time days"),
    ("R218", "mexc_fwd_sq", "journal/status.json", {"X2": "flow book X2 (k squared) on MEXC"},
     "R221 looks at 90 / 182 / 365 on-time days"),
    ("R220", "carry_fwd", "journal/status.json", {"MEXC": "funding carry, MEXC", "BIN": "funding carry, Binance"},
     "90 on-time days through go_real"),
    ("R200", "flow72_fwd2", "journal/status.json", {"A": "flow book A, Binance", "B": "top-vs-crowd, Binance"},
     "90 scored days through go_real plus NW t >= 2"),
    ("R214", "flow72_fwd3", "journal/status.json", {"A": "A one bar late", "B": "B one bar late"},
     "same days as R200, a delay check"),
]
WAITING = [
    "Answered 2026-10-20: every public download approved (\"we need all data possible\"); execution mode both"
    " (manual-web and API, labelled per lane); tiny live calibration orders: not yet; R263 runs once offline.",
    "Install PyTorch CPU and the Kronos-small weights (about 300 MB): R227 Kronos lane (PR #9).",
    "Rotate the two Coinalyze API keys pasted into the old session's chat (`docs/OLD_SESSION_EDGES.md`, security note).",
    "Set the stake and max loss for gate 4 (`docs/GATES.md`; the lab only proposes 2% of trading capital per book and a"
    " stop at 25% of the stake).",
    "Review and integration: [current open PRs](https://github.com/SaikiK12/T/pulls); each PR states its dependencies and blockers.",
]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def read_json(p):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def pct(x):
    return "-" if x is None else f"{x * 100:+.1f}%"


def r200_split(book):
    """R200's tickets for one book, split by its `late` flag (days before its freeze) into replay and on-time."""
    p = EXP / "flow72_fwd2" / "journal" / "tickets.csv"
    if not p.exists():
        return {}, {}
    tk = pd.read_csv(p)
    tk = tk[tk.book == book]
    part = lambda x: {"days": len(x), "total": float(x.net.sum()), "total_2x": float(x.net_2x.sum()),
                      "total_3x": float(x.net_3x.sum())} if len(x) else {}
    return part(tk[tk.late == 1]), part(tk[tk.late == 0])


def forward_rows():
    rows = []
    for rid, lane, f, books, decides in FORWARD:
        s = read_json(EXP / lane / f)
        for key, label in books.items():
            rep = s.get(f"{key}_replay") or (s.get(key) or {}).get("replay") or {}
            on = s.get(f"{key}_ontime") or (s.get(key) or {}).get("ontime") or {}
            if lane == "flow72_fwd2":                   # R200 keeps one series per book; its `late` flag splits it
                rep, on = r200_split(key)
            rows.append({"lane": f"{rid} {lane}", "book": label, "replay": f"{rep.get('days', 0)} d {pct(rep.get('total'))}",
                         "on_time": f"{on.get('days', 0)} d {pct(on.get('total'))}" if on else "0 d",
                         "2x / 3x": f"{pct(on.get('total_2x'))} / {pct(on.get('total_3x'))}" if on else "-",
                         "decided by": decides})
    return pd.DataFrame(rows)


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


def main():
    reg = pd.read_csv(ROOT / "registry" / "rounds.csv", keep_default_na=False)
    trials = registry.program_trials(ROOT / "registry" / "rounds.csv")
    verdicts = reg.verdict.value_counts().to_dict()
    lag = read_json(EXP / "forward_lag" / "status.json")
    m = methods()
    L = [f"# Panel", "", f"Rebuilt {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} by `scripts/panel.py` at the end "
         "of each tick. Do not edit by hand.", "", f"**Objective.** {OBJECTIVE}", "",
         "## How we proceed (owner-approved direction, 2026-10-20: [DIRECTION](DIRECTION.md))", "",
         "Every tick:",
         "1. `scripts/forward_all.sh` runs the point-in-time recorders (MEXC funding and ticker, notices, unlock"
         " calendar), every forward paper lane, the lag report, this panel and the recorder digests.",
         "2. Background jobs (family runs, downloads) are checked; a finished one gets FINDINGS at 1x/2x/3x of its"
         " execution mode's cost and a registry row with its full trial count.",
         "3. Breadth through families: strategies from the queue and the quant literature run as one frozen PREREG per"
         " family (all variants, reality check or SPA, random null), in the background. A null is evidence.",
         "4. Family survivors go to scheduled batch reads of the reserved samples (2020 crypto, MEXC-only coins; GATES"
         " \"Reserved samples\"). A batch pass becomes one frozen forward paper lane (gate 1), labelled manual-web or API."
         " Real money only after gates 1-3, placed by the owner (gate 4).",
         "5. Read the room (issue #7), commit and push.", "",
         "Roles: Claude and Codex claim current work in [room #7](https://github.com/SaikiK12/T/issues/7). "
         "No subagents and no Workflows (owner, 2026-10-20).", "",
         "## 1. The funnel", "",
         "Screen (gate 0, exploratory) → research on unseen days (gate 1) → execution on MEXC (gate 2, `go_real` here) →"
         " account risk (gate 3) → the owner (gate 4). Rules and dates: [GATES](GATES.md); what the critics found:"
         " [CRITIQUE](CRITIQUE.md).", ""]
    funnel = [("Ideas in the queue, untested", "-" if m is None else str((m.status == "UNTESTED").sum())),
              ("Ideas partly tested", "-" if m is None else str((m.status == "PARTIAL").sum())),
              ("Ideas blocked (data, download, compute)", "-" if m is None else str((m.status == "BLOCKED").sum())),
              ("Rounds in the registry", f"{len(reg)} ({', '.join(f'{k} {v}' for k, v in verdicts.items())})"),
              ("Program trials", f"{trials:,}"),
              ("Forward paper lanes running", str((reg.status == "RUNNING").sum() + 1)),
              ("Strict on-time paper days so far", str(lag.get("strict_ontime_days", 0))),
              ("Passed gate 1 (unseen days)", "none yet"),
              ("Next decision date", "2027-01-18: first 90-on-time-day looks (R215, R218, R220, R221 futility)")]
    L += [table(pd.DataFrame(funnel, columns=["stage", "now"])), ""]
    L += ["## 2. Forward paper lanes (the only road to money)", "",
          "Replay days were scored after the freeze on days the archive did not hold; on-time days are the evidence.", "",
          table(forward_rows()), ""]
    if lag:
        h = lag.get("ontime_hour_lag_min", {})
        L += [f"Processing lag of on-time hours: {h.get('n', 0)} hours, median {h.get('median', '-')} min, max "
              f"{h.get('max', '-')} min; days with late hours: {', '.join(lag.get('ontime_days_with_late_hours', [])) or 'none'}.",
              ""]
    L += ["## 3. Next in the queue", ""]
    if m is None:
        L += ["`registry/methods.csv` is not built yet.", ""]
    else:
        todo = m[m.status.isin(["UNTESTED", "PARTIAL"])].head(12)
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
