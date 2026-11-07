"""R412 boroslock_v1 (M480, item 97): does a Boros funding-rate lock deliver the APR it locked? A historical
fidelity audit of matured BTC/ETH single-venue markets on Binance and Hyperliquid, as set out in
experiments/boroslock_v1/PREREG.md. A measurement: 0 trials, no trade.

The lock: short the perp (receive its funding) and sell YU on Boros at the best bid (pay Boros's floating rate,
receive the fixed bid). If Boros's floating settlements equal the venue's funding, the funding legs cancel and the
position earns the bid minus Boros's fees, whatever funding does. The audit measures how far that held:
- each Boros settlement (data/boros/hist/settlement) against the venue funding event it should copy
  (data/fundingRate for Binance, data/hyperliquid/funding for Hyperliquid);
- each daily 04:00 UTC entry: realized = locked + (venue funding - Boros floating) / tau over (entry, maturity].

usage: python scripts/run_boroslock.py [--plumbing]
"""
import argparse
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg  # noqa: E402

LANE = ROOT / "experiments" / "boroslock_v1"
BOROS = data.ROOT / "boros"
PROV = ROOT / "docs" / "provenance" / "boros_hist.json"
VENUES = ("BINANCE", "HYPERLIQUID")
COINS = ("BTC", "ETH")
YEAR = 365 * 86400                     # Boros annualizes with 365 days (settlementApr = rate x 8760 h / period h)
T_LO_MS = int(pd.Timestamp("2025-07-01", tz="UTC").value // 10**6)  # venue rows before this are never read
ENTRY_HOUR = 4                         # 04:00 UTC: no Binance funding hour; the next HL settlement is seconds later
MIN_DAYS = 7                           # entries need at least 7 days to maturity
MATCH_S = 600                          # a settlement copies the venue event at most 10 minutes before it
ORACLE_TOL = 1e-4                      # 1 bp APR: a settlement "matches" its venue event within this
HEDGE_RT = 0.0030                      # indicative spot+perp round trip (2 x (10 + 5) bp), scaled by m
MS = (1, 2, 3)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def check_files(prov_path=PROV, root=ROOT):
    """Every file the fetch recorded must still hash to its recorded sha256; returns the set of paths."""
    prov = json.loads(Path(prov_path).read_text())
    for f in prov["file_hashes"]:
        got = prereg.sha256_file(root / f["path"])
        if got != f["sha256"]:
            raise prereg.PreregError(f"{f['path']}: sha256 {got} != recorded {f['sha256']}")
    return {f["path"] for f in prov["file_hashes"]}


def ndjson(kind, name, base=BOROS):
    """All records of one kind for one market, sorted by timestamp, de-duplicated."""
    rows = []
    for p in sorted((base / "hist" / kind / name).glob("*.ndjson.zip")):
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                rows += [json.loads(line) for line in io.TextIOWrapper(z.open(n), encoding="utf-8") if line.strip()]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)


def scope(markets, venue_end):
    """Matured single-venue BTC/ETH markets on Binance/Hyperliquid whose maturity the venue data covers."""
    out = []
    for m in markets:
        md, im, cf, ex = m["metadata"], m["imData"], m["config"], m["extConfig"]
        venue = im["symbol"].split("-")[0]
        if md.get("isSpreadMarket") or venue not in VENUES or md.get("underlyingSymbol") not in COINS:
            continue
        mat = int(im["maturity"])
        if mat > venue_end[venue][md["underlyingSymbol"]]:
            continue
        out.append({"id": m["marketId"], "name": f"{m['marketId']}-{im['symbol']}", "venue": venue,
                    "coin": md["underlyingSymbol"], "token": m.get("tokenId"), "maturity": mat,
                    "taker": int(cf["takerFee"]) / 1e18, "settle": int(ex["settleFeeRate"]) / 1e18,
                    "period": int(ex["paymentPeriod"])})
    return sorted(out, key=lambda r: (r["venue"], r["coin"], r["maturity"], r["id"]))


def venue_funding(venue, coin, root=data.ROOT):
    """Venue funding events from T_LO_MS: columns ts (s, rounded to the minute), rate (per period), apr."""
    if venue == "BINANCE":
        d = pd.read_parquet(root / "fundingRate" / f"{coin}USDT.parquet", filters=[("t", ">=", T_LO_MS)])
        apr = d.rate * 8760 / d.interval_h
    else:
        d = pd.read_parquet(root / "hyperliquid" / "funding" / f"{coin}.parquet", columns=["t", "rate"],
                            filters=[("t", ">=", T_LO_MS)])
        apr = d.rate * 8760
    ts = (np.round(d.t.to_numpy(np.int64) / 60_000) * 60).astype(np.int64)
    return pd.DataFrame({"ts": ts, "rate": d.rate.to_numpy(float), "apr": apr.to_numpy(float)}) \
        .drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def match(st, vf, maturity):
    """Pair each Boros settlement with the latest venue event in [ts - MATCH_S, ts]; and each venue event in the
    market's life (after its first settlement, up to maturity) with a settlement in [t_v, t_v + MATCH_S]. A first
    settlement at exactly 0 APR is the listing event and is left out of the pairing.
    Returns (settlement table with venue apr or NaN, number of venue events, number of them without a settlement)."""
    s = st[["timestamp", "settlementApr"]].rename(columns={"timestamp": "ts"}).astype({"ts": np.int64})
    life = vf[(vf.ts > s.ts.min()) & (vf.ts <= maturity)]
    if s.settlementApr.iloc[0] == 0:                 # the listing event initializes the index and copies nothing
        s = s.iloc[1:]
    m = pd.merge_asof(s.sort_values("ts"), vf.rename(columns={"ts": "tv"})[["tv", "apr"]], left_on="ts",
                      right_on="tv", direction="backward", tolerance=MATCH_S)
    hit = pd.merge_asof(life[["ts"]], s[["ts"]].rename(columns={"ts": "tb"}), left_on="ts", right_on="tb",
                        direction="forward", tolerance=MATCH_S)
    return m, len(life), int(hit.tb.isna().sum())


