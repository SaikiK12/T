# Epistemics and purpose review (Sonnet, 2026-11-16)

Method: I read the fact pack, AGENTS.md, docs/GATES.md, the first 175 lines of docs/EDGE_SCOREBOARD.md, a scan of registry/rounds.csv, and the FINDINGS of brute5k_v1, carry_holdout and ltroll_v1. I did not read the whole corpus. Speculation is labelled.

## 1. What does the lab actually know?

**Accumulated is not the same as learned. Here is what has been learned.**

- **One reproducible positive: cross-venue funding carry.** It is small, and it is not "only the edge confirmed on reserved samples" in a strong sense. Evidence: R275/R277/R288 and R391 replications on venues never read, and R437/R438 re-ran the headline books on a second engine, where all 7 survive (registry/rounds.csv notes for R437). R483 (same file) checked six forward books against a benchmark (sUSDe) and the notes show several beat it. Plain single-venue carry is about 1%/yr since 2025 (experiments/carry_holdout/FINDINGS.md, "economically small", t 2.07 at 1x, t 1.14 at 2x).
- **Costs are the wall. This is the lab's biggest finding about the world.**
  - The fact pack quotes the OpenHands summary of "1-15 bp/day gross against 9-19 bp/day cost" (FACTS.md).
  - The scoreboard repeats it row after row. Slow factors have gross below 3 bp/day. Fast ones have gross that exists but is below the taker round trip. Examples: R287 PCA reversion, gross +18.8 against cost 18-76; R300, gross +72 against a 34 bp/day round trip (docs/EDGE_SCOREBOARD.md).
- **Backtest costs were wrong in the optimistic direction.** The 2026-11-04 audit F1 found that R354, R356 and R363 "PASS" results recompute to -26.2, -6.6 and -35.9 bp a hop at measured cost (docs/EDGE_SCOREBOARD.md item 1). That is a lesson about the lab's own instruments: modelled fills and costs fail exactly where the edge looks biggest.
- **Mechanisms replicate gross but die at net.** Round-number reversal (R249), the Friday settlement reversal (R289), the funding forecast (R353/R354) and flow cells (R197 to R216) are all real-looking effects below cost or concentrated in a few coins and days (scoreboard).
- **Decay and concentration are the typical failure.** The best "walk-forward" (R263) goes from +5.76 bp/day in 2021H2 to negative by 2025 (brute5k_v1/FINDINGS.md). R349 decays to +0.59 bp a trade since 2025-07. R304's ML ranker "passed" because of a metrics leak (R332).
- **The reserved-sample discipline works.** The lab can say which results are gate 0 and which are not, and it demoted its own CONFIRMED rows (docs/GATES.md).

**What it has merely accumulated.**

- **"9.8 million trials" is a misleading number.** Computed from rounds.csv: the sum is 9,785,313, but the top five rounds (R192 8.3M, R195 0.64M, R185 0.34M, R386 0.30M, R182 0.14M) contribute nearly all of it. The median round has 3 trials. So it is not a measure of multiple testing in any usable sense. Whether it is used as a Bonferroni denominator anywhere is something I did not check. It should not be read as "we searched very hard"; the search count that matters is roughly the number of distinct ideas, perhaps 500 to 1,000 (speculation).
- **Forty method rows come from reels or social posts** (grep of registry/methods.csv for "reel|tiktok": 40 rows). I did not read their outcomes. The scoreboard rows that name a reel or TikTok origin (R283, R293, R306, R307 and others) are all NULL.
- **Many verdicts are "PASS by frozen rule (recorded PARTIAL)"** at gate 0 on seen data. They read as hits in the registry and as nulls in the audits.

**Honest tally.** Zero forward passes. Zero strategies that survive measured cost on unseen data other than carry (small). The lab knows a great deal about where edges are not.

## 2. Is the objective realistic?

The objective is "reproducible positive net return at executable costs and comparable capital/risk" (AGENTS.md).

- **Read literally, it is already met in a thin form.** Carry is positive net at 1x and 2x in the replications. The binding questions are different: capacity, margin, venue access and fees.
  - From the fact pack, OpenHands measured carry clearing cost only at about $1k-$5k per leg, not $10k (FACTS.md; I did not verify, since it is an unmerged PR).
  - Carry needs two venue accounts and cross margin (EDGE_SCOREBOARD row 86).
  - Funding carry in 2025-26 is about 1%/yr on the simple version (carry_holdout).
- **So the reachable edge is small.** My estimate (speculation): single-digit percent per year on a few thousand dollars, which is tens to low hundreds of euros a year. That is real but is not a "trade for a living" outcome.
- **A wiser objective** has three parts.
  1. **Preserve capital and learn at near-zero cost.** Keep paper carry running with an honest net-of-measured-cost ledger.
  2. **Reach one decision** about whether carry at the owner's real size clears real costs. That decision needs live-book costs, not backtest bands.
  3. **Treat everything else as research for its own sake**, with an explicit budget, not as a path to income.
- **"Comparable capital/risk" is under-defined.** Comparable to what? A savings account or T-bill (about 3-4%) is the correct hurdle and the lab already uses a bill hurdle in some lanes (ltroll_v1). Carry at 1-3%/yr does not beat that after tax and effort. The honest answer may be "the owner should not expect profit; the product is knowledge plus a small optional carry book."

