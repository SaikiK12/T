"""R270 montag_fwd: the Monitoring Tag short at +24 h, forward on MEXC paper (experiments/montag_fwd/PREREG.md).

Each tick (after scripts/record_notices.py and scripts/forward_delist.py): every "Extend the Monitoring Tag" notice
first seen since the freeze gets one ticket per tagged ticker with a MEXC perp, written before its entry bar opens.
Entry is the open of the first full hour after the ticket; the cover is 24 hours later (+1 h logged). Tickets are
scored once the +24 h bar has closed. Idempotent; journals in experiments/montag_fwd/journal/ are append-only,
status.json is derived. Ticketing (contract lookup, identity check, missed rule) is R268's.

usage: python scripts/forward_montag.py
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data, gate, mexc, prereg  # noqa: E402
import montag_events  # noqa: E402
from forward_delist import H, MAX_LAG, MODEL, SPOT_API, SPREAD_FALLBACK, bar_open, iso  # noqa: E402
from forward_unlocks import contract_for, spread_at, TICKS  # noqa: E402

LANE = ROOT / "experiments" / "montag_fwd"
J = LANE / "journal"
CATALOGS = [data.ROOT / "recorders" / "notices" / f"binance_{c}.csv" for c in ("news", "delisting")]
FIRST_SEEN_FROM = "2026-10-20T19:00:00Z"
N_DECIDE, N_FUTILE, DEADLINE = 12, 6, pd.Timestamp("2028-06-30", tz="UTC").value // 10**6
TICKET_COLS = ["ticket", "notice", "ticker", "contract", "mult", "title", "release_ms", "first_seen_utc", "frozen_at",
               "entry_ms", "exit_ms", "exit1h_ms", "last_at_freeze", "spot_price", "price_ratio", "check", "taker"]
SKIP_COLS = ["notice", "ticker", "reason", "detail", "noted_at"]
SCORE_COLS = ["ticket", "notice", "entry_price", "exit_price", "exit1h_price", "stopped_trading", "gross", "funding",
              "settlements", "taker", "spread_entry", "spread_exit", "spread_flag", "cost_measured", "net", "net_1x",
              "net_2x", "net_3x", "gross_1h", "funding_1h", "net1h_1x", "mae_24h", "scored_at"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def read(name, cols):
    p = J / name
    return pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame(columns=cols)


def append(name, rows, cols):
    if not rows:
        return
    p = J / name
    new = not p.exists() or not p.stat().st_size
    pd.DataFrame(rows, columns=cols).to_csv(p, mode="a", header=new, index=False)


def tag_notices(catalogs):
    """(notice row, tickers) for tag notices first seen since the freeze, by release time."""
    parts = [pd.read_csv(p) for p in catalogs if Path(p).exists() and Path(p).stat().st_size]
    if not parts:
        return []
    d = pd.concat(parts).drop_duplicates("id").sort_values(["release_ms", "id"])
    d = d[pd.to_datetime(d.first_seen_utc, utc=True) >= pd.Timestamp(FIRST_SEEN_FROM)]
    out = []
    for r in d.itertuples():
        for kind, ticks in montag_events.parse(r.title):
            if kind == "tag":
                out.append((r, ticks))
    return out


def score(t, bars, fund, ticks=TICKS):
    """One scored row for ticket t from its MEXC hourly bars (t, open, high, low, close) and settled funding."""
    e, x, x1 = int(t["entry_ms"]), int(t["exit_ms"]), int(t["exit1h_ms"])
    b = bars.sort_values("t")
    entry = bar_open(b, e)
    if entry is None:
        return None
    stopped = False
    px = {}
    for k, ms in (("24h", x), ("1h", x1)):
        p = bar_open(b, ms)
        if p is None:
            p, stopped = float(b[b.t < ms].close.iloc[-1]), True
        px[k] = p
    f24 = fund[(fund.t > e) & (fund.t <= x)]
    f1 = fund[(fund.t > e) & (fund.t <= x1)]
    se, sx = spread_at(e, t["contract"], ticks), spread_at(x, t["contract"], ticks)
    flag = se is None or sx is None
    se = SPREAD_FALLBACK if se is None else se
    sx = SPREAD_FALLBACK if sx is None else sx
    taker = float(t["taker"]) if pd.notna(t["taker"]) else 0.0
    cost = 2 * taker + se + sx
    gross, gross1 = -(px["24h"] / entry - 1), -(px["1h"] / entry - 1)
    funding, funding1 = float(f24.rate.sum()), float(f1.rate.sum())
    row = {"ticket": t["ticket"], "notice": int(t["notice"]), "entry_price": entry, "exit_price": px["24h"],
           "exit1h_price": px["1h"], "stopped_trading": stopped, "gross": gross, "funding": funding,
           "settlements": int(len(f24)), "taker": taker, "spread_entry": se, "spread_exit": sx, "spread_flag": flag,
           "cost_measured": cost, "net": gross - cost + funding, "gross_1h": gross1, "funding_1h": funding1,
           "net1h_1x": gross1 - MODEL["1x"] + funding1,
           "mae_24h": float(b[(b.t >= e) & (b.t < x)].high.max() / entry - 1)}
    for k, c in MODEL.items():
        row[f"net_{k}"] = gross - c + funding
    return row


def summary(sc, now_ms):
    """Per-notice observations and the frozen decision rule."""
    if sc.empty:
        return {"scored_notices": 0, "decision": f"pending (0 of {N_DECIDE} scored notices)"}
    g = sc.groupby("notice")
    obs = pd.DataFrame({"net": g.net.mean(), "net_2x": g.net_2x.mean(), "gross": g.gross.mean(),
                        "net1h_1x": g.net1h_1x.mean()})
    n = len(obs)
    x = obs.net.values
    t = float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 1 and x.std(ddof=1) > 0 else np.nan
    st = {"scored_notices": n, "scored_tickets": int(len(sc)), "mean_net_pct": float(x.mean() * 100), "t": t,
          "mean_net_2x_pct": float(obs.net_2x.mean() * 100), "mean_gross_pct": float(obs.gross.mean() * 100),
          "mean_net1h_1x_pct": float(obs.net1h_1x.mean() * 100), "hit": float((x > 0).mean()),
          "spread_flags": int(sc.spread_flag.astype(bool).sum()), "stopped": int(sc.stopped_trading.astype(bool).sum())}
    passed = bool(np.isfinite(t) and t >= 2 and obs.net_2x.mean() > 0)
    if n >= N_DECIDE:
        st["decision"] = "PASS (gate 1 forward)" if passed else "NULL"
    elif n >= N_FUTILE and x.mean() < 0:
        st["decision"] = "NULL (futility at 6)"
    elif now_ms >= DEADLINE:
        st["decision"] = ("PASS" if passed else "NULL") + f" (deadline, underpowered: {n} of {N_DECIDE})"
    else:
        st["decision"] = f"pending ({n} of {N_DECIDE} scored notices)"
    st["go_real"] = gate.go_real(x, entry_days=list(obs.index))     # reported, not gated
    return st


def tick(now_ms, *, contracts, last_price, spot_price, klines, funding, catalogs=CATALOGS, ticks=TICKS):
    J.mkdir(parents=True, exist_ok=True)
    tk = read("tickets.csv", TICKET_COLS)
    sk = read("skipped.csv", SKIP_COLS)
    done = set(zip(tk.notice.astype(int), tk.ticker)) | set(zip(sk.notice.astype(int), sk.ticker))
    new_t, new_s = [], []
    notices = tag_notices(catalogs)
    table = contracts() if any((int(r.id), x) not in done for r, ts in notices for x in ts) else None
    entry = (now_ms // H + 1) * H                         # first full hour after the ticket
    for r, ts in notices:
        for ticker in ts:
            if (int(r.id), ticker) in done:
                continue
            base = {"notice": int(r.id), "ticker": ticker, "noted_at": iso(now_ms)}
            done.add((int(r.id), ticker))
            if entry - int(r.release_ms) > MAX_LAG:
                new_s.append({**base, "reason": "missed", "detail": f"entry {iso(entry)} > release + 3 h"})
                continue
            c, mult = contract_for(ticker, table)
            if c is None:
                new_s.append({**base, "reason": "no_contract", "detail": ""})
                continue
            last = last_price(c)
            spot = spot_price(ticker + "USDT")
            ratio = last / (spot * mult) if last and spot else np.nan
            if np.isfinite(ratio) and not 1 / 3 <= ratio <= 3:
                new_s.append({**base, "reason": "mismatch", "detail": f"{c} ratio {ratio:.4g}"})
                continue
            taker = table.loc[table.symbol == c, "taker"]
            new_t.append({"ticket": f"T{int(r.id)}-{c}", "notice": int(r.id), "ticker": ticker, "contract": c,
                          "mult": mult, "title": r.title, "release_ms": int(r.release_ms),
                          "first_seen_utc": r.first_seen_utc, "frozen_at": iso(now_ms), "entry_ms": entry,
                          "exit_ms": entry + 24 * H, "exit1h_ms": entry + H, "last_at_freeze": last,
                          "spot_price": spot, "price_ratio": ratio,
                          "check": "verified" if np.isfinite(ratio) else "unverified",
                          "taker": float(taker.iloc[0]) if len(taker) else np.nan})
    append("tickets.csv", new_t, TICKET_COLS)
    append("skipped.csv", new_s, SKIP_COLS)
    tk = read("tickets.csv", TICKET_COLS)
    sc = read("scores.csv", SCORE_COLS)
    new_sc = []
    for _, t in tk[~tk.ticket.isin(sc.ticket)].iterrows():
        if now_ms < int(t["exit_ms"]) + H + 10 * 60_000:
            continue
        lo, hi = int(t["entry_ms"]) - H, int(t["exit_ms"]) + 2 * H
        row = score(t, klines(t["contract"], lo, hi), funding(t["contract"], lo, hi), ticks)
        if row is not None:
            row["scored_at"] = iso(now_ms)
            new_sc.append(row)
    append("scores.csv", new_sc, SCORE_COLS)
    sc = read("scores.csv", SCORE_COLS)
    st = summary(sc, now_ms)
    st.update(updated=iso(now_ms), tickets=int(len(tk)), open=int((~tk.ticket.isin(sc.ticket)).sum()),
              skipped=read("skipped.csv", SKIP_COLS).reason.value_counts().to_dict(),
              new_tickets=[t["ticket"] for t in new_t], tag_notices_seen=len(notices))
    (J / "status.json").write_text(json.dumps(st, indent=1, default=str))
    return st


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    now = int(time.time() * 1000)
    hour = pd.Timestamp(now, unit="ms", tz="UTC")
    rec = TICKS / hour.strftime("%Y-%m-%d") / f"{hour:%H}.parquet"

    def last_price(c):
        if rec.exists():
            df = pd.read_parquet(rec, columns=["symbol", "t_lastPrice"])
            r = df[df.symbol == c]
            if len(r) and r.t_lastPrice.iloc[0] > 0:
                return float(r.t_lastPrice.iloc[0])
        return float(mexc.get("ticker", {"symbol": c})["lastPrice"])

    def spot_price(sym):
        try:
            req = urllib.request.Request(SPOT_API.format(sym=sym), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return float(json.loads(r.read())["price"])
        except (OSError, ValueError, KeyError):
            return None

    st = tick(now, contracts=mexc.contracts, last_price=last_price, spot_price=spot_price,
              klines=lambda c, s, e: mexc.fetch_klines(c, s, e), funding=mexc.funding_history)
    log(f"montag_fwd: {st['tickets']} tickets ({len(st['new_tickets'])} new), {st['open']} open, "
        f"{st['scored_notices']} notices scored, skipped {st['skipped']}, {st['decision']}")


if __name__ == "__main__":
    main()
