import io
import unittest

from scripts.check import Result, summarize_counts


class GateAccountingTests(unittest.TestCase):
    def test_reports_methods_blocked_by_class_fixture_separately(self):
        class PassingCase(unittest.TestCase):
            def test_pass(self):
                pass

        class DirectSkipCase(unittest.TestCase):
            def test_skip(self):
                self.skipTest("synthetic direct skip")

        class FixtureSkipCase(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise unittest.SkipTest("synthetic class fixture skip")

            def test_first(self):
                self.fail("fixture-skipped test must not run")

            def test_second(self):
                self.fail("fixture-skipped test must not run")

        selected = [
            PassingCase("test_pass"),
            DirectSkipCase("test_skip"),
            FixtureSkipCase("test_first"),
            FixtureSkipCase("test_second"),
        ]
        result = unittest.TextTestRunner(
            stream=io.StringIO(), verbosity=0, resultclass=Result
        ).run(unittest.TestSuite(selected))

        counts = summarize_counts(selected, result, suite="fast", collected_count=8)

        self.assertTrue(result.wasSuccessful())
        self.assertEqual(counts["selected"], 4)
        self.assertEqual(counts["started"], 2)
        self.assertEqual(counts["direct_skipped_methods"], 1)
        self.assertEqual(counts["class_fixture_skipped_methods"], 2)
        self.assertEqual(counts["fast_deferred_methods"], 4)
        self.assertEqual(len(result.skipped), 2)
        self.assertEqual(counts["class_fixture_skips"][0]["selected_methods"], 2)
        self.assertEqual(
            summarize_counts(selected, result, suite="full", collected_count=8)["fast_deferred_methods"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
