"""carry_fwd (R220): the R191 funding carry rule forward on paper, entered one bar late, on Binance and on MEXC, as set
out in experiments/carry_fwd/PREREG.md. Reads R200's journal (eligibility and liquidity rank; never writes it);
appends to its own journal. Paper only: nothing here can place an order.

BIN:  Binance funding settlements, basis = Binance premium index close, spot leg on a Binance USDT spot pair.
MEXC: MEXC funding settlements, basis = MEXC last close / MEXC index close - 1, spot leg on a MEXC USDT spot pair.

usage: python scripts/forward_carry.py   (after scripts/forward_tick.py)
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import forward_tick as ft  # noqa: E402
from lab import carry, engine, events, gate, live, mexc, panel, prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "carry_fwd"
J = LANE / "journal"
ON_TIME = panel.ms("2026-10-20")
H = ft.H
LOOK, TH_IN, TH_OUT, SPOT = 72, 0.20, 0.10, 0.0010
DECIDE_DAYS = 90
TRADFI = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
# variant -> (cost multiple, spot cost, bars of delay); "1x" is the decided one
VARIANTS = {"1x": (1.0, SPOT, 1), "2x": (2.0, 2 * SPOT, 1), "3x": (3.0, 3 * SPOT, 1), "spot5": (1.0, 0.0005, 1),
            "r191_timing": (1.0, SPOT, 0)}
TICKET_COLUMNS = ["day", "book", "kind", "net", "funding", "basis", "cost", "avg_open",
                  *[f"net_{k}" for k in VARIANTS if k != "1x"], "n_elig", "n_elig_spot"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def read(name):
    p = J / name
    return pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame()


def journal_grid():
    """R200's eligibility and rank on a grid that starts LOOK hours before the forward start (the signal's warm-up)."""
    sig, ticks = ft.read("signals.csv"), ft.read("ticks.csv")
    if sig.empty or ticks.empty:
        raise SystemExit("R200 signals/ticks are empty; no carry tickets this run")
    last_closed = int(time.time() * 1000) // H * H - H
    t0, last = ft.FWD_START, min(int(ticks.t.max()), last_closed)
    sig = sig[(sig.t >= t0) & (sig.t <= last)]
    if sig.empty:
        raise SystemExit("No closed R200 signal hours; no carry tickets this run")
    syms = sorted(sig.symbol.unique())
    T = (last - t0) // H + 1
    tt = np.arange(t0 - LOOK * H, last + H, H)
    col = {s: i for i, s in enumerate(syms)}
    ri, ci = ((sig.t.values - tt[0]) // H).astype(int), sig.symbol.map(col).values
    elig = np.zeros((len(tt), len(syms)), bool)
    elig[ri, ci] = True
    rank = np.full(elig.shape, np.nan, np.float32)
    rank[ri, ci] = sig["rank"].values
    return {"syms": syms, "tt": tt, "T": T, "last": last, "elig": elig, "rank": rank}


def fetch(fn, keys):
    """An empty successful response can mean no settlement; a failed response must never become zero funding."""
    def one(k):
        try:
            return k, fn(k)
        except (live.LiveError, mexc.MexcError) as e:
            log("fetch failed", k, e)
            return k, None

    with ThreadPoolExecutor(4) as ex:
        got = list(ex.map(one, keys))
    failed = [k for k, v in got if v is None]
    if failed:
        raise SystemExit(f"Carry fetch failed for {failed}; no tickets this run")
    return dict(got)


def venue_binance(g):
    tt, syms = g["tt"], g["syms"]
    a, b = int(tt[0]), int(tt[-1]) + H
    spot = live.spot_usdt()
    pair = {s: carry.spot_pair([s[:-4]], spot) for s in syms}
    fr = fetch(lambda s: live.funding_history(s, a, b), syms)
    pm = fetch(lambda s: live.fetch_klines(s, a, b, path="fapi/v1/premiumIndexKlines"), syms)
    fund = place(live.grid(fr, tt, "rate"), list(fr), syms)
    basis = place(live.grid(pm, tt, "close"), list(pm), syms)
    return {"fund": fund, "basis": basis, "has": np.array([pair[s] is not None for s in syms]), "pair": pair,
            "elig": g["elig"]}


def venue_mexc(g):
    tt, syms = g["tt"], g["syms"]
    a, b = int(tt[0]), int(tt[-1]) + H
    table = mexc.contracts()
    mp = mexc.map_symbols(syms, table)
    for s in (TRADFI | live.tradfi()) & set(mp):    # R215's static and current TradFi exclusions
        mp[s] = None
    try:
        mexc.require_unique_mapping(mp)
    except mexc.MexcError as e:
        raise SystemExit(f"{e}; no carry tickets this run") from e
    spot = mexc.spot_usdt()
    pair = {s: carry.spot_pair([s[:-4], mp[s][:-5]], spot) if mp[s] else None for s in syms}
    mx = sorted({m for m in mp.values() if m})
    fr = fetch(lambda m: mexc.funding_history(m, a, b), mx)
    cl = fetch(lambda m: mexc.fetch_klines(m, a, b), mx)  # uncached: R215 is the one writer of the MEXC price cache
    ix = fetch(lambda m: mexc.klines_cached(m, a, b, kind="index_price"), mx)
    by = lambda d: place(live.grid(d, tt, "close" if d is not fr else "rate"), list(d), [mp[s] for s in syms])
    fund, close, index = by(fr), by(cl), by(ix)
    with np.errstate(divide="ignore", invalid="ignore"):
        basis = close / index - 1
    taker = [spot.get(pair[s]) for s in syms if pair[s]]
    return {"fund": fund, "basis": basis, "has": np.array([pair[s] is not None for s in syms]), "pair": pair,
            "elig": g["elig"] & np.isfinite(close), "mapped": int(sum(m is not None for m in mp.values())),
            "spot_taker_mean": float(np.nanmean(taker)) if taker else None}


def place(x, have, want):
    """Columns of x (named by `have`) reordered to `want`; a name missing from `have` (or None) gives a NaN column."""
    idx = {k: i for i, k in enumerate(have)}
    out = np.full((x.shape[0], len(want)), np.nan, np.float32)
    for j, k in enumerate(want):
        if k in idx:
            out[:, j] = x[:, idx[k]]
    return out


def book(g, v, cm, spot_cost, delay):
    """Hourly (net, funding, basis, cost, n_open) on the forward grid, scored rows only, and the symbols held last."""
    if np.isinf(v["fund"]).any():
        raise SystemExit("Non-finite funding rate; no carry tickets this run")
    apr = carry.trailing_apr(v["fund"], LOOK)
    elig = v["elig"]
    if delay:
        apr = np.vstack([np.full((delay, apr.shape[1]), np.nan), apr[:-delay]])
        elig = elig & np.vstack([np.zeros((delay, elig.shape[1]), bool), elig[:-delay]])
    rank = panel.ffill(g["rank"])
    cost = engine.cost_matrix(rank).astype(np.float64) * cm
    o = carry.run(apr, np.asarray(v["fund"], np.float64), np.asarray(v["basis"], np.float64), elig, v["has"], cost,
                  spot_cost, TH_IN, TH_OUT, LOOK, len(g["tt"]), require_complete=True)
    return o[: g["T"] - 1]                                 # the last row needs the next hour's basis: not scored yet


def day_tickets(g, name, v, out, done):
    """Build only complete 24-hour tickets, preserving the existing journal column order."""
    D = (g["T"] - 1) // 24
    day = {k: o[:D * 24].reshape(D, 24, 5) for k, o in out.items()}
    valid = np.logical_and.reduce([np.isfinite(x).all(axis=(1, 2)) for x in day.values()])
    daily = np.where(valid, day["1x"][..., 0].sum(1), np.nan)
    elig = v["elig"][LOOK:LOOK + D * 24].reshape(D, 24, -1)
    rows = []
    for d in range(D):
        ts = ft.FWD_START + d * 24 * H
        key = pd.Timestamp(ts, unit="ms", tz="UTC").strftime("%Y-%m-%d")
        if (key, name) in done:
            continue
        if not valid[d]:
            log("deferred incomplete carry day", name, key)
            continue
        x = day["1x"][d]
        rows.append({"day": key, "book": name, "kind": "ontime" if ts >= ON_TIME else "replay",
                     "net": float(x[:, 0].sum()), "funding": float(x[:, 1].sum()), "basis": float(x[:, 2].sum()),
                     "cost": float(x[:, 3].sum()), "avg_open": float(x[:, 4].mean()),
                     **{f"net_{k}": float(day[k][d][:, 0].sum()) for k in VARIANTS if k != "1x"},
                     "n_elig": int(elig[d].any(0).sum()),
                     "n_elig_spot": int((elig[d].any(0) & v["has"]).sum())})
    return rows, daily


def decision(tickets):
    """R220's frozen rule on the first 90 complete UTC on-time days, independent of later observations."""
    if tickets.empty:
        tickets = pd.DataFrame(columns=["day", "kind", "net", "avg_open"])
    if tickets.day.duplicated().any():
        raise ValueError("Duplicate carry day; refusing to decide")
    dates = pd.to_datetime(tickets.day, format="%Y-%m-%d", utc=True, errors="raise")
    if not dates.dt.strftime("%Y-%m-%d").equals(tickets.day):
        raise ValueError("Carry days must be canonical UTC dates")
    expected_kind = np.where(dates.astype("int64") // 1_000_000 >= ON_TIME, "ontime", "replay")
    if not np.array_equal(tickets.kind.values, expected_kind):
        raise ValueError("Carry ticket kind disagrees with frozen on-time cutoff")
    values = tickets[["net", "avg_open"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, 1] < 0).any():
        raise ValueError("Invalid carry net/position count; refusing to decide")
    expected = pd.date_range(pd.Timestamp(ON_TIME, unit="ms", tz="UTC"), periods=DECIDE_DAYS, freq="D")
    days = expected.strftime("%Y-%m-%d").tolist()
    first = tickets.set_index("day").reindex(days)
    missing = first.kind.isna()
    result = {"decision": "PENDING", "required_days": DECIDE_DAYS, "days": int((~missing).sum()),
              "missing_days": int(missing.sum()), "through_day": days[-1]}
    if missing.any():
        return result
    inv = first[first.avg_open > 0]
    total = float(first.net.sum())
    t = float(stats.newey_west_t(first.net.values, 10)[2])
    g = gate.go_real(inv.net.values) if len(inv) else None
    checks = {"total_positive": total > 0, "nw_t_at_least_2": bool(np.isfinite(t) and t >= 2),
              "go_real_invested": bool(g and g["pass"])}
    verdict = "INCONCLUSIVE" if len(inv) < 20 else "PASS" if all(checks.values()) else "FAIL"
    return {**result, "decision": verdict, "days_invested": int(len(inv)), "total": total,
            "t_nw": t if np.isfinite(t) else None, "go_real_invested": g, "checks": checks}


def held_now(g, v):
    """Symbols the 1x rule holds at the last scored hour, replayed with the same state machine on one column each."""
    apr = carry.trailing_apr(v["fund"], LOOK)
    r = len(g["tt"]) - 2
    lagged = np.vstack([np.full((1, apr.shape[1]), np.nan), apr[:-1]])
    out = []
    for j, s in enumerate(g["syms"]):
        if not v["has"][j]:
            continue
        o = carry.run(lagged[:, [j]], np.asarray(v["fund"][:, [j]], np.float64),
                      np.asarray(v["basis"][:, [j]], np.float64), v["elig"][:, [j]] &
                      np.vstack([[False], v["elig"][:-1, [j]]]), [True], np.zeros((len(g["tt"]), 1)), 0.0, TH_IN,
                      TH_OUT, LOOK, len(g["tt"]))
        if o[r - LOOK, 4] > 0:
            out.append({"symbol": s, "apr": float(apr[r, j])})
    with np.errstate(invalid="ignore"):
        mkt = float(np.nanmean(np.where(v["elig"][r], apr[r], np.nan)))
    top = sorted(((float(apr[r, j]), s) for j, s in enumerate(g["syms"]) if v["elig"][r, j] and np.isfinite(apr[r, j])),
                 reverse=True)[:5]
    return out, mkt, [{"symbol": s, "apr": a, "spot": bool(v["has"][g["syms"].index(s)])} for a, s in top]


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    g = journal_grid()
    D = (g["T"] - 1) // 24
    if D == 0:
        log("no full scored carry day yet")
        return
    venues = {"BIN": venue_binance(g), "MEXC": venue_mexc(g)}
    have = read("tickets.csv")
    if not have.empty and ("day" not in have or "book" not in have):
        raise SystemExit("Malformed carry tickets journal; no tickets this run")
    done = set(zip(have.day, have.book)) if not have.empty else set()
    rows, daily, coverage = [], {}, {}
    for name, v in venues.items():
        out = {k: book(g, v, *p) for k, p in VARIANTS.items()}
        new_rows, daily[name] = day_tickets(g, name, v, out, done)
        rows.extend(new_rows)
        coverage[name] = v
    J.mkdir(parents=True, exist_ok=True)
    if rows:
        new = pd.DataFrame(rows)
        new.to_csv(J / "tickets.csv", mode="a", header=have.empty, index=False)
        log(f"ticketed {len(new)} rows, days {new.day.min()}..{new.day.max()}")
    tk = read("tickets.csv") if (J / "tickets.csv").exists() else pd.DataFrame(columns=TICKET_COLUMNS)
    if tk.empty:
        tk = pd.DataFrame(columns=TICKET_COLUMNS)
    if tk.duplicated(["day", "book"]).any():
        raise SystemExit("Duplicate carry day/book journal rows; refusing to report")
    status = {"last_scored_hour": pd.Timestamp(int(g["tt"][-2]), unit="ms", tz="UTC").isoformat(),
              "days_ticketed": int(tk.day.nunique()), "decision_at_90_days": {}}
    for name, v in venues.items():
        n = tk[tk.book == name].sort_values("day")
        held, mkt, top = held_now(g, v)
        s = {"coverage": {"symbols": len(g["syms"]), "with_spot_pair": int(v["has"].sum()),
                          **({"mapped": v["mapped"], "spot_taker_mean": v["spot_taker_mean"]} if name == "MEXC" else {})},
             "held_now": held, "market_mean_apr_now": mkt, "top_apr_now": top}
        ontime = n[n.kind == "ontime"].sort_values("day")
        status["decision_at_90_days"][name] = decision(ontime)
        for kind in ("replay", "ontime"):
            x = n[n.kind == kind]
            if x.empty:
                continue
            inv = x[x.avg_open > 0]
            s[kind] = {"days": int(len(x)), "days_invested": int(len(inv)), "total": float(x.net.sum()),
                       **{f"total_{k}": float(x[f"net_{k}"].sum()) for k in VARIANTS if k != "1x"},
                       "funding": float(x.funding.sum()), "basis": float(x.basis.sum()), "cost": float(x.cost.sum()),
                       "avg_open": float(x.avg_open.mean()), **events.summary(x.net.values),
                       "go_real_invested": gate.go_real(inv.net.values) if len(inv) else None}
        status[name] = s
    if len(daily["BIN"]) >= 3 and np.std(daily["BIN"]) > 0 and np.std(daily["MEXC"]) > 0:
        status["corr_BIN_MEXC_daily"] = float(np.corrcoef(daily["BIN"], daily["MEXC"])[0, 1])
    (J / "status.json").write_text(json.dumps(status, indent=1, default=float))
    log(json.dumps({b: {k: {f: status[b][k][f] for f in ("days", "days_invested", "total", "total_2x")}
                        for k in ("replay", "ontime") if k in status[b]} for b in venues}))


if __name__ == "__main__":
    main()
