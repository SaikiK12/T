"""Explicit test-only fixture ownership for an unchanged frozen test class.

Pandas copy-on-write can expose a read-only NumPy view from market(). Tests
which deliberately mutate their invented fixture must own those arrays.
This context changes only LevelProbabilityTests.source, not market(), data,
financial assertions, or pandas options. Use it in a single-threaded test run.
Plain discovery is not rewritten and no actual pandas3 execution is implied.
"""
import argparse
from contextlib import contextmanager
from functools import wraps
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def owned_fixture_arrays(fixture):
    """Own array storage without changing any fixture value or numeric dtype."""
    return {key: value.copy(order='K') if isinstance(value, np.ndarray) else value
            for key, value in fixture.items()}


@contextmanager
def owned_level_fixtures():
    """Temporarily copy this frozen class's invented fixture arrays only."""
    from tests.test_level_probability import LevelProbabilityTests
    original = LevelProbabilityTests.source

    @wraps(original)
    def source(self):
        return owned_fixture_arrays(original(self))

    with patch.object(LevelProbabilityTests, 'source', source):
        yield


def _run_original():
    from tests.test_level_probability import LevelProbabilityTests
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LevelProbabilityTests)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    summary = {'tests': result.testsRun, 'successful': result.wasSuccessful(),
               'errors': [case.id() for case, _ in result.errors],
               'failures': [case.id() for case, _ in result.failures],
               'skipped': [case.id() for case, _ in result.skipped]}
    return summary, stream.getvalue()


def check(out):
    """Retain expected pre-adapter failures and every original assertion after."""
    from tests.test_level_probability import LevelProbabilityTests
    out = Path(out)
    out.mkdir(parents=True)  # exclusive: never overwrite an earlier receipt
    paths = ('tests/test_level_probability.py', 'lab/level_probability.py')
    digest = lambda path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    before_sha = {path: digest(path) for path in paths}
    source_before = LevelProbabilityTests.source
    cow_before = pd.get_option('mode.copy_on_write')
    with pd.option_context('mode.copy_on_write', True):
        fixture = LevelProbabilityTests().source()
        writable_before = bool(fixture['close'].flags.writeable)
        before, before_log = _run_original()
        with owned_level_fixtures():
            writable_after = bool(LevelProbabilityTests().source()['close'].flags.writeable)
            after, after_log = _run_original()
        cow_unchanged_inside = pd.get_option('mode.copy_on_write') is True
    after_sha = {path: digest(path) for path in paths}
    expected = {
        'tests.test_level_probability.LevelProbabilityTests.test_full_constructed_model_score_account_protocol',
        'tests.test_level_probability.LevelProbabilityTests.test_hour_delay_overshoot_and_funding_entry_exclusion',
    }
    expected_baseline = (not writable_before and set(before['errors']) == expected
                         and not before['failures'] and not before['skipped'])
    restored = (source_before is LevelProbabilityTests.source
                and cow_before == pd.get_option('mode.copy_on_write') and cow_unchanged_inside)
    passed = (expected_baseline and writable_after and after['successful'] and not after['skipped']
              and before['tests'] == after['tests'] == 10 and before_sha == after_sha and restored)
    report = {'status': 'PASS' if passed else 'FAIL', 'pandas_version': pd.__version__,
              'numpy_version': np.__version__, 'copy_on_write_regime_tested': True,
              'actual_pandas3_runtime_tested': pd.__version__.split('.')[0] == '3',
              'before': before, 'after': after, 'expected_readonly_failure_reproduced': expected_baseline,
              'close_fixture_writeable_before': writable_before, 'close_fixture_writeable_after': writable_after,
              'original_source_and_pandas_option_restored': restored,
              'sha256_before': before_sha, 'sha256_after': after_sha,
              'frozen_files_byte_unchanged': before_sha == after_sha,
              'production_function_or_assertions_modified': False,
              'scope': 'invented frozen test fixtures only; explicit context, not a change to plain discovery',
              'market_outcomes_or_prospective_days': 0}
    for name, text in (('before.log', before_log), ('after.log', after_log)):
        with (out / name).open('x') as handle:
            handle.write(text)
    with (out / 'results.json').open('x') as handle:
        json.dump(report, handle, sort_keys=True, indent=2)
        handle.write('\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    result = check(parser.parse_args().out)
    print(json.dumps(result, sort_keys=True, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
