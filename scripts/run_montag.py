"""R269 montag_v1: short the perps of coins Binance adds to its Monitoring Tag (experiments/montag_v1/PREREG.md).

Verifies the frozen PREREG, checks the catalog and leg hashes, rebuilds legs.csv byte for byte, then prices every tag
leg with R267's rules (scripts/run_delist.py): short at the first hourly open after the notice, cover +1 h / +24 h /
+72 h. One observation per notice cluster. Gates G1-G4 on the primary (+1 h, unhedged, 1x).

usage: python scripts/run_montag.py   (under a minute)
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import panel, prereg  # noqa: E402
import montag_events  # noqa: E402
from run_delist import BTC_COST, COST, Book, cluster_obs, log, sha, stats  # noqa: E402

LANE = ROOT / "experiments" / "montag_v1"
SHA = {"legs": "771a8a3a4d06e0e13c77d97a35bd506aed6caacb7499415b8b6740ce1a9d9057",
       "catalog_rows": "00630318fed1b32268ba4212bbe22a707f2d6506a483d9015208200c8c43a8d9"}
HORIZONS = {"1h": 1, "24h": 24, "72h": 72}
REPS, SEED = 2000, 269


def check_inputs():
    cat = pd.concat([pd.read_csv(p) for p in montag_events.SRC]).drop_duplicates("id").sort_values("id")
    cat = cat[cat.release_ms < int(pd.Timestamp(montag_events.UNTIL).value // 10**6)]
    got = {"catalog_rows": sha(cat[["id", "code", "title", "release_ms"]].to_csv(index=False).encode()),
           "legs": sha((LANE / "legs.csv").read_bytes())}
    for k, v in SHA.items():
        if got[k] != v:
            raise SystemExit(f"input {k} changed: {got[k]} != frozen {v}")
    with tempfile.TemporaryDirectory() as d:
        montag_events.legs().to_csv(Path(d) / "legs.csv", index=False)
        if (Path(d) / "legs.csv").read_bytes() != (LANE / "legs.csv").read_bytes():
            raise SystemExit("rebuilt legs.csv differs from the frozen file")
    log("inputs match the frozen hashes; legs rebuild byte for byte")


def price(L, bk, btc):
    """Per-leg gross, funding, flags and the BTC long over the same rows, for every horizon."""
    L = L.copy()
    L["r0"] = [bk.row(t) for t in L.release_ms]
    L["cluster"] = L.r0
    L["t0"] = L.release_ms
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
            rec[f"btc_{name}"] = bret - bfund
        if not rec["no_market"] and bk.traded[r.r0 - 1, s]:
            rec["premove"] = -(bk.close[r.r0, s] / bk.close[r.r0 - 1, s] - 1)
        rows.append(rec)
    return pd.concat([L, pd.DataFrame(rows, index=L.index)], axis=1)


def gates_g1_g3(s):
    return {"G1": bool(s.get("t", -np.inf) >= 2.0), "G2": bool(s.get("half1_pct", -1) > 0 and s.get("half2_pct", -1) > 0),
            "G3": bool(s.get("y2025_pct", -1) > 0)}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    check_inputs()
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    A = pd.read_csv(LANE / "legs.csv")
    A = A[(A.window == "archive") & A.in_archive].copy()
    p = panel.load_panel(sorted(set(A.perp) | {"BTCUSDT"}))
    bk = Book(p)
    btc = bk.col["BTCUSDT"]
    L = price(A[A.kind == "tag"], bk, btc)
    log(f"tag sample: {L.notice.nunique()} notices, {len(L)} legs")
    P = L[~L.no_market].copy()
    for name in HORIZONS:
        for m, c in COST.items():
            P[f"net_{name}_{m}x"] = P[f"gross_{name}"] + P[f"funding_{name}"] - c
            P[f"hedged_{name}_{m}x"] = P[f"net_{name}_{m}x"] + P[f"btc_{name}"] - BTC_COST * m
    log(f"priced legs {len(P)}, no_market {int(L.no_market.sum())}, clusters {P.cluster.nunique()}; stale exits "
        + ", ".join(f"{n} {int(P[f'stale_{n}'].sum())}" for n in HORIZONS)
        + "; delisted in hold " + ", ".join(f"{n} {int(P[f'delisted_{n}'].sum())}" for n in HORIZONS))
    P.to_csv(out / "legs_priced.csv", index=False)

    variants = {1: ("1h", "net"), 2: ("24h", "net"), 3: ("72h", "net"), 4: ("1h", "hedged"), 5: ("24h", "hedged"),
                6: ("72h", "hedged")}
    res = {"variants": {}}
    for k, (hz, line) in variants.items():
        v = {f"{m}x": stats(cluster_obs(P, f"{line}_{hz}_{m}x")) for m in COST}
        v["gates_1x"] = gates_g1_g3(v["1x"])
        res["variants"][f"{k}: tag {hz} {line}"] = v
        s1 = v["1x"]
        log(f"V{k} {hz:3s} {line:6s} n {s1['n']:3d} mean {s1['mean_pct']:+.2f}% med {s1['median_pct']:+.2f}% "
            f"t {s1['t']:.2f} halves {s1['half1_pct']:+.2f}/{s1['half2_pct']:+.2f} 2025+ {s1['y2025_pct']:+.2f}% "
            f"(2x {v['2x']['mean_pct']:+.2f}%, 3x {v['3x']['mean_pct']:+.2f}%)")
    prim_obs = cluster_obs(P, "net_1h_1x")
    prim_obs.to_csv(out / "clusters_primary.csv")

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
                vals.append(np.mean([x["gross"] + x["funding"] - COST[1] for x in (bk.leg(s, r, 1) for s in S)]))
            if len(vals) >= 10:
                break
        if len(vals) >= 10:
            cand[c] = np.array(vals)
            kept.append(c)
    obs_null = prim_obs.loc[kept, "obs"].mean()
    null = np.array([np.mean([cand[c][rng.integers(len(cand[c]))] for c in kept]) for _ in range(REPS)])
    p_null = (1 + int((null >= obs_null).sum())) / (REPS + 1)
    pd.DataFrame({"null_mean": null}).to_csv(out / "null_means.csv", index=False)
    log(f"G4 null: {len(kept)}/{len(prim_obs)} clusters; observed {obs_null * 100:+.2f}%, null mean "
        f"{null.mean() * 100:+.2f}%, 95th pct {np.percentile(null, 95) * 100:+.2f}%, p {p_null:.4f}")

    gates = dict(res["variants"]["1: tag 1h net"]["gates_1x"], G4=bool(p_null < 0.05))
    verdict = "PASS (gate 0)" if all(gates.values()) else "NULL"
    res.update({"verdict": verdict, "gates": gates,
                "null": {"clusters": len(kept), "observed_pct": obs_null * 100, "null_mean_pct": null.mean() * 100,
                         "null_p95_pct": float(np.percentile(null, 95) * 100), "p": p_null},
                "counts": {"sample_legs": int(len(L)), "priced_legs": int(len(P)), "no_market": int(L.no_market.sum()),
                           "clusters": int(P.cluster.nunique())}})

    rob = {}
    for name in HORIZONS:
        col = f"net_{name}_1x"
        rob[f"drop_top3_legs_{name}"] = stats(cluster_obs(P.drop(P.nlargest(3, col).index), col))
        rob[f"gross_{name}"] = stats(cluster_obs(P, f"gross_{name}"))
        rob[f"funding_{name}_mean_pct"] = float(cluster_obs(P, f"funding_{name}").obs.mean() * 100)
        o = cluster_obs(P, col)
        o["year"] = pd.to_datetime(o.t0, unit="ms").dt.year
        rob[f"per_year_{name}"] = {int(y): {"n": int(len(g)), "mean_pct": float(g.obs.mean() * 100)}
                                   for y, g in o.groupby("year")}
    pm = P.dropna(subset=["premove"])
    rob["premove_short_sign"] = stats(cluster_obs(pm.assign(x=pm.premove), "x"))
    U = price(A[A.kind == "untag"], bk, btc)
    U = U[~U.no_market]
    rob["untag_long"] = {name: {"n_notices": int(U.notice.nunique()), "legs": int(len(U)),
                                "mean_gross_long_pct": float(-cluster_obs(U, f"gross_{name}").obs.mean() * 100)}
                         for name in HORIZONS} if len(U) else {}
    res["robustness"] = rob
    for k in ("drop_top3_legs_1h", "drop_top3_legs_24h", "drop_top3_legs_72h", "gross_1h", "gross_24h", "gross_72h",
              "premove_short_sign"):
        s = rob[k]
        log(f"rob {k:20s} n {s['n']:3d} mean {s['mean_pct']:+.2f}% t {s['t']:.2f}")
    log("per year 1h", json.dumps(rob["per_year_1h"]))
    log("per year 24h", json.dumps(rob["per_year_24h"]))
    log("untag long", json.dumps(rob["untag_long"]))
    log(f"VERDICT {verdict} gates {gates}")
    (out / "verdict.json").write_text(json.dumps(res, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
