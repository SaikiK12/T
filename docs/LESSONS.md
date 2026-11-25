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

## L053 · 2026-11-25 · Correction to L052: I compared a gross ratio with a net one, and the room's critic caught it
- **What happened.** L052's "Fermi kept one idea… TSLA 15-45 times crypto" was wrong. Evidence:
  `docs/reviews/room_20261125b/critic_greeks.md`, checked by me.
  - TSLA's figure was gross open-interest gamma over an assumed volume.
  - Crypto's 0.13% is the dealer's net from taker flow.
  - The same registry row (`registry/methods.csv:280`) gives crypto's gross at about 8% of perp volume. Gross with
    gross, TSLA is about 2× crypto (18% of a measured $13.2bn a day), and its dealer net is unknown.
  - **Same page, two more slips:**
    - an assumed volume ($40bn) where a free fetch gave $13bn;
    - a snapshot that contradicts my O3b prediction, which I called a "fit".
- **What surprised me.** All three errors pushed toward a cleaner story. A Haiku critic with a checklist found them in
  five minutes. My own re-reading had not.
- **What I will do differently:**
  - **Numerator discipline.** A ratio is compared only with the same numerator (gross with gross, net with net), and
    the decisive quantity is named before the comparison.
  - **No assumed input** when a free fetch gives the number.
  - **A critic reads every reflection page before it reaches the owner.** This is rule 3's room used as a gate, not
    as a decoration.
- **Instruction changed.** `CLAUDE.md` approach item 4 now says the dealer's **net** forced trade. This entry corrects
  L052; it does not rewrite it.

## L052 · 2026-11-25 · One ratio decides the Greek class, and the incumbents' quotes come before the world's data
- **The owner.** "Réfléchis à des choses que toi tu peux créer… le gamma, le vanna, le vomma… pose-toi des questions…
  si c'est la vérif qui limite, débloque-la." Evidence: `docs/reviews/reflection_20261125_greeks.md` and register
  O1-O6.
- **What surprised me:**
  - **The deciding number was already in the lab.** R292 measured crypto dealer gamma at 0.13% of perp volume per 1%
    move. That explains all of the lab's NULL crypto Greek rounds, and the room's literature reader did not know it.
  - I spent the first part of the cycle verifying paper figures, all of which held, before asking which figure
    decides the subject.
  - **Fermi ended three ideas without a test:**
    - SPX charm before the SOQ: $300M against $29-82bn of overnight ES volume, which I measured. The square-root law
      predicts 4-6 bp, worth under 2%/yr at 12 chances a year.
    - Crypto vanna: the same 0.13% ratio.
  - **Fermi kept one idea for $0.08.** TSLA option gamma is about 6% of the stock's daily volume, 15-45 times
    crypto's ratio.
  - **The weekend clock was settled in ten minutes from our own Deribit snapshots.**
    - Market makers already price Saturday at about half a weekday's vol, and they are right: a 75-88 bp straddle
      against a 77-81 bp mean move.
    - The field's best evidence agrees: Deribit's own backtest, read on the page after my prediction was committed.
      Selling on Sunday loses, and buying on Sunday nets 2.1%/yr.
- **What I will do differently:**
  - Before a class of ideas, I find the one ratio that decides it, and I look for it in the lab's own results first.
  - For a forced flow, that ratio is the forced trade over the liquidity in the window where it must trade.
  - For a pricing-convention gap, I read the incumbents' quotes (their term structure, their book) before measuring
    realized data. A gap they already price is no gap.
- **Instruction changed.** `CLAUDE.md`, "How I approach a subject":
  - item 3 gains "read the incumbents' own quotes first";
  - item 4 gains the forced-flow ratio, with a stop below about 0.5%.

## L051 · 2026-11-25 · Verification is work I can build, and memory is a file, not my context
- **The owner.** "Pose-toi des questions sur les choses où tu ne peux pas savoir si c'est acquis… raffine-les… si
  c'est la vérif qui limite, débloque-la… souviens-toi de ce que j'ai dit avant tes compressions."
