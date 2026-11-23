"""R526 risk_limits_v1: what the live risk limits cost R525's design-gap books, and whether they remove the tail, as
set out in experiments/risk_limits_v1/PREREG.md.

R525's book (R275's L14d th5% K20 on `lab.xfund_v2`, R437's loader, R525's spec and symbols) with up to three limits:
- **agree:** no entry when the two legs' prices at the entry instant differ by more than AGREE (|log ratio|).
- **active:** no entry unless each leg printed (volume > 0) in at least ACTIVE of the 24 hourly bars before the entry
  instant. Only where both legs have hourly bars.
- **stop:** close both legs at the first hourly close where the legs' price ratio has moved more than STOP from entry
  and both legs printed in that hour. Funding on the stop day is prorated by the hours held. The coin is barred for
  COOL days. Only where both legs have hourly bars.

Each runs at the base timing and with R525's audit delay (entries decided on day d - 1's windows, made at day d).
A slot is 1/K = 5% of book capital, so the per-coin cap of 5% is the book itself.

usage: python scripts/run_risk_limits.py run
"""
import json
import math
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import xfund as v1  # noqa: E402
from lab import xfund_v2 as v2  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_carry_v2_audit as loader  # noqa: E402  (frozen R437 loader)
from scripts import run_gap_breadth as gb  # noqa: E402  (frozen R525: pairs, book, costs)
from scripts import run_xfund_bfx as base  # noqa: E402  (frozen R507: check_inputs)

LANE = ROOT / "experiments" / "risk_limits_v1"
SPEC = ROOT / "experiments" / "gap_breadth_v1" / "spec.toml"
R525_NETS = ROOT / "experiments" / "gap_breadth_v1" / "results" / "pair_daily_net_1x.csv"
HOURLY = ("binance", "gate", "bitfinex", "deribit")
HOURLY_FLOORLESS = ("bitfinex", "deribit")
AGREE, STOP, COOL, ACTIVE = 0.02, 0.10, 7, 20
SENS_AGREE, SENS_STOP, STOP_SLIP = 0.05, 0.20, 0.01
DAY, H = v1.DAY, v1.H


@dataclass
class LPos(v2.Position):
    stopped: bool = False


class Hourly:
    """Hourly printed bars per (coin index, venue name): bar end times (ms) and closes, volume > 0 only."""

    def __init__(self, bars):
        self.bars = bars            # {(coin, venue): (end_ms int64 sorted, close float)}

    @classmethod
    def load(cls, spec, keys, need):
        sym = pd.read_csv(ROOT / spec["symbols"], dtype=str).fillna("").set_index("key")
        out = {}
        for v in spec["venues"]:
            if v["name"] not in need or v.get("bar_h", 1) != 1:
                continue
            for c, k in enumerate(keys):
                if k not in sym.index or not any(sym.at[k, f].strip() for f in HOURLY_FLOORLESS):
                    continue                            # a pair needs an hourly floorless leg
                s = sym.at[k, v["name"]].strip()
                if not s:
                    continue
                try:
                    p = pd.read_parquet(ROOT / "data" / v["prices"] / f"{s}.parquet", columns=["t", "close", v["vol"]])
                except (FileNotFoundError, OSError):
                    continue
                t, close, vol = (p[x].to_numpy(np.float64) for x in ("t", "close", v["vol"]))
                ok = np.isfinite(t) & np.isfinite(close) & (close > 0) & np.isfinite(vol) & (vol > 0)
                end = t[ok].astype(np.int64) + H
                o = np.argsort(end, kind="stable")
                out[(c, v["name"])] = (end[o], close[ok][o])
        return cls(out)

    def has(self, c, venue):
        return (c, venue) in self.bars

    def path(self, c, venue, start, p0, n=24):
        """(price, printed) at the n hour ends start + H .. start + n H: the last printed close at or before each
        hour end (p0 before any print), and whether a bar ended exactly then."""
        end, close = self.bars[(c, venue)]
        grid = start + H * np.arange(1, n + 1, dtype=np.int64)
        i = np.searchsorted(end, grid, side="right") - 1
        lo = np.searchsorted(end, start, side="right")
        px = np.where(i >= lo, close[np.clip(i, 0, None)], p0)
        printed = (i >= 0) & (end[np.clip(i, 0, None)] == grid)
        return px, printed

    def prints(self, c, venue, end_at, hours=24):
        end, _ = self.bars[(c, venue)]
        return int(np.searchsorted(end, end_at, side="right") - np.searchsorted(end, end_at - hours * H, side="right"))


