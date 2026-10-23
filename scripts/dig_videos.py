"""Dig YouTube for deep, little-watched practitioner videos and keep their captions as searchable text.

The owner's ask (2026-10-21): find people who worked at trading firms and the long videos few people watched, then
read what they actually say about what to trade. Steps:
1. `search`: run every query in QUERIES through yt-dlp's YouTube search (no login) and keep each hit's id, channel,
   title, duration and view count in data/videos/hits.csv (one row per video, the queries that found it joined).
2. `pick`: keep videos at least MIN_MIN minutes long with at most MAX_VIEWS views whose title or channel names a
   trading firm, a practitioner role or a market mechanism (WORDS), ranked by fewest views; write data/videos/pick.csv.
3. `subs`: fetch the English captions (manual first, else automatic) of the picked videos as plain text in
   data/videos/subs/<id>.txt (--ids FILE: a hand-picked subset). YouTube refused this from the lab's machine on
   2026-10-21 (HTTP 429, "confirm you're not a bot"); scripts/dig_podcasts.py reads the same people's podcast feeds.
4. `grep`: print caption passages around the mechanism words in GREP (or --words), per video or podcast episode
   (scripts/dig_podcasts.py writes those), so a reader sees what was said.

Media is never downloaded; captions are text. data/ is gitignored, so docs/VIDEO_DIG.md holds the reading.
yt-dlp runs from a separate tool environment: --ytdlp PATH (default: yt-dlp on PATH).

usage: python scripts/dig_videos.py search|pick|subs|grep [--ytdlp PATH] [--limit N] [--ids FILE]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "videos"
MIN_MIN, MAX_VIEWS, PER_QUERY = 15, 30_000, 25
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

FIRMS = ["jane street", "citadel", "optiver", "susquehanna", "sig ", "jump trading", "drw", "two sigma", "renaissance",
         "millennium", "point72", "de shaw", "hudson river", "virtu", "imc", "flow traders", "akuna", "tower research",
         "goldman", "morgan stanley", "jpmorgan", "wintermute", "gsr", "cumberland", "alameda", "galaxy", "b2c2",
         "bridgewater", "aqr", "man group", "winton", "squarepoint", "qube", "xtx", "headlands", "five rings"]
ROLES = ["former", "ex-", "ex ", "trader", "quant", "market maker", "market making", "portfolio manager", "pod",
         "prop", "desk", "researcher", "head of", "cio", "partner", "hedge fund"]
MECH = ["news", "headline", "event", "earnings", "macro", "cpi", "fomc", "basis", "carry", "funding", "arbitrage",
        "order flow", "orderflow", "order book", "liquidity", "volatility", "vix", "options", "gamma", "skew",
        "momentum", "mean reversion", "stat arb", "statistical arbitrage", "pairs", "rebalanc", "index", "listing",
        "liquidation", "on-chain", "onchain", "latency", "high frequency", "hft", "alpha", "edge", "signal",
        "backtest", "risk", "sizing", "kelly", "crypto", "bitcoin", "perpetual", "futures", "dispersion", "merger"]
WORDS = FIRMS + ROLES + MECH
GREP = ["edge", "alpha", "signal", "news", "headline", "funding", "basis", "carry", "arbitrage", "order flow",
        "order book", "liquidat", "listing", "rebalanc", "mean revers", "momentum", "spread", "latency", "volatility",
        "vix", "gamma", "event", "earnings", "we would", "the trade", "the strategy", "made money", "lost money",
        "nobody", "most people", "retail"]

QUERIES = [
    # people from trading firms, long-form
    "ex jane street trader podcast", "former citadel quant researcher interview", "former optiver trader explains",
    "ex SIG options trader interview", "former jump trading engineer interview", "DRW trader interview",
    "former two sigma quant interview", "renaissance technologies former researcher talk",
    "millennium pod portfolio manager interview", "hudson river trading former interview",
    "former goldman sachs trader explains how desk makes money", "former market maker explains spread capture",
    "crypto market maker interview wintermute", "GSR crypto market making interview", "crypto prop trading firm founder",
    "former hedge fund cio interview process", "quant researcher alpha research process talk",
    "prop trader futures order flow interview", "former bank flow trader explains", "volatility trader former bank vix",
    # news and events
    "news trading futures headline squawk professional", "bloomberg terminal news trading how traders react",
    "trading the cpi release futures professional", "fomc announcement trading strategy professional",
    "event driven trading desk explained", "earnings announcement drift strategy research",
    "crypto news trading bot latency", "trading exchange listing announcements crypto", "upbit listing pump trading",
    "coinbase listing effect trading", "tree of alpha news terminal crypto", "geopolitical headline trading oil",
    # mechanisms
    "funding rate arbitrage crypto desk", "crypto basis trade explained professional", "perpetual futures funding edge",
    "liquidation cascade trading crypto", "statistical arbitrage practitioner talk", "pairs trading crypto practitioner",
    "index rebalancing trade explained", "vix term structure trading strategy", "gamma exposure dealer positioning",
    "dispersion trading explained", "merger arbitrage explained practitioner", "short term reversal strategy research",
    "order book imbalance trading", "market microstructure lecture high frequency", "crypto quant fund strategies",
    "polymarket trading strategy arbitrage", "prediction market arbitrage", "on-chain whale tracking trading strategy",
    "how retail traders lose money research", "quant trading strategy that still works 2026",
]


def ytdlp(args, path):
    r = subprocess.run([path, "--impersonate", "chrome", "--no-warnings", *args], capture_output=True, text=True,
                       timeout=300)
    return r.stdout


def search(path, limit):
    rows = {}
    for i, q in enumerate(QUERIES[:limit] if limit else QUERIES, 1):
        out = ytdlp(["--flat-playlist", "-j", f"ytsearch{PER_QUERY}:{q}"], path)
        n = 0
        for line in out.splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = d.get("id")
            if not vid:
                continue
            r = rows.setdefault(vid, {"id": vid, "channel": d.get("channel") or "", "title": d.get("title") or "",
                                      "duration_s": d.get("duration"), "views": d.get("view_count"), "queries": []})
            r["queries"].append(q)
            n += 1
        log(f"{i}/{len(QUERIES)} {q!r}: {n}")
    df = pd.DataFrame(rows.values())
    df["queries"] = df.queries.map(" | ".join)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "hits.csv", index=False)
    log(f"{len(df)} videos in {OUT / 'hits.csv'}")


def pick():
    df = pd.read_csv(OUT / "hits.csv")
    text = (df.title.fillna("") + " " + df.channel.fillna("")).str.lower()
    hit = text.map(lambda s: sum(w in s for w in WORDS))
    firm = text.map(lambda s: any(w in s for w in FIRMS))
    keep = (df.duration_s >= MIN_MIN * 60) & (df.views <= MAX_VIEWS) & (hit >= 2)
    p = df[keep].assign(words=hit[keep], firm=firm[keep]).sort_values(["firm", "views"], ascending=[False, True])
    p.to_csv(OUT / "pick.csv", index=False)
    log(f"{len(p)} picked of {len(df)} ({int(p.firm.sum())} name a firm)")
    print(p[["views", "duration_s", "channel", "title"]].head(60).to_string(index=False))


def vtt_text(path):
    seen, out = set(), []
    for line in Path(path).read_text(errors="ignore").splitlines():
        if "-->" in line or not line.strip() or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        t = re.sub(r"<[^>]+>", "", line).strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return " ".join(out)


def subs(path, limit, ids=None):
    p = pd.read_csv(OUT / "pick.csv")
    if ids:                                            # a reader's hand-picked subset of pick.csv, in its order
        p = p.set_index("id").loc[[i for i in ids if i in set(p.id)]].reset_index()
    d = OUT / "subs"
    d.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(p.head(limit or len(p)).itertuples(), 1):
        txt = d / f"{r.id}.txt"
        if txt.exists():
            continue
        ytdlp(["--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "en.*,en", "--sub-format", "vtt",
               "-o", str(d / "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={r.id}"], path)
        vtts = sorted(d.glob(f"{r.id}*.vtt"))
        if vtts:
            txt.write_text(vtt_text(vtts[0]))
            for v in vtts:
                v.unlink()
        log(f"{i} {r.id} {'ok' if txt.exists() else 'no captions'} {r.title[:70]}")


def headers():
    """File stem -> one-line header, for videos (pick.csv) and podcast episodes (episodes.csv, scripts/dig_podcasts.py)."""
    out = {}
    if (OUT / "pick.csv").exists():
        for r in pd.read_csv(OUT / "pick.csv").itertuples():
            out[r.id] = f"{r.channel} | {r.title} | {r.views} views | {int(r.duration_s) // 60} min"
    if (OUT / "episodes.csv").exists():
        for r in pd.read_csv(OUT / "episodes.csv").itertuples():
            out[f"pod_{r.key}"] = f"{r.feed} | {r.title} | {str(r.pub_utc)[:10]}"
    return out


def grep(width=220, per_video=12, words=None):
    head_of = headers()
    for txt in sorted((OUT / "subs").glob("*.txt")):
        s = txt.read_text()
        low = s.lower()
        hits = sorted({m.start() for w in (words or GREP) for m in re.finditer(re.escape(w), low)})
        head = head_of.get(txt.stem, "")
        print(f"\n=== {txt.stem} {head} ({len(s.split())} words, {len(hits)} hits)")
        last = -10**9
        shown = 0
        for h in hits:
            if h - last < width or shown >= per_video:
                continue
            print("  ...", s[max(0, h - width // 2):h + width].replace("\n", " "))
            last, shown = h, shown + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["search", "pick", "subs", "grep"])
    ap.add_argument("--ytdlp", default="yt-dlp")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", default=None, help="subs: a file of video ids, one per line (default: all of pick.csv)")
    ap.add_argument("--words", nargs="*", default=None, help="grep: these words instead of GREP")
    a = ap.parse_args()
    if a.cmd == "search":
        search(a.ytdlp, a.limit)
    elif a.cmd == "pick":
        pick()
    elif a.cmd == "subs":
        subs(a.ytdlp, a.limit, Path(a.ids).read_text().split() if a.ids else None)
    else:
        grep(words=a.words)


if __name__ == "__main__":
    sys.exit(main())
