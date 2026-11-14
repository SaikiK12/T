"""unlocks_fwd (R266): the unlock short forward on MEXC paper, as set out in experiments/unlocks_fwd/PREREG.md.

Each tick: read the newest daily calendar snapshot (scripts/record_unlocks.py), apply R265's event rule, write a
ticket for every event whose entry E (00:00 UTC of D-6) is less than 24 h away and has none yet, then score the
tickets whose exit bar has opened. Journals (append-only): tickets.csv, skipped.csv, scores.csv. Derived each tick:
book_days.csv and status.json. Paper only: nothing here can place an order.

usage: python scripts/forward_unlocks.py
"""
import ast
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import unlock_events as ue  # noqa: E402
from lab import data, gate, mexc, panel, prereg  # noqa: E402

LANE = ROOT / "experiments" / "unlocks_fwd"
J = LANE / "journal"
SNAPS = data.ROOT / "recorders" / "unlocks"
TICKS = data.ROOT / "recorders" / "mexc_ticker"
H, DAY = 3_600_000, 86_400_000
START_MS = panel.ms("2026-10-21")          # events with E from here are the lane's population
MODEL = {"1x": 0.002, "2x": 0.004, "3x": 0.006}
SPREAD_FALLBACK = 0.0010                   # one leg, when the recorder has no bid/ask for that hour
WEIGHT = 0.10                              # book line: each open ticket at 10% of capital, 1x notional
N_DECIDE, N_FUTILE, DEADLINE = 120, 60, panel.ms("2027-12-31")
TICKET_COLS = ["ticket", "gecko_id", "ticker", "contract", "mult", "listed_binance", "day", "entry_ms", "exit_ms",
               "frac_max_supply", "tokens", "snapshot", "snapshot_sha256", "frozen_at", "last_at_freeze",
               "index_price", "price_ratio", "taker"]
