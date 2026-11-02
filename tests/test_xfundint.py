import unittest

import numpy as np

from lab import xfund
from scripts import run_xfundint as xi


def synth(nd=70):
    """Two coins on binance/gate/kucoin with the same price path, KuCoin paying more per day; coin A is a 4h contract."""
    rng = np.random.default_rng(1)
    base = np.cumprod(1 + rng.normal(0, 0.01, nd))
    fresh = np.ones(nd, bool)

    def daily(close, rate, n):
        f = np.full(nd, rate * n)
        return xfund.Daily.build(close, fresh, f, np.full(nd, n))

    series = []
    for kn in (6, 3):                                          # coin A: 4h (6 a day); coin B: 8h (3 a day)
        series.append([daily(base * (1 + rng.normal(0, 1e-4, nd)), 1e-5, 3),
                       daily(base * (1 + rng.normal(0, 1e-4, nd)), 2e-5, 3),
                       daily(base * (1 + rng.normal(0, 1e-4, nd)), 3e-4, kn)])
    return xfund.Universe(["A", "B"], ["binance", "gate", "kucoin"], series, 0, nd), {"A": "4h", "B": "8h"}


class XFundIntTest(unittest.TestCase):
    def test_label_rule(self):
        self.assertEqual(xi.label(True, True, False), "interval-artifact")
        self.assertEqual(xi.label(True, True, True), "robust")      # the post-scaling book decides first
        self.assertEqual(xi.label(True, False, False), "inconclusive")
        self.assertEqual(xi.lead_label(["robust", "robust"]), "robust")
        self.assertEqual(xi.lead_label(["robust", "inconclusive"]), "inconclusive")

    def test_day_class(self):
        u, _ = synth()
        self.assertEqual(xi.day_class(u.series[0][2], 30), "4h")
        self.assertEqual(xi.day_class(u.series[1][2], 30), "8h")

    def test_attribution_reconciles_with_replay(self):
        u, kcls = synth()
        vset = [0, 2]
        w0 = xfund.window_start(u, vset, 14)
        rows, trades = xfund.replay(u, xfund.Book(vset, 14, 0.05, 2), w0)
        self.assertGreater(len(trades), 0)
        cls, oth, held, agree, recs = xi.attribute(u, xfund.Book(vset, 14, 0.05, 2), w0, 2, kcls)
        tot = lambda k: sum(cls[c][k] for c in xi.CLASSES)
        self.assertTrue(np.allclose(tot("gross"), rows.gross, atol=1e-12))
        self.assertTrue(np.allclose(tot("fund"), rows.funding, atol=1e-12))
        self.assertTrue(np.allclose(tot("legs"), rows.legs))
        self.assertTrue(np.array_equal(held, rows.held))
        self.assertTrue(np.allclose(sum(oth[c] for c in xi.CLASSES) + tot("fundK"), rows.funding, atol=1e-12))
        self.assertEqual(agree["days"], agree["same"])             # synthetic counts match the static classes
        self.assertTrue(cls["4h"]["fund"].sum() > 0 and cls["8h"]["fund"].sum() > 0)

    def test_restrict_drops_other_classes(self):
        u, kcls = synth()
        r = xi.restrict(u, 2, kcls, "8h")
        self.assertIsNone(r.series[0][2])
        self.assertIsNotNone(r.series[1][2])
        self.assertIsNotNone(r.series[0][0])


if __name__ == "__main__":
    unittest.main()
