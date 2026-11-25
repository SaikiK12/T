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
| Q19 | Does the euro P&L of the dollar legs move with EUR/USD? | room Q19 | open | — | — |
| Q16 | Does lot rounding leave hedges more than 2% off on R509's coins at €1-5k? | room Q16 | open | — | — |
| Q20 | Do venue deposit and withdrawal halts precede 10%+ gaps? | room Q20 | open | — | — |
| Q01 | Variational's frozen weekend index: is the gap to xyz above 100 bp on at least 20% of weekends, and closed by the open? | room Q01; `room_20261125/synthesis.md` | **recording** (from 2026-11-25) | P ≈ 0.25 that its quotes stay near the frozen index | first weekend 11-28/29 |
| L1 | Does a floor venue's perp funding (about 10.95%/yr in calm markets) exceed the same coin's dated-futures or options-implied rate by more than costs, with convergence forced at expiry? | lead researcher, 2026-11-25 (cf. M170, M244: neighbours, not this pair) | open | — | — |
| O* | Options: vanna, charm, vomma and their mixes | `room_20261125b/options_*.md` | room working | — | — |

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

