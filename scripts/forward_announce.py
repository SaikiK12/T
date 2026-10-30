"""R272 announce_fwd: R271's two candidates forward on MEXC paper (experiments/announce_fwd/PREREG.md).

Books (frozen):
- FF: a Binance notice that changes one perp's funding settlement frequency (R271 type fund_freq) -> long the MEXC perp
  for 1 h (logged: 24 h).
- PL: a Binance pre-listing notice, Launchpool / Launchpad / HODLer Airdrops / Megadrop (R271 type prelist) -> short the
  MEXC perp for 168 h (logged: 24 h and 72 h).

Titles are classified by scripts/announce_events.py (frozen with R271). Every notice first seen since the freeze gets
one ticket per ticker with an open MEXC perp, written before its entry bar opens: entry is the open of the first full
hour after the ticket, at most 3 h after the release. Tickets are scored once the last horizon's bar has closed.
Idempotent; journals in experiments/announce_fwd/journal/ are append-only, status.json is derived. It runs from
scripts/notice_loop.sh every 5 minutes (right after the notice recorder) and from scripts/forward_all.sh hourly.

usage: python scripts/forward_announce.py
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
import announce_events  # noqa: E402
from forward_delist import H, MAX_LAG, MODEL, SPOT_API, SPREAD_FALLBACK, bar_open, iso  # noqa: E402
from forward_unlocks import contract_for, spread_at, TICKS  # noqa: E402

LANE = ROOT / "experiments" / "announce_fwd"
J = LANE / "journal"
CATALOGS = [data.ROOT / "recorders" / "notices" / f"binance_{c}.csv" for c in ("news", "listing", "delisting")]
FIRST_SEEN_FROM = "2026-10-20T19:00:00Z"
# book: (R271 type, side: +1 long / -1 short, primary horizon h, logged horizons h)
BOOKS = {"FF": ("fund_freq", +1, 1, (24,)), "PL": ("prelist", -1, 168, (24, 72))}
LOGGED = (24, 72)
N_DECIDE, N_FUTILE, T_PASS, DEADLINE = 12, 6, 2.2, pd.Timestamp("2028-06-30", tz="UTC").value // 10**6
TICKET_COLS = ["ticket", "book", "notice", "ticker", "contract", "mult", "title", "release_ms", "first_seen_utc",
               "frozen_at", "entry_ms", "exit_ms", "last_at_freeze", "funding_rate_at_freeze", "spot_price",
               "price_ratio", "check", "taker"]
SKIP_COLS = ["book", "notice", "ticker", "reason", "detail", "noted_at"]
SCORE_COLS = ["ticket", "book", "notice", "entry_price", "exit_price", "stopped_trading", "gross", "funding",
              "settlements", "taker", "spread_entry", "spread_exit", "spread_flag", "cost_measured", "net", "net_1x",
              "net_2x", "net_3x"] + [f"{k}_{h}h" for h in LOGGED for k in ("gross", "net_1x")] + ["mae", "scored_at"]
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


def notices(catalogs):
    """(book, notice row, tickers) for the books' notices first seen since the freeze, by release time."""
    parts = [pd.read_csv(p) for p in catalogs if Path(p).exists() and Path(p).stat().st_size]
    if not parts:
        return []
    d = pd.concat(parts).drop_duplicates("id").sort_values(["release_ms", "id"])
    d = d[pd.to_datetime(d.first_seen_utc, utc=True) >= pd.Timestamp(FIRST_SEEN_FROM)]
    kinds = {v[0]: k for k, v in BOOKS.items()}
    out = []
    for r in d.itertuples():
        for kind, ticks in announce_events.parse(r.title):
            if kind in kinds:
                out.append((kinds[kind], r, ticks))
    return out


def horizons(book):
    _, _, h, logged = BOOKS[book]
    return h, logged