- **What surprised me:**
  - **Re-reading all 27 of the owner's messages** (extracted verbatim from the transcript into
    `docs/OWNER_LEDGER.md`) showed instructions my summaries had lost. On 11-19 the owner asked for whole books read by
    Haiku, one message per part, with me understanding the key parts.
  - **A mechanical citation checker** (`scripts/verify_citations.py`) cut the first room's 129 citations to 21 that
    need my eyes. One of the 21 was a claim I would otherwise have repeated (KuCoin +20-24%/yr).
  - **The critic found a money number I had to correct** (the December stake's costs, verified in R508's own
    FINDINGS).
  - **It also produced a figure I could not reproduce** (a lag correlation). Both outcomes are what verification is
    for.
- **What I will do differently:**
  - Room claims come with exact quotes, the checker runs on every report, and my reading goes to the failures and to
    what moves money.
  - The owner's words are read from the ledger at each open step.
  - Open questions go in a register and are refined before any test.
- **Instruction changed:** `CLAUDE.md` gains rules 13 (open-question register), 14 (verification as work) and 15 (the
  owner ledger). Step 3 gains whole-book Haiku reading.

## L050 · 2026-11-25 · The owner: think together with a Haiku room, always. Its best output came from comparing rules
- **The owner.** "Vois des façons de t'améliorer x100… re-vérifie tout le repo… invente… lance des subagents,
  toujours Haiku, pour penser ensemble, toujours." `CLAUDE.md` rule 3, chain step 3 and the habits were changed the
  same turn. The two-hourly task now launches the room every cycle.
- **What surprised me** (eight Haiku members, about five minutes each; `docs/reviews/room_20261125/`):
  - **The auditors found what my memory had lost:**
    - R304's PARTIAL is superseded by R332's presence leak;
    - R197 is labelled CONFIRMED although its holdout R198 is NULL;
    - isolated margin liquidates carry books even at 1x (R280). I then checked that none of R509's Hyperliquid coins
      is isolated-only.
  - **The framework member found a risk larger than the edge:** euro-dollar swings on a dollar principal.
  - **The best lead came from the rules-matrix readers, not the inventor.** Variational freezes its equity index on
    weekends while xyz moves; a public API exists, so it is now recorded. The inventor's own ideas were worth €10-100
    a year. Comparing rules beats imagining them, the same lesson as the original design gap.
  - **Verification was needed:**
    - the framework member's "inconsistent figures" were consistent (costs grow with size);
    - an auditor's suggested 20:30 entry would miss the reversal (R465's hourly table).
- **What I will do differently:**
  - Generation is now cheap and verification is the bottleneck. Every room claim that moves something gets a
    source check, and the checks go in the synthesis.
  - The rules matrix (venues × mechanisms) is the room's standing job.
- **Instruction changed:** `CLAUDE.md` rule 3, chain step 3, and the habit (owner 2026-11-25).

