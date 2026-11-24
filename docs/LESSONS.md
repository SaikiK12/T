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

## L030 · 2026-11-24 · Going wide starts in the registry, and a data budget shapes the design
- **What surprised me:**
  - The registry had already closed most of the "obvious" other families:
    - prediction markets: illegal for the owner in France;
    - the crypto variance premium: NULL and shrinking;
    - the overnight drift: R235 NULL.
  - The one structural payer left untested in its basic form was the close (leveraged-ETF and dealer hedging flow).
  - Minute bars would have cost $21, beyond everything the lab has spent ($2.78). Hourly bars ($0.97) keep the
    literature's exact predictor and change only the target (the last hour instead of the last half hour). Writing
    that dilution in the PREREG was cheaper than asking for money.
  - Databento's API crawled (timeouts, minutes a pull). A detached, resumable loop with retries is needed for any
    pull over a few files.
- **What I will do differently:**
  - Before a wide cycle, run the family keywords through `registry/methods.csv` and choose among the gaps.
  - Price data with the free quote before designing. Fit the design to the cheapest data that keeps the predictor
    exact, and write the cost of that choice into the pre-mortem.
- **Instruction changed:** none.

## L029 · 2026-11-24 · Borrowing credit risk: venue failure costs about as much as half the edge
- **What surprised me:**
  - Ordinary credit arithmetic (default rate × loss given default), fed by the published exchange-closure models,
    costs the stake about 2% a year. That is the same size as the gap between the in-sample edge and a halved one.
  - The models put Deribit at 9% a year (crypto only, few coins), yet Coinbase has owned it since 2025. A fitted
    model is blind to facts outside its variables.
  - I had made five web searches over two cycles without logging them.
- **What I will do differently:**
  - Write a counterparty's default rate and recovery next to every edge that leaves money on a venue.
  - Check a model's output against facts it cannot see (owner, age, regulation) before using it.
  - Log each search when it is made: `python -m lab websearch add`.
- **Instruction changed:** none. A stake's rule now needs a forward edge of at least about 5%/yr (stake note).

## L028 · 2026-11-24 · An odd number in my own tool was a bug in my own model (second Millikan save)
- **What surprised me:**
  - The two-account simulation showed **more** liquidations at 1.5x than at 2x on Kraken + Hyperliquid.
  - Looking at those days found the cause in my margin model, not in the market.
    - The uniform-move distance nets an account's long and short legs, so a mixed account reads safe at any
      equity.
    - The equalising split then funded it at its bare maintenance.
  - Last night's ticket figures (64-67% from liquidation at 2x) rested on that flaw. The corrected Kraken lane is at
    29% at 2x, so it gets 1.5x.
- **What I will do differently:**
  - Every new risk measure gets a mixed-direction case in its tests.
  - An outcome that moves the wrong way with its cause (more risk at less leverage) is a bug until shown otherwise.
