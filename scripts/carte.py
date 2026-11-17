"""Generate the owner's French map of every registered experiment, grouped by family (docs/guides/CARTE.fr.md).

The map is a generated view, never an authority:
- `registry/rounds.csv` gives each round's status and verdict as registered;
- `registry/lane_families.csv` gives each lane's family (one row per lane; a new lane needs a row here);
- the family summaries below are stable, plain-language descriptions. What is true now stays in docs/STATUS.md.

No folder is moved: frozen PREREGs pin paths. Rows lag FINDINGS where the registry does (it is append-only), so each
line links the lane's folder for the exact result.

    python scripts/carte.py           # rewrite docs/guides/CARTE.fr.md
    python scripts/carte.py --check   # exit 1 if the committed map is stale or a lane has no family
"""
import argparse
import csv
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "guides" / "CARTE.fr.md"

# key: (title, summary). Order = order on the page.
FAMILIES = OrderedDict([
    ("carry", ("Portage de financement crypto entre plateformes",
               "Tenir un achat sur la plateforme où le financement est bas et une vente là où il est haut, sans pari "
               "sur le prix, et encaisser l'écart. C'est la seule famille dont le gain tient sur plusieurs "
               "plateformes et sur des données lues à l'aveugle (2020, longues traînes). Sur 2021-2026, les "
               "meilleurs livres gagnent environ +6 à +16 % par an avant les doutes d'exécution. Les répliques à "
               "l'aveugle sur les longues traînes gagnent beaucoup moins (+0,7 à +2,5 % par an). Huit livres sont "
               "testés sur papier.")),
    ("carry_tradfi", ("Portage sur actions, obligations et matières premières",
                      "Le même principe sur des perpétuels d'actions, d'obligations et de gaz ou de pétrole "
                      "(trade.xyz, Lighter, OKX Europe), couverts par l'actif réel. Quelques résultats partiels sur "
                      "des historiques courts ; plusieurs tests sur papier, lus en 2027.")),
    ("settle", ("Autour de l'heure de paiement du financement",
                "Encaisser le financement juste avant et après l'heure où il est payé. Quelques résultats "
                "partiels, mais petits ou rares une fois les frais et le délai comptés. Les tests sur papier se sont "
                "arrêtés avec le conteneur le 6 novembre 2026.")),
    ("events", ("Événements et annonces",
                "Parier sur ce qui suit une annonce : déblocage de jetons, délistage, nouveau contrat, publication "
                "économique. La vente avant un déblocage de jetons est partiellement confirmée ; la plupart des "
                "autres sont nuls. Plusieurs tests sur papier n'ont plus d'écrivain depuis le 6 novembre 2026.")),
    ("flow", ("Flux d'ordres et positionnement des traders",
              "Suivre ou contrer les gros comptes et le flux acheteur ou vendeur. Un livre a passé l'historique "
              "(R197) mais pas la vérification à l'aveugle (R198) ; les autres sont nuls. Des tests sur papier "
              "tournent encore.")),
    ("xsec", ("Classements de cryptos et chasse aux signaux",
              "Classer les cryptos entre elles (momentum, retour à la moyenne, apprentissage automatique) ou fouiller "
              "de grands tableaux de signaux. Des effets bruts existent ; aucun n'a encore tenu après frais sur des "
              "données neuves.")),
    ("charts", ("Graphiques, niveaux et tendances",
                "Règles de chartistes, niveaux, supports et résistances, tendances : plus de 5 000 variantes "
                "testées (R263). Nulles après frais, à part deux résultats partiels sur le modèle de niveaux.")),
    ("calendar", ("Week-ends, sessions et calendrier",
                  "Effets de week-end, d'ouverture de séance, de clôture asiatique, de fin de mois. Quelques "
                  "résultats partiels, testés sur papier et lus en 2027.")),
    ("options", ("Options, volatilité et signaux de marché",
                 "Prime de volatilité, VIX, gamma des teneurs de marché, flux d'options. Aucun gain à ce jour.")),
    ("micro", ("Très court terme (secondes, minutes)",
               "Aller plus vite que le carnet d'ordres. Presque tout est nul : le délai de cette machine et les frais "
               "mangent l'avantage.")),
    ("vaults", ("Coffres et pools des plateformes décentralisées",
                "Déposer dans les coffres HLP, LLP ou JLP, ou suivre leurs positions. Tests sur papier en cours ; "
                "choisir un coffre d'après son passé n'a rien donné.")),
    ("portfolio", ("Portefeuilles, comptes papier et règles de gestion",
                   "Combiner les stratégies, les dimensionner, simuler les règles des challenges de prop firms, le "
                   "compte papier de 10 000 $. Ces outils ne valent que ce que valent les stratégies combinées.")),
    ("reserved", ("Lectures à l'aveugle d'échantillons mis de côté",
                  "Des lots de candidats lus une seule fois sur des données gardées de côté (2020, longues "
                  "traînes). La lecture de lot 2 (portage) est rangée avec le portage.")),
    ("infra", ("Mesures de coûts, de données et outils (sans pari)",
               "Coûts réels des carnets d'ordres, frais, fidélité des données, outils du compte papier, audits. Ces "
               "lignes servent à décider ; elles ne gagnent ni ne perdent.")),
])