## L049 · 2026-11-25 · The field's best paper belongs before the design, not after it
- **What surprised me:**
  - Once the weekend family became the best capacity × edge candidate, I searched for its literature. An arXiv
    preprint of August 2026 (Seo et al.) gives in its fixed-point model the formal reason for the design I had reached
    empirically over three cycles (R530's balanced book): the common component tracks live index futures; the
    idiosyncratic part is network noise that the reopen removes.
  - It also names a mechanism the lab had not mapped, the oracle network echo. OKX's index imports Hyperliquid's
    oracle at a weight of 0.343, so damped venues should lag xyz over a weekend and snap at the open.
  - Reading it took about 40 minutes. Designing without it took three cycles.
- **What I will do differently:**
  - When a family becomes a candidate for money or for a lane, read the field's best recent paper on its mechanism in
    full before designing, not after freezing.
- **Promoted:** this is the second time (L038: read the theory of the market before reasoning alone). Step 0 of the
  one-page approach in `CLAUDE.md` now adds "what the field knows: the best paper on the mechanism, read in full
  before designing anything".

## L048 · 2026-11-25 · Write the decision before the result, and the money before the decision
- **What surprised me:**
  - Writing the arithmetic of the first stake before any read changed what the stake is. At the autumn level,
    halved, levered 1.5x, net of venue risk, tax and euro cash, €2,000 earns about €65 a year. The first stake is a
    calibration of fills, funding and paperwork, not an income.
  - With the decision table fixed now, a December pass cannot be read as more than it is. A fast funding-only pass on
    Deribit or Bitfinex triggers nothing, because their 2026 net was about zero.
  - **The pre-listing class:** the mechanism fired exactly as designed. Anthropic's Lighter/xyz spread of −1.4%
    closed on its 2026-11-19 listing. But the size was small, and Oura's venues sat within ±0.1%: cross-venue
    capital is already there.
  - The lab's own recorder answered that in minutes. Step 0's "data no question has used" paid at once.
- **What I will do differently:**
  - Before any read that can move money, write the outcome-to-action table and the money arithmetic, dated.
  - For a rule-forced convergence, measure today's spread first. It shows how much capital already crosses the
    barrier, and so the size of what is left.
- **Instruction changed:** none.

## L047 · 2026-11-25 · Check a risk rule on what the account actually holds
- **What surprised me:**
  - The feared risk was real but smaller than I expected. The Kraken account of the sign-agnostic book is 46% short.
  - Its largest single moves are up-spikes on short legs (ACE +88% in a day).
  - But on Kraken's own mark the account lost at most 4.4% of notional in a day (upper bound 12.6%), against 59% of
    room at 1.5x.
  - The risk that binds is the account's net long/short imbalance in a market-wide move: a 2025-10-10 crash on the
    most long-heavy day costs about 26%. A long-alt account loses the full move.
  - The rule survives. The way it was argued (for a long-only account) was wrong, and only luck made it
    conservative.
- **What I will do differently:**
  - Describe a book's risk from its daily positions (net share, number of legs, the largest leg) before reusing a
    rule argued for another composition.
- **Promoted:** this is the second time (L043: describe a book by what it earns, not by the story that found it).
  `CLAUDE.md`'s habits gain "describe a book by what it holds and earns, measured".

## L046 · 2026-11-25 · Self-review 3: my first estimates are optimistic every time
- **What surprised me** ([self_review_20261125.md](reviews/self_review_20261125.md)):
  - Under rule 11, five of nine cycles changed the money plan. The changes came from deep reads of the lab's own
    data and of venue rules, not from new tests (none were run).
  - **Every first Fermi size I gave the owner was cut by 2 to 10 times within two days:** Kraken sleeve, weekend
    fade, the "sell-off" claim.
  - Each first estimate used the measurement just made, and left out the binding constraint and the decay.
  - **Half of R508's trades are short Kraken and earned 63% of the funding,** yet the stake's leverage rule was
    argued for long Kraken accounts only.
- **What I will do differently:**
  - The first Fermi size names the binding constraint and the decay. That is now step 4 of the one-page approach in
    `CLAUDE.md` (promoted).
  - Claims made to the owner go in a scoreboard that each self-review updates.
  - Next cycle: check the stake rule for short Kraken legs (up-spikes) before anything else.
- **Instruction changed:** `CLAUDE.md` step 4 of "How I approach a subject" (capacity = min(market, owner under the
  margin rule), net of decay). Flagged, not pruned: "the sign comes from the design".
- **Method reading** (Bailey et al. 2014, read in full): no change. The lab already counts trials and halves
  in-sample edges.

## L045 · 2026-11-25 · Ask whether a class can grow before searching for its next member
- **What surprised me:**
  - Cycle 8 said the product is a pipeline of new design gaps. A census of the funding rules of seven new perp venues
    (their own docs) found none without the floor.
  - Drift even raised its floor to the standard 10.95% in 2026.
  - Floorless designs survive only at legacy venues (Kraken, Deribit, Bitfinex, dYdX cross).
  - My reading of why: the floor subsidizes the liquidity providers a new venue needs. So the class has a fixed
    membership, and its rent decays with no replacement.
  - The new rents are where demand is new: 24/7 equities, pre-listing perps, outcome markets. That is not where an
    old rule is copied.
- **What I will do differently:**
  - When a lesson says "find more like this", first ask who sets the rule that makes it pay, and whether anyone has a
    reason to set it again.
  - If not, the search goes to where demand is growing faster than arbitrage capital, not to more copies of the
    rule.
- **Instruction changed:** none in `CLAUDE.md`. The approach page gains the line.

## L044 · 2026-11-25 · Test a conclusion on the longest series before telling the owner
- **What surprised me:**
  - Cycle 7 told the owner the carry sleeve "pays most in sell-offs", from R508's single year.
  - One cycle later, R525's 5.7-year, 12-pair panel said the opposite: the family pays after BTC rallies (past
    120-day return t +4.9) and in volatile months.
  - It also decays about 30% of its mean level a year (regime-adjusted t −5.2). Every long pair is negative. Outside
    Kraken it earns nothing in 2026.
  - The data for the right answer sat in the lab's own results folder the whole time. My step 0 was applied to
    "which rounds touched this", not to "which is the longest series that can test this claim".
