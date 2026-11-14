"""R435 stock_tugofwar_v1: the overnight-versus-intraday tug of war across MEXC's US-stock perps (M492).

Lou, Polk and Skouras (2019) find that a stock's past overnight (close-to-open) returns predict its future overnight
returns with a positive sign and its future intraday (open-to-close) returns with a negative sign. MEXC lists hundreds
of US-stock perpetuals that trade 24/7, so the overnight leg can be held without an opening auction. This runner asks
whether that cross-sectional pattern exists on these perps, and whether an overnight-only long-short book clears the
measured cost of trading them. Everything is fixed in experiments/stock_tugofwar_v1/PREREG.md.

usage: python scripts/run_stock_tugofwar.py            # the one frozen run (verifies the PREREG and every input)
       python scripts/run_stock_tugofwar.py --plumbing # pre-freeze counts only: universe sizes, no returns
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402
from lab.sessions import NYSEHolidays  # noqa: E402

LANE = ROOT / "experiments" / "stock_tugofwar_v1"
TICKER_LAST = "2026-11-06"                                  # last recorder day held at the freeze

HOUR = 3_600_000
DAY = 86_400_000
EXTRA = {"NVIDIA", "TESLA", "ROBINHOOD", "COINBASE"}      # US single stocks listed without the STOCK suffix
ETF = {"QQQSTOCK", "DIASTOCK"}                             # funds listed with the STOCK suffix
EARLY_CLOSE = {"2025-07-03", "2025-11-28", "2025-12-24"}   # NYSE 13:00 closes inside the sample: not sessions
CLOSE_H = 16                                               # NY local hour of the cash close
PROXY = {"o+30": 10, "o-30": 9}                            # NY local hour standing in for the 09:30 open
LOOKBACKS = (20, 60)
MIN_VALID = {20: 15, 60: 45}                               # valid overnight returns needed inside the lookback
N_TOP = 30                                                 # names kept by trailing quote volume
MIN_NAMES = 15                                             # fewer eligible names: no trade that session
QUINTILE = 5
MIN_LEG = 3
LIST_DAYS = 30                                             # listed at least this many days before the decision
AMT_DAYS = 20                                              # trailing UTC days of quote volume for the ranking
FEE_API = 8e-4                                             # MEXC API taker fee since 2026-06-01 (docs/MEXC_EDGES.md)
COST_MULT = (1, 2, 3)
BOOKS = ("B1", "B2", "B3")                                 # overnight momentum, intraday reversal, both
TARGETS = ("on", "id")
PRIMARY = ("B1", 20, "o+30")
BLOCK = 5                                                  # sessions per bootstrap block (one trading week)
BOOT = 10_000
SEED = 435
N_MIN = 120                                                # traded sessions needed for a PASS
NW_LAG = 5
TRIALS = len(TARGETS) * len(LOOKBACKS) * len(PROXY) + len(BOOKS) * len(LOOKBACKS) * len(PROXY)   # 8 + 12 = 20

log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


# ---------------------------------------------------------------- universe and sessions

def stock_candidates(contracts):
    """US-or-foreign single-stock perps by name: base ending in STOCK (funds excluded) plus the four unsuffixed names."""
    out = [r["symbol"] for r in contracts
           if r.get("type") == 2 and r.get("state") == 0
           and ((r["base"].endswith("STOCK") and r["base"] not in ETF) or r["base"] in EXTRA)]
    return sorted(out)


def session_shares(t_ms, close):
    """Shares of the total absolute hourly index move that fall in NYSE regular hours (bars opening 09:00-15:00 New York
    on NYSE trading days) and in Tokyo's cash hours (bars opening 09:00-14:00 Tokyo, weekdays)."""
    t_ms, close = np.asarray(t_ms, np.int64), np.asarray(close, float)
    if len(close) < 2:
        return np.nan, np.nan
    a = np.abs(np.diff(np.log(np.clip(close, 1e-12, None))))
    t = t_ms[1:]
    ny = pd.to_datetime(t, unit="ms", utc=True).tz_convert("America/New_York")
    days = ny.normalize().tz_localize(None)
    hol = NYSEHolidays().holidays(days.min(), days.max()) if len(days) else []
    trading = np.asarray((ny.weekday < 5) & ~days.isin(hol))
    h = np.asarray(ny.hour)
    tk = pd.to_datetime(t, unit="ms", utc=True).tz_convert("Asia/Tokyo")
    ht, wd = np.asarray(tk.hour), np.asarray(tk.weekday)
    tot = a.sum()
    if not tot > 0:
        return np.nan, np.nan
    return float(a[(h >= 9) & (h < 16) & trading].sum() / tot), float(a[(ht >= 9) & (ht < 15) & (wd < 5)].sum() / tot)


