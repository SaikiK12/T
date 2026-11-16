# Owner's advocate review (2026-11-16)

Sources: FACTS.md (fact pack), docs/guides/START_HERE.fr.md, AGENTS.md, docs/GATES.md, docs/ROOM.md, and `git log --since='3 days ago'` (read-only). Paths are relative to /home/user/T.

## 1. What the owner needs versus what they get

The owner needs a short, trustworthy answer to two questions: "can this make money for me, and what would it cost me to try?" and "do I have to keep watching this?" Their own words ("rien ne dépend de moi, tu dois tout faire") show they want the machine to run without them, but not at the cost of being misled.

What they get is a research archive. The registry has 275 rows, ids up to R482, and about 9.8 million "program trials" (FACTS.md, Scale). Those numbers measure activity, not returns. No strategy has passed forward paper, and no money has moved (FACTS.md). The decision dates that matter are mostly in 2027 (docs/GATES.md, Dates).

## 2. What the project costs the owner today

- **Email and attention.** Bot commits went to the default branch, so each one emailed the owner. There were about 300 scheduled runs a day and 88 bot commits in 48 hours (FACTS.md, Automation). PR #1 was closed on 11-16 (reversible). The root cause was configuration, not content, and the owner should not have had to find it.
- **Decisions asked.** Issue #7 has 600+ comments (FACTS.md). Four unmerged OpenHands drafts (#97-#100) act "on behalf of" the owner (FACTS.md, Who writes here). Each one is a review item.
- **Conflicting documents.** README says Codex is the single scheduled writer, yet Claude has 735 commits. DIRECTION.md is 900 lines and was last changed 11-02. PANEL.md was last rebuilt 11-14 (FACTS.md, Documents). A reader cannot tell what is current.
- **Risk.** A note says Codex's runtime ends 2026-11-19, three days from now. I did not verify this, but if it is true, the owner should decide it. Also, 67 lanes still say RUNNING although several of their containers no longer exist (FACTS.md). That suggests live activity that is not there.
- **False hope.** "CONFIRMED" (13 rows) means in-sample only, which is gate 0 (docs/GATES.md, The funnel). "DATA_PASS" (10) and "TESTED" (159) read like progress. "PENDING" (76) reads like results on the way, but it includes dead daemon rows.
- **What to remove.** Automated commits to the default branch. Status documents that claim to be current but are not. Catalog recaps and repeated passed checks (the owner's own rule in AGENTS.md says not to spend runs on these). Any substitute for the paused hourly loop: respect the 11-13 pause, do not recreate it through other channels.

## 3. Communication contract (proposal)

- **One French note a week**, on Monday, at most 10 lines, in one place (a single issue or file). Not email. Email only for an owner decision with a deadline.
- **Fixed template:**
  1. Argent: rien engagé / montant (always "rien" until gate 4 is passed).
  2. Ce qui a changé cette semaine (two lines at most).
  3. Décision demandée: aucune, or one yes/no question with the default if the owner does not answer.
  4. Alerte: only if it is real.
- **No bare ids.** Any R### or M### must come with a plain French gloss.
- **Silence is the default.** If nothing changed, the note says "rien à décider" and nothing more.
- **Money in the owner's units.** Give net results after costs at 1x, 2x and 3x (required by AGENTS.md), and convert them to dollars at the owner's size. Percentages per year alone mislead a non-quant.
- **Automation.** Runs that change no decision do not notify anyone, and bot commits stay off the default branch.

## 4. Decisions that are the owner's, and those agents should stop raising

Owner only:
- any real money or stake (AGENTS.md rule 6; GATES.md gate 4);
- accounts, keys and credentials (rule 5);
- large downloads and the historical acquisition budget (rule 5);
- stopping, pausing or budgeting the project, including Codex and OpenHands compute and whether they act in the owner's name;
- priorities, such as which market or venue, given the owner's constraints in France (FACTS.md, Constraints).

Agents should stop asking the owner about:
- id assignment, lane wording within frozen rules, or whether to reopen a lane;
- PR triage, doc reorganisation, comment cleanup or tick cadence;
- whether a null is worth recording (AGENTS.md rule 8 already says record it);
- anything the room protocol (docs/ROOM.md) says a peer agent can settle.

## 5. Honesty check

Yes, in several places.
- **False hope.** The positive numbers (carry +2.86%/yr at 1x for C14; R391 +2.48%/yr; R392 +0.73%/yr at 1x only, FACTS.md) are the best results. They are not executable at the owner's size. OpenHands found carry clears costs only up to about $1k-$5k per leg, and R391 long-tail books cost 28-48 times the assumed unit on most KuCoin contracts (FACTS.md, Scale). Showing these numbers without that caveat invites a bet.
- **Multiplicity.** With 9.8 million program trials, some rows will pass by chance. A single CONFIRMED in-sample row is weak evidence. GATES.md already says so; the summaries should repeat it.
- **False despair.** A count of 128 NULL verdicts can read as failure of the whole effort. Most of those nulls are honest tests of a 1-15 bp/day gross edge against a 9-19 bp/day cost (FACTS.md). That is a real and useful answer ("the fees are the wall"). The owner asked "why always fees?" The honest reply is that fees are the binding constraint, and that is worth saying plainly once, not repeatedly.
- **Spent samples.** Reserved samples are read in batches and their budget is limited (GATES.md, Reserved samples). Once spent, they cannot give a fresh answer. Say so before anyone plans on them.

**Résumé pour le propriétaire (en français):**
Où en est l'argent ? Aucune stratégie n'a encore réussi un test sur des jours nouveaux, et aucun argent n'a été engagé. Le seul écart positif trouvé, lié au financement des contrats perpétuels (environ 2,9 % par an au coût de base, sur une partie des données), n'est pas exécutable à ta taille : une mesure des carnets d'ordres du 15 novembre indique qu'il ne couvre les frais qu'à quelques milliers de dollars par jambe, et qu'il ne tient plus à 10 000 $. La plupart des autres pistes restent négatives après frais, qui pèsent davantage que le gain brut. Les premières décisions sérieuses sont prévues en 2027. Ma recommandation : ne mets aucun argent réel, traite le projet comme une recherche qui peut durer plutôt que comme une source de revenu, et ne fais rien cette semaine.

*Not checked:* I did not run `python -m lab integrity` or read the lane FINDINGS; figures come from the fact pack and the four docs above. The Codex end date is unverified.
