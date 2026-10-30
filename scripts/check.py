"""One offline unittest entry point: full release gate or bounded feedback.

Fast runs omit explicit simulation classes, never silently replace the full
gate. --list shows exact membership; unknown/new tests default to fast + full.
Durations include the test body/setUp/tearDown, not module/class fixtures.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Measured on 2026-10-23, owner5bb9309. Classification is explicit semantics,
# not a clock threshold that could hide a newly slow integrity regression.
SIMULATIONS = (
    "tests.test_run_fundxs.EndToEndTest.", "tests.test_run_qbasis.EndToEndTest.",
    "tests.test_run_mlrank.EndToEndTest.", "tests.test_run_mlrank2.EndToEndTest.",
    "tests.test_policy.PowerAndSize.", "tests.test_slow_trend.Account.",
    "tests.test_screen.TestScreen.",
    "tests.test_run_capit.EndToEndTest.", "tests.test_run_intrars.EndToEndTest.",
    "tests.test_run_optflow.PlantedTest.", "tests.test_search.CatalogAndSearch.",
)


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def select(tests, mode):
    return [test for test in tests if mode == "full" or
            (test.id().startswith(SIMULATIONS)) == (mode == "simulation")]


def _class_fixture_id(test):
    """Return the class id carried by unittest's setUpClass skip holder."""
    ident = test.id() if hasattr(test, "id") else ""
    prefix = "setUpClass ("
    if ident.startswith(prefix) and ident.endswith(")"):
        return ident[len(prefix):-1]
    return None


def _test_class_id(test):
    cls = type(test)
    return f"{cls.__module__}.{cls.__qualname__}"


def summarize_counts(selected, result, suite, collected_count):
    """Distinguish started methods from methods blocked by a class fixture.

    unittest records a ``setUpClass`` SkipTest as one skip holder, even when
    several selected methods in that class were never started. Direct method
    skips are TestCase records and are included in ``result.testsRun``.
    """
    direct_skips = []
    direct_skip_methods = set()
    class_skips = []
    selected_by_class = {}
    for test in selected:
        if isinstance(test, unittest.case.TestCase):
            selected_by_class.setdefault(_test_class_id(test), []).append(test)

    for test, reason in result.skipped:
        if isinstance(test, unittest.case.TestCase):
            direct_skips.append({"test": test.id(), "reason": reason})
            direct_skip_methods.add(test.id())
            continue
        fixture_class = _class_fixture_id(test)
        if fixture_class is not None:
            class_skips.append({
                "class": fixture_class,
                "selected_methods": len(selected_by_class.get(fixture_class, ())),
                "reason": reason,
            })

    return {
        "selected": len(selected),
        "started": result.testsRun,
        "direct_skipped_methods": len(direct_skip_methods),
        "direct_skips": direct_skips,
        "class_fixture_skipped_methods": sum(item["selected_methods"] for item in class_skips),
        "class_fixture_skips": class_skips,
        "fast_deferred_methods": collected_count - len(selected) if suite == "fast" else 0,
    }


class Result(unittest.TextTestResult):
    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        self.timings.append({"test": test.id(), "seconds": time.perf_counter() - self.started})
        super().stopTest(test)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("full", "fast", "simulation"), default="full")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--report", type=Path, help="new JSON report, outside the repository")
    args = parser.parse_args(argv)
    if args.report and (args.report.resolve().is_relative_to(ROOT) or args.report.exists()):
        parser.error("--report must be a new file outside the repository")
    discovery_started = time.perf_counter()
    tests = list(flatten(unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))))
    discovery_seconds = time.perf_counter() - discovery_started
    chosen = select(tests, args.suite)
    if args.list:
        print("\n".join(test.id() for test in chosen))
        return 0
    print(f"{args.suite}: selected {len(chosen)}/{len(tests)} tests; full suite remains the commit gate", flush=True)
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=1, resultclass=Result).run(unittest.TestSuite(chosen))
    counts = summarize_counts(chosen, result, args.suite, len(tests))
    report = {"suite": args.suite, "selected": len(chosen), "collected": len(tests),
              "started": counts["started"], "tests_run": result.testsRun,
              "direct_skipped_methods": counts["direct_skipped_methods"],
              "direct_skips": counts["direct_skips"],
              "class_fixture_skipped_methods": counts["class_fixture_skipped_methods"],
              "class_fixture_skips": counts["class_fixture_skips"],
              "fast_deferred_methods": counts["fast_deferred_methods"],
              "wall_seconds": time.perf_counter() - started,
              "successful": result.wasSuccessful(), "skipped": [(t.id(), why) for t, why in result.skipped],
              "failures": [t.id() for t, _ in result.failures], "errors": [t.id() for t, _ in result.errors],
              "timings": sorted(result.timings, key=lambda x: x["seconds"], reverse=True)}
    from lab import runtime
    from scripts.orchestrate_forward import code_version
    report.update(environment=runtime.environment(ROOT), source=code_version(ROOT), discovery_seconds=discovery_seconds)
    if args.report:
        with args.report.open("x") as stream:
            json.dump(report, stream, indent=2)
    print(f"test accounting: selected {counts['selected']}; started {counts['started']}; "
          f"direct method skips {counts['direct_skipped_methods']}; "
          f"class-fixture-skipped methods {counts['class_fixture_skipped_methods']}")
    for item in counts["class_fixture_skips"]:
        print(f"  setUpClass skipped {item['selected_methods']} selected method(s) in "
              f"{item['class']}: {item['reason']}")
    if args.suite == "fast":
        print(f"fast profile deferred {counts['fast_deferred_methods']} simulation-profile methods; "
              "full suite remains the commit gate")
    for item in report["timings"][:5]:
        print(f"{item['seconds']:.3f}s {item['test']}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
