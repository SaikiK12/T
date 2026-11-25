# Open questions that only an experiment can settle (the register; `CLAUDE.md` rule 13)

- **How it works.** Each question is refined in its source file (hypothesis and opposite, why it is not known, the
  mechanism, the data, the cheapest experiment, the kill result, the value).
- **This register keeps:**
  - the status;
  - the prediction written before the experiment;
  - the result.
- **Each cycle picks by value × probability ÷ cost.** The first 30 questions and their scoring come from the room
  (`room_20261125b/open_questions.md`, citations checked with `scripts/verify_citations.py`: 3 verified, 13 located,
  2 to review).

| Id | Question (short) | Source | Status | Prediction (written first) | Result |
|---|---|---|---|---|---|
| Q26 | Do the gap books become correlated in crash months? | room Q26 | **answered 2026-11-25** | Mean pairwise correlation in stress months about 0.35: above the full-period median, below the 0.6 that would change sizing | **0.35 on average; H1 (>0.6) not supported.** Sizing unchanged; shared-venue pairs move together |
| Q19 | Does the euro P&L of the dollar legs move with EUR/USD? | room Q19 | **answered by reasoning** | — | The exposure is on the **principal**, not the P&L. A dollar collateral moves one for one in euros, and the strategy's dollar P&L is a few % of it. Use euro collateral where accepted (Kraken); count Hyperliquid's USDC principal as currency risk |
| Q16 | Does lot rounding leave hedges more than 2% off on R509's coins at €1-5k? | room Q16 | **answered 2026-11-25** | (none written: answered the same hour) | Legs of $50 / $100 / $250: 9% / 4% / 0% of 107 coins have a hedge more than 2% off. At stake 1's about $150 a leg, about 3%, and `stake_ticket.py` already skips any hedge more than 5% off. H1 (at least 10%) not supported |
| Q20 | Do venue deposit and withdrawal halts precede 10%+ gaps? | room Q20 | open | — | — |
| Q01 | Variational's frozen weekend index: is the gap to xyz above 100 bp on at least 20% of weekends, and closed by the open? | room Q01; `room_20261125/synthesis.md` | **recording** (from 2026-11-25) | P ≈ 0.25 that its quotes stay near the frozen index | first weekend 11-28/29 |
| L1 | Does a floor venue's perp funding (about 10.95%/yr in calm markets) exceed the same coin's dated-futures or options-implied rate by more than costs, with convergence forced at expiry? | lead researcher, 2026-11-25 (cf. M170, M244: neighbours, not this pair) | open | — | — |
| O1 | SPX charm: is ES up from Thursday 16:00 to Friday 09:00 New York before 3rd-Friday SOQ expiries in 2022-26, after the paper's sample? | `reflection_20261125_greeks.md` §2; Baltussen-Terstegge-Whelan 2024 | **closed at Fermi** (2026-11-25) | If measured: at most +6 bp over other Thursday nights (square-root impact on $29-82bn of overnight ES), and t < 1. Worth under 2%/yr on notional even at the paper's 18 bp | not tested: the 2022-26 standard error (about 9 bp) cannot tell 5 bp from 0 |
| O2 | Single-stock gamma (TSLA, NVDA weekly and 0DTE call OI): is dealer gamma per 1% above 2% of the stock's daily volume, where pinning or squeezes can move the price xyz perps follow? | §2 | open: first step is a free data quote (OPRA open interest by strike), then one week's ratio | Ratio above 2% for TSLA on at least half of expiry Fridays: P ≈ 0.5 | — |
| O3a | Weekend clock: does Deribit price Saturday like a weekday? | §3 | **answered 2026-11-25** (2 snapshots + 2023-26 realized) | (none written: answered in the same step) | **No.** Implied Sat→Sun forward vol 18-21% (straddle 75-88 bp) against a mean Saturday move of 77-81 bp. Priced right; no gap after about 16 bp of cost |
| O3b | Is the Sunday 08:00 → Monday 08:00 UTC day underpriced? (one-day BTC option IV on Sunday 08:00-10:00, trade-flow IV nearest the money, against that window's realized move, 2022-26) | §3 | **data fetching** (`data/deribit_trades` BTC from 2022-01, started 2026-11-25) | Written before the data: the mean Sunday straddle premium is at least 90% of the mean Sunday move, so no underpricing beyond costs. P(underpriced by more than 16 bp) ≈ 0.2. Weekday one-day VRP positive (implied above realized) on at least 4 of 5 weekdays; Saturday within ±10% | — |
| O4 | Crypto vanna (M310): does an IV fall after FOMC push perps up? | §4 | **closed at Fermi** | Null: R292's dealer book is 0.13% of perp volume per 1% move, and its vanna scales with it | not tested |
| O5 | Vomma: does DVOL's own variance forecast realized vol beyond HAR? | room Q10 | open, low priority (a sizing input, not a payer) | — | — |
| O6 | Mix: do single stocks pinned at a strike on Friday move away from it on xyz over the weekend? | §4 | idea; waits for O2's ratio | — | — |

## Results
### Q26 (2026-11-25; R525's seen daily nets at 1x, `experiments/gap_breadth_v1/results/pair_daily_net_1x.csv`)
- **Full period:** mean pairwise correlation 0.20, median 0.04, over 66 pairs.

| Stress month | Live pairs | Mean pairwise correlation | Equal-weight portfolio that month |
|---|---|---|---|
| 2021-05 (crash of 05-19) | 3 (all Bitfinex) | 0.92 | +1.45% |
| 2022-05 (LUNA) | 6 | 0.05 | −0.10% |
| 2022-11 (FTX) | 6 | 0.24 | +0.77% |
| 2024-08 (08-05) | 8 | 0.42 | +0.21% |
| 2025-10 (10-10) | 8 | 0.11 | −0.20% |
| any month | — | median 0.24, 90th percentile 0.65 | median +0.45% |

- **Stress months average 0.35. The prediction held, and H1 (above 0.6) is not supported.** The portfolio did not lose
  more than 0.2% in any of these months.
- **The 0.92 of 2021-05 is three pairs sharing one floorless venue (Bitfinex).** The risk that binds is a shared
  venue, not a shared crash.
  - This agrees with the framework note's caveat, and with the stake rule's 50% venue cap proposed by the room.
- **Limits:**
  - in-sample nets on R525's engine, with last-trade valuation;
  - daily, not intraday;
  - five events.

### Q16 (2026-11-25; Kraken and Hyperliquid instrument lists, live; Hyperliquid mids)
- 107 of R508/R509's coins have both lot rules. Each leg is rounded down to its venue's step at the same dollar size.

  | Leg size | Coins more than 2% off | Worst |
  |---|---|---|
  | $50 | 10 (9%) | XMR 7.2% |
  | $100 | 4 (4%) | BTC 3.6% |
  | $250 | 0 | — |

- **Limit:** the 1000x-unit coins (PEPE, BONK) use one mid for both venues, so their flags may be a unit artifact.
  The ticket handles units per venue.

