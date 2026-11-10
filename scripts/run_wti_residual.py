"""R434 wti_residual_v1 (M443): cross-venue residual on the 24/7 commodity perps, CME open versus closed.

When one venue's mid departs from the median of the other venues' mids by more than a multiple of that venue's own
round-trip cost (relative to the residual's own trailing 30-minute median, which absorbs contract-month and index
offsets), does it converge, and does a taker on the deviating venue earn it? Gate 0, files only, no orders.

Clock: every quote is placed on this container's local receive clock (`t`, microseconds): a decision uses only what
this machine had received. Decisions are taken on a 1-second grid; the order reaches the venue L seconds later (1.0 s,
plus 0.3 s for a Lighter Standard taker) and fills at the displayed touch as of that instant; the exit is a taker at
the displayed touch H seconds later. The spread of both fills is inside the gross; the fee is charged per side.

Venues per instrument (data/commodity_perps and data/lighter_trades, recorded 2026-10-28..2026-11-06):
  WTI    Lighter WTI, Hyperliquid xyz:CL, Kraken PF_WTIOILUSD, Binance CLUSDT
  BRENT  Lighter BRENTOIL, Hyperliquid xyz:BRENTOIL, Kraken PF_BRENTOILUSD, Binance BZUSDT
  NATGAS Lighter NATGAS, Hyperliquid xyz:NATGAS, Kraken PF_NATGASUSD, Binance NATGASUSDT
  GOLD   Hyperliquid xyz:GOLD, Kraken PF_XAUUSD, Binance XAUUSDT

usage: python scripts/run_wti_residual.py --manifest   write the lane's data manifest (paths, sizes, sha256); no prices
       python scripts/run_wti_residual.py --plumbing   coverage, spreads and trigger counts; reads no price after a trigger
       python scripts/run_wti_residual.py              the frozen run (verifies the PREREG, its inputs and the manifest)
"""
import argparse
import hashlib
import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "wti_residual_v1"
DATA = ROOT / "data"
MANIFEST = LANE / "data_manifest.json"

VENUES = ("lighter", "hl", "kraken", "binance")
INSTRUMENTS = {
    "WTI": {"lighter": "lighter_trades/quote/WTI", "hl": "commodity_perps/hlbbo/CL",
            "kraken": "commodity_perps/krtick/PF_WTIOILUSD", "binance": "commodity_perps/bnbook/CLUSDT"},
    "BRENT": {"lighter": "lighter_trades/quote/BRENTOIL", "hl": "commodity_perps/hlbbo/BRENTOIL",
              "kraken": "commodity_perps/krtick/PF_BRENTOILUSD", "binance": "commodity_perps/bnbook/BZUSDT"},
    "NATGAS": {"lighter": "lighter_trades/quote/NATGAS", "hl": "commodity_perps/hlbbo/NATGAS",
               "kraken": "commodity_perps/krtick/PF_NATGASUSD", "binance": "commodity_perps/bnbook/NATGASUSDT"},
    "GOLD": {"hl": "commodity_perps/hlbbo/GOLD", "kraken": "commodity_perps/krtick/PF_XAUUSD",
             "binance": "commodity_perps/bnbook/XAUUSDT"},
}
SESSIONS = {"lighter": ("lighter_trades/sessions.csv", None), "hl": ("commodity_perps/sessions.csv", "hl"),
            "kraken": ("commodity_perps/sessions.csv", "kraken"), "binance": ("commodity_perps/sessions.csv", "bn_public")}
FEE_BP = {"lighter": 0.0, "hl": 9.0, "kraken": 5.0, "binance": 5.0}     # taker fee per side, bp of notional
DELAY_S = {"lighter": 1.3, "hl": 1.0, "kraken": 1.0, "binance": 1.0}  # decision to fill, seconds
WARMUP_S = 60                 # a venue counts only from 60 s after its feed (re)connected
BASE_WINDOW_S = 1800          # trailing window of the residual's own median (offsets, contract months, index rolls)
BASE_MIN_S = 900              # valid seconds required inside that window
MIN_OTHERS = 2                # the consensus needs at least two other venues
K_THETA = (2.0, 3.0)          # trigger when |deviation| >= k x the venue's round-trip cost
THETA_FLOOR_BP = 4.0          # and never below 4 bp
HOLDS_S = (10, 60, 300)
STRATA = ("open", "closed")
SCOPES = {ins: tuple(v) + ("pooled",) for ins, v in INSTRUMENTS.items()}
PRIMARY = dict(instrument="WTI", scope="pooled", k=2.0, hold=60, stratum="open")
COST_MULTS = (1, 2, 3)
NOTIONAL = 5000.0             # USD, thin-touch diagnostic only
BOOT, SEED = 10_000, 434
MIN_TRADES, MIN_BLOCKS = 30, 4
TRIALS = sum(len(s) for s in SCOPES.values()) * len(K_THETA) * len(HOLDS_S) * len(STRATA)   # 228
CHICAGO = ZoneInfo("America/Chicago")
US = 1_000_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------------------------------------- inputs, manifest
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_files(root=DATA):
    """Every file the run reads, as paths relative to the data root, sorted."""
    files = set()
    for venues in INSTRUMENTS.values():
        for rel in venues.values():
            files.update(str(p.relative_to(root)) for p in (root / rel).glob("*/*.parquet"))
    files.update(rel for rel, _ in SESSIONS.values())
    return sorted(files)