def score(t, bars, fund, ticks=TICKS):
    """One scored row for ticket t from its MEXC hourly bars (t, open, high, low, close) and settled funding."""
    side = BOOKS[t["book"]][1]
    h, logged = horizons(t["book"])
    e = int(t["entry_ms"])
    b = bars.sort_values("t")
    entry = bar_open(b, e)
    if entry is None:
        return None

    def exit_at(ms):
        p = bar_open(b, ms)
        return (p, False) if p is not None else (float(b[b.t < ms].close.iloc[-1]), True)

    px, stopped = exit_at(e + h * H)
    x = e + h * H
    f = fund[(fund.t > e) & (fund.t <= x)]
    se, sx = spread_at(e, t["contract"], ticks), spread_at(x, t["contract"], ticks)
    flag = se is None or sx is None
    se = SPREAD_FALLBACK if se is None else se
    sx = SPREAD_FALLBACK if sx is None else sx
    taker = float(t["taker"]) if pd.notna(t["taker"]) else 0.0
    cost = 2 * taker + se + sx
    gross = side * (px / entry - 1)
    funding = -side * float(f.rate.sum())                  # the short receives a positive rate, the long pays it
    hold = b[(b.t >= e) & (b.t < x)]
    mae = (hold.high.max() / entry - 1) if side < 0 else (1 - hold.low.min() / entry)
    row = {"ticket": t["ticket"], "book": t["book"], "notice": int(t["notice"]), "entry_price": entry,
           "exit_price": px, "stopped_trading": stopped, "gross": gross, "funding": funding, "settlements": int(len(f)),
           "taker": taker, "spread_entry": se, "spread_exit": sx, "spread_flag": flag, "cost_measured": cost,
           "net": gross - cost + funding, "mae": float(mae)}
    for k, c in MODEL.items():
        row[f"net_{k}"] = gross - c + funding
    for lh in LOGGED:
        if lh in logged:
            p, _ = exit_at(e + lh * H)
            g = side * (p / entry - 1)
            fl = -side * float(fund[(fund.t > e) & (fund.t <= e + lh * H)].rate.sum())
            row[f"gross_{lh}h"], row[f"net_1x_{lh}h"] = g, g - MODEL["1x"] + fl
    return row


def book_summary(sc, now_ms):
    """Per-notice observations of one book and its frozen decision rule."""
    if sc.empty:
        return {"scored_notices": 0, "decision": f"pending (0 of {N_DECIDE} scored notices)"}
    g = sc.groupby("notice")
    obs = pd.DataFrame({"net": g.net.mean(), "net_2x": g.net_2x.mean(), "gross": g.gross.mean()})
    n = len(obs)
    x = obs.net.values
    t = float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if n > 1 and x.std(ddof=1) > 0 else np.nan
    st = {"scored_notices": n, "scored_tickets": int(len(sc)), "mean_net_pct": float(x.mean() * 100), "t": t,
          "mean_net_2x_pct": float(obs.net_2x.mean() * 100), "mean_gross_pct": float(obs.gross.mean() * 100),
          "hit": float((x > 0).mean()), "spread_flags": int(sc.spread_flag.astype(bool).sum()),
          "stopped": int(sc.stopped_trading.astype(bool).sum())}
    passed = bool(np.isfinite(t) and t >= T_PASS and obs.net_2x.mean() > 0)
    if n >= N_DECIDE:
        st["decision"] = "PASS (gate 1 forward)" if passed else "NULL"
    elif n >= N_FUTILE and x.mean() < 0:
        st["decision"] = f"NULL (futility at {N_FUTILE})"
    elif now_ms >= DEADLINE:
        st["decision"] = ("PASS" if passed else "NULL") + f" (deadline, underpowered: {n} of {N_DECIDE})"
    else:
        st["decision"] = f"pending ({n} of {N_DECIDE} scored notices)"
    st["go_real"] = gate.go_real(x, entry_days=list(obs.index))     # reported, not gated
    return st