SKIP_COLS = ["gecko_id", "ticker", "day", "reason", "detail", "snapshot", "noted_at"]
SCORE_COLS = ["ticket", "entry_price", "exit_price", "stopped_trading", "gross", "funding", "settlements", "taker",
              "spread_entry", "spread_exit", "spread_flag", "cost_measured", "net", "net_1x", "net_2x", "net_3x",
              "mae", "mfe", "liq_1x", "liq_2x", "liq_3x", "scored_at"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
iso = lambda ms: pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- events
def latest_snapshot(now_ms, snaps=SNAPS):
    day = pd.Timestamp(now_ms, unit="ms", tz="UTC").strftime("%Y-%m-%d")
    files = sorted(p for p in Path(snaps).glob("*.json.gz") if p.name[:10] <= day)
    return files[-1] if files else None


def _list(v):
    if isinstance(v, str):
        try:
            v = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return []
    return v or []


def snapshot_events(path):
    """Qualifying unlock days per token in one index snapshot (R265's rule)."""
    rows = json.loads(gzip.decompress(Path(path).read_bytes()))["data"]
    out = []
    for r in rows:
        gid = r.get("gecko_id")
        tp = _list(r.get("tokenPrice"))
        sym = (tp[0].get("symbol") or "").upper() if tp else ""
        try:
            ms = float(r.get("maxSupply"))
        except (TypeError, ValueError):
            ms = np.nan
        if not gid or not sym or sym in ue.EXCLUDE or not (np.isfinite(ms) and ms > 0):
            continue
        last = None
        for d, (amt, frac) in ue.cliff_days({"metadata": {"unlockEvents": _list(r.get("unlockEvents"))}}, ms).items():
            if frac < ue.MIN_FRAC or (last is not None and d - last < ue.SPACING_DAYS * DAY):
                continue
            last = d
            out.append({"gecko_id": gid, "ticker": sym, "day_ms": d, "tokens": amt, "frac_max_supply": frac,
                        "index_price": tp[0].get("price")})
    return out


def contract_for(ticker, table):
    """(contract, multiplier) for an open type-1 USDT perp on MEXC, else (None, None)."""
    open_ = table[(table.type == 1) & (table.state == 0)]
    by_base = {str(b).upper(): (s, b) for s, b in zip(open_.symbol, open_.base)}
    cands = [(ticker, 1), ("1000" + ticker, 1000), ("1000000" + ticker, 1_000_000)]
    if ticker in mexc.ALIAS:
        cands.append((mexc.ALIAS[ticker], 1))
    for base, m in cands:
        if base in by_base:
            return by_base[base][0], m
    return None, None


# ---------------------------------------------------------------- journals
def read(name, cols):
    p = J / name
    return pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame(columns=cols)


def append(name, rows, cols):
    if not rows:
        return
    p = J / name
    new = not p.exists() or not p.stat().st_size
    pd.DataFrame(rows, columns=cols).to_csv(p, mode="a", header=new, index=False)


# ---------------------------------------------------------------- ticket and score
def spread_at(ms, contract, ticks=TICKS):
    """Half the relative bid-ask spread in the recorder's file for the hour of ms, or None."""
    ts = pd.Timestamp(int(ms), unit="ms", tz="UTC")
    p = Path(ticks) / ts.strftime("%Y-%m-%d") / f"{ts:%H}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p, columns=["symbol", "t_bid1", "t_ask1"])
    r = df[df.symbol == contract]
    if r.empty or not (r.t_bid1.iloc[0] > 0 and r.t_ask1.iloc[0] > 0):
        return None
    b, a = float(r.t_bid1.iloc[0]), float(r.t_ask1.iloc[0])
    return (a - b) / (a + b)


def score(t, bars, fund, ticks=TICKS):
    """One scored row for ticket t from its hourly bars (t, open, high, low, close) and settled funding (t, rate)."""
    e1, x1 = int(t["entry_ms"]) + H, int(t["exit_ms"]) + H
    b = bars.sort_values("t")
    at_e = b[b.t == e1]
    if at_e.empty:
        return None
    entry = float(at_e.open.iloc[0])
    at_x = b[b.t == x1]
    stopped = at_x.empty
    exit_ = float(at_x.open.iloc[0]) if not stopped else float(b[b.t < x1].close.iloc[-1])
    held = b[(b.t >= e1) & (b.t < x1)]
    mae = float(held.high.max() / entry - 1) if len(held) else np.nan
    mfe = float(1 - held.low.min() / entry) if len(held) else np.nan
    f = fund[(fund.t > e1) & (fund.t <= x1)]
    funding = float(f.rate.sum())
    se, sx = spread_at(e1, t["contract"], ticks), spread_at(x1, t["contract"], ticks)
    flag = se is None or sx is None
    se = SPREAD_FALLBACK if se is None else se
    sx = SPREAD_FALLBACK if sx is None else sx
    taker = float(t["taker"]) if pd.notna(t["taker"]) else 0.0
    cost = 2 * taker + se + sx
    gross = -(exit_ / entry - 1)
    row = {"ticket": t["ticket"], "entry_price": entry, "exit_price": exit_, "stopped_trading": stopped,
           "gross": gross, "funding": funding, "settlements": int(len(f)), "taker": taker, "spread_entry": se,
           "spread_exit": sx, "spread_flag": flag, "cost_measured": cost, "net": gross - cost + funding}
    for k, c in MODEL.items():
        row[f"net_{k}"] = gross - c + funding
    for L in (1, 2, 3):
        row[f"liq_{L}x"] = bool(np.isfinite(mae) and mae >= 1 / L - 0.01)
    row.update(mae=mae, mfe=mfe)
    return row


def book_days(tickets, scores, bars_of):
    """Daily book return: each ticket at WEIGHT notional, short, marked at 00:00 UTC opens (daily-rebalanced)."""
    out = {}
    s = scores.set_index("ticket")
    for _, t in tickets.iterrows():
        if t["ticket"] not in s.index:
            continue
        sc = s.loc[t["ticket"]]
        b = bars_of(t).set_index("t")
        e1, x1 = int(t["entry_ms"]) + H, int(t["exit_ms"]) + H
        marks = [e1] + [m for m in range((e1 // DAY + 1) * DAY, x1, DAY)] + [x1]
        price = lambda m: float(b.open.get(m, np.nan)) if m in b.index else np.nan
        p = [float(sc.entry_price)] + [price(m) for m in marks[1:-1]] + [float(sc.exit_price)]
        for i in range(1, len(marks)):
            day = pd.Timestamp(marks[i] - 1, unit="ms", tz="UTC").strftime("%Y-%m-%d")
            r = -(p[i] / p[i - 1] - 1) if np.isfinite(p[i]) and np.isfinite(p[i - 1]) else 0.0
            out[day] = out.get(day, 0.0) + WEIGHT * r
        last = pd.Timestamp(x1 - 1, unit="ms", tz="UTC").strftime("%Y-%m-%d")
        out[last] = out.get(last, 0.0) + WEIGHT * (float(sc.funding) - float(sc.cost_measured))
    if not out:
        return pd.DataFrame(columns=["day", "ret", "equity", "drawdown"])
    df = pd.DataFrame(sorted(out.items()), columns=["day", "ret"])
    df["equity"] = 1 + df.ret.cumsum()
    df["drawdown"] = df.equity / df.equity.cummax() - 1
    return df


def cluster_t(x, groups):
    x = np.asarray(x, float)
    if len(x) < 2:
        return np.nan
    s = pd.Series(x - x.mean()).groupby(np.asarray(groups)).sum().values
    G = len(s)
    se = np.sqrt(G / (G - 1) * (s ** 2).sum()) / len(x) if G > 1 else 0
    return float(x.mean() / se) if se > 0 else np.nan


def summary(sc, tk, now_ms):
    m = sc.merge(tk, on="ticket")
    wk = pd.to_datetime(m["day"]).dt.isocalendar()
    groups = (wk.year * 100 + wk.week).values
    n = len(m)
    out = {"scored": n, "mean_net": float(m.net.mean()) if n else None, "t_net": cluster_t(m.net, groups),
           "mean_net_2x": float(m.net_2x.mean()) if n else None, "mean_gross": float(m.gross.mean()) if n else None,
           "mean_funding": float(m.funding.mean()) if n else None, "hit": float((m.net > 0).mean()) if n else None,
           "liq_flags": {L: int(m[f"liq_{L}"].astype(bool).sum()) for L in ("1x", "2x", "3x")},
           "binance_listed": {"n": int(m.listed_binance.astype(bool).sum()),
                              "mean_net": float(m.net[m.listed_binance.astype(bool)].mean()) if n else None},
           "mexc_only": {"n": int((~m.listed_binance.astype(bool)).sum()),
                         "mean_net": float(m.net[~m.listed_binance.astype(bool)].mean()) if n else None},
           "go_real": gate.go_real(m.net.values, entry_days=list(m.entry_ms)) if n else None}
    f = m.frac_max_supply
    out["dose"] = {k: {"n": int(v.sum()), "mean_net": float(m.net[v].mean()) if v.any() else None}
                   for k, v in (("1-2%", f < 0.02), ("2-5%", (f >= 0.02) & (f < 0.05)), (">=5%", f >= 0.05))}
    if n >= N_DECIDE or (now_ms >= DEADLINE and n):
        ok = out["t_net"] is not None and out["t_net"] >= 2 and out["mean_net_2x"] > 0
        out["decision"] = ("PASS" if ok else "NULL") + ("" if n >= N_DECIDE else " (underpowered)")
    elif n >= N_FUTILE and out["mean_net"] < 0 and (out["t_net"] or 0) <= -1:
        out["decision"] = "NULL (futility at 60)"
    else:
        out["decision"] = f"pending ({n} of {N_DECIDE} scored)"
    return out


# ---------------------------------------------------------------- tick
def tick(now_ms, *, contracts, last_price, klines, funding, binance_bases, snaps=SNAPS, ticks=TICKS):
    J.mkdir(parents=True, exist_ok=True)
    tk = read("tickets.csv", TICKET_COLS)
    sk = read("skipped.csv", SKIP_COLS)
    done = set(zip(tk.gecko_id, tk.day)) | set(zip(sk.gecko_id, sk.day))
    snap = latest_snapshot(now_ms, snaps)
    new_t, new_s = [], []
    if snap is not None:
        sha = hashlib.sha256(snap.read_bytes()).hexdigest()
        table = contracts()
        used = set(zip(tk.contract, tk.day))
        for ev in snapshot_events(snap):
            day = pd.Timestamp(ev["day_ms"], unit="ms", tz="UTC").strftime("%Y-%m-%d")
            E = ev["day_ms"] - 6 * DAY
            if E < START_MS or (ev["gecko_id"], day) in done:
                continue
            base = {"gecko_id": ev["gecko_id"], "ticker": ev["ticker"], "day": day, "snapshot": snap.name,
                    "noted_at": iso(now_ms)}
            if now_ms >= E + H:
                new_s.append({**base, "reason": "missed", "detail": f"window closed at {iso(E + H)}"})
                done.add((ev["gecko_id"], day))
                continue
            if now_ms < E - DAY:
                continue
            c, mult = contract_for(ev["ticker"], table)
            if c is None:
                new_s.append({**base, "reason": "no_contract", "detail": ""})
                done.add((ev["gecko_id"], day))
                continue
            if (c, day) in used:
                new_s.append({**base, "reason": "duplicate_contract", "detail": c})
                done.add((ev["gecko_id"], day))
                continue
            last = last_price(c)
            ratio = last / (ev["index_price"] * mult) if last and ev["index_price"] else np.nan
            if not (np.isfinite(ratio) and 1 / 3 <= ratio <= 3):
                new_s.append({**base, "reason": "mismatch", "detail": f"{c} ratio {ratio:.4g}"})
                done.add((ev["gecko_id"], day))
                continue
            taker = table.loc[table.symbol == c, "taker"]
            new_t.append({"ticket": f"U{ev['day_ms'] // DAY}-{c}", "gecko_id": ev["gecko_id"], "ticker": ev["ticker"],
                          "contract": c, "mult": mult, "listed_binance": ev["ticker"] in binance_bases, "day": day,
                          "entry_ms": E, "exit_ms": ev["day_ms"] + DAY, "frac_max_supply": ev["frac_max_supply"],
                          "tokens": ev["tokens"], "snapshot": snap.name, "snapshot_sha256": sha,
                          "frozen_at": iso(now_ms), "last_at_freeze": last, "index_price": ev["index_price"],
                          "price_ratio": ratio, "taker": float(taker.iloc[0]) if len(taker) else np.nan})
            used.add((c, day))
            done.add((ev["gecko_id"], day))
    append("tickets.csv", new_t, TICKET_COLS)
    append("skipped.csv", new_s, SKIP_COLS)
    tk = read("tickets.csv", TICKET_COLS)
    sc = read("scores.csv", SCORE_COLS)
    cache = {}

    def bars_of(t):
        if t["ticket"] not in cache:
            cache[t["ticket"]] = klines(t["contract"], int(t["entry_ms"]), int(t["exit_ms"]) + 2 * H)
        return cache[t["ticket"]]

    new_sc = []
    for _, t in tk[~tk.ticket.isin(sc.ticket)].iterrows():
        if now_ms < int(t["exit_ms"]) + H + 10 * 60_000:
            continue
        row = score(t, bars_of(t), funding(t["contract"], int(t["entry_ms"]), int(t["exit_ms"]) + 2 * H), ticks)
        if row is not None:
            row["scored_at"] = iso(now_ms)
            new_sc.append(row)
    append("scores.csv", new_sc, SCORE_COLS)
    sc = read("scores.csv", SCORE_COLS)
    book = book_days(tk, sc, bars_of)
    book.to_csv(J / "book_days.csv", index=False)
    st = summary(sc, tk, now_ms)
    st.update(updated=iso(now_ms), snapshot=snap.name if snap else None, tickets=int(len(tk)),
              open=int((~tk.ticket.isin(sc.ticket)).sum()), skipped=read("skipped.csv", SKIP_COLS).reason.value_counts().to_dict(),
              new_tickets=[t["ticket"] for t in new_t], book_equity=float(book.equity.iloc[-1]) if len(book) else 1.0,
              book_max_drawdown=float(book.drawdown.min()) if len(book) else 0.0,
              next_entries=sorted({iso(e["day_ms"] - 6 * DAY) + " " + e["ticker"]
                                   for e in (snapshot_events(snap) if snap else [])
                                   if now_ms <= e["day_ms"] - 6 * DAY < now_ms + 7 * DAY})[:20])
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

    bases = {p.stem[:-4] for p in (data.ROOT / "klines_1h").glob("*USDT.parquet")}
    bases |= {b[len(x):] for b in list(bases) for x in mexc.PREFIXES if b.startswith(x)}
    st = tick(now, contracts=mexc.contracts, last_price=last_price,
              klines=lambda c, s, e: mexc.fetch_klines(c, s, e), funding=mexc.funding_history, binance_bases=bases)
    log(f"unlocks_fwd: {st['tickets']} tickets ({len(st['new_tickets'])} new), {st['open']} open, "
        f"{st['scored']} scored, skipped {st['skipped']}, {st['decision']}")


if __name__ == "__main__":
    main()
