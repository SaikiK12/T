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

## L018 · 2026-11-23 · Breadth also buys time: a combined read is due a week before either lane's
- **Choose.**
  - Lens: "the owner's reach". Money arrives sooner if evidence does.
  - The binding constraint: time to evidence.
- **Make.** R523 reads R509 and R520 together (independent pairs; funding-net correlation −0.04 in sample).
  - Calibrated before the freeze at threshold 3.0: power 0.78 at 20 common days and 0.92 at 30, against about 0.8 at
    20 days for either lane alone at the looser 2.5. Size 0.046 / 0.038.
  - Look 1 falls about 2026-12-13, a week before R510.
- **Surprise.** At 2.5 the combined read over-rejected (size 0.06-0.08) on short windows. NW with lag 5 on 20-30
  autocorrelated days is liberal. Checking size on demeaned history caught it.
- **What I do differently.** Calibrate every early-look threshold for size on demeaned history, not only for power.
- **Instruction changed:** none yet. With L012's power check, this is the same family ("do the arithmetic before the
  freeze"), so it joins that line if it recurs.

## L017 · 2026-11-23 · The owner's "higher than strategies" was right, in a measurable form
- **Question.** Are frameworks better than strategies?
- **Answer, measured.** The four design-gap books are almost uncorrelated, so equal weight lifts Sharpe to 8.5 and
  cuts the drawdown to a third ([note](reviews/framework_20261123.md)).
- **Surprise.** I had treated the pairs as replications, evidence for one claim. They are also diversifiers, and the
  combination is the product.
- **What I do differently.**
  - When an edge replicates, measure the cross-correlation of its replications before anything else.
  - Plan forward evidence and sizing at the portfolio level.
- **Instruction changed: added to `CLAUDE.md`'s lenses.** "Change the scale" now names "from one replication to the
  portfolio of replications".

## L016 · 2026-11-23 · Money readiness is measurement too
- **Choose.** Item 4 of the breakthrough review. Lens "invert": how does a hedged, levered book die? By one venue's
  account being liquidated on a market-wide move before the other venue's gain can be moved across.
- **Make.**
  - `lab/margin.py`: liquidation move, the equalising split and the rebalance transfer, all tested.
  - `scripts/stress_dhl.py`: worst 24 h basket moves of −24% / +21% over 2023-26.
  - So leverage is capped at about 2.5 with daily rebalancing ([note](reviews/stake_dhl_20261123.md)).
- **Surprise.** Single-coin spikes (+86% on TRX in 24 h) look scary, but on 20 slots of cross margin they are a few
  percent of the account. The binding risk is the market-wide move and the transfer delay.
- **What I do differently.** Size leverage from measured worst moves and the rebalance cadence. Never from a venue's
  maximum leverage.
- **Instruction changed:** none.

## L015 · 2026-11-23 · Readiness rules built for liquid venues misread thin ones; and a restart loop can eat a day
- **What happened.**
  - **A restart loop.** The worker restarted for about 38 hours, so 20 scheduled cycles queued and none ran. The
    forward lanes kept running on GitHub. They live outside this container, and that is why they survived.
  - **R520's first scored Sunday was late.** Carrylane's readiness ratio (fresh coins today over yesterday, at least
    0.9) fell to 0.759 on Deribit's thin perps on a quiet day.
- **Surprise.** I checked bar times (L011), but not how "fresh" behaves when coins can go a day without a trade.
- **What I do differently.**
  - For a new venue, run the lane's readiness and freshness rules on a week of its real data before the freeze, and
    note weekend behaviour.
  - Keep every lane that must not stop on GitHub, not in this container.
- **Instruction changed:** none yet. The first half joins L011's loader check if it happens again.
- **Owner reels 2026-11-23:** caption-only (Instagram answered 429). An order-flow funnel on families already NULL;
  no test.

