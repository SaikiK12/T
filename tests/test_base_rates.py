"""The outside-view tool: verdict classification and Ioannidis's formulas."""
import unittest

from scripts import base_rates as br


class BaseRates(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(br.classify("# FINDINGS: x\n\n**Verdict: PASS.** All good"), "pass")
        self.assertEqual(br.classify("# FINDINGS: x\n\n**Verdict: FAIL for both rules** (NULL)."), "fail")
        self.assertEqual(br.classify("# T\n**Verdict by the frozen rules: NULL** (gate 0)"), "fail")
        self.assertEqual(br.classify("# T\n**Verdict: all 7 books SURVIVE the frozen rule**"), "pass")
        self.assertEqual(br.classify("# T\n**Verdict: PARTIAL.**"), "other")
        self.assertEqual(br.classify("# T\n**Verdict: PASS by one rule, FAIL by the other.**"), "other")
        self.assertEqual(br.classify("# FINDINGS: a measurement\nno verdict here"), "other")

    def test_ioannidis(self):
        # Ioannidis's condition: a finding is more likely true than false iff (1 - beta) R > alpha
        R, power, alpha = 0.1, 0.8, 0.05
        pi = R / (R + 1)
        self.assertAlmostEqual(br.ppv(pi, power, alpha), (power * R) / (R - (1 - power) * R + alpha))
        self.assertGreater(br.ppv(pi, power, alpha), 0.5)
        self.assertLess(br.ppv(0.01 / 1.01, 0.2, 0.05), 0.5)
        self.assertAlmostEqual(br.p_pass(0.0, 0.5, 0.0026), 0.0026)
        self.assertAlmostEqual(br.implied_prior(br.p_pass(0.3, 0.5, 0.01), 0.5, 0.01), 0.3)

    def test_table_runs(self):
        t = br.table()
        self.assertGreater(sum(sum(c.values()) for c in t.values()), 100)


if __name__ == "__main__":
    unittest.main()