def entries(md, st, vf, mk, tbill):
    """One row per daily ENTRY_HOUR snapshot with a bid and at least MIN_DAYS to maturity."""
    T = mk["maturity"]
    md = md[md.bestBid.notna() & (md.timestamp % 86400 == ENTRY_HOUR * 3600) & (md.timestamp <= T - MIN_DAYS * 86400)]
    s_ts, s_apr = st.timestamp.to_numpy(np.int64), st.settlementApr.to_numpy(float)
    v_ts, v_rate = vf.ts.to_numpy(np.int64), vf.rate.to_numpy(float)
    rows = []
    for r in md.itertuples():
        t0 = int(r.timestamp)
        tau = (T - t0) / YEAR
        V = v_rate[(v_ts >= t0) & (v_ts <= T)].sum()       # the venue event at t0 is the one settled at t0 + secs
        B = (s_apr[(s_ts > t0) & (s_ts <= T + MATCH_S)] * mk["period"] / YEAR).sum()
        fee = mk["taker"] + mk["settle"]
        locked = r.bestBid - fee
        tb = tbill(t0)
        row = {"market": mk["name"], "venue": mk["venue"], "coin": mk["coin"], "token": mk["token"], "t0": t0,
               "maturity": T, "days": (T - t0) / 86400, "bid": r.bestBid, "ask": r.bestAsk, "oi": r.notionalOI,
               "fee": fee, "locked": locked, "fidelity": (V - B) / tau, "realized": locked + (V - B) / tau,
               "naked": V / tau, "boros_float": B / tau, "tbill": tb}
        for m in MS:
            row[f"carry_{m}x"] = r.bestBid - m * fee - m * HEDGE_RT / tau - tb
        rows.append(row)
    return rows


