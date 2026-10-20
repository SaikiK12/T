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
    "Download MEXC public history (about 9.4k requests, `scripts/fetch_mexc_history.py`): carry on MEXC-only coins.",
    "Install PyTorch CPU and the Kronos-small weights (about 300 MB): R227 Kronos lane (PR #9).",
    "Download the DefiLlama unlock calendar (old source: 372 protocol files): replicates the old session's unlock short"
    " (E01, R179/R181, +2.5% per event), the strongest edge in `docs/OLD_SESSION_EDGES.md`.",
    "Rotate the two Coinalyze API keys pasted into the old session's chat (`docs/OLD_SESSION_EDGES.md`, security note).",
    "Yes or no: 20-30 tiny live MEXC orders placed by the owner to measure real fills against paper (a carve-out from"
    " rule 6; `docs/CRITIQUE.md`).",
    "Set the stake and max loss for gate 4 (`docs/GATES.md`; the lab only proposes 2% of trading capital per book and a"
    " stop at 25% of the stake).",
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
         "## How we proceed: one item at a time", "",
         "Every 30-minute tick:",
         "1. `scripts/forward_all.sh` runs every forward paper lane, the lag report and this panel.",
         "2. Read the room (issue #7) and answer Codex.",
         "3. Take the top `UNTESTED` method in `registry/methods.csv` that runs on data we hold. Write its PREREG,"
         " freeze it, run it (`lab/screen.py` for a cross-sectional feature), write FINDINGS at 1x/2x/3x costs, append"
         " the registry row and mark the method tested. Finish it before starting another. A bad-looking idea is"
         " still tested: a null is evidence.",
         "4. A method that passes its screen becomes one frozen forward paper lane under a new id (gate 1). Real money"
         " only after gates 1-3, placed by the owner (gate 4).",
         "5. Commit and push.", "",
         "Roles: Claude runs the lanes and the forward pipeline; Codex reviews and drafts on `codex/` branches;"
         " subagents (Haiku preferred) read, extract and critique (at most 3 at a time). No Workflows.", "",
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