def ny_ms(day, hour):
    """UTC ms of `hour`:00 New York time on calendar date `day` (YYYY-MM-DD)."""
    ts = pd.Timestamp(f"{day} {hour:02d}:00").tz_localize("America/New_York")
    return int(ts.tz_convert("UTC").value // 1_000_000)


def sessions(start_day, end_day):
    """NYSE full sessions between two dates: DataFrame day, close, o+30, o-30 (UTC ms) and prev_ok (the previous NYSE
    trading day is the previous row, i.e. no early-close day in between, so the overnight return is one night)."""
    days = pd.bdate_range(start_day, end_day)
    hol = NYSEHolidays().holidays(days.min(), days.max())
    trading = [d.strftime("%Y-%m-%d") for d in days if d not in hol]
    rows, prev_full = [], None
    for i, d in enumerate(trading):
        if d in EARLY_CLOSE:
            prev_full = None                      # the next session's overnight spans an early close: not one night
            continue
        rows.append(dict(day=d, close=ny_ms(d, CLOSE_H), **{p: ny_ms(d, h) for p, h in PROXY.items()},
                         prev_ok=prev_full is not None and i > 0 and trading[i - 1] == prev_full))
        prev_full = d
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- per-symbol arrays

def price_at(t_bar, close_bar, T):
    """Price at instant T: the close of the hourly bar that opens at T - 1 h (NaN if that bar is missing)."""
    t_bar = np.asarray(t_bar, np.int64)
    T = np.asarray(T, np.int64)
    i = np.searchsorted(t_bar, T - HOUR)
    ok = (i < len(t_bar)) & (t_bar[np.minimum(i, len(t_bar) - 1)] == T - HOUR)
    return np.where(ok, np.asarray(close_bar, float)[np.minimum(i, len(t_bar) - 1)], np.nan)


def funding_between(f_t, f_rate, t0, t1):
    """Sum of settled funding rates with t0 < t <= t1 (per unit long notional; a long pays a positive rate)."""
    f_t = np.asarray(f_t, np.int64)
    c = np.r_[0.0, np.cumsum(np.asarray(f_rate, float))]
    return c[np.searchsorted(f_t, np.asarray(t1, np.int64), "right")] - c[np.searchsorted(f_t, np.asarray(t0, np.int64),
                                                                                           "right")]


def symbol_arrays(k, f, S):
    """Per-session arrays for one symbol: closes, open proxies, overnight and intraday log returns, funding over each
    leg, trailing quote volume (mean of the AMT_DAYS UTC days before the close's UTC day) and first bar time."""
    k = k.sort_values("t").drop_duplicates("t")
    k = k[k.close > 0]
    t, c = k.t.values.astype(np.int64), k.close.values.astype(float)
    out = {"first": int(t[0]) if len(t) else None}
    if not len(t):                                         # no usable bar: every value missing
        nan = np.full(len(S), np.nan)
        out.update(C=nan, amt=nan, **{f"{x}_{p}": nan for p in PROXY for x in ("on", "id", "fon", "fid")})
        return out
    C = price_at(t, c, S["close"].values)
    out["C"] = C
    for p in PROXY:
        O = price_at(t, c, S[p].values)
        on = np.full(len(S), np.nan)
        on[1:] = np.log(O[1:]) - np.log(C[:-1])
        on[~S["prev_ok"].values] = np.nan
        out[f"on_{p}"] = on
        out[f"id_{p}"] = np.log(C) - np.log(O)
        # fon[s]: funding settled over (close of s, open proxy of s+1]; fid[s]: over (open proxy of s, close of s]
        nxt_o = np.r_[S[p].values[1:], S["close"].values[-1]]
        out[f"fon_{p}"] = (funding_between(f.t.values, f.rate.values, S["close"].values, nxt_o) if len(f)
                           else np.zeros(len(S)))
        out[f"fid_{p}"] = (funding_between(f.t.values, f.rate.values, S[p].values, S["close"].values) if len(f)
                           else np.zeros(len(S)))
    day = t // DAY
    amt = pd.Series(k.amount.values, index=day).groupby(level=0).sum()
    full = amt.reindex(np.arange(day.min(), day.max() + 1), fill_value=0.0) if len(amt) else amt
    trail = full.rolling(AMT_DAYS, min_periods=AMT_DAYS).mean().shift(1)      # days strictly before
    dec_day = S["close"].values // DAY
    out["amt"] = trail.reindex(dec_day).values if len(trail) else np.full(len(S), np.nan)
    return out


def signal(on, L):
    """Trailing mean of the last L overnight returns up to and including the current session, or NaN with too few."""
    s = pd.Series(on)
    m = s.rolling(L, min_periods=MIN_VALID[L]).mean()
    return m.values


# ---------------------------------------------------------------- the books

def spearman(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 5:
        return np.nan
    rx, ry = pd.Series(x[ok]).rank().values, pd.Series(y[ok]).rank().values
    if rx.std() == 0 or ry.std() == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def nw_t(x, lag=NW_LAG):
    """Mean and Newey-West t-statistic of a series (NaNs dropped)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return dict(n=n, mean=None, t=None)
    e = x - x.mean()
    v = e @ e / n
    for j in range(1, min(lag, n - 1) + 1):
        v += 2 * (1 - j / (lag + 1)) * (e[j:] @ e[:-j]) / n
    return dict(n=n, mean=float(x.mean()), t=float(x.mean() / np.sqrt(v / n)) if v > 0 else None)


def evaluate(panel, S, fee, hs, L, p, mult=1, fee_override=None):
    """One (lookback, proxy) cell over every session. panel: symbol -> symbol_arrays; fee/hs: symbol -> per-side taker
    fee and half-spread (fractions). Returns a DataFrame per decision session with the universe size, the IC of the
    signal against the next overnight and intraday returns, and the B1/B2/B3 net and gross returns (sum of the long
    and short legs, i.e. per $1 long plus $1 short), with leg costs at `mult` times fee plus half-spread."""
    syms = sorted(panel)
    n = len(S)
    sig = np.vstack([signal(panel[s][f"on_{p}"], L) for s in syms])                 # [N, T]
    first = np.array([panel[s]["first"] if panel[s]["first"] is not None else 2**62 for s in syms], np.int64)
    amt = np.vstack([panel[s]["amt"] for s in syms])
    C = np.vstack([panel[s]["C"] for s in syms])
    on = np.vstack([panel[s][f"on_{p}"] for s in syms])
    idr = np.vstack([panel[s][f"id_{p}"] for s in syms])
    fon = np.vstack([panel[s][f"fon_{p}"] for s in syms])
    fid = np.vstack([panel[s][f"fid_{p}"] for s in syms])
    f_side = np.array([fee_override if fee_override is not None else fee[s] for s in syms])
    rt = 2 * mult * (f_side + np.array([hs[s] for s in syms]))                      # round-trip cost per name
    close = S["close"].values
    rows = []
    for d in range(n - 1):
        elig = (np.isfinite(sig[:, d]) & np.isfinite(C[:, d]) & np.isfinite(amt[:, d])
                & (first <= close[d] - LIST_DAYS * DAY))
        idx = np.flatnonzero(elig)
        row = dict(d=d, day=S["day"].iloc[d], n_elig=len(idx))
        if len(idx) < MIN_NAMES:
            rows.append(row)
            continue
        idx = idx[np.argsort(-amt[idx, d], kind="stable")][:N_TOP]
        row["n_univ"] = len(idx)
        s_d = sig[idx, d]
        row["ic_on"] = spearman(s_d, on[idx, d + 1])
        row["ic_id"] = spearman(s_d, idr[idx, d + 1])
        k = max(MIN_LEG, len(idx) // QUINTILE)
        order = idx[np.argsort(s_d, kind="stable")]
        bot, top = order[:k], order[-k:]

        def leg(names, r, fnd, side):
            """Mean gross and net of one leg: side x log return, minus the round trip, minus side x funding."""
            ok = np.isfinite(r[names])
            if not ok.any():
                return np.nan, np.nan, 0
            gross = side * r[names][ok]
            net = gross - rt[names][ok] - side * fnd[names][ok]
            return float(gross.mean()), float(net.mean()), int(ok.sum())

        # B1: long top / short bottom from this close to the next open proxy (funding settled in between)
        gl, nl, cl = leg(top, on[:, d + 1], fon[:, d], +1)
        gs, ns, cs = leg(bot, on[:, d + 1], fon[:, d], -1)
        row.update(b1_gross=gl + gs, b1_net=nl + ns, b1_nlong=cl, b1_nshort=cs)
        # B2: at the next open proxy, long bottom / short top until the next close
        gl2, nl2, _ = leg(bot, idr[:, d + 1], fid[:, d + 1], +1)
        gs2, ns2, _ = leg(top, idr[:, d + 1], fid[:, d + 1], -1)
        row.update(b2_gross=gl2 + gs2, b2_net=nl2 + ns2)
        row.update(b3_gross=row["b1_gross"] + row["b2_gross"], b3_net=row["b1_net"] + row["b2_net"])
        row["k"] = k
        row["amt_med"] = float(np.median(amt[np.r_[top, bot], d]))
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- inference

def block_boot(values, blocks, rng, boot=BOOT):
    """Mean, 95% percentile interval and one-sided p (share of resampled means <= 0), resampling whole blocks."""
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    v, blocks = v[ok], np.asarray(blocks)[ok]
    if len(v) == 0:
        return dict(n=0, mean=None, lo=None, hi=None, p_le0=None, blocks=0)
    u, inv = np.unique(blocks, return_inverse=True)
    s, c = np.bincount(inv, v, len(u)), np.bincount(inv, None, len(u))
    pick = rng.integers(0, len(u), (boot, len(u)))
    means = s[pick].sum(1) / np.maximum(c[pick].sum(1), 1)
    return dict(n=int(len(v)), mean=float(v.mean()), lo=float(np.percentile(means, 2.5)),
                hi=float(np.percentile(means, 97.5)), p_le0=float((means <= 0).mean()), blocks=int(len(u)))


def verdict(net1, net2, ci1, n_min=N_MIN):
    """PASS needs n >= n_min, mean 1x net > 0 with the block-bootstrap lower bound > 0, mean 2x net > 0 and a positive
    1x mean in each half of the traded sessions; fewer than n_min sessions is INCONCLUSIVE; anything else NULL."""
    net1, net2 = np.asarray(net1, float), np.asarray(net2, float)
    ok = np.isfinite(net1)
    net1, net2 = net1[ok], net2[ok]
    if len(net1) < n_min:
        return "INCONCLUSIVE"
    h = len(net1) // 2
    if (net1.mean() > 0 and ci1["lo"] is not None and ci1["lo"] > 0 and net2.mean() > 0
            and net1[:h].mean() > 0 and net1[h:].mean() > 0):
        return "PASS"
    return "NULL"


# ---------------------------------------------------------------- inputs (every loader takes its root explicitly)

def paths(root):
    root = Path(root)
    data = root / "data" / "mexc_tradfi"
    run = data / "runs" / "1792671203016652636"
    return dict(root=root, data=data, contracts=run / "contracts.json", run_manifest=run / "manifest.json",
                ticker=root / "data" / "recorders" / "mexc_ticker", manifest=root / LANE.relative_to(ROOT) /
                "inputs_manifest.json")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ticker_files(root):
    P = paths(root)
    return sorted(f for f in P["ticker"].glob("*/*.parquet") if f.parent.name <= TICKER_LAST)


def input_files(root):
    P = paths(root)
    contracts = json.loads(P["contracts"].read_text())
    files = [P["contracts"], P["run_manifest"]]
    for s in stock_candidates(contracts):
        files += [P["data"] / "klines_1h" / f"{s}.parquet", P["data"] / "index_price_1h" / f"{s}.parquet",
                  P["data"] / "funding" / f"{s}.parquet"]
    return files + ticker_files(root)


def write_manifest(root):
    P = paths(root)
    m = {str(p.relative_to(P["root"])): sha256(p) for p in input_files(root)}
    P["manifest"].write_text(json.dumps(m, indent=0, sort_keys=True) + "\n")
    return m


def check_manifest(root):
    P = paths(root)
    m = json.loads(P["manifest"].read_text())
    bad = [rel for rel, want in m.items() if sha256(P["root"] / rel) != want]
    if bad:
        raise SystemExit(f"{len(bad)} inputs differ from the manifest, e.g. {bad[:3]}")
    if {str(p.relative_to(P["root"])) for p in input_files(root)} != set(m):
        raise SystemExit("the input file set differs from the manifest")
    return len(m)


def half_spreads(root, symbols):
    """Median half-spread (fraction) per symbol over every held MEXC ticker snapshot; symbols never recorded get the
    90th percentile of the recorded medians."""
    tk = pd.concat([pd.read_parquet(f, columns=["symbol", "t_bid1", "t_ask1"]) for f in ticker_files(root)])
    tk = tk[(tk.t_bid1 > 0) & (tk.t_ask1 >= tk.t_bid1) & tk.symbol.isin(symbols)]
    hs = ((tk.t_ask1 - tk.t_bid1) / ((tk.t_ask1 + tk.t_bid1) / 2) / 2).groupby(tk.symbol).median()
    fill = float(np.percentile(hs.values, 90)) if len(hs) else 0.0
    return {s: float(hs.get(s, fill)) for s in symbols}, int(len(hs)), fill


def classify(ix, first_t):
    """Point-in-time session class: shares computed only on index bars before first_t + LIST_DAYS days, i.e. before
    the contract can first enter the universe."""
    ix = ix[ix.t < first_t + LIST_DAYS * DAY]
    us, asia = session_shares(ix.t.values, ix.close.values)
    return dict(us_share=us, asia_share=asia, us=bool(np.isfinite(us) and np.isfinite(asia) and us > asia))


def load(root, symbols_all, S):
    """Real-data panel: classify each contract on its first LIST_DAYS days, keep US names, build per-symbol arrays."""
    data = paths(root)["data"]
    panel, cls = {}, {}
    for s in symbols_all:
        k = pd.read_parquet(data / "klines_1h" / f"{s}.parquet")
        if not len(k):
            continue
        ix = pd.read_parquet(data / "index_price_1h" / f"{s}.parquet").sort_values("t")
        cls[s] = classify(ix, int(k.t.min()))
        if not cls[s]["us"]:
            continue
        f = pd.read_parquet(data / "funding" / f"{s}.parquet").sort_values("t")
        panel[s] = symbol_arrays(k, f, S)
    return panel, cls


def frame(root):
    P = paths(root)
    contracts = json.loads(P["contracts"].read_text())
    syms = stock_candidates(contracts)
    fee = {r["symbol"]: float(r["taker"]) for r in contracts}
    end = pd.to_datetime(json.loads(P["run_manifest"].read_text())["end_exclusive"], unit="ms").strftime("%Y-%m-%d")
    S = sessions("2025-07-01", end)
    return syms, fee, S


def plumbing():
    """Counts only: candidates, US classification, sessions, eligible-universe sizes. No return is computed."""
    syms, fee, S = frame(ROOT)
    panel, cls = load(ROOT, syms, S)
    hs, n_rec, fill = half_spreads(ROOT, sorted(panel))
    first = {s: panel[s]["first"] for s in panel}
    close = S["close"].values
    sizes = []
    for L in LOOKBACKS:
        for p in PROXY:
            valid = {s: np.isfinite(signal(panel[s][f"on_{p}"], L)) for s in panel}   # availability, not values
            n = [sum(1 for s in panel if valid[s][d] and np.isfinite(panel[s]["C"][d])
                     and np.isfinite(panel[s]["amt"][d]) and first[s] <= close[d] - LIST_DAYS * DAY)
                 for d in range(len(S) - 1)]
            n = np.array(n)
            sizes.append(dict(L=L, proxy=p, sessions_traded=int((n >= MIN_NAMES).sum()),
                              first_traded=S["day"].iloc[int(np.argmax(n >= MIN_NAMES))] if (n >= MIN_NAMES).any()
                              else None, median_eligible=float(np.median(n[n >= MIN_NAMES])) if (n >= MIN_NAMES).any()
                              else 0))
    out = dict(candidates=len(syms), us=int(sum(c["us"] for c in cls.values())), non_us=sorted(
        s for s, c in cls.items() if not c["us"]), sessions=int(len(S)), sessions_one_night=int(S.prev_ok.sum()),
        first_session=S.day.iloc[0], last_session=S.day.iloc[-1], half_spread_recorded=n_rec,
        half_spread_fill_bp=fill * 1e4, half_spread_median_bp=float(np.median(list(hs.values())) * 1e4),
        fee_counts={str(v): int(sum(1 for s in panel if fee[s] == v)) for v in sorted({fee[s] for s in panel})},
        universe=sizes)
    (LANE / "plumbing.json").write_text(json.dumps(out, indent=1) + "\n")
    log(json.dumps({k: v for k, v in out.items() if k != "non_us"}, indent=1))


def run():
    sha = prereg.verify(LANE / "PREREG.md")
    from scripts.run_clockflow import check_inputs
    log(f"PREREG verified {sha[:12]}; {len(check_inputs(LANE / 'PREREG.md'))} inputs match; "
        f"{check_manifest(ROOT)} data files match the manifest; trials {TRIALS}")
    syms, fee, S = frame(ROOT)
    panel, cls = load(ROOT, syms, S)
    hs, n_rec, fill = half_spreads(ROOT, sorted(panel))
    log(f"{len(panel)} US names, {len(S)} sessions, spreads recorded for {n_rec}")
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    rng = np.random.default_rng(SEED)
    cells, keep = [], {}
    for L in LOOKBACKS:
        for p in PROXY:
            fr = {m: evaluate(panel, S, fee, hs, L, p, mult=m) for m in COST_MULT}
            api = evaluate(panel, S, fee, hs, L, p, mult=1, fee_override=FEE_API)
            base = fr[1]
            traded = base[base["b1_net"].notna()] if "b1_net" in base.columns else base.iloc[:0]
            blocks = np.arange(len(traded)) // BLOCK
            for tgt in TARGETS:
                st = nw_t(traded[f"ic_{tgt}"].values) if len(traded) else dict(n=0, mean=None, t=None)
                cells.append(dict(kind="ic", target=tgt, L=L, proxy=p, n=st["n"], mean=st["mean"], t=st["t"]))
            for b in BOOKS:
                key = b.lower()
                row = dict(kind="book", book=b, L=L, proxy=p)
                for m in COST_MULT:
                    t_m = fr[m].loc[traded.index]
                    ci = block_boot(t_m[f"{key}_net"].values, blocks, rng)
                    row.update({f"net{m}x_bp": None if ci["mean"] is None else ci["mean"] * 1e4,
                                f"lo{m}x_bp": None if ci["lo"] is None else ci["lo"] * 1e4,
                                f"hi{m}x_bp": None if ci["hi"] is None else ci["hi"] * 1e4,
                                f"p{m}x": ci["p_le0"]})
                g = block_boot(traded[f"{key}_gross"].values, blocks, rng)
                a = block_boot(api.loc[traded.index, f"{key}_net"].values, blocks, rng)
                row.update(n=g["n"], blocks=g["blocks"], gross_bp=None if g["mean"] is None else g["mean"] * 1e4,
                           gross_lo_bp=None if g["lo"] is None else g["lo"] * 1e4,
                           gross_hi_bp=None if g["hi"] is None else g["hi"] * 1e4,
                           api_net_bp=None if a["mean"] is None else a["mean"] * 1e4)
                cells.append(row)
                if (b, L, p) == PRIMARY:
                    keep = dict(frames=fr, traded=traded, blocks=blocks, api=api)
            base.assign(L=L, proxy=p).to_csv(res / f"sessions_L{L}_{p}.csv", index=False)
    cdf = pd.DataFrame(cells)
    cdf.to_csv(res / "cells.csv", index=False)
    tr, fr = keep["traded"], keep["frames"]
    n1 = fr[1].loc[tr.index, "b1_net"].values
    n2 = fr[2].loc[tr.index, "b1_net"].values
    ci1 = block_boot(n1, keep["blocks"], rng)
    v = verdict(n1, n2, ci1)
    h = len(tr) // 2
    summary = dict(
        lane="stock_tugofwar_v1", registry="R435", trials=TRIALS, program_trials=registry.program_trials(
            ROOT / "registry" / "rounds.csv"), primary=dict(book="B1", L=20, proxy="o+30"), verdict=v,
        n_sessions=int(len(tr)), first=tr.day.iloc[0] if len(tr) else None, last=tr.day.iloc[-1] if len(tr) else None,
        net1x=ci1, net2x_mean_bp=float(np.nanmean(n2) * 1e4) if len(n2) else None,
        net3x_mean_bp=float(np.nanmean(fr[3].loc[tr.index, "b1_net"].values) * 1e4) if len(tr) else None,
        api_net_mean_bp=float(np.nanmean(keep["api"].loc[tr.index, "b1_net"].values) * 1e4) if len(tr) else None,
        gross_mean_bp=float(np.nanmean(tr.b1_gross.values) * 1e4) if len(tr) else None,
        halves_net1x_bp=[float(np.nanmean(n1[:h]) * 1e4), float(np.nanmean(n1[h:]) * 1e4)] if len(tr) else None,
        bonferroni_p=0.05 / TRIALS, primary_p_le0=ci1["p_le0"],
        median_leg_names=float(tr.k.median()) if len(tr) else None,
        median_leg_quote_volume_usd=float(tr.amt_med.median()) if len(tr) else None,
        universe_median=float(tr.n_univ.median()) if len(tr) else None,
        half_spread_median_bp=float(np.median(list(hs.values())) * 1e4), half_spread_fill_bp=fill * 1e4,
        us_names=len(panel), classified=cls)
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    log(f"VERDICT {v}: n {len(tr)}, gross {summary['gross_mean_bp']}, net1x {ci1}")
    log(cdf.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--manifest", action="store_true", help="pre-freeze: write the data-file manifest")
    a = ap.parse_args()
    if a.manifest:
        log(f"{len(write_manifest(ROOT))} files in the manifest")
    elif a.plumbing:
        plumbing()
    else:
        run()
