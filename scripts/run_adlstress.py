"""adlstress_v1 (R487, M534, gate 0): a worst-case auto-deleveraging (ADL) stress bound on 2025-10-10 for the audited
cross-venue carry books.

Per pair exposed over the UTC day D = 2025-10-10 (engine timing: entry_day <= D < exit_day; day d's instant is 00:00
UTC and the pair is held over the UTC day d -> d + 1):
    profitable leg = the short if close < open of D's UTC candle on the short venue (the long venue's candle if the
                     short's is missing), else the long
    stressed if the profitable leg's venue is in the scenario's ADL set; the other leg is left naked
    naked long:  r = (H - L) / H of its venue's D candle       naked short: r = (H - L) / L
    N = notional of the naked leg at the reference price (H for a long, L for a short) in units of its entry notional
        = ref / P_e, P_e = the venue's close at 00:00 UTC of entry_day (engine q = 1 / P_e), so r x N = (H - L) / P_e
    loss_c = r x N + 2 x c x N, c = 7, 14, 21 bp (one extra round trip to re-hedge)
Fills, in order and counted: D candle from the other leg's venue; else the largest (H - L) / H of the book's priced
legs on D; notional from the 2025-10-09 close over P_e on the naked venue, then the other venue, else N = 1.
Book bound (% of book capital) = 100 x sum of loss_c / (2 x K), K = 20 (lab.xfund.net). Scenarios: S1 {hyperliquid}
decides, S1B {hyperliquid, binance} and S2 (all five venues) reported. SURVIVES if S1 at 2x < the book's v2 2x net
for one month (v2_ann_2x_pct / 12); lane PASS if all six deciders survive, PARTIAL if 3-5, NULL if fewer.

The run reads only the paths passed to run(); main() supplies the lane's paths.
usage: .venv/bin/python scripts/run_adlstress.py [--no-check]
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

REGISTRY = "R487"
LANE = ROOT / "experiments" / "adlstress_v1"
SRC = (ROOT / "experiments" / "carry_v2_audit_v1" / "results", ROOT / "experiments" / "carry_v2_audit_kc_v1" / "results")
D = "2025-10-10"
DAY = 86_400_000
SLOTS = 20
COSTS = {1: 0.0007, 2: 0.0014, 3: 0.0021}
VENUES = ("binance", "gate", "hyperliquid", "kucoin", "mexc")
SCENARIOS = {"S1": ("hyperliquid",), "S1B": ("hyperliquid", "binance"), "S2": VENUES}
DECIDE = "S1"
DECIDERS = {
    "gate+hyperliquid L14d th5% K20": "R278 A",
    "binance+mexc L14d th10% K20": "R278 B",
    "gate+mexc L7d th10% K20": "R278 C",
    "binance+gate L14d th10% K20": "R390 A",
    "gate+kucoin L14d th5% K20": "R279 A",
    "binance+kucoin L14d th5% K20": "R279 B",
}
MIN_1H = 20                      # hourly bars needed to rebuild a UTC day from 1h candles
REGISTRY_VERDICT = {"PASS": "CONFIRMED", "PARTIAL": "PARTIAL", "NULL": "NULL"}


class InputError(Exception):
    pass


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


# ---------------------------------------------------------------------------------------------------------- parsing
def _frame(rows):
    df = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"]).astype(float)
    df["t"] = df["t"].astype("int64")
    return df.drop_duplicates("t").sort_values("t").reset_index(drop=True)


def parse(venue, body):
    """Candles (t = bar open in ms UTC, o, h, l, c) from one raw body."""
    if venue == "gate":
        js = json.loads(body)
        if not isinstance(js, list):
            return _frame([])
        return _frame([(int(r["t"]) * 1000, r["o"], r["h"], r["l"], r["c"]) for r in js])
    if venue == "kucoin":
        js = json.loads(body)
        return _frame([(r[0], r[1], r[2], r[3], r[4]) for r in (js.get("data") or [])])
    if venue == "mexc":
        js = json.loads(body).get("data") or {}
        n = len(js.get("time") or [])
        return _frame([(js["time"][i] * 1000, js["open"][i], js["high"][i], js["low"][i], js["close"][i])
                       for i in range(n)])
    if venue == "hyperliquid":
        js = json.loads(body)
        return _frame([(r["t"], r["o"], r["h"], r["l"], r["c"]) for r in (js if isinstance(js, list) else [])])
    if venue == "binance":
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            txt = z.read(z.namelist()[0]).decode()
        rows = [r for r in csv.reader(io.StringIO(txt)) if r and r[0][:1].isdigit()]
        return _frame([(int(r[0]), r[1], r[2], r[3], r[4]) for r in rows])
    raise ValueError(venue)


def verify_raw(raw):
    """Every file listed in the manifest exists and matches its sha256; returns the manifest."""
    raw = Path(raw)
    man = json.loads((raw / "manifest.json").read_text())
    for name, want in man["files"].items():
        got = hashlib.sha256((raw / name).read_bytes()).hexdigest()
        if got != want:
            raise InputError(f"{name}: sha256 {got} != manifest {want}")
    return man


def load_candles(raw, man):
    """{(venue, coin): {"d": daily frame, "h": hourly frame}} from the manifest's files."""
    raw, out = Path(raw), {}
    for rec in man["requests"]:
        if not rec.get("file"):
            continue
        name = rec["file"]
        venue = name.split("/")[0]
        if venue == "binance":
            coin = next((k.split("/", 1)[1] for k, v in man["legs"].items()
                         if k.startswith("binance/") and name.startswith(f"binance/{v['symbol']}-1")), None)
            kind = "h" if "-1h-" in name else "d"
        else:
            m = re.match(r"^(.*)_1([dh])(_\d+)?\.json$", name.split("/", 1)[1])
            coin, kind = (m.group(1), m.group(2)) if m else (None, None)
        if coin is None:
            continue
        try:
            df = parse(venue, (raw / name).read_bytes())
        except (ValueError, KeyError, TypeError, zipfile.BadZipFile, json.JSONDecodeError):
            df = _frame([])
        slot = out.setdefault((venue, coin), {"d": _frame([]), "h": _frame([])})
        slot[kind] = _frame(pd.concat([slot[kind], df]).to_numpy().tolist()) if len(df) else slot[kind]
    return out


