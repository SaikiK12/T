"""Plain-language catalogs of the repository's folders, rebuilt from what the files already say:

- experiments/README.md: registered lanes (including absent imported folders), running/armed rounds, unregistered
  folders and known collection folders, with registry status and links to local evidence;
- scripts/README.md: every script by kind (fetch, record, run, forward, check and tools), with the first line of its
  docstring or header comment;
- lab/README.md: every module of the research library with the first line of its docstring.

It decides nothing and reads no market data. All views use one Git-index snapshot:
stage intended source/registry changes first; unstaged work and untracked files
are excluded. Rerun it whenever a round, script or module is added.

usage: python scripts/catalog.py [--check] [--root REPOSITORY]
--check reports stale/missing catalogs without writing them.
"""
import argparse
import ast
import csv
import io
import os
import re
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
from types import MappingProxyType

ROOT = Path(__file__).resolve().parent.parent
HEAD = "<!-- written by scripts/catalog.py; edit the sources (registry, docstrings), not this file -->\n"
INDEX_NOTE = "Source: tracked and staged Git-index metadata; untracked files and unstaged edits are excluded."
MAX_SOURCE_BYTES = 2 * 1024 ** 2
# folders that hold collected data or loop state rather than a registered round
NOT_ROUNDS = {
    "copylead_data": "Daily snapshots of public copy-trading leaderboards (Binance, OKX, Hyperliquid); collection only",
    "forward_lag": "How late each forward tick ran after the hour, per day (written by the forward loop)",
    "recorders": "Point-in-time recorders: MEXC tickers, Binance notices, unlock calendar; digests of what was recorded",
    "propsim_v1": "Edge map used by the prop-firm simulation (R202 propfirm_v1)",
}
KINDS = [  # (heading, test on the script's file name)
    ("Fetch: download archives and public history", lambda n: n.startswith("fetch_")),
    ("Record: point-in-time collectors (cannot be backfilled)", lambda n: n.startswith(("record_", "scrape_"))),
    ("Forward: paper lanes and the loops that run them",
     lambda n: n.startswith("forward_") or n.endswith(".sh") or n.startswith(("notice", "live_"))),
    ("Run: one lane's frozen measurement", lambda n: n.startswith(("run_", "qx_"))),
    ("Check: parity, audits and integrity", lambda n: n.startswith(("audit_", "check_", "verify_", "validate_"))
     or "parity" in n),
    ("Build: tables, views and symbol maps", lambda n: n.startswith(("build_", "make_", "venue_"))),
    ("Research: videos, podcasts and transcripts (docs/VIDEO_DIG.md)",
     lambda n: n.startswith(("dig_", "transcribe_"))),
]


