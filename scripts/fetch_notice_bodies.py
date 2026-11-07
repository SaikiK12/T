"""Plain text of each Binance delisting article in the notice journal (data/recorders/notices/binance_delisting.csv),
from the public CMS detail endpoint. Some titles do not name the coins ("Binance Futures Will Delist Multiple
Perpetual Contracts"); the body does. One file per article, data/recorders/notices/articles/<id>.txt; existing files
are kept, so a rerun only fetches new articles. Data collection only.

usage: python scripts/fetch_notice_bodies.py [--catalog delisting]
"""
import argparse
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

API = "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={code}"
NOTICES = data.ROOT / "recorders" / "notices"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=4):
    delay = 2.0
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url}: {err}")


def texts(node, out):
    """Text nodes of the CMS body tree, in document order."""
    if isinstance(node, dict):
        if node.get("node") == "text":
            out.append(node.get("text", ""))
        for c in node.get("child") or []:
            texts(c, out)
    return out


def body_text(article):
    body = article.get("body") or ""
    try:
        return " ".join(" ".join(texts(json.loads(body), [])).split())
    except ValueError:  # older articles may carry HTML instead of the JSON tree
        return " ".join(body.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="delisting")
    a = ap.parse_args()
    out = NOTICES / "articles"
    out.mkdir(parents=True, exist_ok=True)
    with (NOTICES / f"binance_{a.catalog}.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    todo = [r for r in rows if not (out / f"{r['id']}.txt").exists()]
    log(f"{len(rows)} articles, {len(todo)} to fetch")
    for i, r in enumerate(todo, 1):
        d = get(API.format(code=r["code"]))["data"]
        tmp = out / f"{r['id']}.tmp"
        tmp.write_text(body_text(d) + "\n")
        tmp.replace(out / f"{r['id']}.txt")
        if i % 50 == 0:
            log(f"{i}/{len(todo)}")
        time.sleep(0.4)
    log("done")


if __name__ == "__main__":
    main()
