"""R353 settlehop_v1: M267's settlement-window hop on hourly bars, frozen in experiments/settlehop_v1/PREREG.md.

Venue S pays funding in a lump every 4 or 8 hours (MEXC, Binance, Gate); venue H pays it every hour (Lighter, dYdX).
One hour before each S settlement at T, when the last settled S rate r and H's last hourly rate h promise a two-hour
capture e = |r - 2h| of at least theta, take the receiving side on S and the other side on H (same coin), and close
both one hour after T. The hop collects S's whole lump and pays only two hours of H, while the two legs hedge the
coin's move. What can take the lump back is the price of the S leg against the H leg around T: if the S perp's price
jumps by the payment once it has been made, the hop earns nothing; that is the question.

usage: python scripts/run_settlehop.py              the frozen run (verifies the PREREG and every input hash first)
       python scripts/run_settlehop.py --symbols    write experiments/settlehop_v1/symbols.csv (before the freeze)
       python scripts/run_settlehop.py --plumbing   counts of settlements, signals and tradable entries; no returns
"""
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "settlehop_v1"
REGISTRY = "R353"
DATA = ROOT / "data"
H = 3_600_000
DAY = 24 * H
T0 = 1_609_459_200_000            # 2021-01-01: no earlier row is read (2020 is reserved)
T1 = 1_790_812_800_000            # 2026-10-01: no row from here is read (post-archive)
VENUES = {   # venue -> (hourly bars folder, volume column, funding folder)
    "mexc": ("mexc_hist/klines_1h", "vol", "mexc_hist/funding"),
    "binance": ("klines_1h", "volume", "fundingRate"),
    "gate": ("gate_hist/open/candlesticks_1h", "vol_contracts", "gate_hist/open/funding_applies"),
    "lighter": ("lighter_hist/open/candles_1h", "volume", "lighter_hist/open/funding"),
    "dydx": ("dydx_hist/open/candles_1h", "volume", "dydx_hist/open/funding"),
}
PAIRS = (("mexc", "lighter"), ("binance", "lighter"), ("gate", "lighter"),
         ("mexc", "dydx"), ("binance", "dydx"), ("gate", "dydx"))
THETAS = (0.003, 0.005)
PRIMARY = ("mexc", "lighter", 0.005)
TRIALS = len(PAIRS) * len(THETAS)
COST_BP = {"mexc": 8.5, "binance": 8.5, "gate": 7.0, "dydx": 7.0}   # a side at 1x, fee plus book
# Lighter (fee 0): the median $1k cost a side of the 22 hourly snapshots of every Lighter book (2026-10-21..27) in the
# band of the coin's 24 h volume, (upper bound in USD, bp). The hop pays the band of its trailing 24 h on Lighter.
LIGHTER_BANDS = ((1e4, 26.67), (1e5, 7.27), (1e6, 4.17), (1e7, 1.09), (1e8, 0.51), (np.inf, 0.26))
MEXC_WEB_BP = 3.0                 # MEXC web a side, reported only
MULTS = (1, 2, 3)
SLOTS = 5                         # hops per settlement time; the book's capital is five equal slots
MIN_GAP, MAX_GAP = 4 * H - 60_000, 24 * H + 60_000
CORR_DAYS, CORR_MIN, CORR_OBS = 30, 0.9, 20
NW_LAG, T_BAR, BONF_T = 5, 2.0, 2.64
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------------------------------------------------ inputs
def frozen_inputs(prereg_path, root=ROOT):
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


TRADFI = ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json"   # R216's list


def build_symbols(root=DATA):
    """One row per Binance crypto perp that Lighter or dYdX lists, with its keys on MEXC, Gate and dYdX (lab.venues) and
    on Lighter (scripts/lighter_table.py). R216's TradFi perps (stocks, ETFs, metals, pre-IPO) are left out. File names
    and contract lists only; no price is read."""
    from lab import venues
    import lighter_table
    lt = lighter_table.lighter_symbols(root)
    tab = {r["key"]: r for r in venues.rows(root)}
    tradfi = set(json.loads(TRADFI.read_text()))
    out = []
    for key in sorted((set(tab) | set(lt)) - tradfi):
        r = tab.get(key, {})
        row = {"key": key, "mexc": r.get("mexc", ""), "gate": r.get("gate", ""), "dydx": r.get("dydx", ""),
               "lighter": lt.get(key, "")}
        if row["lighter"] or row["dydx"]:
            out.append(row)
    return out