def write_manifest(root=DATA, path=MANIFEST):
    rows = [{"path": rel, "bytes": (root / rel).stat().st_size, "sha256": sha256(root / rel)} for rel in data_files(root)]
    Path(path).write_text(json.dumps({"root": "data", "files": rows}, indent=0) + "\n")
    return len(rows)


def check_manifest(root=DATA, path=MANIFEST):
    """The data on disk must be exactly the manifest: same file set, sizes and hashes."""
    want = {r["path"]: r for r in json.loads(Path(path).read_text())["files"]}
    have = set(data_files(root))
    if have != set(want):
        raise prereg.PreregError(f"data file set differs from the manifest: {len(have ^ set(want))} files")
    for rel, r in want.items():
        if (root / rel).stat().st_size != r["bytes"] or sha256(root / rel) != r["sha256"]:
            raise prereg.PreregError(f"{rel} differs from the manifest")
    return len(want)


# ------------------------------------------------------------------------------------------------------------ loading
def load_quotes(root, rel):
    """Best quote rows of one venue and instrument in local receive order: t (us), bid, ask, bq, aq."""
    files = sorted((root / rel).glob("*/*.parquet"))
    cols = ["t", "bid", "ask", "bq", "aq"]
    parts = []
    for f in files:
        d = pd.read_parquet(f)
        if "suspended" in d:
            d.loc[d["suspended"] != 0, ["bid", "ask"]] = np.nan
        parts.append(d[cols])
    d = pd.concat(parts, ignore_index=True).sort_values("t", kind="stable") if parts else pd.DataFrame(columns=cols)
    return {c: d[c].to_numpy(np.int64 if c == "t" else float) for c in cols}


def load_sessions(root, venue):
    """Merged connected intervals of one venue's feed, in UTC seconds."""
    rel, name = SESSIONS[venue]
    s = pd.read_csv(root / rel)
    if name is not None:
        s = s[s.venue == name]
    sec = lambda c: ((pd.to_datetime(c, utc=True) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)).to_numpy(
        np.int64)                                     # resolution-proof (pandas 3 parses to microseconds)
    a, b = sec(s.start_utc), sec(s.end_utc)
    order = np.argsort(a)
    out = []
    for x, y in zip(a[order], b[order]):
        if out and x <= out[-1][1]:
            out[-1][1] = max(out[-1][1], y)
        else:
            out.append([x, y])
    arr = np.array(out, np.int64).reshape(-1, 2)
    return arr[:, 0], arr[:, 1]


def session_of(starts, ends, s):
    """Index of the merged session containing each time s (seconds, may be fractional), or -1."""
    s = np.asarray(s, float)
    i = np.searchsorted(starts, s, side="right") - 1
    ok = (i >= 0) & (s <= ends[np.clip(i, 0, None)])
    return np.where(ok, i, -1)


def asof(q, t_us):
    """Index of the last quote row received at or before each t_us, or -1."""
    return np.searchsorted(q["t"], np.asarray(t_us, np.int64), side="right") - 1


def quote_at(q, starts, ends, t_s, warm=0):
    """bid, ask, bq, aq at local times t_s (seconds) where the venue is connected (warm seconds after it connected) and
    has sent a quote since it connected; NaN elsewhere."""
    t_s = np.asarray(t_s, float)
    nan = np.full(len(t_s), np.nan)
    if len(q["t"]) == 0 or len(starts) == 0:
        return nan, nan, nan, nan
    k = session_of(starts, ends, t_s)
    t_us = np.round(t_s * US).astype(np.int64)
    j = asof(q, t_us)
    ok = (k >= 0) & (j >= 0)
    kk, jj = np.clip(k, 0, None), np.clip(j, 0, None)
    ok &= t_s >= starts[kk] + warm
    ok &= q["t"][jj] >= starts[kk] * US
    bid, ask = q["bid"][jj], q["ask"][jj]
    ok &= np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask > bid)
    return (np.where(ok, bid, nan), np.where(ok, ask, nan), np.where(ok, q["bq"][jj], nan),
            np.where(ok, q["aq"][jj], nan))


