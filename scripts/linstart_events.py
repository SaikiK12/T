"""Linear-vesting start events for linstart_v1 (R485, M538) from a DefiLlama emissions snapshot (scripts/fetch_unlocks.py)
and OKX's public swap list. Reads the calendar and, for the ticker check only, OKX's current last price per swap.
No return, funding or price change is computed here: the outputs are frozen with the lane's PREREG before any candle
is fetched.

Token -> perp map (symbol_map.csv):
- the ticker is the one DefiLlama's index prices the token under (scripts/unlock_events.index_rows);
- an OKX USDT-margined linear crypto swap (instCategory 1, ruleType normal, state live) matches when <T>-USDT-SWAP,
  1000<T>-USDT-SWAP or 1000000<T>-USDT-SWAP is listed (multiplier 1, 1e3, 1e6). OKX quotes per unit of ctValCcy,
  so the multiplier is the instId prefix, not ctVal;
- R265's exclusions (GRAM, ETH, BNB, POL, FTM) are kept;
- check: OKX last price over (index price x multiplier) must lie in [1/3, 3] ("verified"); outside it the pair is a
  ticker collision ("mismatch", dropped); no index price or no OKX last price is "unverified" (dropped);
- two tokens on one swap: the verified one is kept if it is the only verified one; otherwise all are "collision".
- OKX lists live swaps only: delisted perps are missing (survivorship bias, stated in the PREREG).

Event rule (M538): for each mapped token, linearAllocations with unlockType linear_start in categories insiders or
privateSale; per UTC day D, the weekly-rate increase is the sum of (newRatePerWeek - previousRatePerWeek) over those
allocations dated on D. D qualifies when that increase is at least 0.25% of max supply. Per swap, a qualifying day is
kept only if it is at least 30 days after the last kept one. Label: "with_cliff" if the token has an R265-qualifying
cliff day (insiders + privateSale cliffAllocations summing to >= 1% of max supply on one UTC day,
unlock_events.cliff_days) in D-30..D+21, else "pure". Window by D: pre_window (before 2021-02-07), archive
(2021-02-07..2026-10-23), post_archive (2026-10-24 up to the snapshot day) and forward (after the snapshot day).

usage: python scripts/linstart_events.py [--snapshot data/unlocks/2026-11-13] [--out experiments/linstart_v1]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data  # noqa: E402
import unlock_events as ue  # noqa: E402

CATS = ue.CATS
EXCLUDE = ue.EXCLUDE
MIN_RATE_FRAC = 0.0025          # weekly-rate increase as a fraction of max supply
CLIFF_FRAC = ue.MIN_FRAC        # R265's 1% cliff rule
SPACING_DAYS = 30
CLIFF_BEFORE, CLIFF_AFTER = 30, 21
FIRST_D, LAST_D = "2021-02-07", "2026-10-23"
MULTS = ((1, ""), (1000, "1000"), (1_000_000, "1000000"))
DAY = ue.DAY
SNAPSHOT = "2026-11-13"
LANE = ROOT / "experiments" / "linstart_v1"


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 1_000_000)


def okx_swaps(instruments_path, tickers_path):
    """instId -> {listTime, last} for live USDT linear crypto swaps."""
    inst = json.loads(Path(instruments_path).read_text())["data"]
    last = {t["instId"]: t.get("last") for t in json.loads(Path(tickers_path).read_text())["data"]}
    out = {}
    for d in inst:
        if (d.get("settleCcy") == "USDT" and d.get("ctType") == "linear" and d.get("state") == "live"
                and d.get("ruleType") == "normal" and d.get("instCategory") == "1"):
            px = last.get(d["instId"])
            out[d["instId"]] = {"listTime": int(d["listTime"]) if d.get("listTime") else None,
                                "last": float(px) if px not in (None, "") else np.nan}
    return out


def symbol_map(snap, instruments_path, tickers_path):
    snap = Path(snap)
    idx = ue.index_rows(snap)
    swaps = okx_swaps(instruments_path, tickers_path)
    rows = []
    for f in sorted((snap / "protocols").glob("*.json.gz")):
        x = ue.load(f)
        gid = x.get("gecko_id")
        sym, price, ms_idx = idx.get(gid, (None, None, np.nan))
        ms_file = (x.get("supplyMetrics") or {}).get("maxSupply")
        max_supply = float(ms_file) if ms_file else ms_idx
        row = {"slug": f.name[:-8], "gecko_id": gid, "ticker": sym, "max_supply": max_supply, "index_price": price,
               "inst_id": "", "mult": np.nan, "list_time_ms": np.nan, "check": "unmapped", "price_ratio": np.nan}
        if sym and sym in EXCLUDE:
            row["check"] = "excluded"
        elif sym:
            hit = next(((m, f"{p}{sym}-USDT-SWAP") for m, p in MULTS if f"{p}{sym}-USDT-SWAP" in swaps), None)
            if hit:
                m, iid = hit
                s = swaps[iid]
                row.update(inst_id=iid, mult=m, list_time_ms=s["listTime"])
                if price and np.isfinite(s["last"]):
                    ratio = s["last"] / (float(price) * m)
                    row.update(price_ratio=ratio, check="verified" if 1 / 3 <= ratio <= 3 else "mismatch")
                else:
                    row["check"] = "unverified"
        rows.append(row)
    m = pd.DataFrame(rows)
    live = m.check.isin(["verified", "unverified"])
    for iid, g in m[live].groupby("inst_id"):
        if len(g) > 1:
            ok = g.index[g.check == "verified"]
            drop = g.index.difference(ok) if len(ok) == 1 else g.index
            m.loc[drop, "check"] = "collision"
    return m


def linear_start_days(x, max_supply):
    """UTC day (ms) -> (weekly-rate increase in tokens, fraction of max supply) from insiders/privateSale
    linear_start allocations."""
    acc = {}
    for e in (x.get("metadata") or {}).get("unlockEvents") or []:
        inc = 0.0
        for a in e.get("linearAllocations") or []:
            if a.get("category") in CATS and a.get("unlockType") == "linear_start":
                inc += float(a.get("newRatePerWeek") or 0) - float(a.get("previousRatePerWeek") or 0)
        if inc != 0:
            d = int(e["timestamp"]) * 1000 // DAY * DAY
            acc[d] = acc.get(d, 0.0) + inc
    return {d: (a, a / max_supply) for d, a in sorted(acc.items())}


def label_cliff(cliffs, d):
    """Largest R265-qualifying cliff fraction in D-30..D+21 (0 if none)."""
    lo, hi = d - CLIFF_BEFORE * DAY, d + CLIFF_AFTER * DAY
    fr = [f for c, (_, f) in cliffs.items() if lo <= c <= hi and f >= CLIFF_FRAC]
    return max(fr) if fr else 0.0


def events(snap, smap, snapshot_day=SNAPSHOT):
    snap = Path(snap)
    keep = smap[smap.check == "verified"]
    raw = []
    for r in keep.itertuples():
        if not (r.max_supply and np.isfinite(r.max_supply) and r.max_supply > 0):
            continue
        x = ue.load(snap / "protocols" / f"{r.slug}.json.gz")
        cliffs = ue.cliff_days(x, r.max_supply)
        for d, (inc, frac) in linear_start_days(x, r.max_supply).items():
            if frac >= MIN_RATE_FRAC:
                cf = label_cliff(cliffs, d)
                raw.append({"inst_id": r.inst_id, "slug": r.slug, "ticker": r.ticker, "mult": r.mult, "day_ms": d,
                            "rate_increase_per_week": inc, "frac_max_supply": frac,
                            "label": "with_cliff" if cf > 0 else "pure", "cliff_frac_max": cf})
    cols = ["inst_id", "slug", "ticker", "mult", "day_ms", "rate_increase_per_week", "frac_max_supply", "label",
            "cliff_frac_max"]
    ev = pd.DataFrame(raw, columns=cols).sort_values(["inst_id", "day_ms"]).reset_index(drop=True)
    kept, last = [], {}
    for i, r in ev.iterrows():
        if r.inst_id in last and r.day_ms - last[r.inst_id] < SPACING_DAYS * DAY:
            continue
        kept.append(i)
        last[r.inst_id] = r.day_ms
    ev = ev.loc[kept].reset_index(drop=True)
    ev.insert(0, "day", pd.to_datetime(ev.day_ms, unit="ms", utc=True).dt.strftime("%Y-%m-%d"))
    ev["window"] = np.select([ev.day_ms < ms(FIRST_D), ev.day_ms <= ms(LAST_D), ev.day_ms <= ms(snapshot_day)],
                             ["pre_window", "archive", "post_archive"], "forward")
    return ev.sort_values(["day_ms", "inst_id"]).reset_index(drop=True)


def build(snap, out, instruments_path, tickers_path, snapshot_day=SNAPSHOT):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    smap = symbol_map(snap, instruments_path, tickers_path)
    smap.to_csv(out / "symbol_map.csv", index=False)
    ev = events(snap, smap, snapshot_day)
    ev.to_csv(out / "events.csv", index=False)
    return smap, ev


def dose_band(f):
    return np.select([f < 0.005, f < 0.01], ["0.25-0.5pct", "0.5-1pct"], "ge_1pct")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(data.ROOT / "unlocks" / SNAPSHOT))
    ap.add_argument("--out", default=str(LANE))
    ap.add_argument("--instruments", default=str(LANE / "okx_instruments_swap.json"))
    ap.add_argument("--tickers", default=str(LANE / "okx_tickers_swap.json"))
    a = ap.parse_args()
    smap, ev = build(a.snapshot, a.out, a.instruments, a.tickers, Path(a.snapshot).name)
    print(smap.check.value_counts().to_string())
    print(ev.groupby(["window", "label"]).size().to_string())
    arch = ev[ev.window == "archive"]
    print(arch.groupby([arch.day.str[:4], "label"]).size().unstack(fill_value=0).to_string())
    print(arch.groupby(["label", dose_band(arch.frac_max_supply)]).size().to_string())
    print("swaps with archive events:", arch.inst_id.nunique(), "pure:", arch[arch.label == "pure"].inst_id.nunique())
    print(ev[ev.window == "forward"][["day", "inst_id", "frac_max_supply", "label"]].to_string(index=False))


if __name__ == "__main__":
    main()
