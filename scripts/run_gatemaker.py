"""gatemaker_v1 (R497, M546): what a resting (maker) order earns or loses on Gate's USDT perps, measured from Gate's
public trade tape, as set out in experiments/gatemaker_v1/PREREG.md.

It prices lever 2 of research/intake/fee_map_20261116.md: rest on the wide leg of a cross-venue carry book (Gate)
and take the hedge on the tight leg (Binance) as soon as the rest fills. Every taker trade fills the resting orders
at the touch, so a trade's maker markout (the move of the mid against the maker over the next delta seconds) is
what a resting order at the touch earned before fees. A hedged leg pays the maker fee and the markout up to the hedge;
a taker pays the effective half-spread and the taker fee.

Measurement only: 0 trials, no order, no key. Public endpoints of api.gateio.ws.

usage: python scripts/run_gatemaker.py [--limit N]
"""
import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "gatemaker_v1"
OUT = LANE / "results"
GATE = "https://api.gateio.ws/api/v4/futures/usdt"
SEED = 497
BANDS = (0, 50_000, 500_000, 5_000_000, float("inf"))
PER_BAND = 15
FIRST_DAY = datetime(2026, 11, 2, tzinfo=timezone.utc)
DAYS = 14
HOURS_PER_DAY = 2
MARGIN_S = 300                       # tape read before and after each window, for the mid proxy and markouts
DELTAS = (1, 5, 60, 300)
MID_LOOKBACK_S = 300                 # a side's last price older than this gives no mid
PAGE = 1000
MAX_PAGES = 30
PACE_S = 0.12
MIN_TRADES = 100                     # core-window trades for a contract to count
MAKER_FEE_BP = 2.0                   # conservative maker fee (the listed rate is a rebate; it is reported beside)
TAKER_FEE_BP = 7.5                   # Gate's listed taker fee on every USDT perp (contract field taker_fee_rate)
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)  # noqa: E731


def frozen_inputs(prereg_path, root=ROOT):
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    rows = [ln.split() for ln in block.strip().splitlines() if ln.strip()]
    for want, rel in rows:
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
    return rows


