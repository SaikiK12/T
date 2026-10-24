import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from lab import prereg
from lab.equations import LABELS
from scripts import run_equations as runner


def account(r):
    r = np.asarray(r, float)
    n = len(r)
    equity = 10000*np.cumprod(1+r)
    net = np.diff(np.r_[10000, equity])
    return {"scored": np.ones(n, bool), "insolvent": np.zeros((n, 3), bool),
            "return": np.tile(r[:, None], (1, 3)), "net": np.tile(net[:, None], (1, 3)),
            "equity": np.tile(equity[:, None], (1, 3)), "cost": np.zeros((n, 3)),
            "price": np.tile(net[:, None], (1, 3)), "funding": np.zeros((n, 3)),
            "held": np.ones(n, int), "turnover": np.ones(n), "entries": 10,
            "gross_breach": np.zeros(n, bool), "final_quantity": np.zeros((2, 2)),
            "coin_net": np.tile(net[:, None, None]/4, (1, 4, 3))}


class EquationRunnerTests(unittest.TestCase):
    def test_complete_synthetic_run_is_reproducible_and_guards_every_input(self):
        from tests.test_equations import toy_panel
        from lab.equations import HOUR
        p = toy_panel(days=85, coins=2)
        rng = np.random.default_rng(711)
        common = np.cumsum(rng.normal(0, .0002, (len(p.times), 2)), axis=0)
        p.prices[:, :, 0] *= np.exp(common)
        p.prices[:, :, 1] = p.prices[:, :, 0]*np.exp(rng.normal(0, .00001, common.shape))
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane = root/"experiments/equations_v1"
            lane.mkdir(parents=True)
            data = root/"data/cache"
            data.mkdir(parents=True)
            table = lane/"symbols.csv"
            table.write_text("key,binance,mexc,lighter\nTOY0,TOY0,TOY0,TOY0\nTOY1,TOY1,TOY1,TOY1\n")
            for v, venue in enumerate(("mexc", "lighter")):
                meta = []
                for i, symbol in enumerate(p.keys):
                    for kind in ("prices", "funding"):
                        (data/venue/kind).mkdir(parents=True, exist_ok=True)
                    frame = pd.DataFrame({"t": p.times[1:]-HOUR, "close": p.prices[1:, i, v],
                                          "vol" if v == 0 else "volume": 1.})
                    frame.to_parquet(data/venue/"prices"/(symbol+".parquet"), index=False)
                    pd.DataFrame({"t": p.times, "rate": .00001 if v == 0 else .00010,
                                  "cycle_h": 1.}).to_parquet(data/venue/"funding"/(symbol+".parquet"), index=False)
                    meta.append({"symbol": symbol, "type": 1, "settleCoin": "USDT", "contractSize": .01,
                                 "volUnit": 1, "minVol": 1, "supported_size_decimals": 2,
                                 "min_base_amount": .01, "min_quote_amount": 1})
                runner.write_json(data/(venue+"_contracts_current.json"), meta)
            runner.write_json(data/"acquisition_status.json", {"complete": True, "errors": {}})
            runner.write_json(lane/"settings.json", {"registry_id": "R310", "labels": LABELS,
                              "trials": 12, "one_way_costs": [.001, .0004], "start": "2025-01-01",
                              "validation_start": "2025-02-15", "end_exclusive": "2025-03-27",
                              "spa_reps": 50, "paired_reps": 100, "seed": 310, "program_trials_before": 1})
            sources = list(data.rglob("*.parquet"))+list(data.glob("*.json"))+[table, lane/"settings.json"]
            runner.write_json(lane/"inputs.json", {"data_root": "data/cache", "symbols": str(table.relative_to(root)),
                              "sha256": {str(f.relative_to(root)): runner.sha(f) for f in sources}})
            (lane/"PREREG.md").write_text("Input manifest SHA-256: "+runner.sha(lane/"inputs.json"))
            prereg.freeze(lane/"PREREG.md")
            with contextlib.redirect_stdout(io.StringIO()):
                runner.run(lane/"out1", lane=lane, root=root)
                runner.run(lane/"out2", lane=lane, root=root)
            for f in (lane/"out1").iterdir():
                self.assertEqual(f.read_bytes(), (lane/"out2"/f.name).read_bytes(), f.name)
            daily = pd.read_csv(lane/"out1/daily.csv.gz")
            for m in (1, 2, 3):
                np.testing.assert_allclose(daily[f"net_{m}x"], daily[f"price_{m}x"]+daily[f"funding_{m}x"]-
                                           daily[f"cost_{m}x"], atol=1e-8)
            with self.assertRaisesRegex(ValueError, "fresh"):
                runner.run(lane/"out1", lane=lane, root=root)
            source = next(data.rglob("*.parquet"))
            with source.open("ab") as h:
                h.write(b"changed")
            with self.assertRaisesRegex(ValueError, "pinned input"):
                runner.run(lane/"out3", lane=lane, root=root)

    def test_common_calibration_risk_only_downsizes_and_cash_cannot_define_target(self):
        z = np.tile([-.001, .001], 60)
        a = {"reference": account(z+.0001), LABELS[0]: account(z/2+.0001), LABELS[1]: account(np.zeros(120))}
        scales, eligible, target = runner.calibration_scales(a)
        self.assertAlmostEqual(scales["reference"], .5)
        self.assertAlmostEqual(scales[LABELS[0]], 1.)
        self.assertNotIn(LABELS[1], eligible)
        self.assertTrue(all(0 < x <= 1 for x in scales.values()))

    def test_validation_winner_cannot_replace_preselected_loser(self):
        rng = np.random.default_rng(2222)
        ref = rng.normal(0, .0001, 120)
        a = {"reference": account(ref)}
        for i, label in enumerate(LABELS):
            a[label] = account(ref+rng.normal(0, .00001, 120)+(-.0002 if i == 0 else .0002))
        result = runner.evaluate(a, LABELS[0], {"spa_reps": 200, "paired_reps": 500, "seed": 310})
        self.assertEqual(result["verdict"], "NULL")
        self.assertIsNone(result["paper_candidate"])
        self.assertFalse(result["gates"]["selected_bonferroni"])

    def test_insufficient_or_degenerate_evidence_stays_inconclusive(self):
        a = {k: account(np.zeros(40)) for k in ("reference",)+LABELS}
        self.assertEqual(runner.evaluate(a, LABELS[0], {})["verdict"], "INCONCLUSIVE")
        a = {k: account(np.zeros(120)) for k in ("reference",)+LABELS}
        self.assertEqual(runner.evaluate(a, LABELS[0], {})["verdict"], "INCONCLUSIVE")

    def test_npz_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/"a.npz", Path(d)/"b.npz"
            runner.deterministic_npz(a, z=np.arange(50), a=np.array(["test"]))
            runner.deterministic_npz(b, a=np.array(["test"]), z=np.arange(50))
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_registration_reconciles_landed_append_after_exception_without_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane = root / "experiments/equations_v1"
            lane.mkdir(parents=True)
            data = root / "data/cache"
            data.mkdir(parents=True)
            state = data / "acquisition_status.json"
            state.write_text('{"complete":true,"errors":{}}')
            settings = lane / "settings.json"
            settings.write_text('{"registry_id":"R310"}')
            inputs = {"data_root": "data/cache", "sha256": {str(p.relative_to(root)): runner.sha(p)
                       for p in (state, settings)}}
            runner.write_json(lane/"inputs.json", inputs)
            (lane/"PREREG.md").write_text("Input manifest SHA-256: "+runner.sha(lane/"inputs.json"))
            digest = prereg.freeze(lane/"PREREG.md")
            out = lane/"results"
            out.mkdir()
            runner.write_json(out/"verdict.json", {"verdict": "INCONCLUSIVE", "selected": None})
            runner.write_json(out/"manifest.json", {"prereg_sha256": digest,
                              "outputs": {"verdict.json": runner.sha(out/"verdict.json")}})
            (root/"registry").mkdir()
            real_append = runner.registry.append
            def fail_after_append(*args, **kwargs):
                real_append(*args, **kwargs)
                raise OSError("reply lost after durable append")
            with mock.patch.object(runner.registry, "append", side_effect=fail_after_append):
                self.assertEqual(runner.register_result(out, root=root, lane=lane), "R310")
            before = (root/"registry/rounds.csv").read_bytes()
            runner.register_result(out, root=root, lane=lane)
            self.assertEqual(before, (root/"registry/rounds.csv").read_bytes())
            receipts = list((lane/"receipts").glob("*.json"))
            self.assertTrue(any(json.loads(p.read_text())["observed_exception"] for p in receipts))


if __name__ == "__main__":
    unittest.main()
