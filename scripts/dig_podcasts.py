"""Practitioner podcasts as searchable text: the people of docs/VIDEO_DIG.md through their shows' RSS feeds.

YouTube refuses caption downloads from this machine (HTTP 429, "confirm you're not a bot"). Most practitioner interview
shows are also podcasts, and many publish full transcripts in their feeds (<podcast:transcript>): Odd Lots as SubRip,
Top Traders Unplugged as word-level JSON, Flirting with Models as HTML. Episodes without one can be transcribed
locally (scripts/transcribe_audio.py, faster-whisper on CPU).

Steps:
1. `episodes`: every item of every FEEDS feed goes to data/videos/episodes.csv (feed, key, title, pub_utc,
   duration_s, audio, transcript, transcript_type, words, mech, firm, summary). `words` counts the WORDS of
   scripts/dig_videos.py in the title and summary; `mech` and `firm` count the mechanism and firm words alone.
2. `text`: for each feed, the top --per-feed episodes with mech >= 1, ranked firm first and then by words, are written
   as plain text to data/videos/subs/pod_<key>.txt from the feed's transcript. With --whisper-python PATH, episodes
   without one are downloaded to --tmp, transcribed with scripts/transcribe_audio.py under that interpreter, and the
   audio is deleted.
3. `python scripts/dig_videos.py grep` reads these files too.

data/ is gitignored; docs/VIDEO_DIG.md holds the reading.

usage: python scripts/dig_podcasts.py episodes
       python scripts/dig_podcasts.py text [--per-feed 12] [--feeds a b] [--match REGEX]
                                           [--whisper-python PATH --tmp DIR]
"""
import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dig_videos as dv  # noqa: E402
import record_news as rn  # noqa: E402

OUT = dv.OUT
SUBS = OUT / "subs"
UA = rn.UA
log = dv.log
FEEDS = {
    # practitioner and markets interview shows (transcripts in the feed where noted)
    "odd_lots": "https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/"
                "8a94442e-5a74-4fa2-8b8d-ae27003a8d6b/982f5071-765c-403d-969d-ae27003a8d83/podcast.rss",   # SubRip
    "top_traders_unplugged": "https://feeds.captivate.fm/top-traders-unplugged/",                         # JSON
    "flirting_with_models": "https://feeds.captivate.fm/flirting-with-models/",                           # HTML
    "chat_with_traders": "https://feeds.megaphone.fm/CWT9205947236",
    "better_system_trader": "https://rss.libsyn.com/shows/66295/destinations/266788.xml",
    "odds_on_open": "https://anchor.fm/s/101506278/podcast/rss",
    "volatility_views": "https://rss.libsyn.com/shows/31880/destinations/68688.xml",
    "market_huddle": "https://markethuddle.com/feed/podcast/",
    "macro_voices": "https://feed.podbean.com/macrovoices/feed.xml",
    "macro_hive": "https://rss.libsyn.com/shows/254951/destinations/1929056.xml",
    "hidden_forces": "https://rss.libsyn.com/shows/91567/destinations/457899.xml",
    "meb_faber": "https://feeds.megaphone.fm/TIFM6133783130",
    "quantopian": "https://anchor.fm/s/ea4e4680/podcast/rss",
    "algorithmic_advantage": "https://anchor.fm/s/e672f04c/podcast/rss",
    "outlier_trading": "https://anchor.fm/s/80153c24/podcast/rss",
    "capital_thesis": "https://anchor.fm/s/1155c2e50/podcast/rss",
    "wall_street_oasis": "https://feeds.megaphone.fm/IBOC6784645588",
    # crypto desks, market makers and funds
    "rekt_radio": "https://anchor.fm/s/eac8d7d8/podcast/rss",
    "the_archive": "https://anchor.fm/s/10e534198/podcast/rss",
    "empire": "https://feeds.megaphone.fm/empire",
    "unchained": "https://feeds.megaphone.fm/LSHML4761942757",
    "forward_guidance": "https://feeds.megaphone.fm/forwardguidance",
    "milk_road": "https://anchor.fm/s/83d264f4/podcast/rss",
}
NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd", "podcast": "https://podcastindex.org/namespace/1.0"}


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def seconds(text):
    """itunes:duration ("3725", "62:05" or "1:02:05") to seconds; None when absent."""
    if not text or not text.strip():
        return None
    parts = [float(p) for p in text.strip().split(":") if p.replace(".", "", 1).isdigit()]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts))) if parts else None


def key(feed, guid):
    return hashlib.sha1(f"{feed}|{guid}".encode()).hexdigest()[:12]


