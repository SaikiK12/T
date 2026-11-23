# Where a breakthrough can come from: a step back over every axis, 2026-11-21

The owner: "We need a breakthrough… don't just keep working, reflect really deeply on all axes." This page is that
reflection. It runs a test of nothing. It sets the order of work until the first forward reads, and each lane's
PREREG and FINDINGS stay the authority for its own numbers.

## 1. What 9.8 million trials say
- **Patterns do not survive.** Price patterns, indicators, flows, sessions and ML rankers pass in sample and fail
  their confirmations:
  - R192→R201, R462→R464, R188→R189;
  - R299/R304 leaked;
  - R263 decayed to nothing.
  - At this many trials, a new pattern has to clear about t 4 to mean anything, and almost none do twice.
- **One family replicates: a structural payer.**
  - The funding-design gap, a floorless venue against one whose longs pay a 0.01%/8 h floor, passed on four pairs
    and on unseen coins:
    - Binance+Bitfinex (R507);
    - Kraken+Hyperliquid (R508);
    - Kraken+Aster (R511);
    - Deribit+Hyperliquid (R519's reported book: +4.5%/yr unlevered, NW t 7.0, every year 2023-26).
  - The payer is known: leveraged longs on the floor venue pay by design. Arbitrage capital is limited because each
    leg needs its own margin.
- **Everything decays in time:**
  - single-venue carry turned negative in 2025 (Borri et al., checked);
  - R507's last two years are half its first four;
  - R508's monthly return fell from 4.5% (January) to 0.9% (October);
  - R516's listing events dried up.
- **The market now.** BTC is near $58k (dYdX oracle, 2026-11-21) from near $80k a month earlier (Deribit's index,
  2026-10-26). Leverage demand, and with it the premium part of funding, is falling. The floor part is a design and
  does not fall.

## 2. What a small French retail account can and cannot win
- **Advantages:**
  - **Capacity niches:** an edge worth $50k a year to us is noise to a fund (R508's thin Kraken coins).
  - **Venues institutions avoid:** wallet-only DEXes such as Hyperliquid, Aster and Lighter.
  - **Patience:** no redemptions, so a hedged book can be held through drawdowns.
  - **Incentive programs:** they pay small accounts too.
- **Disadvantages:**
  - no speed (anything sub-second is lost);
  - no private information;
  - regulated leverage of 2:1 on EU venues (ESMA);
  - venue risk: a 30% one-year closure rate in the old Moore-Christin sample.
- **Arithmetic.** $2,000 at even 45%/yr is $900 a year. A breakthrough in money means a proven high-Sharpe book that
  can take leverage and more capital. A clever idea alone is not one.

## 3. The insight: the breakthrough is leverage on a high-Sharpe structural edge, then scale
- **Deribit+Hyperliquid's in-sample book** earns about 4.5%/yr unlevered on two-leg capital, at an annual Sharpe
  ratio of about 3.7 (daily 0.20).
  - Its risk is not market direction. It is operational: one leg's margin on one venue, and venue failure.
- **On liquid coins** (BTC, ETH, SOL, DOGE, LTC…), 3x on cross margin with daily rebalancing between venues is about
  13%/yr. Hyperliquid's portfolio-margin yield on idle USDC (2.65%/yr live, above a $10k account) adds to it.
  - It needs a margin buffer and alerts. Deribit and Kraken liquidate without warning.
- **Capacity:** millions, not thousands.
- **R508's thin-coin version** earns more per dollar (in sample) but cannot take leverage (spikes of 50-100%) or
  size.
- **The two together:** a small high-yield sleeve on thin coins, and a large levered sleeve on liquid coins. That is
  a "stable PnL" that real money can match. It is the realistic breakthrough, if the forward reads confirm.

## 4. Three bets, ranked by expected value per unit of work
### Bet 1: prove the design gap fast, then lever it (in progress; accelerate)
- **Running:**
  - R509/R510/R512 on Kraken/Hyperliquid/Aster;
  - R514, passive Kraken costs;
  - R520 on Deribit+Hyperliquid, from 2026-11-22.
- **Accelerate.** Its price legs are a hedge, mean about 0, and they are most of the noise. So a read on funding net
  of measured costs, with a guard on the full net, reaches significance in weeks rather than months. R510 does this
  for R509.
  - **Next lane:** the same fast read for R520 (30/45 days).
- **Prepare money now, before the read:**
  - the owner's accounts (Deribit access from France is unchecked; Kraken's written leverage answer is pending);
  - a margin monitor with alerts above each venue's liquidation line;
  - a rebalancing rule between venues;
  - `lab.gate.go_real()` with a small stake on the first PASS.
- **Kill:**
  - R510/R520's fast reads FAIL;
  - or measured costs on liquid coins exceed 2x the 7 bp test charge.

### Bet 2: turn the cost into income by making on the thin venue and hedging on the liquid one
- **Who pays:** impatient takers on thin books (Kraken's and Deribit's new perps, Aster), whose spreads are tens of bp.
  - R513 showed a resting Kraken order saves about 8 bp a side at a 1-hour fallback.
  - The full version quotes passively on the thin venue and hedges each fill at once on Hyperliquid. It keeps the
    spread and the funding gap.
  - This is what the ex-prop trader called "obscure arbitrage". It needs seconds, not microseconds.
- **Missing data:** depth and trades on the thin venue at the moment of the hedge. Kraken publishes order-level
  events (`uid`), which would allow a queue-aware simulation.
- **First step (cheap):** record books and trades on 10-20 thin perps on Kraken, Deribit's new listings and Aster,
  plus Hyperliquid, for 3-4 weeks. Then register a simulation with adverse selection measured from mark-outs.
- **Kill:** if the mark-out after a passive fill eats the half-spread on most coins.

### Bet 3: capture venue incentives with a hedged book (the asymmetric one)
- **Who pays:** new venues buying open interest and volume with tokens.
  - Hyperliquid's 2024 distribution and later DEX airdrops paid early users large sums relative to their capital.
  - A delta-neutral carry book on a points venue earns funding plus points at almost no market risk.
- **Rule** (from the lab's fake-edge checks): never count points at a hoped-for price. Measure the realized value
  per dollar of hedged capital per month from past programs: points issued, the share of supply, the price at
  launch, and the wash-trading and Sybil rules.
- **First step (reading, by me):** the official docs and public data of the past 4-6 programs, then the current
  ones. Which reachable venue pays points for open interest or maker volume now?
- **Kill:** if realized past values per capital-month are below the carry itself, or if current terms exclude
  hedged books.

## 5. What not to do
- **More pattern mining on seen data,** or more historical replications of the design gap. It is replicated; only
  forward days add information now.
- **A venue tunnel** (Kraken took three days).
- **A "breakthrough" from unverified numbers,** or anything that loosens the gates.

## 6. Order of work until the first reads (about 2026-12-20)
1. **R520's fast read:** a funding-net-of-costs read at 30/45 days, frozen before R520 has 30 scored days.
2. **Bet 3's reading:** the realized value of past points programs, and the current programs on reachable venues.
3. **Bet 2's recorder:** thin-venue books and trades for the make-and-hedge simulation.
4. **Money readiness:** a margin and liquidation monitor, a rebalancing rule, and the owner's two access answers
   (Deribit, Kraken).
5. **The first reads** (R510 around 2026-12-20, then R512, R514, R520): a stake via `go_real()` only on a PASS.

## Addendum, the same day: Bet 3 measured, and folded into Bet 2
- **Measured** (`research/intake/points_value_20261121.md`, order of magnitude): realized points value was about 3 bp
  of volume on Hyperliquid and 1 bp or less on Lighter, at launch prices.
- **For a hedged carry book,** which trades little volume, that is noise.
- **Bet 3 is now part of Bet 2.** Run the make-and-hedge book on a zero-fee venue that pays points, with points
  counted at zero in every decision.
- **Order of work:** item 2 is done; item 3 (the thin-venue book and trade recorder) is next.
- **Item 3 needs no recorder for Deribit** (checked 2026-11-21, counts and field names only):
  - `www.deribit.com`'s trade-history call serves only the last few days;
  - `history.deribit.com/api/v2/public/get_last_trades_by_instrument_and_time` serves full history, back past 90
    days on AAVE_USDC-PERPETUAL. Each trade carries `price`, `amount`, `direction`, `index_price` and `mark_price`.
  - So the make-and-hedge book can be simulated on Deribit's thin new perps from history:
    - quote at index ± k bp;
    - a fill when a trade prints through the quote;
    - hedge at the index plus Hyperliquid's cost;
    - adverse selection measured by the index's mark-out after the fill.
  - Its PREREG must write the fills per day per coin, the break-even (k against 1.5 bp maker + 4.5 bp hedge taker +
    the hedge spread) and the power before any fill is computed.
- **Item 3 read (R522, 2026-11-21): FAIL.**
  - Quoting around the index on Deribit's thin new perps lost 27 bp a fill (205,771 fills, every k from 5 to
    40 bp), because trade-through fills are adversely selected.
  - It is a lower bound: touch-level fills need book data.
  - Bet 2 drops below Bet 1. A Kraken queue reconstruction from order events is the one open way to test it, and it is
    lower priority than proving and levering the design gap.

## Addendum, 2026-11-23: the breakthrough widened (R525), and the next order of work
- **R525: PASS.** All 12 floorless × floor pairs pay after 3x costs. Their equal-weight portfolio earned +7.8%/yr
  at Sharpe 5.5 with a −0.73% max drawdown over 2021-2026, every year positive
  ([FINDINGS](../../experiments/gap_breadth_v1/FINDINGS.md)).
- **Forward evidence running:**
  - R509 and R512: Kraken + Hyperliquid (+ Aster);
  - R520: Deribit + Hyperliquid, with R521 (fast) and R523 (combined) reading it;
  - R524: Bitfinex + Binance, warm-up on GitHub done 2026-11-23, scored from 11-25.
- **Next, in order** (standing rule 1: never wait while these run):
  0. **A Millikan audit of R525** (Feynman: hunt bugs in a pleasing result as hard as in a failing one).
     - Funding timestamp conventions per venue (period start or end), and whether a decision at day d can collect
       funding settled before d.
     - Kraken's +31%/yr: split it into floor, premium extremes and price legs, and by coin liquidity.
     - A one-day decision delay as a lookahead check.
     - Reproduce R507 and R508 exactly under R525's engine before trusting the new pairs.
     - **Done 2026-11-23:**
       - the delay check (11 of 12 pairs keep 82-105%);
       - the tail, priced by R526: two entry filters remove it at no cost;
       - Kraken decomposed: funding is 113-122% of gross, price legs lose; 96% of gross is on coins under $100k a
         day; without the top 5 coins, +10-22%/yr.
       - R507 and R508 differ under the new engine for known reasons (marks and notional at entry).
  1. **Forward sleeves, one per floorless venue,** each R275's book across all held floor venues:
     - kraken + binance + gate + kucoin + hyperliquid;
     - deribit + the same four;
     - bitfinex + the same four.
     The widest pair is chosen per coin, as in R439. Each sleeve gets a new id, its own cache and the margin plan.
  2. **A combined portfolio read** over all forward sleeves, under a new id. It is calibrated for size on demeaned
     history before its freeze (L018).
  3. **Money:** the owner's accounts on the floorless venues (Kraken, Deribit, Bitfinex) and one or two floor venues;
     `lab/margin.py` sizing at about 2.5x with daily rebalancing; `go_real()` only after a PASS.
