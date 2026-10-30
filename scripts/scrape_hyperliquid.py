"""Forward collector of on-chain trader data from Hyperliquid, for docs/CLAIMS.md C04 (do top on-chain traders keep
winning; does mirroring their positions pay). Data collection only: no statistic. The sources keep no history, so the
outputs are small gzipped CSVs under experiments/copylead_data/hyperliquid/, meant to be committed.

daily   once per UTC day; a day already written is skipped.
  leaderboard/{day}.csv.gz  filtered snapshot of GET stats-data.hyperliquid.xyz/Mainnet/leaderboard (about 39 MB,
      47k rows, one cached file refreshed by Hyperliquid about hourly; its Last-Modified is kept as
      source_modified_utc). Kept: accountValue >= USD 1 M OR |allTime pnl| >= USD 1 M OR month vlm >= USD 10 M.
      Columns: ethAddress, accountValue, {day,week,month,allTime}_{pnl,roi,vlm}, snapshot_utc, source_modified_utc.
      displayName is dropped (personal handles are not stored).
  picks/{day}.csv  the accounts the hourly job follows. Rule, fixed before any data was looked at:
      eligible = accountValue >= USD 1 M and month vlm >= USD 10 M;
      picks    = top 50 eligible by month pnl  UNION  top 50 eligible by allTime pnl
      (pnl descending, ties broken by address). Column `list` = month | allTime | both, with the rank in each list.
      Built from the saved snapshot, so it can be rebuilt exactly.

hourly  for the latest picks file, POST api.hyperliquid.xyz/info per pick:
      clearinghouseState (the pick's own positions) and subAccounts (each sub-account's clearinghouseState). A master's
      leaderboard row aggregates its sub-accounts, whose positions do not show in the master's own clearinghouseState.
  positions/{day}.csv.gz  a change log of open perp positions, keyed by (address, account, coin):
      kind = snapshot: the first hour written in the day file, every open position of every account read, so each
          day file stands alone;
      kind = change: later hours, a row only when a position opens, closes (szi = 0, other fields NaN), flips sign,
          or moves by |szi - szi_written| >= TOL (10%) of |szi_written|, szi_written being the last size written for
          that (address, account, coin); drift accumulates until it crosses 10%. Each account read is compared with
          its last written state in the day file, so an account missed in an hour is compared with what was written
          when it was last read.
      positions_at(day, hour) rebuilds the full table for an hour. The set of open positions and their signs are
      exact; sizes are exact at the snapshot hour and APPROXIMATE TO 10% between snapshots (|true - rebuilt| <
      10% of |rebuilt|); the other fields are as of the hour the row was written. Sizes are written in shortest
      round-trip form and read with float_precision="round_trip".
      Columns: hour_utc (run start floored to the hour), kind, address (the pick), account (the pick itself or the
      sub-account holding the position), coin, szi (signed size), entryPx, positionValue, unrealizedPnl,
      leverage_type, leverage, marginUsed, liquidationPx, then the holding account's marginSummary (accountValue,
      totalNtlPos, totalRawUsd, totalMarginUsed), withdrawable, time_ms (server time).
      Before writing, the hourly job checks that the file it is about to write rebuilds, for the accounts read,
      exactly the fetched set of open positions, each with the fetched sign and within TOL of the fetched size.
  accounts/{day}.csv.gz  one row per account read that hour (every pick; sub-accounts with value or positions), with
      n_positions and the same totals, complete every hour. An address absent from an hour was not read (fetch
      failed) and keeps its last known positions. It is also the hour's done mark: an hour already in it is skipped.
  Only the main perp dex is read: builder-deployed HIP-3 dexes (xyz:..., flx:..., ...) and spot balances are not.
  Pacing: at least 0.2 s between calls and at most BUDGET request weight a minute (Hyperliquid allows 1200 per IP).

usage: python scripts/scrape_hyperliquid.py [daily|hourly|both]     (default both)
"""
import argparse
import gzip
import io
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "copylead_data" / "hyperliquid"
LEADERBOARD = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
INFO = "https://api.hyperliquid.xyz/info"
WINDOWS = ("day", "week", "month", "allTime")
KEEP_AV, KEEP_ALLTIME_PNL, KEEP_MONTH_VLM = 1e6, 1e6, 1e7          # snapshot filter (any one)
PICK_AV, PICK_MONTH_VLM, PICK_TOP = 1e6, 1e7, 50                   # pick rule (both, then top 50 per list)
WEIGHT = {"clearinghouseState": 2, "subAccounts": 20}              # info request weights (others are 20)
BUDGET = 800                                                       # weight a minute we allow ourselves
FLOAT = "%.12g"
TOL = 0.10                                                         # change log: relative size move worth a row
KEY =["address", "account", "coin"]
TOTALS = ["accountValue", "totalNtlPos", "totalRawUsd", "totalMarginUsed", "withdrawable", "time_ms"]
POS_COLS = ["hour_utc", "kind", *KEY, "szi", "entryPx", "positionValue", "unrealizedPnl", "leverage_type", "leverage",
            "marginUsed", "liquidationPx", *TOTALS]