## L014 · 2026-11-21 · A conservative fill rule can be the most adverse-selected one
- **Choose.** Lens "invert". Bet 2: make on thin books, hedge on the liquid venue.
- **Make.** R522 was frozen before the data, with the break-even written (adverse selection under about 7 bp). It
  FAILed hard: −27 bp a fill, every k loses, NW t −6.6.
- **Surprise.** "Fill only when a trade prints through the quote" is conservative about how many fills happen, but it
  keeps exactly the toxic ones: the takers who sweep the book because the price is moving.
  - The rule also used a stale index between trades.
  - Even 2-5 second fresh fills lost 5 bp.
- **What I do differently.** For any passive-fill study, ask which fills the rule keeps, not only how many. If the
  rule keeps the most informed side of the flow, the result is a lower bound and is labelled one. Touch fills need
  book data.
- **Instruction changed:** none yet. It joins the break-even and power checks if it happens again.

## L013 · 2026-11-21 · A "breakthrough" story becomes a number when it is written per unit of what earns it
- **Choose.**
  - Lens: "who pays, and why must they?" New venues buy volume with tokens.
  - The binding constraint: an idea with a large tail (Bet 3).
- **Read myself.** Hyperliquid's $1.2B and Lighter's $675M sound like a breakthrough.
  - Divided by the volume that earned them, they are about 3 bp and 1 bp or less.
  - That is a rebate, and it matters only to a strategy that trades real volume.
- **Surprise.** Twenty minutes of division moved Bet 3 from "asymmetric jackpot" to "a fee rebate inside Bet 2".
- **What I do differently.** For any large headline payout, compute it per unit of the input that earned it (volume,
  capital-month, event) before ranking it.
- **Instruction changed:** none yet. It belongs with the break-even step if it happens again.
- **Also:** the owner asked for continuous work. The existing weekly task is re-enabled every 2 hours as one chain
  cycle per wake. No second loop was created.

## L012 · 2026-11-21 · The power check saved a forward lane from a rule that could not pass
- **Choose.**
  - Lens: "the owner's reach". A forward lane on venues the owner can use.
  - The binding constraint: time to evidence for R519's gap.
- **Make.** R520 runs R275's book on Deribit + Hyperliquid forward, with a new `lab/deribit.py` (hourly bars, closes at
  00:00 UTC, per L011). A scratch dry run on 3 coins passed end to end before the freeze.
- **Surprise.** I was about to reuse R512's anytime rule (E >= 40 by day 180). At R519's daily Sharpe ratio of about
  0.20, it needs about 300 days, so it would have FAILed a true edge at 180.
  - Two fixed looks have about 30% power at 90 days and about 75% at 180.
- **What I do differently.** Before freezing any decision rule, write the expected t (or crossing day) at each look
  from the in-sample effect. If power by the last look is under about 50%, change the rule or the horizon.
- **Instruction changed: promoted.** With L009's break-even, this is the second "do the arithmetic before the
  freeze" lesson. `CLAUDE.md` step 4 now names power next to the break-even.

## L011 · 2026-11-21 · The owner asked for a faille: the gap is real on liquid coins, and I locked the wrong sign
- **Choose.** The binding constraint: R508's faille has little capacity.
  - Lens: "follow the plumbing", scanning venues' funding rules.
  - **dYdX** is floorless on its cross markets, but nearly dead ($18.7M a day; median market $1.3k).
  - **Drift** added a 10.95% floor.
  - **Deribit** has a ±0.025%/8 h dead zone and no interest term.
- **Make.** R519 was frozen with the break-even written. Two plumbing bugs came up before any result: a "not open"
  perp, and Deribit's day starting at 08:00 UTC.
  - **The decided static book failed.** Its 30-day entry window chose the sign in June 2023, when Deribit's premia were
    high, and held the wrong side for 3.4 years.
  - **The reported R275 book passed every check:** +4.5%/yr, t 7.0, 49 coins.
- **Surprise.** Applying L009 ("fit the rule to the edge"), I fixed the holding but not the sign. A design asymmetry
  gives its own sign.