def parse_episodes(feed, body):
    rows = []
    for it in ET.fromstring(body).iter("item"):
        guid = (it.findtext("guid") or it.findtext("link") or it.findtext("title") or "").strip()
        enc = it.find("enclosure")
        trs = it.findall("podcast:transcript", NS)
        # prefer the text formats this reader parses, in this order
        tr = sorted(trs, key=lambda t: ["application/json", "application/srt", "application/x-subrip", "text/vtt",
                                        "text/html"].index(t.get("type")) if t.get("type") in (
            "application/json", "application/srt", "application/x-subrip", "text/vtt", "text/html") else 9)
        rows.append({"feed": feed, "key": key(feed, guid), "title": rn._strip(it.findtext("title")),
                     "pub_utc": rn.pub_time(it.findtext("pubDate")),
                     "duration_s": seconds(it.findtext("itunes:duration", namespaces=NS)),
                     "audio": enc.get("url", "") if enc is not None else "",
                     "transcript": tr[0].get("url", "") if tr else "", "transcript_type": tr[0].get("type", "") if tr else "",
                     "summary": rn._strip(it.findtext("description") or it.findtext("itunes:summary", namespaces=NS))[:800]})
    return rows


def score(df):
    text = (df.title.fillna("") + " " + df.summary.fillna("")).str.lower()
    count = lambda ws: text.map(lambda s: sum(w in s for w in ws))
    return df.assign(words=count(dv.WORDS), mech=count(dv.MECH), firm=count(dv.FIRMS))


def episodes():
    rows = []
    for feed, url in FEEDS.items():
        try:
            got = parse_episodes(feed, get(url))
        except Exception as e:  # noqa: BLE001  (one dead feed must not stop the others)
            log(f"{feed}: failed ({type(e).__name__}: {e})")
            continue
        rows += got
        log(f"{feed}: {len(got)} episodes, {sum(bool(r['transcript']) for r in got)} with a transcript")
    df = score(pd.DataFrame(rows)).drop_duplicates("key")
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "episodes.csv", index=False)
    log(f"{len(df)} episodes in {OUT / 'episodes.csv'}")


def transcript_text(body, kind):
    """A feed transcript (JSON word segments, SubRip, WebVTT or HTML) to one line of plain text."""
    s = body.decode("utf-8", "ignore")
    if kind == "application/json" or s.lstrip().startswith("{"):
        segs = json.loads(s).get("segments") or []
        return re.sub(r"\s+", " ", " ".join(str(x.get("body", "")) for x in segs)).strip()
    if kind == "text/html" or s.lstrip().startswith("<"):
        s = re.sub(r"<(time|cite)>[^<]*</\1>", " ", s)
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    lines = [ln for ln in s.splitlines() if ln.strip() and "-->" not in ln and not ln.strip().isdigit()
             and not ln.startswith(("WEBVTT", "Kind:", "Language:"))]
    return re.sub(r"\s+", " ", " ".join(re.sub(r"^Speaker \d+:\s*", "", ln) for ln in lines)).strip()


def chosen(df, per_feed, feeds=None, match=None):
    d = df[(df.mech >= 1) & (df.feed.isin(feeds) if feeds else True)]
    if match:                                          # a reader's topic: titles matching this regex, any case
        d = d[d.title.str.contains(match, case=False, regex=True, na=False)]
    d = d.sort_values(["feed", "firm", "words", "pub_utc"], ascending=[True, False, False, False])
    return d.groupby("feed", sort=False).head(per_feed)


def text(per_feed, feeds, whisper_python, tmp, match=None):
    df = pd.read_csv(OUT / "episodes.csv").fillna({"transcript": "", "transcript_type": "", "audio": ""})
    SUBS.mkdir(parents=True, exist_ok=True)
    todo = chosen(df, per_feed, feeds, match)
    log(f"{len(todo)} episodes chosen from {todo.feed.nunique()} feeds")
    for r in todo.itertuples():
        out = SUBS / f"pod_{r.key}.txt"
        if out.exists():
            continue
        try:
            if r.transcript:
                out.write_text(transcript_text(get(r.transcript), r.transcript_type))
                how = "feed transcript"
            elif whisper_python and r.audio:
                tmpd = Path(tmp)
                tmpd.mkdir(parents=True, exist_ok=True)
                audio = tmpd / f"{r.key}.audio"
                audio.write_bytes(get(r.audio, timeout=600))
                subprocess.run([whisper_python, str(ROOT / "scripts" / "transcribe_audio.py"), str(audio), str(out)],
                               check=True, timeout=4 * 3600)
                audio.unlink()
                how = "whisper"
            else:
                continue
        except Exception as e:  # noqa: BLE001
            log(f"{r.feed} {r.key}: failed ({type(e).__name__}: {e})")
            continue
        log(f"{r.feed} {r.key} {how}: {len(out.read_text().split())} words | {r.title[:70]}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["episodes", "text"])
    ap.add_argument("--per-feed", type=int, default=12)
    ap.add_argument("--feeds", nargs="*", default=None)
    ap.add_argument("--match", default=None, help="text: only titles matching this regex (case-insensitive)")
    ap.add_argument("--whisper-python", default=None)
    ap.add_argument("--tmp", default=None, help="audio download directory (required with --whisper-python)")
    a = ap.parse_args(argv)
    if a.cmd == "episodes":
        episodes()
    else:
        if a.whisper_python and not a.tmp:
            ap.error("--whisper-python needs --tmp")
        text(a.per_feed, a.feeds, a.whisper_python, a.tmp, a.match)


if __name__ == "__main__":
    sys.exit(main())