@dataclass
class Limits(v2.Book):
    delay: int = 0
    agree: float = None
    active: int = None
    stop: float = None
    cool: int = COOL
    hourly: Hourly = None
    barred: dict = field(default_factory=dict)
    counts: dict = field(default_factory=lambda: {"blocked_agree": 0, "blocked_active": 0, "stops": 0,
                                                    "stops_reverted_24h": 0})

    def _hourly_pair(self, u, c, lo, hi):
        hv = self.hourly
        return hv is not None and hv.has(c, u.names[lo]) and hv.has(c, u.names[hi])

    def entries(self, u, d):
        if len(self.open) >= self.slots:
            return []
        held = {p.coin for p in self.open}
        cs = []
        for c in range(len(u.keys)):
            if c in held or self.barred.get(c, -1) >= d:
                continue
            x = u.candidate(c, self.vset, d - self.delay, self.lookback)
            if x is None or x.spread < self.threshold:
                continue
            a, h = u.series[c][x.lo], u.series[c][x.hi]
            if not (math.isfinite(a.val[d]) and math.isfinite(h.val[d]) and a.val[d] > 0 and h.val[d] > 0):
                continue
            if self.agree is not None and abs(math.log(a.val[d] / h.val[d])) > math.log1p(self.agree):
                self.counts["blocked_agree"] += 1
                continue
            if self.active is not None and self._hourly_pair(u, c, x.lo, x.hi):
                at = u.t0 + d * DAY
                if min(self.hourly.prints(c, u.names[x.lo], at), self.hourly.prints(c, u.names[x.hi], at)) < self.active:
                    self.counts["blocked_active"] += 1
                    continue
            cs.append((c, x))
        cs.sort(key=lambda z: (-z[1].spread, z[0]))
        new = []
        for c, x in cs[: self.slots - len(self.open)]:
            a, h = u.series[c][x.lo], u.series[c][x.hi]
            new.append(LPos(c, x.lo, x.hi, d, x.spread, pl_e=float(a.val[d]), ph_e=float(h.val[d])))
        self.open.extend(new)
        return new

    def exits(self, u, d, forced_fn=None):
        stopped = [p for p in self.open if getattr(p, "stopped", False)]
        self.open = [p for p in self.open if not getattr(p, "stopped", False)]
        return [(p, "stop") for p in stopped] + super().exits(u, d, forced_fn)

    def _stop_hour(self, u, p, d):
        """(hours into the interval, long price, short price) of the stop in day d -> d + 1, or None."""
        if not self._hourly_pair(u, p.coin, p.lo, p.hi):
            return None
        a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
        if not (math.isfinite(a.val[d]) and math.isfinite(h.val[d])):
            return None
        start = u.t0 + d * DAY
        pa, ka = self.hourly.path(p.coin, u.names[p.lo], start, a.val[d])
        ph, kh = self.hourly.path(p.coin, u.names[p.hi], start, h.val[d])
        move = np.abs(np.log((pa / p.pl_e) / (ph / p.ph_e)))
        hit = np.flatnonzero(ka & kh & (move > math.log1p(self.stop)))
        if not len(hit):
            return None
        j = int(hit[0])
        later = start + (j + 1) * H
        qa, _ = self.hourly.path(p.coin, u.names[p.lo], later, pa[j])
        qh, _ = self.hourly.path(p.coin, u.names[p.hi], later, ph[j])
        if abs(math.log((qa[-1] / p.pl_e) / (qh[-1] / p.ph_e))) <= math.log1p(self.stop):
            self.counts["stops_reverted_24h"] += 1
        return j + 1, float(pa[j]), float(ph[j])

    def interval(self, u, d):
        if self.stop is None:
            return super().interval(u, d)
        gross = fund = 0.0
        unobserved = 0
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            ql, qh = 1.0 / p.pl_e, 1.0 / p.ph_e
            hit = self._stop_hour(u, p, d)
            if hit is None:
                price = ql * (a.val[d + 1] - a.val[d]) - qh * (h.val[d + 1] - h.val[d])
                if not math.isfinite(price):
                    price = 0.0
                if not (a.fresh[d + 1] and h.fresh[d + 1]):
                    price = min(price, 0.0)
                    p.unobserved += 1
                    unobserved += 1
                share = 1.0
            else:
                k, xa, xh = hit
                price = ql * (xa - a.val[d]) - qh * (xh - h.val[d])
                price = price if math.isfinite(price) else 0.0
                share = k / 24.0
                p.stopped = True
                self.barred[p.coin] = d + 1 + self.cool
                self.counts["stops"] += 1
            f = qh * h.val[d] * h.fund_on(d + 1) - ql * a.val[d] * a.fund_on(d + 1)
            f = f * share if math.isfinite(f) else 0.0
            p.price_pnl += price
            p.funding_pnl += f
            gross += price + f
            fund += f
        return gross, fund, unobserved


