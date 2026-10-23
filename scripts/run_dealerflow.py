"""dealerflow_v1 (R292): does dealer gamma estimated from Deribit taker flow (M308) explain the next UTC day's realized
volatility beyond a HAR base, and the sign of the next day's hourly return autocorrelation? As set out in
experiments/dealerflow_v1/PREREG.md. A mechanism check only: no trades, no PnL.

Each Deribit option trade carries the taker's side. An option's net taker buying since its first trade is the takers'
position in it; the makers hold the opposite, and reading the makers as dealers is the assumption under test. Dealer
gamma exposure at the close of UTC day d is
    GEX_d = sum over options alive after the close of (-taker position) x gamma x F^2 x 0.01   (USD per 1% move)
with gamma from Black-76 (lab/exposure.py) at the option's last traded IV and F the Binance perp's close. Scaled by the
perp's 30-day mean daily quote volume, g_d = GEX_d / ADV_d is the hedge flow a 1% move asks for, as a share of a day's
volume. Dealers long gamma (g > 0) sell rallies and buy dips, which should calm the next day (lower realized volatility,
negative hourly autocorrelation); short gamma (g < 0) chases the move.

usage: python scripts/run_dealerflow.py
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, exposure, prereg, stats  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_effratio import daily as path_daily  # noqa: E402
from scripts.run_vpin import load_bars  # noqa: E402

LANE = ROOT / "experiments" / "dealerflow_v1"
FLOW = data.ROOT / "deribit_trades"
PROVENANCE = ROOT / "docs" / "provenance" / "deribit_trades.json"
COINS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
HOUR, DAY = 3_600_000, 86_400_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)       # 2020 perp bars are reserved: dropped on load
T1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)       # exclusive
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
IV_DAYS = 7                          # an option's last traded IV is used for up to this many days
ADV_DAYS, ADV_NEED = 30, 20
DAY_BARS = 1200                      # valid 1-minute bars for a day's quote volume
HAR = ((5, 4), (22, 18))             # (days, needed) for the weekly and monthly HAR terms
NW_LAG = 5
T_MIN, MSE_MIN = 2.5, 0.01           # Bonferroni over 4 trials, two-sided 5%; at least 1% lower validation MSE
FEATURES = {"g": -1.0, "short": 1.0}  # predicted sign: on next-day log RV and on next-day hourly autocorrelation
TRIALS = 2 * len(FEATURES)           # 4: two features x two targets
VARIANTS = ("ex_blocks", "ex_24h")   # reported only
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- flow
def load_flow(cur, root=FLOW, hashes=None):
    """Every hourly flow row of one currency (scripts/fetch_deribit_trades.py). With `hashes` (path relative to
    `root` -> sha256, from the provenance record), each file must still hash to its recorded value."""
    parts = []
    for p in sorted((root / cur / "flow").glob("*.parquet")):
        if hashes is not None:
            rel = p.relative_to(root).as_posix()
            if hashes.get(rel) != prereg.sha256_file(p):
                raise prereg.PreregError(f"{rel}: not in the provenance record, or changed since it")
        f = pd.read_parquet(p, columns=["t", "instrument", "expiry_ms", "strike", "cp", "buy", "sell",
                                        "block_buy", "block_sell", "iv"])
        if len(f):
            parts.append(f)
    f = pd.concat(parts, ignore_index=True)
    f["instrument"] = f.instrument.astype("category")
    return f


def daily_grid(flow, d_last):
    """One row per (option, day D) for every day D from the option's first trade to the last close before its expiry
    (and at most d_last), D in days since the epoch. Columns: the takers' net position at the close of D (all trades,
    and without block trades), the IV used for D (percent: the option's last traded IV within IV_DAYS days, else the
    median of those IVs over the same expiry on D), strike, call, expiry_ms. Only trades in hours that end by the
    close of D count."""
    f = flow.assign(day=flow.t // DAY, net=flow.buy - flow.sell,
                    net_ex=(flow.buy - flow.sell) - (flow.block_buy - flow.block_sell))
    code = f.instrument.cat.codes.to_numpy(np.int64)
    f = f.assign(code=code)
    g = f.groupby(["code", "day"], sort=True).agg(net=("net", "sum"), net_ex=("net_ex", "sum"))
    g[["pos", "pos_ex"]] = g.groupby(level=0)[["net", "net_ex"]].cumsum()
    g = g.reset_index()
    ivr = f[np.isfinite(f.iv) & (f.iv > 0)].sort_values(["code", "t"]).groupby(["code", "day"]).iv.last().reset_index()
    meta = f.groupby("code").agg(expiry_ms=("expiry_ms", "first"), strike=("strike", "first"), cp=("cp", "first"),
                                 first=("day", "min"))
    last = np.minimum(meta.expiry_ms.to_numpy() // DAY - 1, d_last)          # live after the close of D: D <= E - 1
    n = np.clip(last - meta["first"].to_numpy() + 1, 0, None)
    codes = np.repeat(meta.index.to_numpy(), n)
    start = np.repeat(meta["first"].to_numpy(), n)
    off = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
    days = start + off
    big = np.int64(1) << 32
    key = codes * big + days
    gk = g.code.to_numpy(np.int64) * big + g.day.to_numpy(np.int64)
    j = np.searchsorted(gk, key, side="right") - 1                            # last trading day <= D, same option
    out = pd.DataFrame({"code": codes, "day": days, "pos": g.pos.to_numpy()[j], "pos_ex": g.pos_ex.to_numpy()[j]})
    ik = ivr.code.to_numpy(np.int64) * big + ivr.day.to_numpy(np.int64)
    k = np.searchsorted(ik, key, side="right") - 1
    kk = np.clip(k, 0, None)
    ok = (k >= 0) & (ivr.code.to_numpy(np.int64)[kk] == codes) & (ivr.day.to_numpy(np.int64)[kk] >= days - IV_DAYS + 1)
    out["iv_own"] = np.where(ok, ivr.iv.to_numpy()[kk], np.nan)
    m = meta.loc[codes]
    out["expiry_ms"], out["strike"] = m.expiry_ms.to_numpy(), m.strike.to_numpy()
    out["call"] = (m.cp.to_numpy() == "C")
    med = out.groupby(["expiry_ms", "day"]).iv_own.transform("median")
    out["iv"] = out.iv_own.fillna(med)
    return out


def gex_daily(grid, close_by_day):
    """Dealer GEX per day (USD per 1% move) from daily_grid() rows and the perp close at each day's end (a Series
    indexed by day), with the variants: without block trades, and without options expiring within 24 hours. Also the
    share of open interest (|position|, coins) dropped for want of an IV."""
    x = grid[grid.day.isin(close_by_day.index)]
    F = close_by_day.reindex(x.day).to_numpy()
    T = (x.expiry_ms.to_numpy() - (x.day.to_numpy() + 1) * DAY) / exposure.YEAR_MS
    gam = exposure.greeks(F, x.strike.to_numpy(), T, x.iv.to_numpy() / 100, x.call.to_numpy()).gamma.to_numpy()
    unit = gam * F * F * 0.01
    ok = np.isfinite(unit)
    d = pd.DataFrame({"day": x.day.to_numpy(), "gex": np.where(ok, -x.pos.to_numpy() * unit, 0.0),
                      "gex_ex_blocks": np.where(ok, -x.pos_ex.to_numpy() * unit, 0.0),
                      "abs_pos": np.abs(x.pos.to_numpy()), "dropped": np.where(ok, 0.0, np.abs(x.pos.to_numpy()))})
    d["gex_ex_24h"] = np.where(T * exposure.YEAR_MS > DAY, d.gex, 0.0)
    s = d.groupby("day").sum()
    s["dropped_share"] = s.dropped / s.abs_pos.where(s.abs_pos > 0)
    return s[["gex", "gex_ex_blocks", "gex_ex_24h", "dropped_share"]]


# ----------------------------------------------------------------------------------------------------------- perp
def perp_daily(bars, t0=T0):
    """Per UTC day of the perp: realized variance of the 5-minute path (scripts/run_effratio.daily), the close, the
    day's quote volume (at least DAY_BARS valid bars) and the hourly autocorrelation ac = sum r_h r_(h-1) / sum r_h^2
    over the day's 24 hourly log returns (all 24 needed; r_1 runs from the previous day's last close)."""
    C = bars["close"]
    d = path_daily(C, t0=t0)
    nd = len(d)
    q = bars["quote_volume"][: nd * 1440].reshape(nd, 1440)
    d["qv"] = np.where(np.isfinite(q).sum(1) >= DAY_BARS, np.nansum(q, 1), np.nan)
    M = C[: nd * 1440].reshape(nd, 1440)
    P = np.column_stack([np.r_[np.nan, M[:-1, -1]], M[:, 59::60]])            # P(00:00), P(01:00) .. P(24:00)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.diff(np.log(P), axis=1)
        num = np.sum(r[:, 1:] * r[:, :-1], 1)
        den = np.sum(r ** 2, 1)
        d["ac"] = np.where(np.isfinite(r).all(1) & (den > 0), num / den, np.nan)
    d["var"] = d.rv ** 2
    d["day"] = d.t // DAY
    return d


def _log(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(np.where(x > 0, x, np.nan))


def frame(perp, gex):
    """One row per day D: features known at D's close, targets on D + 1."""
    v = pd.Series(perp["var"].to_numpy())
    f = pd.DataFrame({"day": perp.day.to_numpy(), "t": perp.t.to_numpy()})
    f["lv1"] = _log(v.to_numpy())
    for n, need in HAR:
        f[f"lv{n}"] = _log(v.rolling(n, min_periods=need).mean().to_numpy())
    adv = pd.Series(perp.qv.to_numpy()).rolling(ADV_DAYS, min_periods=ADV_NEED).mean().to_numpy()
    gx = gex.reindex(f.day)
    for c in ("gex", "gex_ex_blocks", "gex_ex_24h"):
        f[c] = gx[c].to_numpy()
    f["dropped_share"] = gx.dropped_share.to_numpy()
    f["adv"] = adv
    f["g"] = f.gex / adv
    f["g_ex_blocks"] = f.gex_ex_blocks / adv
    f["g_ex_24h"] = f.gex_ex_24h / adv
    f["short"] = np.where(np.isfinite(f.g), (f.gex < 0).astype(float), np.nan)
    f["short_ex_blocks"] = np.where(np.isfinite(f.g_ex_blocks), (f.gex_ex_blocks < 0).astype(float), np.nan)
    f["short_ex_24h"] = np.where(np.isfinite(f.g_ex_24h), (f.gex_ex_24h < 0).astype(float), np.nan)
    f["y"] = np.r_[f.lv1.to_numpy()[1:], np.nan]
    f["ac_next"] = np.r_[perp.ac.to_numpy()[1:], np.nan]
    f["wk_next"] = (pd.to_datetime((f.day + 1) * DAY, unit="ms").dt.dayofweek >= 5).astype(float).to_numpy()
    return f


