from pathlib import Path
import tempfile
import unittest
from unittest import mock
import json

import numpy as np
import pandas as pd

from scripts.repair_equation_funding import targets, add_observed
from scripts.fetch_equation_history import START, H, lighter_rows
from scripts import run_equations_v2 as runner


class ExclusiveEndpoint:
    def get(self, base, path, params, lighter=False):
        start, end = params["start_timestamp"]*1000, params["end_timestamp"]*1000
        return {"fundings": [{"timestamp": int(t)//1000, "rate": ".01", "direction": "long", "value": "1"}
                              for t in np.arange(START, START+1403*H, H) if start < t < end]}


class EquationRepairTests(unittest.TestCase):
    def test_real_endpoint_boundary_contract_creates_old_seams_and_interior_queries_recover_them(self):
        c = ExclusiveEndpoint()
        frame = lighter_rows(c, 1, "funding", start=START, end=START+1402*H)
        for timestamp in (START+700*H, START+1400*H):
            self.assertFalse(frame.t.eq(timestamp).any())
            rows = lighter_rows(c, 1, "funding", start=timestamp-H, end=timestamp+H)
            old = frame.copy()
            frame = add_observed(frame, rows, timestamp)
            pd.testing.assert_frame_equal(frame[frame.t.isin(old.t)].reset_index(drop=True), old)
            self.assertTrue(frame.t.eq(timestamp).any())

    def test_target_set_is_clock_defined_and_refuses_unexplained_missing_hours(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"lighter/funding"
            p.mkdir(parents=True)
            times = START+np.arange(1, 1402)*H
            times = times[(times != START+700*H) & (times != START+1400*H)]
            pd.DataFrame({"t": times, "rate": 0.}).to_parquet(p/"TOY.parquet", index=False)
            self.assertEqual(targets(d), [["TOY", START+700*H], ["TOY", START+1400*H]])
            f = pd.read_parquet(p/"TOY.parquet")
            f[f.t.ne(START+5*H)].to_parquet(p/"TOY.parquet", index=False)
            with self.assertRaisesRegex(ValueError, "non-seam"):
                targets(d)

    def test_missing_or_revised_source_event_cannot_be_repaired_by_zero_or_overwrite(self):
        f = pd.DataFrame({"t": [START+H, START+3*H], "rate": [.001, .003], "cycle_h": 1.})
        r = pd.DataFrame({"t": [START+H, START+2*H], "rate": [.009, 0.], "cycle_h": 1.})
        with self.assertRaisesRegex(ValueError, "revised"):
            add_observed(f, r, START+2*H)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            add_observed(f, r.iloc[:1], START+2*H)

    def test_corrective_round_append_reconciles_a_lost_reply_without_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane = root/"experiments/equations_v2"
            out = lane/"results"
            out.mkdir(parents=True)
            (root/"registry").mkdir()
            runner.base.write_json(out/"verdict.json", {"verdict": "INCONCLUSIVE", "selected": None})
            runner.base.write_json(out/"manifest.json", {"prereg_sha256": "a"*64,
                                   "outputs": {"verdict.json": runner.base.sha(out/"verdict.json")}})
            real = runner.registry.append
            def lost(*args, **kwargs):
                real(*args, **kwargs)
                raise OSError("reply lost after append")
            with mock.patch.object(runner, "ROOT", root), mock.patch.object(runner, "LANE", lane), \
                 mock.patch.object(runner, "verify_family"), \
                 mock.patch.object(runner.base, "verify_inputs", return_value=("a"*64, {})):
                with mock.patch.object(runner.registry, "append", side_effect=lost):
                    runner.register(out)
                before = (root/"registry/rounds.csv").read_bytes()
                runner.register(out)
                self.assertEqual(before, (root/"registry/rounds.csv").read_bytes())
                receipt = [json.loads(p.read_text()) for p in (lane/"receipts").glob("*.json")]
                self.assertTrue(any(x["observed_exception"] for x in receipt))

    def test_audit_refuses_changed_result_before_reconstructing_cash(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out/"daily.csv.gz").write_bytes(b"old")
            runner.base.write_json(out/"manifest.json", {"prereg_sha256": "a"*64,
                                   "outputs": {"daily.csv.gz": runner.base.sha(out/"daily.csv.gz")}})
            (out/"daily.csv.gz").write_bytes(b"changed")
            with mock.patch.object(runner.base, "verify_inputs", return_value=("a"*64, {})):
                with self.assertRaisesRegex(ValueError, "changed audit input"):
                    runner.audit(out)

    def test_source_correction_refuses_a_new_cost_split_or_extra_parameter(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = root/"experiments/equations_v1"
            new = root/"experiments/equations_v2"
            old.mkdir(parents=True); new.mkdir()
            a = {"registry_id": "R310", "program_trials_before": 10, "one_way_costs": [.001, .0004],
                 "validation_start": "2026-01-01", "trials": 12}
            b = {**a, "registry_id": "R311", "program_trials_before": 22}
            runner.base.write_json(old/"settings.json", a)
            runner.base.write_json(new/"settings.json", b)
            with mock.patch.object(runner, "ROOT", root), mock.patch.object(runner, "LANE", new):
                runner.verify_family()
                runner.base.write_json(new/"settings.json", {**b, "one_way_costs": [0., 0.]})
                with self.assertRaisesRegex(ValueError, "economic parameter"):
                    runner.verify_family()
                runner.base.write_json(new/"settings.json", {**b, "extra_horizon": 30})
                with self.assertRaisesRegex(ValueError, "schema"):
                    runner.verify_family()


if __name__ == "__main__":
    unittest.main()
