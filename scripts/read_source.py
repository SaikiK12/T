"""Cheap, targeted reading of long sources (books, papers, docs): locate the pages that matter, then read only those.

Why: reading PDFs page-image by page-image costs many tokens, and most pages of a book do not bear on the question.
Plain text from `pdftotext`, cut to the pages that match the question's terms, costs a small fraction.

Commands (all print compact text to stdout; nothing is written in the repository):
- `fetch URL`: download into its own new folder under the cache, then extract text page by page. It prints the
  cache id, the page count and the first contents lines. PDFs are treated as untrusted data: never executed.
- `locate ID TERM [TERM ...] [--top 8]`: score pages by how many distinct terms they hit (then by hit count), and
  print the top pages with one short snippet per term.
- `pages ID 12-14 30 [--max-chars 6000]`: print the text of those pages, whitespace squeezed, capped at max-chars.
- `toc ID [--pages 1-12]`: print the lines that look like a table of contents from the first pages.

Cache: $READ_CACHE or the session scratchpad (`.../scratchpad/read_cache`). Local PDFs can be read with `fetch PATH`.

usage: python scripts/read_source.py fetch https://arxiv.org/pdf/1012.0349
       python scripts/read_source.py locate 3f2a9c1b "queue" "fill probability" "adverse selection"
       python scripts/read_source.py pages 3f2a9c1b 12-13
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("READ_CACHE", "/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/"
                                         "scratchpad/read_cache"))
UA = {"User-Agent": "curl/8.5.0"}


def cache_id(src):
    return hashlib.sha256(src.encode()).hexdigest()[:10]


def squeeze(text):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch(src):
    cid = cache_id(src)
    d = CACHE / cid
    if (d / "meta.json").exists():
        return json.loads((d / "meta.json").read_text())
    d.mkdir(parents=True, exist_ok=True)
    pdf = d / "source.pdf"
    if Path(src).exists():
        shutil.copy(src, pdf)
    else:
        with urllib.request.urlopen(urllib.request.Request(src, headers=UA), timeout=120) as r, pdf.open("wb") as f:
            shutil.copyfileobj(r, f)
    if pdf.read_bytes()[:5] != b"%PDF-":
        raise SystemExit(f"{src}: not a PDF (an HTML page or a block); read it with a web fetch instead")
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, timeout=60).stdout
    n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    pages = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True,
                           text=True, timeout=60).stdout
        pages.append(squeeze(t))
    (d / "pages.json").write_text(json.dumps(pages))
    meta = {"id": cid, "source": src, "pages": n, "chars": sum(len(p) for p in pages)}
    (d / "meta.json").write_text(json.dumps(meta))
    return meta


def load(cid):
    p = CACHE / cid / "pages.json"
    if not p.exists():
        raise SystemExit(f"unknown id {cid}: run fetch first")
    return json.loads(p.read_text())


def locate(cid, terms, top=8, snippet=160):
    pages = load(cid)
    pats = [re.compile(re.escape(t), re.I) for t in terms]
    scored = []
    for i, text in enumerate(pages, start=1):
        hits = [len(p.findall(text)) for p in pats]
        if any(hits):
            scored.append((sum(h > 0 for h in hits), sum(hits), i))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
    out = []
    for distinct, total, i in scored[:top]:
        text = pages[i - 1]
        snips = []
        for t, p in zip(terms, pats):
            m = p.search(text)
            if m:
                a = max(0, m.start() - snippet // 2)
                snips.append(f"  [{t}] …{text[a:a + snippet].replace(chr(10), ' ')}…")
        out.append(f"p.{i}: {distinct}/{len(terms)} terms, {total} hits\n" + "\n".join(snips))
    return "\n".join(out) if out else "no page matches"


def parse_pages(specs):
    out = []
    for s in specs:
        if "-" in s:
            a, b = s.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(s))
    return out


def pages_text(cid, specs, max_chars=6000):
    pages = load(cid)
    out, used = [], 0
    for i in parse_pages(specs):
        if not 1 <= i <= len(pages):
            continue
        t = pages[i - 1]
        room = max_chars - used
        if room <= 0:
            out.append(f"[cap of {max_chars} chars reached before p.{i}]")
            break
        out.append(f"=== p.{i} ===\n{t[:room]}")
        used += min(len(t), room)
    return "\n".join(out)


def toc(cid, spec="1-12"):
    pages = load(cid)
    lines = []
    for i in parse_pages([spec]):
        if 1 <= i <= len(pages):
            lines += [ln for ln in pages[i - 1].split("\n") if re.search(r"(\.{3,}|\s\d{1,4}$)", ln)]
    return "\n".join(lines[:120]) or "no contents-like lines found"


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("src")
    lo = sub.add_parser("locate")
    lo.add_argument("id")
    lo.add_argument("terms", nargs="+")
    lo.add_argument("--top", type=int, default=8)
    pg = sub.add_parser("pages")
    pg.add_argument("id")
    pg.add_argument("pages", nargs="+")
    pg.add_argument("--max-chars", type=int, default=6000)
    tc = sub.add_parser("toc")
    tc.add_argument("id")
    tc.add_argument("--pages", default="1-12")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        m = fetch(a.src)
        print(json.dumps(m))
        print(toc(m["id"], "1-8")[:1500])
    elif a.cmd == "locate":
        print(locate(a.id, a.terms, a.top))
    elif a.cmd == "pages":
        print(pages_text(a.id, a.pages, a.max_chars))
    else:
        print(toc(a.id, a.pages))


if __name__ == "__main__":
    main()
