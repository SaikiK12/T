"""auction_v1 (R290): auction-market levels on 1-minute bars of the BTC, ETH and SOL perps, from real session anchors
and from placebo clocks, as set out in experiments/auction_v1/PREREG.md (M305, docs/AUCTION_AND_FLOW.md).

Five textbook rules (value-area re-entry, initial-balance break, opening-range break, VWAP +-2 SD, naked prior POC),
each traded in its textbook direction and against it, held 60 or 240 minutes, on three real anchors (00:00 UTC,
09:30 New York, 08:00 London) and eight placebo clocks. Two questions: do real anchors show more structure than
placebo clocks (an exact permutation test of ranks), and does any real-anchor variant trade (a White reality check
on 2021-04..2023 and the selected variant read on 2024-01..2026-09)?

usage: python scripts/run_auction.py
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import auction, data, prereg, stats  # noqa: E402
from scripts.run_clockflow import (check_inputs, funding_paid, load_funding, local_ms, net,  # noqa: E402
                                   reality_check, window)

LANE = ROOT / "experiments" / "auction_v1"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
MIN = 60_000
DAY = 86_400_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)       # 2020 is reserved: dropped on load
T1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)       # exclusive
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
HALVES = (("2024-01-01", "2025-06-30"), ("2025-07-01", "2026-09-30"))
COST, API = 2e-4, 8.5e-4                       # per side: Lighter API (0 fee) at 1x; MEXC API reported
REAL = {"U00": ("UTC", 0, 0), "NY": ("America/New_York", 9, 30), "LDN": ("Europe/London", 8, 0)}
PLACEBO = {"P0225": 145, "P0447": 287, "P0925": 565, "P1104": 664,          # minutes after 00:00 UTC, drawn with
           "P0600": 360, "P1700": 1020, "P1900": 1140, "P2300": 1380}       # seed 290 (PREREG)
RULES = ("VA80", "IB60", "OR15", "VWAP2", "NPOC")
SIDES = ("book", "anti")
HOLDS = (60, 240)
TICK = 5e-4                                    # profile bin: 5 bp of the prior session's last close
MIN_PRIOR = 1200                               # valid bars the prior session needs for its profile
SCAN = {"IB60": 480, "OR15": 480, "VWAP2": 1200}   # minutes after the anchor within which a trigger may fire
RC_B, RC_BLOCK, SEED = 2000, 10, 290
TRIALS = len(REAL) * len(RULES) * len(SIDES) * len(HOLDS)          # 60
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- inputs
def load_bars(path, t0=T0, t1=T1):
    """High, low, close and volume of the bar opening at t0 + i minutes, NaN where the bar is missing or invalid."""
    k = pd.read_parquet(path, columns=["t", "high", "low", "close", "volume", "count"])
    k = k[(k.t >= t0) & (k.t < t1)].drop_duplicates("t")
    k = k[(k["count"] > 0) & (k.close > 0)]
    n = (t1 - t0) // MIN
    out = {c: np.full(n, np.nan) for c in ("high", "low", "close", "volume")}
    i = (k.t.values - t0) // MIN
    for c in out:
        out[c][i] = k[c].values
    return out["high"], out["low"], out["close"], out["volume"]


def anchor_times(name, days):
    """Epoch ms of the anchor on each calendar day: local time for the real anchors, a UTC clock for placebos."""
    if name in REAL:
        tz, hh, mm = REAL[name]
        return local_ms(days, hh, mm, tz)
    return days.as_unit("ms").asi8.astype(np.int64) + PLACEBO[name] * MIN


# ----------------------------------------------------------------------------------------------------------- rules
def first(cond):
    """Index of the first True, or -1."""
    return int(np.argmax(cond)) if cond.any() else -1


def session_signals(H, L, C, V, A, t0=T0):
    """Decision times (ms, -1 when the rule does not fire) and textbook sides of every rule, one per session.
    Session d runs from A[d] to A[d+1]; its prior session is d - 1. A decision at time tau uses bars that close by
    tau only."""
    n = len(C)
    idx = (np.asarray(A, np.int64) - t0) // MIN
    S = len(A)
    tau = {r: np.full(S, -1, np.int64) for r in RULES}
    side = {r: np.zeros(S, np.int8) for r in RULES}
    tb = t0 + np.arange(n, dtype=np.int64) * MIN
    sid = auction.session_ids(tb, A)
    vw = auction.vwap_bands(H, L, C, V, session=sid, ks=(2,))
    up2, dn2 = vw.up2.values, vw.dn2.values
    with np.errstate(invalid="ignore"):
        for d in range(1, S - 1):
            p0, b0, b1 = idx[d - 1], idx[d], idx[d + 1]
            if p0 < 0 or b1 > n:
                continue
            at = lambda m: C[b0 + m - 1]                     # price at A + m minutes: close of the bar before
            # prior-session levels: VA80 and NPOC
            pc = C[p0:b0]
            if np.isfinite(pc).sum() >= MIN_PRIOR:
                tick = pc[np.isfinite(pc)][-1] * TICK
                prof = auction.volume_profile(H[p0:b0], L[p0:b0], V[p0:b0], tick)
                poc, val, vah = auction.value_area(prof)
                lo, hi = val, vah + tick
                o = at(0)
                if np.isfinite(o) and (o < lo or o >= hi):
                    c = np.array([at(30 * p) for p in range(1, 13)])
                    inside = (c >= lo) & (c < hi)
                    k = first(inside[1:] & inside[:-1])
                    if k >= 0:
                        tau["VA80"][d] = A[d] + 30 * (k + 2) * MIN
                        side["VA80"][d] = 1 if o < lo else -1
                h, l = H[b0:b0 + 60], L[b0:b0 + 60]
                touched = np.any((l < poc + tick) & (h >= poc))
                c60 = at(60)
                if not touched and np.isfinite(c60):
                    tau["NPOC"][d] = A[d] + 60 * MIN
                    side["NPOC"][d] = 1 if c60 < poc + tick / 2 else -1
            # initial balance and opening range: follow the first close beyond
            for r, w in (("IB60", 60), ("OR15", 15)):
                h, l = H[b0:b0 + w], L[b0:b0 + w]
                if np.isfinite(h).sum() < 0.8 * w:
                    continue
                ibh, ibl = np.nanmax(h), np.nanmin(l)
                end = min(b0 + SCAN[r], b1)
                seg = C[b0 + w:end]
                k = first((seg > ibh) | (seg < ibl))
                if k >= 0:
                    tau[r][d] = tb[b0 + w + k] + MIN
                    side[r][d] = 1 if seg[k] > ibh else -1
            # session VWAP +-2 SD: fade the first close beyond, after the first hour
            end = min(b0 + SCAN["VWAP2"], b1)
            seg = C[b0 + 60:end]
            k = first((seg > up2[b0 + 60:end]) | (seg < dn2[b0 + 60:end]))
            if k >= 0:
                tau["VWAP2"][d] = tb[b0 + 60 + k] + MIN
                side["VWAP2"][d] = -1 if seg[k] > up2[b0 + 60 + k] else 1
    return tau, side


def rule_trades(C, F, rate, tau, side, sgn, h, t0=T0):
    """Trades of one rule, side (+1 book, -1 anti) and hold: entry one minute after the decision, exit h later."""
    ok = tau >= 0
    entry = tau[ok] + MIN
    exit_ = entry + h * MIN
    price = lambda t: np.where((t - t0) // MIN - 1 < len(C), C[np.clip((t - t0) // MIN - 1, 0, len(C) - 1)], np.nan)
    E, X = price(entry), price(exit_)
    s = side[ok].astype(float) * sgn
    good = np.isfinite(E) & np.isfinite(X)
    gross = s[good] * (X[good] / E[good] - 1)
    fund = funding_paid(F, rate, s[good], entry[good], exit_[good])
    return pd.DataFrame({"entry": entry[good], "side": s[good], "E": E[good], "X": X[good], "gross": gross,
                         "funding": fund})


def book_of(trs, cal):
    tr = pd.concat(trs, ignore_index=True)
    tr["day"] = pd.to_datetime(tr.entry // DAY * DAY, unit="ms").astype(cal.dtype)
    g = tr.groupby("day")
    book = pd.DataFrame({"gross": g.gross.sum() / 3, "funding": g.funding.sum() / 3, "n": g.size()})
    return book.reindex(cal, fill_value=0), tr


def name_of(anchor, rule, sd, h):
    return f"{anchor}_{rule}_{sd}_h{h}"


# ------------------------------------------------------------------------------------------------------------ tests
def anchor_test(T, real=tuple(REAL), anchors=None):
    """Exact permutation test: T[combo][anchor] = |t| of a rule-hold's discovery gross series at that anchor. Ranks
    within each combo (1 = smallest, ties averaged); S(set) = the sum of the set's ranks over combos. p is the share
    of all 3-anchor sets whose S is at least the real set's."""
    anchors = anchors or list(next(iter(T.values())).keys())
    R = pd.DataFrame(T).T[anchors].rank(axis=1)              # rows: combos, columns: anchors
    s_obs = float(R[list(real)].sum().sum())
    sets = list(itertools.combinations(anchors, len(real)))
    s_all = np.array([R[list(s)].sum().sum() for s in sets])
    return {"S": s_obs, "p": float((s_all >= s_obs - 1e-9).mean()), "sets": len(sets),
            "mean_rank_real": {a: float(R[a].mean()) for a in real}, "ranks": R.round(2).to_dict()}


