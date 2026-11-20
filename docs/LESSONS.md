# Lessons: the memory of the improvement chain

How this file works ([CLAUDE.md](../CLAUDE.md), step 5):
- **One entry per session or round,** newest first, appended and never rewritten. A correction is a new entry that
  names the old one.
- **Each entry says:**
  - what happened, with a link to the evidence;
  - what surprised me;
  - what I will do differently;
  - which instruction it changes.
- **Promotion.** A lesson seen twice moves into `CLAUDE.md`.
- **What does not belong here:** lane facts. Those stay in each lane's FINDINGS and in the registry.

## L007 · 2026-11-20 · The owner: stop the subagents, stop the venue tunnel
- **What happened.** For three days most rounds turned around Kraken (R508-R515), because a regulated venue looked
  like the shortest path to a stake. Readers were Haiku subagents.
- **The owner's correction.** "Ne reste pas bloqué à Kraken ou autre et arrête de lancer des subagents."
- **What I do differently:**
  - read myself;
  - rotate lenses;
  - write the binding constraint before choosing.
- **Changes:** created `CLAUDE.md` and this file. The rule "no venue or family three sessions in a row" is in
  `CLAUDE.md`, step 2.

## L006 · 2026-11-20 · A blind spot found an edge; counting the supply found its limit
- **What happened.** R516 asked what R275's engine can never trade (a coin's first three weeks on a venue). It passed:
  t 5.77, +1.76% net per trade ([FINDINGS](../experiments/xfund_listing_v1/FINDINGS.md)).
- **But the events fell** from 43 in 2023 to 6 in 2026, and the Kraken count was 1-2 a year.
- **Surprise.** I counted 87 events before the freeze, but not per year. The yearly count would have shown the dry-up
  before I spent the trial.
- **Changes:** `CLAUDE.md` step 4 now says to count the supply per year before freezing.

## L005 · 2026-11-20 · Verify the one page that changes expectations
- **What happened.** A reader's card said single-venue carry turned negative in 2025. I re-read printed pp. 26-27 of
  Borri, Liu, Tsyvinski & Wu myself and confirmed it: Sharpe 6.45, then 4.06 from 2024, then negative in 2025
  ([reading round](../research/intake/reading_round_20261120.md)).
- **Also seen:** the same reader flattened a table and had to infer its columns.
- **What I do differently.** Claims that change expectations or money are read at the source by me. Now that readers
  are stopped, this is simply how I read.

## L004 · 2026-11-20 · Reading by question costs half and yields more
- **What happened.** Question bank, then locate, then pages, then mini-cards. This cut tokens about 55% against the
  whole-library readers of 2026-11-19, and each question ended in an answer
  ([protocol](../research/intake/reading_protocol.md)).
- **Lesson.** A question that names the decision it serves is what makes reading pay.

## L003 · 2026-11-19..20 · In-sample passes are mostly their early years
- **What happened.** By year:
  - R507: 2021-24 about +5.5%/yr, 2025-26 about +2.7%/yr;
  - R516: 2023 carries most of the gain;
  - Borri et al.: carry compressed from 2024.
- **Lesson.** Read the by-year table before the headline, and judge forward lanes against cash, not against 2021-24.
- **This is the second time,** so it is promoted into `CLAUDE.md` step 4.

## L002 · 2026-11-19 · Infrastructure changes have hidden keys
- **What happened.** Adding a path to a shared GitHub Actions cache changed the cache's version key. Every lane lost
  its cache, and R278 crashed rebuilding from APIs.
- **Lesson.** Before editing shared workflow plumbing, ask what else keys on it. Give a new lane its own cache.

## L001 · 2026-11-18 · Regulated access is a fact to check, not to assume
- **What happened.** Kraken EEA advertises 10x, while ESMA's 2026 statement makes retail perps likely CFDs (2:1). The
  conflict is still open on Kraken's pages.
- **Lesson.** Access and leverage rules are read at the source, by me. A venue's own marketing is not the rule.
