"""unlocks_v1 (R265): the old session's unlock short (E01, S1) on 2021-26 Binance perps, as set out in
experiments/unlocks_v1/PREREG.md. Gate 0. Rebuilds the frozen event list and symbol map from the snapshot first,
then prices every event, the matched random-date null and the logged variants.

usage: python scripts/run_unlocks.py
"""
import gzip
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data, panel, prereg  # noqa: E402
import unlock_events  # noqa: E402

LANE = ROOT / "experiments" / "unlocks_v1"
SNAP = data.ROOT / "unlocks" / "2026-10-20"
FROZEN = {"events.csv": "24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e",
          "symbol_map.csv": "0f924ae96cf137e8a09305aff0c07ec041f3a07cd5417643741e3366aace472b"}
COST = {1: 0.002, 2: 0.004, 3: 0.006}            # round trip
REPS, SEED = 2000, 265
FIRST_D, LAST_D = "2021-02-07", data.END
H, DAYH = panel.HOUR, 24
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_inputs():
    for name, want in FROZEN.items():
        assert sha(LANE / name) == want, f"{name} differs from the frozen sha"
    files = json.loads((SNAP / "manifest.json").read_text())["files"]
    for rel, meta in files.items():
        raw = gzip.decompress((SNAP / rel).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == meta["sha256"], f"snapshot file {rel} changed"
    with tempfile.TemporaryDirectory() as d:
        smap = unlock_events.symbol_map(SNAP)
        smap.to_csv(Path(d) / "symbol_map.csv", index=False)
        unlock_events.events(SNAP, smap, SNAP.name).to_csv(Path(d) / "events.csv", index=False)
        for name, want in FROZEN.items():
            assert sha(Path(d) / name) == want, f"rebuilt {name} does not reproduce the frozen file"
    log(f"inputs: frozen files match, {len(files)} snapshot files verified, rebuild reproduces both byte for byte")


def cluster_t(x, groups):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return np.nan
    m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(groups)).sum().values
    G = len(s)
    if G < 2:
        return np.nan
    se = np.sqrt(G / (G - 1) * (s ** 2).sum()) / n
    return m / se if se > 0 else np.nan


