"""clockflow_v1 (R289): fixed-clock flows on 1-minute bars of the BTC, ETH and SOL perps, as set out in
experiments/clockflow_v1/PREREG.md. OPEN (M301) fades or follows the first minutes after the US cash open; SETTLE
(M303) fades or follows the 07:30-08:00 UTC move of Deribit's settlement window on expiry Fridays. 40 variants, a White
reality check per sub-family on 2021-04..2023 and each selected variant read on 2024-01..2026-09.

usage: python scripts/run_clockflow.py
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg, stats  # noqa: E402
from lab.sessions import NYSEHolidays  # noqa: E402

LANE = ROOT / "experiments" / "clockflow_v1"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
MIN = 60_000
DAY = 86_400_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)       # 2020 is reserved: dropped on load
T1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)       # exclusive
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
HALVES = (("2024-01-01", "2025-06-30"), ("2025-07-01", "2026-09-30"))
COST, API = 3e-4, 8.5e-4                                            # per side: manual web at 1x, API (reported)
LOOK, NEED = 60, 40                                                 # sigma: last 60 days of the set, 40 defined
RC_B, RC_BLOCK = 2000, 10
SEEDS = {"OPEN": 289, "SETTLE": 2890}
TRIALS = 40
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- inputs
def check_inputs(prereg_path, root=ROOT):
    """Every file in the PREREG's inputs block must still hash to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    shas = {}
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
        shas[rel] = got
    return shas


