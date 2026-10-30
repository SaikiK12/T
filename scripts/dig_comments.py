"""Comment sections as searchable text: where practitioners answer each other, not where they present.

The owner's ask (2026-10-21): gather what quant and trading people say, transcripts and comment sections included
(Instagram and others), and look for good ideas. Long-form talks are in scripts/dig_videos.py and
scripts/dig_podcasts.py. This script collects the threads under them and the forums practitioners use, one JSON line
per post or comment, then ranks comments for a human reader.

Sources, all public and read without a login (AGENTS.md rule 5: no credentials):
- `hn`: Hacker News threads found by QUERIES through the Algolia API, whole comment trees.
- `reddit`: SUBS_ALL paged in full and SUBS_SEARCH by title keywords, through the Arctic Shift archive (reddit.com
  refuses this machine); the comment trees of the most discussed posts.
- `se`: Quantitative Finance Stack Exchange, top-voted questions and their answers.
- `yt`: YouTube comments of data/videos/pick.csv (and --ids FILE) through public Piped mirrors (youtube.com refuses
  this machine). `ytcaps` tries captions through an Invidious mirror, which works only some of the time.
- `tiktok`: TikTok comments of the videos in --urls FILE through TikTok's web API. Needs curl_cffi (browser
  impersonation): run it under the tool environment that has yt-dlp.
- `substack`: comments under the top posts of PUBS.
- Instagram: reel pages give caption, likes and comment count, but its comment API answers 429/403 without a login, so
  Instagram comments are not collected.

Then:
- `mine`: score every comment for mechanism words, a practitioner speaking ("when I was at", "our desk"), specific
  numbers and votes; write data/comments/top.csv and one reading file per source in data/comments/read/.
- `stats`: rows per source.

Everything goes to data/comments/ (gitignored); docs/COMMENT_DIG.md holds the reading. Each collector is resumable:
threads already saved are skipped.

usage: python scripts/dig_comments.py hn|reddit|se|yt|ytcaps|tiktok|substack|mine|stats [--limit N] [--ids FILE]
                                      [--urls FILE] [--top N] [--no-page]
"""
import argparse
import csv
import html
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "comments"
VIDEOS = ROOT / "data" / "videos"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136 Safari/537.36"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)

QUERIES = [
    "quant trading", "quantitative trading", "algorithmic trading", "high frequency trading", "market making",
    "market maker", "statistical arbitrage", "stat arb", "hedge fund strategy", "prop trading", "proprietary trading",
    "jane street", "citadel securities", "renaissance technologies", "two sigma", "jump trading", "hudson river trading",
    "optiver", "trading strategy", "backtest", "backtesting", "alpha research", "order book", "orderbook",
    "crypto arbitrage", "funding rate", "perpetual futures", "basis trade", "crypto market maker", "crypto trading bot",
    "options trading", "volatility trading", "momentum strategy", "mean reversion", "trend following",
    "retail traders lose", "payment for order flow", "latency arbitrage", "MEV", "polymarket", "prediction market",
    "Ask HN trading", "I made money trading", "I lost money trading", "how I trade", "trading edge",
]
SUBS_ALL = ["algotrading", "quant", "quantfinance", "highfreqtrading"]
SUBS_SEARCH = ["BitcoinMarkets", "FuturesTrading", "options", "thetagang", "Daytrading", "CryptoCurrency",
               "ethfinance", "defi", "SecurityAnalysis", "investing", "wallstreetbets"]
TITLE_WORDS = ["strategy", "edge", "arbitrage", "market maker", "funding", "basis", "backtest", "quant", "systematic",
               "AMA", "worked at", "profitable"]
PUBS = ["moontower", "concoda", "thediff", "netinterest", "macrocompass", "quantitativo", "quantseeker",
        "systematicindividualinvestor", "alphaarchitect", "theblock"]
PIPED = ["https://api.piped.private.coffee", "https://pipedapi.ducks.party"]
INVIDIOUS = ["https://inv.nadeko.net"]
SINCE = "2016-01-01"

