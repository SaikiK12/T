"""R267 delist_v1: the Binance delisting-notice short on the hourly archive (experiments/delist_v1/PREREG.md).

Verifies the frozen PREREG, checks the catalog, article and leg hashes, rebuilds legs.csv byte for byte, then prices
every leg: short at the close of the bar containing the notice (the first hourly open after it), cover +1 h and
+24 h later. One observation per notice cluster (notices in the same hourly bar). Gates G1-G4 on the primary.

usage: python scripts/run_delist.py   (about a minute)
"""
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
import delist_events  # noqa: E402

LANE = ROOT / "experiments" / "delist_v1"
UNTIL = "2026-10-20T17:00:00Z"
SHA = {"legs": "fbdfe6efc9a7bedebb66f1d465d6294b3764bc42ee6f3200f5ab4f537e51771e",
       "catalog_rows": "4711c4f6b6df02db045d0f53c5712bbd5a02edd31d06a0acf18d386251463d29",
       "articles": "f155ba8da5eacbf837ac763beb902494d8536cd5159779b6de1e6882bc1501a6"}
COST = {1: 0.004, 2: 0.008, 3: 0.012}            # round trip
BTC_COST = 0.0010                                # the hedge leg, round trip at 1x
HORIZONS = {"1h": 1, "24h": 24}
CRASH = {91745, 91819, 141460}                   # LUNA x2, FTT (2022)
REPS, SEED = 2000, 267
H = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check_inputs():
    cat = pd.read_csv(delist_events.SRC)
    cat = cat[cat.release_ms < int(pd.Timestamp(UNTIL).value // 10**6)].sort_values("id")
    got = {"catalog_rows": sha(cat[["id", "code", "title", "release_ms"]].to_csv(index=False).encode()),
           "legs": sha((LANE / "legs.csv").read_bytes())}
    h = hashlib.sha256()
    for i in cat.id:
        h.update(f"{i}\t{sha((delist_events.ARTICLES / f'{i}.txt').read_bytes())}\n".encode())
    got["articles"] = h.hexdigest()
    for k, v in SHA.items():
        if got[k] != v:
            raise SystemExit(f"input {k} changed: {got[k]} != frozen {v}")
    L, _ = delist_events.legs(until=UNTIL)
    with tempfile.TemporaryDirectory() as d:
        L.to_csv(Path(d) / "legs.csv", index=False)
        if (Path(d) / "legs.csv").read_bytes() != (LANE / "legs.csv").read_bytes():
            raise SystemExit("rebuilt legs.csv differs from the frozen file")
    log("inputs match the frozen hashes; legs rebuild byte for byte")


class Book:
    """Hourly closes, traded flags and settled funding for the legs' perps and BTC."""

    def __init__(self, p):
        self.t = p.t
        self.T = len(p.t)
        self.col = {s: i for i, s in enumerate(p.symbols)}
        self.close = np.asarray(p["close"], np.float64)
        self.traded = np.isfinite(self.close) & (np.nan_to_num(np.asarray(p["volume"], np.float64)) > 0)
        idx = np.where(self.traded, np.arange(self.T)[:, None], -1)
        self.last = np.maximum.accumulate(idx, axis=0)
        fe = np.nan_to_num(np.asarray(p["fund_event"], np.float64))
        self.cumf = np.vstack([np.zeros((1, fe.shape[1])), np.cumsum(fe, axis=0)])   # cumf[k] = sum fe[:k]

    def row(self, ms):
        return int((ms - self.t[0]) // H)

    def fund(self, s, r0, xr):
        """Settlements in (entry, exit]: fund_event rows r0+2 .. xr+1."""
        return self.cumf[xr + 2, s] - self.cumf[r0 + 2, s]

    def leg(self, s, r0, h):
        """Short from the close of r0 to the close of r0+h (last traded close at or before it). None if not tradable."""
        xr = r0 + h
        if r0 < 1 or xr + 1 >= self.T or not self.traded[r0, s]:
            return None
        jx = self.last[xr, s]
        entry, exit_ = self.close[r0, s], self.close[jx, s]
        return {"gross": -(exit_ / entry - 1), "funding": self.fund(s, r0, xr), "stale_exit": bool(jx < xr),
                "delisted_in_hold": bool(self.last[-1, s] < xr)}

    def long(self, s, r0, h):
        xr = r0 + h
        return self.close[xr, s] / self.close[r0, s] - 1, self.fund(s, r0, xr)


def cluster_obs(legs, net_col):
    """One observation per cluster: the mean net of its legs (one per perp)."""
    g = legs.groupby("cluster", sort=True)
    return pd.DataFrame({"t0": g.t0.min(), "obs": g[net_col].mean(), "legs": g.size()}).sort_values("t0")


def stats(obs):
    x = obs.obs.values
    n = len(x)
    if n < 2:
        return {"n": n}
    half = n // 2
    y25 = obs[obs.t0 >= panel.ms("2025-01-01")].obs
    return {"n": int(n), "legs": int(obs.legs.sum()), "mean_pct": float(x.mean() * 100),
            "median_pct": float(np.median(x) * 100), "hit": float((x > 0).mean()),
            "t": float(x.mean() / (x.std(ddof=1) / np.sqrt(n))) if x.std(ddof=1) > 0 else np.nan,
            "half1_pct": float(x[:half].mean() * 100), "half2_pct": float(x[half:].mean() * 100),
            "y2025_pct": float(y25.mean() * 100) if len(y25) else np.nan, "y2025_n": int(len(y25))}


def gates_g1_g3(s):
    return {"G1": bool(s.get("t", -np.inf) >= 2.40), "G2": bool(s.get("half1_pct", -1) > 0 and s.get("half2_pct", -1) > 0),
            "G3": bool(s.get("y2025_pct", -1) > 0)}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs()
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    L = pd.read_csv(LANE / "legs.csv")
    L = L[(L.window == "archive") & L.in_archive].copy()
    log(f"sample: {L.notice.nunique()} notices, {len(L)} legs on {L.perp.nunique()} perps")
    p = panel.load_panel(sorted(set(L.perp) | {"BTCUSDT"}))
    bk = Book(p)
    btc = bk.col["BTCUSDT"]

    L["r0"] = [bk.row(t) for t in L.release_ms]
    L["cluster"] = L.r0
    L = L.sort_values(["release_ms", "notice", "perp"]).drop_duplicates(["cluster", "perp"]).reset_index(drop=True)
    rows = []
    for r in L.itertuples():
        s = bk.col[r.perp]
        rec = {"no_market": True}
        for name, h in HORIZONS.items():
            x = bk.leg(s, r.r0, h)
            if x is None:
                break
            rec.update({"no_market": False, f"gross_{name}": x["gross"], f"funding_{name}": x["funding"],
                        f"stale_{name}": x["stale_exit"], f"delisted_{name}": x["delisted_in_hold"]})
            bret, bfund = bk.long(btc, r.r0, h)
            rec[f"btc_{name}"] = bret - bfund                      # the long pays +rate
        if not rec["no_market"] and bk.traded[r.r0 - 1, s]:
            rec["premove"] = -(bk.close[r.r0, s] / bk.close[r.r0 - 1, s] - 1)
        rows.append(rec)
    L = pd.concat([L, pd.DataFrame(rows, index=L.index)], axis=1)
    L["t0"] = L.release_ms
    no_mkt = int(L.no_market.sum())
    P = L[~L.no_market].copy()
    for name in HORIZONS:
        for m, c in COST.items():
            P[f"net_{name}_{m}x"] = P[f"gross_{name}"] + P[f"funding_{name}"] - c
            P[f"hedged_{name}_{m}x"] = P[f"net_{name}_{m}x"] + P[f"btc_{name}"] - BTC_COST * m
    log(f"priced legs {len(P)}, no_market {no_mkt}, clusters {P.cluster.nunique()}; "
        f"stale exits 1h {int(P.stale_1h.sum())} / 24h {int(P.stale_24h.sum())}, "
        f"delisted in 24h hold {int(P.delisted_24h.sum())}")
    P.to_csv(out / "legs_priced.csv", index=False)

    variants = {1: ("all", "1h", "net"), 2: ("all", "24h", "net"), 3: ("all", "1h", "hedged"),
                4: ("all", "24h", "hedged"), 5: ("spot", "1h", "net"), 6: ("futures", "1h", "net"),
                7: ("spot", "24h", "net"), 8: ("futures", "24h", "net")}
    res = {"variants": {}}
    for k, (kind, hz, line) in variants.items():
        sub = P if kind == "all" else P[P.kind == kind]
        v = {f"{m}x": stats(cluster_obs(sub, f"{line}_{hz}_{m}x")) for m in COST}
        v["gates_1x"] = gates_g1_g3(v["1x"])
        res["variants"][f"{k}: {kind} {hz} {line}"] = v
        s1 = v["1x"]
        log(f"V{k} {kind:7s} {hz:3s} {line:6s} n {s1['n']:3d} mean {s1['mean_pct']:+.2f}% t {s1['t']:.2f} "
            f"halves {s1['half1_pct']:+.2f}/{s1['half2_pct']:+.2f} 2025+ {s1['y2025_pct']:+.2f}% "
            f"(2x {v['2x']['mean_pct']:+.2f}%, 3x {v['3x']['mean_pct']:+.2f}%)")
    prim_obs = cluster_obs(P, "net_1h_1x")
    prim_obs.to_csv(out / "clusters_primary.csv")

    # G4: matched null, same hour of day on a random earlier day
    rng = np.random.default_rng(SEED)
    cand, kept = {}, []
    for c, g in P.groupby("cluster"):
        S = [bk.col[s] for s in g.perp]
        for kmax in (60, 180):
            vals = []
            for k in range(7, kmax + 1):
                r = c - 24 * k
                if r < 1 or not all(bk.traded[r, s] for s in S):
                    continue
                legs_ = [bk.leg(s, r, 1) for s in S]
                vals.append(np.mean([x["gross"] + x["funding"] - COST[1] for x in legs_]))
            if len(vals) >= 10:
                break
        if len(vals) >= 10:
            cand[c] = np.array(vals)
            kept.append(c)
    obs_null = prim_obs.loc[kept, "obs"].mean()
    null = np.array([np.mean([cand[c][rng.integers(len(cand[c]))] for c in kept]) for _ in range(REPS)])
    p_null = (1 + int((null >= obs_null).sum())) / (REPS + 1)
    pd.DataFrame({"null_mean": null}).to_csv(out / "null_means.csv", index=False)
    log(f"G4 null: {len(kept)}/{len(prim_obs)} clusters with >= 10 admissible days; observed {obs_null * 100:+.2f}%, "
        f"null mean {null.mean() * 100:+.2f}%, 95th pct {np.percentile(null, 95) * 100:+.2f}%, p {p_null:.4f}")

    prim = res["variants"]["1: all 1h net"]
    gates = dict(prim["gates_1x"], G4=bool(p_null < 0.05))
    verdict = "REPLICATES (gate 0)" if all(gates.values()) else "NULL"
    res.update({"verdict": verdict, "gates": gates,
                "null": {"clusters": len(kept), "observed_pct": obs_null * 100, "null_mean_pct": null.mean() * 100,
                         "null_p95_pct": float(np.percentile(null, 95) * 100), "p": p_null},
                "counts": {"sample_legs": int(len(L)), "priced_legs": int(len(P)), "no_market": no_mkt,
                           "clusters": int(P.cluster.nunique()), "stale_1h": int(P.stale_1h.sum()),
                           "stale_24h": int(P.stale_24h.sum()), "delisted_24h": int(P.delisted_24h.sum())}})

    # robustness, not counted
    rob = {}
    top3 = P.nlargest(3, "net_1h_1x").index
    rob["drop_top3_legs_1h"] = stats(cluster_obs(P.drop(top3), "net_1h_1x"))
    rob["drop_top3_legs_24h"] = stats(cluster_obs(P.drop(P.nlargest(3, "net_24h_1x").index), "net_24h_1x"))
    rob["no_crash_1h"] = stats(cluster_obs(P[~P.notice.isin(CRASH)], "net_1h_1x"))
    rob["no_crash_24h"] = stats(cluster_obs(P[~P.notice.isin(CRASH)], "net_24h_1x"))
    pm = P.dropna(subset=["premove"])
    rob["premove_short_sign"] = stats(cluster_obs(pm.assign(x=pm.premove), "x"))
    for name in HORIZONS:
        rob[f"gross_{name}"] = stats(cluster_obs(P, f"gross_{name}"))
        rob[f"funding_{name}_mean_pct"] = float(cluster_obs(P, f"funding_{name}").obs.mean() * 100)
    yr = {}
    for name in HORIZONS:
        o = cluster_obs(P, f"net_{name}_1x")
        o["year"] = pd.to_datetime(o.t0, unit="ms").dt.year
        yr[name] = {int(y): {"n": int(len(g)), "mean_pct": float(g.obs.mean() * 100)} for y, g in o.groupby("year")}
    rob["per_year"] = yr
    res["robustness"] = rob
    for k in ("drop_top3_legs_1h", "drop_top3_legs_24h", "no_crash_1h", "no_crash_24h", "premove_short_sign",
              "gross_1h", "gross_24h"):
        s = rob[k]
        log(f"rob {k:20s} n {s['n']:3d} mean {s['mean_pct']:+.2f}% t {s['t']:.2f}")
    log("per year", json.dumps(yr))
    log(f"VERDICT {verdict} gates {gates}")
    (out / "verdict.json").write_text(json.dumps(res, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
