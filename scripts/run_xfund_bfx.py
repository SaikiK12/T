"""xfund_bfx_v1: R275's cross-venue funding carry book on a venue pair never read for carry, Binance + Bitfinex.

The carry plan's "weeks" replication (docs/reviews/plan_20261117.md section 9): does the rule generalise to another
venue? It is not a validation of the forward books. Bitfinex's funding has a dead zone (no payment while the period's
average premium stays within +-CLAMP_MIN, 5 bp), unlike Binance's, so this also asks whether the rule survives a
different funding design.

Steps (each refuses unless the PREREG verifies):
1. `fetch`: the current crypto F0 list, then the frozen discovery of delisted pairs (below), then
   `scripts/fetch_bitfinex_history.py` on every pair, 2021-01-01..2026-09-30.
2. `run`: the symbol table by the frozen alias rule, then `lab.xfund` (the parity-tested Python twin of qx spread)
   on the set binance+bitfinex, R275's spec values, and the decision by R391's rule.

**Discovery of delisted pairs (frozen).** For every Binance USD-M symbol in `data/klines_1h` ending in USDT, the coin
name is the symbol without `USDT` and without a leading `1000000` or `1000`. Its Bitfinex codes are the name itself and
any code that Bitfinex's currency map (`pub:map:currency:sym`) maps to that name. A code not already listed is kept
when `candles/trade:1h:t<CODE>F0:USTF0/hist` returns at least one candle in the window (one request, `limit=1`).

**Alias rule (frozen).** A Bitfinex code's name is its currency-map name if it has one, else the code. Its Binance symbol
is the first of `NAME`, `1000NAME`, `1000000NAME`, `CODE`, `1000CODE` (each + `USDT`) present in both `data/klines_1h`
and `data/fundingRate`. A code with no Binance symbol is dropped. The engine's identity guard (30-day correlation of
daily returns >= 0.9, at least 20 days) then decides, day by day, whether the two venues trade the same coin.

usage: python scripts/run_xfund_bfx.py fetch | run
"""
import argparse
import hashlib
import json
import re
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as sps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import fetch_bitfinex_history as fb  # noqa: E402

LANE = ROOT / "experiments" / "xfund_bfx_v1"
DATA = ROOT / "data" / "bitfinex_hist"
START, END = "2021-01-01", "2026-09-30"           # inclusive days; the fetch end is exclusive 2026-10-01
PRIMARY = ("binance+bitfinex", 14, 0.05, 20)
SECONDARY = ("binance+bitfinex", 14, 0.10, 20)    # R390 C14's threshold; reported, not decided
COST = 0.0007                                     # R275: 7 bp a leg at 1x
ALPHA, N_MIN, TRIM, NW_LAG = 0.05, 60, 0.10, 10


def check_inputs(prereg=None):
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        got = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if got != digest:
            raise SystemExit(f"{path} changed since the freeze: {got} != {digest}")
    return pairs


def coin_name(symbol):
    n = symbol[:-4] if symbol.endswith("USDT") else symbol
    for p in ("1000000", "1000"):
        if n.startswith(p) and len(n) > len(p):
            return n[len(p):]
    return n


def binance_symbols(root=ROOT / "data"):
    k = {p.stem for p in (root / "klines_1h").glob("*USDT.parquet")}
    f = {p.stem for p in (root / "fundingRate").glob("*USDT.parquet")}
    return sorted(k & f)


def binance_for(code, cmap, have):
    name = cmap.get(code, code)
    for s in (name, "1000" + name, "1000000" + name, code, "1000" + code):
        if s + "USDT" in have:
            return s + "USDT"
    return None


def discovery_codes(bn_symbols, cmap, listed):
    """Codes to probe: each Binance coin name and every Bitfinex code mapped to that name, minus listed codes."""
    inv = {}
    for code, name in cmap.items():
        inv.setdefault(str(name).upper(), set()).add(code)
    out = set()
    for s in bn_symbols:
        n = coin_name(s)
        out |= {n, *inv.get(n.upper(), ())}
    return sorted(c for c in out - set(listed) if c.isascii() and c.isalnum())


def symbol_table(codes, cmap, have):
    rows = [(c, binance_for(c, cmap, have)) for c in sorted(set(codes))]
    return pd.DataFrame([{"key": c, "binance": b, "bitfinex": c} for c, b in rows if b])


def currency_map():
    return {str(a): str(b) for a, b in fb.get(f"{fb.API}/conf/pub:map:currency:sym")[0]}


# ---------- fetch ----------

