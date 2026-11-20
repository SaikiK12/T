"""xfund_listing_v1 (R516): cross-venue funding carry in the listing phase, the days R275's book cannot trade.

- R275's engine (`lab/xfund.py`, `lab/xfund_v2.py`) needs a full 14-day funding window on both venues, and its identity
  guard needs 20 days of returns. So a pair cannot enter until about three weeks after the younger venue lists the coin.
- On Kraken-Hyperliquid (2026-11-20, descriptive), the absolute funding spread had a median of 128%/yr in the first 30
  days after Kraken listed the contract, and 18%/yr after a year.
- He, Manela, Ross & von Wachter: thin new books make the premium, and so funding, large.

This book trades only that phase, on Binance USD-M and Hyperliquid (both histories hold delisted coins):
- **Window:** the funding window is k = min(14, age of either venue) days, at least 3.
- **Eligible pair:**
  - the younger venue's funding age is 3-21 days;
  - the older venue has funded the coin for at least 30 more days;
  - the younger venue's first funding day is at least 7 days after that venue's first funding day in the data (a
    venue's own launch is not a listing).
- **Identity:** the two prices match within 5% up to a power-of-1000 multiplier (kPEPE, 1000PEPEUSDT), instead of the
  20-day return correlation.
- **Entry:** spread (short-venue minus long-venue funding over the window, annualised) at least the threshold;
  widest first, K slots.
- **Exit, first of:**
  - the spread falls below half the threshold;
  - the younger venue's age passes 35 days (the phase ends);
  - the legs' price ratio moves more than 20% from entry (v2's blowout rule);
  - a leg stops trading.
- **Accounting:** `lab.xfund_v2` (marks, notional per entry price), R275's costs of 7/14/21 bp a leg.
- **Decision:** R391's rule read on book days (a pair held or a leg paid), since the book is empty on many days.

usage: python scripts/run_xfund_listing.py events | manifest | run
- events: before the freeze. Counts eligible listing events from funding ages only; it prints nothing computed from a
  rate or a price.
- manifest: before the freeze. The sha256 of every price and funding file of the coins on both venues.
"""
import argparse
import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_carry_v2_audit as loader  # noqa: E402  (frozen R437 loader: load)
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507 runner: summarize, decide, check_inputs style)

LANE = ROOT / "experiments" / "xfund_listing_v1"
PAIR = ("binance", "hyperliquid")
PRIMARY = (0.20, 10)                  # threshold (per year), slots
SECONDARY = ((0.10, 10), (0.50, 10))  # reported, not decided
LOOKBACK, MIN_AGE, MAX_ENTRY_AGE, PHASE_END, EST_GAP, LAUNCH_GAP, TOL = 14, 3, 21, 35, 30, 7, 0.05
MULTS = (1.0, 1e3, 1e-3, 1e6, 1e-6)
COSTS = (0.0007, 0.0014, 0.0021)


def age(s, d):
    """Days of funding history on this venue through day d (1 on its first funding day)."""
    return d + 1 - s.first_fund


def same_coin(pa, pb, tol=TOL):
    if not (math.isfinite(pa) and math.isfinite(pb) and pa > 0 and pb > 0):
        return False
    r = pa / pb
    return any(abs(math.log(r / m)) <= math.log1p(tol) for m in MULTS)


def phase_pair(sa, sb, d, launch):
    """(young age, old age) if (sa, sb) is a listing-phase pair on day d, else None. `launch` maps id(series) to its
    venue's first funding day in the data."""
    ya, yb = age(sa, d), age(sb, d)
    young, old = (sa, sb) if ya <= yb else (sb, sa)
    y, o = min(ya, yb), max(ya, yb)
    if y < MIN_AGE or o - y < EST_GAP:
        return None
    if young.first_fund - launch[id(young)] < LAUNCH_GAP:
        return None
    return y, o


