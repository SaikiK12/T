import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import qx_run


def factor_report(gross=1.0, net=-13.0, rank_ic=0.1):
    """Two valid dates, unchanged members: entry cost is paid only on the first date."""
    result = {
        "factor": "signal", "horizon_h": 24, "dates": 2, "mean_names": 30.0,
        "ic": 0.1, "rank_ic": rank_ic, "rank_ic_t": 3.0, "rank_ic_ir": 0.1, "rank_ic_pos": 0.5,
        "q_mean_bp": [-gross / 2, 0.0, 0.0, 0.0, gross / 2], "ls_bp": gross, "ls_t": 1.0,
        "turnover_top": 0.0, "turnover_bottom": 0.0,
        "ls_net_bp": net, "ls_net_t": -1.0, "ls_net_ann_pct": net * 365 / 100,
        "p_rc": 0.01, "rc_pass": True,
    }
    return {"name": "factor_fixture", "trials": 1, "coins": 30, "dates": 2, "rc_null_p95": 2.0,
            "block": 7, "survivors": ["signal 24h"], "results": [result],
            "spec": {"step_h": 24, "cost": 0.0007, "alpha": 0.05}}


class InputsTest(unittest.TestCase):
    def test_parse_and_rebuild_only_checks_lane_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane, other = root / "experiments" / "a", root / "experiments" / "b"
            lane.mkdir(parents=True)
            other.mkdir(parents=True)
            (lane / "legs.csv").write_text("x\n1\n")
            (other / "legs.csv").write_text("x\n2\n")          # same name, another lane's frozen input
            (root / "build.py").write_text(
                "import sys, pathlib\np = pathlib.Path(sys.argv[2])\np.mkdir(exist_ok=True)\n"
                "(p / 'legs.csv').write_text('x\\n1\\n')\n")
            h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            text = ("```inputs\n"
                    f"experiments/a/legs.csv  {h(lane / 'legs.csv')}\n"
                    f"experiments/b/legs.csv  {h(other / 'legs.csv')}  # hashed only\n"
                    "rebuild: python build.py --out {tmp}\n```\n")
            files, rebuild = qx_run.inputs(text)
            self.assertEqual(len(files), 2)
            self.assertEqual(rebuild, "python build.py --out {tmp}")
            with mock.patch.object(qx_run, "ROOT", root):
                qx_run.check(lane, text)                         # passes: b's legs.csv is not compared
                (lane / "legs.csv").write_text("x\n3\n")
                with self.assertRaises(SystemExit):
                    qx_run.check(lane, text)                     # hash changed


class FactorDecisionTest(unittest.TestCase):
    def test_initial_cost_is_retained_when_later_turnover_is_zero(self):
        # At 7 bp/side, first-date charge is 28 bp; net mean is (1 - 28 + 1) / 2.
        verdict, decision = qx_run.factor_decision(factor_report())
        self.assertEqual(verdict, "NULL")
        self.assertFalse(decision["signal"]["pass"])
        self.assertEqual(decision["signal"]["paid_cost_bp_day"], 14.0)
        self.assertEqual([decision["signal"][f"net_{m}x_bp_day"] for m in (1, 2, 3)],
                         [-13.0, -27.0, -41.0])

    def test_negative_direction_reverses_gross_and_keeps_full_cost_positive(self):
        verdict, decision = qx_run.factor_decision(factor_report(gross=-40.0, net=-54.0, rank_ic=-0.1))
        self.assertEqual(verdict, "PARTIAL")
        self.assertEqual(decision["signal"]["direction"], "long bottom")
        self.assertEqual([decision["signal"][f"net_{m}x_bp_day"] for m in (1, 2, 3)],
                         [26.0, 12.0, -2.0])

    def test_unavailable_or_nonfinite_daily_evidence_aborts_decision(self):
        for field in ("rank_ic", "ls_bp", "ls_net_bp"):
            for value in (None, float("nan"), float("inf"), -float("inf"), True):
                with self.subTest(field=field, value=value):
                    report = factor_report()
                    report["results"][0][field] = value
                    with self.assertRaisesRegex(ValueError, field):
                        qx_run.factor_decision(report)
        report = factor_report()
        del report["results"][0]["ls_net_bp"]
        with self.assertRaisesRegex(ValueError, "ls_net_bp"):
            qx_run.factor_decision(report)
        report = factor_report()
        report["results"][0]["horizon_h"] = 72
        with self.assertRaisesRegex(ValueError, "daily costed book"):
            qx_run.factor_decision(report)

    def test_invalid_negative_paid_cost_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "paid cost"):
            qx_run.factor_decision(factor_report(gross=1.0, net=2.0))

    def test_zero_daily_rank_ic_has_no_trade_direction(self):
        self.assertEqual(qx_run.factor_decision(factor_report(rank_ic=0.0)), ("NULL", {}))


