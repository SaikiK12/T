"""Hourly record of which coins can be deposited and withdrawn on Bithumb, Gate, KuCoin, HTX and Bitget (M294).

When a venue stops deposits or withdrawals of a coin, arbitrage stops closing the gap between that venue's price and
everyone else's. Builders of arbitrage bots say large cross-venue gaps nearly always come with a wallet offline
(docs/COMMENT_DIG.md). No archive keeps these statuses, so the clock starts with this recorder. Each venue serves its
statuses without an account (read 2026-10-21); Upbit, MEXC, Binance and OKX need an API key, so they are not here.

Rows are (venue, coin, chain, deposit, withdraw), one per network a coin travels on (Bithumb gives one per coin, chain
""). Files under data/recorders/wallets/ (gitignored; digests committed by record_digest.py):
- <YYYY-MM-DD>/full.parquet: every row, at the first run of each UTC day;
- <YYYY-MM-DD>/<HH>.parquet: the rows that changed since the previous run (kind new, change or gone, with the
  previous statuses), written every hour, empty when nothing changed. A second run in the same hour writes nothing.
The last state is kept in data/logs/wallets_state.parquet, outside the digested folder. A venue whose request fails
keeps its previous state and adds no rows that hour. Data collection only.

usage: python scripts/record_wallets.py
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "recorders" / "wallets"
STATE = data.ROOT / "logs" / "wallets_state.parquet"
KEY = ["venue", "coin", "chain"]
COLS = KEY + ["deposit", "withdraw"]
CHANGE_COLS = ["ts"] + COLS + ["prev_deposit", "prev_withdraw", "kind"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def bithumb(j):
    return [("", c, v["deposit_status"] == 1, v["withdrawal_status"] == 1) for c, v in j["data"].items()]


def gate(j):
    out = []
    for c in j:
        chains = c.get("chains") or [{"name": c.get("chain") or "", "deposit_disabled": c.get("deposit_disabled"),
                                      "withdraw_disabled": c.get("withdraw_disabled")}]
        out += [(ch.get("name") or "", c["currency"], not ch.get("deposit_disabled"), not ch.get("withdraw_disabled"))
                for ch in chains]
    return out


def kucoin(j):
    return [(ch.get("chainName") or ch.get("chainId") or "", c["currency"], bool(ch.get("isDepositEnabled")),
             bool(ch.get("isWithdrawEnabled"))) for c in j["data"] for ch in c.get("chains") or []]


def htx(j):
    return [(ch.get("displayName") or ch.get("chain") or "", c["currency"], ch.get("depositStatus") == "allowed",
             ch.get("withdrawStatus") == "allowed") for c in j["data"] for ch in c.get("chains") or []]


def bitget(j):
    return [(ch.get("chain") or "", c["coin"], str(ch.get("rechargeable")).lower() == "true",
             str(ch.get("withdrawable")).lower() == "true") for c in j["data"] for ch in c.get("chains") or []]


VENUES = {
    "bithumb": ("https://api.bithumb.com/public/assetsstatus/ALL", bithumb),
    "gate": ("https://api.gateio.ws/api/v4/spot/currencies", gate),
    "kucoin": ("https://api.kucoin.com/api/v3/currencies", kucoin),
    "htx": ("https://api.huobi.pro/v2/reference/currencies", htx),
    "bitget": ("https://api.bitget.com/api/v2/spot/public/coins", bitget),
}


def http(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lab/1", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def frame(venue, rows):
    df = pd.DataFrame(rows, columns=["chain", "coin", "deposit", "withdraw"])
    df.insert(0, "venue", venue)
    df["coin"] = df.coin.astype(str).str.upper()
    return df.drop_duplicates(KEY, keep="last")[COLS]


def snapshot(get=None, venues=None):
    """The current statuses of every venue that answered, and the venues that failed."""
    get = get or http
    frames, failed = [], []
    for name, (url, parse) in (venues or VENUES).items():
        try:
            df = frame(name, parse(get(url)))
            if df.empty:
                raise ValueError("no rows")
            frames.append(df)
        except Exception as e:  # noqa: BLE001 - one venue failing does not stop the others
            failed.append(f"{name}: {type(e).__name__}: {e}")
    cur = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLS)
    return cur, failed


def changes(prev, cur, ts):
    """Rows of `cur` that are new or changed against `prev`, and rows of `prev` gone from `cur`, for the venues in
    `cur` only (a venue that failed this hour is not compared)."""
    prev = prev[prev.venue.isin(set(cur.venue))]
    m = cur.merge(prev, on=KEY, how="outer", suffixes=("", "_p"), indicator=True)
    m["kind"] = m["_merge"].map({"left_only": "new", "right_only": "gone", "both": "change"}).astype(str)
    both = m.kind == "change"
    m = m[~both | (m.deposit != m.deposit_p) | (m.withdraw != m.withdraw_p)].copy()
    m["ts"] = ts
    m = m.rename(columns={"deposit_p": "prev_deposit", "withdraw_p": "prev_withdraw"})
    for c in ("deposit", "withdraw", "prev_deposit", "prev_withdraw"):
        m[c] = m[c].astype("boolean")
    return m[CHANGE_COLS].sort_values(KEY).reset_index(drop=True)


def write(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")                  # record_digest.py skips .part files
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def run(now=None, out=OUT, state=STATE, get=None, venues=None):
    now = time.time() if now is None else now
    t = time.gmtime(now)
    day = out / time.strftime("%Y-%m-%d", t)
    hour = day / f"{time.strftime('%H', t)}.parquet"
    if hour.exists():
        log(f"wallets: {hour.relative_to(out.parent.parent)} already written")
        return None
    cur, failed = snapshot(get, venues)
    for f in failed:
        log(f"wallets: {f}")
    if cur.empty:
        log("wallets: nothing read")
        return None
    ts = int(now * 1000)
    prev = pd.read_parquet(state) if Path(state).exists() else None
    ch = changes(prev, cur, ts) if prev is not None else pd.DataFrame(columns=CHANGE_COLS)
    if not (day / "full.parquet").exists():
        write(cur.assign(ts=ts)[["ts"] + COLS], day / "full.parquet")
    write(ch, hour)
    keep = prev[~prev.venue.isin(set(cur.venue))] if prev is not None else cur.iloc[:0]
    write(pd.concat([keep, cur], ignore_index=True) if len(keep) else cur, Path(state))
    closed = cur[~(cur.deposit & cur.withdraw)]
    log(f"wallets: {len(cur)} rows on {cur.venue.nunique()} venues, {len(closed)} with deposit or withdrawal off; "
        f"{len(ch)} changes -> {hour.relative_to(out.parent.parent)}")
    return hour


if __name__ == "__main__":
    run()