- **Second occurrence** of L023's lesson (audit an odd or pleasing result at once). `CLAUDE.md` already carries it
  (Feynman: Millikan's oil drop), so this entry confirms that rule and adds no new one.

## L027 · 2026-11-24 · Thorp: the edge is smaller than measured, and the jump sets the size
- **Read:** Thorp 2006, section 7 (`docs/METHOD_LIBRARY.md`). It was overdue: four cycles had passed since the last
  method reading.
- **What surprised me:**
  - **Variance-Kelly is useless here** (about 390x). The size is set by a jump, a venue failing, which no backtest
    of mine models.
  - **At leverage 1, half the in-sample edge of the three forward pairs is below cash.** At leverage 2, the stake
    pays only while venues fail less than 2.5-5% a year. That is the same order as the real risk.
  - **R524's own pair** (Bitfinex + Binance) earned −5.9%/yr in 2026 on R525's engine, from the stale legs R526's
    filters remove.
- **What I will do differently:**
  - Size every stake by the shrunk edge and the worst plausible jump, at most half Kelly.
  - Write the venue concentration next to the edge. Hyperliquid holds 38% of the deposits; spreading the short legs
    is a free reduction of risk.
- **Instruction changed:** `CLAUDE.md`, "Principles from the masters" (Thorp).

## L026 · 2026-11-23 · A field name is not a fact; a live ticket finds what a model hides
- **What surprised me:**
  - **An API label nearly gave a false access verdict.** Kraken's instrument list gives 8 of R509's 20 held coins a
    `dlt` margin schedule and no `europa` one. I read that as "not offered to EU clients": 54-63% of the Kraken
    pairs' in-sample gross sat on such coins.
    - Kraken's own EEA contract list (323 contracts, updated 2026-06-29) includes every one of them.
    - Standing rule 5 (no conclusion without a search) caught it before anything was written.
  - **The ticket found constraints the margin model did not:**
    - Kraken's retail schedule (50% initial on most alts) binds at 2.5x;
    - Binance's minimum orders exclude BTC and ZEC at $42 a leg;
    - lot steps can leave a hedge 7% off.
    The first stake's leverage drops to 2.0.
- **What I will do differently:**
  - Treat an access or rule inference from a field name as a hypothesis, and check it against the venue's own
    published page before it changes a number.
  - Build the concrete artifact (the order ticket on live specs) early. It tests the plan against the venue's real
    rules.
- **Instruction changed:** none. Standing rule 5 already covers the search; this is its first recorded save.

## L025 · 2026-11-23 · Price a risk control against the clean base, on the prices I would trade
- **What surprised me** (R526):
  - **The cheapest check removed the tail.** "Do the two legs show the same price at entry?" blocked LUNA (legs 5x
    apart) and ANC, at no cost.
  - **The hourly stop passed my frozen rule while doubling drawdowns.** The rule compared each limit with the
    *delayed* base, which holds LUNA's −86% day. Any limit looked good against that.
  - **On Bitfinex's last-trade closes, 92% of stops reverted within a day.** Some "filled" at outlier prints (−166% of
    a leg). The simulated stop measured data quality, not the control.
- **What I will do differently:**
  - A rule for a control compares it with the clean base on Sharpe and drawdown, as well as with the stressed base.
  - Simulate a control on the prices it would execute at (book mids), or say that it was not.
  - Try the simplest invariant check first (prices agree, a leg prints) before a dynamic rule.
- **Beat the plan, first use.** The planned forward sleeves would have added pairs that correlate up to 0.94. The
  three-lane combined read (R527) adds the one independent piece, with power 0.86 against 0.74, and it had to be
  frozen before 2026-11-25.
- **Instruction changed:** none yet. The first point joins the pre-mortem in `CLAUDE.md` step 4 if it recurs.

## L024 · 2026-11-23 · Treating my own choices as data
- **The owner.** "Tu dois t'améliorer et voir les choses qui seraient encore mieux à faire par toi-même."
- **Measured** ([self-review](reviews/self_review_20261123.md)):
  - plumbing and scale lenses earned;
  - transfers without the cause failed;
  - 4 of 5 FAILs had a design flaw a pre-mortem would have named;
  - 6 plumbing bugs; 5 process misses the owner had to correct.
- **What I do differently:**
  - each choice names one unasked, higher-value item;
  - a pre-mortem before each freeze;
  - a self-review every tenth cycle, with lenses ranked by yield.
- **First unasked item, started now:** pricing the risk limits (divergence stop, per-coin cap) on R525's pairs.
- **Instruction changed:** `CLAUDE.md` steps 2, 4 and 5.

## L023 · 2026-11-23 · Auditing the pleasing result found its tail at once
- **What happened.** Applying Feynman's rule (L022) to R525, a one-day decision delay kept 82-105% of 11 pairs'
  returns, so there is no lookahead.
  - It also exposed LUNA, May 2022: one delayed entry lost about 34x a leg's notional as the hedge broke between
    venues.
  - It showed stale-looking Bitfinex legs (−64 to −84% price moves on one coin across two venues).
- **Surprise.** The robustness check found the risk that matters for money: the broken hedge, at a speed no daily
  check sees. The base run had missed LUNA by one day.
- **What I do differently.** Every passing carry result gets a delay test and a worst-trade review, and the worst
  trade sets a risk limit. The stake note now requires an hourly divergence stop and a per-coin cap.