- **What I do differently:**
  - when the edge is a design gap, hard-code its direction;
  - before freezing a loader, check where each venue's day starts.
- **Instruction changed.** Step 4 of `CLAUDE.md` is extended: fit the rule to the edge, including its sign.

## L010 · 2026-11-21 · A check-in: read what a label means before calling a day late
- **What happened.** The 00:31 UTC clock dispatch decided 2026-11-21 on time for R509 and R512 (01:18-01:19 UTC).
  The day row labelled 2026-11-21 still says `late`.
- **Why.** `lab/carrylane.py` gives a day row the kind of the previous day's decision, and the 2026-11-20 decision
  was late.
- **Surprise.** I nearly read a fixed pipeline as broken.
- **What I do differently.** For any status flag, find the line that sets it before acting on it. I checked only
  `day`, `kind` and `run`, never results, as the sealed-interim rule asks.
- **Also.** A reminder is set for R510's first look (about 2026-12-20).
- **Instruction changed:** none.

## L009 · 2026-11-20 · Plumbing found a real gap, and arithmetic I had already written killed it
- **Choose.**
  - Lenses: "change the scale" first (a lab-wide McLean-Pontiff decay), then "follow the plumbing".
  - The decay could not be measured cleanly: forward interims are sealed until their reads, and only about ten
    finished pairs exist.
  - **What the registry does show:** carry replicated five times on new venues, while price-pattern passes failed
    their confirmations (R192→R201, R462→R464, R188→R189). That is why I stayed in carry, in writing.
- **Read myself.** Hyperliquid's HIP-3 deployer actions let each deployer set a funding multiplier, an interest rate
  and a clamp per asset. `perpDexs` shows them differing for the same ticker: Felix 0, Dreamcash ~0, xyz 0.5, mkts
  the default.
- **Make.** Two lanes, both frozen before the data existed:
  - **R517**, R516's listing phase on HIP-3: FAIL. 18 trades, t 1.31; stock-perp premia are small and turn.
  - **R518**, the design gap: FAIL. Funding +0.32% a trade, costs 0.28% a trade, net about 0.
- **Surprise.** R518's PREREG already said the gap was 2.5-5.5%/yr on capital before costs, and that a PASS needed
  more. I wrote the break-even and froze anyway.
- **What I do differently.** Before the freeze, compare edge per trade with cost per trade. If my own arithmetic
  says thin, change the rule to fit the edge (a static hold for a constant gap) or do not spend the trial.
- **Also learned.** A mechanism travels only with its cause. R516's extremes came from free-floating premia on thin
  crypto books; HIP-3 stocks are pinned to an oracle every 3 seconds.
- **Instruction changed: promoted.** With R470 (the same thin stock carry) this is the second time, so `CLAUDE.md`
  step 4 now asks for the break-even before the freeze.

## L008 · 2026-11-20 · The first session run by the chain
- **Open.** The lessons pointed away from Kraken and from subagents.
- **Choose.**
  - Binding constraint: the carry books earn about the cash rate.
  - Lens: "who pays, and why must they?"
- **Two candidates.**
  - Forced sellers (family E2) was my first pick. Checking the registry first showed five earlier rounds (R206, R252,
    R255, R303, R308), mostly NULL. Skipped, and that saved a trial.
  - V1 (collateral yield, incentives) was the one family never measured. Chosen.
- **Read myself.** Five pages of venue docs, plus one API call.
  - Hyperliquid's portfolio margin pays idle USDC 2.65%/yr today, and the live state matches its formula.
  - Aster's USDF trading rewards need $50k of volume a week
    ([venue_yield_20261120.md](../research/intake/venue_yield_20261120.md)).
- **Surprise.** The binding fact was eligibility (a $10k account; $50k a week of volume), not the rate.
- **What I do differently.** For any incentive, read who qualifies before reading what it pays.
- **Instruction changed:** none yet. It becomes one if it happens again.

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
