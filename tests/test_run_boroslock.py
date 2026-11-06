import unittest

import numpy as np
import pandas as pd

from scripts import run_boroslock as R

H = 3600


def synth(period=8 * H, days=20, rate=1e-4, miss=()):
    """A market listed at day 0 + 5 min, maturing at day `days`; venue events every `period` s from day 0;
    Boros copies each event 10 s later (except indices in `miss`)."""
    T = days * 86400
    vt = np.arange(0, T + 1, period, dtype=np.int64)
    vf = pd.DataFrame({"ts": vt, "rate": rate, "apr": rate * R.YEAR / period})
    st = [{"timestamp": 300, "settlementApr": 0.0}]
    st += [{"timestamp": int(t) + 10, "settlementApr": rate * R.YEAR / period}
           for i, t in enumerate(vt) if t > 300 and i not in miss]
    st = pd.DataFrame(st)
    hours = np.arange(0, T + 1, H, dtype=np.int64)
    md = pd.DataFrame({"timestamp": hours, "bestBid": 0.08, "bestAsk": 0.081, "notionalOI": 10.0})
    mk = {"name": "1-X", "venue": "BINANCE", "coin": "BTC", "token": 1, "maturity": T, "taker": 5e-4,
          "settle": 1e-3, "period": period}
    return md, st, vf, mk


class BorosLock(unittest.TestCase):
    def test_perfect_oracle_delivers_the_lock(self):
        for period in (8 * H, H):
            md, st, vf, mk = synth(period=period)
            rows = R.entries(md, st, vf, mk, lambda t: 0.04)
            self.assertEqual(len(rows), 20 - R.MIN_DAYS)
            for r in rows:
                self.assertAlmostEqual(r["fidelity"], 0.0, places=12)
                self.assertAlmostEqual(r["realized"], 0.08 - 1.5e-3, places=12)
                self.assertEqual(r["t0"] % 86400, R.ENTRY_HOUR * H)

    def test_a_missed_settlement_shows_as_fidelity(self):
        md, st, vf, mk = synth(miss=(30,))           # the event at day 10 is never settled on Boros
        rows = R.entries(md, st, vf, mk, lambda t: 0.04)
        r0 = rows[0]                                  # entry at day 0 04:00, tau = (20 d - 4 h) / year
        tau = (mk["maturity"] - r0["t0"]) / R.YEAR
        self.assertAlmostEqual(r0["fidelity"], 1e-4 / tau, places=12)
        late = [r for r in rows if r["t0"] > 10 * 86400]
        self.assertTrue(all(abs(r["fidelity"]) < 1e-12 for r in late))

    def test_match_counts_misses_and_listing(self):
        md, st, vf, mk = synth(miss=(30, 31))
        m, n_v, n_miss = R.match(st, vf, mk["maturity"])
        self.assertEqual(n_v, 60)                     # events at 8 h .. 20 d
        self.assertEqual(n_miss, 2)
        self.assertEqual(len(m), len(st) - 1)         # the listing event is left out
        self.assertTrue(m.apr.notna().all())
        ok = m[m.apr.notna()]
        self.assertTrue(((ok.settlementApr - ok.apr).abs() < 1e-15).all())

    def test_carry_scales_costs_and_subtracts_tbill(self):
        md, st, vf, mk = synth()
        r = R.entries(md, st, vf, mk, lambda t: 0.04)[0]
        tau = (mk["maturity"] - r["t0"]) / R.YEAR
        self.assertAlmostEqual(r["carry_2x"], 0.08 - 2 * 1.5e-3 - 2 * R.HEDGE_RT / tau - 0.04, places=12)

    def test_verdict_needs_every_check(self):
        d = {"oracle_within_1bp_share": 1.0, "fidelity_bp": {"median_abs": 1.0, "p95_abs": 60.0}}
        self.assertEqual(R.verdict(d, 100, 0)["verdict"], "LOCK_DEVIATES")
        d["fidelity_bp"]["p95_abs"] = 40.0
        self.assertEqual(R.verdict(d, 100, 0)["verdict"], "LOCK_HOLDS")
        self.assertEqual(R.verdict(d, 100, 2)["verdict"], "LOCK_DEVIATES")


if __name__ == "__main__":
    unittest.main()
