#!/usr/bin/env python3
"""Query tracked repository metadata without importing runners or reading outcomes.

python scripts/repository_index.py --find funding
python scripts/repository_index.py --find R225 --json

README.md is the maintained document index. This command builds its lookup in
memory from tracked document headings and registry/source metadata, then prints
the requested view. It has no write or cached-index mode. Market caches, result
payloads, journal contents and environment variables are never inspected.
"""

import argparse
import csv
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


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
        "PRIMARY_EQUATIONS", "AUCTION_AND_FLOW", "QUANTDATA", "TRADER_TALKS", "VIDEO_DIG", "COMMENT_DIG",
    },
    "Data, venues and tooling": {
        "DATA_SOURCES", "VENUE_STRUCTURE", "BENCHMARK", "FREE_AI_AGENT",
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
    # Search these canonical inputs in memory; never emit another methods queue.
    tables = [
        ("registry/methods.csv", "method", "id", "method", ("status", "data_held")),
        ("registry/methods_aliases.csv", "alias", "rec_id", "title", ("queue_id", "also")),
    ]
    tables += [(p, "provider", "id", "provider", ("url", "received_scope", "access_boundary", "research_gap", "existing_queue"))
               for p in files if p.startswith("research/intake/source_catalog") and p.endswith(".csv")]
    for path, kind, id_key, title_key, metadata in tables:
        if path not in available:
            continue
        with safe_file(root, path).open(newline="", encoding="utf-8") as source:
            table = csv.DictReader(source)
            required = {id_key, title_key, *metadata}
            if not required <= set(table.fieldnames or []):
                raise ValueError(f"Missing catalog columns in {path}: {sorted(required - set(table.fieldnames or []))}")
            for row in table:
                if None in row or not row[id_key] or not row[title_key]:
                    raise ValueError(f"Malformed catalog row in {path}")
                entries.append(dict(kind=kind, path=path, id=row[id_key], title=row[title_key],
                                    group="Canonical lookup", **{k: row[k] for k in metadata}))
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


def render(entries):
    """Return a transient text view; canonical records remain in their source files."""
    lines = []
    for entry in entries:
        identifier = f" [{entry['id']}]" if entry.get('id') else ""
        title = entry['title'].replace("\n", " ").replace("\r", " ")
        line = f"{entry['kind']}{identifier}: {entry['path']} — {title}"
        if entry['kind'] == 'experiment':
            records = "; ".join(" / ".join(r[k] or "unspecified" for k in ("id", "status", "verdict"))
                                for r in entry['registry'])
            line += f"; {records or 'No registry row in this checkout'}"
            if not entry['local']:
                line += "; Registered folder absent from this checkout"
            elif not entry['prereg'] and not entry['findings']:
                line += "; No local spec/findings"
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def trace(root,identifier,files=None):
    """Follow canonical method→round→spec/code/data identities, metadata only.

    Reported hashes are provenance pointers, not reverified market data or
    results. No result payload, journal, cached table or runner is opened.
    """
    if not re.fullmatch(r'[MR][0-9]+',identifier):raise ValueError('one canonical M/R identifier required')
    files=set(tracked_files(root) if files is None else files)
    def rows(relative):
        with safe_file(root,relative).open(newline='') as stream:return list(csv.DictReader(stream))
    methods=rows('registry/methods.csv');registered=rows('registry/rounds.csv')
    selected=[m for m in methods if m['id']==identifier]
    if identifier.startswith('M') and not selected:raise ValueError('unknown canonical method')
    rids={identifier} if identifier.startswith('R') else set(re.findall(r'\bR[0-9]+\b',selected[0].get('rid','')))
    records=[r for r in registered if r['id'] in rids];lanes=[]
    for r in records:
        prefix='experiments/'+r['lane'];identities=[]
        metadata=sorted(p for p in files if p.startswith(prefix+'/') and p.endswith('.json') and
            '/' not in p[len(prefix)+1:] and 'inputs' in Path(p).name)
        for name in metadata:
            p=safe_file(root,name)
            if p.stat().st_size>2*1024**2:raise ValueError('oversized provenance metadata')
            obj=json.loads(p.read_text())
            def visit(x,at=''):
                if isinstance(x,dict):
                    for k,v in x.items():
                        if isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v):
                            identities.append({'manifest':name,'field':at+'/'+k,'reported_sha256':v,
                                'local_tracked':k in files,'identity_reverified':False})
                        elif isinstance(v,(dict,list)):visit(v,at+'/'+k)
                elif isinstance(x,list):
                    for i,v in enumerate(x):visit(v,at+'/'+str(i))
            visit(obj)
        lanes.append({'id':r['id'],'lane':r['lane'],'status':r['status'],'verdict':r['verdict'],
            'trials':r['trials'],'spec':prefix+'/PREREG.md' if prefix+'/PREREG.md' in files else None,
            'findings':prefix+'/FINDINGS.md' if prefix+'/FINDINGS.md' in files else None,
            'registered_prereg_sha256':r['prereg_sha'],'identities':identities})
    if identifier.startswith('R') and not records:raise ValueError('unknown registered round')
    return {'query':identifier,'canonical_methods':selected,'rounds':lanes,
        'scope':'Metadata links only; reported identities, verdicts and input completeness are not independently verified here.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--find", metavar="TEXT")
    parser.add_argument("--trace", metavar="M_ID_OR_R_ID",help='trace existing code/data manifest identities without opening market inputs')
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.trace:
            if args.find:raise ValueError('choose either trace or text search')
            print(json.dumps(trace(root,args.trace),ensure_ascii=False,indent=2))
            return 0
        entries = build_index(root, tracked_files(root))
        if args.find is not None:
            query = args.find.casefold()
            entries = [e for e in entries if query in json.dumps(e, ensure_ascii=False).casefold()]
        if args.json:
            print(json.dumps(entries, ensure_ascii=False, indent=2))
        else:
            print(render(entries), end="")
            print(f"{len(entries)} {'matches' if args.find is not None else 'indexed entries'}")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Repository index: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
