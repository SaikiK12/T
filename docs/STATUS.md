# Status: what is true now

**Rewritten in place, never appended. Last rewrite: 2026-11-16 by Claude.**
- If this date is more than two weeks old, trust `registry/rounds.csv` and `python scripts/lane_census.py` over this
  page.
- Why this page exists: [reviews/stepback_20261116.md](reviews/stepback_20261116.md).
- The owner's reading guide: [START_HERE.fr.md](guides/START_HERE.fr.md).

## En bref (pour le propriétaire)
- **Argent.** Aucun argent réel n'est engagé. Aucune stratégie n'a encore réussi l'épreuve du papier sur des jours
  nouveaux. La règle par défaut est donc : pas de trade.
- **Ce qu'on a appris.** La plupart des idées étaient réelles mais plus petites que les frais pour les exécuter.
- **Plateformes (décision du 16-11-2026).** Tu as remis Binance, Gate, KuCoin et MEXC dans le périmètre, à ton
  risque d'accès (gel possible d'un compte ou des retraits pour un résident d'un pays non servi). L'argent réel
  reste ton geste.
- **Frais.** Il existe des routes à 0 frais même par API (Lighter, et Paradex « retail »). Ce qui coûte encore,
  c'est l'écart entre prix d'achat et de vente. Sur Binance + Gate, le portage C14 ne couvre ses coûts qu'à
  1 000 $ par jambe. Le levier non testé : un ordre posé sur Gate, couvert aussitôt sur Binance
  ([carte des frais](../research/intake/fee_map_20261116.md)).
- **Ce qui est encore testé, sur des plateformes utilisables depuis la France.** Des rendements de type « portage » :
  - dépôts dans les coffres HLP/LLP ;
  - financement des perpétuels sur trade.xyz, Lighter et OKX Europe ;
  - quelques règles de week-end ou d'ouverture US.
- **Calendrier.** Premières lectures d'arrêt en février 2027. Première réussite possible en mai 2027.
- **Ce qui tourne.** Tout tourne seul sur GitHub, sans e-mail.
- **Ce qu'on te demandera.** Uniquement les décisions qui sont les tiennes : argent, comptes, gros téléchargements,
  budget, ou rallumer le réveil hebdomadaire.

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
    would earn about +3.9%/yr on total capital, near the bill. The untested lever is a hedged maker on the Gate
    leg (M546).
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
- **Open registry rows** (`python scripts/lane_census.py`, 2026-11-16, 69 in all):

  | class | rows | meaning |
  |---|---|---|
  | workflow | 38 | named by a workflow and committed within 7 days (not proof that every run succeeded) |
  | codex | 16 | Codex lanes (see below) |
  | no-writer | 13 | no workflow and no commit for more than 7 days (listed below) |
  | no-writer-recent | 2 | R406, R413: read by a session when their locks settle, or on 2027-10-01 |

  - **Codex lanes.** Codex has been unavailable since 2026-11-09. Its R420 runtime ends its dispatch on 2026-11-19
    00:00 UTC by design, then only reports health.
  - **Rows with no writer:**
    - daemons that stopped with the container on 2026-11-06: R224, R266, R268, R270, R272, R355, R364;
    - R369, registered with a container daemon;
    - R286, reserved batch 1, last commit 2026-11-03;
    - R419, a Codex lane meant for Claude's container, never run;
    - older ARMED/PLANNED/REGISTERED rows: R180, R184, R199.
  - **Rows change status only with their frozen read.** A lane whose writer is gone gets a dated "**Writer lost**" note
    in its README instead; the census then counts it as `writer-lost-noted`.
- **Agents:**
  - Claude works in cloud sessions, with no always-on host.
  - Its hourly self-wake-up was paused by the owner on 2026-11-13 and stays off. A weekly version is prepared but
    disabled; only the owner turns it on.
  - The OpenHands drafts #97-#100 wait for one reviewed integration batch.
  - Coordination happens on issue #7 ([ROOM](ROOM.md)).

## 3. Dates
| when | what |
|---|---|
| 2026-11-18 00:00 UTC | R404 `book_costs_v1` closes (cost snapshots; its writer is the workflow) |
| 2026-11-19 00:00 UTC | Codex's R420 dispatch ends by design. At the next session, confirm the four `quant-*` workflows only report health, then retire them by the runtime's `active_contract` route |
| 2027-02-01 | R469 `asiaclose_c`, its one read |
| 2027-02-08 | first frozen look of the R441-R447 reads (`claude-xperp-reads.yml`) |
| 2027-02-13 | R474 and R479 futility reads (a NULL stops them; no PASS is possible here) |
| 2027-05-09 / 05-15 | second R441-R447 look; R474 and R479 final; R415 `paperacct_fwd`; R480 and R482 futility |
| 2027-10-01 | R406 and R413 latest read |
| 2027-11-13 | R480 and R482 final |
| count-based | R371/R457 (125, then 500 scored days), weekend lanes R459/R463/R467, carry books R390/R440, R454/R455 (90, then 365 counted days): see each PREREG |

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
1. Run `python scripts/lane_census.py`.
2. Any `workflow-quiet` row means a writer that stopped: read its last run.
3. Read any decision that falls due.
4. Rewrite this page if anything changed.
