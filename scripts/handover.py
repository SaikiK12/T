"""Hand-over tooling: what lives outside git, and how to get it back without Claude.

`data/` is gitignored (13 GB here). registry/data_manifest.csv classifies every entry in it:
  REFETCH   public history that scripts in this repo download again (docs/DATA_SOURCES.md has the source, the script and
            the sha256 in docs/provenance/<folder>.json)
  RECORDED  a live capture of a public stream that no endpoint serves again: the only copy is on the machine that
            recorded it, so `pack` copies it into chunks that can be pushed or carried away
  DERIVED   rebuilt from other data by frozen code
  LICENSED  a vendor's data (CME via Databento): never committed or archived; the exact requests are in its manifest
  SCRATCH   logs, locks and third-party text; not worth keeping

usage:
  python scripts/handover.py status                       # sizes per class; unclassified entries; what is absent
  python scripts/handover.py commands [--missing]         # the commands that restore REFETCH / DERIVED folders
  python scripts/handover.py pack --out DIR [--max-chunk-mb 50] [--budget-mb N] [--min-age-min 15] [--public] [--exclude data/x]
  python scripts/handover.py restore --src DIR [--force]  # put a packed archive back into data/

`pack` is incremental: a file already in DIR/files.csv with the same size and mtime is skipped, a changed file goes into a
new chunk, and a file above 95 MB (GitHub's limit is 100 MB) is reported and left out. Files younger than --min-age-min
minutes, locks, pids, logs and the daemons' status.json are never read, so a running recorder is not disturbed. `restore`
checks every chunk's sha256 and every file's sha256, rejects any member outside data/, and never overwrites a file that
differs unless --force. --public leaves out data/news (third-party text) for an archive that goes on the public repo.
Nothing here reads a key or places an order, and nothing is deleted.
"""
import argparse
import csv
import hashlib
import io
import os
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "registry" / "data_manifest.csv"
CLASSES = ("REFETCH", "RECORDED", "DERIVED", "LICENSED", "SCRATCH")
MAX_FILE_MB = 95
PUBLIC_EXCLUDE = ("data/news",)      # third-party news text: kept in a private archive, not on the public branch
SKIP_SUFFIX = (".lock", ".tmp", ".pid", ".log", ".part")
SKIP_NAME = {"status.json"}
FILE_COLS = ["path", "size", "mtime_ns", "sha256", "chunk"]
CHUNK_COLS = ["chunk", "bytes", "sha256", "files", "created_utc"]


def load_manifest(path=MANIFEST):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r["class"] not in CLASSES:
            raise SystemExit(f"{path}: {r['path']} has class {r['class']!r}, not one of {CLASSES}")
    return rows


def classify(rel, rows):
    """The class of a path relative to the checkout (longest manifest prefix wins), or None when it is not listed."""
    best = None
    for r in rows:
        p = r["path"].rstrip("/")
        if rel == p or rel.startswith(p + "/"):
            if best is None or len(p) > len(best["path"].rstrip("/")):
                best = r
    return best["class"] if best else None


def skipped(name):
    return name.startswith(".") or name in SKIP_NAME or name.endswith(SKIP_SUFFIX)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def walk(root):
    """Every regular file under root/data as (relative path, size, mtime_ns); symlinks are never followed."""
    base = Path(root) / "data"
    stack = [base]
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                stack.append(Path(e.path))
            elif e.is_file(follow_symlinks=False):
                st = e.stat(follow_symlinks=False)
                yield Path(e.path).relative_to(root).as_posix(), st.st_size, st.st_mtime_ns


def status(root, rows):
    """Totals per class, the data/ entries the manifest does not list, and the listed ones that are absent."""
    totals = {c: [0, 0] for c in CLASSES}
    unclassified = {}
    for rel, size, _ in walk(root):
        c = classify(rel, rows)
        if c is None:
            top = "/".join(rel.split("/")[:2])
            unclassified[top] = unclassified.get(top, 0) + size
        else:
            totals[c][0] += 1
            totals[c][1] += size
    absent = [r["path"] for r in rows if not (Path(root) / r["path"]).exists()]
    return totals, unclassified, absent