class RunnerFixtureTest(unittest.TestCase):
    def run_fixture(self, report, kind="factors", *, policy="complete_paid_v1", hash_spec=True):
        """Use a frozen synthetic prereg and executable report stub; all writes stay in the temporary root."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane = root / "experiments" / "factor_fixture"
            lane.mkdir(parents=True)
            (root / "registry").mkdir()
            sp = lane / "spec.toml"
            spec_text = {"factors": 'factors = "unused-fixture.parquet"\n',
                         "spread": 'sets = []\n', "events": 'events = []\n'}[kind]
            if kind == "factors" and policy is not None:
                spec_text += f"factor_cost_policy = {json.dumps(policy)}\n"
            sp.write_text(spec_text)
            fixture = root / "report_fixture.json"
            fixture.write_text(json.dumps(report))
            stub = root / "engine_stub.py"
            stub.write_text(
                f"#!{sys.executable}\n"
                "from pathlib import Path\nimport sys\n"
                f"Path({str(root / 'called_kind.txt')!r}).write_text(sys.argv[1])\n"
                "out = Path(sys.argv[2]).parent / 'results' / 'report.json'\n"
                f"out.write_bytes(Path({str(fixture)!r}).read_bytes())\n")
            stub.chmod(0o755)
            pre = lane / "PREREG.md"
            pre.write_text(
                "# PREREG: factor_fixture (R999999). Synthetic runner regression\n"
                "- **Registry id:** R999999\n\n```inputs\n"
                + "".join(f"{p.relative_to(root)}  {qx_run.sha(p)}\n"
                          for p in ((sp, fixture, stub) if hash_spec else (fixture, stub)))
                + "```\n")
            digest = qx_run.prereg.freeze(pre)
            with mock.patch.object(qx_run, "ROOT", root), mock.patch.object(qx_run, "QX", stub), \
                    mock.patch.object(sys, "argv", ["qx_run.py", str(lane.relative_to(root)), "--register"]), \
                    mock.patch.object(qx_run, "log") as log:
                qx_run.main()
            return {"summary": (lane / "results" / "SUMMARY.md").read_text(),
                    "rows": qx_run.registry.rows(root / "registry" / "rounds.csv"),
                    "logs": [c.args[0] for c in log.call_args_list],
                    "kind": (root / "called_kind.txt").read_text(), "digest": digest}

    def test_factor_cli_summary_log_and_registration_share_verdict_without_engine_verdict(self):
        cases = [(factor_report(), "NULL"),
                 (factor_report(gross=-40.0, net=-54.0, rank_ic=-0.1), "PARTIAL")]
        for report, verdict in cases:
            with self.subTest(verdict=verdict):
                self.assertNotIn("verdict", report)              # actual engine Factor Report has no verdict field
                actual = self.run_fixture(report)
                self.assertEqual(actual["kind"], "factors")
                self.assertTrue(actual["summary"].startswith(f"# factor_fixture (R999999): {verdict}\n"))
                self.assertIn("Decision cost policy:** complete_paid_v1", actual["summary"])
                self.assertIn("1x / 2x / 3x", actual["summary"])
                self.assertEqual(len(actual["rows"]), 1)
                self.assertEqual(actual["rows"][0]["verdict"], verdict)
                self.assertEqual(actual["rows"][0]["prereg_sha"], actual["digest"])
                self.assertEqual(actual["rows"][0]["trials"], "1")
                self.assertIn("cost policy complete_paid_v1", actual["rows"][0]["notes"])
                self.assertTrue(any(str(x).startswith(f"R999999 {verdict}; survivors") for x in actual["logs"]))
                self.assertTrue(any("cost policy complete_paid_v1" in str(x) for x in actual["logs"]))

    def test_legacy_or_unknown_policy_aborts_before_rebuild_engine_or_registration(self):
        for policy in (None, "mean_turnover_v0"):
            with self.subTest(policy=policy), mock.patch.object(qx_run, "check") as check, \
                    mock.patch.object(qx_run.subprocess, "run") as run, \
                    mock.patch.object(qx_run.registry, "append") as append:
                with self.assertRaisesRegex(SystemExit, "original frozen commit"):
                    self.run_fixture(factor_report(), policy=policy)
                check.assert_not_called()
                run.assert_not_called()
                append.assert_not_called()

    def test_policy_spec_must_be_listed_in_frozen_inputs_before_any_compute(self):
        with mock.patch.object(qx_run, "check") as check, \
                mock.patch.object(qx_run.subprocess, "run") as run, \
                mock.patch.object(qx_run.registry, "append") as append:
            with self.assertRaisesRegex(SystemExit, "spec.toml in frozen inputs"):
                self.run_fixture(factor_report(), hash_spec=False)
            check.assert_not_called()
            run.assert_not_called()
            append.assert_not_called()

    def test_factor_engine_verdict_cannot_override_complete_cost_decision(self):
        report = factor_report()
        report["verdict"] = "PARTIAL"
        actual = self.run_fixture(report)
        self.assertEqual(actual["rows"][0]["verdict"], "NULL")
        self.assertTrue(actual["summary"].startswith("# factor_fixture (R999999): NULL\n"))
        self.assertTrue(any(str(x).startswith("R999999 NULL; survivors") for x in actual["logs"]))

    def test_missing_costed_evidence_does_not_register(self):
        report = factor_report()
        report["results"][0]["ls_net_bp"] = None
        with mock.patch.object(qx_run.registry, "append") as append:
            with self.assertRaisesRegex(ValueError, "ls_net_bp"):
                self.run_fixture(report)
            append.assert_not_called()

    def test_event_and_spread_paths_keep_their_renderer_and_registry_behavior(self):
        for kind, renderer in (("events", "summary"), ("spread", "spread_summary")):
            with self.subTest(kind=kind):
                stats = [{"mean_pct": 1.0, "ann_pct": 1.0, "t": 3.0, "t_nw": 2.5}] * 3
                report = {"name": "fixture", "trials": 1, "verdict": "PARTIAL", "survivors": ["fixture"],
                          "strategies": [{"label": "fixture", "stats": stats, "p_rc": 0.01}]}
                with mock.patch.object(qx_run, renderer, return_value=f"synthetic {kind}\n") as render:
                    actual = self.run_fixture(report, kind)
                    render.assert_called_once()
                self.assertEqual(actual["kind"], kind)
                self.assertEqual(actual["summary"], f"synthetic {kind}\n")
                self.assertEqual(actual["rows"][0]["verdict"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
