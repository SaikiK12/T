#!/usr/bin/env python3
"""Browse committed repository metadata without importing runners or reading outcomes.

python scripts/repository_index.py --write   # rebuild docs/README.md only
python scripts/repository_index.py --check   # fail if the navigation needs rebuilding
python scripts/repository_index.py --find funding --json

The index describes this checkout, not unmerged PRs or the state of another sandbox.
It reads tracked documentation headings and registry metadata only. Market caches,
result payloads, journal contents and environment variables are never inspected.
"""

import argparse
import csv
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import quote


OUTPUT = "docs/README.md"
DOC_GROUPS = {
    "Operating rules and decisions": {
        "DIRECTION", "GATES", "ROOM", "CRITIQUE", "PANEL", "METHODS_QUEUE",
    },
    "Evidence summaries and historical handoffs": {
        "MAP", "EDGE_SCOREBOARD", "RESEARCH_HANDOFF", "FOUNDATION", "OLD_SESSION_EDGES",
        "RESEARCH_COVERAGE_LEDGER",
    },
    "Sources and methods to reconcile": {
        "SOURCES", "CLAIMS", "CONCEPTS", "ALTCOIN_LEADS", "NEXT_SEARCH_SPACE",
        "RESEARCH_FRONTIER", "QUANTPEDIA_RESEARCH_REVIEW", "REELS_TRANSCRIPT",
        "QUARTER_HOUR_AGGRESSOR_FLOW_PROPOSAL", "FOREX_AND_INDICES", "PROP_FIRMS",
    },
    "Execution, accounting and risk": {
        "PERP_CARRY_ACCOUNTING", "PERP_EXECUTION_AND_RISK", "SIZING_EVIDENCE",
        "PAPER_REFINEMENT", "OPERATIONAL_API_RISK", "CAPITAL_GATE_REVIEW",
        "CONFIDENCE_AND_SIZING_AUDIT", "MEXC_EDGES",
    },
    "Inference and signal interpretation": {
        "ADAPTIVE_SELECTION_AND_DRIFT", "CRYPTO_CROSS_SECTION_EVIDENCE",
        "FORECAST_EVALUATION_PLAYBOOK", "MARKET_DIRECTION_AND_REGIME",
        "POSITIONING_AND_ORDERFLOW_VALIDITY", "VOLATILITY_AND_TAIL_RISK_FORECASTS",
    },
    "Integrity reviews and fixes": {
        "AUDIT", "CONFIDENCE_REVIEW", "CONTRACT_LIFECYCLE_INTEGRITY",
        "DATA_PROVENANCE_AUDIT", "FEATURE_VINTAGE_INTEGRITY",
        "IMPLEMENTATION_INTEGRITY_REVIEW", "SELECTION_AND_TRIAL_ACCOUNTING_AUDIT",
        "TARGET_INTEGRITY_FIX",
    },
}