- **What I will do differently:**
  - Before a claim about when or why an edge pays leaves the lab, check it on the longest panel the lab holds, with
    the regime measured rather than matched by eye.
  - Write dated forecasts for the coming reads, so the self-review can score my calibration rather than my
    stories.
- **Instruction changed:** none. Step 0 of the one-page approach already asks what the lab knows. This adds "the
  longest series that can test the claim" to how I read it. If a one-window claim misleads again, it goes into the
  step's text.

## L043 · 2026-11-25 · Decompose a book by what it actually earns, not by the story that found it
- **What surprised me:**
  - I asked why the design gap's return fell through 2026 and predicted the floorless side was being arbitraged.
  - The decomposition showed something else. In the winter sell-off, Hyperliquid's alt funding sat below its own
    floor, so the design-signed gap was negative in four of five months.
  - R508 earned anyway, because R275's rule is sign-agnostic: it harvests cross-venue dispersion. Its monthly return
    follows the realized top-20 dispersion (same-month corr 0.91).
  - The dispersion fell about threefold, and about twofold at a matched sell-off month a year apart.
  - For three cycles I had described this book by the mechanism that led to it (the floor). What it earns is a
    broader, regime-driven dispersion.
  - The forward edge at the autumn level is thin after tax and cash (about +2.5%/yr at 1x). My earlier €3-8k a year
    used the whole year.
- **What I will do differently:**
  - Before sizing or forecasting a book, decompose its return by the quantity it actually harvests, measured month
    by month, and compare it with the story that found it.
  - Name the state variable (here, live dispersion) to watch.
  - A mechanism explains why an edge exists. It does not say how much of the PnL comes from it.
- **Instruction changed:** none. López de Prado's line in `CLAUDE.md` ("decompose by source, coin, venue, regime
  before another backtest") already says it. This is the first time I ran it on the money case, and it changed the
  money plan.

## L042 · 2026-11-25 · Capacity is the smaller of the market's and the owner's
- **What surprised me:**
  - I froze R530 (the balanced weekend fade) and then read the venue's margin rule. 58 of its 72 markets are
    isolated-only, so a market-neutral book gets no margin relief.
  - At the owner's €10k stage the useful size is about $1k a trade, worth about $2k a year at half the edge. Cycle 4's
    $5-7k a year assumed the book's depth was the limit. It is not, until about $50k of capital.
  - I had sized the family by the measurement I had just made, not by the constraint that binds.
  - Also: before the freeze, the lane's code reproduced the seen numbers exactly, and a live plumbing run on a seen
    weekend matched them to the basis point. Doing both is what lets me trust the forward journal.
- **What I will do differently:**
  - A Fermi size names two capacities: the market's (depth, supply) and the owner's (capital under the venue's
    margin regime). The smaller one is the size.
  - Read the margin mode of every market a lane trades before sizing it.
- **Instruction changed:** none. Step 4 of the one-page approach already says "a Fermi size and the capacity".
  This is how to read it. If it recurs, "capacity = min(market, owner under the margin rule)" goes into `CLAUDE.md`.

## L041 · 2026-11-25 · Derive the design from the mechanism of the noise, then let the mechanism be refuted
- **What surprised me:**
  - Asking where the weekend noise comes from did more than any new signal. The common weekend move does not
    reverse (R464), so a book with equal notional long and short drops it.
  - On R462's own weekends the balanced book's SD per weekend fell to 34-56% of the raw book's, with a higher mean.
    Power at half the edge went from 32% to 92%.
  - The theory was already written (Nagel 2012). The textbook reversal book is exactly this: market-adjusted,
    $1 long and $1 short, beta-hedged.
  - **My second prediction failed.** I fixed the set of crypto-proxy names before computing and predicted they fade
    less, because they are hedgeable. In sample A they faded more. Writing the falsification criterion first kept me
    from explaining it away. Part of the refined mechanism is not supported.
  - **The baseline reproduced first** (B exactly; A within one weekend), and that is why the variation can be
    trusted.
