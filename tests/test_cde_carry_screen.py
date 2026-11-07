"""Invented inputs only: cash units, segregated losses and no recovery resurrection."""
from copy import deepcopy
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from lab.cde_carry_screen import fixed_quantity, friction, number, replay, text
from scripts.run_cde_carry_screen import body


def bar(p):
    return dict(open=str(p), high=str(p), low=str(p), close=str(p))


def fixture():
    return dict(cde_bars={t: bar(100) for t in (-3600, 0, 3600, 7200)},
                kraken_marks={t: bar(100) for t in (0, 3600, 7200)},
                cde_rates={3600: "0.001", 7200: "0.002"}, kraken_rates={0: "0.05", 3600: "0.1"},
                start=0, end=7200, allowed_missing_cde_bars=[], capital="10000", lot="1",
                slips={v: {s: F(0) for s in ("buy", "sell")} for v in ("cde", "kraken")},
                fees=dict(cde="0", kraken="0", cde_per_contract="0"), multiple=1, direction=1)


class CdeCarryScreenTests(unittest.TestCase):
    def test_absolute_kraken_cash_not_multiplied_by_mark(self):
        r = replay(**fixture())
        self.assertEqual(r["quantity"], "50.000000000000")
        self.assertEqual(r["funding"]["cde"]["center"], "15.000000000000")
        self.assertEqual(r["funding"]["kraken"]["center"], "-7.500000000000")
        self.assertEqual(r["terminal_net"]["center"], "7.500000000000")
        self.assertEqual(r["withheld_positive_funding"]["cde"], "15.000000000000")
        self.assertEqual(r["minimum_wallet"]["cde"], "5000.000000000000")
        self.assertEqual(r["minimum_wallet"]["kraken"], "4992.500000000000")

    def test_reverse_hedge_and_signed_price_envelope(self):
        f = fixture(); f["direction"] = -1
        f["cde_bars"][0].update(low="90", high="110")
        r = replay(**f)
        self.assertEqual(r["terminal_net"], dict(low="-8.000000000000", center="-7.500000000000", high="-7.000000000000"))
        self.assertEqual(r["minimum_wallet"]["cde"], "4984.500000000000")

    def test_basis_path_is_separate_from_funding(self):
        f = fixture(); f["cde_bars"][7200] = bar(105); f["kraken_marks"][7200] = bar(102)
        r = replay(**f)
        self.assertEqual(r["gross_basis_pnl"], "-150.000000000000")
        self.assertEqual(r["terminal_net"]["center"], "-142.500000000000")
        self.assertEqual(sum(F(x) for x in r["terminal_wallets"].values()) - 10000, F("-142.5"))

    def test_fixed_fee_per_contract_per_side(self):
        f = fixture(); f["fees"]["cde_per_contract"] = "0.12"
        r = replay(**f)
        self.assertEqual(r["quantity"], "49.000000000000")
        self.assertEqual(r["fees"], "11.760000000000")
        self.assertEqual(r["terminal_net"]["center"], "-4.410000000000")

    def test_three_costs_same_quantity_and_separate_wallet_identity(self):
        f = fixture(); f["fees"] = dict(cde="0.0002", kraken="0.0005", cde_per_contract="0.12")
        f["slips"] = {v: {s: F("0.0001") for s in ("buy", "sell")} for v in ("cde", "kraken")}
        rows = [replay(**dict(f, multiple=m)) for m in (1, 2, 3)]
        self.assertEqual(len({r["quantity"] for r in rows}), 1)
        self.assertTrue(all(F(a["terminal_net"]["center"]) > F(b["terminal_net"]["center"]) for a,b in zip(rows,rows[1:])))
        for r in rows:
            # Independent ledger addition from serialized USD components.
            net = F(r["gross_basis_pnl"]) - F(r["execution_drag"]) - F(r["fees"]) + sum(F(x["center"]) for x in r["funding"].values())
            self.assertEqual(net, F(r["terminal_net"]["center"]))

    def test_first_capital_failure_is_terminal_despite_later_recovery(self):
        f = fixture(); f["cde_rates"][3600] = "0.5"; f["kraken_rates"][0] = "10"
        f["kraken_marks"][3600] = bar(1)  # Other venue's profit cannot transfer across wallets.
        r = replay(**f)
        self.assertEqual(r["state"], "CONDITIONAL_CAPITAL_DEFICIT")
        self.assertEqual(r["stop"]["time"], 3600)
        self.assertEqual(len(r["path"]), 1)
        self.assertIsNone(r["terminal_net"])
        self.assertFalse(r["recovery_pnl_counted"])

    def test_declared_missing_trade_bar_is_stale_not_interpolated(self):
        f = fixture(); del f["cde_bars"][3600]; f["allowed_missing_cde_bars"] = [3600]
        r = replay(**f)
        self.assertEqual(r["stale_trade_proxy_references"], [dict(payment_time=7200,prior_bar=0)])
        self.assertFalse(r["envelope_is_verified_mark_bound"])
        self.assertEqual(r["terminal_net"]["center"], "7.500000000000")

    def test_missing_or_unexpected_sources_fail_instead_of_zero_fill(self):
        for path in ("cde_rates", "kraken_rates", "kraken_marks", "cde_bars"):
            f = fixture(); del f[path][next(iter(f[path]))]
            with self.assertRaises(ValueError, msg=path): replay(**f)

    def test_no_floats_nonfinite_negative_fees_or_invalid_ohlc(self):
        for x in (float("nan"), 0.1, "NaN", "Infinity", True):
            with self.assertRaises(ValueError): number(x)
        f = fixture(); f["fees"]["kraken"] = "-0.1"
        with self.assertRaises(ValueError): replay(**f)
        f = fixture(); f["cde_bars"][0]["high"] = "99"
        with self.assertRaises(ValueError): replay(**f)

    def test_current_parent_drag_keeps_worst_unit_phase_by_side(self):
        rows=[]
        for unit in ("contracts", "base"):
            for phase in ("initial", "delayed"):
                cost = "2" if (unit,phase)==("base","delayed") else "1"
                buy=dict(complete=True,filled="1",book_cost=cost,quote=str(100+int(cost)))
                sell=dict(complete=True,filled="1",book_cost=cost,quote=str(100-int(cost)))
                rows.append(dict(coin="btc",target_per_leg="5000",cost_multiple=1,round_trip_complete=True,cde_size_unit=unit,phase=phase,quantity="1",directions=[dict(buyer=0,seller=1,buy=buy,sell=sell),dict(buyer=1,seller=0,buy=buy,sell=sell)]))
        s=friction(dict(scenarios=rows),"btc")
        self.assertEqual(s,{v:{side:F("0.02") for side in ("buy","sell")} for v in ("cde","kraken")})
        with self.assertRaises(ValueError): friction(dict(scenarios=rows[:-1]),"btc")

    def test_raw_body_receipts_honor_both_saved_length_schemas(self):
        raw=b'{"funding_rate":"0.000001"}'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'raw.gz').write_bytes(gzip.compress(raw))
            for key in ('bytes','bytes_read'):
                receipt=dict(body='raw.gz',status=200,sha256=hashlib.sha256(raw).hexdigest(),**{key:len(raw)})
                self.assertEqual(body(p,receipt),json.loads(raw))

    def test_cut_or_hash_changed_bodies_never_enter_accounts(self):
        raw=b'{}'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'raw.gz').write_bytes(gzip.compress(raw))
            receipt=dict(body='raw.gz',status=200,bytes_read=2,sha256=hashlib.sha256(raw).hexdigest())
            for patch in [dict(response_complete=False),dict(status=401),dict(sha256='0'*64),dict(bytes_read=3)]:
                with self.assertRaises(ValueError): body(p,dict(receipt,**patch))


if __name__ == "__main__":
    unittest.main()