log =lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
num = lambda v: math.nan if v is None else float(v)


class FetchError(Exception):
    pass


def fetch(url, body=None, tries=4, timeout=30):
    """GET (no body) or POST JSON; returns (parsed JSON, response headers). Retries with doubling backoff."""
    data = None if body is None else json.dumps(body).encode()
    delay, err = 2.0, None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, method="GET" if data is None else "POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "lab-paper/1"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read()), r.headers
        except (OSError, ValueError) as e:            # HTTP errors, timeouts, resets; ValueError: truncated JSON
            err = e
            if attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
    raise FetchError(f"{url} {json.dumps(body) if body else ''}: {err!r}")


def info(body):
    d = fetch(INFO, body)[0]
    time.sleep(max(0.2, WEIGHT.get(body["type"], 20) * 60 / BUDGET))
    return d


def text(df):
    """CSV text as saved. szi is written in shortest round-trip form so sizes survive the file exactly."""
    if "szi" in df:
        df = df.assign(szi=[repr(float(x)) for x in df.szi])
    return df.to_csv(index=False, float_format=FLOAT)


def read(path):
    return pd.read_csv(path, float_precision="round_trip")


def save(df, path):
    """Write atomically (tmp then rename), gzip when the name ends in .gz."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    data = text(df).encode()
    with (gzip.open(tmp, "wb") if path.suffix == ".gz" else open(tmp, "wb")) as f:
        f.write(data)
    os.replace(tmp, path)


# ---------------------------------------------------------------- daily

def flatten(rows):
    out = []
    for x in rows:
        perf = dict(x.get("windowPerformances") or [])
        r = {"ethAddress": x["ethAddress"].lower(), "accountValue": num(x.get("accountValue"))}
        for w in WINDOWS:
            for k in ("pnl", "roi", "vlm"):
                r[f"{w}_{k}"] = num((perf.get(w) or {}).get(k))
        out.append(r)                                 # displayName and prize deliberately not kept
    return pd.DataFrame(out)


def keep(snap):
    return ((snap.accountValue >= KEEP_AV) | (snap.allTime_pnl.abs() >= KEEP_ALLTIME_PNL)
            | (snap.month_vlm >= KEEP_MONTH_VLM))


def picks_from(snap):
    el = snap[(snap.accountValue >= PICK_AV) & (snap.month_vlm >= PICK_MONTH_VLM)]
    rank = {}
    for w in ("month", "allTime"):
        top = el.sort_values([f"{w}_pnl", "ethAddress"], ascending=[False, True]).head(PICK_TOP)
        rank[w] = dict(zip(top.ethAddress, range(1, len(top) + 1)))
    m, t = rank["month"], rank["allTime"]
    rows = [{"address": a, "list": "both" if a in m and a in t else "month" if a in m else "allTime",
             "rank_month": m.get(a), "rank_allTime": t.get(a)} for a in set(m) | set(t)]
    df = pd.DataFrame(rows).sort_values(["rank_month", "rank_allTime"], na_position="last")
    return df.assign(rank_month=df.rank_month.astype("Int64"), rank_allTime=df.rank_allTime.astype("Int64"),
                      snapshot_utc=snap.snapshot_utc.iloc[0])


def daily(now):
    day = now.strftime("%Y-%m-%d")
    snap_path, picks_path = OUT / "leaderboard" / f"{day}.csv.gz", OUT / "picks" / f"{day}.csv"
    if not snap_path.exists():
        d, h = fetch(LEADERBOARD, timeout=180)
        full = flatten(d["leaderboardRows"])
        modified = h.get("Last-Modified")
        snap = full[keep(full)].assign(snapshot_utc=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                       source_modified_utc=parsedate_to_datetime(modified).astimezone(timezone.utc)
                                       .strftime("%Y-%m-%dT%H:%M:%SZ") if modified else "")
        save(snap, snap_path)
        log(f"leaderboard {len(full)} rows, kept {len(snap)} -> {snap_path.relative_to(ROOT)}")
    if not picks_path.exists():
        picks = picks_from(pd.read_csv(snap_path))
        save(picks, picks_path)
        log(f"picks {len(picks)} -> {picks_path.relative_to(ROOT)}")


# ---------------------------------------------------------------- hourly

def rows_from(state, hour, address, account):
    ms = state.get("marginSummary") or {}
    tot = {k: num(ms.get(k)) for k in ("accountValue", "totalNtlPos", "totalRawUsd", "totalMarginUsed")}
    tot |= {"withdrawable": num(state.get("withdrawable")), "time_ms": state.get("time")}
    base = {"hour_utc": hour, "address": address, "account": account}
    pos = []
    for ap in state.get("assetPositions") or []:
        p = ap["position"]
        lev = p.get("leverage") or {}
        if not num(p.get("szi")):                     # szi 0 marks a closed position in the change log
            continue
        pos.append(base | {"coin": p["coin"], "szi": num(p.get("szi")), "entryPx": num(p.get("entryPx")),
                           "positionValue": num(p.get("positionValue")), "unrealizedPnl": num(p.get("unrealizedPnl")),
                           "leverage_type": lev.get("type"), "leverage": num(lev.get("value")),
                           "marginUsed": num(p.get("marginUsed")), "liquidationPx": num(p.get("liquidationPx"))}
                   | tot)
    return base | {"is_sub": account != address, "n_positions": len(pos)} | tot, pos


def rebuild(log_df, hour=None):
    """Positions open at `hour` (default: the last) from a change-log frame: the last row per key, closed dropped."""
    df = log_df if hour is None else log_df[log_df.hour_utc <= hour]
    last = df.sort_values("hour_utc", kind="stable").drop_duplicates(KEY, keep="last")
    return last[last.szi != 0].reset_index(drop=True)


def positions_at(day, hour=None):
    """Full position table at `hour` (0-23 or 'YYYY-MM-DDTHH:00:00Z'; default the day's last) from positions/{day}.
    Accounts not read at that hour (absent from accounts/{day}) carry their last known positions."""
    if isinstance(hour, int):
        hour = f"{day}T{hour:02d}:00:00Z"
    return rebuild(read(OUT / "positions" / f"{day}.csv.gz"), hour)


def moved(written, szi):
    """True when a size must be written: the position flipped sign or moved >= TOL of the last written size."""
    return (written > 0) != (szi > 0) or abs(szi - written) >= TOL * abs(written)


def changes(prev, fetched, accounts_read, hour, kind):
    """Rows that turn `prev` into `fetched` for the accounts read, to within TOL: opened, flipped or moved positions
    as fetched, and a szi = 0 row for each position of a read account that is gone."""
    was = {t[:3]: t[3] for t in prev[KEY + ["szi"]].itertuples(index=False, name=None)}
    now = {tuple(r[k] for k in KEY): r for r in fetched}
    rows = [r for k, r in now.items() if k not in was or moved(was[k], r["szi"])]
    rows += [dict(zip(KEY, k), szi=0.0) for k in was if k[:2] in accounts_read and k not in now]
    return [r | {"hour_utc": hour, "kind": kind} for r in rows]


def join(before, rows):
    new = pd.DataFrame(rows, columns=POS_COLS)
    return new if not len(before) else pd.concat([before, new], ignore_index=True) if rows else before


def check(before, rows, fetched, accounts_read):
    """The file about to be written, read back, must rebuild for the accounts read exactly the fetched set of open
    positions, each with the fetched sign and its size within TOL (measured as in moved(), against the rebuilt size)."""
    df = join(before, rows)
    back = rebuild(read(io.StringIO(text(df)))) if len(df) else pd.DataFrame(columns=KEY + ["szi"])
    got = {k[:3]: k[3] for k in back[KEY + ["szi"]].itertuples(index=False, name=None) if k[:2] in accounts_read}
    want = {tuple(r[k] for k in KEY): r["szi"] for r in fetched}
    bad = sorted(set(got) ^ set(want))[:5]                                   # missing or extra positions
    bad += [(k, got[k], s) for k, s in want.items() if k in got and moved(got[k], s)][:5]   # sign or size off
    if bad:
        raise RuntimeError(f"change log does not rebuild the fetched state: {bad}")


def has_hour(path, hour):
    return path.exists() and (pd.read_csv(path, usecols=["hour_utc"]).hour_utc == hour).any()


def hourly(now):
    files = sorted((OUT / "picks").glob("*.csv"))
    if not files:
        log("hourly: no picks file yet")
        return True
    hour = now.strftime("%Y-%m-%dT%H:00:00Z")
    day = now.strftime("%Y-%m-%d")
    acc_path, pos_path = OUT / "accounts" / f"{day}.csv.gz", OUT / "positions" / f"{day}.csv.gz"
    if has_hour(acc_path, hour):
        return True
    picks = pd.read_csv(files[-1])
    accounts, fetched, accounts_read, failed = [], [], set(), []
    for addr in picks.address.str.lower():
        try:
            states = [(addr, info({"type": "clearinghouseState", "user": addr}))]
            states += [(s["subAccountUser"].lower(), s["clearinghouseState"])
                       for s in info({"type": "subAccounts", "user": addr}) or []]
        except FetchError as e:                       # this pick is missing from this hour; others still count
            failed.append(addr)
            log("hourly:", e)
            continue
        for account, st in states:
            acc, pos = rows_from(st, hour, addr, account)
            accounts_read.add((addr, account))        # empty sub-accounts too: their closes must be logged
            fetched += pos
            if account != addr and not pos and not acc["accountValue"]:
                continue                              # empty sub-account: no row in accounts/
            accounts.append(acc)
    if not accounts:
        log("hourly: nothing read; the hour is retried on the next tick")
        return False
    if has_hour(acc_path, hour):                      # another run finished this hour meanwhile
        return True
    old = read(pos_path) if pos_path.exists() else pd.DataFrame(columns=POS_COLS)
    before = old[old.hour_utc < hour]                 # drops a half-written attempt at this hour
    kind = "change" if len(before) else "snapshot"
    rows = changes(rebuild(before), fetched, accounts_read, hour, kind)
    check(before, rows, fetched, accounts_read)       # raises before anything is written
    if rows or len(before) != len(old):
        save(join(before, rows), pos_path)
    acc_old = pd.read_csv(acc_path) if acc_path.exists() else None
    save(pd.concat([acc_old[acc_old.hour_utc != hour], pd.DataFrame(accounts)], ignore_index=True)
         if acc_old is not None else pd.DataFrame(accounts), acc_path)   # last: marks the hour done
    log(f"hourly {hour}: picks {len(picks)} ({files[-1].name}), failed {len(failed)}, accounts {len(accounts)}, "
        f"open positions {len(fetched)}, {kind} rows {len(rows)} -> {pos_path.relative_to(ROOT)}")
    return not failed


def main():
    ap = argparse.ArgumentParser(description="Hyperliquid leaderboard snapshot (daily) and picks' positions (hourly)")
    ap.add_argument("job", nargs="?", default="both", choices=("daily", "hourly", "both"))
    a = ap.parse_args()
    now = datetime.now(timezone.utc)
    ok = True
    if a.job in ("daily", "both"):
        try:
            daily(now)
        except (FetchError, KeyError) as e:           # retried on the next tick; hourly uses the latest picks
            log("daily failed:", e)
            ok = False
    if a.job in ("hourly", "both"):
        ok = hourly(now) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