def tracked_files(root):
    """Use the tracked file list, never walk caches, virtualenvs or secret files."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True,
    )
    return sorted(set(result.stdout.decode("utf-8").strip("\0").split("\0")) - {""})


def safe_file(root, relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts or "\\" in relative:
        raise ValueError(f"Unsafe repository path: {relative}")
    path = root / relative
    # Do not follow tracked symlinks, including through a parent directory.
    if any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1)):
        raise ValueError(f"Symlink cannot be indexed: {relative}")
    path.resolve().relative_to(root.resolve())
    if not path.is_file():
        raise ValueError(f"Tracked file missing: {relative}")
    return path


def heading(root, path):
    # Only headings of documentation are read, never result tables or journals.
    with safe_file(root, path).open(encoding="utf-8") as source:
        for line in source:
            if line.startswith("# "):
                return line[2:].strip()
    return Path(path).stem


def script_group(name):
    if name.startswith("forward_") or name in {"orchestrate_forward.py", "live_parity.py"}:
        return "Prospective paper and orchestration"
    if name.startswith("record_"):
        return "Point-in-time recorders"
    if name.startswith(("fetch_", "scrape_")):
        return "Acquisition (network and volume approval may be required)"
    if name.startswith("run_") or name == "atlas_replication.py":
        return "Research runners (read the frozen specification first)"
    if name.startswith(("check_", "repository_")) or name == "panel.py":
        return "Checks and navigation"
    return "Builders and supporting tools"


def build_index(root, files):
    """Return a deterministic catalog from an explicit list of tracked files."""
    root = Path(root)
    files = sorted(set(files))
    if any(PurePosixPath(p).is_absolute() or ".." in PurePosixPath(p).parts or "\\" in p for p in files):
        raise ValueError("Unsafe tracked path in file list")
    available = set(files)
    entries = []
    rows = []
    if "registry/rounds.csv" in available:
        with safe_file(root, "registry/rounds.csv").open(newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
    for path in files:
        parts = PurePosixPath(path).parts
        if path == OUTPUT:
            continue  # The generated file must not index itself.
        if len(parts) == 2 and parts[0] == "docs" and path.endswith(".md"):
            stem = PurePosixPath(path).stem
            group = next((g for g, names in DOC_GROUPS.items() if stem in names), "New / unclassified documents")
            entries.append(dict(kind="document", path=path, title=heading(root, path), group=group))
        elif len(parts) == 2 and parts[0] == "scripts" and path.endswith((".py", ".sh")):
            safe_file(root, path)  # Existence/symlink validation; never execute or import it.
            entries.append(dict(kind="command", path=path, title=parts[-1], group=script_group(parts[-1])))
        elif len(parts) >= 3 and parts[:2] == ("research", "intake"):
            safe_file(root, path)
            entries.append(dict(kind="source", path=path, title=parts[-1], group="Source inputs"))
    local_lanes = {PurePosixPath(p).parts[1] for p in files
                   if len(PurePosixPath(p).parts) >= 3 and p.startswith("experiments/")}
    registered_lanes = {r.get("lane", "") for r in rows}
    if any(not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", lane) for lane in registered_lanes):
        raise ValueError("Invalid lane name in registry")
    lanes = sorted(local_lanes | registered_lanes)
    for lane in lanes:
        prefix = f"experiments/{lane}"
        spec = f"{prefix}/PREREG.md"
        findings = f"{prefix}/FINDINGS.md"
        records = [r for r in rows if r.get("lane") == lane]
        entry = dict(kind="experiment", path=spec if spec in available else prefix,
                     title=lane, group="Experiments", local=lane in local_lanes,
                     registry=[{k: r.get(k, "") for k in ("id", "status", "verdict")} for r in records],
                     prereg=spec if spec in available else None,
                     findings=findings if findings in available else None)
        # A file is only linked when present; no verdict is inferred from its name.
        for key in ("prereg", "findings"):
            if entry[key]:
                safe_file(root, entry[key])
        entries.append(entry)
    return entries


def cell(text):
    return str(text).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def link(path, title):
    return f"[{cell(title).replace('[', '&#91;').replace(']', '&#93;')}](../{quote(path, safe='/')})"


def render(entries):
    docs = [e for e in entries if e["kind"] == "document"]
    commands = [e for e in entries if e["kind"] == "command"]
    lanes = [e for e in entries if e["kind"] == "experiment"]
    sources = [e for e in entries if e["kind"] == "source"]
    lines = [
        "# Repository navigation", "",
        "Generated by `python scripts/repository_index.py --write` from tracked files in this checkout. "
        "The index describes file locations and recorded registry metadata; it does not recompute or promote evidence.", "",
        "## One place for each decision", "",
        "| Need | Authority |", "|---|---|",
        "| Current operating status | [PANEL](PANEL.md); regenerate with `scripts/panel.py` |",
        "| Objective and evidence gates | [DIRECTION](DIRECTION.md), [GATES](GATES.md), [CRITIQUE](CRITIQUE.md) |",
        "| Current method status and next study | [methods.csv](../registry/methods.csv); "
        "[METHODS_QUEUE](METHODS_QUEUE.md) preserves an older snapshot |",
        "| Study verdict and trial count | [rounds.csv](../registry/rounds.csv), then that lane's frozen spec and findings |",
        "| Source scope and aliases | [source intake](../research/intake/README.md) and "
        "[methods_aliases.csv](../registry/methods_aliases.csv) |",
        "| Writer claim and review dependencies | [room #7](https://github.com/SaikiK12/T/issues/7), "
        "[open PRs](https://github.com/SaikiK12/T/pulls); [ROOM protocol](ROOM.md) |", "",
        "MAP, SCOREBOARD, reviews and old handoffs are interpretations with their own dates. "
        "When prose and recorded evidence disagree, inspect the exact lane and report the discrepancy; "
        "do not rewrite a frozen specification or silently choose the favorable number.", "",
        "## Find and maintain", "", "```sh",
        "python scripts/repository_index.py --find funding",
        "python scripts/repository_index.py --find R225 --json",
        "python scripts/repository_index.py --check",
        "python scripts/check_research_integrity.py", "```", "",
        "`--find` searches filenames, document headings and recorded experiment metadata. "
        "It does not search full papers, result payloads or market caches. After adding or renaming tracked files, "
        "stage them and run `--write`, then `--check`. Commands below are navigation links, not an execution queue.", "",
        f"## Documents ({len(docs)})", "",
    ]
    groups = list(DOC_GROUPS) + ["New / unclassified documents"]
    for group in groups:
        selected = [e for e in docs if e["group"] == group]
        if not selected:
            continue
        lines += [f"### {group}", ""]
        lines += [f"- {link(e['path'], e['title'])}" for e in selected]
        lines += [""]
    lines += [f"## Source inputs ({len(sources)})", "",
              "These are received-source catalogs and provenance, not additional methods queues. "
              "A provider catalog is not a fully read corpus or evidence of access to its paid data.", ""]
    lines += [f"- {link(e['path'], e['title'])}" for e in sources]
    lines += ["", f"## Commands ({len(commands)})", "",
              "Acquisition may consume network/storage; study runners may consume reserved data. "
              "Read AGENTS, GATES and the lane's protocol before running either. "
              "Forward runners and journals remain owned by their registered writer.", ""]
    for group in sorted({e["group"] for e in commands}):
        selected = [e for e in commands if e["group"] == group]
        lines += ["<details>", f"<summary>{group} ({len(selected)})</summary>", ""]
        lines += [f"- {link(e['path'], e['title'])}" for e in selected]
        lines += ["", "</details>", ""]
    lines += [f"## Experiment locations ({len(lanes)})", "",
              "Recorded status/verdict comes only from this checkout's rounds.csv. "
              "A findings link means the file exists, not that a study passed. Unregistered folders and "
              "missing specs stay visible. Use the integrity audit to verify frozen digests; this index does not.", "",
              "<details>", "<summary>All experiment folders and their registered IDs</summary>", "",
              "| Lane | Recorded ID / status / verdict | Local files |", "|---|---|---|"]
    for entry in lanes:
        recorded = "; ".join(" / ".join(r[k] or "unspecified" for k in ("id", "status", "verdict"))
                             for r in entry["registry"]) or "No registry row in this checkout"
        local = [link(entry[k], label) for k, label in (("prereg", "spec"), ("findings", "findings")) if entry[k]]
        title = link(entry['path'], entry['title']) if entry['local'] else cell(entry['title'])
        missing = 'No local spec/findings' if entry['local'] else 'Registered folder absent from this checkout'
        lines.append(f"| {title} | {cell(recorded)} | {' · '.join(local) or missing} |")
    lines += ["", "</details>", "",
              "## Layout and provenance", "",
              "- `lab/`: reusable data, accounting, inference and gate primitives.",
              "- `tests/`: offline unit and synthetic checks; test filenames identify the module or lane.",
              "- `templates/lane/`: scaffolding for a new registered study.",
              "- `experiments/<lane>/results/`: result provenance; `journal/`: append-only paper observations.",
              "- Existing paths are retained: frozen specs, source hashes and cross-PR references can depend on them.",
              "- Bulk archives and caches stay outside Git; an index entry does not imply those inputs exist locally.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--find", metavar="TEXT")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.json and (args.write or args.check):
        parser.error("--json is only for browsing or --find")
    try:
        root = args.root.resolve()
        entries = build_index(root, tracked_files(root))
        document = render(entries)
        if args.write or args.check:
            target = root / OUTPUT
            if target.is_symlink() or target.parent.is_symlink():
                raise ValueError("Navigation output cannot be a symlink")
            if args.write:
                target.write_text(document, encoding="utf-8")
                print(f"Wrote {OUTPUT}; {len(entries)} indexed entries")
                return 0
            if not target.exists() or target.read_text(encoding="utf-8") != document:
                print(f"Stale {OUTPUT}: stage new paths and run --write", file=sys.stderr)
                return 1
            print(f"Current {OUTPUT}; {len(entries)} indexed entries")
            return 0
        if args.find is not None:
            query = args.find.casefold()
            entries = [e for e in entries if query in json.dumps(e, ensure_ascii=False).casefold()]
        if args.json:
            print(json.dumps(entries, ensure_ascii=False, indent=2))
        elif args.find is not None:
            for entry in entries:
                print(f"{entry['kind']}: {entry['path']} — {entry['title']}")
            print(f"{len(entries)} matches")
        else:
            print(document, end="")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Repository index: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
