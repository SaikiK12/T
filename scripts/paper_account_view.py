"""Offline French view of an explicit simulated-account report; no calculations or orders.

The renderer copies supplied figures and preserves unknown values. Each venue and
asset stays separate; no combined spendable balance, trading control, network or
prospective-performance inference is introduced.
"""
import argparse
from decimal import Decimal, InvalidOperation
from html import escape
import json
from pathlib import Path

MAX_INPUT_BYTES = 4 * 1024 * 1024
FIELDS = (
    ("initial_cash", "Capital initial"),
    ("cash", "Solde comptable"),
    ("realized_price_pnl", "Gain ou perte de prix réalisé"),
    ("funding_pnl", "Financement imputé"),
    ("fees_paid", "Frais imputés"),
    ("realized_net_pnl", "Gain ou perte net réalisé"),
    ("unrealized_liquidation_pnl", "Gain ou perte ouvert au prix de sortie"),
    ("nav", "Valeur totale du compte"),
    ("locked_capital", "Capital immobilisé"),
    ("available_capital", "Capital disponible"),
)
STATES = {
    "pass": "conditions remplies pour ce contrôle",
    "passed": "conditions remplies pour ce contrôle",
    "verified": "vérifié dans le modèle",
    "known": "renseigné dans le modèle",
    "complete": "complet",
    "partial": "partiel",
    "unknown": "inconnu",
    "unscored": "non évalué",
    "blocked": "bloqué",
    "fail": "échec",
    "failed": "échec",
    "inactive": "inactif",
    "simulation": "simulation",
    "model": "calcul de modèle",
    "recognized": "comptabilisé dans le modèle",
    "prospective": "observation prospective déclarée",
    "replay": "reconstitution historique",
    "late": "observation tardive",
}


def _plain(value):
    if value is None:
        return "inconnu"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def _number(value):
    if value is None or isinstance(value, bool):
        return "inconnu"
    try:
        number = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return "inconnu"
    if not number.is_finite():
        return "inconnu"
    if number and (number.adjusted() > 12 or number.adjusted() < -6):
        return format(number, ".4E").replace(".", ",")
    return format(number, ",.2f").replace(",", " ").replace(".", ",")


def _state(value):
    if value is None:
        return "inconnu"
    return STATES.get(str(value).lower(), _plain(value))


def _items(value):
    if value is None:
        return ["inconnu"]
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return [_plain(value)]


def _validate(report):
    if not isinstance(report, dict) or type(report.get("schema_version")) is not int or report["schema_version"] != 1:
        raise ValueError("rapport de simulation schema_version=1 requis")
    if report.get("simulation_only") is not True or report.get("activation_allowed") is not False:
        raise ValueError("simulation_only=true et activation_allowed=false requis")
    accounts = report.get("accounts")
    if not isinstance(accounts, list) or any(not isinstance(account, dict) for account in accounts):
        raise ValueError("accounts doit être une liste de comptes simulés")
    return accounts


def _readiness(report):
    value = report.get("readiness")
    if value is None:
        return []
    if isinstance(value, dict):
        components = value.get("components")
        if components is None:
            return [{"name": "État des entrées", **value}]
        value = components
    if isinstance(value, dict):
        return [{"name": key, **item} if isinstance(item, dict) else {"name": key, "state": item}
                for key, item in value.items()]
    if isinstance(value, list):
        return [item if isinstance(item, dict) else {"name": "Contrôle", "state": item} for item in value]
    return [{"name": "État des entrées", "state": value}]


def _comparisons(report):
    value = report.get("cost_comparisons", report.get("cost_scenarios"))
    if isinstance(value, dict):
        return [{"label": key, **item} if isinstance(item, dict) else {"label": key, "net_pnl": item}
                for key, item in value.items()]
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _comparison_label(item):
    if "label" in item:
        return _plain(item["label"])
    multiple = item.get("multiple", item.get("cost_multiple"))
    return _plain(multiple) + "x" if multiple is not None else "inconnu"


def _coverage(report):
    value = report.get("coverage")
    if isinstance(value, dict):
        return [(str(key), _plain(item)) for key, item in value.items()]
    if isinstance(value, list):
        return [("Observation", _plain(item)) for item in value]
    return [("Couverture", _plain(value))]