MECH = ["news", "headline", "event", "earnings", "macro", "cpi", "fomc", "basis", "carry", "funding", "arbitrage",
        "arb ", "order flow", "orderflow", "order book", "orderbook", "liquidity", "volatility", "vix", "option",
        "gamma", "skew", "momentum", "mean revers", "stat arb", "statistical arbitrage", "pairs", "rebalanc", "index",
        "listing", "delist", "liquidat", "on-chain", "onchain", "latency", "high frequency", "hft", "alpha", "edge",
        "signal", "backtest", "sizing", "kelly", "perp", "futures", "dispersion", "merger", "spread", "maker",
        "taker", "rebate", "imbalance", "adverse selection", "toxic", "inventory", "queue", "slippage", "unlock",
        "airdrop", "mev", "premium", "open interest", "term structure", "seasonal", "weekend", "overnight", "auction",
        "etf", "flows", "short interest", "squeeze", "correlation", "regime", "overfit", "transaction cost", "fees",
        "market impact", "execution"]
PRAC = [r"\bi (used to |still )?(work|worked|trade|traded|ran|run|built|managed|was a|am a)\b",
        r"\bwe (used to )?(trade|traded|ran|run|built|made|had|did)\b",
        r"\bat my (old |previous |last |former |current )?(firm|shop|desk|fund|bank|job|employer|company)\b",
        r"\bwhen i was at\b", r"\bi worked at\b", r"\b(our|my) (desk|pod|book|fund|firm|strat|strategy|alpha)\b",
        r"\b(ex|former)[- ]?(jane street|citadel|optiver|sig|susquehanna|jump|drw|two sigma|hrt|imc|goldman|jpm|"
        r"morgan stanley|market maker|quant|trader|pm|hedge fund)",
        r"\bin my experience\b", r"\bi('m| am) a (quant|trader|pm|portfolio manager|market maker|researcher)\b",
        r"\bi('ve| have) been (trading|a trader|a quant)\b"]
SPEC = r"\b\d+(\.\d+)?\s?(bps?|basis points|%|ms|µs|us|sharpe|x|k|m|bn|years?|days?|hours?)\b"
MECH_RE = re.compile("|".join(re.escape(w) for w in MECH))
# trading words that rarely mean anything else; a thread whose title has none is usually off topic (a broad query hit)
TRADE = ["arbitrage", "arb", "basis", "carry", "funding", "order flow", "order book", "orderbook", "market mak",
         "liquidity", "volatility", "option", "gamma", "skew", "momentum", "mean revers", "stat arb", "pairs trad",
         "rebalanc", "liquidat", "latency", "hft", "high frequency", "high-frequency", "alpha", "edge", "backtest",
         "sharpe", "perp", "futures", "spread", "maker", "taker", "rebate", "adverse selection", "slippage",
         "market impact", "short interest", "squeeze", "etf", "hedge", "pnl", "p&l", "drawdown", "overfit", "trade",
         "trading", "trader", "quant", "stock", "crypto", "bitcoin", "exchange", "broker", "invest", "market",
         "jane street", "citadel", "renaissance", "two sigma", "jump", "optiver", "polymarket", "kalshi", "fund"]
TRADE_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in TRADE) + ")")
PRAC_RE = re.compile("|".join(PRAC))
SPEC_RE = re.compile(SPEC)


