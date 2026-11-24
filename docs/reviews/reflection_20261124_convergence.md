# Reflection, 2026-11-24 (cycle 3 of rule 11): our book is on the wrong side of a convergence trade

## How I approached the last subject, and what changed before measuring
- **The plan** from cycle 2 was to count Kraken's own spot-perp deviations (candidate 2).
- **Thinking first killed it for a small account.** At low volume Kraken Pro charges 0.25% maker and 0.40% taker on spot,
  so a round trip of both legs costs 0.54-0.9%. The Binance count assumed 0.19%. On the venue the owner can use, the
  supply collapses.
- **The paper's real lesson for us** came from its return decomposition: convergence-strategy returns come mostly from
  **price convergence**, not funding. Our design-gap book is the mirror image: funding is 113-122% of its gross, and
  its price legs lose. Why?

## 1. The economic question
Does our book lose on its price legs because it enters at a price gap that then closes against it?

## 2. The mechanism
- **Each venue's perp deviates from spot** by its own premium (ρ in He et al.). Between two venues, the gap
  log(P_long/P_short) is the difference of two deviations.
- **Arbitrage pulls the deviations back,** with random maturity, so the gap converges.
- **R275's entry rule looks only at trailing funding.** When the long venue's perp is dearer than the short venue's at
  entry, convergence costs the trade that gap.

## 3. The observation (post hoc, R525's seen trades; a diagnostic, not a test)
| Long leg's venue | Trades | Slope of price PnL on the entry gap | Price PnL, dearest-long quintile | Price PnL, cheapest-long quintile |
|---|---|---|---|---|
| Kraken | 837 | −1.25 (corr −0.38) | −2.98% | +0.32% |
| Deribit | 2,614 | −1.19 (corr −0.34) | −1.25% | +0.09% |
| Bitfinex | 3,287 | −1.06 (corr −0.12) | −2.00% | −0.26% |

- **A slope near −1 means the gap paid at entry is lost in full.**
- **What is left on the table** (Fermi estimate; it assumes entries could be timed at a non-positive gap): about +1%
  per Kraken trade, roughly +6%/yr on the Kraken pairs' capital, and about +1%/yr on Deribit's.

## 4. What could make this an artifact
- **The gap uses daily last-trade closes.** On thin coins a stale last trade "converges" when it next prints, and
  nobody could have traded at the stale price. That inflates the slope.
- **The decisive check uses executable prices:** Kraken's mark (index-anchored) and Hyperliquid's mid, from the hourly
  candles. If the slope stays near −1 on marks and mids, the effect is tradable.

## 5. What it would change
- **Entry:** prefer, or wait for, moments when the long perp is not dearer than the short one (gap ≤ 0 after the
  contract multiplier). Or rank candidates by expected funding minus the entry gap.
- **Exit:** consider closing when the gap has converged in our favour, as in He et al.'s close rule, not only on
  funding.
- **How to test it cleanly:** the R525 data is now seen for this question. The test is a new forward lane (a new id;
  R509/R520/R524 are frozen) or the reserved samples. A live execution rule is honest only after that.

## 6. How my way of thinking changed
- **The paper's decomposition table** (where its returns come from) mattered more than its headline Sharpe.
- **Turning the paper's lens on our own book** found more than looking for a new strategy did. A mechanism that pays
  someone (convergence) is first a cost we may be paying.

## 7. The decisive observation, made the same cycle (`scripts/check_exec_gap.py`)
- **Data.** R525's 103 kraken+hyperliquid trades entered from 2026-04-26, re-valued on executable prices: Kraken's
  hourly mark (index-anchored) and Hyperliquid's hourly close.

  | Entry-gap quartile (executable prices) | Mean gap | Price PnL, executable | Price PnL, engine (daily last trade) |
  |---|---|---|---|
  | 1 (long leg cheapest) | −0.41% | +0.26% | −0.28% |
  | 2 | −0.06% | +0.11% | −0.21% |
  | 3 | +0.06% | −0.04% | −0.20% |
  | 4 (long leg dearest) | +0.31% | −0.26% | −0.34% |

- **Convergence is real on executable prices:** slope −0.86, corr −0.46.
- **The gaps are small:** 0.21% at entry on average. Timing entries to a non-positive gap is worth roughly +0.2% a
  trade, about +1%/yr on the Kraken pairs' capital. That is not the +6% that daily last trades suggested.
- **A second finding.** On the same trades, the engine's daily last-trade valuation shows a price loss of −0.2% to −0.34%
  a trade in every quartile, while executable prices average about zero.
  - Part of the book's price-leg loss (funding at 113-122% of gross) may be a valuation artifact of stale last trades.
  - If so, the true book is slightly better than measured.
  - The sample is small (103 trades, five months, one pair); not yet a claim.
- **What it changes:**
  - Entries at a non-positive executable gap are a small, mechanistic improvement. They belong in the live ticket's
    checks once tested forward.
  - The bigger lesson is that backtest valuation on last trades misstates thin-coin books in both directions. A
    forward lane on executable prices (the lanes already walk the books) is the reference.
