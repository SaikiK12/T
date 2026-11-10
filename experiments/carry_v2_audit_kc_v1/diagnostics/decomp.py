"""R438 post-hoc diagnostic (descriptive, no decision), as R437's diagnostics/decomp.py: per book and engine, mean
slots held and annualised funding, price and cost P&L on book capital; for v2 the price P&L by exit reason; then v2
with the P&L of blowout and dead-leg trades removed day by day (costs kept)."""
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lab import xfund as v1, xfund_v2 as v2  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402
from scripts import run_carry_v2_audit as base, run_carry_v2_audit_kc as r  # noqa: E402

spec = tomllib.loads((r.RUN277 / "spec.toml").read_text())
need = {v for s, *_ in r.BOOKS for v in s.split("+")}
u1 = base.load(spec, v1, need)
u2 = base.load(spec, v2, need)
for s, l, th, k, fwd in r.BOOKS:
    rec = {"book": base.label(s, l, th, k)}
    for name, u, mod in (("v1", u1, v1), ("v2", u2, v2)):
        rows, trades, nets = base.run_book(u, mod, s, l, th, k, spec["costs"])
        n = len(rows)
        ann = lambda x: round(float(x) / (2 * k) / n * 365 * 100, 2)  # noqa: E731
        rec[name] = {"held": round(float(rows.held.mean()), 2), "funding_pct": ann(rows.funding.sum()),
                     "price_pct": ann((rows.gross - rows.funding).sum()),
                     "cost_pct": ann((spec["costs"][0] * rows.legs).sum()),
                     "net_pct": round(float(nets[1].mean() * 365 * 100), 2), "trades": len(trades)}
        if name == "v2":
            tr = pd.DataFrame(trades)
            rec[name]["price_by_reason_pct"] = {rs: ann(g.price_pnl.sum()) for rs, g in tr.groupby("reason")}
            rec[name]["exits"] = tr.reason.value_counts().to_dict()
    print(json.dumps(rec), flush=True)


class LogBook(v2.Book):
    def interval(self, u, d):
        out = super().interval(u, d)
        for p in self.open:
            self.log.append((d, u.keys[p.coin], p.entry_day, p.price_pnl + p.funding_pnl))
        return out


print("SENSITIVITY", flush=True)
for s, l, th, k, fwd in r.BOOKS:
    vset = [u2.names.index(v) for v in s.split("+")]
    b = LogBook(vset, l, th, k)
    b.log = []
    rows, trades = v2.replay(u2, b, v2.window_start(u2, vset, l))
    tr = pd.DataFrame(trades)
    bad = {(c, e) for c, e, rs in zip(tr.coin, tr.entry_day, tr.reason) if rs in ("blowout", "dead")}
    lg = pd.DataFrame(b.log, columns=["day", "coin", "entry", "cum"])
    lg["inc"] = lg.groupby(["coin", "entry"]).cum.diff().fillna(lg.cum)
    lg = lg[[(c, e) in bad for c, e in zip(lg.coin, lg.entry)]]
    sub = lg.groupby("day").inc.sum()
    g = rows.gross.to_numpy() - rows.day.map(sub).fillna(0.0).to_numpy()
    net = (g - spec["costs"][0] * rows.legs.to_numpy()) / (2 * k)
    net2 = (g - spec["costs"][1] * rows.legs.to_numpy()) / (2 * k)
    _, mu, t = newey_west_t(net, 10)
    h = len(net) // 2
    print(json.dumps({"book": base.label(s, l, th, k), "excl_trades": len(bad), "ann_1x": round(mu * 365 * 100, 2),
                      "ann_2x": round(float(net2.mean()) * 365 * 100, 2), "nw_t": round(t, 2),
                      "half1_bp": round(float(net[:h].mean()) * 1e4, 2),
                      "half2_bp": round(float(net[h:].mean()) * 1e4, 2)}), flush=True)