def get(url, params=None, tries=5, wait=1.0, headers=None, as_json=True):
    """GET with backoff on 429, 5xx and timeouts. Returns parsed JSON (or text), or None after the last try."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json",
                                                       **(headers or {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode("utf-8", "replace")
            time.sleep(wait)
            if not as_json:
                return body
            d = json.loads(body)
            if isinstance(d, dict) and d.get("error") and "slow down" in str(d["error"]).lower():
                raise TimeoutError(d["error"])
            return d
        except Exception as e:  # noqa: BLE001 - every failure is retried, then reported
            code = getattr(e, "code", None)
            if code in (400, 401, 403, 404, 405):              # Arctic Shift sends 422 for "slow down": retried
                log("  refused", code, url[:120])
                return None
            time.sleep(wait * 2 ** (i + 1))
    log("  gave up", url[:120])
    return None


def clean(text):
    text = re.sub(r"<(br|p|/p|li)[^>]*>", "\n", text or "")
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class Store:
    """One JSONL file per source; remembers which threads are already saved."""
    def __init__(self, source):
        OUT.mkdir(parents=True, exist_ok=True)
        self.path = OUT / f"{source}.jsonl"
        self.source = source
        self.threads = set()
        if self.path.exists():
            with open(self.path) as f:
                for line in f:
                    self.threads.add(json.loads(line)["thread"])

    def add(self, rows):
        with open(self.path, "a") as f:
            for r in rows:
                f.write(json.dumps({"source": self.source, **r}, ensure_ascii=False) + "\n")
        if rows:
            self.threads.add(rows[0]["thread"])


def row(thread, title, url, cid, parent, score, created, text, **extra):
    return {"thread": str(thread), "thread_title": title, "url": url, "id": str(cid), "parent": str(parent or ""),
            "score": score, "created_utc": created, "text": text, **extra}


# ---------------------------------------------------------------------------------------------------- Hacker News
def hn(limit):
    st = Store("hn")
    stories = {}
    for q in QUERIES:
        d = get("https://hn.algolia.com/api/v1/search", {"query": q, "tags": "story", "hitsPerPage": 50,
                                                         "numericFilters": "num_comments>=30"}, wait=0.3)
        for h in (d or {}).get("hits", []):
            stories[h["objectID"]] = (h.get("num_comments") or 0, h.get("points") or 0, h.get("title") or "")
    order = sorted(stories, key=lambda k: -stories[k][0])[:limit]
    log(f"hn: {len(stories)} stories, reading {len(order)}")
    for k in order:
        if k in st.threads:
            continue
        d = get(f"https://hn.algolia.com/api/v1/items/{k}", wait=0.3)
        if not d:
            continue
        title, url = stories[k][2], f"https://news.ycombinator.com/item?id={k}"
        rows = [row(k, title, url, k, "", stories[k][1], d.get("created_at_i"), clean(d.get("text") or ""),
                    is_post=True)]
        stack = [(c, 1) for c in d.get("children", [])]
        while stack:
            c, depth = stack.pop()
            if c.get("text"):
                rows.append(row(k, title, url, c["id"], c.get("parent_id"), None, c.get("created_at_i"),
                                clean(c["text"]), depth=depth))
            stack += [(x, depth + 1) for x in c.get("children", [])]
        st.add(rows)
        log(f"  {k} {len(rows)} {title[:70]}")


# --------------------------------------------------------------------------------------------------------- Reddit
AS = "https://arctic-shift.photon-reddit.com/api"
POST_FIELDS = "id,title,score,num_comments,created_utc,selftext,subreddit,link_flair_text"


def months(since):
    """Month windows [start, end) as epoch seconds, from since to now: the archive answers short windows only."""
    y, m = map(int, since[:7].split("-"))
    now = time.gmtime()
    out = []
    while (y, m) <= (now.tm_year, now.tm_mon):
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append((int(time.mktime((y, m, 1, 0, 0, 0, 0, 0, 0)) - time.timezone),
                    int(time.mktime((y2, m2, 1, 0, 0, 0, 0, 0, 0)) - time.timezone)))
        y, m = y2, m2
    return out


def reddit_posts():
    """Every post of SUBS_ALL since SINCE, month by month, and SUBS_SEARCH posts whose title has a TITLE_WORDS word
    (in three eras)."""
    path = OUT / "reddit_posts.jsonl"
    seen, done = set(), set()
    if path.exists():
        for x in open(path):
            seen.add(json.loads(x)["id"])
    marks = OUT / "reddit_windows.txt"                       # windows already paged, so a rerun resumes
    if marks.exists():
        done = set(marks.read_text().split())
    with open(path, "a") as f, open(marks, "a") as mk:
        def keep(posts):
            for p in posts:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")

        def page(q, start, end, key):
            if key in done:
                return 0
            before, n = end, 0
            while True:
                d = get(f"{AS}/posts/search", {**q, "limit": 100, "sort": "desc", "fields": POST_FIELDS,
                                               "after": start, "before": before}, wait=1.0)
                posts = (d or {}).get("data") or []
                keep(posts)
                n += len(posts)
                if len(posts) < 100:
                    break
                before = min(p["created_utc"] for p in posts)
            mk.write(key + "\n")
            mk.flush()
            return n
        for sub in SUBS_ALL:
            n = sum(page({"subreddit": sub}, a, b, f"{sub}:{a}") for a, b in months(SINCE))
            log(f"reddit r/{sub}: {n} posts")
        eras = [("2016-01-01", "2021-01-01"), ("2021-01-01", "2024-01-01"), ("2024-01-01", "2027-01-01")]
        for sub in SUBS_SEARCH:
            n = 0
            for w in TITLE_WORDS:
                for a, b in eras:
                    ta = int(time.mktime(time.strptime(a, "%Y-%m-%d")) - time.timezone)
                    tb = int(time.mktime(time.strptime(b, "%Y-%m-%d")) - time.timezone)
                    n += page({"subreddit": sub, "title": w}, ta, tb, f"{sub}:{w}:{a}")
            log(f"reddit r/{sub}: {n} title hits")
    return [json.loads(x) for x in open(path)]


def reddit(limit, page=True):
    """Comment trees of the most discussed posts; page=False reads only the posts already saved (paging every
    month of a large subreddit takes hours, so the trees of what is saved can be read first)."""
    st = Store("reddit")
    path = OUT / "reddit_posts.jsonl"
    posts = reddit_posts() if page or not path.exists() else [json.loads(x) for x in open(path)]
    by_sub = {}
    for p in posts:
        if (p.get("num_comments") or 0) >= 15:
            by_sub.setdefault(p["subreddit"], []).append(p)
    for sub, ps in by_sub.items():
        ps.sort(key=lambda p: -(p.get("num_comments") or 0) * (1 + len(MECH_RE.findall(p["title"].lower()))))
        todo = [p for p in ps[:limit] if p["id"] not in st.threads]
        log(f"reddit r/{sub}: {len(ps)} discussed posts, reading {len(todo)} more")
        for p in todo:
            url = f"https://www.reddit.com/r/{sub}/comments/{p['id']}/"
            rows = [row(p["id"], p["title"], url, p["id"], "", p.get("score"), p.get("created_utc"),
                        clean(p.get("selftext") or ""), is_post=True, sub=sub, flair=p.get("link_flair_text"))]
            d = get(f"{AS}/comments/tree", {"link_id": f"t3_{p['id']}", "limit": 9999}, wait=0.6)
            stack = [(c, 1) for c in (d or {}).get("data") or []]
            while stack:
                c, depth = stack.pop()
                if c.get("kind") != "t1":
                    continue
                x = c["data"]
                body = x.get("body") or ""
                if body and body not in ("[deleted]", "[removed]"):
                    rows.append(row(p["id"], p["title"], url, x["id"], x.get("parent_id"), x.get("score"),
                                    x.get("created_utc"), clean(body), depth=depth, sub=sub,
                                    flair=x.get("author_flair_text")))
                rep = x.get("replies")
                if isinstance(rep, dict):
                    stack += [(y, depth + 1) for y in rep.get("data", {}).get("children", [])]
            st.add(rows)


# ------------------------------------------------------------------------------------------------- Stack Exchange
def se(limit):
    st = Store("se")
    base = "https://api.stackexchange.com/2.3"
    qs = []
    for page in range(1, limit // 100 + 2):
        d = get(f"{base}/questions", {"order": "desc", "sort": "votes", "site": "quant", "pagesize": 100,
                                      "page": page, "filter": "withbody"}, wait=0.5)
        qs += (d or {}).get("items", [])
        if not (d or {}).get("has_more"):
            break
    qs = [q for q in qs[:limit] if str(q["question_id"]) not in st.threads]
    log(f"se: {len(qs)} questions to read")
    for i in range(0, len(qs), 100):
        chunk = qs[i:i + 100]
        ans, page = [], 1
        while True:
            ids = ";".join(str(q["question_id"]) for q in chunk)
            d = get(f"{base}/questions/{ids}/answers", {"order": "desc", "sort": "votes", "site": "quant",
                                                        "pagesize": 100, "page": page, "filter": "withbody"}, wait=0.5)
            ans += (d or {}).get("items", [])
            if (d or {}).get("backoff"):
                time.sleep(d["backoff"])
            if not (d or {}).get("has_more"):
                break
            page += 1
        for q in chunk:
            qid = q["question_id"]
            title = html.unescape(q["title"])
            rows = [row(qid, title, q["link"], qid, "", q["score"], q["creation_date"], clean(q.get("body")),
                        is_post=True)]
            rows += [row(qid, title, q["link"], a["answer_id"], qid, a["score"], a["creation_date"],
                         clean(a.get("body")), accepted=a.get("is_accepted")) for a in ans if a["question_id"] == qid]
            st.add(rows)
        log(f"  se {i + len(chunk)} questions, {len(ans)} answers in this chunk")


# --------------------------------------------------------------------------------------------- YouTube (mirrors)
def video_list(ids_file):
    vids = {}
    for path in [VIDEOS / "pick.csv"] + ([Path(ids_file)] if ids_file else []):
        if path.exists() and path.suffix == ".csv":
            for r in csv.DictReader(open(path)):
                vids[r["id"]] = r.get("title", "")
        elif path.exists():
            for line in open(path):
                if line.strip():
                    vids[line.split()[0]] = " ".join(line.split()[1:])
    return vids


def yt(ids_file, pages):
    st = Store("yt")
    vids = video_list(ids_file)
    todo = [v for v in vids if v not in st.threads]
    log(f"yt: {len(vids)} videos, {len(todo)} to read")
    for v in todo:
        rows, inst = [], None
        for inst in PIPED:
            d = get(f"{inst}/comments/{v}", tries=2, wait=0.5)
            if d and not d.get("disabled") and d.get("comments") is not None:
                break
            d = None
        url = f"https://www.youtube.com/watch?v={v}"
        for _ in range(pages):
            if not d:
                break
            for c in d.get("comments") or []:
                rows.append(row(v, vids[v], url, c["commentId"], "", c.get("likeCount"), c.get("commentedTime"),
                                clean(c.get("commentText")), replies=c.get("replyCount"), pinned=c.get("pinned")))
            nxt = d.get("nextpage")
            d = get(f"{inst}/nextpage/comments/{v}", {"nextpage": nxt}, tries=2, wait=0.5) if nxt else None
        st.add(rows or [row(v, vids[v], url, "", "", None, None, "", empty=True)])
        log(f"  {v} {len(rows)} comments {vids[v][:60]}")


def ytcaps(ids_file):
    """Captions through Invidious, best effort: data/videos/subs/<id>.txt, which dig_videos.py grep reads."""
    subs = VIDEOS / "subs"
    subs.mkdir(parents=True, exist_ok=True)
    vids = [v for v in video_list(ids_file) if not (subs / f"{v}.txt").exists()]
    fails = 0
    for v in vids:
        got = False
        for inst in INVIDIOUS:
            d = get(f"{inst}/api/v1/captions/{v}", tries=3, wait=1)
            caps = (d or {}).get("captions") or []
            en = [c for c in caps if c.get("languageCode", "").startswith("en")]
            if en:
                vtt = get(inst + en[0]["url"], tries=3, wait=1, as_json=False)
                if vtt and "-->" in vtt:
                    lines = [x for x in vtt.splitlines() if x and "-->" not in x and not x.startswith(("WEBVTT", "Kind",
                                                                                                    "Language"))]
                    text, prev = [], None
                    for x in lines:
                        x = re.sub(r"<[^>]+>", "", x).strip()
                        if x and x != prev:
                            text.append(x)
                        prev = x
                    (subs / f"{v}.txt").write_text(" ".join(text))
                    got = True
                    break
        fails = 0 if got else fails + 1
        log(f"  {v} {'captions' if got else 'none'}")
        if fails >= 15:
            log("ytcaps: 15 misses in a row, stopping")
            break


# --------------------------------------------------------------------------------------------------------- TikTok
def tiktok(urls_file, pages):
    from curl_cffi import requests as cr  # the tool environment's impersonating client
    st = Store("tiktok")
    s = cr.Session(impersonate="chrome")
    for line in open(urls_file):
        u = line.split("#")[0].strip()
        if not u:
            continue
        m = re.search(r"/video/(\d+)", u)
        if not m:
            r = s.get(u, allow_redirects=True, timeout=30)
            m = re.search(r"/video/(\d+)", r.url)
        if not m:
            log("  no video id", u)
            continue
        vid = m.group(1)
        if vid in st.threads:
            continue
        title = ""
        try:
            title = s.get("https://www.tiktok.com/oembed", params={"url": u}, timeout=30).json().get("title", "")
        except Exception:  # noqa: BLE001 - the title is optional
            pass
        rows, cursor = [], 0
        for _ in range(pages):
            r = s.get("https://www.tiktok.com/api/comment/list/", params={"aweme_id": vid, "count": 50,
                                                                          "cursor": cursor, "aid": 1988}, timeout=30)
            d = r.json() if r.text else {}
            for c in d.get("comments") or []:
                rows.append(row(vid, title, u, c["cid"], "", c.get("digg_count"), c.get("create_time"),
                                c.get("text", ""), replies=c.get("reply_comment_total")))
            if not d.get("has_more"):
                break
            cursor = d.get("cursor", cursor + 50)
            time.sleep(1)
        st.add(rows or [row(vid, title, u, "", "", None, None, "", empty=True)])
        log(f"  {vid} {len(rows)} comments {title[:60]}")


# ------------------------------------------------------------------------------------------------------- Substack
def substack(limit):
    st = Store("substack")
    for pub in PUBS:
        base = f"https://{pub}.substack.com/api/v1"
        posts = []
        for off in range(0, 200, 50):
            d = get(f"{base}/archive", {"sort": "top", "limit": 50, "offset": off}, tries=2, wait=0.5)
            if not d:
                break
            posts += d
            if len(d) < 50:
                break
        posts = [p for p in posts if (p.get("comment_count") or 0) >= 5][:limit]
        log(f"substack {pub}: {len(posts)} posts with comments")
        for p in posts:
            if str(p["id"]) in st.threads:
                continue
            d = get(f"{base}/post/{p['id']}/comments", {"all_comments": "true", "sort": "best_first"}, wait=0.5)
            url = p.get("canonical_url", "")
            rows = [row(p["id"], p["title"], url, p["id"], "", p.get("reactions", {}).get("❤") if isinstance(
                p.get("reactions"), dict) else None, p.get("post_date"), clean(p.get("description") or ""),
                is_post=True, pub=pub)]
            stack = [(c, 1) for c in (d or {}).get("comments", [])]
            while stack:
                c, depth = stack.pop()
                if c.get("body"):
                    rows.append(row(p["id"], p["title"], url, c["id"], c.get("ancestor_path"), c.get("reaction_count"),
                                    c.get("date"), clean(c["body"]), depth=depth, pub=pub))
                stack += [(x, depth + 1) for x in c.get("children", [])]
            st.add(rows)


# -------------------------------------------------------------------------------------------------------- mining
def features(text, score, title=""):
    """mech: distinct trading words; prac: a practitioner speaking; spec: numbers with units. The rank adds votes,
    and takes points off for very short or very long text and for threads whose title is not about markets."""
    t = text.lower()
    mech = len(set(TRADE_RE.findall(t)) - {"market", "trade", "fund", "invest", "exchange", "stock"})
    prac = len(PRAC_RE.findall(t))
    spec = len(SPEC_RE.findall(t))
    n = len(text)
    s = min(mech, 8) + 3 * min(prac, 2) + 0.5 * min(spec, 4)
    s += 0.8 * math.log1p(max(score or 0, 0)) if isinstance(score, (int, float)) else 0
    if n < 150 or n > 6000:
        s -= 3
    if title and not TRADE_RE.search(title.lower()):
        s -= 6
    return mech, prac, spec, round(s, 2)


def mine(top):
    rows, seen = [], set()
    for path in sorted(OUT.glob("*.jsonl")):
        if path.name == "reddit_posts.jsonl":
            continue
        for line in open(path):
            r = json.loads(line)
            if not r.get("text") or (r.get("is_post") and r["source"] == "hn"):
                continue
            key = (r["source"], r["text"][:500])             # one copy of a pasted reply or a moderator notice
            if key in seen:
                continue
            seen.add(key)
            mech, prac, spec, s = features(r["text"], r.get("score"), r.get("thread_title") or "")
            rows.append({**r, "mech": mech, "prac": prac, "spec": spec, "rank_score": s})
    rows.sort(key=lambda r: -r["rank_score"])
    cols = ["source", "rank_score", "mech", "prac", "spec", "score", "thread_title", "url", "id", "text"]
    with open(OUT / "top.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows[: top * 10])
    read = OUT / "read"
    read.mkdir(exist_ok=True)
    for src in sorted({r["source"] for r in rows}):
        sel = [r for r in rows if r["source"] == src][:top]
        with open(read / f"{src}.md", "w") as f:
            for i, r in enumerate(sel, 1):
                f.write(f"### {i}. [{r['rank_score']}] {r['thread_title'][:120]}\n{r['url']} (votes {r.get('score')}, "
                        f"mech {r['mech']}, prac {r['prac']})\n\n{r['text'][:3000]}\n\n")
        log(f"mine {src}: {sum(r['source'] == src for r in rows)} comments, wrote the top {len(sel)}")


def stats():
    for path in sorted(OUT.glob("*.jsonl")):
        n = sum(1 for _ in open(path))
        threads = len({json.loads(x).get("thread", json.loads(x).get("id")) for x in open(path)})
        log(f"{path.name}: {n} rows, {threads} threads")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hn", "reddit", "se", "yt", "ytcaps", "tiktok", "substack", "mine", "stats"])
    ap.add_argument("--limit", type=int, default=300, help="threads per source (per subreddit, per publication)")
    ap.add_argument("--pages", type=int, default=10, help="comment pages per video")
    ap.add_argument("--ids", help="extra YouTube ids, one per line (id then title)")
    ap.add_argument("--urls", help="TikTok video URLs, one per line")
    ap.add_argument("--top", type=int, default=300, help="comments per source in the reading files")
    ap.add_argument("--no-page", action="store_true", help="reddit: read trees of the saved posts only")
    a = ap.parse_args()
    {"hn": lambda: hn(a.limit), "reddit": lambda: reddit(a.limit, not a.no_page), "se": lambda: se(a.limit),
     "yt": lambda: yt(a.ids, a.pages), "ytcaps": lambda: ytcaps(a.ids), "tiktok": lambda: tiktok(a.urls, a.pages),
     "substack": lambda: substack(a.limit), "mine": lambda: mine(a.top), "stats": stats}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