def read_csv(path, cols):
    if not Path(path).exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def append_csv(path, cols, rows):
    new = not Path(path).exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(cols)
        w.writerows([[r[c] for c in cols] for r in rows])


def excluded(rel, exclude):
    return any(rel == p.rstrip("/") or rel.startswith(p.rstrip("/") + "/") for p in exclude)


def candidates(root, rows, now, min_age_s, exclude=()):
    for rel, size, mtime in walk(root):
        if classify(rel, rows) != "RECORDED" or skipped(os.path.basename(rel)) or excluded(rel, exclude):
            continue
        if now - mtime / 1e9 < min_age_s:
            continue
        yield rel, size, mtime


def pack(root, out, rows, max_chunk_mb=50, budget_mb=None, min_age_min=15, now=None, exclude=()):
    """Copy RECORDED files not yet archived into tar.gz chunks under out; returns a summary dict.
    exclude: path prefixes left out (PUBLIC_EXCLUDE for an archive that goes on a public branch)."""
    now = time.time() if now is None else now
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    files = read_csv(out / "files.csv", FILE_COLS)
    chunks = read_csv(out / "chunks.csv", CHUNK_COLS)
    seen = {(r["path"], int(r["size"]), int(r["mtime_ns"])) for r in files}
    known = {(r["path"], r["sha256"]) for r in files}
    used = sum(int(c["bytes"]) for c in chunks)
    budget = None if budget_mb is None else int(budget_mb * 1e6)
    seq = seq0 = max([int(c["chunk"].split("-")[1].split(".")[0]) for c in chunks], default=0)
    todo, oversize, unchanged = [], [], 0
    for rel, size, mtime in sorted(candidates(root, rows, now, min_age_min * 60, exclude)):
        if (rel, size, mtime) in seen:
            unchanged += 1
        elif size > MAX_FILE_MB * 1_000_000:
            oversize.append(rel)
        else:
            todo.append((rel, size, mtime))
    limit = int(max_chunk_mb * 1e6)
    added, left, batch, batch_bytes = [], [], [], 0

    def flush():
        nonlocal seq, used, batch, batch_bytes
        if not batch:
            return True
        if budget is not None and used + batch_bytes > budget:
            return False
        seq += 1
        name = f"chunk-{seq:05d}.tar.gz"
        tmp = out / (name + ".tmp")
        rowsout = []
        with tarfile.open(tmp, "w:gz") as tar:
            for rel, size, mtime in batch:
                data = (Path(root) / rel).read_bytes()
                sha = hashlib.sha256(data).hexdigest()
                if (rel, sha) in known:
                    continue
                info = tarfile.TarInfo(rel)
                info.size, info.mtime, info.mode = len(data), mtime // 10**9, 0o644
                tar.addfile(info, io.BytesIO(data))
                known.add((rel, sha))
                rowsout.append({"path": rel, "size": len(data), "mtime_ns": mtime, "sha256": sha, "chunk": name})
        if not rowsout:
            tmp.unlink()
            seq -= 1
            batch, batch_bytes = [], 0
            return True
        tmp.rename(out / name)
        nbytes = (out / name).stat().st_size
        used += nbytes
        append_csv(out / "files.csv", FILE_COLS, rowsout)
        append_csv(out / "chunks.csv", CHUNK_COLS, [{"chunk": name, "bytes": nbytes, "sha256": sha256_file(out / name),
                                                     "files": len(rowsout),
                                                     "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}])
        added.extend(r["path"] for r in rowsout)
        batch, batch_bytes = [], 0
        return True

    for item in todo:
        if batch and batch_bytes + item[1] > limit:
            if not flush():
                left.extend(i[0] for i in batch)
                batch, batch_bytes = [], 0
        if budget is not None and left:
            left.append(item[0])
            continue
        batch.append(item)
        batch_bytes += item[1]
    if not flush():
        left.extend(i[0] for i in batch)
    return {"added": len(added), "chunks": seq - seq0, "unchanged": unchanged, "oversize": oversize,
            "over_budget": left, "archive_bytes": used}


def safe_member(m):
    parts = Path(m.name).parts
    return m.isfile() and parts[:1] == ("data",) and ".." not in parts and not os.path.isabs(m.name)


def restore(src, root, force=False):
    """Unpack the archive in src into root/data; returns (written, skipped, problems)."""
    src, root = Path(src), Path(root)
    chunks = sorted(read_csv(src / "chunks.csv", CHUNK_COLS), key=lambda c: c["chunk"])
    want = {(r["chunk"], r["path"]): r["sha256"] for r in read_csv(src / "files.csv", FILE_COLS)}
    written, skipped, problems, mine = 0, 0, [], set()
    for c in chunks:
        path = src / c["chunk"]
        if not path.exists() or sha256_file(path) != c["sha256"]:
            problems.append(f"{c['chunk']}: missing or its sha256 differs from chunks.csv")
            continue
        with tarfile.open(path, "r:gz") as tar:
            for m in tar:
                if not safe_member(m):
                    problems.append(f"{c['chunk']}: refused member {m.name!r}")
                    continue
                data = tar.extractfile(m).read()
                sha = hashlib.sha256(data).hexdigest()
                if want.get((c["chunk"], m.name)) != sha:
                    problems.append(f"{c['chunk']}: {m.name} does not match files.csv")
                    continue
                dest = root / m.name
                if dest.exists() and m.name not in mine and not force:
                    if sha256_file(dest) == sha:
                        skipped += 1
                    else:
                        problems.append(f"{m.name}: exists and differs; kept (use --force to replace)")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_name(dest.name + ".restore")
                tmp.write_bytes(data)
                os.utime(tmp, (m.mtime, m.mtime))
                tmp.rename(dest)
                mine.add(m.name)
                written += 1
    return written, skipped, problems


def human(n):
    return f"{n / 1e6:,.0f} MB" if n < 1e9 else f"{n / 1e9:,.2f} GB"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("commands")
    p.add_argument("--missing", action="store_true", help="only folders that are not on disk")
    p = sub.add_parser("pack")
    p.add_argument("--out", required=True)
    p.add_argument("--max-chunk-mb", type=float, default=50)
    p.add_argument("--budget-mb", type=float)
    p.add_argument("--min-age-min", type=float, default=15)
    p.add_argument("--exclude", action="append", default=[], metavar="PREFIX", help="leave out this data/ path (repeatable)")
    p.add_argument("--public", action="store_true", help="for a public branch: also leave out " + ", ".join(PUBLIC_EXCLUDE))
    p = sub.add_parser("restore")
    p.add_argument("--src", required=True)
    p.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    rows = load_manifest()
    if a.cmd == "status":
        totals, unclassified, absent = status(ROOT, rows)
        for c in CLASSES:
            print(f"{c:9} {totals[c][0]:>8,} files  {human(totals[c][1])}")
        for top, size in sorted(unclassified.items()):
            print(f"UNCLASSIFIED {top} {human(size)}: add it to registry/data_manifest.csv")
        for r in rows:
            if r["path"] in absent:
                print(f"absent  {r['class']:9} {r['path']}")
        return 1 if unclassified else 0
    if a.cmd == "commands":
        for r in rows:
            if r["class"] in ("RECORDED", "SCRATCH"):
                continue
            if a.missing and (ROOT / r["path"]).exists():
                continue
            print(f"{r['path']:34} {r['class']:9} {r['restore']}")
        return 0
    if a.cmd == "pack":
        s = pack(ROOT, a.out, rows, a.max_chunk_mb, a.budget_mb, a.min_age_min,
                 exclude=tuple(a.exclude) + (PUBLIC_EXCLUDE if a.public else ()))
        print(f"added {s['added']} files in {s['chunks']} new chunk(s); {s['unchanged']} unchanged; archive {human(s['archive_bytes'])}")
        for rel in s["oversize"]:
            print(f"NOT ARCHIVED (above {MAX_FILE_MB} MB): {rel}")
        for rel in s["over_budget"]:
            print(f"NOT ARCHIVED (over budget): {rel}")
        return 0
    written, skipped, problems = restore(a.src, ROOT, a.force)
    print(f"restored {written} files; {skipped} already present and identical")
    for pr in problems:
        print("PROBLEM", pr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
