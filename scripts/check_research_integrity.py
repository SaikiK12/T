#!/usr/bin/env python3
"""Audit the research register and local preregistrations without changing files.

``audit(root: Path) -> dict`` returns a JSON-serializable snapshot with ``summary``
and ``issues``. Summary keys are registry_rows, local_specs, verified_frozen,
planned_drafts, errors and warnings. Each issue has severity (error, warning or
info), a stable code, a message, and optionally a root-relative path and round_id.
Blank legacy dates/trial counts are allowed. Missing imported experiment folders
are warnings; PLANNED drafts may remain unfrozen. No results or market data are
read, and no status is inferred from FINDINGS prose.

``main(argv=None) -> int`` implements --root, --json and --strict. Errors fail the
command; --strict also fails on warnings. Codes describe the failed invariant,
not a proposed repair. The audit never freezes, repairs or appends anything.
"""

import argparse
import csv
from datetime import date
import json
from pathlib import Path, PureWindowsPath
import re
import sys

# Permit `python scripts/check_research_integrity.py` from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab import prereg, registry


_ID = re.compile(r"R[0-9]+\Z")
_SHA = re.compile(r"[0-9a-f]{8,64}\Z")
_FULL_SHA = re.compile(r"[0-9a-f]{64}\Z")
_META = re.compile(
    r"^[ \t]*(?:[-*+][ \t]+)?(?:\*\*)?Registry[ \t]+id[ \t]*:"
    r"[ \t]*(?:\*\*)?[ \t]*(.*?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
# One bare or backtick-quoted id, optionally followed by a single annotation.
# Keep the full-value match: arbitrary trailing text must not hide another id.
_META_ID = re.compile(
    r"(?P<quote>`?)(?P<id>R[0-9]+)(?P=quote)"
    r"(?:[ \t]+\([^()\r\n]*\))?\Z"
)


def audit(root: Path) -> dict:
    """Read one local snapshot; report inconsistencies without modifying it."""
    root = Path(root).resolve()
    report = {
        "summary": dict(registry_rows=0, local_specs=0, verified_frozen=0,
                        planned_drafts=0, errors=0, warnings=0),
        "issues": [],
    }
    issues = report["issues"]
    summary = report["summary"]

    def add(severity, code, message, path=None, round_id=None):
        issue = dict(severity=severity, code=code, message=message)
        if path is not None:
            try:
                issue["path"] = str(Path(path).relative_to(root))
            except ValueError:
                # Unsafe user-supplied paths are displayed, never opened.
                issue["path"] = str(path)
        if round_id:
            issue["round_id"] = round_id
        issues.append(issue)

    def safe(path, round_id=None):
        """Check symlinks before any filesystem content is read."""
        try:
            path.relative_to(root)
            resolved = path.resolve()
            resolved.relative_to(root)
        except (ValueError, OSError, RuntimeError) as exc:
            add("error", "UNSAFE_PATH", f"Path cannot be safely read inside root: {exc}",
                path, round_id)
            return None
        return resolved

    def registered_path(raw, round_id):
        portable = raw.replace("\\", "/")
        if (Path(raw).is_absolute() or PureWindowsPath(raw).drive
                or ".." in portable.split("/")):
            add("error", "UNSAFE_PATH", "Registry path must be relative and contain no traversal.",
                raw, round_id)
            return None
        return safe(root / raw, round_id)

    def is_file(path, round_id=None):
        if safe(path, round_id) is None:
            return None
        try:
            return path.is_file()
        except OSError as exc:
            add("error", "FILE_READ_ERROR", str(exc), path, round_id)
            return None

    rows = []
    register_path = root / "registry" / "rounds.csv"
    if safe(register_path) is not None:
        try:
            with register_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle, strict=True)
                header = next(reader, [])
                header_ok = tuple(header) == registry.FIELDS
                if not header_ok:
                    add("error", "REGISTRY_HEADER",
                        f"Expected columns {registry.FIELDS!r}; found {tuple(header)!r}.",
                        register_path)
                for values in reader:
                    if not values:
                        continue
                    summary["registry_rows"] += 1
                    if len(values) != len(registry.FIELDS):
                        add("error", "REGISTRY_ROW_COLUMNS",
                            f"CSV line {reader.line_num}: expected {len(registry.FIELDS)} fields, "
                            f"found {len(values)}.", register_path)
                        continue
                    if header_ok:
                        rows.append(dict(zip(registry.FIELDS, values)))
        except FileNotFoundError:
            add("error", "REGISTRY_MISSING", "Research register is missing.", register_path)
        except csv.Error as exc:
            add("error", "REGISTRY_CSV_ERROR", f"Malformed CSV: {exc}", register_path)
        except (OSError, UnicodeError) as exc:
            add("error", "REGISTRY_READ_ERROR", str(exc), register_path)

    seen_ids = set()
    directories = {}  # Safe canonical local directories, never a recursive walk.
    for row in rows:
        round_id = row["id"]
        if not _ID.fullmatch(round_id):
            add("error", "REGISTRY_ID", "Round id must be R followed by digits.",
                register_path, round_id)
        if round_id in seen_ids:
            add("error", "REGISTRY_DUPLICATE_ID", "Round id occurs more than once.",
                register_path, round_id)
        seen_ids.add(round_id)
        if row["date"]:
            try:
                parsed_date = date.fromisoformat(row["date"])
                if parsed_date.isoformat() != row["date"]:
                    raise ValueError("expected YYYY-MM-DD")
            except ValueError:
                add("error", "REGISTRY_DATE", "Date must be YYYY-MM-DD or empty.",
                    register_path, round_id)
        if row["status"] not in registry.STATUS:
            add("error", "REGISTRY_STATUS", f"Unknown status {row['status']!r}.",
                register_path, round_id)
        if row["verdict"] not in registry.VERDICT:
            add("error", "REGISTRY_VERDICT", f"Unknown verdict {row['verdict']!r}.",
                register_path, round_id)
        if row["trials"] and not re.fullmatch(r"[0-9]+", row["trials"]):
            add("error", "REGISTRY_TRIALS", "Trials must be a nonnegative integer or empty.",
                register_path, round_id)
        if row["prereg_sha"] and not _SHA.fullmatch(row["prereg_sha"]):
            add("error", "REGISTRY_SHA", "prereg_sha must be 8-64 lowercase hex characters.",
                register_path, round_id)
        elif not row["prereg_sha"]:
            add("warning", "REGISTRY_SHA_MISSING", "Registry row has no preregistration digest.",
                register_path, round_id)
        if not row["path"]:
            add("warning", "EXPERIMENT_MISSING", "No experiment path is registered.",
                round_id=round_id)
            continue
        directory = registered_path(row["path"], round_id)
        if directory is None:
            continue
        if Path(row["path"]).name != row["lane"]:
            add("error", "LANE_PATH_MISMATCH", "Registry lane differs from its path directory.",
                root / row["path"], round_id)
        try:
            if not directory.exists():
                add("warning", "EXPERIMENT_MISSING",
                    "Registered experiment directory is absent (possibly a legacy import).",
                    root / row["path"], round_id)
                continue
            if not directory.is_dir():
                add("error", "EXPERIMENT_NOT_DIRECTORY", "Experiment path is not a directory.",
                    root / row["path"], round_id)
                continue
        except OSError as exc:
            add("error", "FILE_READ_ERROR", str(exc), directory, round_id)
            continue
        directories.setdefault(directory, []).append(row)

    experiments = root / "experiments"
    if safe(experiments) is not None:
        try:
            if experiments.is_dir():
                for child in sorted(experiments.iterdir()):
                    resolved = safe(child)
                    if resolved is not None and child.is_dir():
                        directories.setdefault(resolved, [])
        except OSError as exc:
            add("error", "FILE_READ_ERROR", str(exc), experiments)

    for directory, lane_rows in sorted(directories.items()):
        if len(lane_rows) > 1:
            add("error", "DUPLICATE_LANE",
                "Multiple registry rows claim this local experiment: "
                + ", ".join(row["id"] for row in lane_rows), directory)
        spec = directory / "PREREG.md"
        side = prereg.sidecar(spec)
        spec_exists = is_file(spec)
        side_exists = is_file(side)
        if side_exists and spec_exists is False:
            add("error", "ORPHAN_SIDECAR", "Frozen sidecar has no PREREG.md.", side)
        if spec_exists is False:
            for row in lane_rows:
                if row["status"] == "PLANNED":
                    add("info", "PLANNED_DRAFT", "PLANNED lane has no preregistration yet.",
                        spec, row["id"])
                else:
                    add("error", "PREREG_MISSING", "Local registered lane has no PREREG.md.",
                        spec, row["id"])
        if spec_exists:
            summary["local_specs"] += 1
            try:
                text = spec.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                add("error", "FILE_READ_ERROR", str(exc), spec)
                text = None
            if text is not None:
                metadata = _META.findall(text)
                declared = _META_ID.fullmatch(metadata[0].strip()) if len(metadata) == 1 else None
                if not metadata:
                    add("warning", "REGISTRY_ID_MISSING", "PREREG has no explicit Registry id metadata.",
                        spec)
                elif declared is None:
                    add("error", "REGISTRY_ID_INVALID", "PREREG must declare one valid Registry id.",
                        spec)
                else:
                    for row in lane_rows:
                        if declared["id"] != row["id"]:
                            add("error", "REGISTRY_ID_MISMATCH",
                                f"PREREG declares {declared['id']}, registry row is {row['id']}.",
                                spec, row["id"])
            frozen = None
            if side_exists:
                try:
                    frozen = side.read_text(encoding="utf-8").strip()
                    if not _FULL_SHA.fullmatch(frozen):
                        add("error", "SIDECAR_INVALID", "Sidecar must contain a full lowercase SHA256.",
                            side)
                        frozen = None
                    else:
                        try:
                            prereg.verify(spec)
                            summary["verified_frozen"] += 1
                        except prereg.PreregError as exc:
                            add("error", "HASH_MISMATCH", str(exc), spec)
                except (OSError, UnicodeError) as exc:
                    add("error", "FILE_READ_ERROR", str(exc), side)
                if not lane_rows:
                    add("warning", "UNREGISTERED_PREREG", "Frozen local spec has no registry row.", spec)
            elif side_exists is False:
                if lane_rows and all(row["status"] == "PLANNED" for row in lane_rows):
                    summary["planned_drafts"] += 1
                    add("info", "PLANNED_DRAFT", "PLANNED preregistration is not frozen yet.", spec)
                else:
                    add("error", "SIDECAR_MISSING", "PREREG.md has no frozen sidecar.", side)
            for row in lane_rows:
                if frozen and _SHA.fullmatch(row["prereg_sha"]):
                    if not frozen.startswith(row["prereg_sha"]):
                        add("error", "REGISTRY_SHA_MISMATCH",
                            "Registered digest prefix does not match the frozen sidecar.",
                            spec, row["id"])
        for row in lane_rows:
            if row["status"] == "DONE" and is_file(directory / "FINDINGS.md", row["id"]) is False:
                add("warning", "FINDINGS_MISSING", "DONE local lane has no FINDINGS.md.",
                    directory / "FINDINGS.md", row["id"])

    summary["errors"] = sum(issue["severity"] == "error" for issue in issues)
    summary["warnings"] = sum(issue["severity"] == "warning" for issue in issues)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="Repository root (defaults to this script's repository)")
    parser.add_argument("--json", action="store_true", help="Print the structured audit snapshot")
    parser.add_argument("--strict", action="store_true", help="Also fail when warnings are present")
    args = parser.parse_args(argv)
    report = audit(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(f"Research integrity: {summary['registry_rows']} registry rows, "
              f"{summary['local_specs']} local specs, {summary['verified_frozen']} verified frozen, "
              f"{summary['planned_drafts']} planned drafts; "
              f"{summary['errors']} errors, {summary['warnings']} warnings.")
        for issue in report["issues"]:
            location = ": ".join(str(issue[key]) for key in ("round_id", "path") if key in issue)
            print(f"{issue['severity'].upper()} {issue['code']}"
                  f"{(' [' + location + ']') if location else ''}: {issue['message']}")
    return int(bool(report["summary"]["errors"]
                    or (args.strict and report["summary"]["warnings"])))


if __name__ == "__main__":
    raise SystemExit(main())