# ------------------------------------------------------------------------------------------------------- the clock
def cme_closed(t_s):
    """True while CME Globex energy and metals are closed: the daily 16:00-17:00 Chicago break Monday to Thursday, and
    Friday 16:00 to Sunday 17:00 Chicago."""
    out = np.zeros(len(t_s), bool)
    for i, s in enumerate(np.asarray(t_s, float)):
        d = datetime.fromtimestamp(float(s), tz=timezone.utc).astimezone(CHICAGO)
        wd, h = d.weekday(), d.hour
        out[i] = (wd == 5) or (wd == 6 and h < 17) or (wd == 4 and h >= 16) or (wd <= 3 and h == 16)
    return out


# --------------------------------------------------------------------------------------------------------- signals
def build(root, ins):
    """Per venue on the 1-second grid: log mid, spread (bp), residual against the others' median, its trailing median
    and the deviation. Returns the grid, per-venue arrays, quotes and sessions."""
    venues = tuple(INSTRUMENTS[ins])
    Q = {v: load_quotes(root, INSTRUMENTS[ins][v]) for v in venues}
    S = {v: load_sessions(root, v) for v in venues}
    lo = min(int(S[v][0].min()) for v in venues if len(S[v][0]))
    hi = max(int(S[v][1].max()) for v in venues if len(S[v][1]))
    grid = np.arange(lo, hi + 1, dtype=np.int64)
    lm = np.full((len(venues), len(grid)), np.nan)
    spr = np.full_like(lm, np.nan)
    for i, v in enumerate(venues):
        bid, ask, _, _ = quote_at(Q[v], *S[v], grid, warm=WARMUP_S)
        lm[i] = np.log((bid + ask) / 2)
        spr[i] = 1e4 * np.log(ask / bid)
    keep = np.isfinite(lm).sum(0) >= MIN_OTHERS + 1
    grid, lm, spr = grid[keep], lm[:, keep], spr[:, keep]
    out = {}
    for i, v in enumerate(venues):
        others = np.delete(lm, i, axis=0)
        n_oth = np.isfinite(others).sum(0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(np.where(n_oth >= MIN_OTHERS, others, np.nan), axis=0)
        e = 1e4 * (lm[i] - med)
        e = np.where((n_oth >= MIN_OTHERS) & np.isfinite(lm[i]), e, np.nan)
        base = baseline(grid, e)
        out[v] = dict(e=e, base=base, d=e - base, spread=spr[i], med=med)
    return grid, out, Q, S, venues


def baseline(grid, e):
    """Median of the residual over the valid seconds of [s - 1800, s), NaN with fewer than 900 of them."""
    ok = np.isfinite(e)
    if not ok.any():
        return np.full(len(e), np.nan)
    ser = pd.Series(e[ok], index=pd.to_datetime(grid[ok], unit="s"))
    b = ser.rolling(f"{BASE_WINDOW_S}s", closed="left", min_periods=BASE_MIN_S).median()
    out = np.full(len(e), np.nan)
    out[ok] = b.to_numpy()
    return out


def triggers(sig, v, k):
    """Grid indices where venue v's deviation reaches k x its round-trip cost (and the 4 bp floor)."""
    cost = sig[v]["spread"] + 2 * FEE_BP[v]
    theta = np.maximum(k * cost, THETA_FLOOR_BP)
    d = sig[v]["d"]
    return np.flatnonzero(np.isfinite(d) & np.isfinite(theta) & (np.abs(d) >= theta))


# ---------------------------------------------------------------------------------------------------------- trades
def trades(grid, sig, Q, S, venues, v, k, hold):
    """Non-overlapping taker trades of venue v toward the consensus: one open position at a time, the next decision no
    earlier than the previous exit. Skipped decisions (feed gap before the exit, no valid quote) consume no time."""
    idx = triggers(sig, v, k)
    starts, ends = S[v]
    rows, free = [], -np.inf
    for i in idx:
        s = float(grid[i])
        if s < free:
            continue
        te, tx = s + DELAY_S[v], s + DELAY_S[v] + hold
        k_s = session_of(starts, ends, [s])[0]
        if k_s < 0 or ends[k_s] < tx:
            continue
        be, ae, bqe, aqe = (x[0] for x in quote_at(Q[v], starts, ends, [te]))
        bx, ax, _, _ = (x[0] for x in quote_at(Q[v], starts, ends, [tx]))
        if not (np.isfinite(be) and np.isfinite(bx)):
            continue
        dev = sig[v]["d"][i]
        side = -1.0 if dev > 0 else 1.0
        me, mx = (be + ae) / 2, (bx + ax) / 2
        gross = side * 1e4 * np.log(mx / me)
        hs_e = 1e4 * (np.log(ae / me) if side > 0 else np.log(me / be))
        hs_x = 1e4 * (np.log(mx / bx) if side > 0 else np.log(ax / mx))
        touch = (aqe * ae) if side > 0 else (bqe * be)
        age = s - Q[v]["t"][asof(Q[v], [int(round(s * US))])[0]] / US      # seconds since the venue's last quote row
        rows.append(dict(venue=v, s=s, te=te, tx=tx, side=side, dev=dev, base=sig[v]["base"][i], age=age,
                         spread=sig[v]["spread"][i], gross=gross, hs_e=hs_e, hs_x=hs_x, fee=2 * FEE_BP[v],
                         cost=hs_e + hs_x + 2 * FEE_BP[v], thin=bool(touch < NOTIONAL)))
        free = tx
    return pd.DataFrame(rows)


def diagnostics(t, Q, S, venues):
    """For each trade: the share of the deviation closed by the exit (baseline held at the decision), how far the venue
    moved toward the consensus and how far the others' median moved toward the venue, decision to exit (bp)."""
    if not len(t):
        return t
    t = t.copy()
    closed, v_move, o_move = [], [], []
    warnings.simplefilter("ignore", RuntimeWarning)
    for r in t.itertuples():
        lm_s, lm_x = {}, {}
        for u in venues:
            for tt, store in ((r.s, lm_s), (r.tx, lm_x)):
                b, a, _, _ = (x[0] for x in quote_at(Q[u], *S[u], [tt]))
                store[u] = np.log((b + a) / 2) if np.isfinite(b) else np.nan
        oth_s = np.nanmedian([lm_s[u] for u in venues if u != r.venue] or [np.nan])
        oth_x = np.nanmedian([lm_x[u] for u in venues if u != r.venue] or [np.nan])
        d_x = 1e4 * (lm_x[r.venue] - oth_x) - r.base
        closed.append(1 - d_x / r.dev if r.dev else np.nan)
        v_move.append(r.side * 1e4 * (lm_x[r.venue] - lm_s[r.venue]))
        o_move.append(-r.side * 1e4 * (oth_x - oth_s))
    t["closed_share"], t["venue_move"], t["others_toward"] = closed, v_move, o_move
    return t


# ------------------------------------------------------------------------------------------------------- inference
def block_boot(x, blocks, rng, n=BOOT):
    x, blocks = np.asarray(x, float), np.asarray(blocks)
    ids = np.unique(blocks)
    if len(x) == 0:
        return dict(mean=np.nan, lo=np.nan, hi=np.nan, p_le0=np.nan, sd=np.nan, blocks=0)
    sums = np.array([x[blocks == b].sum() for b in ids])
    cnts = np.array([(blocks == b).sum() for b in ids])
    pick = rng.integers(0, len(ids), size=(n, len(ids)))
    m = sums[pick].sum(1) / cnts[pick].sum(1)
    return dict(mean=float(x.mean()), lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)),
                p_le0=float((m <= 0).mean()), sd=float(m.std()), blocks=int(len(ids)))