class Prices:
    """Last traded close (volume > 0) at or before each hour row, per perp."""

    def __init__(self, p):
        self.t0 = int(p.t[0])
        close = np.asarray(p["close"], np.float64)
        vol = np.asarray(p["volume"], np.float64)
        ok = np.isfinite(close) & (np.nan_to_num(vol) > 0)
        T = len(p.t)
        idx = np.where(ok, np.arange(T)[:, None], -1)
        self.last = np.maximum.accumulate(idx, axis=0)
        self.close = close
        self.final = self.last[-1]                             # last traded row overall
        self.fund = np.nan_to_num(np.asarray(p["fund_event"], np.float64))
        self.cumfund = np.vstack([np.zeros((1, close.shape[1])), np.cumsum(self.fund, axis=0)])
        qv = np.nan_to_num(np.asarray(p["quote_volume"], np.float64))
        has = np.isfinite(np.asarray(p["quote_volume"], np.float64))
        D = T // DAYH
        self.dqv = qv[:D * DAYH].reshape(D, DAYH, -1).sum(axis=1)
        self.dhas = has[:D * DAYH].reshape(D, DAYH, -1).any(axis=1)
        self.T = T

    def row_close_of_day(self, day_ms):
        """Row of the bar opening 23:00 UTC on that day (its close is the day's close)."""
        return (np.asarray(day_ms, np.int64) - self.t0) // H + 23

    def trade(self, s, entry_row, exit_row):
        """(gross short return, funding received, delisted_in_hold) or None when the entry is not priceable."""
        entry_row, exit_row = np.asarray(entry_row), np.asarray(exit_row)
        inside = (entry_row >= 0) & (exit_row < self.T)
        er = np.clip(entry_row, 0, self.T - 1)
        xr = np.clip(exit_row, 0, self.T - 1)
        je = self.last[er, s]
        ok = inside & (je >= 0) & (er - je < 24)
        jx = self.last[xr, s]
        jx = np.where(ok, np.maximum(jx, je), je)
        ce = np.where(ok, self.close[np.maximum(je, 0), s], np.nan)
        cx = np.where(ok, self.close[np.maximum(jx, 0), s], np.nan)
        gross = -(cx / ce - 1)
        fund = self.cumfund[xr + 1, s] - self.cumfund[er + 1, s]
        delisted = ok & (self.final[s] < xr)
        return np.where(ok, gross, np.nan), np.where(ok, fund, np.nan), delisted

    def adv_ratio(self, s, day_ms, tokens, mult):
        """V = tokens x (close at end of D-8 / mult) / mean daily quote volume over D-37..D-8 (>= 20 days)."""
        d = int((day_ms - self.t0) // (DAYH * H))
        r8 = self.row_close_of_day(day_ms - 8 * DAYH * H)
        if r8 < 0 or d - 37 < 0:
            return np.nan
        j = self.last[r8, s]
        if j < 0 or r8 - j >= 24:
            return np.nan
        sl = slice(d - 37, d - 7)
        days = self.dhas[sl, s]
        if days.sum() < 20:
            return np.nan
        adv = self.dqv[sl, s][days].mean()
        return tokens * self.close[j, s] / mult / adv if adv > 0 else np.nan


def summarize(x, groups):
    x = np.asarray(x, float)
    return {"n": int(len(x)), "mean_pct": float(np.mean(x) * 100) if len(x) else np.nan,
            "median_pct": float(np.median(x) * 100) if len(x) else np.nan,
            "hit": float((x > 0).mean()) if len(x) else np.nan, "week_cluster_t": float(cluster_t(x, groups))}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs()
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    ev = pd.read_csv(LANE / "events.csv")
    smap = pd.read_csv(LANE / "symbol_map.csv")
    prim = ev[(ev.venue == "binance") & (ev.window == "archive") & ev.check.isin(["verified", "unverified"])].copy()
    log(f"primary candidates: {len(prim)} events on {prim.perp.nunique()} perps")
    perps = sorted(set(prim.perp) | {"BTCUSDT"})
    p = panel.load_panel(perps)
    px = Prices(p)
    col = {s: i for i, s in enumerate(p.symbols)}
    btc = col["BTCUSDT"]

    D = px.row_close_of_day(prim.day_ms.values)
    S = np.array([col[s] for s in prim.perp])
    gross = np.full(len(prim), np.nan)
    fund = np.full(len(prim), np.nan)
    dl = np.zeros(len(prim), bool)
    extra = {k: np.full(len(prim), np.nan) for k in ("btc", "g30", "g_post", "V")}
    for i, (s, d) in enumerate(zip(S, D)):
        g, f, x = px.trade(s, d - 7 * DAYH, d)
        gross[i], fund[i], dl[i] = g, f, x
        if np.isfinite(g):
            gb, _, _ = px.trade(btc, d - 7 * DAYH, d)
            extra["btc"][i] = -gb                                   # BTC's own return over the hold
            extra["g30"][i] = px.trade(s, d - 30 * DAYH, d)[0]
            extra["g_post"][i] = px.trade(s, d, d + 7 * DAYH)[0]
            r = prim.iloc[i]
            extra["V"][i] = px.adv_ratio(s, int(r.day_ms), float(r.tokens), float(r.mult))
    prim["gross"], prim["funding"], prim["delisted_in_hold"] = gross, fund, dl
    for k, v in extra.items():
        prim[k] = v
    priced = prim[np.isfinite(prim.gross)].copy()
    log(f"priced {len(priced)}, no_market {len(prim) - len(priced)}, delisted_in_hold {int(priced.delisted_in_hold.sum())}")
    wk = pd.to_datetime(priced.day_ms, unit="ms", utc=True).dt.isocalendar()
    priced["week"] = (wk.year * 100 + wk.week).values
    for m, c in COST.items():
        priced[f"net{m}x"] = priced.gross - c
    priced = priced.sort_values(["day_ms", "perp"]).reset_index(drop=True)
    x = priced.net1x.values
    res = {"primary": {f"{m}x": summarize(priced[f"net{m}x"], priced.week) for m in COST}}

    # G2: matched random-date null (same perp, random admissible day)
    kept = ev.groupby("perp").day_ms.apply(lambda v: np.sort(v.values)).to_dict()
    d0, d1 = panel.ms(FIRST_D), panel.ms(LAST_D)
    days = np.arange(d0, d1 + 1, DAYH * H, dtype=np.int64)
    cand = {}
    for s in priced.perp.unique():
        k = kept[s]
        far = np.abs(days[:, None] - k[None, :]).min(axis=1) > 14 * DAYH * H
        dd = px.row_close_of_day(days[far])
        g, _, _ = px.trade(col[s], dd - 7 * DAYH, dd)
        cand[s] = g[np.isfinite(g)] - COST[1]
    rng = np.random.default_rng(SEED)
    null = np.zeros(REPS)
    groups = priced.groupby("perp").indices
    for rep in range(REPS):
        tot = 0.0
        for s, ix in groups.items():
            c = cand[s]
            tot += c[rng.integers(0, len(c), len(ix))].sum()
        null[rep] = tot / len(priced)
    p_null = (1 + (null >= x.mean()).sum()) / (REPS + 1)
    np.savetxt(out / "null_means.csv", null, fmt="%.8f", header="mean net 1x per replication", comments="")
    res["null"] = {"reps": REPS, "seed": SEED, "mean_pct": float(null.mean() * 100), "p95_pct": float(np.quantile(null, 0.95) * 100),
                   "p": float(p_null), "admissible_days_min": int(min(len(c) for c in cand.values()))}

    half = len(priced) // 2
    h1, h2 = priced.net1x.iloc[:half], priced.net1x.iloc[half:]
    top3 = priced.groupby("perp").net1x.sum().nlargest(3).index.tolist()
    rest = priced[~priced.perp.isin(top3)]
    gates = {"G1_cluster_t_ge_2": res["primary"]["1x"]["week_cluster_t"] >= 2,
             "G2_null_p_lt_0.05": p_null < 0.05,
             "G3_both_halves_positive": bool(h1.mean() > 0 and h2.mean() > 0),
             "G4_positive_without_top3": bool(rest.net1x.mean() > 0)}
    res["gates"] = {k: bool(v) for k, v in gates.items()}
    res["gate_detail"] = {"half1_mean_pct": float(h1.mean() * 100), "half2_mean_pct": float(h2.mean() * 100),
                          "half_split_day": priced.day.iloc[half], "top3": top3,
                          "without_top3_mean_pct": float(rest.net1x.mean() * 100),
                          "G1_2x": bool(res["primary"]["2x"]["week_cluster_t"] >= 2),
                          "G1_3x": bool(res["primary"]["3x"]["week_cluster_t"] >= 2)}
    verdict = "REPLICATES" if all(gates.values()) else "NULL"

    w = priced.week
    lg = {"1_net_incl_funding": summarize(priced.net1x + priced.funding, w)}
    f = priced.frac_max_supply
    for name, mask in (("2_dose_1_2pct", f < 0.02), ("3_dose_2_5pct", (f >= 0.02) & (f < 0.05)), ("4_dose_ge_5pct", f >= 0.05)):
        lg[name] = summarize(priced.net1x[mask], w[mask])
    v = priced.V
    lg["5_V_ge_0.82"] = summarize(priced.net1x[v >= 0.82], w[v >= 0.82])
    lg["6_V_lt_0.82"] = summarize(priced.net1x[v < 0.82], w[v < 0.82])
    lg["6_V_missing"] = int(v.isna().sum())
    hb = priced.gross + priced.btc
    lg["7_btc_hedged_gross"] = summarize(hb, w)
    lg["7_btc_hedged_net_two_legs_1x"] = summarize(hb - 2 * COST[1], w)
    m30, mpost = priced.g30.notna(), priced.g_post.notna()
    lg["8_horizon_D-30_to_D_net1x"] = summarize(priced.g30[m30] - COST[1], w[m30])
    lg["9_horizon_D_to_D+7_net1x"] = summarize(priced.g_post[mpost] - COST[1], w[mpost])
    res["logged"] = lg
    ver = priced.check == "verified"
    res["robustness"] = {
        "verified_only": summarize(priced.net1x[ver], w[ver]),
        "unverified_only": summarize(priced.net1x[~ver], w[~ver]),
        "per_year": {y: summarize(g.net1x, g.week) for y, g in priced.groupby(priced.day.str[:4])},
        "worst_event": priced.loc[priced.net1x.idxmin(), ["day", "perp", "net1x"]].to_dict(),
        "best_event": priced.loc[priced.net1x.idxmax(), ["day", "perp", "net1x"]].to_dict(),
        "delisted_in_hold": int(priced.delisted_in_hold.sum()),
        "events_losing_over_40pct": int((priced.gross < -0.40).sum()),
        "funding_mean_pct": float(priced.funding.mean() * 100),
        "perps": int(priced.perp.nunique()), "weeks": int(priced.week.nunique()),
    }
    res["counts"] = {"candidates": int(len(prim)), "priced": int(len(priced)), "no_market": int(len(prim) - len(priced))}
    res["verdict"] = verdict
    res["trials"] = 10
    priced.drop(columns=["day_ms"]).to_csv(out / "events_priced.csv", index=False, float_format="%.6g")
    (out / "verdict.json").write_text(json.dumps(res, indent=1, default=float))
    log("primary", json.dumps(res["primary"]))
    log("null", json.dumps(res["null"]))
    log("gates", json.dumps(res["gates"]), json.dumps(res["gate_detail"]))
    log("logged", json.dumps(lg))
    log("robustness", json.dumps(res["robustness"], default=float))
    log("verdict", verdict)


if __name__ == "__main__":
    main()