class ListingBook(v2.Book):
    launch: dict = None

    def spread(self, lo, hi, d):
        k = min(self.lookback, age(lo, d), age(hi, d))
        if k < MIN_AGE:
            return None
        fl, fh = lo.window(d, k), hi.window(d, k)
        if fl is None or fh is None:
            return None
        return (fh - fl) * 365.0 / k

    def candidate(self, u, c, d):
        sv, best = u.series[c], None
        for i, a in enumerate(self.vset):
            sa = sv[a]
            if sa is None or not sa.fresh[d]:
                continue
            for b in self.vset[i + 1:]:
                sb = sv[b]
                if sb is None or not sb.fresh[d]:
                    continue
                ph = phase_pair(sa, sb, d, self.launch)
                if ph is None or ph[0] > MAX_ENTRY_AGE or not same_coin(sa.val[d], sb.val[d]):
                    continue
                s = self.spread(sa, sb, d)
                if s is None:
                    continue
                lo, hi, w = (a, b, s) if s >= 0 else (b, a, -s)
                if best is None or w > best.spread:
                    best = v1.Cand(lo, hi, w)
        return best

    def exits(self, u, d, forced_fn=None):
        out, keep = [], []
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            reason = None
            if a.last_fresh < d or h.last_fresh < d:
                reason = "dead"
            elif v2.ratio_move(a, h, p, d) > math.log1p(self.blowout):
                reason = "blowout"
            elif min(age(a, d), age(h, d)) > PHASE_END:
                reason = "phase_end"
            elif a.fresh[d] and h.fresh[d]:
                w = self.spread(a, h, d)
                if w is None or w < self.threshold / 2.0:
                    reason = "spread"
            (out.append((p, reason)) if reason else keep.append(p))
        self.open = keep
        return out

    def entries(self, u, d):
        if len(self.open) >= self.slots:
            return []
        held = {p.coin for p in self.open}
        cs = []
        for c in range(len(u.keys)):
            if c in held:
                continue
            x = self.candidate(u, c, d)
            if x is not None and x.spread >= self.threshold:
                cs.append((c, x))
        cs.sort(key=lambda z: (-z[1].spread, z[0]))
        new = []
        for c, x in cs[: self.slots - len(self.open)]:
            a, h = u.series[c][x.lo], u.series[c][x.hi]
            new.append(v2.Position(c, x.lo, x.hi, d, x.spread, pl_e=float(a.val[d]), ph_e=float(h.val[d])))
        self.open.extend(new)
        return new


def launches(u, vset):
    """id(series) -> its venue's first funding day over all coins (the venue's data start)."""
    first = {}
    for v in vset:
        days = [s[v].first_fund for s in u.series if s[v] is not None and s[v].first_fund < 2**62]
        first[v] = min(days) if days else 2**62
    return {id(s[v]): first[v] for s in u.series for v in vset if s[v] is not None}


def events(u, vset, launch):
    """Eligible listing events from funding ages only: one per coin and younger venue."""
    out = []
    for c, sv in enumerate(u.series):
        if any(sv[v] is None for v in vset):
            continue
        sa, sb = sv[vset[0]], sv[vset[1]]
        if sa.first_fund >= 2**62 or sb.first_fund >= 2**62:
            continue
        d = max(sa.first_fund, sb.first_fund) + MIN_AGE - 1
        if d >= u.nd or phase_pair(sa, sb, d, launch) is None:
            continue
        young = u.names[vset[0]] if sa.first_fund > sb.first_fund else u.names[vset[1]]
        out.append({"coin": u.keys[c], "young": young,
                    "listed": str(pd.Timestamp(u.t0 + max(sa.first_fund, sb.first_fund) * v1.DAY, unit="ms").date())})
    return pd.DataFrame(out, columns=["coin", "young", "listed"])


def data_files(sp):
    """The price and funding files of every coin with both venues in the symbol table."""
    sym = pd.read_csv(ROOT / sp["symbols"], dtype=str).fillna("")
    vs = {v["name"]: v for v in sp["venues"]}
    out = []
    for _, row in sym.iterrows():
        if not all(row[v].strip() for v in PAIR):
            continue
        for v in PAIR:
            for kind in ("prices", "funding"):
                f = ROOT / "data" / vs[v][kind] / f"{row[v].strip()}.parquet"
                if f.exists():
                    out.append(f)
    return sorted(out)


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def manifest(lane=None):
    lane = Path(lane or LANE)
    if (lane / "PREREG.sha256").exists():
        raise SystemExit("frozen: the manifest is written before the freeze only")
    files = {str(f.relative_to(ROOT / "data")): sha256(f) for f in data_files(spec(lane))}
    (lane / "data_manifest.json").write_text(json.dumps({"root": "data", "files": files}, indent=1, sort_keys=True))
    print(json.dumps({"files": len(files)}))


def check_data(lane):
    m = json.loads((lane / "data_manifest.json").read_text())["files"]
    bad = [p for p, h in m.items() if not (ROOT / "data" / p).exists() or sha256(ROOT / "data" / p) != h]
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from the manifest, e.g. {bad[:3]}")
    return len(m)