- **What I will do differently:**
  - Before designing a test, decompose the noise by its mechanism (which part is common, which part is paid) and
    build the book that keeps only the paid part.
  - State every refinement's prediction with its failure criterion before computing, and record a failed one as
    plainly as a confirmed one.
  - Pólya's "Have you seen it before?" and "Did you use all the data?" are the same lesson as L040, heard a second
    time.
- **Instruction changed: promoted.** `CLAUDE.md`'s one-page approach gains step 0: what the lab already knows, and
  the recorded data no question has used yet (Pólya; L040).

## L040 · 2026-11-24 · The lab's own record is the first primary source of the mechanism map
- **What surprised me:**
  - To leave the design-gap family (three cycles in a row), I went looking for a "new" class: 24/7 stock perps while
    the stock market is closed. The registry already held eleven rounds on it and two forward lanes. My three-cycle
    map had marked the row "not mapped".
  - **Read by mechanism, those rounds tell one story.** Single-name weekend moves overshoot where market makers cannot
    hedge: R462, R465, and R468 in sample A. Index perps, which are hedgeable and quoted everywhere, do not (R464, R432).
    So R464 was the mechanism's control, not the failed replication that L009 had counted.
  - **The venue's changelog shows it moving the transfer on purpose.** The oracle constant went from 8 hours to
    30 minutes, which removed the funding that had paid faders (by the venue's own figure, a trader right on a gap
    move now keeps 87% of it, against 10% before).
  - **The decisive number was capacity, and it was cheap:** the recorded books.
    - The entry hour has the week's thinnest book.
    - About $5k a trade is the useful size: about $7k a year at half the edge, $23k at full.
    - R463 is likely underpowered if the edge is only half its in-sample size.
- **What I will do differently:**
  - Read the lab's past as evidence about mechanisms, not as a list of verdicts.
  - Start every map row from the registry, then go to the venue's rules.
  - Classify a family by what forces the transfer, not by the test's name.
  - When a refined mechanism is written after a failure, name its new prediction and test it only on fresh data.
- **Instruction changed:** none in `CLAUDE.md`. The approach page gains section 4c, the "solve the class" step
  applied to the lab's own history.

## L039 · 2026-11-24 · Turn a paper's lens on my own book before hunting a new strategy
- **What surprised me:**
  - The paper's decomposition (returns come mostly from price convergence) did more for us than its headline.
  - Turned on our book, it shows the price legs are not noise. The entry price gap closes with a slope of about −1
    (Kraken −1.25, Deribit −1.19, Bitfinex −1.06), so we lose it whenever we buy the dearer perp.
  - Meanwhile the new strategy I had planned (Kraken spot-perp convergence) died on arithmetic: Kraken's retail spot
    fees.
- **What I will do differently:**
  - After reading a paper, ask first what it says about the edge I already have, and only then what new strategy it
    suggests.
  - Do the fee arithmetic for the owner's actual venue before counting supply on a venue they cannot use.
- **Measured the same cycle on executable prices:**
  - the slope is still −0.86, but the gaps are small (0.21%), so the gain is about +1%/yr, not +6%;
  - the engine's last-trade valuation showed price losses that executable prices do not.
  - The first, larger number was mostly the stale-price artifact I had named as the weak point. Naming the weak link
    before trusting a number is what caught it.
- **Instruction changed:** none.

## L038 · 2026-11-24 · Read the theory of the market before reasoning alone
- **What surprised me:**
  - A paper I had listed in the intake on 2026-11-20 and never read (He, Manela, Ross & von Wachter) answers in its
    first 37 pages what my own reasoning had half-found. Funding above cash is the price of leverage, bounded by
    arbitrage capacity W/m. With unlimited capacity every venue's funding equals the cash rate, so our design gap is
    a limits-of-arbitrage rent, protected by the absence of cross-venue netting and decaying as capital grows.
  - It also showed that the lab's premium tests used the wrong target (premium = 0). The clamp-correct one is about
    −0.046% per 8 h, and on our data the supply for that trade is still large in 2025-26.