def fetch():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    DATA.mkdir(parents=True, exist_ok=True)
    if not (DATA / "pairs.csv").exists():
        fb.pairs(DATA)
    cmap = currency_map()
    (DATA / "currency_map.json").write_text(json.dumps(cmap, indent=1, sort_keys=True))
    listed = pd.read_csv(DATA / "pairs.csv")
    disc_path = DATA / "discovery.csv"
    done = pd.read_csv(disc_path) if disc_path.exists() else pd.DataFrame(columns=["code", "found"])
    todo = [c for c in discovery_codes(binance_symbols(), cmap, listed.base) if c not in set(done.code)]
    t0, t1 = fb.ms(START), fb.ms("2026-10-01")
    for i, c in enumerate(todo, 1):
        r = fb.get(f"{fb.API}/candles/trade:1h:t{c}F0:USTF0/hist?start={t0}&end={t1 - 1}&limit=1&sort=1", pace=2.1)
        row = pd.DataFrame([{"code": c, "found": bool(r)}])
        row.to_csv(disc_path, mode="a", header=not disc_path.exists(), index=False)
        if i % 100 == 0:
            print(f"{time.strftime('%H:%M:%S')} discovery {i}/{len(todo)}", flush=True)
    disc = pd.read_csv(disc_path)
    found = sorted(disc[disc.found].code)
    extra = pd.DataFrame({"pair": [f"{c}F0:USTF0" for c in found], "base": found})
    allp = pd.concat([listed, extra]).drop_duplicates("base").sort_values("base")
    allp.to_csv(DATA / "pairs_all.csv", index=False)
    print(f"{len(listed)} listed + {len(found)} delisted pairs found; fetching", flush=True)
    fb.fetch("2021-01-01", "2026-10-01", [], DATA, 0.9, log=lambda *x: print(*x, flush=True),
             pairs_file=DATA / "pairs_all.csv")


# ---------- run ----------

def load_universe(sym, spec_venues, t0, nd):
    def one(row):
        out = []
        for v in spec_venues:
            s = row[v["name"]]
            out.append(xfund.load_daily(ROOT / "data" / v["prices"] / f"{s}.parquet",
                                        ROOT / "data" / v["funding"] / f"{s}.parquet", v["vol"], 1, t0, nd))
        return out

    with ThreadPoolExecutor(8) as ex:
        series = list(ex.map(one, [r for _, r in sym.iterrows()]))
    return xfund.Universe(sym.key.tolist(), [v["name"] for v in spec_venues], series, t0, nd, 30, 0.9, 20)


VENUES = [{"name": "binance", "prices": "klines_1h", "vol": "volume", "funding": "fundingRate"},
          {"name": "bitfinex", "prices": "bitfinex_hist/candles_1h", "vol": "volume", "funding": "bitfinex_hist/funding"}]


def trade_pnl(u, tr, last_day):
    """Each trade's gross (price + funding) and funding over its held days, as Book.interval adds them."""
    out = []
    for x in tr:
        c = u.keys.index(x["coin"])
        lo, hi = u.names.index(x["long"]), u.names.index(x["short"])
        a, h = u.series[c][lo], u.series[c][hi]
        end = x["exit_day"] if x["exit_day"] is not None else last_day + 1
        g = f = 0.0
        for d in range(x["entry_day"], end):
            ff = h.fund_on(d + 1) - a.fund_on(d + 1)
            g += a.ret(d) - h.ret(d) + ff
            f += ff
        out.append({**x, "gross": g, "funding": f})
    return pd.DataFrame(out)


def summarize(rows, trades, slots, cost):
    x = xfund.net(rows, slots, cost).to_numpy(float)
    out = {"n": int(len(x)), "first_day": int(rows.day.iloc[0]) if len(rows) else None,
           "avg_held": float(rows.held.mean()) if len(rows) else 0.0, "trades": int(len(trades))}
    if len(x) < 3:
        return out, x
    _, mu, t = newey_west_t(x, NW_LAG)
    out.update({"mean_1x_bp": float(mu * 1e4), "ann_1x_pct": float(mu * 365 * 100), "t_nw_1x": float(t),
                "p_one_sided": float(sps.norm.sf(t)), "trimmed_mean_bp": float(sps.trim_mean(x, TRIM) * 1e4)})
    for m in (2, 3):
        xm = xfund.net(rows, slots, cost * m).to_numpy(float)
        out[f"mean_{m}x_bp"] = float(xm.mean() * 1e4)
        out[f"ann_{m}x_pct"] = float(xm.mean() * 365 * 100)
    h = len(x) // 2
    out["halves_bp"] = [float(x[:h].mean() * 1e4), float(x[h:].mean() * 1e4)]
    eq = np.cumsum(x)
    out["max_dd_pct"] = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min() * 100)
    srt = np.sort(x)[::-1]
    out["top10_share"] = float(srt[:10].sum() / x.sum()) if x.sum() > 0 else None
    out["funding_share"] = float(rows.funding.sum() / rows.gross.sum()) if rows.gross.sum() != 0 else None
    if len(trades):
        by = ((trades.gross - 4 * cost) / (2 * slots)).groupby(trades.coin).sum().sort_values()
        top = by.index[::-1][:2].tolist()
        out["by_coin_bp_per_day"] = {c: float(v / len(x) * 1e4) for c, v in by.items()}
        out["l2co_dropped"] = top
        out["l2co_mean_bp"] = float((x.sum() - by[top].sum()) / len(x) * 1e4)
        out["by_long_venue_trades"] = {k: int(v) for k, v in trades.long.value_counts().items()}
    return out, x