def spec(lane=None):
    return tomllib.loads(Path(lane or LANE, "spec.toml").read_text())


def universe(sp):
    return loader.load(sp, v2, set(PAIR))


def run_book(u, vset, launch, th, k, w0):
    b = ListingBook(vset, LOOKBACK, th, k)
    b.launch = launch
    rows, trades = v2.replay(u, b, w0)
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["gross"] = tr.price_pnl + tr.funding_pnl
        tr["funding"] = tr.funding_pnl
    else:
        tr = pd.DataFrame(columns=["coin", "long", "short", "gross", "funding"])
    return rows, tr


def book_days(rows):
    """Days the book holds a pair or pays a leg: R391's rule is read on these (an empty day is not a book day)."""
    return rows[(rows.held > 0) | (rows.legs > 0)].reset_index(drop=True)


def report(rows, tr, k, t0):
    r, _ = base.summarize(book_days(rows), tr, k, COSTS[0])
    x = v2.net(rows, k, COSTS[0]).to_numpy(float)
    r["calendar_days"] = int(len(x))
    r["calendar_ann_pct"] = {f"{m}x": float(v2.net(rows, k, c).mean() * 365 * 100) if len(rows) else None
                             for m, c in zip((1, 2, 3), COSTS)}
    r["by_year_1x_calendar"] = base.by_year(rows, k, COSTS[0], t0) if len(rows) else {}
    used = (rows.held.to_numpy(float) / k).sum()
    r["ann_on_deployed_1x_pct"] = float(x.sum() / used * 365 * 100) if used > 0 else None   # per unit of capital in use
    r["share_days_held"] = float((rows.held > 0).mean()) if len(rows) else 0.0
    if len(tr):
        r["exit_reasons"] = {str(a): int(b) for a, b in tr.reason.value_counts().items()}
        r["mean_hold_days"] = float((tr.exit_day - tr.entry_day).mean())
        r["by_short_venue_trades"] = {str(a): int(b) for a, b in tr.short.value_counts().items()}
    return r


def run(lane=None):
    from lab.prereg import verify
    lane = Path(lane or LANE)
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    n_files = check_data(lane)
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    sp = spec(lane)
    u = universe(sp)
    vset = [u.names.index(v) for v in PAIR]
    launch = launches(u, vset)
    ev = events(u, vset, launch)
    w0 = int((pd.Timestamp(sp["book_start"], tz="UTC").value // 10**6 - u.t0) // v1.DAY)
    rep = {"window": [sp["book_start"], sp["end"]], "data_files_verified": n_files, "events": int(len(ev)),
           "events_by_young": {str(a): int(b) for a, b in ev.young.value_counts().items()}}
    rows, tr = run_book(u, vset, launch, *PRIMARY, w0)
    rep["primary"] = report(rows, tr, PRIMARY[1], u.t0)
    rep["verdict"], rep["checks"] = base.decide(rep["primary"])
    for th, k in SECONDARY:
        r2, t2 = run_book(u, vset, launch, th, k, w0)
        rep[f"secondary_th{round(th * 100)}"] = report(r2, t2, k, u.t0)
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"day": rows.day, "date": pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.date,
                  **{f"net_{m}x": v2.net(rows, PRIMARY[1], c) for m, c in zip((1, 2, 3), COSTS)},
                  "gross": rows.gross, "funding": rows.funding, "legs": rows.legs, "held": rows.held}
                 ).to_csv(res / "daily.csv", index=False)
    tr.to_csv(res / "trades.csv", index=False)
    ev.to_csv(res / "events.csv", index=False)
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    p = rep["primary"]
    print(json.dumps({"verdict": rep["verdict"], "checks": rep["checks"],
                      **{x: p.get(x) for x in ("n", "ann_1x_pct", "ann_2x_pct", "ann_3x_pct", "t_nw_1x", "avg_held",
                                               "trades", "exit_reasons")}}, default=str))
    return rep


def count(lane=None):
    """Before the freeze: listing events by year and younger venue, from funding ages only."""
    sp = spec(lane)
    u = universe(sp)
    vset = [u.names.index(v) for v in PAIR]
    ev = events(u, vset, launches(u, vset))
    ev["year"] = ev.listed.str[:4]
    print(ev.groupby(["year", "young"]).size().unstack(fill_value=0).to_string())
    print(json.dumps({"events": len(ev)}))
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("events", "manifest", "run"))
    a = ap.parse_args(argv)
    {"events": count, "manifest": manifest, "run": run}[a.cmd]()


if __name__ == "__main__":
    main()