def tick(now_ms, *, contracts, quote, spot_price, klines, funding, catalogs=CATALOGS, ticks=TICKS):
    J.mkdir(parents=True, exist_ok=True)
    tk = read("tickets.csv", TICKET_COLS)
    sk = read("skipped.csv", SKIP_COLS)
    done = set(zip(tk.book, tk.notice.astype(int), tk.ticker)) | set(zip(sk.book, sk.notice.astype(int), sk.ticker))
    new_t, new_s = [], []
    found = notices(catalogs)
    todo = [(b, r, x) for b, r, ts in found for x in ts if (b, int(r.id), x) not in done]
    table = contracts() if todo else None
    entry = (now_ms // H + 1) * H                         # first full hour after the ticket
    for book, r, ticker in todo:
        if (book, int(r.id), ticker) in done:
            continue
        done.add((book, int(r.id), ticker))
        base = {"book": book, "notice": int(r.id), "ticker": ticker, "noted_at": iso(now_ms)}
        if entry - int(r.release_ms) > MAX_LAG:
            new_s.append({**base, "reason": "missed", "detail": f"entry {iso(entry)} > release + 3 h"})
            continue
        c, mult = contract_for(ticker, table)
        if c is None:
            new_s.append({**base, "reason": "no_contract", "detail": ""})
            continue
        q = quote(c) or {}
        last = q.get("last")
        spot = spot_price(ticker + "USDT")
        ratio = last / (spot * mult) if last and spot else np.nan
        if np.isfinite(ratio) and not 1 / 3 <= ratio <= 3:
            new_s.append({**base, "reason": "mismatch", "detail": f"{c} ratio {ratio:.4g}"})
            continue
        taker = table.loc[table.symbol == c, "taker"]
        h, _ = horizons(book)
        new_t.append({"ticket": f"{book}{int(r.id)}-{c}", "book": book, "notice": int(r.id), "ticker": ticker,
                      "contract": c, "mult": mult, "title": r.title, "release_ms": int(r.release_ms),
                      "first_seen_utc": r.first_seen_utc, "frozen_at": iso(now_ms), "entry_ms": entry,
                      "exit_ms": entry + h * H, "last_at_freeze": last, "funding_rate_at_freeze": q.get("funding"),
                      "spot_price": spot, "price_ratio": ratio,
                      "check": "verified" if np.isfinite(ratio) else "unverified",
                      "taker": float(taker.iloc[0]) if len(taker) else np.nan})
    append("tickets.csv", new_t, TICKET_COLS)
    append("skipped.csv", new_s, SKIP_COLS)
    tk = read("tickets.csv", TICKET_COLS)
    sc = read("scores.csv", SCORE_COLS)
    new_sc = []
    for _, t in tk[~tk.ticket.isin(sc.ticket)].iterrows():
        h, logged = horizons(t["book"])
        last_ms = int(t["entry_ms"]) + max((h,) + logged) * H
        if now_ms < last_ms + H + 10 * 60_000:
            continue
        lo, hi = int(t["entry_ms"]) - H, last_ms + 2 * H
        row = score(t, klines(t["contract"], lo, hi), funding(t["contract"], lo, hi), ticks)
        if row is not None:
            row["scored_at"] = iso(now_ms)
            new_sc.append(row)
    append("scores.csv", new_sc, SCORE_COLS)
    sc = read("scores.csv", SCORE_COLS)
    books = {b: book_summary(sc[sc.book == b], now_ms) for b in BOOKS}
    st = {"books": books, "scored_notices": sum(v["scored_notices"] for v in books.values()),
          "decision": "; ".join(f"{b} {v['decision']}" for b, v in books.items()), "updated": iso(now_ms),
          "tickets": int(len(tk)), "open": int((~tk.ticket.isin(sc.ticket)).sum()),
          "skipped": read("skipped.csv", SKIP_COLS).reason.value_counts().to_dict(),
          "new_tickets": [t["ticket"] for t in new_t], "notices_seen": len(found)}
    (J / "status.json").write_text(json.dumps(st, indent=1, default=str))
    return st


def main():
    prereg.verify(LANE / "PREREG.md")
    now = int(time.time() * 1000)

    def quote(c):
        try:
            d = mexc.get("ticker", {"symbol": c})
            return {"last": float(d["lastPrice"]), "funding": float(d.get("fundingRate", np.nan))}
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def spot_price(sym):
        try:
            req = urllib.request.Request(SPOT_API.format(sym=sym), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return float(json.loads(r.read())["price"])
        except (OSError, ValueError, KeyError):
            return None

    st = tick(now, contracts=lambda: mexc.contracts(refresh=True), quote=quote, spot_price=spot_price,
              klines=lambda c, s, e: mexc.fetch_klines(c, s, e), funding=mexc.funding_history)
    if st["new_tickets"] or "--verbose" in sys.argv or time.gmtime().tm_min < 10:
        log(f"announce_fwd: {st['tickets']} tickets ({len(st['new_tickets'])} new), {st['open']} open, "
            f"skipped {st['skipped']}, {st['decision']}")


if __name__ == "__main__":
    main()
