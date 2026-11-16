"""Census of open registry rows: which RUNNING/REGISTERED/ARMED/PLANNED lanes still have a writer.

Read-only. It changes no registry row and no lane file; it prints (or writes with --out) a markdown table so a
weekly check can see, in one command, which open rows are written by a GitHub workflow, which belong to Codex's
ended runtime, and which have had no writer since a container stopped. Classes are operational facts, not
verdicts: a row's status changes only with its frozen read. A lane whose writer is gone gets a dated line starting
"**Writer lost" in its README.md or FINDINGS.md, and is then counted as writer-lost-noted.

Classes:
- workflow: named by a workflow file and its folder had a commit within --stale-days ("named and recently
  committed", not proof that every run succeeded);
- workflow-dated: named only by workflows whose crons all fix a day of month and a month (reads on set dates);
- workflow-quiet: named by a workflow with an open schedule, but no commit within --stale-days;
- codex: no workflow names it and its PREREG owner is Codex;
- writer-lost-noted: no writer, and its README/FINDINGS carries the "**Writer lost" note;
- no-folder: no writer and no experiments/<lane> folder in this repo (old-session rows such as R180);
- no-writer-recent / no-writer: no workflow, a commit within --stale-days or not.

    python scripts/lane_census.py               # table to stdout
    python scripts/lane_census.py --stale-days 14
"""
import argparse
import csv
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPEN = ("RUNNING", "REGISTERED", "ARMED", "PLANNED")


def writers(lane, workflows):
    """Workflow file names whose text names the lane as a whole word (tltcarry_fwd must not match carry_fwd)."""
    pat = re.compile(r"(?<![\w])" + re.escape(lane) + r"(?![\w])")
    return sorted(name for name, text in workflows.items() if pat.search(text))


CRON = re.compile(r"cron:\s*['\"]([^'\"]+)['\"]")


def dated_only(texts):
    """True if every cron in these workflow texts fixes both a day of month and a month (e.g. '41 6 13-16 2 *')."""
    crons = [c.split() for t in texts for c in CRON.findall(t)]
    return bool(crons) and all(len(f) >= 4 and f[2] != "*" and f[3] != "*" for f in crons)


def owner(prereg_text):
    m = re.search(r"\*\*Owner[^*]*\*\*:?\s*(.*)", prereg_text or "")
    return m.group(1).strip() if m else ""


def classify(row, wf, own, last, today, stale_days, dated=False, noted=False, folder=True):
    """One of the classes in the module docstring."""
    age = (today - last).days if last else None
    if wf:
        if age is not None and age <= stale_days:
            return "workflow"
        return "workflow-dated" if dated else "workflow-quiet"
    if not folder:
        return "no-folder"
    if "codex" in own.lower():
        return "codex"
    if noted:
        return "writer-lost-noted"
    if age is not None and age <= stale_days:
        return "no-writer-recent"
    return "no-writer"


def last_commit(path):
    out = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%cs", "--", path],
                         capture_output=True, text=True).stdout.strip()
    return date.fromisoformat(out) if out else None


def census(root=ROOT, today=None, stale_days=7, last=last_commit):
    today = today or date.today()
    rows = list(csv.DictReader(open(root / "registry" / "rounds.csv", newline="")))
    workflows = {p.name: p.read_text() for p in sorted((root / ".github" / "workflows").glob("*.yml"))}
    out = []
    for r in rows:
        if r["status"] not in OPEN:
            continue
        lane = r["lane"]
        prereg = root / "experiments" / lane / "PREREG.md"
        own = owner(prereg.read_text()) if prereg.exists() else ""
        wf = writers(lane, workflows)
        lc = last(f"experiments/{lane}")
        notes = "".join((root / "experiments" / lane / f).read_text()
                        for f in ("README.md", "FINDINGS.md") if (root / "experiments" / lane / f).exists())
        out.append({"id": r["id"], "status": r["status"], "lane": lane, "writer": ",".join(wf) or "-",
                    "last_commit": lc.isoformat() if lc else "", "owner": own[:60],
                    "class": classify(r, wf, own, lc, today, stale_days,
                                      dated=dated_only(workflows[w] for w in wf), noted="**Writer lost" in notes,
                                      folder=(root / "experiments" / lane).is_dir())})
    return out


def render(rows, today):
    counts = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    lines = [f"Lane census, {today.isoformat()}: {len(rows)} open rows. "
             + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".", "",
             "| id | status | lane | class | writer | last commit |", "|---|---|---|---|---|---|"]
    order = {"no-writer": 0, "workflow-quiet": 1, "codex": 2, "no-writer-recent": 3, "writer-lost-noted": 4,
             "no-folder": 5, "workflow-dated": 6, "workflow": 7}
    for r in sorted(rows, key=lambda r: (order.get(r["class"], 9), r["id"])):
        lines.append(f"| {r['id']} | {r['status']} | {r['lane']} | {r['class']} | {r['writer']} | {r['last_commit']} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stale-days", type=int, default=7)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    today = date.today()
    text = render(census(today=today, stale_days=a.stale_days), today)
    if a.out:
        a.out.write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