VERDICT = {
    ("DONE", "CONFIRMED"): "confirmé (historique)",
    ("DONE", "PARTIAL"): "partiel",
    ("DONE", "NULL"): "nul",
    ("DONE", "DATA_PASS"): "mesure faite",
    ("DONE", "PENDING"): "fait, verdict à lire dans FINDINGS",
    ("RUNNING", "PENDING"): "en cours",
    ("REGISTERED", "PENDING"): "enregistré",
    ("ARMED", "PENDING"): "armé",
}
COLUMNS = ["confirmé (historique)", "partiel", "nul", "en cours", "autre"]


def verdict(status, ver):
    if status == "ABANDONED":
        return "abandonné"
    if status == "PLANNED":
        return "projet"
    return VERDICT.get((status, ver), f"{status.lower()} / {ver.lower()}")


def column(word):
    return word if word in COLUMNS[:4] else "autre"


def load(root=ROOT):
    with (root / "registry" / "rounds.csv").open(newline="", encoding="utf-8") as f:
        rounds = list(csv.DictReader(f))
    with (root / "registry" / "lane_families.csv").open(newline="", encoding="utf-8") as f:
        fam = {r["lane"]: r["family"] for r in csv.DictReader(f)}
    return rounds, fam


def problems(rounds, fam):
    out = []
    for r in rounds:
        if r["lane"] not in fam:
            out.append(f"{r['id']} {r['lane']}: no row in registry/lane_families.csv")
        elif fam[r["lane"]] not in FAMILIES:
            out.append(f"{r['id']} {r['lane']}: unknown family {fam[r['lane']]!r}")
    return out


def short(text, n=110):
    text = " ".join(text.split()).replace("|", "/")
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def render(rounds, fam):
    groups = OrderedDict((k, []) for k in FAMILIES)
    for r in rounds:
        groups[fam[r["lane"]]].append(r)
    lines = [
        "# Carte du projet : toutes les expériences, rangées par famille",
        "",
        "[Accueil](../../README.md) · [Statut](../STATUS.md) · [Guide de lecture](START_HERE.fr.md)",
        "",
        "**Page générée** par `python scripts/carte.py` à partir de `registry/rounds.csv` et "
        "`registry/lane_families.csv`. Ne pas la modifier à la main. Aucun dossier n'a été déplacé : les règles "
        "figées des expériences pointent vers leurs chemins.",
        "",
        "## Où on en est",
        "- **Argent réel engagé : aucun.** Ce qui est vrai aujourd'hui, les dates et les décisions qui t'attendent "
        "sont dans le [Statut](../STATUS.md).",
        "- **Le plan** : [plan du 17-11-2026](../reviews/plan_20261117.md), revu le même jour avec la "
        "[salle de réflexion](../reviews/room_haiku_20261117.md).",
        "- **La famille qui compte** : le portage de financement crypto, en tête ci-dessous.",
        "",
        "## Comment lire",
        "- **R390**, par exemple, est le numéro d'une expérience. Son dossier est `experiments/<nom>/` : "
        "`PREREG.md` y fixe les règles avant le test, `FINDINGS.md` donne le résultat.",
        "- **Verdicts** (tels qu'inscrits au registre ; le registre ne s'efface pas, il peut donc être en retard "
        "sur FINDINGS) :",
        "  - *confirmé (historique)* : passé sur des données passées, pas encore en conditions réelles ;",
        "  - *partiel* : un morceau tient, le reste non, ou c'est trop petit ;",
        "  - *nul* : pas de gain après frais pour cette règle. C'est un résultat, pas un oubli ;",
        "  - *en cours* : test sur papier ou mesure qui tourne ;",
        "  - *autre* : enregistré, mesure faite, abandonné ou projet.",
        "",
        "## Vue d'ensemble",
        "",
        "| Famille | Expériences | " + " | ".join(COLUMNS) + " |",
        "|---|---|" + "---|" * len(COLUMNS),
    ]
    total = Counter()
    for key, rows in groups.items():
        c = Counter(column(verdict(r["status"], r["verdict"])) for r in rows)
        total.update(c)
        anchor = key.replace("_", "-")
        lines.append(f"| [{FAMILIES[key][0]}](#{anchor}) | {len(rows)} | "
                     + " | ".join(str(c.get(col, 0)) for col in COLUMNS) + " |")
    lines.append(f"| **Total** | **{len(rounds)}** | " + " | ".join(f"**{total.get(c, 0)}**" for c in COLUMNS)
                 + " |")
    for key, rows in groups.items():
        title, summary = FAMILIES[key]
        lines += ["", f'<a id="{key.replace("_", "-")}"></a>', "", f"## {title}", "", summary, "",
                  "| R | Dossier | Ce qui a été testé (titre du registre, en anglais) | Verdict |",
                  "|---|---|---|---|"]
        for r in rows:
            path = r["path"].strip() or f"experiments/{r['lane']}"
            link = f"[`{r['lane']}`](../../{path})" if (ROOT / path).exists() else f"`{r['lane']}`"
            lines.append(f"| {r['id']} | {link} | {short(r['title'])} | {verdict(r['status'], r['verdict'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    rounds, fam = load()
    bad = problems(rounds, fam)
    if bad:
        print("\n".join(bad))
        return 1
    text = render(rounds, fam)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(ROOT)} is stale: run python scripts/carte.py")
            return 1
        print("Map matches the registry.")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rounds)} rounds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