# ------------------------------------------------------------------------------------------------- candle lookups
def aligned(daily):
    """True if every daily bar opens at 00:00 UTC."""
    return bool(len(daily)) and bool((daily["t"] % DAY == 0).all())


def day_ohlc(c, day=D):
    """(o, h, l, c, source) for the UTC day, or None. Daily bar if UTC-aligned, else rebuilt from >= MIN_1H 1h bars."""
    if c is None:
        return None
    t0 = ms(day)
    d = c["d"]
    if aligned(d):
        r = d[d.t == t0]
        if len(r):
            r = r.iloc[0]
            return float(r.o), float(r.h), float(r.l), float(r.c), "1d"
    h = c["h"]
    h = h[(h.t >= t0) & (h.t < t0 + DAY)] if len(h) else h
    if len(h) >= MIN_1H:
        return float(h.o.iloc[0]), float(h.h.max()), float(h.l.min()), float(h.c.iloc[-1]), "1h"
    return None


def close_at(c, instant_ms):
    """Last close at or before an instant: the daily bar ending at it if UTC-aligned, else the latest bar (daily or
    1h) that ends at or before it. None if there is none within 3 days."""
    if c is None:
        return None
    best = None
    for kind, span in (("d", DAY), ("h", DAY // 24)):
        f = c[kind]
        if not len(f):
            continue
        e = f[(f.t + span <= instant_ms) & (f.t + span > instant_ms - 3 * DAY)]
        if len(e):
            r = e.iloc[-1]
            end = int(r.t) + span
            if best is None or end > best[0]:
                best = (end, float(r.c))
    return best[1] if best else None


# ------------------------------------------------------------------------------------------------------ the bound
def pair_stress(pair, candles, adl_set, fill_r):
    """Bound for one pair. pair: dict(coin, long, short, entry_day). Returns a dict with loss_{1,2,3} (entry-notional
    units) and fill flags."""
    lv, sv, coin = pair["long"], pair["short"], pair["coin"]
    cl, cs = candles.get((lv, coin)), candles.get((sv, coin))
    ol, os_ = day_ohlc(cl), day_ohlc(cs)
    ref = os_ or ol
    rec = {"profitable": None, "naked": None, "stressed": False, "r": 0.0, "N": 0.0, "candle_fill": "",
           "notional_fill": "", "src": ""}
    if ref is not None:
        profitable = "short" if ref[3] < ref[0] else "long"
        rec["profitable"] = profitable
        adl_v = sv if profitable == "short" else lv
        if adl_v not in adl_set:
            return {**rec, **{f"loss_{k}": 0.0 for k in COSTS}}
        naked = "long" if profitable == "short" else "short"
    else:
        in_l, in_s = lv in adl_set, sv in adl_set
        if not (in_l or in_s):
            return {**rec, **{f"loss_{k}": 0.0 for k in COSTS}}
        naked = "long" if in_s else "short"          # if both legs sit on ADL venues, the long is left naked
    nv, ov = (lv, sv) if naked == "long" else (sv, lv)
    cn, co = candles.get((nv, coin)), candles.get((ov, coin))
    on, oo = day_ohlc(cn), day_ohlc(co)
    entry = ms(pair["entry_day"])
    pe_n, pe_o = close_at(cn, entry), close_at(co, entry)
    c09_n, c09_o = close_at(cn, ms(D)), close_at(co, ms(D))
    if on is not None:
        _, h, l, _, src = on
        r = (h - l) / h if naked == "long" else (h - l) / l
        refp = h if naked == "long" else l
        rec["src"] = f"{nv}:{src}"
    elif oo is not None:
        _, h, l, _, src = oo
        r = (h - l) / h if naked == "long" else (h - l) / l
        refp = None
        rec["candle_fill"] = "other_venue"
        rec["src"] = f"{ov}:{src}"
    else:
        r, refp = fill_r, None
        rec["candle_fill"] = "book_max"
    if refp is not None and pe_n:
        n = refp / pe_n
    elif c09_n and pe_n:
        n, rec["notional_fill"] = c09_n / pe_n, "naked_close_0909"
    elif c09_o and pe_o:
        n, rec["notional_fill"] = c09_o / pe_o, "other_close_0909"
    else:
        n, rec["notional_fill"] = 1.0, "unit"
    rec.update(naked=naked, stressed=True, r=float(r), N=float(n))
    for k, c in COSTS.items():
        rec[f"loss_{k}"] = float(r * n + 2.0 * c * n)
    return rec


def book_fill_r(pairs, candles):
    """The largest (H - L) / H among the book's priced legs on D (0 if none)."""
    best = 0.0
    for p in pairs:
        for v in (p["long"], p["short"]):
            o = day_ohlc(candles.get((v, p["coin"])))
            if o is not None and o[1] > 0:
                best = max(best, (o[1] - o[2]) / o[1])
    return best


def book_bound(pairs, candles, adl_set, slots=SLOTS):
    """(per-pair rows, {cost: bound in % of book capital}, counts)."""
    fill_r = book_fill_r(pairs, candles)
    rows = [{**p, **pair_stress(p, candles, adl_set, fill_r)} for p in pairs]
    pct = {k: 100.0 * sum(r[f"loss_{k}"] for r in rows) / (2.0 * slots) for k in COSTS}
    counts = {"pairs": len(rows), "stressed": sum(r["stressed"] for r in rows),
              "candle_fills": sum(bool(r["candle_fill"]) and r["stressed"] for r in rows),
              "notional_fills": sum(bool(r["notional_fill"]) and r["stressed"] for r in rows),
              "fill_r": fill_r}
    return rows, pct, counts


def book_call(bound_2x_pct, ann_2x_pct):
    return "SURVIVES" if bound_2x_pct < ann_2x_pct / 12.0 else "EXPOSED"


def lane_verdict(calls):
    n = sum(c == "SURVIVES" for c in calls)
    if n == len(calls) and n:
        return "PASS"
    if n >= 3:
        return "PARTIAL"
    return "NULL"


# --------------------------------------------------------------------------------------------------------- inputs
def frozen_inputs(prereg_path, root):
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S)
    if not block:
        raise prereg.PreregError(f"{prereg_path}: no inputs block")
    rows = [ln.split() for ln in block.group(1).strip().splitlines() if ln.strip()]
    for want, rel in rows:
        got = prereg.sha256_file(Path(root) / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
    return rows


def load_trades(src):
    t = pd.concat([pd.read_csv(Path(s) / "trades_v2.csv") for s in src], ignore_index=True)
    books = pd.concat([pd.read_csv(Path(s) / "books.csv") for s in src], ignore_index=True).set_index("book")
    daily = pd.concat([pd.read_csv(Path(s) / "daily.csv") for s in src], ignore_index=True)
    return t, books, daily


def run(lane, raw, src, root, check=True, out=None):
    lane, out = Path(lane), Path(out) if out else Path(lane)
    lines = []

    def log(*a):
        s = " ".join(str(x) for x in a)
        lines.append(s)
        print(time.strftime("%H:%M:%S"), s, flush=True)

    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md', root))} inputs match")
    man = verify_raw(raw)
    mdig = hashlib.sha256((Path(raw) / "manifest.json").read_bytes()).hexdigest()
    log(f"raw manifest {mdig[:12]}: {len(man['files'])} files verified; "
        f"{sum(1 for r in man['requests'] if not r.get('file'))} of {len(man['requests'])} requests without a body")
    candles = load_candles(raw, man)
    align = {v: {"daily_legs": sum(1 for (vv, _), c in candles.items() if vv == v and len(c["d"])),
                 "aligned_legs": sum(1 for (vv, _), c in candles.items() if vv == v and aligned(c["d"]))}
             for v in VENUES}
    log("daily alignment (legs with daily bars / UTC-aligned): "
        + ", ".join(f"{v} {a['daily_legs']}/{a['aligned_legs']}" for v, a in align.items()))
    trades, books, daily = load_trades(src)
    exposed = trades[(trades.entry_day <= D) & (trades.exit_day > D)]
    inclusive = trades[(trades.entry_day <= D) & (trades.exit_day >= D)]
    pair_rows, book_rows = [], []
    for book in sorted(trades.book.unique()):
        ann = {k: float(books.loc[book, f"v2_ann_{k}x_pct"]) for k in COSTS}
        dd = daily[(daily.book == book) & (daily.engine == "v2")].set_index("date")
        rec = {"book": book, "forward": DECIDERS.get(book, ""),
               **{f"ann_{k}x_pct": ann[k] for k in COSTS},
               **{f"month_{k}x_pct": ann[k] / 12.0 for k in COSTS},
               "net_2x_20251010_pct": float(dd.net_2x.get(D, math.nan)) * 100,
               "net_2x_20251011_pct": float(dd.net_2x.get("2025-10-11", math.nan)) * 100}
        for uni, frame in (("", exposed), ("incl_", inclusive)):
            pairs = frame[frame.book == book][["coin", "long", "short", "entry_day", "exit_day"]].to_dict("records")
            for sc, vs in SCENARIOS.items():
                rows, pct, cnt = book_bound(pairs, candles, set(vs))
                if uni:
                    rec[f"incl_{sc}_2x_pct"] = pct[2]
                    rec["incl_pairs"] = cnt["pairs"]
                    continue
                for r in rows:
                    pair_rows.append({"book": book, "scenario": sc, **r})
                for k in COSTS:
                    rec[f"{sc}_{k}x_pct"] = pct[k]
                    rec[f"{sc}_{k}x_months"] = pct[k] / (ann[k] / 12.0) if ann[k] > 0 else math.inf
                    rec[f"{sc}_{k}x_share_ann"] = pct[k] / ann[k] if ann[k] > 0 else math.inf
                rec.update({f"{sc}_{kk}": vv for kk, vv in cnt.items()})
        rec["call"] = book_call(rec[f"{DECIDE}_2x_pct"], ann[2]) if book in DECIDERS else ""
        rec["call_S2"] = book_call(rec["S2_2x_pct"], ann[2])
        book_rows.append(rec)
    tab = pd.DataFrame(book_rows)
    dec = tab[tab.book.isin(list(DECIDERS))]
    if len(dec) != len(DECIDERS):
        raise InputError(f"{len(dec)} decider books, expected {len(DECIDERS)}")
    verdict = lane_verdict(dec.call.tolist())
    for _, r in tab.iterrows():
        log(f"{r.forward or '-':6s} {r.book}: pairs {r.S1_pairs}; S1 2x {r.S1_2x_pct:.3f}% "
            f"({r.S1_2x_months:.2f} months, stressed {r.S1_stressed}); S1B 2x {r.S1B_2x_pct:.3f}%; "
            f"S2 2x {r.S2_2x_pct:.3f}% ({r.S2_2x_months:.2f} months); month 2x {r.month_2x_pct:.3f}% -> "
            f"{r.call or 'reported'}")
    log(f"verdict: {verdict} (registry {REGISTRY_VERDICT[verdict]})")
    res = out / "results"
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(pair_rows).to_csv(res / "pairs.csv", index=False, float_format="%.8f")
    tab.to_csv(res / "books.csv", index=False, float_format="%.6f")
    rep = {"registry": REGISTRY, "day": D, "decides": DECIDE, "scenarios": {k: list(v) for k, v in SCENARIOS.items()},
           "raw_manifest_sha256": mdig, "alignment": align, "exposed_pairs": int(len(exposed)),
           "inclusive_pairs": int(len(inclusive)),
           "deciders": {b: {"forward": DECIDERS[b], "call": c} for b, c in dec.set_index("book").call.items()},
           "verdict": verdict, "registry_verdict": REGISTRY_VERDICT[verdict]}
    (res / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
    (out / "run.log").write_text("\n".join(lines) + "\n")
    return rep, tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-check", action="store_true", help="skip the PREREG check (tests only)")
    a = ap.parse_args()
    run(LANE, LANE / "raw", SRC, ROOT, check=not a.no_check)


if __name__ == "__main__":
    main()