def render_text(report):
    """Return a deterministic plain-text projection without deriving balances."""
    accounts = _validate(report)
    lines = ["Compte simulé — résultats et données", "Simulation uniquement. Activation interdite.",
             "Les calculs présentés ne prouvent pas un gain futur.",
             "Chaque compte conserve son actif et son solde propres."]
    if 'scope' in report:lines.append("Portée : " + _plain(report['scope']))
    if not accounts:
        lines.append("Aucun compte fourni ; résultat inconnu.")
    for account in accounts:
        asset = _plain(account.get("asset"))
        lines += ["", f"{_plain(account.get('venue'))} — {asset}",
                  "État de la valeur : " + _state(account.get("nav_state"))]
        lines += [f"{label} : {_number(account.get(field))} {asset}" for field, label in FIELDS]
        lines.append("Prix, financement et frais sont déjà compris dans le résultat fourni ; cette vue ne les additionne pas de nouveau.")
        positions = account.get("positions")
        if isinstance(positions, list):
            lines.append(f"Positions simulées fournies : {len(positions)}")
            lines += ["  " + _plain(position) for position in positions]
        else:
            lines.append("Positions simulées : inconnu")
        reasons = _items(account.get("reasons"))
        lines += ["Motifs : " + (" ; ".join(reasons) if reasons else "aucun motif enregistré")]
        if "fee_assumption" in account or "fee_source" in account:
            lines.append("Hypothèse de frais, sans preuve de frais réellement prélevés : " +
                         _plain(account.get("fee_assumption", account.get("fee_source"))))
    lines += ["", "État des données et contrôles"]
    controls = _readiness(report)
    if not controls:
        lines.append("Contrôles : inconnu")
    for item in controls:
        name = _plain(item.get("name", item.get("component", item.get("id"))))
        lines.append(name + " : " + _state(item.get("state", item.get("status"))))
        if "reasons" in item:
            lines.append("  Motifs : " + " ; ".join(_items(item["reasons"])))
        if "next_evidence" in item:
            lines.append("  Preuve nécessaire : " + " ; ".join(_items(item["next_evidence"])))
    lines += ["", "Couverture des observations"]
    lines += [key + " : " + value for key, value in _coverage(report)]
    if "next_evidence" in report:
        lines += ["", "Preuves encore nécessaires", *_items(report["next_evidence"])]
    comparisons = _comparisons(report)
    if comparisons:
        lines += ["", "Coûts hypothétiques : sensibilités, sans preuve de frais réels ou de remplissage"]
        lines += [_comparison_label(item) + " : résultat fourni " + _number(item.get("net_pnl", item.get("realized_net_pnl"))) +
                  " ; unité " + _plain(item.get("asset")) + " ; hypothèse " + _plain(item.get("fee_assumption"))
                  for item in comparisons]
    return "\n".join(lines) + "\n"


def _table(headers, rows):
    header = "".join("<th scope=\"col\">" + escape(str(item)) + "</th>" for item in headers)
    body = "".join("<tr>" + "".join("<td>" + escape(str(item)) + "</td>" for item in row) + "</tr>" for row in rows)
    return "<div class=\"tablebox\"><table><thead><tr>" + header + "</tr></thead><tbody>" + body + "</tbody></table></div>"


def _list(items):
    return "<ul>" + "".join("<li>" + escape(str(item)) + "</li>" for item in items) + "</ul>"