def stats(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return {"days": n}
    cum = np.cumsum(x)
    return {"days": n, "ann_pct": float(x.mean() * 36500), "sharpe": float(x.mean() / x.std() * np.sqrt(365)),
            "nw_t": float(newey_west_t(x, 10)[2]), "max_dd_pct": float((cum - np.maximum.accumulate(cum)).min() * 100),
            "worst_day_pct": float(x.min() * 100)}


def book(u, a, b, hourly, delay=0, agree=None, active=None, stop=None):
    """Daily nets (1x, 2x, 3x, 1x with stop slippage) as Series on dates, the trades and the limit counts."""
    vset = [u.names.index(a), u.names.index(b)]
    bk = Limits(vset, *gb.BOOK, delay=delay, agree=agree, active=active, stop=stop, hourly=hourly)
    rows, trades = v2.replay(u, bk, v2.window_start(u, vset, gb.BOOK[0]) + delay)
    if not len(rows):
        return None
    dates = pd.to_datetime(u.t0 + rows.day * v1.DAY, unit="ms").dt.normalize()
    tr = pd.DataFrame(trades)
    stops = tr[tr.reason == "stop"].groupby("exit_day").size() if len(tr) else pd.Series(dtype=float)
    slip = rows.day.map(lambda dd: stops.get(dd, 0)).to_numpy(float) * 2 * STOP_SLIP / (2 * gb.BOOK[2])
    nets = {f"{m}x": pd.Series(v2.net(rows, gb.BOOK[2], c).to_numpy(float), index=dates)
            for m, c in zip((1, 2, 3), gb.COSTS)}
    nets["1x_slip"] = nets["1x"] - slip
    return nets, tr, bk.counts


def summary(nets, tr, counts):
    s = stats(nets["1x"])
    s.update({"ann_2x_pct": float(nets["2x"].mean() * 36500), "ann_3x_pct": float(nets["3x"].mean() * 36500),
              "ann_1x_slip_pct": float(nets["1x_slip"].mean() * 36500), **counts, "trades": int(len(tr))})
    if len(tr):
        pnl = tr.price_pnl + tr.funding_pnl
        s["worst_trade_leg_pct"] = float(pnl.min() * 100)
        s["funding_share"] = float(tr.funding_pnl.sum() / pnl.sum()) if pnl.sum() else None
        w = tr.loc[pnl.idxmin()]
        s["worst_trade"] = f"{w.coin} long {w.long} short {w.short} day {w.entry_day}-{w.exit_day} {w.reason}"
    return s


VARIANTS = {  # name: (pairs, limits)
    "base": ("all", {}),
    "agree": ("all", {"agree": AGREE}),
    "agree_5pct": ("all", {"agree": SENS_AGREE}),
    "active": ("hourly", {"active": ACTIVE}),
    "stop": ("hourly", {"stop": STOP}),
    "stop_20pct": ("hourly", {"stop": SENS_STOP}),
    "all": ("hourly", {"agree": AGREE, "active": ACTIVE, "stop": STOP}),
}


def pairs(kind):
    out = [(a, b) for a in gb.FLOORLESS for b in gb.FLOOR]
    return out if kind == "all" else [(a, b) for a, b in out if a in HOURLY and b in HOURLY]


def portfolio(nets_by_pair, key):
    df = pd.concat({k: v[key] for k, v in nets_by_pair.items()}, axis=1, sort=True)
    return df.mean(axis=1, skipna=True).dropna()


def decide(rep):
    """R526's frozen rule. A limit is ADOPTED if, on its portfolio, (i) at delay 0 its 1x return is at least 80% of
    the base's, and (ii) at delay 1 its worst day and its 1x return are no worse than the base's. PASS if "all" is
    adopted and its delay-1 worst day is above -5% of book capital."""
    out = {}
    for name, (kind, _) in VARIANTS.items():
        if name == "base":
            continue
        port = "P12" if kind == "all" else "P4"
        b0, b1 = rep[port]["base"]["0"], rep[port]["base"]["1"]
        v0, v1_ = rep[port][name]["0"], rep[port][name]["1"]
        checks = {"keeps_80pct_d0": v0["ann_pct"] >= 0.8 * b0["ann_pct"],
                  "worst_day_d1_no_worse": v1_["worst_day_pct"] >= b1["worst_day_pct"],
                  "ann_d1_no_worse": v1_["ann_pct"] >= b1["ann_pct"]}
        out[name] = {"verdict": "ADOPT" if all(checks.values()) else "REJECT", "checks": checks}
    a = out["all"]
    ok = a["verdict"] == "ADOPT" and rep["P4"]["all"]["1"]["worst_day_pct"] > -5.0
    return ("PASS" if ok else "FAIL"), out


def run(lane=LANE):
    from lab.prereg import verify
    verify(lane / "PREREG.md")
    base.check_inputs(lane / "PREREG.md")
    res = lane / "results"
    if (res / "report.json").exists():
        raise SystemExit("results exist: this lane is read once")
    sp = tomllib.loads(SPEC.read_text())
    u = loader.load(sp, v2, set(gb.FLOORLESS + gb.FLOOR))
    hourly = Hourly.load(sp, u.keys, set(HOURLY))
    ref = pd.read_csv(R525_NETS, index_col=0, parse_dates=True)
    rep = {"pairs": {}, "P12": {}, "P4": {}}
    allnets = {}
    for name, (kind, lim) in VARIANTS.items():
        for delay in (0, 1):
            nets_by_pair = {}
            for a, b in pairs(kind):
                out = book(u, a, b, hourly, delay=delay, **lim)
                if out is None:
                    continue
                nets, tr, counts = out
                pn = f"{a}+{b}"
                if name == "base" and delay == 0:     # reproduce R525 before reading any limit
                    r = ref[pn].dropna()
                    x = nets["1x"].reindex(r.index)
                    if not np.allclose(x.to_numpy(), r.to_numpy(), atol=1e-12, rtol=0):
                        raise SystemExit(f"base does not reproduce R525 on {pn}")
                nets_by_pair[pn] = nets
                rep["pairs"].setdefault(pn, {}).setdefault(name, {})[str(delay)] = summary(nets, tr, counts)
                allnets[(name, delay, pn)] = nets["1x"]
            for port, kinds in (("P12", ("all",)), ("P4", ("all", "hourly"))):
                if kind not in kinds:
                    continue
                use = nets_by_pair if port == "P12" else {k: v for k, v in nets_by_pair.items()
                                                          if tuple(k.split("+")) in pairs("hourly")}
                p1 = portfolio(use, "1x")
                rep[port].setdefault(name, {})[str(delay)] = {
                    **stats(p1), "ann_2x_pct": float(portfolio(use, "2x").mean() * 36500),
                    "ann_3x_pct": float(portfolio(use, "3x").mean() * 36500),
                    "ann_1x_slip_pct": float(portfolio(use, "1x_slip").mean() * 36500),
                    "by_year_ann_pct": {int(y): float(g.mean() * 36500) for y, g in p1.groupby(p1.index.year)}}
            print(name, delay, json.dumps({k: round(v.get("ann_pct", 0), 2) for k, v in
                                           ((p, rep[p].get(name, {}).get(str(delay), {})) for p in ("P12", "P4"))}),
                  flush=True)
    rep["verdict"], rep["limits"] = decide(rep)
    rep["reproduced_r525"] = True
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({f"{n}|{d}|{p}": s for (n, d, p), s in allnets.items()}).sort_index().to_csv(res / "daily_net_1x.csv")
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], "limits": rep["limits"],
                      "P12": {k: {d: round(v[d]["ann_pct"], 2) for d in v} for k, v in rep["P12"].items()},
                      "P4": {k: {d: (round(v[d]["ann_pct"], 2), round(v[d]["worst_day_pct"], 2)) for d in v}
                             for k, v in rep["P4"].items()}}, indent=1, default=str))
    return rep


if __name__ == "__main__":
    if sys.argv[1:] != ["run"]:
        raise SystemExit("usage: python scripts/run_risk_limits.py run")
    run()