def http(url, tries=4, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "lab/1", "Accept": "application/json"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or k == tries - 1:
                raise
            time.sleep(5.0 * (k + 1))
        except urllib.error.URLError:
            if k == tries - 1:
                raise
            time.sleep(3.0 * (k + 1))


def band(v):
    for lo, hi in zip(BANDS[:-1], BANDS[1:]):
        if lo <= v < hi:
            return f"{lo:g}-{hi:g}"
    return "unknown"


def universe(contracts, tickers, seed=SEED, per_band=PER_BAND):
    """Seeded sample of up to per_band contracts in each 24 h quote-volume band, from the USDT perps that are
    open, not delisting and have a ticker. Sorted by name before sampling, so the draw depends only on the seed."""
    vol = {t["contract"]: float(t.get("volume_24h_quote") or 0) for t in tickers}
    rows = []
    for c in sorted(contracts, key=lambda c: c["name"]):
        if c.get("in_delisting") or c.get("status", "trading") != "trading" or c["name"] not in vol:
            continue
        rows.append({"contract": c["name"], "vol24_usd": vol[c["name"]], "band": band(vol[c["name"]]),
                     "quanto": float(c.get("quanto_multiplier") or 0),
                     "maker_fee_listed_bp": float(c.get("maker_fee_rate") or "nan") * 1e4,
                     "taker_fee_listed_bp": float(c.get("taker_fee_rate") or "nan") * 1e4})
    rows = [r for r in rows if r["quanto"] > 0]
    rng = random.Random(seed)
    out = []
    for b in sorted({r["band"] for r in rows}, key=lambda s: float(s.split("-")[0])):
        pool = [r for r in rows if r["band"] == b]
        out += rng.sample(pool, min(per_band, len(pool)))
    return out


def windows(seed=SEED, first=FIRST_DAY, days=DAYS, per_day=HOURS_PER_DAY):
    """The same one-hour windows for every contract: per day, per_day distinct hours drawn with the seed."""
    rng = random.Random(seed)
    out = []
    for d in range(days):
        for h in sorted(rng.sample(range(24), per_day)):
            out.append(first + timedelta(days=d, hours=h))
    return out


def fetch_window(get, contract, start, pace=PACE_S, sleep=time.sleep):
    """Trades in [start - MARGIN_S, start + 3600 + MARGIN_S], paging back from the end; (frame, covered_from, pages).
    covered_from is the earliest time the pages reach (the window start minus the margin when complete)."""
    lo = int(start.timestamp()) - MARGIN_S
    hi = int(start.timestamp()) + 3600 + MARGIN_S
    seen, rows, to, pages = set(), [], hi, 0
    while pages < MAX_PAGES:
        sleep(pace)
        batch = get(f"{GATE}/trades?contract={contract}&limit={PAGE}&from={lo}&to={to}")
        pages += 1
        new = [t for t in batch if t["id"] not in seen]
        for t in new:
            seen.add(t["id"])
            rows.append({"id": int(t["id"]), "t": float(t.get("create_time_ms") or t["create_time"]),
                         "size": float(t["size"]), "price": float(t["price"])})
        if len(batch) < PAGE or not new:
            return pd.DataFrame(rows, columns=["id", "t", "size", "price"]), lo, pages
        to = int(min(t["t"] for t in rows[-len(new):]))
        if to <= lo:
            return pd.DataFrame(rows, columns=["id", "t", "size", "price"]), lo, pages
    x = pd.DataFrame(rows, columns=["id", "t", "size", "price"])
    return x, (float(x.t.min()) if len(x) else hi), pages


def mid_series(t, d, p, lookback=MID_LOOKBACK_S):
    """For each query time, the mean of the last taker-buy price and the last taker-sell price at or before it, each
    within `lookback` seconds; NaN otherwise. Returns a function q(times, strict) over the sorted tape (t, d, p)."""
    buy_t, buy_p = t[d > 0], p[d > 0]
    sell_t, sell_p = t[d < 0], p[d < 0]

    def last(at, tt, pp, strict):
        idx = np.searchsorted(tt, at, side="left" if strict else "right") - 1
        ok = idx >= 0
        val = np.full(len(at), np.nan)
        val[ok] = pp[idx[ok]]
        age = np.full(len(at), np.inf)
        age[ok] = at[ok] - tt[idx[ok]]
        val[age > lookback] = np.nan
        return val

    def q(at, strict=False):
        at = np.asarray(at, dtype=float)
        return (last(at, buy_t, buy_p, strict) + last(at, sell_t, sell_p, strict)) / 2
    return q


def measure(trades, start, covered_from, quanto):
    """Per-trade rows for the core window [max(start, covered_from + MARGIN_S), start + 3600): taker sign, notional,
    effective half-spread against the mid just before the trade, and maker markouts at each delta (bp; positive =
    the resting order gained)."""
    x = trades.sort_values(["t", "id"]).reset_index(drop=True)
    x = x[x["size"] != 0]
    t, p = x.t.to_numpy(), x.price.to_numpy()
    d = np.sign(x["size"].to_numpy())
    q = mid_series(t, d, p)
    s0 = max(start.timestamp(), covered_from + MARGIN_S)
    core = (t >= s0) & (t < start.timestamp() + 3600)
    if not core.any():
        return pd.DataFrame()
    tc, pc, dc = t[core], p[core], d[core]
    out = pd.DataFrame({"t": tc, "d": dc, "notional": np.abs(x["size"].to_numpy()[core]) * quanto * pc})
    m0 = q(tc, strict=True)
    out["eff_half_bp"] = dc * (pc - m0) / m0 * 1e4
    for k in DELTAS:
        mk = q(tc + k)
        out[f"mk_{k}s_bp"] = -dc * (mk - pc) / pc * 1e4
    return out


def sign_check(trades, gap_s=2.0):
    """Share of adjacent opposite-sign trade pairs within gap_s whose taker-buy price is >= the taker-sell price.
    Near 1 when a positive size means a taker buy; near 0 if the sign is reversed."""
    x = trades.sort_values(["t", "id"])
    t, p, d = x.t.to_numpy(), x.price.to_numpy(), np.sign(x["size"].to_numpy())
    pair = (np.diff(t) <= gap_s) & (d[1:] * d[:-1] < 0)
    if not pair.any():
        return np.nan, 0
    buy = np.where(d[1:] > 0, p[1:], p[:-1])[pair]
    sell = np.where(d[1:] > 0, p[:-1], p[1:])[pair]
    return float((buy >= sell).mean()), int(pair.sum())


def contract_summary(rows):
    """One contract's medians and weighted means over its core trades and windows."""
    if rows.empty:
        return {"trades": 0}
    w = rows.notional.clip(upper=None)
    out = {"trades": int(len(rows)), "notional_usd": float(w.sum())}
    v = rows.dropna(subset=["eff_half_bp"])
    out["eff_half_bp"] = float(np.average(v.eff_half_bp, weights=v.notional)) if len(v) else np.nan
    for k in DELTAS:
        c = f"mk_{k}s_bp"
        v = rows.dropna(subset=[c])
        out[f"mk_{k}s_bp_nw"] = float(np.average(v[c], weights=v.notional)) if len(v) else np.nan
        out[f"mk_{k}s_bp_tw"] = float(v[c].mean()) if len(v) else np.nan
    return out


def band_table(per):
    """Per band: contracts that count (>= MIN_TRADES core trades), and medians over them."""
    ok = per[per.trades >= MIN_TRADES].copy()
    ok["hedged_maker_bp"] = MAKER_FEE_BP - ok["mk_5s_bp_nw"]
    ok["hedged_maker_listed_bp"] = ok["maker_fee_listed_bp"] - ok["mk_5s_bp_nw"]
    ok["taker_bp"] = ok["eff_half_bp"] + TAKER_FEE_BP
    out = []
    for b, g in ok.groupby("band", sort=False):
        rec = {"band_usd": b, "contracts": int(len(g)), "sampled": int((per.band == b).sum())}
        for c in ["eff_half_bp", "taker_bp", "hedged_maker_bp", "hedged_maker_listed_bp", "flow_sell_usd_h",
                  "flow_buy_usd_h"] + [f"mk_{k}s_bp_nw" for k in DELTAS] + [f"mk_{k}s_bp_tw" for k in DELTAS]:
            rec[c] = float(g[c].median())
        rec["holds"] = bool(len(g) >= 8 and rec["hedged_maker_bp"] <= 0.5 * rec["taker_bp"])
        out.append(rec)
    return out


def verdict(bands, n_ok, sign_med):
    if not np.isfinite(sign_med) or sign_med < 0.6:
        return "INVALID"
    if n_ok < 30:
        return "INSUFFICIENT_DATA"
    judged = [b for b in bands if b["contracts"] >= 8]
    if not judged:
        return "INSUFFICIENT_DATA"
    held = sum(b["holds"] for b in judged)
    return "LEVER_HOLDS" if held == len(judged) else ("PARTIAL" if held else "LEVER_FAILS")


def run(get=http, limit=None, sleep=time.sleep):
    contracts = get(f"{GATE}/contracts")
    tickers = get(f"{GATE}/tickers")
    uni = universe(contracts, tickers)[:limit]
    wins = windows()
    log(f"universe {len(uni)} contracts; {len(wins)} windows of 1 h from {wins[0]:%Y-%m-%d} to {wins[-1]:%Y-%m-%d %H}")
    per, signs, manifest = [], [], []
    for i, u in enumerate(uni):
        rows, tape = [], []
        for w in wins:
            try:
                tr, cov, pages = fetch_window(get, u["contract"], w, sleep=sleep)
            except Exception as e:  # noqa: BLE001 - a window that fails is recorded, not fatal
                manifest.append({"contract": u["contract"], "start": w.isoformat(), "error": str(e)[:200]})
                continue
            manifest.append({"contract": u["contract"], "start": w.isoformat(), "trades": int(len(tr)),
                             "pages": pages, "truncated": bool(cov > w.timestamp() - MARGIN_S)})
            if len(tr):
                tape.append(tr)
                r = measure(tr, w, cov, u["quanto"])
                if len(r):
                    rows.append(r)
        allr = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        s = contract_summary(allr)
        sc, npairs = sign_check(pd.concat(tape, ignore_index=True)) if tape else (np.nan, 0)
        signs.append(sc)
        hours = max(1, sum(1 for m in manifest if m["contract"] == u["contract"] and "trades" in m))
        if len(allr):
            s["flow_sell_usd_h"] = float(allr.loc[allr.d < 0, "notional"].sum() / hours)
            s["flow_buy_usd_h"] = float(allr.loc[allr.d > 0, "notional"].sum() / hours)
        per.append({**u, **s, "sign_check": sc, "sign_pairs": npairs})
        log(f"[{i + 1}/{len(uni)}] {u['contract']} band {u['band']}: {s.get('trades', 0)} trades, "
            f"sign {sc:.2f}" if np.isfinite(sc) else f"[{i + 1}/{len(uni)}] {u['contract']}: no sign pairs")
    per = pd.DataFrame(per)
    for c in ["eff_half_bp", "flow_sell_usd_h", "flow_buy_usd_h"] + [f"mk_{k}s_bp_{w}" for k in DELTAS
                                                                        for w in ("nw", "tw")]:
        if c not in per:
            per[c] = np.nan
    sign_med = float(np.nanmedian(signs)) if np.isfinite(signs).any() else np.nan
    n_ok = int((per.trades >= MIN_TRADES).sum())
    bands = band_table(per) if n_ok else []
    return per, bands, manifest, {"verdict": verdict(bands, n_ok, sign_med), "contracts_counted": n_ok,
                                  "contracts_sampled": int(len(per)), "sign_check_median": sign_med,
                                  "windows": len(wins), "maker_fee_bp_assumed": MAKER_FEE_BP,
                                  "taker_fee_bp": TAKER_FEE_BP, "hedge_delta_s": 5}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="first N contracts only (plumbing checks; not a run)")
    a = ap.parse_args(argv)
    digest = prereg.verify(LANE / "PREREG.md")
    inputs = frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
    per, bands, manifest, summ = run(limit=a.limit)
    out = OUT if a.limit is None else OUT / "plumbing"
    out.mkdir(parents=True, exist_ok=True)
    per.round(4).to_csv(out / "contracts.csv", index=False)
    pd.DataFrame(manifest).to_csv(out / "windows.csv", index=False)
    (out / "summary.json").write_text(json.dumps({**summ, "prereg_sha256": digest, "bands": bands}, indent=1))
    log(f"verdict {summ['verdict']}: {summ['contracts_counted']} of {summ['contracts_sampled']} contracts counted")
    for b in bands:
        log(f"  {b['band_usd']}: n {b['contracts']}, taker {b['taker_bp']:.2f} bp, hedged maker "
            f"{b['hedged_maker_bp']:.2f} bp, markout 5 s {b['mk_5s_bp_nw']:.2f}, holds {b['holds']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