- **What I will do differently:**
  - Before reasoning about a market from scratch, read its best theory paper in full. The intake list is a reading
    queue, not a catalogue.
  - Search for capacity rents with the three measurable conditions: demand θ, capacity W/m, our access.
- **Instruction changed:** none. Rule 6 (read in depth) already says it; this is the first time I applied it to the
  core market.

## L037 · 2026-11-24 · My questions were mine to answer
- **The owner.** "Toutes tes questions, réponds-les toi-même… même pour lire les arXiv etc., fais-le en profondeur."
- **What surprised me** when I answered them myself from primary sources
  ([answers_20261124.md](reviews/answers_20261124.md)):
  - **Kraken EU's maintenance for our coins is 5%** (EEA margin schedule, Class E, Level I). I had asked the owner for
    it twice. It sets the Kraken lane at 1.5x.
  - **Gains are taxed under art. 150 ter CGI** (BOFiP 70-10 and 70-20) on the year's net across contracts: about 31.4%
    in 2026, with losses carried ten years.
  - **The owner's hurdle is euro cash after tax (about 1.5%), not the US bill (4.13%).** Dollar collateral is a
    currency position that I had never counted.
  - "Breakthrough" became a number I can steer by: €10,000 a year of after-tax excess, made of several capacity rents.
- **What I will do differently:**
  - I do not ask the owner anything I can find or decide. I research it, decide, write what I assumed, and leave only
    the acts that are legally theirs.
  - A paper that bears on the work is read in full.
- **Instruction changed:** `CLAUDE.md`:
  - the owner's quote;
  - rule 6 (read in depth, no page cap);
  - rule 12 (answer my own questions);
  - chain step 3.

## L036 · 2026-11-24 · Rule first, then the data the rule names (first reflection cycle)
- **What surprised me:**
  - Asking "on which price does each venue liquidate?" before measuring changed the answer:
    - Kraken liquidates on a spot-index mark, which fell −44% on 2025-10-10;
    - Binance's prints fell −65% to −69%.
  - The reflection also split the design gap in two:
    - a risk premium on liquid pairs, which is why funds leave it;
    - a capacity rent on thin coins, which is where a small account has an edge.
  - The clamp band in the floor formula explains why the gap persists: arbitrage cannot move the floor.
- **What I will do differently:**
  - Read the rule that produces a number (formula, liquidation price, margin schedule) before choosing the data.
  - Look for the next edges as capacity rents behind thin books, not as published anomalies.
- **The way of thinking changed:** measure → mechanism → measure the right thing. Recorded in
  `docs/reviews/mechanism_map.md`, the living map.
- **Instruction changed:** none. The approach section of `CLAUDE.md` already says it; this cycle is the first time I
  followed it.

## L035 · 2026-11-24 · The owner: I work too much and reflect too little
- **The owner.** "Tu travailles trop et tu réfléchis peu sur toi-même… c'est ça qui nous sépare terriblement des
  breakthroughs… tu dois passer le plus clair de ton temps à faire ça."
- **What I see when I look:**
  - The only breakthrough came from understanding a rule (funding formulas) and comparing it across venues.
  - My loop rewarded two-hour increments, so I chose tools, notes and cheap tests.
  - My self-improvement added rules after each mistake. It did not change how I think.
  - The wide cycles tested other people's published ideas instead of mechanisms we uniquely see.
- **What I will do differently** ([approach_20261124.md](reviews/approach_20261124.md)):
  - Most of each cycle is written reflection: the one-page approach (question, mechanism, barrier, Fermi size, our
    edge, cheapest decisive observation).
  - The map of venue design mechanisms, filled from primary sources.
  - A review of how I approached the last subject.
  - A test only when the reflection names it.
- **Instruction changed:** `CLAUDE.md`:
  - the owner's quote;
  - a new section "How I approach a subject" at the top;
  - rule 11 (reflect more than I produce);
  - rules 1 and 9 amended (a reflection is the default increment);
  - chain step 2 is now "Think".

