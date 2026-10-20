"""Legs for the delisting-notice short (E03, docs/OLD_SESSION_EDGES.md S2) from the Binance delisting catalog
(data/recorders/notices/binance_delisting.csv, scripts/record_notices.py) and the articles' plain text
(data/recorders/notices/articles/<id>.txt, scripts/fetch_notice_bodies.py). No price is read.

Two notice types count, by title:
- spot:    "Binance Will Delist A, B and C on YYYY-MM-DD" (also "... Vote to Delist Results and Will Delist ... on ...").
           Tickers come from the title.
- futures: "Binance Futures Will Delist ..." and titles announcing a USD-M futures delisting ("... USDⓈ-M Futures
           Contracts ...", "Delisting (of) USDⓈ-M ..."). Tickers are the union of the title's names and every
           <X>USDT symbol in the article text, so "Multiple Perpetual Contracts" titles are covered. Postponements are
           excluded.
Every other title (margin, loans, staking, options, leveraged tokens, trading-pair removals) is excluded and counted.
A leg is one ticker of one notice, mapped to the USD-M perp <T>USDT (a ticker already ending in USDT is kept as is;
BUSD-, USDC- and USD-quoted names are dropped). t0 is the notice's release time.

The catalog is append-only and grows every hour, so legs are built from notices released before --until (R267 froze
2026-10-20T17:00:00Z); a rebuild with the same cutoff is byte-identical.

usage: python scripts/delist_events.py [--out experiments/delist_v1] [--until 2026-10-20T17:00:00Z]
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

SRC = data.ROOT / "recorders" / "notices" / "binance_delisting.csv"
ARTICLES = data.ROOT / "recorders" / "notices" / "articles"
SPOT = re.compile(r"^Binance (?:Announced .+? and )?Will Delist (?P<names>.+?) on \d{4}-\d{2}-\d{2}\s*$", re.I)
FUT = re.compile(r"^Binance Futures Will Delist (?:and Update the Leverage & Margin Tiers of )?(?:the )?"
                 r"(?:(?:USD[ⓈT]|COIN)-?M(?:argined)? )?(?P<names>.+?) (?:USD[ⓈT]-?M(?:argined)? )?"
                 r"(?:Perpetual )?(?:Futures )?Contracts?\b", re.I)
FUT_OTHER = re.compile(r"USDⓈ-M Futures Contracts|Delisting (?:of )?USDⓈ-M", re.I)
POSTPONED = re.compile(r"Postpone", re.I)
TICKER = re.compile(r"[A-Z0-9]{1,15}")
UNTIL = "2026-10-20T17:00:00Z"
BODY_PERP = re.compile(r"\b[A-Z0-9]{1,20}USDT\b")


def names(text):
    """Tickers of a comma / and / & list, or [] if any part is not a bare ticker."""
    text = re.sub(r"(?:USD[ⓈT]|COIN)-?M(?:argined)?|Perpetual", " ", text, flags=re.I)
    parts = [p.strip().upper() for p in re.split(r",|&|\band\b", text, flags=re.I)]
    parts = [p for p in parts if p]
    return parts if parts and all(TICKER.fullmatch(p) for p in parts) else []


def parse(title, body=""):
    """(kind, [tickers]) or (None, []) for an excluded title."""
    t = re.sub(r"\s*\(.*?\)\s*$", "", title.strip())
    if POSTPONED.search(t) or re.search(r"Coin-Margined", t, re.I):     # COIN-M only; USD-M titles say USDⓈ-M
        return None, []
    m = SPOT.match(t)
    if m:
        ticks = names(m.group("names"))
        return ("spot", ticks) if ticks else (None, [])
    m = FUT.match(t)
    if m or FUT_OTHER.search(t):
        ticks = [] if not m or re.search(r"Multiple", t, re.I) else names(m.group("names"))
        ticks = list(dict.fromkeys(ticks + BODY_PERP.findall(body)))
        return ("futures", ticks) if ticks else (None, [])
    return None, []


def body(notice_id, articles=ARTICLES):
    f = articles / f"{notice_id}.txt"
    return f.read_text() if f.exists() else ""


def perp_for(ticker, perps):
    """The USD-M perp of a ticker: <T>USDT, else a 1000- or 1000000-prefixed contract in the archive."""
    if ticker.endswith("USDT"):
        return ticker, ticker in perps
    for c in (ticker + "USDT", "1000" + ticker + "USDT", "1000000" + ticker + "USDT"):
        if c in perps:
            return c, True
    return ticker + "USDT", False


def legs(src=SRC, root=None, until=UNTIL):
    root = Path(root or data.ROOT)
    perps = {f.stem for f in (root / "klines_1h").glob("*.parquet")}     # names only; no price is read
    end_ms = int(pd.Timestamp(data.END, tz="UTC").value // 10**6) + 86_400_000
    d = pd.read_csv(src)
    d = d[d.release_ms < int(pd.Timestamp(until).value // 10**6)]
    rows, excluded = [], []
    for r in d.itertuples():
        kind, ticks = parse(r.title, body(r.id))
        if kind is None:
            excluded.append(r.id)
            continue
        for t in ticks:
            if t.endswith(("BUSD", "USDC")) or (t.endswith("USD") and not t.endswith("USDT")):
                continue
            perp, in_archive = perp_for(t, perps)
            rows.append({"notice": int(r.id), "kind": kind, "ticker": t, "perp": perp, "in_archive": in_archive,
                         "window": "archive" if int(r.release_ms) < end_ms else "post_archive",
                         "release_ms": int(r.release_ms), "title": r.title})
    out = pd.DataFrame(rows).drop_duplicates(["notice", "perp"])
    out = out.sort_values(["release_ms", "notice", "perp"]).reset_index(drop=True)
    return out, d[d.id.isin(excluded)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "experiments" / "delist_v1"))
    ap.add_argument("--until", default=UNTIL)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L, ex = legs(until=a.until)
    L.to_csv(out / "legs.csv", index=False)
    print(f"{L.notice.nunique()} notices -> {len(L)} legs; {len(ex)} titles excluded")
    print(L.groupby(["window", "kind", "in_archive"]).agg(notices=("notice", "nunique"), legs=("perp", "size")).to_string())


if __name__ == "__main__":
    main()
