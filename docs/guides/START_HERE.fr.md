# Comprendre et parcourir le projet

[Accueil](../../README.md) · [Index des documents](../../README.md#docs) · [Guide technique](OPERATIONS.md)

T cherche des stratégies de trading dont le gain reste positif après les frais,
le financement et les contraintes d'exécution. Une idée, un calcul historique
et une preuve sur des jours nouveaux correspondent à des étapes différentes.

## Trouver ce qui t'intéresse

| Je veux… | Où regarder |
|---|---|
| Comprendre les priorités | [Direction du projet](../DIRECTION.md) |
| Retrouver une piste précise | [Liste vivante des méthodes](../../registry/methods.csv) |
| Voir ce qu'une expérience a réellement testé | [Catalogue des expériences](../../experiments/README.md), puis ses fichiers PREREG et FINDINGS |
| Lire les sources et les hypothèses | [Dossier research](../../research/README.md) |
| Voir l'activité et les blocages récents | [Panel](../PANEL.md), avec sa date, puis [room #7](https://github.com/SaikiK12/T/issues/7) |
| Comprendre un ancien rapport | [Dossier reports](../../reports/README.md) et ses notes d'appui |
| Installer ou lancer quelque chose | [Guide technique](OPERATIONS.md) |

## Comprendre les identifiants et les fichiers

- **M290**, par exemple, désigne une méthode dans la liste de recherche.
- **R400**, par exemple, désigne une expérience enregistrée. Plusieurs
  expériences peuvent étudier des variantes d'une même méthode.
- **PREREG.md** décrit les règles fixées avant le test ; son empreinte permet
  de vérifier qu'elles n'ont pas été changées après lecture des résultats.
- **FINDINGS.md** décrit ce qui a été fait, le résultat et ses limites.
- **NULL** concerne la règle et l'échantillon testés. **REFUSED** signifie
  que les conditions d'admission du test n'étaient pas réunies.

Une ancienne ligne « REGISTERED » ou un processus terminé ne suffit pas à
connaître le verdict actuel. Ouvre les preuves natives indiquées par la recherche.
Les notes et rapports datés conservent leur contexte historique ; les CSV du
registre et les preuves de l'expérience définissent le périmètre exact.

## Chercher dans le dépôt

Tu peux lire les documents directement dans GitHub. Si l'environnement Python
est déjà installé, ces recherches affichent des métadonnées existantes :

```sh
.venv/bin/python -m lab find funding
.venv/bin/python -m lab find --trace M290
.venv/bin/python -m lab find R400
.venv/bin/python -m lab find room_actions_20261103
```

Elles ne lancent aucune expérience. Pour modifier le projet, commence par les
[règles de travail](../../AGENTS.md) et les intervenants annoncés dans la room.