class IndexSnapshot:
    """Pin tracked regular filenames and blobs once; never follow worktree inputs."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        top = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', '--show-toplevel'])
        if Path(os.fsdecode(top).strip()).resolve() != self.root:
            raise ValueError('catalog root must be the repository root')
        cmd = ['git', '-C', str(self.root)]
        index_name = subprocess.check_output(cmd + ['rev-parse', '--git-path', 'index']).decode().rstrip('\n')
        object_name = subprocess.check_output(cmd + ['rev-parse', '--git-path', 'objects']).decode().rstrip('\n')
        index = Path(index_name) if Path(index_name).is_absolute() else self.root / index_name
        objects = Path(object_name) if Path(object_name).is_absolute() else self.root / object_name
        # Let Git interpret index flags (intent-to-add, split/sparse index, conflicts).
        # The copied index and newly materialized trees stay in a temporary directory:
        # --check does not update the real index or leave objects in the repository.
        with tempfile.TemporaryDirectory(prefix='catalog-index-') as temp:
            temp = Path(temp)
            copied = temp / 'index'
            if index.exists():
                copied.write_bytes(index.read_bytes())
            (temp / 'objects/info').mkdir(parents=True)
            if '\n' in str(objects.resolve()):
                raise ValueError('unsupported newline in Git object directory')
            (temp / 'objects/info/alternates').write_text(str(objects.resolve()) + '\n')
            env = dict(os.environ, GIT_INDEX_FILE=str(copied), GIT_OBJECT_DIRECTORY=str(temp / 'objects'))
            try:
                tree = subprocess.check_output(cmd + ['write-tree'], env=env, stderr=subprocess.PIPE).decode().strip()
            except subprocess.CalledProcessError as exc:
                raise ValueError('cannot snapshot Git index; resolve unmerged entries and missing objects first') from exc
            raw = subprocess.check_output(cmd + ['ls-tree', '--full-tree', '-r', '-z', tree], env=env)
        blobs = {}
        for row in raw.split(b'\0'):
            if not row:
                continue
            meta, name = row.split(b'\t', 1)
            mode, kind, sha = meta.decode('ascii').split()
            path = name.decode('utf-8')
            parts = PurePosixPath(path).parts
            if not parts or PurePosixPath(path).is_absolute() or '..' in parts or '\\' in path:
                raise ValueError('unsafe indexed catalog path')
            if not re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}', sha):
                raise ValueError('invalid indexed blob identity')
            if kind == 'blob' and mode in ('100644', '100755'):
                blobs[path] = sha
        self.blobs = MappingProxyType(blobs)
        self.files = frozenset(blobs)
        self.directories = frozenset(str(p) for name in blobs for p in PurePosixPath(name).parents
                                     if str(p) != '.')
        self._text = {}

    def read(self, path):
        if path not in self.blobs:
            raise ValueError('regular indexed source required: ' + path)
        if path not in self._text:
            sha = self.blobs[path]
            cmd = ['git', '-C', str(self.root), 'cat-file']
            size = int(subprocess.check_output(cmd + ['-s', sha]))
            if size > MAX_SOURCE_BYTES:
                raise ValueError('oversized catalog source: ' + path)
            raw = subprocess.check_output(cmd + ['blob', sha])
            if len(raw) != size:
                raise ValueError('catalog source identity/size changed')
            self._text[path] = raw.decode('utf-8')
        return self._text[path]


def first_line(text, suffix):
    """The first sentence-line of a Python module's docstring or a shell script's header comment."""
    if suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text)) or ""
        except SyntaxError:
            doc = ""
        line = doc.strip().split("\n\n")[0].replace("\n", " ")
    else:
        com = [x[1:].strip() for x in text.splitlines()[1:] if x.startswith("#")]
        line = " ".join(com).split(". ")[0] if com else ""
    line = re.sub(r"\s+", " ", line).strip()
    if not line:
        return ""
    line = re.split(r"(?<=[a-z0-9)])\. ", line)[0].rstrip(".:") + "."    # the first sentence
    return line if len(line) <= 200 else line[:197].rsplit(" ", 1)[0] + " ..."


def experiment_catalog(root, source=None):
    """Render registry metadata and local paths only; never inspect results or journal contents.

    RUNNING/ARMED is a registry status, not proof of a live process or a paper lane.
    Missing imported folders remain visible without inventing links or outcomes.
    """
    source = source if source is not None else IndexSnapshot(root)
    reader = csv.DictReader(io.StringIO(source.read('registry/rounds.csv')))
    required = {'id', 'path', 'status', 'verdict', 'trials', 'title'}
    if not required <= set(reader.fieldnames or []):
        raise ValueError('missing required registry columns')
    rows = list(reader)
    if any(None in r or any(r[k] is None for k in required) for r in rows):
        raise ValueError('malformed registry row')
    by_dir = {}
    for r in rows:
        p = r["path"].strip().rstrip("/")
        if p.startswith("experiments/") and p.count("/") == 1:
            by_dir.setdefault(p.split("/")[1], []).append(r)
    dirs = sorted(PurePosixPath(d).name for d in source.directories
                  if len(PurePosixPath(d).parts) == 2 and d.startswith('experiments/')
                  and not PurePosixPath(d).name.startswith('.'))
    num = lambda r: int(r["id"][1:]) if r["id"][1:].isdigit() else 0
    lanes = sorted((d for d in dirs if d in by_dir), key=lambda d: -max(num(r) for r in by_dir[d]))
    L = ["# Experiments", "", HEAD, INDEX_NOTE, "",
         "One folder per lane. A lane is frozen (`PREREG.md`) before any statistic and reports in `FINDINGS.md`; a",
         "forward paper lane also keeps a `journal/`. The ids, statuses and trial counts come from",
         "[`registry/rounds.csv`](../registry/rounds.csv). Newest first.", "",
         "Status: RUNNING, DONE, ARMED (waits for an event), REGISTERED or PLANNED.",
         "Verdict: CONFIRMED, PARTIAL, NULL, DATA_PASS (a measurement), PENDING.", "",
         "These are recorded statuses, not process-health or freshness checks. Running rounds can include a reserved",
         "batch or a measurement; this heading does not turn them into forward paper evidence.", ""]
    groups = [("Running or armed registered rounds", [d for d in lanes if any(r["status"] in ("RUNNING", "ARMED")
                                                                          for r in by_dir[d])]),
              ("Other registered rounds (done, registered or planned)", [d for d in lanes if all(r["status"] not in ("RUNNING", "ARMED")
                                                                            for r in by_dir[d])])]
    for title, ds in groups:
        L += [f"## {title} ({len(ds)})", ""]
        for d in ds:
            for r in sorted(by_dir[d], key=num, reverse=True):
                links = [f"[{f.split('.')[0]}]({d}/{f})" for f in ("PREREG.md", "FINDINGS.md")
                         if f'experiments/{d}/{f}' in source.files]
                if f'experiments/{d}/journal' in source.directories:
                    links.append(f"[journal]({d}/journal/)")
                n = int(r["trials"]) if r["trials"] else None
                trials = "trials not set" if n is None else f"{n:,} trial" + ("" if n == 1 else "s")
                L.append(f"- **[{d}]({d}/)** {r['id']}, {r['status']} {r['verdict']}, {trials}. {r['title'].strip()}"
                         + (f" ({', '.join(links)})" if links else ""))
        L.append("")
    missing = sorted(set(by_dir) - set(dirs), key=lambda d: -max(num(r) for r in by_dir[d]))
    L += [f"## Registered rounds with no local folder ({sum(len(by_dir[d]) for d in missing)})", "",
          "The registry retains these rounds. Missing local evidence may be a legacy import or an incomplete checkout;",
          "it is neither a null result nor permission to recreate the round. Paths below are declarations, not links.", ""]
    for d in missing:
        for r in sorted(by_dir[d], key=num, reverse=True):
            L.append(f"- **{r['id']}** `{r['path']}`: {r['status']} {r['verdict']}. {r['title'].strip()}")
    other = [d for d in dirs if d not in by_dir]
    collection = [d for d in other if d in NOT_ROUNDS]
    unregistered = [d for d in other if d not in NOT_ROUNDS]
    L += ["", f"## Collection and loop folders ({len(collection)})", ""]
    L += [f"- **[{d}]({d}/)** {NOT_ROUNDS[d]}" for d in collection]
    L += ["", f"## Unregistered folders ({len(unregistered)})", "",
          "These have no registry row and are not classified as collection folders. Inspect their scope and freeze",
          "state before use; their presence does not establish a registered or completed study.", ""]
    L += [f"- **[{d}]({d}/)** No registry row; scope unclassified." for d in unregistered]
    return "\n".join(L).rstrip() + "\n", (len(lanes), len(other))


def script_catalog(root, source=None):
    source = source if source is not None else IndexSnapshot(root)
    files = sorted(PurePosixPath(p) for p in source.files if len(PurePosixPath(p).parts) == 2
                   and p.startswith('scripts/') and Path(p).suffix in ('.py', '.sh')
                   and Path(p).name != '__init__.py')
    seen, L = set(), ["# Scripts", "", HEAD, INDEX_NOTE, "",
                      "Everything here is run from the repository root, e.g. `python scripts/<name>.py --help`. Each",
                      "line is the first line of the script's own docstring.", ""]
    for heading, test in KINDS + [("Tools and everything else", lambda n: True)]:
        mine = [f for f in files if f.name not in seen and test(f.name)]
        if not mine:
            continue
        seen |= {f.name for f in mine}
        L += [f"## {heading} ({len(mine)})", ""]
        L += [f"- [`{f.name}`]({f.name}): {first_line(source.read(str(f)), f.suffix) or 'no description yet'}" for f in mine]
        L.append("")
    return "\n".join(L), len(files)


def library_catalog(root, source=None):
    source = source if source is not None else IndexSnapshot(root)
    files = sorted(PurePosixPath(p) for p in source.files if len(PurePosixPath(p).parts) == 2
                   and p.startswith('lab/') and p.endswith('.py') and Path(p).name != '__init__.py')
    L = ["# lab: the research library", "", HEAD, INDEX_NOTE, "",
         "Imported as `from lab import <module>`. Tests are in `tests/test_<module>.py`; run them all with",
         "`python -m unittest discover -s tests -t .` before committing a change here.", ""]
    L += [f"- [`{f.stem}`]({f.name}): {first_line(source.read(str(f)), f.suffix) or 'no description yet'}" for f in files]
    return "\n".join(L) + "\n", len(files)


def output_path(root, relative):
    root = Path(root).resolve()
    parts = PurePosixPath(relative).parts
    if PurePosixPath(relative).is_absolute() or '..' in parts or '\\' in relative:
        raise ValueError('unsafe catalog output')
    for n in range(1, len(parts) + 1):
        if root.joinpath(*parts[:n]).is_symlink():
            raise ValueError('catalog output or parent is a symlink: ' + relative)
    target = root / relative
    if not target.parent.is_dir() or target.exists() and not target.is_file():
        raise ValueError('regular catalog output directory/file required: ' + relative)
    return target


def publish(root, views, check=False):
    # Validate every destination and render every view before replacing anything.
    targets = {p: output_path(root, p) for p in views}
    stale = [p for p, target in targets.items()
             if not target.exists() or target.read_bytes() != views[p].encode('utf-8')]
    if check:
        for p in stale:
            print('STALE ' + p)
        return stale
    for p in stale:
        target = output_path(root, p)
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        fd, name = tempfile.mkstemp(prefix='.catalog-', suffix='.tmp', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                os.fchmod(handle.fileno(), mode)
                handle.write(views[p].encode('utf-8'))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return stale


def experiments():
    text, counts = experiment_catalog(ROOT)
    publish(ROOT, {'experiments/README.md': text})
    return counts


def scripts():
    text, count = script_catalog(ROOT)
    publish(ROOT, {'scripts/README.md': text})
    return count


def lab():
    text, count = library_catalog(ROOT)
    publish(ROOT, {'lab/README.md': text})
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        source = IndexSnapshot(args.root)
        exp, (lanes, other) = experiment_catalog(args.root, source)
        commands, script_count = script_catalog(args.root, source)
        library, module_count = library_catalog(args.root, source)
        stale = publish(args.root, {'experiments/README.md': exp, 'scripts/README.md': commands,
                                   'lab/README.md': library}, check=args.check)
        if args.check:
            if not stale:
                print('Catalogs match the Git index.')
            return 1 if stale else 0
        print(f"experiments/README.md: {lanes} registered local folders, {other} other folders; "
              f"scripts/README.md: {script_count} scripts; lab/README.md: {module_count} modules")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('Catalog: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