def window_of(day):
    """'disc', 'valid' or '' per row, by the target day D + 1."""
    out = np.full(len(day), "", dtype=object)
    for name, (a, b) in (("disc", DISC), ("valid", VALID)):
        lo, hi = (pd.Timestamp(a, tz="UTC").value // 10**6) // DAY, (pd.Timestamp(b, tz="UTC").value // 10**6) // DAY
        out[(day + 1 >= lo) & (day + 1 <= hi)] = name
    return out


# ------------------------------------------------------------------------------------------------------ inference
def _ols(X, y, m):
    b = np.linalg.lstsq(X[m], y[m], rcond=None)[0]
    return b, y - X @ b


def vol_test(frames, feat):
    """HAR (log RV today, 5-day and 22-day means, weekend) against HAR + feat, fitted per coin on discovery and read
    on validation. Diebold-Mariano: Newey-West t of the per-day mean (across coins) of e_HAR^2 - e_feat^2."""
    per, dd, sse = {}, [], [0.0, 0.0]
    for coin, f in frames.items():
        w = window_of(f.day.to_numpy())
        X0 = np.column_stack([np.ones(len(f)), f.lv1, f.lv5, f.lv22, f.wk_next])
        X1 = np.column_stack([X0, f[feat]])
        y = f.y.to_numpy()
        good = np.isfinite(y) & np.isfinite(X1).all(1)
        md, mv = good & (w == "disc"), good & (w == "valid")
        b0, e0 = _ols(X0, y, md)
        b1, e1 = _ols(X1, y, md)
        per[coin] = {"rows_disc": int(md.sum()), "rows_valid": int(mv.sum()), "coef_disc": float(b1[-1]),
                     "mse_cut_valid": float(1 - np.sum(e1[mv] ** 2) / np.sum(e0[mv] ** 2)),
                     "r2_valid_har": float(1 - np.mean(e0[mv] ** 2) / np.var(y[mv]))}
        dd.append(pd.Series(np.where(mv, e0 ** 2 - e1 ** 2, np.nan), index=f.day.to_numpy()))
        sse[0] += float(np.sum(e0[mv] ** 2))
        sse[1] += float(np.sum(e1[mv] ** 2))
    x = pd.concat(dd, axis=1).mean(axis=1, skipna=True).dropna().to_numpy()
    n, mu, t = stats.newey_west_t(x, NW_LAG)
    return {"per_coin": per, "dm_t": float(t), "days_valid": int(n), "mse_cut": 1 - sse[1] / sse[0] if sse[0] else np.nan}


def ac_t(frames, feat, window):
    """Within one window: the Newey-West t of the per-day sum over coins of (feat - its coin mean) x (next-day ac -
    its coin mean), and the pooled slope of ac on feat with coin fixed effects."""
    z, sxx, sxy = [], 0.0, 0.0
    for f in frames.values():
        m = (window_of(f.day.to_numpy()) == window) & np.isfinite(f[feat]) & np.isfinite(f.ac_next)
        x = f[feat].to_numpy()[m] - np.mean(f[feat].to_numpy()[m])
        y = f.ac_next.to_numpy()[m] - np.mean(f.ac_next.to_numpy()[m])
        z.append(pd.Series(x * y, index=f.day.to_numpy()[m]))
        sxx, sxy = sxx + float(np.sum(x * x)), sxy + float(np.sum(x * y))
    s = pd.concat(z, axis=1).sum(axis=1, min_count=1).dropna().to_numpy()
    n, mu, t = stats.newey_west_t(s, NW_LAG)
    return {"t": float(t), "slope": sxy / sxx if sxx else np.nan, "days": int(n)}


def terciles(frames, feat):
    """Mean next-day HAR residual (validation forecast error of the discovery HAR fit) and next-day ac by tercile of
    feat, cuts from discovery, pooled over coins (reported only)."""
    rows = {w: {k: [] for k in ("res", "ac")} for w in ("disc", "valid")}
    for f in frames.values():
        w = window_of(f.day.to_numpy())
        X0 = np.column_stack([np.ones(len(f)), f.lv1, f.lv5, f.lv22, f.wk_next])
        y = f.y.to_numpy()
        good = np.isfinite(y) & np.isfinite(X0).all(1) & np.isfinite(f[feat])
        b0, e0 = _ols(X0, y, good & (w == "disc"))
        x = f[feat].to_numpy()
        cuts = np.nanquantile(x[good & (w == "disc")], [1 / 3, 2 / 3]) if feat != "short" else [0.5, 0.5]
        ter = np.searchsorted(cuts, x, side="right")
        for name in rows:
            m = good & (w == name)
            rows[name]["res"].append(pd.DataFrame({"ter": ter[m], "v": e0[m]}))
            m2 = m & np.isfinite(f.ac_next)
            rows[name]["ac"].append(pd.DataFrame({"ter": ter[m2], "v": f.ac_next.to_numpy()[m2]}))
    out = {}
    for name, r in rows.items():
        for k, parts in r.items():
            g = pd.concat(parts).groupby("ter").v.agg(["mean", "count"])
            out[f"{k}_{name}"] = {int(i): {"mean": round(float(a), 4), "n": int(b)} for i, (a, b) in g.iterrows()}
    return out


def analyze(frames):
    tests, passes = {}, {}
    for feat, sign in FEATURES.items():
        v = vol_test(frames, feat)
        v["coef_sign_ok"] = bool(all(np.sign(p["coef_disc"]) == sign for p in v["per_coin"].values()))
        v["pass"] = bool(v["dm_t"] >= T_MIN and v["mse_cut"] >= MSE_MIN and v["coef_sign_ok"])
        a = {w: ac_t(frames, feat, w) for w in ("disc", "valid")}
        a["pass"] = bool(np.sign(a["valid"]["t"]) == sign and abs(a["valid"]["t"]) >= T_MIN
                         and np.sign(a["disc"]["t"]) == sign)
        tests[feat] = {"vol": v, "ac": a, "terciles": terciles(frames, feat)}
        passes[f"vol_{feat}"], passes[f"ac_{feat}"] = v["pass"], a["pass"]
    variants = {}
    for var in VARIANTS:
        for feat in FEATURES:
            name = f"{feat}_{var}"
            v = vol_test(frames, name)
            variants[name] = {"vol_dm_t": v["dm_t"], "vol_mse_cut": v["mse_cut"],
                              "vol_coef_disc": {c: p["coef_disc"] for c, p in v["per_coin"].items()},
                              "ac_t_disc": ac_t(frames, name, "disc")["t"], "ac_t_valid": ac_t(frames, name, "valid")["t"]}
    desc = {}
    for coin, f in frames.items():
        w = window_of(f.day.to_numpy())
        for name in ("disc", "valid"):
            m = (w == name) & np.isfinite(f.g)
            desc[f"{coin}_{name}"] = {
                "days": int(m.sum()), "short_share": float(f.short[m].mean()),
                "gex_musd_q10_50_90": [round(float(q) / 1e6, 2) for q in np.nanquantile(f.gex[m], [0.1, 0.5, 0.9])],
                "g_q10_50_90": [round(float(q), 5) for q in np.nanquantile(f.g[m], [0.1, 0.5, 0.9])],
                "corr_g_lv1": float(np.corrcoef(f.g[m & np.isfinite(f.lv1)], f.lv1[m & np.isfinite(f.lv1)])[0, 1]),
                "dropped_share_mean": float(np.nanmean(f.dropped_share[m]))}
    found = [k for k, p in passes.items() if p]
    return {"verdict": "PARTIAL" if found else "NULL", "passes": passes, "found": found, "tests": tests,
            "variants": variants, "describe": desc}


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    hashes = {h["path"]: h["sha256"] for h in json.loads(PROVENANCE.read_text())["file_hashes"]}
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    frames = {}
    for cur, sym in COINS.items():
        perp = perp_daily(load_bars(data.ROOT / "klines_1m" / f"{sym}.parquet"))
        flow = load_flow(cur, hashes=hashes)
        iv_med = float(np.nanmedian(flow.iv[(flow.t >= T0) & (flow.t < T1)]))
        if not 10 <= iv_med <= 300:
            raise SystemExit(f"{cur}: median traded IV {iv_med:.2f} is not in percent; the unit is wrong")
        grid = daily_grid(flow, int(perp.day.max()))
        close = pd.Series(perp.close.to_numpy(), index=perp.day.to_numpy()).dropna()
        gex = gex_daily(grid, close)
        frames[cur] = frame(perp, gex)
        log(f"{cur}: {len(flow)} flow rows, {grid.code.nunique()} options, {len(gex)} GEX days, "
            f"{np.isfinite(frames[cur].g).sum()} days with g")
        del flow, grid
    res = analyze(frames)
    for feat in FEATURES:
        t = res["tests"][feat]
        log(f"{feat}: vol DM t {t['vol']['dm_t']:.2f}, MSE cut {100 * t['vol']['mse_cut']:.2f}%, coef "
            + ", ".join(f"{c} {p['coef_disc']:+.4f}" for c, p in t["vol"]["per_coin"].items())
            + f"; ac t disc {t['ac']['disc']['t']:+.2f} valid {t['ac']['valid']['t']:+.2f}")
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    keep = ["day", "lv1", "lv5", "lv22", "gex", "g", "short", "g_ex_blocks", "g_ex_24h", "dropped_share", "y",
            "ac_next"]
    pd.concat([f[keep].assign(coin=c, window=window_of(f.day.to_numpy())) for c, f in frames.items()]).to_csv(
        out / "daily.csv", index=False, float_format="%.6g")
    summary = {"rid": "R292", "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, **res}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {res['verdict']}: {res['found'] or 'no mechanism'}")
    return summary


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        main()
