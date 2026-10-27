import io
import unittest

import numpy as np
import pandas as pd

from scripts.check_level_fixture_ownership import owned_fixture_arrays, owned_level_fixtures


class LevelFixtureOwnershipTests(unittest.TestCase):
    def test_owned_copy_is_equal_and_mutation_cannot_change_original_fixture(self):
        from tests.test_level_probability import LevelProbabilityTests
        with pd.option_context('mode.copy_on_write', True):
            original = LevelProbabilityTests().source()
            self.assertFalse(original['close'].flags.writeable)
            owned = owned_fixture_arrays(original)
            self.assertEqual(owned.keys(), original.keys())
            for name, array in original.items():
                np.testing.assert_array_equal(owned[name], array)
                self.assertEqual(owned[name].dtype, array.dtype)
                self.assertTrue(owned[name].flags.writeable)
                self.assertTrue(owned[name].flags.owndata)
                self.assertFalse(np.shares_memory(owned[name], array))
            old = original['close'][73]
            owned['close'][73] = 99999
            self.assertEqual(original['close'][73], old)

    def test_context_restores_source_and_does_not_disable_copy_on_write_on_exception(self):
        from tests.test_level_probability import LevelProbabilityTests
        original = LevelProbabilityTests.source
        global_cow = pd.get_option('mode.copy_on_write')
        with pd.option_context('mode.copy_on_write', True):
            with self.assertRaisesRegex(RuntimeError, 'intentional'):
                with owned_level_fixtures():
                    self.assertTrue(pd.get_option('mode.copy_on_write'))
                    self.assertTrue(LevelProbabilityTests().source()['close'].flags.writeable)
                    raise RuntimeError('intentional')
            self.assertIs(LevelProbabilityTests.source, original)
            self.assertTrue(pd.get_option('mode.copy_on_write'))
            self.assertFalse(LevelProbabilityTests().source()['close'].flags.writeable)
        self.assertEqual(pd.get_option('mode.copy_on_write'), global_cow)

    def test_every_original_financial_assertion_passes_with_owned_fixtures(self):
        from tests.test_level_probability import LevelProbabilityTests
        source = LevelProbabilityTests.source
        stream = io.StringIO()
        with pd.option_context('mode.copy_on_write', True), owned_level_fixtures():
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(LevelProbabilityTests)
            result = unittest.TextTestRunner(stream=stream).run(suite)
        self.assertEqual(result.testsRun, 10)
        self.assertFalse(result.skipped)
        self.assertTrue(result.wasSuccessful(), stream.getvalue())
        self.assertIs(LevelProbabilityTests.source, source)


if __name__ == '__main__':
    unittest.main()