def tbill_fn(root=data.ROOT):
    u = pd.read_parquet(root / "macro" / "ust_3m.parquet", filters=[("t", ">=", T_LO_MS)]).sort_values("t")
    t, v = (u.t.to_numpy(np.int64) // 1000), u.value.to_numpy(float) / 100
    return lambda t0: float(v[np.searchsorted(t, t0, side="right") - 1])


def q(x, p):
    return float(np.quantile(x, p)) if len(x) else None


def describe(e, s):
    """The decision measures and the descriptive economics for one venue (entries e, matched settlements s)."""
    ok = s[s.apr.notna()]
    af = (e.fidelity.abs() * 1e4).to_numpy()
    out = {"markets": int(e.market.nunique()), "entries": len(e),
           "settlements": int(len(s)), "settlements_matched": int(len(ok)),
           "oracle_abs_diff_bp": {"median": q((ok.settlementApr - ok.apr).abs() * 1e4, 0.5),
                                  "p99": q((ok.settlementApr - ok.apr).abs() * 1e4, 0.99),
                                  "max": float((ok.settlementApr - ok.apr).abs().max() * 1e4) if len(ok) else None},
           "oracle_within_1bp_share": float(((ok.settlementApr - ok.apr).abs() <= ORACLE_TOL).mean()) if len(ok) else None,
           "fidelity_bp": {"mean": float(e.fidelity.mean() * 1e4), "median_abs": q(af, 0.5), "p95_abs": q(af, 0.95),
                           "max_abs": float(af.max()) if len(af) else None},
           "locked_pct": {"mean": float(e.locked.mean() * 100), "median": q(e.locked * 100, 0.5)},
           "realized_pct_mean": float(e.realized.mean() * 100),
           "naked_pct": {"mean": float(e.naked.mean() * 100), "median": q(e.naked * 100, 0.5)},
           "naked_minus_locked_pct": {"mean": float((e.naked - e.locked).mean() * 100),
                                      "p05": q((e.naked - e.locked) * 100, 0.05),
                                      "p95": q((e.naked - e.locked) * 100, 0.95)},
           "locked_minus_tbill_pct": {"mean": float((e.locked - e.tbill).mean() * 100),
                                      "median": q((e.locked - e.tbill) * 100, 0.5),
                                      "share_gt0": float((e.locked > e.tbill).mean()),
                                      "share_ge1pct": float((e.locked - e.tbill >= 0.01).mean())},
           "carry_minus_tbill_pct": {f"{m}x": {"mean": float(e[f'carry_{m}x'].mean() * 100),
                                               "share_gt0": float((e[f'carry_{m}x'] > 0).mean())} for m in MS},
           "spread_bp_median": q((e.ask - e.bid) * 1e4, 0.5), "oi_median": q(e.oi, 0.5),
           "by_coin": {c: {"entries": int((e.coin == c).sum()), "locked_pct": float(e[e.coin == c].locked.mean() * 100),
                           "fidelity_bp_mean": float(e[e.coin == c].fidelity.mean() * 1e4)}
                       for c in COINS if (e.coin == c).any()},
           "by_month": {k: {"entries": len(g), "locked_pct": round(float(g.locked.mean() * 100), 3),
                            "naked_pct": round(float(g.naked.mean() * 100), 3),
                            "tbill_pct": round(float(g.tbill.mean() * 100), 3)}
                        for k, g in e.groupby(pd.to_datetime(e.t0, unit="s").dt.strftime("%Y-%m"))}}
    return out


def verdict(d, n_venue, n_missed):
    share = 1 - n_missed / n_venue if n_venue else 0.0
    checks = {"venue_events_with_settlement_ge_99pct": share >= 0.99,
              "settlements_within_1bp_ge_99pct": (d["oracle_within_1bp_share"] or 0) >= 0.99,
              "fidelity_median_abs_le_10bp": (d["fidelity_bp"]["median_abs"] or 1e9) <= 10,
              "fidelity_p95_abs_le_50bp": (d["fidelity_bp"]["p95_abs"] or 1e9) <= 50}
    return {"venue_events": n_venue, "venue_events_missed": n_missed, "coverage": share, "checks": checks,
            "verdict": "LOCK_HOLDS" if all(checks.values()) else "LOCK_DEVIATES"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only: no fidelity, rate or return statistic")
    a = ap.parse_args()
    if not a.plumbing:
        sha = prereg.verify(LANE / "PREREG.md")
        from scripts.run_clockflow import check_inputs
        shas = check_inputs(LANE / "PREREG.md")
        log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    n_files = len(check_files())
    log(f"{n_files} Boros files match docs/provenance/boros_hist.json")
    VF = {(v, c): venue_funding(v, c) for v in VENUES for c in COINS}
    venue_end = {v: {c: int(VF[(v, c)].ts.max()) for c in COINS} for v in VENUES}
    tbill = tbill_fn()
    mks = scope(json.loads((BOROS / "markets.json").read_text()), venue_end)
    E, S, cover = [], [], {v: [0, 0] for v in VENUES}
    for mk in mks:
        st, md = ndjson("settlement", mk["name"]), ndjson("market-data", mk["name"])
        if st.empty or md.empty:
            log(f"{mk['name']}: no settlement or market data, skipped")
            continue
        vf = VF[(mk["venue"], mk["coin"])]
        if a.plumbing:
            n_e = int((md.bestBid.notna() & (md.timestamp % 86400 == ENTRY_HOUR * 3600)
                       & (md.timestamp <= mk["maturity"] - MIN_DAYS * 86400)).sum())
            log(f"{mk['name']}: {len(st)} settlements, {len(md)} hourly snapshots, {n_e} entry days")
            E.append({"venue": mk["venue"], "n": n_e}); S.append({"venue": mk["venue"], "n": len(st)})
            continue
        m, n_v, n_miss = match(st, vf, mk["maturity"])
        cover[mk["venue"]][0] += n_v
        cover[mk["venue"]][1] += n_miss
        S.append(m.assign(venue=mk["venue"], market=mk["name"]))
        E += entries(md, st, vf, mk, tbill)
    if a.plumbing:
        for v in VENUES:
            log(f"{v}: {sum(1 for mk in mks if mk['venue'] == v)} markets in scope, "
                f"{sum(r['n'] for r in S if r['venue'] == v)} settlements, {sum(r['n'] for r in E if r['venue'] == v)} entries")
        return
    E, S = pd.DataFrame(E), pd.concat(S, ignore_index=True)
    res = {"prereg_sha256": sha, "boros_files": n_files, "venue_end": venue_end,
           "markets": [mk["name"] for mk in mks], "venues": {}}
    for v in VENUES:
        d = describe(E[E.venue == v], S[S.venue == v])
        d.update(verdict(d, *cover[v]))
        res["venues"][v] = d
        log(f"{v}: {d['verdict']} {json.dumps(d['checks'])}")
    (LANE / "results").mkdir(exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    E.to_csv(LANE / "results" / "entries.csv", index=False)
    S["absdiff_bp"] = (S.settlementApr - S.apr).abs() * 1e4
    S.groupby("market").agg(settlements=("ts", "size"), matched=("apr", "count"),
                            absdiff_bp_median=("absdiff_bp", "median"), absdiff_bp_max=("absdiff_bp", "max")) \
        .to_csv(LANE / "results" / "settlements_by_market.csv")
    log(f"done: {len(E)} entries, {len(S)} settlements")


if __name__ == "__main__":
    main()