def summarize(name, meta, book, tr, cal):
    rows = []
    for wname, (a, b) in (("discovery", DISC), ("validation", VALID), ("valid_h1", HALVES[0]),
                          ("valid_h2", HALVES[1])):
        sel = window(cal, a, b)
        trw = tr[(tr.day >= pd.Timestamp(a)) & (tr.day <= pd.Timestamp(b))]
        x1 = net(book, COST)[sel]
        _, mu, t = stats.newey_west_t(x1, 10)
        _, _, tg = stats.newey_west_t(book.gross.values[sel], 10)
        rows.append({"variant": name, **meta, "window": wname, "days": int(sel.sum()), "trades": len(trw),
                     "hit": float((trw.gross > 0).mean()) if len(trw) else np.nan,
                     "gross_trade_bp": trw.gross.mean() * 1e4 if len(trw) else np.nan, "gross_t": tg,
                     "net1_bp": mu * 1e4, "net2_bp": net(book, 2 * COST)[sel].mean() * 1e4,
                     "net3_bp": net(book, 3 * COST)[sel].mean() * 1e4, "net_api_bp": net(book, API)[sel].mean() * 1e4,
                     "nw_t1": t, "sharpe1": x1.mean() / x1.std() * np.sqrt(365) if x1.std() > 0 else np.nan,
                     "breakeven_bp_side": trw.gross.mean() / 2 * 1e4 if len(trw) else np.nan})
    return rows