def load_prices(path, t0=T0, t1=T1):
    """P[i] = price at the instant t0 + i minutes: the close of the valid bar that opens one minute earlier."""
    k = pd.read_parquet(path, columns=["t", "close", "count"])
    k = k[(k.t >= t0) & (k.t < t1)].drop_duplicates("t")
    k = k[(k["count"] > 0) & (k.close > 0)]
    P = np.full((t1 - t0) // MIN + 1, np.nan)
    P[(k.t.values - t0) // MIN + 1] = k.close.values
    return P


def load_funding(path):
    f = pd.read_parquet(path, columns=["t", "rate"]).sort_values("t")
    return np.rint(f.t.values / MIN).astype(np.int64) * MIN, f.rate.values.astype(float)


def price(P, tau, t0=T0):
    i = (np.asarray(tau, np.int64) - t0) // MIN
    ok = (i >= 0) & (i < len(P))
    return np.where(ok, P[np.clip(i, 0, len(P) - 1)], np.nan)


def funding_paid(F, rate, side, entry, exit_):
    """side x the rates settled at F with entry < F <= exit, per trade."""
    lo = np.searchsorted(F, entry, side="right")
    hi = np.searchsorted(F, exit_, side="right")
    c = np.concatenate([[0.0], np.cumsum(rate)])
    return side * (c[hi] - c[lo])


# ------------------------------------------------------------------------------------------------------------ rules
def local_ms(days, hh, mm, tz):
    """UTC ms of hh:mm local time in tz on each calendar day (daylight saving followed)."""
    ts = pd.to_datetime(days) + pd.Timedelta(hours=hh, minutes=mm)
    return ts.tz_localize(tz).tz_convert("UTC").as_unit("ms").asi8.astype(np.int64)


def sigma(m, look=LOOK, need=NEED):
    """sd (ddof 1) of the defined m over the `look` earlier entries of the same day set; NaN below `need`."""
    out = np.full(len(m), np.nan)
    for i in range(len(m)):
        x = m[max(0, i - look):i]
        x = x[~np.isnan(x)]
        if len(x) >= need:
            out[i] = x.std(ddof=1)
    return out


def trades(P, F, rate, starts, w, sig, k, side, h, mask=None, t0=T0):
    """One coin's trades for one variant: start, m, sigma, side, entry/exit prices, gross and funding."""
    m = price(P, starts + w * MIN, t0) / price(P, starts, t0) - 1
    with np.errstate(invalid="ignore"):
        go = ~np.isnan(m) & ~np.isnan(sig) & (m != 0) & (np.abs(m) >= k * sig)
    if mask is not None:
        go &= mask
    s = np.sign(m) * (1 if side == "follow" else -1)
    entry = starts + (w + 1) * MIN
    exit_ = entry + h * MIN
    E, X = price(P, entry, t0), price(P, exit_, t0)
    go &= ~np.isnan(E) & ~np.isnan(X)
    i = np.flatnonzero(go)
    gross = s[i] * (X[i] / E[i] - 1)
    fund = funding_paid(F, rate, s[i], entry[i], exit_[i])
    return pd.DataFrame({"start": starts[i], "m": m[i], "sigma": sig[i], "side": s[i], "E": E[i], "X": X[i],
                         "gross": gross, "funding": fund})


def clocks(t0=T0, t1=T1):
    """The day sets and window starts of every rule and placebo."""
    days = pd.date_range(pd.to_datetime(t0, unit="ms"), pd.to_datetime(t1 - DAY, unit="ms"), freq="D")
    hol = NYSEHolidays().holidays(days.min(), days.max())
    trading = (days.weekday < 5) & ~days.isin(hol)
    month_end = days + pd.offsets.MonthEnd(0)
    last_fri = month_end - pd.to_timedelta((month_end.weekday - 4) % 7, unit="D")
    utc0730 = days.as_unit("ms").asi8.astype(np.int64) + (7 * 60 + 30) * MIN
    return {
        "OPEN": (days[trading], local_ms(days[trading], 9, 30, "America/New_York"), None),
        "OPEN_1030": (days[trading], local_ms(days[trading], 10, 30, "America/New_York"), None),
        "OPEN_OFF": (days[~trading], local_ms(days[~trading], 9, 30, "America/New_York"), None),
        "SETTLE_weekly": (days, utc0730, np.asarray(days.weekday == 4)),
        "SETTLE_monthly": (days, utc0730, np.asarray(days == last_fri)),
        "SETTLE_monthu": (days, utc0730, np.asarray(days.weekday < 4)),
    }


def variants():
    out = []
    for w in (5, 15, 30):
        for k in (1, 2):
            for side in ("fade", "follow"):
                for h in (60, 120):
                    out.append({"family": "OPEN", "clock": "OPEN", "w": w, "k": k, "side": side, "h": h})
    for dset in ("weekly", "monthly"):
        for k in (0, 1):
            for side in ("fade", "follow"):
                for h in (60, 120):
                    out.append({"family": "SETTLE", "clock": f"SETTLE_{dset}", "w": 30, "k": k, "side": side, "h": h})
    assert len(out) == TRIALS
    return out


def name_of(v):
    return f"{v['clock']}_w{v['w']}_k{v['k']}_{v['side']}_h{v['h']}"


def placebo_of(v):
    if v["family"] == "OPEN":
        return [dict(v, clock="OPEN_1030"), dict(v, clock="OPEN_OFF")]
    return [dict(v, clock="SETTLE_monthu")] if v["clock"] == "SETTLE_weekly" else []


# --------------------------------------------------------------------------------------------------------- the run
def run_variant(v, coins, clk, cal, t0=T0):
    """Daily book (gross, funding, n trades) over the calendar `cal` and the trade list, for one variant."""
    days, starts, mask = clk[v["clock"]]
    rows = []
    for sym, (P, F, rate) in coins.items():
        m_all = price(P, starts + v["w"] * MIN, t0) / price(P, starts, t0) - 1
        t = trades(P, F, rate, starts, v["w"], sigma(m_all), v["k"], v["side"], v["h"], mask, t0)
        t["coin"] = sym
        rows.append(t)
    tr = pd.concat(rows, ignore_index=True)
    tr["day"] = pd.to_datetime(tr.start // DAY * DAY, unit="ms").astype(cal.dtype)
    g = tr.groupby("day")
    book = pd.DataFrame({"gross": g.gross.sum() / 3, "funding": g.funding.sum() / 3, "n": g.size()})
    book = book.reindex(cal, fill_value=0)
    return book, tr


def net(book, c):
    return (book.gross - book.funding - 2 * c * book.n / 3).values


def window(cal, a, b):
    return np.asarray((cal >= pd.Timestamp(a)) & (cal <= pd.Timestamp(b)))


def summarize(name, v, book, tr, cal, placebo=False):
    rows = []
    for wname, (a, b) in (("discovery", DISC), ("validation", VALID), ("valid_h1", HALVES[0]),
                          ("valid_h2", HALVES[1])):
        sel = window(cal, a, b)
        trw = tr[(tr.day >= pd.Timestamp(a)) & (tr.day <= pd.Timestamp(b))]
        x1 = net(book, COST)[sel]
        _, mu, t = stats.newey_west_t(x1, 10)
        rows.append({"variant": name, **v, "placebo": placebo, "window": wname, "days": int(sel.sum()),
                     "trades": len(trw), "hit": float((trw.gross > 0).mean()) if len(trw) else np.nan,
                     "gross_trade_bp": trw.gross.mean() * 1e4 if len(trw) else np.nan,
                     "net1_bp": mu * 1e4, "net2_bp": net(book, 2 * COST)[sel].mean() * 1e4,
                     "net3_bp": net(book, 3 * COST)[sel].mean() * 1e4, "net_api_bp": net(book, API)[sel].mean() * 1e4,
                     "nw_t1": t, "sharpe1": x1.mean() / x1.std() * np.sqrt(365) if x1.std() > 0 else np.nan,
                     "breakeven_bp_side": trw.gross.mean() / 2 * 1e4 if len(trw) else np.nan})
    return rows


def stationary_idx(rng, n, block, B):
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, B)
    jump = rng.random((B, n)) < 1.0 / block
    fresh = rng.integers(0, n, (B, n))
    for t in range(1, n):
        idx[:, t] = np.where(jump[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def reality_check(X, rng, B=RC_B, block=RC_BLOCK):
    """White's reality check, studentized, as in R263 and R287: X is (variants, days)."""
    n = X.shape[1]
    sd = X.std(axis=1)
    sd = np.where(sd > 0, sd, np.inf)
    stat = np.sqrt(n) * X.mean(axis=1) / sd
    Xd = X - X.mean(axis=1, keepdims=True)
    mx = np.array([np.max(np.sqrt(n) * Xd[:, b].mean(axis=1) / sd) for b in stationary_idx(rng, n, block, B)])
    return stat, float((mx >= stat.max()).mean()), float(np.percentile(mx, 95))


def decide(fam_names, books, cal, seed):
    """Reality check over one sub-family's discovery series, the selected variant and its validation tests."""
    disc, val = window(cal, *DISC), window(cal, *VALID)
    X = np.array([net(books[n], COST)[disc] for n in fam_names])
    stat, rc_p, p95 = reality_check(X, np.random.default_rng(seed))
    j = int(np.argmax(stat))
    b = books[fam_names[j]]
    v1, v2 = net(b, COST)[val], net(b, 2 * COST)[val]
    tv = float(stats.newey_west_t(v1, 10)[2])
    halves = [float(net(b, COST)[window(cal, *hh)].mean()) for hh in HALVES]
    passed = bool(rc_p < 0.025 and tv >= 2.0 and v2.mean() > 0 and min(halves) > 0)
    return {"rc_p": rc_p, "rc_null_p95": p95, "best": fam_names[j], "best_disc_stat": float(stat[j]),
            "best_disc_net1_bp": float(X[j].mean() * 1e4), "valid_t1": tv, "valid_net1_bp": float(v1.mean() * 1e4),
            "valid_net2_bp": float(v2.mean() * 1e4), "valid_net3_bp": float(net(b, 3 * COST)[val].mean() * 1e4),
            "valid_api_bp": float(net(b, API)[val].mean() * 1e4), "valid_halves_net1_bp": [h * 1e4 for h in halves],
            "pass": passed}


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    coins = {s: (load_prices(data.ROOT / "klines_1m" / f"{s}.parquet"),
                 *load_funding(data.ROOT / "fundingRate" / f"{s}.parquet")) for s in COINS}
    clk = clocks()
    cal = pd.date_range(pd.to_datetime(T0, unit="ms"), pd.to_datetime(T1 - DAY, unit="ms"), freq="D")
    rows, books, trs, daily = [], {}, [], {}
    for v in variants():
        for pv, is_p in [(v, False)] + [(p, True) for p in placebo_of(v)]:
            name = name_of(pv)
            if name in books:
                continue
            book, tr = run_variant(pv, coins, clk, cal)
            books[name] = book
            r = summarize(name, pv, book, tr, cal, placebo=is_p)
            rows += r
            if not is_p:
                tr["variant"] = name
                trs.append(tr)
                daily[name] = net(book, COST)
                log(f"{name:34s} disc n {r[0]['trades']:4d} net1 {r[0]['net1_bp']:6.2f} bp/d t {r[0]['nw_t1']:5.2f}"
                    f" | valid n {r[1]['trades']:4d} net1 {r[1]['net1_bp']:6.2f} t {r[1]['nw_t1']:5.2f}")
    fams = {f: [name_of(v) for v in variants() if v["family"] == f] for f in ("OPEN", "SETTLE")}
    res = {f: decide(fams[f], books, cal, SEEDS[f]) for f in fams}
    for f, d in res.items():
        b = books[d["best"]]
        x = pd.Series(net(b, COST), index=cal)
        d["best_net1_bp_by_year"] = (x.groupby(x.index.year).mean() * 1e4).round(3).to_dict()
        d["best_top5_days_share"] = float(np.sort(x.values)[::-1][:5].sum() / x.sum()) if x.sum() > 0 else None
        tb = pd.concat(trs)
        tb = tb[tb.variant == d["best"]]
        d["best_gross_bp_per_trade_by_coin"] = (tb.groupby("coin").gross.mean() * 1e4).round(3).to_dict()
        log(f"{f}: best {d['best']} stat {d['best_disc_stat']:.2f} rc_p {d['rc_p']:.4f}; validation t "
            f"{d['valid_t1']:.2f}, 2x {d['valid_net2_bp']:.2f} bp/d, halves "
            f"{[round(h, 2) for h in d['valid_halves_net1_bp']]} -> {'PASS' if d['pass'] else 'fail'}")
    verdict = "PARTIAL" if any(d["pass"] for d in res.values()) else "NULL"
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "variants.csv", index=False, float_format="%.6g")
    pd.DataFrame(daily, index=cal.date).rename_axis("day").to_csv(out / "daily.csv.gz", float_format="%.8g")
    pd.concat(trs).to_csv(out / "trades.csv.gz", index=False, float_format="%.8g")
    summary = {"rid": "R289", "verdict": verdict, "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               "families": res}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {verdict}")
    return summary


if __name__ == "__main__":
    main()