def read_symbols(path=LANE / "symbols.csv"):
    with open(path, newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def key_of(row, venue):
    return row["key"] if venue == "binance" else row[venue]


MANIFEST = {}                     # data file (relative to ROOT) -> frozen sha256; filled by the frozen run


def data_paths(rows):
    """Every bars and funding file a run reads: both venues of each pair, for coins with keys on both."""
    out = set()
    for S, Hv in PAIRS:
        for r in rows:
            ks, kh = key_of(r, S), key_of(r, Hv)
            if not ks or not kh:
                continue
            for v, k in ((S, ks), (Hv, kh)):
                for folder in (VENUES[v][0], VENUES[v][2]):
                    p = DATA / folder / f"{k}.parquet"
                    if p.exists():
                        out.add(p.relative_to(ROOT).as_posix())
    return sorted(out)


def checked(path):
    """A data file the frozen run may read: it must be in the manifest with the same sha256."""
    if MANIFEST:
        rel = Path(path).relative_to(ROOT).as_posix()
        want = MANIFEST.get(rel)
        if want is None or prereg.sha256_file(path) != want:
            raise prereg.PreregError(f"{rel}: not in the frozen data manifest or changed since")
    return path


def check_bands(paths):
    """LIGHTER_BANDS must equal the medians, to 2 decimals, of the listed Lighter book snapshots."""
    df = pd.concat([pd.read_parquet(ROOT / p, columns=["buy_1k_bp", "sell_1k_bp", "vol24_usd"]) for p in paths])
    side = ((df.buy_1k_bp + df.sell_1k_bp) / 2).to_numpy(float)
    vol = df.vol24_usd.to_numpy(float)
    ok = np.isfinite(side) & np.isfinite(vol)
    lo = 0.0
    for upper, bp in LIGHTER_BANDS:
        m = ok & (vol >= lo) & (vol < upper)
        got = round(float(np.median(side[m])), 2)
        if got != bp:
            raise ValueError(f"Lighter band below {upper}: snapshot median {got} != frozen {bp}")
        lo = upper
    return len(paths)


# -------------------------------------------------------------------------------------------------------------- data
def hour(t):
    """Settlement stamps to the nearest hour (Binance writes 16:00:00.002, dYdX 18:00:01)."""
    return (np.asarray(t, np.int64) + H // 2) // H * H


def load_bars(venue, key, t0=T0, t1=T1):
    """Hourly bars opening in [t0, t1): open time, close, traded flag (close > 0 and volume > 0) and, on Lighter, the
    quote volume. Rows outside [t0, t1) are filtered by the reader and never loaded."""
    folder, vol, _ = VENUES[venue]
    p = DATA / folder / f"{key}.parquet"
    if not key or not p.exists():
        return None
    cols = ["t", "close", vol] + (["quote_volume"] if venue == "lighter" else [])
    k = pq.read_table(checked(p), columns=cols, filters=[("t", ">=", t0), ("t", "<", t1)]).to_pandas()
    k = k.drop_duplicates("t").sort_values("t", ignore_index=True)
    k = k[k.t % H == 0]
    if not len(k):
        return None
    close = k.close.to_numpy(float)
    v = k[vol].to_numpy(float)
    return {"t": k.t.to_numpy(np.int64), "close": close,
            "traded": np.isfinite(close) & (close > 0) & np.isfinite(v) & (v > 0),
            "qv": k.quote_volume.to_numpy(float) if venue == "lighter" else None}


def load_funding(venue, key, t0=T0, t1=T1):
    """Settlements in [t0, t1) as (hour stamps, signed rate per settlement, positive when longs pay; cumulative sum with
    a leading 0, so the settlements in (a, b] sum to cs[searchsorted(t, b, 'right')] - cs[searchsorted(t, a, 'right')])."""
    p = DATA / VENUES[venue][2] / f"{key}.parquet"
    if not key or not p.exists():
        return None
    f = pq.read_table(checked(p), columns=["t", "rate"], filters=[("t", ">=", t0 - H), ("t", "<", t1)]).to_pandas()
    f = f[np.isfinite(f.rate.to_numpy(float))]
    t = hour(f.t.to_numpy(np.int64))
    keep = (t >= t0) & (t < t1)
    f = pd.DataFrame({"t": t[keep], "rate": f.rate.to_numpy(float)[keep]}).drop_duplicates("t").sort_values("t")
    if not len(f):
        return None
    r = f.rate.to_numpy(float)
    return f.t.to_numpy(np.int64), r, np.concatenate([[0.0], np.cumsum(r)])


def window_sum(f, a, b):
    """Funding settled in (a, b]."""
    t, _, cs = f
    return float(cs[np.searchsorted(t, b, side="right")] - cs[np.searchsorted(t, a, side="right")])


# ------------------------------------------------------------------------------------------------------------- rules
def signals(fs, fh):
    """Every S settlement T that follows the previous one by 4 to 24 hours, with H settling in the hour before the
    entry (T - 1 h): (T, r_prev, h_prev, e_signed = r_prev - 2 h_prev). All of it is known at the entry."""
    ts, rs, _ = fs
    th, rh, _ = fh
    gap = np.diff(ts)
    T, rprev = ts[1:], rs[:-1]
    ok = (gap >= MIN_GAP) & (gap <= MAX_GAP)
    j = np.searchsorted(th, T - H, side="right") - 1
    jj = np.clip(j, 0, None)
    ok &= (j >= 0) & ((T - H) - th[jj] <= 2 * H)
    T, rprev, hprev = T[ok], rprev[ok], rh[jj][ok]
    return T, rprev, hprev, rprev - 2 * hprev


def at(bars, t):
    """Index of the bar opening at t, or -1."""
    i = np.searchsorted(bars["t"], t)
    return int(i) if i < len(bars["t"]) and bars["t"][i] == t else -1


def last_traded(bars, t_open_max, i_min):
    """Index of the last traded bar opening at or before t_open_max and at or after i_min (the entry), else i_min."""
    i = int(np.searchsorted(bars["t"], t_open_max, side="right")) - 1
    while i > i_min and not bars["traded"][i]:
        i -= 1
    return max(i, i_min)


def daily_closes(bars):
    """{day start ms: close of the last traded bar opening in [day - 1 h, day)}, the 00:00 UTC close."""
    t, c, tr = bars["t"], bars["close"], bars["traded"]
    sel = tr & ((t + H) % DAY == 0)
    return dict(zip((t[sel] + H).tolist(), c[sel].tolist()))


def same_coin(ds, dh, entry):
    """Point-in-time identity: the correlation of daily returns over the CORR_DAYS daily closes up to the last 00:00 at
    or before the entry must reach CORR_MIN on at least CORR_OBS paired days."""
    d_e = entry // DAY * DAY
    days = d_e - DAY * np.arange(CORR_DAYS, -1, -1)
    a = np.array([ds.get(int(d), np.nan) for d in days])
    b = np.array([dh.get(int(d), np.nan) for d in days])
    ra, rb = a[1:] / a[:-1] - 1, b[1:] / b[:-1] - 1
    m = np.isfinite(ra) & np.isfinite(rb)
    if m.sum() < CORR_OBS or np.std(ra[m]) == 0 or np.std(rb[m]) == 0:
        return False
    return bool(np.corrcoef(ra[m], rb[m])[0, 1] >= CORR_MIN)


def lighter_cost_bp(qv24):
    """Lighter's cost a side for the hop: the snapshot median of the coin's trailing 24 h volume band."""
    q = qv24 if np.isfinite(qv24) else 0.0
    for upper, bp in LIGHTER_BANDS:
        if q < upper:
            return bp
    return LIGHTER_BANDS[-1][1]


def hop(sb, hb, fs, fh, T, d):
    """One hop at settlement T, direction d (+1: short S and long H). None when either entry bar is not traded, or when
    H's file lacks either of its settlements in the hold (T and T + 1 h). Entry at the close of the bar ending T - 1 h,
    exit at the last traded close at or before the bar ending T + 1 h; funding in (T - 1 h, T + 1 h] on each venue,
    held to T + 1 h even when the exit close is stale. Also the same hop closed at T (the close of the bar ending T)."""
    i_s, i_h = at(sb, T - 2 * H), at(hb, T - 2 * H)
    if i_s < 0 or i_h < 0 or not sb["traded"][i_s] or not hb["traded"][i_h]:
        return None
    th = fh[0]
    if np.searchsorted(th, T + H, side="right") - np.searchsorted(th, T - H, side="right") != 2:
        return None
    x_s, x_h = last_traded(sb, T, i_s), last_traded(hb, T, i_h)
    m_s, m_h = last_traded(sb, T - H, i_s), last_traded(hb, T - H, i_h)
    ret = lambda b, i, j: b["close"][j] / b["close"][i] - 1
    f_s, f_h = window_sum(fs, T - H, T + H), window_sum(fh, T - H, T + H)
    f_s0, f_h0 = window_sum(fs, T - H, T), window_sum(fh, T - H, T)
    price = d * (ret(hb, i_h, x_h) - ret(sb, i_s, x_s))
    price0 = d * (ret(hb, i_h, m_h) - ret(sb, i_s, m_s))
    qv24 = np.nan
    if hb["qv"] is not None:                       # the 24 bars opening in [T - 25 h, T - 2 h]
        lo = int(np.searchsorted(hb["t"], T - 25 * H, side="left"))
        qv24 = float(np.nansum(hb["qv"][lo: i_h + 1]))
    return {"price": price, "fund": d * (f_s - f_h), "fund_s": d * f_s, "fund_h": -d * f_h,
            "price0": price0, "fund0": d * (f_s0 - f_h0), "stale": bool(x_s != at(sb, T) or x_h != at(hb, T)),
            "qv24": qv24}


def eligible(T):
    """Settlements whose identity window starts in the lane's rows and whose exit and funding end before T1."""
    return (T - H >= T0 + (CORR_DAYS + 1) * DAY) & (T + H < T1)


def pair_hops(S, Hv, rows, log_every=0):
    """Every hop of the pair with e at or above the smallest theta, with its legs, funding, identity flag and cost;
    and the pair's calendar: the days from the first to the last eligible S settlement with H settling, at any e.
    Thresholds and the slot cap are applied later."""
    out, first, last = [], None, None
    for n, r in enumerate(rows):
        ks, kh = key_of(r, S), key_of(r, Hv)
        if not ks or not kh:
            continue
        fs, fh = load_funding(S, ks), load_funding(Hv, kh)
        if fs is None or fh is None:
            continue
        T, rp, hp, es = signals(fs, fh)
        keep = eligible(T)
        T, rp, hp, es = T[keep], rp[keep], hp[keep], es[keep]
        if not len(T):
            continue
        first = int(T.min()) if first is None else min(first, int(T.min()))
        last = int(T.max()) if last is None else max(last, int(T.max()))
        big = np.abs(es) >= min(THETAS)
        if not big.any():
            continue
        sb, hb = load_bars(S, ks), load_bars(Hv, kh)
        if sb is None or hb is None:
            continue
        ds, dh = daily_closes(sb), daily_closes(hb)
        for t, rp_, hp_, es_ in zip(T[big], rp[big], hp[big], es[big]):
            t = int(t)
            d = 1 if es_ > 0 else -1
            h = hop(sb, hb, fs, fh, t, d)
            if h is None:
                continue
            c_h = lighter_cost_bp(h["qv24"]) if Hv == "lighter" else COST_BP[Hv]
            out.append({"S": S, "H": Hv, "coin": r["key"], "T": t, "d": d, "r_prev": rp_, "h_prev": hp_,
                        "e": abs(es_), "same": same_coin(ds, dh, t - H), "cost_s_bp": COST_BP[S], "cost_h_bp": c_h,
                        **h})
        if log_every and n % log_every == 0:
            log(f"{S}+{Hv}: {n}/{len(rows)} coins, {len(out)} hops")
    days = (np.arange(first // DAY * DAY, last // DAY * DAY + DAY, DAY, dtype=np.int64) if first is not None
            else np.array([], np.int64))
    return pd.DataFrame(out), days


def select(cand, theta):
    """The hops a trader takes: identity passed, e >= theta, at most SLOTS per settlement time (largest e first, then
    the coin's name)."""
    x = cand[cand.same & (cand.e >= theta)]
    x = x.sort_values(["T", "e", "coin"], ascending=[True, False, True])
    return x.groupby("T", sort=False).head(SLOTS).reset_index(drop=True)


def net(h, mult=1, s_bp=None):
    """Net return of each hop at cost multiple mult: two sides on each venue."""
    cs = h.cost_s_bp if s_bp is None else s_bp
    return h.price + h.fund - mult * 2 * (cs + h.cost_h_bp) / 1e4


def book(h, days, mult=1, s_bp=None):
    """Daily return of the book (bp of capital): each day's hop nets, each on one of SLOTS slots, 0 on idle days."""
    x = np.zeros(len(days))
    if len(h) and len(days):
        idx = ((h["T"].to_numpy(np.int64) // DAY * DAY) - days[0]) // DAY
        np.add.at(x, idx, net(h, mult, s_bp).to_numpy() / SLOTS)
    return x * 1e4


def nw(x):
    n, mu, t = stats.newey_west_t(x, NW_LAG)
    return mu, t


def describe(h, days, s=None, label=""):
    """Every reported statistic of one book."""
    out = {"book": label, "hops": int(len(h)), "coins": int(h.coin.nunique()) if len(h) else 0, "days": int(len(days))}
    if not len(h):
        return out
    n1 = net(h, 1)
    out.update({
        "hops_per_day": len(h) / max(len(days), 1), "mean_e_bp": float(h.e.mean() * 1e4),
        "fund_bp": float(h.fund.mean() * 1e4), "price_bp": float(h.price.mean() * 1e4),
        "price_pre_bp": float(h.price0.mean() * 1e4), "price_post_bp": float((h.price - h.price0).mean() * 1e4),
        "gross_bp": float((h.price + h.fund).mean() * 1e4), "cost1_bp": float((2 * (h.cost_s_bp + h.cost_h_bp)).mean()),
        "net1_bp": float(n1.mean() * 1e4), "net2_bp": float(net(h, 2).mean() * 1e4),
        "net3_bp": float(net(h, 3).mean() * 1e4), "hit1": float((n1 > 0).mean()),
        "net1_trim_bp": float(stats_trim(n1) * 1e4), "stale": int(h.stale.sum()),
        "exitT_net1_bp": float((h.price0 + h.fund0 - 2 * (h.cost_s_bp + h.cost_h_bp) / 1e4).mean() * 1e4),
    })
    for m in MULTS:
        mu, t = nw(book(h, days, m))
        out[f"day{m}_bp"], out[f"t{m}"] = mu, t
    half = len(days) // 2
    for k, (a, b) in enumerate(((0, half), (half, len(days)))):
        sub = days[a:b]
        hk = h[(h["T"] // DAY * DAY >= sub[0]) & (h["T"] // DAY * DAY <= sub[-1])] if len(sub) else h.iloc[:0]
        out[f"half{k + 1}_day1_bp"] = float(book(hk, sub, 1).mean()) if len(sub) else float("nan")
    by = n1.groupby(h.coin).sum().sort_values(ascending=False)
    out["best_coin"] = by.index[0]
    rest = h[h.coin != by.index[0]]
    out["wo_best_day1_bp"] = float(book(rest, days, 1).mean())
    if s == "mexc":
        mu, t = nw(book(h, days, 1, s_bp=MEXC_WEB_BP))
        out["mexc_web_day1_bp"], out["mexc_web_t1"] = mu, t
        out["mexc_web_net1_bp"] = float(net(h, 1, s_bp=MEXC_WEB_BP).mean() * 1e4)
    return out


def stats_trim(x, q=0.01):
    lo, hi = np.quantile(x, [q, 1 - q])
    return float(x[(x >= lo) & (x <= hi)].mean())


def decide(d):
    """The frozen rule on the primary book's description."""
    checks = {"t1": d.get("t1", np.nan) >= T_BAR, "day2_positive": d.get("day2_bp", np.nan) > 0,
              "halves_positive": all(d.get(k, np.nan) > 0 for k in ("half1_day1_bp", "half2_day1_bp")),
              "without_best_coin_positive": d.get("wo_best_day1_bp", np.nan) > 0}
    return {"checks": checks, "verdict": "PASS" if all(checks.values()) else "NULL"}


# -------------------------------------------------------------------------------------------------------------- main
def plumbing(rows):
    """Counts only: eligible settlements, signals at each theta, tradable entries, calendar days. No price return."""
    for S, Hv in PAIRS:
        n = {"coins": 0, "signals": 0, **{f"ge{th}": 0 for th in THETAS}, "entry_traded": 0}
        first, last = None, None
        for r in rows:
            ks, kh = key_of(r, S), key_of(r, Hv)
            if not ks or not kh:
                continue
            fs, fh = load_funding(S, ks), load_funding(Hv, kh)
            if fs is None or fh is None:
                continue
            T, rp, hp, es = signals(fs, fh)
            keep = eligible(T)
            T, es = T[keep], es[keep]
            if not len(T):
                continue
            first = int(T.min()) if first is None else min(first, int(T.min()))
            last = int(T.max()) if last is None else max(last, int(T.max()))
            n["coins"] += 1
            n["signals"] += len(T)
            for th in THETAS:
                n[f"ge{th}"] += int((np.abs(es) >= th).sum())
            sb, hb = load_bars(S, ks), load_bars(Hv, kh)
            if sb is None or hb is None:
                continue
            for t in T[np.abs(es) >= min(THETAS)]:
                i_s, i_h = at(sb, int(t) - 2 * H), at(hb, int(t) - 2 * H)
                n["entry_traded"] += int(i_s >= 0 and i_h >= 0 and sb["traded"][i_s] and hb["traded"][i_h])
        span = (pd.Timestamp(first, unit="ms").date(), pd.Timestamp(last, unit="ms").date()) if first else None
        log(f"{S}+{Hv}: {n} span {span}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", action="store_true")
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--manifest", action="store_true")
    a = ap.parse_args()
    if a.manifest:
        paths = data_paths(read_symbols())
        with open(LANE / "data_files.csv", "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["path", "sha256"])
            for rel in paths:
                w.writerow([rel, prereg.sha256_file(ROOT / rel)])
        log(f"{len(paths)} data files hashed")
        return
    if a.symbols:
        rows = build_symbols()
        with open(LANE / "symbols.csv", "w", newline="") as f:
            w = csv.DictWriter(f, ["key", "mexc", "gate", "dydx", "lighter"], lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        log(f"{len(rows)} rows written")
        return
    if a.plumbing:
        plumbing(read_symbols())
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    n_snap = check_bands([p for p in shas if p.startswith("data/recorders/lighter_book/")])
    with open(LANE / "data_files.csv", newline="") as f:
        MANIFEST.update({r["path"]: r["sha256"] for r in csv.DictReader(f)})
    rows = read_symbols()
    if sorted(MANIFEST) != data_paths(rows):
        raise prereg.PreregError("the data manifest does not list exactly the files this run reads")
    log(f"Lighter bands match {n_snap} snapshots; {len(MANIFEST)} data files in the manifest")
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    books, hops, daily, dec = [], [], [], None
    for S, Hv in PAIRS:
        cand, days = pair_hops(S, Hv, rows, log_every=50)
        log(f"{S}+{Hv}: {len(cand)} candidates, {int(cand.same.sum()) if len(cand) else 0} same-coin, {len(days)} days")
        for th in THETAS:
            h = select(cand, th) if len(cand) else cand
            label = f"{S}+{Hv} th{th * 100:g}%"
            dsc = describe(h, days, S, label)
            dsc.update({"S": S, "H": Hv, "theta": th})
            books.append(dsc)
            if len(h):
                hops.append(h.assign(book=label, net1=net(h, 1)))
            daily.append(pd.DataFrame({"book": label, "day": pd.to_datetime(days, unit="ms").date,
                                       **{f"net{m}_bp": book(h, days, m) for m in MULTS}}))
            if (S, Hv, th) == PRIMARY:
                dec = decide(dsc)
            log(f"{label}: {dsc.get('hops', 0)} hops, net1 {dsc.get('net1_bp', float('nan')):.1f} bp a hop, "
                f"{dsc.get('day1_bp', float('nan')):.2f} bp/day t {dsc.get('t1', float('nan')):.2f}")
    bk = pd.DataFrame(books)
    bk.to_csv(res / "books.csv", index=False, float_format="%.6g")
    pd.concat(hops, ignore_index=True).to_csv(res / "hops.csv.gz", index=False, float_format="%.8g")
    pd.concat(daily, ignore_index=True).to_csv(res / "daily.csv.gz", index=False, float_format="%.6g")
    fam = {"bonferroni_t": BONF_T, "books_at_or_above": int((bk.t1 >= BONF_T).sum()),
           "books_t2": int((bk.t1 >= T_BAR).sum()), "books": len(bk)}
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "primary": list(PRIMARY),
               "decision": dec, "verdict": dec["verdict"], "family": fam, "costs_bp": COST_BP,
               "lighter_bands": [[u if np.isfinite(u) else None, bp] for u, bp in LIGHTER_BANDS],
               "inputs": shas}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {dec['verdict']} {dec['checks']}; family {fam}")


if __name__ == "__main__":
    main()