- **Instruction changed:** none. Feynman's line in `CLAUDE.md` already says it; this is its first payoff.

## L022 · 2026-11-23 · Better rules come from the best sources, not only from my mistakes
- **The owner.** My advice must improve too, and the best moments came from precise passages of good books. Find ways
  to improve constantly.
- **Read myself:**
  - Feynman's "Cargo Cult Science" (in full);
  - Hamming's "You and Your Research" (in full);
  - López de Prado's "10 Reasons" (pp. 4-5 and 18).
- **Surprise.** Feynman's Millikan story describes what I did with R519: I hunted the loader bug only because the
  result was bad. R525's pass got no such hunt.
- **What I do differently:**
  - audit good results as hard as bad ones;
  - explain an edge before re-backtesting it;
  - keep the important-problems list;
  - every fourth cycle, read one method source and keep only rules that change decisions.
- **Instruction changed:**
  - `CLAUDE.md` gains "Principles from the masters" and the reading cadence in step 5;
  - `docs/METHOD_LIBRARY.md` holds the passages and the reading queue.
- **Next, by Feynman's rule:** a Millikan audit of R525 before more forward lanes (breakthrough review, item 0).

## L021 · 2026-11-23 · Digging at once (rule 2) produced the lab's broadest result
- **What happened.** Instead of waiting on R524's workflow, I widened the framework result at once. R525 ran all 12
  floorless × floor pairs, and all pass.
  - The portfolio earned +7.8%/yr, Sharpe 5.5, max drawdown −0.73% over 5.7 years.
  - The whole round took about 40 minutes, including the freeze.
- **Surprise.** Kraken against Binance, Gate or KuCoin earns more (+31%/yr) than Kraken against Hyperliquid (+22%).
  The thin side is the source, and any floor venue harvests it.
- **What I do differently.** When a mechanism replicates, map its whole space (every venue pair, every coin set) in
  one registered round before building lanes one by one.
- **Instruction changed:** none. Standing rules 1 and 2 already say it; this is the evidence they work.

## L020 · 2026-11-23 · I waited on a workflow after a breakthrough, though the owner had told me not to wait
- **What happened.**
  - After the framework result (four design-gap books nearly uncorrelated; Sharpe 8.5 together), I built R524 and
    then ended a turn "waiting for the journal".
  - The owner: "Ta eu un breakthrough énorme je crois donc creuse ou creuse à côté au lieu d'attendre des workflows…
    ta rien retenu donc self improve."
  - They had said it before, in other words: cut the waiting, find a useful distraction.
- **Surprise.** My chain recorded lessons from data and code, but not the owner's process advice. So it was not
  retained.
- **What I do differently.**
  - Every piece of the owner's working advice is a numbered standing rule at the top of `CLAUDE.md`, read before
    anything else.
  - Background jobs never end a turn.
  - A strong result triggers digging at once.
- **Instruction changed:** `CLAUDE.md` gains "Standing rules from the owner" (10 rules).

## L019 · 2026-11-23 · A silent overwrite broke a hard rule; the full suite caught it
- **What happened.**
  - I wrote R522's fetcher with `cat > scripts/fetch_deribit_trades.py`. A script of that name already existed: the
    options-flow fetcher that five older lanes name.
  - The provenance step overwrote its record too.
  - Two days later the full test suite, run before adding `lab/bitfinex.py`, failed on that file's tests.
- **Repair.** The original and its provenance are restored. R522's fetcher is kept byte-identical under a new name,
  and its data moved to its own folder ([DEVIATIONS](../experiments/dmake_v1/DEVIATIONS.md)). The result is
  unchanged.
- **What I do differently.** Check that a path is new before writing it, and prefer the file tools, which refuse to
  overwrite an unread file.
- **Instruction changed: added at once to `CLAUDE.md`'s habits.** It breaks AGENTS.md's "frozen files are never
  edited", so it does not wait for a second time.
- **Also:** one frozen R520 test assumed an empty journal; it now fails by design (noted in R520's DEVIATIONS).

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