def verdict(n, ci1, mean2):
    if n < MIN_TRADES or ci1["blocks"] < MIN_BLOCKS:
        return "INCONCLUSIVE"
    return "PASS" if (ci1["lo"] > 0 and mean2 > 0) else "NULL"


def net(t, mult):
    return t.gross.to_numpy() - mult * t.cost.to_numpy()


def cell_rows(ins, scope, k, hold, t, rng):
    out = []
    for st in STRATA:
        g = t[t.stratum == st] if len(t) else t
        blocks = (g.s // 3600).to_numpy() if len(g) else np.array([])
        ci = block_boot(net(g, 1), blocks, rng) if len(g) else block_boot([], [], rng)
        row = dict(instrument=ins, scope=scope, k=k, hold=hold, stratum=st, n=len(g), blocks=ci["blocks"],
                   gross=float(g.gross.mean()) if len(g) else np.nan,
                   cost=float(g.cost.mean()) if len(g) else np.nan,
                   lo_1x=ci["lo"], hi_1x=ci["hi"], p_le0_1x=ci["p_le0"], mde80_1x=2.8 * ci["sd"],
                   thin=float(g.thin.mean()) if len(g) else np.nan)
        for m in COST_MULTS:
            row[f"net_{m}x"] = float(net(g, m).mean()) if len(g) else np.nan
        out.append(row)
    return out


# -------------------------------------------------------------------------------------------------------------- run
def run(root=DATA, out=None, plumbing=False):
    rng = np.random.default_rng(SEED)
    cells, primary, plumb = [], None, {}
    for ins in INSTRUMENTS:
        log(f"{ins}: building the 1-second residuals")
        grid, sig, Q, S, venues = build(root, ins)
        closed = cme_closed(grid) if len(grid) else np.zeros(0, bool)
        p = dict(grid_s=int(len(grid)), closed_s=int(closed.sum()), venues={})
        for v in venues:
            ok = np.isfinite(sig[v]["d"])
            p["venues"][v] = dict(valid_s=int(ok.sum()), median_spread_bp=float(np.nanmedian(sig[v]["spread"]))
                                  if np.isfinite(sig[v]["spread"]).any() else None,
                                  triggers={str(k): int(len(triggers(sig, v, k))) for k in K_THETA})
        plumb[ins] = p
        if plumbing:
            continue
        for k in K_THETA:
            for hold in HOLDS_S:
                per = {}
                for v in venues:
                    t = trades(grid, sig, Q, S, venues, v, k, hold)
                    if len(t):
                        t["stratum"] = np.where(cme_closed(t.s.to_numpy()), "closed", "open")
                    per[v] = t
                    cells += cell_rows(ins, v, k, hold, t, rng)
                pooled = pd.concat([x for x in per.values() if len(x)], ignore_index=True) if any(
                    len(x) for x in per.values()) else pd.DataFrame(columns=["s", "gross", "cost", "thin", "stratum"])
                cells += cell_rows(ins, "pooled", k, hold, pooled, rng)
                if (ins, k, hold) == (PRIMARY["instrument"], PRIMARY["k"], PRIMARY["hold"]):
                    primary = diagnostics(pooled[pooled.stratum == PRIMARY["stratum"]].reset_index(drop=True)
                                          if len(pooled) else pooled, Q, S, venues)
    if plumbing:
        return dict(plumbing=plumb)
    cells = pd.DataFrame(cells)
    pr = cells[(cells.instrument == PRIMARY["instrument"]) & (cells.scope == PRIMARY["scope"]) &
               (cells.k == PRIMARY["k"]) & (cells.hold == PRIMARY["hold"]) &
               (cells.stratum == PRIMARY["stratum"])].iloc[0]
    v = verdict(int(pr.n), dict(lo=pr.lo_1x, blocks=pr.blocks), pr.net_2x)
    summary = dict(verdict=v, primary=PRIMARY, primary_cell=pr.to_dict(), trials=TRIALS, plumbing=plumb,
                   primary_diag=dict(
                       n=int(len(primary)) if primary is not None else 0,
                       by_venue=primary.venue.value_counts().to_dict() if primary is not None and len(primary) else {},
                       closed_share_median=float(primary.closed_share.median()) if primary is not None and len(primary)
                       else None,
                       venue_move_median=float(primary.venue_move.median()) if primary is not None and len(primary)
                       else None,
                       others_toward_median=float(primary.others_toward.median())
                       if primary is not None and len(primary) else None,
                       quote_age_median_s=float(primary.age.median()) if primary is not None and len(primary) else None,
                       quote_age_over_5s=float((primary.age > 5).mean()) if primary is not None and len(primary)
                       else None))
    if out is not None:
        out = Path(out)
        (out / "results").mkdir(parents=True, exist_ok=True)
        cells.to_csv(out / "results" / "cells.csv", index=False)
        if primary is not None:
            primary.to_csv(out / "results" / "events_primary.csv", index=False)
        (out / "results" / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", action="store_true")
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args(argv)
    if a.manifest:
        log(f"manifest: {write_manifest()} files")
        return
    if a.plumbing:
        res = run(plumbing=True)
        (LANE / "plumbing.json").write_text(json.dumps(res, indent=1) + "\n")
        log("plumbing written")
        return
    sha = prereg.verify(LANE / "PREREG.md")
    from scripts.run_clockflow import check_inputs
    log(f"PREREG verified {sha[:12]}; {len(check_inputs(LANE / 'PREREG.md'))} inputs match; trials {TRIALS}")
    log(f"data manifest: {check_manifest()} files match")
    res = run(out=LANE)
    log(f"verdict {res['verdict']}: {json.dumps(res['primary_cell'], default=float)}")


if __name__ == "__main__":
    main()
