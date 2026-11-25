"""Mechanical check of a report's citations: does each cited file and line exist, and does the quoted text appear
there? It turns verification of a Haiku room report from reading into a table, so the lead researcher spends attention
only on the claims that fail or that move money (owner 2026-11-25: "si c'est la vérif qui limite, débloque-la").

A citation is `path:LINE` or `path:START-END` (backticked or not; path relative to the repo root, or absolute). A quote
is text in "..." or “...” on the same line as the citation. Statuses:
- verified: the quote appears within ±8 lines of the cited lines;
- quote elsewhere: the quote appears in the file, but not near the cited lines;
- quote missing: the quote is not in the file;
- located: no quote given; the file and lines exist;
- bad line: the line number is past the end of the file;
- no file: the path does not exist.

External sources (papers) have no repo path. With `--corpus DIR`, every quote on a line with no path:line citation is
searched in the .txt files under DIR (text extracted from the PDFs, e.g. `pdftotext` without `-layout`, so sentences
keep their reading order). Ligatures, hyphenation at line ends, curly quotes and the Unicode minus are normalized.
Statuses: in corpus (with the file), not in corpus.

usage: python scripts/verify_citations.py REPORT.md [REPORT.md ...] [--fails] [--corpus DIR]
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CITE = re.compile(r"`?((?:/[\w.\-]+)+|[\w.\-]+(?:/[\w.\-]+)+\.(?:md|py|csv|toml|yml|yaml|json|txt))`?:(\d+)(?:\s*[-–]\s*(\d+))?")
QUOTE = re.compile(r"[\"“]([^\"”]{8,})[\"”]")
NEAR = 8


LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "−": "-", "–": "-", "—": "-", "∗": "*",
             "“": '"', "”": '"'}


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")).strip().lower()


def norm_pdf(s):
    """Normalize extracted PDF text: ligatures, dashes, hyphenation at line ends, then norm()."""
    for k, v in LIGATURES.items():
        s = s.replace(k, v)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    return norm(s)


def load_corpus(d):
    """{file name: normalized text} for every .txt under d."""
    return {str(f.relative_to(d)): norm_pdf(f.read_text(errors="ignore")) for f in sorted(Path(d).rglob("*.txt"))}


def check_corpus(line, corpus):
    """Quotes on a line without a repo citation, looked up in the corpus: [(status, file, quote)]."""
    if CITE.search(line):
        return []
    out = []
    for q in QUOTE.findall(line):
        q2 = norm_pdf(q)[:120]
        hit = next((name for name, text in corpus.items() if q2 in text), None)
        out.append(("in corpus", hit, q2[:80]) if hit else ("not in corpus", "", q2[:80]))
    return out


def resolve(p):
    q = Path(p)
    return q if q.is_absolute() else ROOT / q


def check_line(line, base):
    out = []
    quotes = [norm(q) for q in QUOTE.findall(line)]
    for m in CITE.finditer(line):
        path, a, b = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
        f = resolve(path)
        if not f.exists() and not Path(path).is_absolute():
            f2 = (base.parent / path)
            f = f2 if f2.exists() else f
        if not f.exists():
            out.append((path, a, b, "no file", ""))
            continue
        try:
            lines = f.read_text(errors="ignore").splitlines()
        except OSError:
            out.append((path, a, b, "no file", ""))
            continue
        if a > len(lines):
            out.append((path, a, b, "bad line", ""))
            continue
        if not quotes:
            out.append((path, a, b, "located", ""))
            continue
        window = norm(" ".join(lines[max(0, a - 1 - NEAR):min(len(lines), b + NEAR)]))
        whole = norm(" ".join(lines))
        for q in quotes:
            q2 = q[:120]
            st = "verified" if q2 in window else ("quote elsewhere" if q2 in whole else "quote missing")
            out.append((path, a, b, st, q[:80]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+")
    ap.add_argument("--fails", action="store_true", help="list the citations that are not verified or located")
    ap.add_argument("--corpus", help="directory of .txt files extracted from the cited papers")
    a = ap.parse_args()
    corpus = load_corpus(a.corpus) if a.corpus else None
    total = {}
    for r in a.reports:
        rp = Path(r)
        counts, fails = {}, []
        for i, line in enumerate(rp.read_text(errors="ignore").splitlines(), 1):
            for path, s, e, st, q in check_line(line, rp):
                counts[st] = counts.get(st, 0) + 1
                total[st] = total.get(st, 0) + 1
                if st not in ("verified", "located"):
                    fails.append(f"  {rp.name}:{i}  {path}:{s}-{e}  {st}  {q}")
            for st, name, q in (check_corpus(line, corpus) if corpus is not None else []):
                counts[st] = counts.get(st, 0) + 1
                total[st] = total.get(st, 0) + 1
                if st == "not in corpus":
                    fails.append(f"  {rp.name}:{i}  {st}  {q}")
        print(f"{rp.name}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        if a.fails:
            print("\n".join(fails[:60]))
    print("TOTAL: " + ", ".join(f"{k} {v}" for k, v in sorted(total.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