def decide(names, books, cal, seed=SEED):
    disc, val = window(cal, *DISC), window(cal, *VALID)
    X = np.array([net(books[n], COST)[disc] for n in names])
    stat, rc_p, p95 = reality_check(X, np.random.default_rng(seed), RC_B, RC_BLOCK)
    j = int(np.argmax(stat))
    b = books[names[j]]
    v1, v2 = net(b, COST)[val], net(b, 2 * COST)[val]
    tv = float(stats.newey_west_t(v1, 10)[2])
    halves = [float(net(b, COST)[window(cal, *hh)].mean()) for hh in HALVES]
    passed = bool(rc_p < 0.05 and tv >= 2.0 and v2.mean() > 0 and min(halves) > 0)
    return {"rc_p": rc_p, "rc_null_p95": p95, "best": names[j], "best_disc_stat": float(stat[j]),
            "best_disc_net1_bp": float(X[j].mean() * 1e4), "valid_t1": tv, "valid_net1_bp": float(v1.mean() * 1e4),
            "valid_net2_bp": float(v2.mean() * 1e4), "valid_net3_bp": float(net(b, 3 * COST)[val].mean() * 1e4),
            "valid_api_bp": float(net(b, API)[val].mean() * 1e4), "valid_halves_net1_bp": [h * 1e4 for h in halves],
            "pass": passed}


