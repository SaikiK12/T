"""Legs for the announcement-family scan (R271) from Binance's three notice catalogs
(data/recorders/notices/binance_{news,delisting,listing}.csv, scripts/record_notices.py). Parses titles only; no price
is read. Types already tested elsewhere are left out: spot and futures delisting (R267) and the Monitoring Tag (R269).

Types (title rules in TYPES below; tickers come from the title):
- spot_list:     "Binance Will List / Lists Name (TKR) ..." (Innovation Zone, Seed Tag and HODLer listings included)
- perp_launch:   "Binance Futures Will Launch USDⓈ-M A, B and C Perpetual Contract(s)" (no TradFi, COIN-M, USDC,
                 quarterly or pre-market)
- prelist:       "Introducing Name (TKR) on Binance Launchpool / Launchpad / HODLer Airdrops / Megadrop"
- margin_add:    cross or isolated margin enabled or added for named coins
- earn_add:      Convert, Simple Earn, Staking, Auto-Invest or Savings adds a named coin
- pairs_add:     "Binance Adds A/B, C/D Trading Pairs" (the base coins)
- fund_freq:     a change of one perp's funding settlement frequency (not "resumed")
- upgrade:       "Binance Will Support the Name (TKR) Network Upgrade / Hard Fork / Token Swap / Rebrand / Migration"
- holder_drop:   "Binance Will Support the ... Airdrop for Name (TKR) Holders" (the holders' coin)

A leg is one ticker of one notice. Instrument candidates, by name only (the runner takes the first one that traded in
the notice's hour): the Binance USD-M perp (data/klines_1h), else the MEXC perp (data/mexc_hist, only for coins that
have a Binance perp in the archive, so the reserved MEXC-only coins are never touched), else the Binance spot pair
(data/spot_1h). Notices released before 2021-01-01 (the reserved 2020 sample) or after the archive end are kept with
window "reserved_2020" / "post_archive" and never priced here. Rows released at or after --until are left out, so a
rebuild is byte-identical.

usage: python scripts/announce_events.py [--out experiments/announce_v1] [--until 2026-10-20T17:00:00Z]
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data  # noqa: E402
from delist_events import perp_for  # noqa: E402

SRC = [data.ROOT / "recorders" / "notices" / f"binance_{c}.csv" for c in ("news", "delisting", "listing")]
UNTIL = "2026-10-20T17:00:00Z"
START = "2021-01-01"
TK = r"[A-Z0-9]{1,15}"
PAREN = re.compile(r"\((" + TK + r")\)")
QUOTE = ("USDT", "BUSD", "USDC", "FDUSD", "TUSD", "BTC", "ETH", "BNB", "EUR", "TRY", "BRL", "GBP", "AUD", "RUB", "UAH",
         "BIDR", "IDRT", "NGN", "PLN", "RON", "ZAR", "ARS", "JPY", "MXN", "COP", "CZK", "DAI", "PAX", "USDP", "AEUR")
STABLE = {"USDT", "BUSD", "USDC", "FDUSD", "TUSD", "DAI", "PAX", "USDP", "AEUR", "EUR", "RLUSD", "USD1", "XUSD", "UST",
          "USDE", "PYUSD", "EURI", "BFUSD", "U"}


def bare(text):
    """Bare tickers in a comma / and / & list: words of capitals and digits, quote suffixes stripped."""
    out = []
    for w in re.findall(r"\b" + TK + r"\b", text):
        if w in {"USDⓈ", "M", "USD", "COIN", "N", "X"} or w.isdigit():
            continue
        for q in ("USDT", "BUSD"):
            if w.endswith(q) and len(w) > len(q):
                w = w[: -len(q)]
        out.append(w)
    return out


def clean(text):
    """Tickers of a comma / and / & list ("& More Pairs" dropped), or [] if any part is not a bare ticker."""
    text = re.sub(r"\s*(?:&|and)?\s*More( \w+)? Pairs.*$", "", text.strip())
    parts = [x.strip() for x in re.split(r",|&|\band\b", text) if x.strip()]
    return parts if parts and all(re.fullmatch(TK, x) for x in parts) else []


def spot_list(t):
    if re.search(r"Leveraged Token|Futures|Options|Margin|Convert|Alpha|Earn\b|Loans?\b|Delist", t, re.I):
        return None
    if not re.match(r"Binance (Will List|Lists) ", t):
        return None
    return PAREN.findall(t) or clean(re.sub(r"^Binance (Will List|Lists) ", "", t).split(" in the ")[0])


def perp_launch(t):
    if not re.match(r"Binance Futures Will Launch", t) or re.search(
            r"TradFi|Equity|Stock|Commodit|Coin-Margined|COIN-M|USDC|Quarterly|Delivery|Pre-Market|Multiple", t, re.I):
        return None
    m = re.search(r"Will Launch (.+?) Perpetual", t)
    return bare(re.sub(r"USDⓈ-M(argined)?|USDT-M(argined)?|-Margined|Margined", " ", m.group(1))) if m else None


def prelist(t):
    if re.match(r"Introducing ", t) and re.search(r"Launchpool|Launchpad|HODLer Airdrop|Megadrop", t):
        return PAREN.findall(t)[:1] or None
    return None


MARGIN = [r"Binance Adds (?P<n>.+?) on (?:Cross|Isolated) Margin", r"(?:Isolated|Cross) Margin Trading for (?P<n>.+?) Enabled",
          r"^(?P<n>.+?) Enabled on Binance (?:Isolated|Cross) Margin", r"Binance Adds Margin Trading for (?P<n>.+)",
          r"Binance Adds \w+ Margin Pairs for (?P<n>.+)", r"^Margin Trading for (?P<n>.+?) Enabled"]
EARN = [r"Binance Convert Adds (?P<n>.+)", r"Binance Adds (?P<n>.+?) on (?:Simple )?Earn", r"Binance Staking Launches (?P<n>\S+) Staking",
        r"Auto-Invest Adding (?P<n>.+)", r"Binance Savings Adds (?P<n>.+?) to"]


def by_rules(rules):
    def f(t):
        for r in rules:
            m = re.search(r, t)
            if m:
                return PAREN.findall(m.group("n")) or clean(m.group("n"))
        return None
    return f


def pairs_add(t):
    m = re.search(r"Binance Adds (.+?) Trading Pairs?", t)
    return sorted({p.split("/")[0] for p in re.findall(TK + "/" + TK, m.group(1))}) if m else None


def fund_freq(t):
    if not re.search(r"Funding Rate Settlement Frequency", t) or re.search(r"Resum|Restor", t, re.I):
        return None
    return [re.sub("(USDT|BUSD)$", "", w) for w in re.findall(r"\b([A-Z0-9]{2,20}(?:USDT|BUSD))\b", t)] or None


def upgrade(t):
    if re.match(r"Binance Will Support the", t) and re.search(
            r"Network Upgrade|Hard Fork|Token Swap|Rebrand|Migration|Redenomination", t) and not re.search(r"Airdrop", t):
        return PAREN.findall(t)[:1] or None
    return None


def holder_drop(t):
    m = re.search(r"Airdrop (?:Program )?for .*?\((" + TK + r")\) Holders", t)
    return [m.group(1)] if m and re.match(r"Binance Will Support", t) else None


TYPES = {"spot_list": spot_list, "perp_launch": perp_launch, "prelist": prelist, "margin_add": by_rules(MARGIN),
         "earn_add": by_rules(EARN), "pairs_add": pairs_add, "fund_freq": fund_freq, "upgrade": upgrade,
         "holder_drop": holder_drop}


def parse(title):
    """[(type, [tickers])] for every type whose title rule matches."""
    t = title.strip()
    out = []
    for k, f in TYPES.items():
        ticks = f(t)
        ticks = [x for x in dict.fromkeys(ticks or []) if x not in STABLE and x not in QUOTE]
        if ticks:
            out.append((k, ticks))
    return out


def mexc_for(ticker, contracts):
    for base, m in ((ticker, 1), ("1000" + ticker, 1000), ("1000000" + ticker, 1_000_000)):
        if base in contracts:
            return contracts[base]
    return ""


def legs(src=SRC, root=None, until=UNTIL):
    root = Path(root or data.ROOT)
    perps = {f.stem for f in (root / "klines_1h").glob("*.parquet")}           # names only; no price is read
    spots = {f.stem for f in (root / "spot_1h").glob("*.parquet")}
    mexc = {f.stem.split("_")[0]: f.stem for f in (root / "mexc_hist" / "klines_1h").glob("*_USDT.parquet")}
    start_ms = int(pd.Timestamp(START, tz="UTC").value // 10**6)
    end_ms = int(pd.Timestamp(data.END, tz="UTC").value // 10**6) + 86_400_000
    d = pd.concat([pd.read_csv(p) for p in src]).drop_duplicates("id").sort_values("id")
    d = d[d.release_ms < int(pd.Timestamp(until).value // 10**6)]
    rows = []
    for r in d.itertuples():
        for kind, ticks in parse(r.title):
            for t in ticks:
                perp, in_archive = perp_for(t, perps)
                rel = int(r.release_ms)
                rows.append({"notice": int(r.id), "kind": kind, "ticker": t, "perp": perp if in_archive else "",
                             "mexc": mexc_for(t, mexc) if in_archive else "",
                             "spot": t + "USDT" if t + "USDT" in spots else "",
                             "window": "reserved_2020" if rel < start_ms else ("archive" if rel < end_ms else "post_archive"),
                             "release_ms": rel, "title": r.title})
    out = pd.DataFrame(rows).drop_duplicates(["notice", "kind", "ticker"])
    return out.sort_values(["release_ms", "notice", "kind", "ticker"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "experiments" / "announce_v1"))
    ap.add_argument("--until", default=UNTIL)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = legs(until=a.until)
    L.to_csv(out / "legs.csv", index=False)
    print(f"{L.notice.nunique()} notices -> {len(L)} legs")
    L["inst"] = (L.perp != "").map({True: "perp", False: ""}) + (L.mexc != "").map({True: "+mexc", False: ""}) \
        + (L.spot != "").map({True: "+spot", False: ""})
    print(L.groupby(["kind", "window"]).agg(notices=("notice", "nunique"), legs=("ticker", "size"),
                                             perp=("perp", lambda s: (s != "").sum()), mexc=("mexc", lambda s: (s != "").sum()),
                                             spot=("spot", lambda s: (s != "").sum())).to_string())


if __name__ == "__main__":
    main()