## 3. Is the hunting process sound?

Mostly no, with some strong parts.

**Strong.**
- Freeze-before-measure, reserved samples, audit lanes (F1, R437/R438) and reality checks (brute5k_v1 uses a White reality check and a random-selection null).
- Nulls are recorded with the same care as hits (AGENTS.md rule 8). ltroll_v1 shows this: a clean 4-trial NULL with a documented hypothesis.

**Weak.**
- **Pre-registration as ritual.** Freezing a PREREG proves the test was fixed, not that the idea was good. When a lane tests a post hoc lead on seen data and calls it "gate 0, PASS recorded PARTIAL", the ritual is satisfied while the evidence is weak. The R354-R363 chain began from a post hoc look at R353's data and then reused the same hops in R356 and R363 ("Not blind: R362 read those hops' Binance seconds", scoreboard item 1).
- **Garden of forking paths across agents.** Claude, Codex, OpenHands, Kiro and others each add lanes. Each lane is individually frozen. The family-wise error rate across agents is controlled by nothing except the registry's trial counter, which (see section 1) is dominated by a few giant rounds.
- **Idea source.** Forty queue rows come from reels, term lists and podcast guests. Social-media ideas are popular ideas. Popular ideas are crowded or wrong more often than not (speculation, but consistent with every reel-sourced row I saw being NULL).
- **Base rate.** About 275 rounds; 13 CONFIRMED, and 6 of those (R181, R185, R190, R192, R195, R197) were demoted to in-sample (docs/GATES.md). Of the remainder, 6 are carry variants, so there is effectively one surviving idea family. The hit rate for "a new idea that survives cost and unseen data" is about 1 in 150 to 1 in 270 rounds (my arithmetic from rounds.csv).
- **New lanes against closed decisions.** 170 rows in October and 102 in November to the 16th (FACTS.md). 67 are RUNNING or REGISTERED, 46 PENDING and RUNNING, and some in containers that no longer exist. The queue of undecided work grows faster than it closes.
- **Forward lanes are mismatched to power.** The lab's own note says 90 days detect only Sharpe 5 (docs/EDGE_SCOREBOARD.md "What paper trading can prove"), and a Sharpe 1.5 book needs about 1,000 days. The settlement-hop lane needs about 8 months for 40 hops (scoreboard item 1). Most decisions land in 2027. So the forward system mostly cannot confirm a small edge; it can only catch a broken one.
- **Does more searching have positive expected value?** On present evidence, probably not for new hypothesis-hunting on public Binance/Lighter-class data. Each new lane costs attention and automation, and the posterior that a fresh idea nets positive at executable cost is below 1%. Marginal value is higher in (a) measuring true costs and capacity of the existing carry book, and (b) closing or abandoning undecided lanes.

## 4. What would a wise researcher do now?

- **Consolidate and narrow.** Pick the one family with replicated evidence (cross-venue funding carry) and drive it to a gate-2 answer at the owner's real size using live order-book costs. Everything else goes on hold.
- **Change the question.** From "which strategy makes money?" to "does carry at $1k-5k per leg net positive after measured costs, margin and operational friction, and is that worth the owner's time?" This is answerable in months, not years.
- **Stop.** Stop new hypothesis lanes except by an explicit budget. Stop social-media sourcing as a feeder. Stop spawning lanes whose decision is 6-12 months out unless they are the carry decision. Stop reporting "program trials" as a rigor signal.
- **Close the backlog.** Mark the RUNNING rows whose containers are gone as ABANDONED, with a note. This is a records fix; I did not verify which ones.
- **Change the horizon.** Accept that forward evidence at this capital is slow. Either use a cheaper statistical standard (a sequential test with a stated small effect) or accept a decision based on mechanism plus measured cost rather than on Sharpe.
- **Stop believing:**
  - that gross edges are close to net edges,
  - that a PASS recorded PARTIAL at gate 0 is evidence,
  - that more lanes means more progress,
  - that backtest cost bands approximate live books.

## 5. Proposed principles for choosing work

1. **Decision-first.** Every lane names the decision it feeds and who will act on it. If nothing would change on either answer, do not run it.
2. **Cost and capacity before signal.** Measure executable cost at the owner's size on live books before testing whether a signal exists. A signal below measured cost is a null before it starts.
3. **A closure budget.** Open no more lanes than were closed in the previous period. Undecided lanes older than their stated date are closed or explicitly renewed by one writer.
4. **One owner per family, one multiplicity count per family.** A family (carry, flow, settlement hop) has one writer at a time and one honest trial count. The program total is not used.
5. **Name the purpose honestly.** The product is (a) knowledge about what does not work and (b) maybe one small carry book. State the hurdle (bill rate plus effort) and the expected income range. Review that statement every quarter, not only on 2027-04-20 as docs/GATES.md currently plans.

## What I would tell the owner in three sentences

After about 275 rounds the lab has learned that costs eat nearly every edge, and it has one small, replicated edge (cross-venue funding carry) whose real-size profit may be tens to low hundreds of euros a year. More idea hunting almost certainly has negative expected value now, so the right move is to stop opening lanes, close the undecided ones, and answer one question: does carry clear measured costs at your real size. If it does not, the honest outcome is a documented, low-cost research archive rather than a trading business.
