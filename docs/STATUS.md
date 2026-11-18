# Status: what is true now

**Rewritten in place, never appended. Last rewrite: 2026-11-18 by Claude.**
- If this date is more than two weeks old, trust `registry/rounds.csv` and `python scripts/lane_census.py` over this
  page.
- Why this page exists: [reviews/stepback_20261116.md](reviews/stepback_20261116.md). The plan it follows:
  [reviews/plan_20261117.md](reviews/plan_20261117.md).
- The owner's reading guide: [START_HERE.fr.md](guides/START_HERE.fr.md). Every experiment, by family, in French:
  [CARTE.fr.md](guides/CARTE.fr.md).

## En bref (pour le propriétaire)
- **Le plan (17-11-2026, revu le soir même).** Une seule question : faut-il mettre une petite mise réelle sur le
  portage de financement entre plateformes, et sur quel livre ? Après ton objection et une
  [salle de réflexion](reviews/room_haiku_20261117.md), le plan avance à deux vitesses :
  - **En semaines.** Trois choses :
    - la mesure des ordres posés sur Gate (R498), lue du 1er au 7 décembre ;
    - une réplique du portage sur une plateforme jamais lue (Bitfinex répond depuis ici), avec ses règles figées avant
      le téléchargement : **faite le 18-11, réussie** (R507, ci-dessous) ;
    - un **pilote de mesure** réel et petit, si tu ajoutes une exception à la règle 6 (voir plus bas).
  - **En mois.** Les huit livres sur papier, lus de janvier à mai 2027. Ils décident d'**augmenter** la mise, plus de la
    première petite mise.
  - **À attendre.** Les répliques à l'aveugle gagnent +0,7 à +2,5 %/an, loin des +10 % des meilleurs livres choisis
    sur le passé. Il faut compter quelques % par an, et payer les transferts.
  - Le détail : [le plan](reviews/plan_20261117.md), section 9.
- **Les numéros R.** R390, par exemple, est le numéro d'une expérience ; son dossier est dans `experiments/`. La
  [carte](guides/CARTE.fr.md) range les 277 expériences en 14 familles, avec un verdict en un mot. Aucun dossier
  n'est déplacé, parce que les règles figées pointent vers leurs chemins.
- **Argent.** Aucun argent réel n'est engagé. Aucune stratégie n'a encore réussi l'épreuve du papier sur des jours
  nouveaux. La règle par défaut est donc : pas de trade.
- **Ce qu'on a appris.** La plupart des idées étaient réelles mais plus petites que les frais pour les exécuter.
- **Plateformes (décision du 16-11-2026).** Tu as remis Binance, Gate, KuCoin et MEXC dans le périmètre, à ton
  risque d'accès (gel possible d'un compte ou des retraits pour un résident d'un pays non servi). L'argent réel
  reste ton geste.
- **Frais.** Il existe des routes à 0 frais même par API (Lighter, et Paradex « retail »). Ce qui coûte encore,
  c'est l'écart entre prix d'achat et de vente. Sur Binance + Gate, le portage C14 ne couvre ses coûts qu'à
  1 000 $ par jambe en ordres au marché ([carte des frais](../research/intake/fee_map_20261116.md)). Le levier :
  un ordre posé sur Gate, couvert aussitôt sur Binance. Mesuré le 16-11 sur deux semaines de transactions (R497), il
  coûte au plus la moitié d'un ordre au marché dans toutes les tranches de volume, si chaque transaction au meilleur
  prix remplit l'ordre ([résultat](../experiments/gatemaker_v1/FINDINGS.md)). La file d'attente et le temps de
  remplissage se mesurent maintenant en papier, sur les contrats de C14, jusqu'au 1er décembre (R498).