# --------------------------------------------------------------------------------------------------------- the run
def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    cal = pd.date_range(pd.to_datetime(T0, unit="ms"), pd.to_datetime(T1 - DAY, unit="ms"), freq="D")
    days = pd.date_range(pd.to_datetime(T0, unit="ms") - pd.Timedelta(days=1), pd.to_datetime(T1, unit="ms"),
                         freq="D")
    anchors = list(REAL) + list(PLACEBO)
    trades = {}                                   # (anchor, rule, side, hold) -> list of per-coin trade frames
    for sym in COINS:
        H, L, C, V = load_bars(data.ROOT / "klines_1m" / f"{sym}.parquet")
        F, rate = load_funding(data.ROOT / "fundingRate" / f"{sym}.parquet")
        for a in anchors:
            tau, side = session_signals(H, L, C, V, anchor_times(a, days))
            for r in RULES:
                for sd, sgn in (("book", 1), ("anti", -1)):
                    for h in HOLDS:
                        t = rule_trades(C, F, rate, tau[r], side[r], sgn, h)
                        t["coin"] = sym
                        trades.setdefault((a, r, sd, h), []).append(t)
            log(f"{sym} {a}: " + ", ".join(f"{r} {int((tau[r] >= 0).sum())}" for r in RULES))
    rows, books, daily, trs = [], {}, {}, []
    for (a, r, sd, h), parts in trades.items():
        name = name_of(a, r, sd, h)
        book, tr = book_of(parts, cal)
        books[name] = book
        meta = {"anchor": a, "real": a in REAL, "rule": r, "side": sd, "hold": h}
        rows += summarize(name, meta, book, tr, cal)
        if a in REAL:
            tr["variant"] = name
            trs.append(tr)
            daily[name] = net(book, COST)
    disc = window(cal, *DISC)
    T = {f"{r}_h{h}": {a: abs(float(stats.newey_west_t(books[name_of(a, r, 'book', h)].gross.values[disc], 10)[2]))
                       for a in anchors} for r in RULES for h in HOLDS}
    at = anchor_test(T, anchors=anchors)
    log(f"anchor test: S {at['S']:.1f}, p {at['p']:.4f} over {at['sets']} sets; mean ranks {at['mean_rank_real']}")
    real_names = [name_of(a, r, sd, h) for a in REAL for r in RULES for sd in SIDES for h in HOLDS]
    assert len(real_names) == TRIALS
    res = decide(real_names, books, cal)
    x = pd.Series(net(books[res["best"]], COST), index=cal)
    res["best_net1_bp_by_year"] = (x.groupby(x.index.year).mean() * 1e4).round(3).to_dict()
    res["best_top5_days_share"] = float(np.sort(x.values)[::-1][:5].sum() / x.sum()) if x.sum() > 0 else None
    tb = pd.concat(trs)
    tb = tb[tb.variant == res["best"]]
    res["best_gross_bp_per_trade_by_coin"] = (tb.groupby("coin").gross.mean() * 1e4).round(3).to_dict()
    log(f"trading: best {res['best']} stat {res['best_disc_stat']:.2f} rc_p {res['rc_p']:.4f}; validation t "
        f"{res['valid_t1']:.2f}, 2x {res['valid_net2_bp']:.2f} bp/d, halves "
        f"{[round(v, 2) for v in res['valid_halves_net1_bp']]} -> {'PASS' if res['pass'] else 'fail'}")
    verdict = "PARTIAL" if res["pass"] else "NULL"
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "variants.csv", index=False, float_format="%.6g")
    pd.DataFrame(daily, index=cal.date).rename_axis("day").to_csv(out / "daily.csv.gz", float_format="%.8g")
    pd.concat(trs).to_csv(out / "trades.csv.gz", index=False, float_format="%.8g")
    summary = {"rid": "R290", "verdict": verdict, "anchor_effect": bool(at["p"] < 0.05), "trials": TRIALS,
               "prereg_sha256": sha, "inputs": shas, "anchor_test": at, "trading": res}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {verdict}; anchor effect {'yes' if summary['anchor_effect'] else 'no'} (p {at['p']:.4f})")
    return summary


if __name__ == "__main__":
    main()
