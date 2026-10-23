"""Point-in-time headline recorder: every FEEDS source polled every POLL_S seconds, each new item kept once with the
time we first saw it.

Why: the owner wants the lab to trade news "like a Bloomberg" (docs/VIDEO_DIG.md). Headline history with honest
timestamps cannot be backfilled from RSS (feeds keep only their latest items, and publishers edit times), so the record
has to start now. Every row has both the publisher's time (`pub_utc`, as the feed states it) and ours (`seen_utc`,
when this recorder first fetched it): a study may act only after `seen_utc`, plus its own reaction delay.

Rows go to data/news/<YYYY-MM-DD>.jsonl (UTC day of seen_utc), one JSON object per new item:
  {"seen_utc", "feed", "id", "title", "link", "pub_utc", "summary"}
`id` is the item's guid (or link, or title) and is unique per feed; items already seen in the last 3 days of files
are not written again after a restart. data/news/status.json holds per-feed counts, errors and the last poll.

Sources (all public, no key): Bloomberg markets/economics/politics/technology/crypto RSS, WSJ markets and world,
MarketWatch real-time headlines, CNBC top news and economy, FT markets, the Federal Reserve, SEC and ECB press releases,
CoinDesk, Cointelegraph, The Block, Decrypt, Blockworks, Kraken's blog, Coinbase status, and OKX's new-listing notices
(JSON). Binance's notices have their own recorder (scripts/record_notices.py). Upbit, Bithumb and Bybit refuse this
machine (HTTP 403).

usage: python scripts/record_news.py [ensure]   (default: start the daemon if none holds data/news/recorder.lock)
       python scripts/record_news.py run|once|status
"""
import email.utils
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "news"
POLL_S, KEEP_DAYS, MAX_SUMMARY = 60, 3, 600
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136 Safari/537.36"
FEEDS = {
    "bloomberg_markets": "https://feeds.bloomberg.com/markets/news.rss",
    "bloomberg_economics": "https://feeds.bloomberg.com/economics/news.rss",
    "bloomberg_politics": "https://feeds.bloomberg.com/politics/news.rss",
    "bloomberg_technology": "https://feeds.bloomberg.com/technology/news.rss",
    "bloomberg_crypto": "https://feeds.bloomberg.com/crypto/news.rss",
    "wsj_markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "wsj_world": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "marketwatch_realtime": "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "cnbc_top": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "cnbc_economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "ft_markets": "https://www.ft.com/markets?format=rss",
    "fed_press": "https://www.federalreserve.gov/feeds/press_all.xml",
    "sec_press": "https://www.sec.gov/news/pressreleases.rss",
    "ecb_press": "https://www.ecb.europa.eu/rss/press.html",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "theblock": "https://www.theblock.co/rss.xml",
    "decrypt": "https://decrypt.co/feed",
    "blockworks": "https://blockworks.co/feed",
    "kraken_blog": "https://blog.kraken.com/feed",
    "coinbase_status": "https://status.coinbase.com/history.rss",
    "okx_listings": "https://www.okx.com/api/v5/support/announcements?annType=announcements-new-listings",
}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def utc(ts=None):
    return datetime.fromtimestamp(time.time() if ts is None else ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pub_time(text):
    """A feed's date string (RFC 822 or ISO 8601) to ISO UTC; '' when absent or unreadable."""
    if not text:
        return ""
    text = text.strip()
    try:
        return utc(email.utils.parsedate_to_datetime(text).timestamp())
    except (TypeError, ValueError):
        pass
    try:
        return utc(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return ""


def _strip(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def parse_feed(feed, body):
    """Items of one response: dicts with id, title, link, pub_utc, summary. RSS 2.0, Atom and OKX's JSON."""
    if feed == "okx_listings":
        data = json.loads(body).get("data") or []
        out = []
        for page in data:
            for x in page.get("details") or []:
                ms = int(x.get("pTime") or 0)
                out.append({"id": x.get("url") or x.get("title", ""), "title": x.get("title", ""),
                            "link": x.get("url", ""), "pub_utc": utc(ms / 1000) if ms else "", "summary": ""})
        return out
    root = ET.fromstring(body)
    out = []
    for it in root.iter():
        tag = it.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        f = {c.tag.rsplit("}", 1)[-1]: c for c in it}
        link = (f["link"].text or f["link"].get("href", "")) if "link" in f else ""
        title = _strip(f["title"].text) if "title" in f else ""
        guid = (f["guid"].text if "guid" in f else None) or (f["id"].text if "id" in f else None) or link or title
        date = next((f[k].text for k in ("pubDate", "published", "updated", "date") if k in f and f[k].text), "")
        summ = next((f[k].text for k in ("description", "summary", "content") if k in f and f[k].text), "")
        out.append({"id": (guid or "").strip(), "title": title, "link": (link or "").strip(), "pub_utc": pub_time(date),
                    "summary": _strip(summ)[:MAX_SUMMARY]})
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


class Recorder:
    def __init__(self):
        self.seen = {f: set() for f in FEEDS}
        self.stats = {f: {"items": 0, "new": 0, "errors": 0, "last_error": ""} for f in FEEDS}
        self.stop = threading.Event()
        self.load_seen()

    def load_seen(self):
        cut = time.time() - KEEP_DAYS * 86400
        for p in sorted(OUT.glob("*.jsonl")):
            if p.stat().st_mtime < cut:
                continue
            for line in p.read_text().splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("feed") in self.seen:
                    self.seen[r["feed"]].add(r["id"])

    def poll(self, pool):
        def one(feed):
            try:
                return feed, parse_feed(feed, fetch(FEEDS[feed])), ""
            except Exception as e:  # noqa: BLE001  (one bad feed must not stop the others)
                return feed, [], f"{type(e).__name__}: {e}"[:200]
        now = utc()
        rows = []
        for feed, items, err in pool.map(one, FEEDS):
            st = self.stats[feed]
            if err:
                st["errors"] += 1
                st["last_error"] = f"{now} {err}"
                continue
            st["items"] = len(items)
            for x in items:
                if not x["id"] or x["id"] in self.seen[feed]:
                    continue
                self.seen[feed].add(x["id"])
                st["new"] += 1
                rows.append({"seen_utc": now, "feed": feed, **x})
        if rows:
            OUT.mkdir(parents=True, exist_ok=True)
            with open(OUT / f"{now[:10]}.jsonl", "a") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        status = {"updated_utc": now, "pid": os.getpid(), "poll_s": POLL_S,
                  "new_this_poll": len(rows), "feeds": self.stats}
        tmp = OUT / "status.json.tmp"
        tmp.write_text(json.dumps(status, indent=1))
        tmp.replace(OUT / "status.json")
        return len(rows)

    def run(self, once=False):
        with ThreadPoolExecutor(8) as pool:
            while not self.stop.is_set():
                t0 = time.time()
                n = self.poll(pool)
                if once:
                    return n
                self.stop.wait(max(1.0, POLL_S - (time.time() - t0)))
        return 0


def lock():
    OUT.mkdir(parents=True, exist_ok=True)
    f = open(OUT / "recorder.lock", "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        return None
    return f


def main(argv=None):
    cmd = (argv or sys.argv[1:] or ["ensure"])[0]
    if cmd == "status":
        st = OUT / "status.json"
        print(st.read_text() if st.exists() else "no status yet")
        return 0
    if cmd == "ensure":
        held = lock()
        if held is None:
            log("news recorder running")
            return 0
        held.close()
        logf = open(OUT / "recorder.log", "a")
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"], cwd=ROOT, stdout=logf,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        log("news recorder started")
        return 0
    held = lock()
    if held is None:
        log("another recorder holds data/news/recorder.lock")
        return 1
    rec = Recorder()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: rec.stop.set())
    if cmd == "once":
        log(f"{rec.run(once=True)} new items")
        return 0
    log(f"recording {len(FEEDS)} feeds every {POLL_S} s")
    rec.run()
    log("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