## L034 · 2026-11-24 · The resolution of the data is part of the risk model
- **What surprised me** (self-review 2, then its first unasked item):
  - Five cycles of margin work (ticket, Kelly, two accounts) used daily closes and found no liquidation at 1.5-2x.
  - Binance's hourly bars show basket drops within a day of −44% (2021-05-19). Each coin's hourly low fell about −65%
    on 2025-10-10. A 1.5-2x long-alt account would not have survived that.
  - Money-station work changed a money decision in 5 of 5 cycles. Wide pattern tests paid 0 of 2.
- **What I will do differently:**
  - A risk number names its data resolution. Before it sets leverage, it is checked at the finest resolution the lab
    holds, and against the venue's own liquidation price when known.
  - Self-reviews choose the next work by measured yield (money station first while a stake is near).
- **Instruction changed:** none yet. If a coarse-resolution risk number misleads again, "name the resolution" joins
  the "Say what was not checked" habit in `CLAUDE.md`.

## L033 · 2026-11-24 · Ten minutes on the venue's own API before a lane
- **What surprised me:**
  - My notes called dYdX a possible fourth floorless venue. The venue's indexer says three things:
    - cross markets are floorless, but premium-driven (their funding ran above Binance's in 2024-25);
    - isolated markets (180 of 296) carry a 10.95%/yr floor;
    - the whole venue trades $42M a day.
  - The queued test (M469) would have spent a registered round on a venue with no capacity.
- **What I will do differently:**
  - Before a lane on a venue, pull its own market list. Check the design field (here `defaultFundingRate1H`), the
    24 h volume per market, and the sign of the funding gap by year.
  - The design is a necessary condition. The gap and the volume decide.
- **Second occurrence?** Close to L026 (an API field read wrongly), but the other way round: here the venue's field
  corrected my notes. The shared lesson is to read the venue's own data before believing a summary. If it recurs, it
  joins the "Data I need" habit in `CLAUDE.md`.
- **Instruction changed:** none.

## L032 · 2026-11-24 · A public payer is paid first by someone else; the first forecast, scored
- **What surprised me** (R529, NULL):
  - Index funds must roll on announced dates, and CFTC economists see the spread move with their holdings. Yet a
    trader starting at the last month-end and holding to the 9th day earned about 3 bp gross a month, nothing, in
    2010-2026.
  - The forecast written before the freeze said 15%. The outcome is a miss, consistent with it. One forecast scores
    nothing alone; the self-review will score them together.
- **What I will do differently:**
  - Ask a second question after "who pays": can anyone with cheaper capital be paid first?
  - A public calendar, one exchange and spread margining mean yes: arbitrage capital is there before me.
  - The design gap pays because each leg needs its own margin on venues institutions avoid. Look for payers behind
    that kind of friction (separate margins, venue access, mandates that forbid the arbitrageur).
- **Instruction changed:** none yet. If this recurs, add the second question to the "Who pays" lens.

## L031 · 2026-11-24 · The outside view, measured: payers pass, patterns do not
- **Read:** Ioannidis (2005), pp. 1-3, in place of Tetlock (his page is behind a Cloudflare challenge; no
  workaround).
- **What surprised me** (`scripts/base_rates.py` on 244 FINDINGS):
  - Families with a structural payer pass most of their decided tests: carry 64%, settle 43%.
  - Charts, options, micro, portfolio and vaults have never passed one.
  - My wide cycle (R528, calendar family) went where past passes had not survived. An honest forecast would have
    been about 5-10%. I did not write one.
- **What I will do differently:**
  - Every PREREG writes a forecast (the family's share, the prior, the power, P(PASS)).
  - Under about 10%, I write why the test is still worth a cycle.
  - Self-reviews score the forecasts.
- **"Wide" should mean new payers, not new patterns.** Rule 7 (wide, not stuck) is best served by looking for
  structural payers in other markets, the families with a measured yield.
- **Instruction changed:** `CLAUDE.md` step 4 (forecast before the freeze) and "Principles from the masters"
  (Ioannidis); the PREREG template gains a "Forecast" section.

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
- **Result, the same cycle:** R528 FAIL (NULL). The sign of the day's move does not predict ES's last hour (sign
  correlation 0.003 and 0.033). The return correlation (0.08-0.11) comes from large-move days, and halved after 2018.
  Regression evidence in a paper (an R²) is not a tradable sign rule; check that before buying data.
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
