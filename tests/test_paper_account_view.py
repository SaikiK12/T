"""Invented offline rendering fixtures; no market/account/network evidence."""
from copy import deepcopy
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts.paper_account_view import load_report, main, render_report, render_text


def fixture():
    return {"schema_version": 1, "simulation_only": True, "activation_allowed": False,
            "accounts": [
                {"venue": "MEXC", "asset": "USDT", "initial_cash": "5000", "cash": "5002.25",
                 "realized_price_pnl": "3", "funding_pnl": "0.25", "fees_paid": "1",
                 "realized_net_pnl": "2.25", "unrealized_liquidation_pnl": None, "nav": None,
                 "nav_state": "unscored", "locked_capital": "250", "available_capital": None,
                 "positions": [{"symbol": "WIF", "quantity": "10", "state": "model"}],
                 "reasons": ["Prix de sortie trop ancien"], "fee_assumption": "réserve de modèle"},
                {"venue": "Lighter", "asset": "USD_quote", "initial_cash": "5000", "cash": "5000",
                 "realized_net_pnl": "0", "positions": [], "reasons": []}],
            "readiness": {"components": {"index": {"state": "unknown", "reasons": ["Valeur effective absente"],
                                                   "next_evidence": ["Index lié au règlement"]}}},
            "coverage": {"model_rows": 2, "recognized_rows": 0, "unscored_rows": 1, "prospective_days": 0},
            "next_evidence": ["Frais du compte non vérifiés"],
            "cost_comparisons": [
                {"multiple": k, "net_pnl": n, "asset": "USDT", "fee_assumption": "hypothèse", "scope": "simulation"}
                for k, n in [(1, "2.25"), (2, "1.25"), (3, "0.25")]]}


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags = []; self.resources = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.resources += [(name, value) for name, value in attrs if name in ("src", "href", "action") or name.startswith("on")]


class AccountViewTests(unittest.TestCase):
    def test_unknowns_do_not_become_zero_and_result_is_not_recomputed(self):
        report = fixture(); before = deepcopy(report)
        text = render_text(report); html = render_report(report)
        self.assertIn("Valeur totale du compte : inconnu USDT", text)
        self.assertIn("Gain ou perte net réalisé : 2,25 USDT", text)
        self.assertIn("Gain ou perte net réalisé : 0,00 USD_quote", text)
        self.assertIn("non évalué", html); self.assertIn("Frais du compte non vérifiés", html)
        self.assertIn("ne les additionne pas de nouveau", html)
        self.assertEqual(report, before)
        self.assertEqual(html, render_report(report))

    def test_separate_venue_asset_balances_and_no_trading_or_network_controls(self):
        html = render_report(fixture()); parsed = Parser(); parsed.feed(html)
        self.assertIn("MEXC · USDT", html); self.assertIn("Lighter · USD_quote", html)
        self.assertNotIn("10 000", html); self.assertNotIn("total disponible", html.lower())
        self.assertEqual(parsed.resources, [])
        self.assertTrue({"html", "head", "body", "table", "meta"} <= set(parsed.tags))
        self.assertFalse({"script", "form", "button", "iframe", "img"} & set(parsed.tags))
        self.assertIn("activation interdite", html.lower())

    def test_untrusted_strings_stay_inert_and_missing_states_remain_visible(self):
        report = fixture(); payload = '<script>alert(1)</script><img src=x onerror="bad">'
        report["accounts"][0]["venue"] = payload
        report["accounts"][0]["positions"] = [{"symbol": payload}]
        report["accounts"][0]["reasons"] = [payload]
        report["next_evidence"] = [payload]
        report["readiness"] = [{"name": payload, "state": payload, "reasons": [payload]}]
        report["cost_comparisons"][0]["fee_assumption"] = payload
        html = render_report(report); parsed = Parser(); parsed.feed(html)
        self.assertNotIn("<script>", html); self.assertNotIn("<img ", html)
        self.assertIn("&lt;script&gt;", html); self.assertEqual(parsed.resources, [])
        self.assertIn("preuve de frais réellement prélevés", html)
        self.assertIn("Preuve nécessaire", html)

    def test_nonfinite_boolean_missing_and_empty_positions_are_distinct(self):
        report = fixture(); report["accounts"][0].update(cash=True, nav="NaN", available_capital="Infinity", positions=None)
        text = render_text(report)
        self.assertIn("Solde comptable : inconnu USDT", text)
        self.assertIn("Valeur totale du compte : inconnu USDT", text)
        self.assertIn("Positions simulées : inconnu", text)
        self.assertIn("Positions simulées fournies : 0", text)
        report["accounts"][0]["nav"] = "1e100000000"
        self.assertLess(len(render_report(report)), 20000)

    def test_report_scope_rejects_live_activation_and_invalid_schema(self):
        for changes in ({"simulation_only": False}, {"activation_allowed": True}, {"schema_version": True},
                        {"schema_version": 2}, {"accounts": None}, {"accounts": ["bad"]}):
            report = fixture(); report.update(changes)
            with self.assertRaises(ValueError): render_report(report)
            with self.assertRaises(ValueError): render_text(report)
        empty = fixture(); empty["accounts"] = []; empty.pop("readiness"); empty.pop("coverage")
        html = render_report(empty)
        self.assertIn("Aucun compte fourni", html); self.assertIn("Contrôles : inconnu", html)

    def test_cli_explicit_file_offline_idempotent_and_refuses_differing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "report.json"; target = root / "view.html"
            source.write_text(json.dumps(fixture()), encoding="utf-8")
            self.assertEqual(main(["--input", str(source), "--out", str(target)]), 0)
            original = target.read_bytes()
            self.assertEqual(main(["--input", str(source), "--out", str(target)]), 0)
            self.assertEqual(target.read_bytes(), original)
            target.write_text("other")
            with self.assertRaisesRegex(ValueError, "différente"): main(["--input", str(source), "--out", str(target)])
            self.assertEqual(target.read_text(), "other")
            with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(main(["--input", str(source)]), 0)
            self.assertIn("Compte simulé", out.getvalue())
            link = root / "linked.json"; link.symlink_to(source)
            with self.assertRaises(ValueError): load_report(link)

    def test_json_duplicate_nonfinite_and_oversized_payloads_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for body in ('{"schema_version":1,"schema_version":1}', '{"cash":NaN}'):
                path.write_text(body)
                with self.assertRaises(ValueError): load_report(path)
            with path.open("wb") as stream: stream.truncate(4 * 1024 * 1024 + 1)
            with self.assertRaises(ValueError): load_report(path)


if __name__ == "__main__":
    unittest.main()
