"""Provenance record for a downloaded data folder (docs/DATA_PROVENANCE_AUDIT.md): every file's size and sha256, a
combined digest, file counts per subfolder, and for hourly parquet folders the bar coverage per file (first and last
open time, bars present, interior holes). Writes docs/provenance/<name>.json; data/ itself is gitignored.

usage: python scripts/data_provenance.py data/mexc_hist --source "https://contract.mexc.com (public)" \
           --script scripts/fetch_mexc_history.py
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
H = 3_600_000


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def coverage(path):
    """Hourly coverage of a parquet with an open-time column t (ms); None for other files."""
    try:
        t = pd.read_parquet(path, columns=["t"]).t.astype("int64").sort_values().values
    except (KeyError, ValueError, OSError):
        return None
    if len(t) == 0:
        return {"bars": 0}
    span = int((t[-1] - t[0]) // H) + 1
    return {"first": int(t[0]), "last": int(t[-1]), "bars": int(len(t)), "holes": span - len(set(t.tolist()))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--source", default="")
    ap.add_argument("--script", default="")
    ap.add_argument("--hourly", nargs="*", default=None, help="subfolders holding hourly parquet (default: *_1h)")
    a = ap.parse_args()
    folder = Path(a.folder).resolve()
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    rows, combined, cov = [], hashlib.sha256(), {}
    for p in files:
        rel = p.relative_to(folder).as_posix()
        d = sha256(p)
        rows.append({"path": rel, "bytes": p.stat().st_size, "sha256": d})
        combined.update(f"{rel}\t{d}\n".encode())
        sub = rel.split("/")[0] if "/" in rel else ""
        hourly = sub in a.hourly if a.hourly is not None else sub.endswith("_1h")
        if hourly and p.suffix == ".parquet":
            c = coverage(p)
            if c is not None:
                cov.setdefault(sub, {})[p.stem] = c
    per_sub = {}
    for r in rows:
        sub = r["path"].split("/")[0] if "/" in r["path"] else "."
        s = per_sub.setdefault(sub, {"files": 0, "bytes": 0})
        s["files"] += 1
        s["bytes"] += r["bytes"]
    summary = {}
    for sub, c in cov.items():
        v = list(c.values())
        summary[sub] = {"files": len(v), "bars": sum(x.get("bars", 0) for x in v),
                        "files_with_holes": sum(1 for x in v if x.get("holes", 0) > 0),
                        "holes": sum(x.get("holes", 0) for x in v),
                        "first": min((x["first"] for x in v if "first" in x), default=None),
                        "last": max((x["last"] for x in v if "last" in x), default=None)}
    out = {"folder": folder.relative_to(ROOT).as_posix(), "source": a.source, "script": a.script,
           "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": len(rows),
           "bytes": sum(r["bytes"] for r in rows), "combined_sha256": combined.hexdigest(),
           "subfolders": per_sub, "hourly_coverage": summary, "coverage": cov, "file_hashes": rows}
    dest = ROOT / "docs" / "provenance" / f"{folder.name}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=0) + "\n")
    print(json.dumps({k: out[k] for k in ("folder", "files", "bytes", "combined_sha256", "subfolders",
                                          "hourly_coverage")}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