def render_report(report):
    """Return standalone offline HTML. Source strings are inert escaped text."""
    accounts = _validate(report)
    parts = ["<header><p class=\"eyebrow\">Quant Lab · compte fictif</p><h1>Compte simulé</h1>",
             "<p class=\"lead\">Comprendre les gains, les pertes et les données manquantes.</p>",
             "<p class=\"notice\">Simulation uniquement · activation interdite. Les calculs présentés ne prouvent pas un gain futur.</p></header>",
             "<p>Chaque compte conserve son actif et son solde propres. Les montants sont copiés du rapport, sans nouveau calcul de PnL.</p>"]
    if 'scope' in report:parts.append('<p>Portée : '+escape(_plain(report['scope']))+'</p>')
    if not accounts:
        parts.append("<p>Aucun compte fourni ; résultat inconnu.</p>")
    for account in accounts:
        asset = _plain(account.get("asset"))
        parts += ["<section class=\"card\"><h2>" + escape(_plain(account.get("venue"))) + " · " + escape(asset) + "</h2>",
                  "<p>État de la valeur : <strong>" + escape(_state(account.get("nav_state"))) + "</strong></p>",
                  _table(("Montant du compte simulé", "Valeur", "Actif"),
                         [(label, _number(account.get(field)), asset) for field, label in FIELDS]),
                  "<p class=\"note\">Prix, financement et frais sont déjà compris dans le résultat fourni ; cette vue ne les additionne pas de nouveau.</p>"]
        positions = account.get("positions")
        if isinstance(positions, list):
            parts.append("<h3>Positions simulées fournies : " + str(len(positions)) + "</h3>")
            if positions:
                parts.append(_list(_plain(position) for position in positions))
        else:
            parts.append("<p>Positions simulées : inconnu</p>")
        reasons = _items(account.get("reasons"))
        parts += ["<h3>Motifs et limites</h3>", _list(reasons or ["Aucun motif enregistré."])]
        if "fee_assumption" in account or "fee_source" in account:
            parts.append("<p>Hypothèse de frais, sans preuve de frais réellement prélevés : " +
                         escape(_plain(account.get("fee_assumption", account.get("fee_source")))) + "</p>")
        parts.append("</section>")
    controls = _readiness(report)
    parts.append("<section class=\"card\"><h2>État des données et contrôles</h2>")
    parts.append("<p class=\"note\">Un contrôle renseigné ne donne pas une autorisation de négocier.</p>")
    parts.append(_table(("Contrôle", "État", "Motifs", "Preuve nécessaire"),
        [(_plain(item.get("name", item.get("component", item.get("id")))),
          _state(item.get("state", item.get("status"))),
          " ; ".join(_items(item.get("reasons"))), " ; ".join(_items(item.get("next_evidence")))) for item in controls])
        if controls else "<p>Contrôles : inconnu</p>")
    parts += ["<h3>Couverture des observations</h3>", _table(("Information", "Valeur fournie"), _coverage(report))]
    if "next_evidence" in report:
        parts += ["<h3>Preuves encore nécessaires</h3>", _list(_items(report["next_evidence"]))]
    parts.append("</section>")
    comparisons = _comparisons(report)
    if comparisons:
        parts += ["<section class=\"card\"><h2>Coûts hypothétiques</h2>",
                  "<p>Sensibilités du modèle, sans preuve de frais réels ou de remplissage. Les unités et comptes restent distincts.</p>",
                  _table(("Scénario", "Résultat fourni", "Actif", "Hypothèse de frais", "Portée"),
                         [(_comparison_label(item), _number(item.get("net_pnl", item.get("realized_net_pnl"))),
                           _plain(item.get("asset")), _plain(item.get("fee_assumption")), _plain(item.get("scope"))) for item in comparisons]),
                  "</section>"]
    style = """body{margin:0;background:#f5f5f2;color:#202721;font:16px/1.55 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:32px 20px 60px}h1{font-size:2.4rem;line-height:1.1;margin:8px 0}h2{margin:0 0 12px;font-size:1.4rem}h3{font-size:1rem;margin:22px 0 6px}.eyebrow{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:#4e6655}.lead{font-size:1.15rem}.notice{padding:12px 16px;background:#edf0e4;border-left:4px solid #73844c}.card{background:#fff;border:1px solid #d9ded8;border-radius:12px;padding:22px;margin:22px 0}.note{color:#536056;font-size:.9rem}.tablebox{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{text-align:left;border-bottom:1px solid #e3e7e1;padding:10px 12px;vertical-align:top;overflow-wrap:anywhere}th{font-size:.85rem;background:#f4f6f1}td:nth-child(2){white-space:normal}li{overflow-wrap:anywhere}footer{font-size:.85rem;color:#536056}@media(max-width:600px){main{padding:22px 12px}.card{padding:16px}h1{font-size:2rem}th,td{padding:8px}}"""
    return ('<!doctype html>\n<html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<title>Compte simulé — Quant Lab</title><style>' + style + '</style></head><body><main>' +
            "".join(parts) + '<footer>Vue locale en lecture seule · aucune connexion réseau · aucun ordre.</footer></main></body></html>\n')


def load_report(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("fichier JSON explicite, ordinaire et de taille bornée requis")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("clé JSON répétée")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("nombre JSON non fini")
    report = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=invalid_constant)
    _validate(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="rapport JSON de simulation déjà calculé")
    parser.add_argument("--out", type=Path, help="nouveau fichier HTML local ; sinon texte sur la sortie standard")
    args = parser.parse_args(argv)
    report = load_report(args.input)
    if args.out is None:
        print(render_text(report), end="")
        return 0
    content = render_report(report).encode("utf-8")
    if args.out.is_symlink():
        raise ValueError("sortie symbolique refusée")
    try:
        with args.out.open("xb") as stream:
            stream.write(content)
    except FileExistsError:
        if not args.out.is_file() or args.out.read_bytes() != content:
            raise ValueError("refus de remplacer une sortie différente") from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