def decide(r, alpha=ALPHA):
    if r.get("n", 0) < N_MIN or "p_one_sided" not in r or "l2co_mean_bp" not in r:
        return "UNREADABLE", {}
    checks = {"p_le_alpha": r["p_one_sided"] <= alpha, "mean_2x_pos": r["mean_2x_bp"] > 0,
              "trimmed_pos": r["trimmed_mean_bp"] > 0, "l2co_pos": r["l2co_mean_bp"] > 0}
    checks = {k: bool(v) for k, v in checks.items()}
    return ("PASS" if all(checks.values()) else "FAIL"), checks


def by_year(rows, slots, cost, t0):
    x = xfund.net(rows, slots, cost)
    yr = pd.to_datetime(t0 + rows.day * xfund.DAY, unit="ms").dt.year
    return {int(y): {"days": int(len(g)), "ann_pct": float(g.mean() * 365 * 100)} for y, g in x.groupby(yr)}


def book(u, spec_book, t0):
    s, l, th, k = spec_book
    vset = [u.names.index(v) for v in s.split("+")]
    rows, trades = xfund.replay(u, xfund.Book(vset, l, th, k), xfund.window_start(u, vset, l))
    tr = trade_pnl(u, trades, int(rows.day.iloc[-1]) if len(rows) else 0)
    r, x = summarize(rows, tr, k, COST)
    r["by_year_1x"] = by_year(rows, k, COST, t0) if len(rows) else {}
    if len(rows):
        r["first_date"] = str(pd.Timestamp(t0 + int(rows.day.iloc[0]) * xfund.DAY, unit="ms").date())
    return r, rows, tr


def funding_profile(sym, t0, t1):
    """Per coin, over the hours when Bitfinex has periods: the share of Bitfinex 8 h periods with a zero rate, and
    each venue's mean funding, annualised (a positive rate is paid by longs). Descriptive only."""
    out = {}
    for _, r in sym.iterrows():
        b = pd.read_parquet(ROOT / "data" / "bitfinex_hist" / "funding" / f"{r.bitfinex}.parquet", columns=["t", "rate"])
        b = b[(b.t >= t0) & (b.t < t1)]
        if b.empty:
            continue
        a = pd.read_parquet(ROOT / "data" / "fundingRate" / f"{r.binance}.parquet", columns=["t", "rate"])
        a = a[(a.t >= b.t.min()) & (a.t <= b.t.max())]
        days = max((b.t.max() - b.t.min()) / xfund.DAY, 1.0)
        out[r.key] = {"bitfinex_periods": int(len(b)), "bitfinex_zero_share": float((b.rate == 0).mean()),
                      "bitfinex_ann_pct": float(b.rate.sum() / days * 365 * 100),
                      "binance_ann_pct": float(a.rate.sum() / days * 365 * 100) if len(a) else None}
    return out


def run():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    res = LANE / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    cmap = json.loads((DATA / "currency_map.json").read_text())
    rec = sorted(p.stem for p in (DATA / "receipts").glob("*.json"))
    sym = symbol_table(rec, cmap, set(binance_symbols()))
    t0 = fb.ms(START)
    nd = int((fb.ms(END) + xfund.DAY - t0) // xfund.DAY + 1)
    u = load_universe(sym, VENUES, t0, nd)
    rep = {"symbols": len(sym), "bitfinex_codes_with_receipt": len(rec), "window": [START, END]}
    prim, rows, tr = book(u, PRIMARY, t0)
    rep["primary"] = prim
    rep["verdict"], rep["checks"] = decide(prim)
    rep["secondary_th10"], _, _ = book(u, SECONDARY, t0)
    rep["funding_profile"] = funding_profile(sym, t0, fb.ms("2026-10-01"))
    res.mkdir(parents=True, exist_ok=True)
    sym.to_csv(res / "symbols.csv", index=False)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(t0 + rows.day * xfund.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": xfund.net(rows, PRIMARY[3], COST * m) for m in (1, 2, 3)},
                  "gross": rows.gross, "funding": rows.funding, "legs": rows.legs,
                  "held": rows.held}).to_csv(res / "daily.csv", index=False)
    tr.to_csv(res / "trades.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"],
                      **{k: prim.get(k) for k in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x",
                                                  "avg_held", "trades")}}, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("fetch", "run"))
    a = ap.parse_args(argv)
    return fetch() if a.cmd == "fetch" else run()


if __name__ == "__main__":
    sys.exit(main() or 0)
