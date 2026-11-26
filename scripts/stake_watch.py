"""Stake 1 watch (register T1; docs/reviews/reflection_20261126_tail.md): the tail events a daily check cannot catch.

Public, read-only endpoints; no key, no order. Run it every hour while the stake is live (cron or by hand). It prints
one line per check and exits 1 if anything needs the owner within the hour.

Checks:
1. Hyperliquid `meta`: a held coin flagged isDelisted (a forced settlement or delisting, JELLY-type).
2. Hyperliquid `userFillsByTime` for the stake's public address since --since-hours: any fill that is a liquidation
   or an auto-deleveraging (the fill carries a `liquidation` object, or its `dir` names a liquidation, deleveraging
   or settlement), the 2025-10-10 case.
3. Kraken Futures `instruments`: a held PF_ contract that is missing, not tradeable, post-only or expired.
4. Kraken's support page of suspensions and delistings: a held PF_ symbol named on it (advance notice, when given).

On any ALERT: close the other leg of that coin on the other venue within the hour (stake-1 addendum,
docs/reviews/december_decision_20261125.md).

usage: python scripts/stake_watch.py --coins SYRUP,CAKE --kraken PF_SYRUPUSD,PF_CAKEUSD [--hl-address 0x...]
       [--since-hours 2]
"""
import argparse
import json
import re
import sys
import time
import urllib.request

HL = "https://api.hyperliquid.xyz/info"
KRAKEN = "https://futures.kraken.com/derivatives/api/v3/instruments"
KRAKEN_DELIST = "https://support.kraken.com/articles/7526425887508-Futures-contracts-trading-suspensions-delistings"
BAD_DIR = re.compile(r"liquidat|deleverag|settle", re.I)


def _get(url, body=None, tries=3):
    for i in range(tries):
        try:
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                                                  "User-Agent": "Mozilla/5.0 (lab-research)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
            return json.loads(raw) if body is not None or url.endswith("instruments") else raw.decode("utf-8", "ignore")
        except (OSError, ValueError):
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def hl_delisted(meta, coins):
    """Held coins that Hyperliquid's meta flags as delisted, or that are absent from it."""
    names = {x["name"]: x for x in meta.get("universe", [])}
    return [c for c in coins if c not in names or names[c].get("isDelisted")]


def hl_bad_fills(fills, coins):
    """Fills on held coins that are liquidations, deleveragings or settlements."""
    out = []
    for f in fills:
        if f.get("coin") not in coins:
            continue
        if f.get("liquidation") or BAD_DIR.search(str(f.get("dir", ""))):
            out.append({"coin": f.get("coin"), "dir": f.get("dir"), "px": f.get("px"), "sz": f.get("sz"),
                        "time": f.get("time")})
    return out


def kraken_problems(instruments, symbols):
    """Held PF_ symbols that are missing, not tradeable, post-only or expired."""
    by = {x.get("symbol"): x for x in instruments.get("instruments", [])}
    out = []
    for s in symbols:
        x = by.get(s)
        if x is None:
            out.append((s, "missing"))
        elif not x.get("tradeable", False):
            out.append((s, "not tradeable"))
        elif x.get("postOnly"):
            out.append((s, "post-only"))
        elif x.get("isExpired"):
            out.append((s, "expired"))
    return out


def kraken_named(page, symbols):
    """Held PF_ symbols named on Kraken's suspensions and delistings page."""
    return [s for s in symbols if re.search(r"\b" + re.escape(s) + r"\b", page)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coins", required=True, help="held Hyperliquid coins, comma-separated (e.g. SYRUP,CAKE)")
    ap.add_argument("--kraken", required=True, help="held Kraken PF_ symbols, comma-separated")
    ap.add_argument("--hl-address", default="", help="the stake's public Hyperliquid address (0x...)")
    ap.add_argument("--since-hours", type=float, default=2.0)
    a = ap.parse_args()
    coins = [c.strip() for c in a.coins.split(",") if c.strip()]
    syms = [s.strip() for s in a.kraken.split(",") if s.strip()]
    alerts = []
    d = hl_delisted(_get(HL, {"type": "meta"}), coins)
    alerts += [f"ALERT hyperliquid {c}: delisted or absent; close its Kraken leg" for c in d]
    print(f"hyperliquid meta: {len(coins)} held, {len(d)} delisted")
    if a.hl_address:
        since = int((time.time() - a.since_hours * 3600) * 1000)
        fills = _get(HL, {"type": "userFillsByTime", "user": a.hl_address, "startTime": since})
        bad = hl_bad_fills(fills, set(coins))
        alerts += [f"ALERT hyperliquid {b['coin']}: {b['dir']} at {b['px']} (size {b['sz']}); close its Kraken leg"
                   for b in bad]
        print(f"hyperliquid fills since {a.since_hours} h: {len(fills)}, flagged {len(bad)}")
    k = kraken_problems(_get(KRAKEN), syms)
    alerts += [f"ALERT kraken {s}: {why}; close its Hyperliquid leg" for s, why in k]
    print(f"kraken instruments: {len(syms)} held, {len(k)} with a problem")
    try:
        named = kraken_named(_get(KRAKEN_DELIST), syms)
        alerts += [f"ALERT kraken {s}: named on the suspensions/delistings page; plan the exit" for s in named]
        print(f"kraken delistings page: {len(named)} held symbols named")
    except OSError as e:
        print(f"kraken delistings page: not read ({e})")
    for x in alerts:
        print(x)
    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