- **Coût réel sur cinq ans d'historique (R500, 17-11, en quelques heures au lieu de mois de papier).**
  - **Méthode.** Chacune des 2 544 entrées et sorties réelles de C14, de 2021-07 à 2026-09, a été facturée au
    prix des carnets d'ordres enregistrés à cette heure-là :
    - Gate par son archive publique horaire, à l'heure exacte ;
    - Binance par le 1er du mois, faute de mieux.
  - **Résultat.** **+7,97 %/an à 1 000 $ par jambe, +8,56 % à 250 $** (la taille d'un livre de 10 k$), contre
    +9,79 % au coût forfaitaire. Le coût moyen est de 14,6 pb par jambe et par côté, deux fois l'hypothèse.
  - **Ce que ça veut dire.** Le coût ne tue pas C14. Ce qui le fragilise, c'est que 2025 porte l'essentiel : sans
    2025, environ +4,5 %/an, à peine au-dessus des bons du Trésor
    ([résultat](../experiments/carrycost_hist_v2/FINDINGS.md)).
- **Le même portage avec un contrat CME (R502, 17-11, cinq ans d'historique pour 0,25 $ de données).**
  - **Méthode.** Le future bitcoin du CME contre le perpétuel Binance : on parie que l'écart entre le financement du
    perpétuel et la prime du future se referme.
  - **Résultat. Faible :** +2,89 %/an net en micro (MBT), t = 3,2, sous le seuil de 4,13 %. Négatif à coûts doublés.
    L'éther (MET) est négatif.
  - **Pourquoi.** L'écart existe (6,97 %/an brut), mais les frais fixes du micro-contrat en prennent environ 3 points.
    L'écart s'est aussi resserré depuis 2024 : presque rien en 2025. Pas de voie papier méritée
    ([résultat](../experiments/cmecarry_v2/FINDINGS.md)).
- **Le portage des matières premières au CME (R505 et R506, 18-11, seize ans de cours de règlement pour 2,9 $).**
  - **Méthode.** 13 contrats (énergie, métaux, céréales, bétail) : on achète les courbes les plus en déport et on vend
    les plus en report. R505 teste la règle des manuels. R506 teste 432 variantes (signal, concentration, poids par
    confiance, fréquence, bande, filtre de coût), choisies chaque année sur le seul passé.
  - **Résultat. Nul pour la règle des manuels :** −0,76 %/an net (R505). **Faible pour la grille :** +2,42 %/an hors
    échantillon, t = 0,8 ; le meilleur des 432 ne bat pas zéro une fois la recherche comptée (SPA p = 0,13).
  - **Ce qui compte.** Les coûts ne pèsent que 0,4 %/an : les gérer ne change presque rien. Les pertes viennent de
    l'énergie lors des krachs pétroliers (2014, 2018, 2020). Le seul motif stable est un portage lent et
    désaisonnalisé (3-5 %/an), à tester sur des données jamais lues. Il faut environ 1 M$ pour tenir ce livre : hors
    de portée de toute façon ([R505](../experiments/cmeterm_v3/FINDINGS.md),
    [R506](../experiments/cmeterm_grid_v1/FINDINGS.md)).
- **Le portage entre plateformes répliqué sur Bitfinex (R507, 18-11, jamais lu avant, règles figées avant le
  téléchargement).**
  - **Méthode.** Le livre de R275, inchangé, sur Binance + Bitfinex, de 2021 à septembre 2026. Bitfinex ne verse aucun
    financement tant que la prime reste dans ±0,05 % : c'était la vraie question.
  - **Résultat. Réussi :** +5,21 %/an net à 1x, +4,17 % à 2x, +3,13 % à 3x, t = 11,9 sur 2 078 jours. Chaque année est
    positive aux trois niveaux de coûts ; la pire baisse cumulée est de 0,94 %.
  - **D'où vient le gain.** Presque tout vient du financement. Binance verse son plancher de 0,01 % par 8 h ; Bitfinex
    est à zéro la plupart du temps. Le livre achète sur Bitfinex et vend sur Binance.
  - **Les limites.** C'est la moitié du livre Binance + KuCoin (+10,8 %/an). Il tombe à environ +3 %/an en 2025-2026,
    à peu près le rendement du cash. Surtout, **l'accès à Bitfinex depuis la France n'est pas établi** : pas
    d'agrément MiCA selon des sources secondaires. Il n'y a donc pas de voie papier. C'est une preuve de plus que la
    prime se généralise, pas de l'argent ([résultat](../experiments/xfund_bfx_v1/FINDINGS.md)).
- **Ce qui est encore testé, sur des plateformes utilisables depuis la France.** Des rendements de type « portage » :
  - dépôts dans les coffres HLP/LLP ;
  - financement des perpétuels sur trade.xyz, Lighter et OKX Europe ;
  - quelques règles de week-end ou d'ouverture US.
- **Calendrier.** Pour augmenter la mise, les données décisives arrivent entre le 20 janvier et le 9 février 2027 :
  ce sont les premières lectures des huit livres de portage. Les deuxièmes lectures (réussite ou échec, sans « on
  continue ») tombent du 20 avril au 10 mai 2027.
- **Ce qui tourne.** Tout tourne seul sur GitHub, sans e-mail.
- **Ce qu'on te demandera.** Uniquement les décisions qui sont les tiennes : argent, comptes, gros téléchargements,
  budget, ou rallumer le réveil hebdomadaire. Avant le 15 janvier 2027, deux réponses rendront une réussite
  utilisable tout de suite :
  - sur quelles plateformes tu peux tenir un compte de contrats perpétuels, selon leurs propres règles (Binance,
    Gate, KuCoin, MEXC ; Hyperliquid et Lighter ne demandent qu'un portefeuille) ;
  - la perte maximale que tu acceptes sur un premier essai réel.
- **La règle 6 est la tienne** (« de l'argent réel seulement après que le papier a prouvé un gain net »). Deux options :
  - **A. La garder.** Le premier essai réel attend une réussite sur papier, au plus tôt le 20 janvier 2027.
  - **B. Ajouter une exception pour un pilote de mesure.** Texte proposé, à ajouter à la règle 6 d'AGENTS.md :
    > *Exception (propriétaire, date) : un seul pilote de mesure, d'au plus X $ de capital, peut commencer avant une
    > réussite sur papier. Son plan est figé et enregistré d'abord. Le propriétaire place les ordres. Le pilote est
    > jugé sur l'exécution seulement, et n'augmente jamais sans une réussite sur papier.*

    Dis-moi A ou B, et le montant X si B. Je n'écris pas dans AGENTS.md sans ton accord.

## 1. Money
- **No real money is engaged.**
- **No strategy has passed forward paper.** Real money needs, in order: a forward paper pass, `lab.gate.go_real()`,
  then small stakes placed by the owner ([GATES](GATES.md)). Until then the default is no trade.
- **The hurdle for any strategy is the 13-week bill.**
- **Most ideas tested were real but smaller than their execution cost.** That is the main finding of about 275
  registered rounds.
- **Funding carry is the one premium that held on data nobody had read**, but only on venues that do not serve French
  residents with perpetuals (Binance, Gate, KuCoin, MEXC).
  - **On 2026-11-16 the owner put those venues back in research scope, at their own access risk.** Their lanes (R390
    C14 Binance + Gate, R440 five venues) are forward on paper already.
  - **Measured cost** ([fee map](../research/intake/fee_map_20261116.md)): with venue fees added to R495's book walk,
    C14 pays 18.4 bp a leg a side at $1k (inside its 26.9 bp break-even) and 31.7 at $5k (outside). At zero cost it
    would earn about +3.9%/yr on total capital, near the bill.
  - **Lever M546, a hedged maker on the Gate leg:** R497 measured it on Gate's tape (2026-11-02..15). Verdict
    LEVER_HOLDS: in every volume band it cost at most half of a taker, at a 2 bp and at a 4 bp maker fee. That rests on
    a touch-fill assumption ([FINDINGS](../experiments/gatemaker_v1/FINDINGS.md)).
  - **R498 `gatefill_fwd`** (frozen 2026-11-16, GitHub every 2 h, read after 2026-12-01) measures that assumption on
    R390's own Gate contracts:
    - the queue ahead;
    - fills by trade-through;
    - the Binance hedge 5 s after each fill;
    - crossing the rest at 60 min.
    It is reported beside R390, never changing it.
  - On venues usable from France, a DEX-only carry book (Hyperliquid + Lighter) earned below the bill on seen rows
    ([venue access review](reviews/venue_access_fr_20261110.md)).
- **Under forward test now, on venues usable from France.** These are candidates, not results:
  - vault deposits: R446 HLP/LLP, R447 LLP with hedged LIT, R449 hedged JLP/GM;
  - perp funding carry on trade.xyz and HIP-3: R474 TLT, R479 US stocks, R480 NATGAS against futures (this one also
    needs CME access), R482 xyz against Lighter NATGAS;
  - OKX Europe X-Perps: R441, R443;
  - flow books on Hyperliquid prices: R448, R451, R453, R458;
  - weekend fades: R459, R463, R467;
  - US-open picks on Lighter: R457;
  - vault inventory books: R454, R455.

## 2. What runs
- **GitHub Actions is the only durable runner.**
  - There are 24 `claude-*` workflows.
  - Recorders push to data branches (`claude/*-data`).
  - Paper journals are committed to the default branch `claude/yo-9a1k5w`, about 44 bot commits a day.
- **No PR may have the default branch as its head.** PR #1 did, and every bot commit e-mailed the owner. It was closed
  on 2026-11-16 for that reason; the owner can also mute pushes under the repository's Watch settings.
- **Open registry rows** (`python scripts/lane_census.py`, 2026-11-16, 70 in all):

  | class | rows | meaning |
  |---|---|---|
  | workflow | 39 | named by a workflow and committed within 7 days (not proof that every run succeeded) |
  | codex | 16 | Codex lanes (see below) |
  | writer-lost-noted | 12 | no writer; each lane's README says since when and what a restart needs (listed below) |
  | no-folder | 1 | R180, an old-session row with no code or folder in this repo |
  | no-writer-recent | 2 | R406, R413: read by a session when their locks settle, or on 2027-10-01 |

  - **Codex lanes.** Codex has been unavailable since 2026-11-09. Its R420 runtime ends its dispatch on 2026-11-19
    00:00 UTC by design, then only reports health.
  - **Rows whose writer is gone** (notes written 2026-11-16):
    - daemons that stopped with the container on 2026-11-06: R224, R266, R268, R270, R272, R355, R364;
    - R369, whose tick recorders stopped then; missed EIA releases cannot be recorded later;
    - R286 and R199, whose rows lag their FINDINGS (R286 read once on 2026-11-03; R199 abandoned);
    - R419, run by Codex's R420 takeover until its own end on 2026-11-14, with no read written yet;
    - R184, a draft never frozen;
    - R180, an old-session row; its forward was replaced here by R266.
  - **Rows change status only with their frozen read.** A lane whose writer is gone gets a dated "**Writer lost**" note
    in its README instead; the census then counts it as `writer-lost-noted`. `registry/rounds.csv` is append-only, so a
    row that lags its FINDINGS stays as written and its README points to the result.
- **Agents:**
  - Claude works in cloud sessions, with no always-on host.
  - Its hourly self-wake-up was paused by the owner on 2026-11-13 and stays off. A weekly version is prepared but
    disabled; only the owner turns it on.
  - The OpenHands drafts #97-#100 wait for one reviewed integration batch.
  - Coordination happens on issue #7 ([ROOM](ROOM.md)).

## 3. Dates
| when | what |
|---|---|
| 2026-11-18 00:00 UTC | R404 `book_costs_v1` closed: PARTIAL, 29 snapshots with all three venues out of the 40 required ([FINDINGS](../experiments/book_costs_v1/FINDINGS.md)) |
| 2026-11-19 00:00 UTC | Codex's R420 dispatch ends by design. At the next session, confirm the four `quant-*` workflows only report health, then retire them by the runtime's `active_contract` route |
| 2026-12-01..07 | R498 `gatefill_fwd`: read the queue and fills of a resting Gate order (it changes no lane) |
| owner, any time | Rule 6: keep it (A) or add a measurement-pilot exception (B) ([plan](reviews/plan_20261117.md) section 9). With B, the pilot's plan is frozen and registered before any order |
| before 2027-01-15 | Owner: which venues you can hold, and the stake you would risk on a first real trial ([plan](reviews/plan_20261117.md) section 5); the small-stake plan is frozen with them before 2027-01-20 |
| 2027-01-20 / 01-21 | First looks of carry books R278 (A, B, C) and R279 (A, B), then R294 |
| 2027-02-01 | R469 `asiaclose_c`, its one read |
| 2027-02-02 | R390 C14 Binance + Gate, first look |
| 2027-02-08 | first frozen look of the R441-R447 reads (`claude-xperp-reads.yml`) |
| 2027-02-09 | R440 five-venue carry, first look |
| 2027-02-13 | R474 and R479 futility reads (a NULL stops them; no PASS is possible here) |
| 2027-04-20 / 04-21 | Second looks (PASS or FAIL) of R278, R279, R294 |
| 2027-05-03 / 05-10 | Second looks of R390 and R440 |
| 2027-05-09 / 05-15 | second R441-R447 look; R474 and R479 final; R415 `paperacct_fwd`; R480 and R482 futility |
| 2027-10-01 | R406 and R413 latest read |
| 2027-11-13 | R480 and R482 final |
| count-based | R371/R457 (125, then 500 scored days), weekend lanes R459/R463/R467, R454/R455 (90, then 365 counted days): see each PREREG |

## 4. How the project runs (charter of 2026-11-16; reasons in the review)
1. **Decision first.** A new lane names the decision it feeds and its date. If it cannot decide within about a year
   at a realistic effect, it is registered as monitoring. Existing frozen lanes keep their own scope.
2. **Constraint before signal.** Measure cost, capacity and venue access at the owner's size before testing a
   signal.
3. **Finish before starting.**
   - No more live forward lanes than today.
   - Rows with no writer get their note before a new forward lane opens.
   - At most 3 new registry rows a week, unless the owner asks for more.
4. **One authority per fact.**
   - This page for "now".
   - The registry for rounds and the queue.
   - PREREG and FINDINGS for each lane's scope.
   - Everything else is dated evidence.
5. **Quiet by default.**
   - Automated commits never notify the owner.
   - Claude sends at most one short French note a week, only when something changed or a decision is due.
   - Ids always come with a plain gloss.
6. **Who decides.**
   - **The owner:** money, accounts, keys, large downloads, compute budgets, the hard rules, and any recurring
     wake-up.
   - **Agents, without asking:** maintenance, docs, integration, writer-lost notes, and new lanes within these limits.
7. **Coordination.**
   - Drafts based on the default branch are merged or closed within 7 days of their last push.
   - An R or M id used on any branch is never reused, even if that branch never merges.
   - `AGENTS.md` changes only with the owner's approval.

**Upkeep check** (at each session, or weekly if the owner turns the weekly task on). Each item is bounded to one
session; an item that needs the owner stops and asks:
1. Run `python scripts/carry_timing.py`. It counts the late-day budget of the eight deciding carry books from
   `decisions.csv` only, never their returns. A failed `claude-carry-paper.yml` run is fixed before any other work.
2. Run `python scripts/lane_census.py`.
3. Any `workflow-quiet` row means a writer that stopped: read its last run.
4. Read any decision that falls due.
5. Rewrite this page if anything changed.

## 5. The plan to 2027-05 (from 2026-11-17; reasons in [the plan](reviews/plan_20261117.md))
**Revised the same evening** ([plan](reviews/plan_20261117.md) section 9, [room](reviews/room_haiku_20261117.md)).
Where it differs from items 1-6 below, the revision wins:
- **History has established the premium as well as it can; forward paper cannot prove the return.** At 90 days the
  expected t is about 1.2-1.3. Paper tests mechanics and regime.
- **Execution is the gap.** Real fills, credited funding, transfers, delistings and outages show only live. Two tracks:
  - *Weeks:* R498's read (12-01..07); a replication on a venue never read for carry, frozen before its fetch; and,
    only if the owner takes option B for rule 6, one small measurement pilot, frozen and registered first, placed by
    the owner, judged on execution.
  - *Months:* the eight forward books gate **scaling**, no longer the first small stake.
- **Expect a few percent a year.** Blind replications earned +0.7 to +2.5%/yr (R391, R392). Fixed costs, meaning
  transfers, withdrawals and collateral moves, are priced in any small-stake plan.

1. **One decision.** Should the owner put a small real stake into cross-venue funding carry, on which book, at what
   size, with which orders? The archive supports the premium (R437, R191, R286, R391). Its open doubts concern
   execution: blowout exits whose prices may not be tradable, and gains concentrated in a few days. Only live data
   settle them.
2. **Eight forward books answer it**, each by its own frozen rule. First looks fall on 2027-01-20..02-09, second looks
   (PASS or FAIL) on 2027-04-20..05-10.
3. **First priority: keep them on time.** On 2026-11-17, R278, R279 and R294 can take only 3 more `late` days before
   their January verdict is labelled degraded timing. R390 can take 12, R440 18.
4. **A PASS is made actionable in advance.**
   - The owner answers two questions before 2027-01-15: which venues they can hold, and the stake they would risk.
   - A small-stake plan, with its own registry row, is frozen before 2027-01-20. It covers:
     - gates 2 and 3 for these venues: market orders inside each leg's measured cost, caps, stops, and a margin
       replay;
     - the operations paper does not model;
     - the paired real-against-paper measurement.
   - **A book qualifies only if:**
     - it PASSes by its own rule;
     - it is one of the seven pre-committed books (never R278 C);
     - no more than 3 of those seven are FAIL (a look FAIL or the kill switch).
   - That rule only adds caution; no lane's verdict changes. The cross-lane bar is reported beside every PASS: z 2.69
     for 7 books × 2 looks.
5. **Everything else is monitoring**, read on its date with no interim work.
   - A new forward lane needs at least 80% power within six months at half the archive effect; otherwise the idea
     goes to the queue with its power note.
   - Zero-trial cost or fidelity measurements for the carry decision are exempt.
   - The charter's three rows a week still applies.
6. **If every carry book FAILs,** carry is closed for real money on these venues. The France-reachable reads
   (2027-02..05) decide the fallback, and a new step back comes before any new family.
