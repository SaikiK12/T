"""Plain-language catalogs of the repository's folders, rebuilt from what the files already say:

- experiments/README.md: every lane folder with its round id, status, verdict, trial count and title, from
  registry/rounds.csv (newest first), and links to its PREREG, FINDINGS and journal;
- scripts/README.md: every script by kind (fetch, record, run, forward, check and tools), with the first line of its
  docstring or header comment;
- lab/README.md: every module of the research library with the first line of its docstring.

It decides nothing and reads no data. Rerun it whenever a round, a script or a module is added; the loop runs it
each tick.

usage: python scripts/catalog.py
"""
import ast
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = "<!-- written by scripts/catalog.py; edit the sources (registry, docstrings), not this file -->\n"
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


def first_line(path):
    """The first sentence-line of a Python module's docstring or a shell script's header comment."""
    text = path.read_text(errors="replace")
    if path.suffix == ".py":
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


def experiments():
    rows = list(csv.DictReader(open(ROOT / "registry" / "rounds.csv", newline="")))
    by_dir = {}
    for r in rows:
        p = r["path"].strip().rstrip("/")
        if p.startswith("experiments/") and p.count("/") == 1:
            by_dir.setdefault(p.split("/")[1], []).append(r)
    dirs = sorted(d.name for d in (ROOT / "experiments").iterdir() if d.is_dir() and not d.name.startswith("."))
    num = lambda r: int(r["id"][1:]) if r["id"][1:].isdigit() else 0
    lanes = sorted((d for d in dirs if d in by_dir), key=lambda d: -max(num(r) for r in by_dir[d]))
    L = ["# Experiments", "", HEAD,
         "One folder per lane. A lane is frozen (`PREREG.md`) before any statistic and reports in `FINDINGS.md`; a",
         "forward paper lane also keeps a `journal/`. The ids, statuses and trial counts come from",
         "[`registry/rounds.csv`](../registry/rounds.csv). Newest first.", "",
         "Status: RUNNING (forward, collecting days), DONE, ARMED (waits for an event), REGISTERED or PLANNED.",
         "Verdict: CONFIRMED, PARTIAL, NULL, DATA_PASS (a measurement), PENDING.", ""]
    groups = [("Forward paper lanes (running)", [d for d in lanes if any(r["status"] in ("RUNNING", "ARMED")
                                                                          for r in by_dir[d])]),
              ("Finished and registered rounds", [d for d in lanes if all(r["status"] not in ("RUNNING", "ARMED")
                                                                            for r in by_dir[d])])]
    for title, ds in groups:
        L += [f"## {title} ({len(ds)})", ""]
        for d in ds:
            for r in sorted(by_dir[d], key=num, reverse=True):
                links = [f"[{f.split('.')[0]}]({d}/{f})" for f in ("PREREG.md", "FINDINGS.md")
                         if (ROOT / "experiments" / d / f).exists()]
                if (ROOT / "experiments" / d / "journal").is_dir():
                    links.append(f"[journal]({d}/journal/)")
                n = int(r["trials"]) if r["trials"] else None
                trials = "trials not set" if n is None else f"{n:,} trial" + ("" if n == 1 else "s")
                L.append(f"- **[{d}]({d}/)** {r['id']}, {r['status']} {r['verdict']}, {trials}. {r['title'].strip()}"
                         + (f" ({', '.join(links)})" if links else ""))
        L.append("")
    other = [d for d in dirs if d not in by_dir]
    L += [f"## Data and loop folders ({len(other)})", ""]
    L += [f"- **[{d}]({d}/)** {NOT_ROUNDS.get(d, 'No registry row and no description yet.')}" for d in other]
    (ROOT / "experiments" / "README.md").write_text("\n".join(L) + "\n")
    return len(lanes), len(other)


def scripts():
    files = sorted(f for f in (ROOT / "scripts").iterdir() if f.suffix in (".py", ".sh") and f.name != "__init__.py")
    seen, L = set(), ["# Scripts", "", HEAD,
                      "Everything here is run from the repository root, e.g. `python scripts/<name>.py --help`. Each",
                      "line is the first line of the script's own docstring.", ""]
    for heading, test in KINDS + [("Tools and everything else", lambda n: True)]:
        mine = [f for f in files if f.name not in seen and test(f.name)]
        if not mine:
            continue
        seen |= {f.name for f in mine}
        L += [f"## {heading} ({len(mine)})", ""]
        L += [f"- [`{f.name}`]({f.name}): {first_line(f) or 'no description yet'}" for f in mine]
        L.append("")
    (ROOT / "scripts" / "README.md").write_text("\n".join(L))
    return len(files)


def lab():
    files = sorted(f for f in (ROOT / "lab").glob("*.py") if f.name != "__init__.py")
    L = ["# lab: the research library", "", HEAD,
         "Imported as `from lab import <module>`. Tests are in `tests/test_<module>.py`; run them all with",
         "`python -m unittest discover -s tests -t .` before committing a change here.", ""]
    L += [f"- [`{f.stem}`]({f.name}): {first_line(f) or 'no description yet'}" for f in files]
    (ROOT / "lab" / "README.md").write_text("\n".join(L) + "\n")
    return len(files)


def main():
    lanes, other = experiments()
    print(f"experiments/README.md: {lanes} lanes, {other} data folders; "
          f"scripts/README.md: {scripts()} scripts; lab/README.md: {lab()} modules")


if __name__ == "__main__":
    main()
