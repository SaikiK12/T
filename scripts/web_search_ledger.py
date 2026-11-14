#!/usr/bin/env python3
"""Check, query and append the web search ledger (registry/web_searches.csv) without any network access.

``audit(root: Path) -> dict`` returns ``summary`` (rows, errors, warnings) and ``issues`` (severity, code, message). ``main(argv=None) -> int``
implements ``check [--root --json --strict]``, ``seen TEXT`` and ``add --field value ...``. Only ``add`` writes, and
only by appending one row through lab.websearch.append.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import websearch
from lab.registry import RegistryError

ROOT = Path(__file__).resolve().parents[1]


def audit(root: Path) -> dict:
    root = Path(root).resolve()
    rows = websearch.load(root)
    issues = [dict(severity="error", code="WEBSEARCH_INVALID", message=m, path=str(websearch.LEDGER))
              for m in websearch.validate(rows, root)]
    if not (root / websearch.LEDGER).exists():
        issues.append(dict(severity="error", code="WEBSEARCH_LEDGER_MISSING", message="ledger file is missing",
                           path=str(websearch.LEDGER)))
    errors = len(issues)
    issues += [dict(severity="warning", code="WEBSEARCH_SUSPECT", message=m, path=str(websearch.LEDGER))
               for m in websearch.warnings(rows)]
    return dict(summary=dict(rows=len(rows), errors=errors, warnings=len(issues) - errors), issues=issues)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate the ledger")
    check.add_argument("--root", default=str(ROOT))
    check.add_argument("--json", action="store_true")
    check.add_argument("--strict", action="store_true", help="also fail on warnings")
    find = sub.add_parser("seen", help="look for a prior query or URL in the ledger and source catalogs")
    find.add_argument("text")
    find.add_argument("--root", default=str(ROOT))
    add = sub.add_parser("add", help="append one ledger row")
    add.add_argument("--root", default=str(ROOT))
    for column in websearch.COLUMNS[1:]:
        add.add_argument("--" + column.replace("_", "-"), dest=column, default="")
    args = parser.parse_args(argv)
    if args.command == "check":
        report = audit(args.root)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for issue in report["issues"]:
                print(f"{issue['severity']} {issue['code']}: {issue['message']}")
            summary = report["summary"]
            print(f"web search ledger: {summary['rows']} rows, {summary['errors']} errors, {summary['warnings']} warnings")
        return 1 if report["summary"]["errors"] or (args.strict and report["summary"]["warnings"]) else 0
    if args.command == "seen":
        hits = websearch.seen(Path(args.root), args.text)
        for hit in hits:
            print(f"{hit['source']} {hit['id']} {hit['match']}")
        print(f"{len(hits)} hit(s) for {args.text!r}" + ("" if hits else ": not seen before"))
        return 0
    fields = {c: getattr(args, c) for c in websearch.COLUMNS[1:]}
    try:
        row = websearch.append(Path(args.root), **fields)
    except (ValueError, RegistryError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    print(f"appended {row['search_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
