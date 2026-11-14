"""R438 post-hoc diagnostic (descriptive, no decision): how much of v2's funding comes from notional drift.
v2 pays funding on each leg's current notional (fixed quantity x today's price). Here the same v2 books are replayed
and, for every held pair-day, funding is also computed on constant entry notional (1 per leg). The gap is the part of
v2's funding that comes from legs whose notional grew or shrank since entry. Run on this lane's two books and, as a
measured check on R437's FINDINGS (which attributed v2's funding gain to drift without measuring it), on R437's seven.
Also reported: the mean over held pair-days of the legs' notional relative to entry (1.0 = no net leverage drift).
If it is near 1 while the drift is positive, the gain is a covariance (funding spreads widen on legs whose price rose
since entry), not a book that is levered up on average."""
import json
import math
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lab import xfund_v2 as v2  # noqa: E402
from scripts import run_carry_v2_audit as base, run_carry_v2_audit_kc as kc  # noqa: E402


class DriftBook(v2.Book):
    def interval(self, u, d):
        fd = fc = 0.0
        for p in self.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            fl, fh = a.fund_on(d + 1), h.fund_on(d + 1)
            drift = fh * h.val[d] / p.ph_e - fl * a.val[d] / p.pl_e
            if math.isfinite(drift):
                fd += drift
                fc += fh - fl if math.isfinite(fh - fl) else 0.0
            nr = (a.val[d] / p.pl_e + h.val[d] / p.ph_e) / 2
            if math.isfinite(nr):
                self.n_sum += nr
                self.n_cnt += 1
        self.f_drift += fd
        self.f_const += fc
        return super().interval(u, d)


for lane, spec_dir, books in (("R438", kc.RUN277, kc.BOOKS), ("R437", base.RUN275, base.BOOKS)):
    spec = tomllib.loads((spec_dir / "spec.toml").read_text())
    u = base.load(spec, v2, {v for s, *_ in books for v in s.split("+")})
    for s, l, th, k, fwd in books:
        vset = [u.names.index(v) for v in s.split("+")]
        b = DriftBook(vset, l, th, k)
        b.f_drift = b.f_const = b.n_sum = 0.0
        b.n_cnt = 0
        rows, _ = v2.replay(u, b, v2.window_start(u, vset, l))
        ann = lambda x: round(x / (2 * k) / len(rows) * 365 * 100, 2)  # noqa: E731
        print(json.dumps({"lane": lane, "book": base.label(s, l, th, k), "forward": fwd,
                          "v2_funding_pct": ann(float(rows.funding.sum())), "check_pct": ann(b.f_drift),
                          "const_notional_funding_pct": ann(b.f_const),
                          "drift_pct": ann(b.f_drift - b.f_const),
                          "mean_notional_vs_entry": round(b.n_sum / b.n_cnt, 4) if b.n_cnt else None}), flush=True)
