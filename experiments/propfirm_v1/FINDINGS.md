# FINDINGS: propfirm_v1 (R202), the lab's streams inside prop-firm rules

**Answer (descriptive): if top-vs-crowd keeps its holdout behaviour, a crypto prop challenge is a far better use of a
few hundred dollars than the same edge on own capital; the flow book fits less well; zero-edge trading looks positive
only in this optimistic model, which real pass and payout rates contradict.** None of this makes a stream real: the
flow book is NOT CONFIRMED (R198) and top-vs-crowd alone was reported, not decided. The forward test (R200) decides.

- **Registry row:** R202 (trials: 0 new return hypotheses; best-of-10 sizes per pair is optimistic)
- **Reproduce:** prereg sha d4314f64; `python scripts/run_propfirm.py` (4,000 runs, 5-day blocks, 365-day evaluation,
  180 funded days, seed 0). Tables: `results/best.csv`, `results/grid.csv`, `results/own_capital.csv`.

## Best size per stream and firm (100k accounts; payout = expected USD to the trader per attempt over 180 funded days)
| stream | firm | size | pass | paid | days to pass | expected payout |
|---|---|---|---|---|---|---|
| top_vs_crowd, holdout | FTMO 2-step | 0.75 | 88% | 85% | 81 | 18,828 |
| top_vs_crowd, holdout | HyroTrader 2-step | 0.5 | 95% | 94% | 136 | 14,662 |
| top_vs_crowd, holdout | CFT 2-phase | 0.75 | 88% | 85% | 69 | 19,072 |
| top_vs_crowd, holdout | Breakout Pro | 0.5 | 86% | 80% | 96 | 11,353 |
| flow book A, holdout | FTMO 2-step | 0.2 | 67% | 62% | 175 | 6,264 |
| flow book A, holdout | HyroTrader 1-step | 0.15 | 67% | 62% | 141 | 4,640 |
| flow book A, top-10 hedge | CFT 2-phase | 0.2 | 56% | 47% | 64 | 7,194 |
| flow book A, in-sample | FTMO 2-step | 0.75 | 68% | 62% | | 9,327 |
| zero edge (flow A demeaned) | FTMO 2-step | 0.3 | 28% | 21% | 93 | 1,863 |
| zero edge (top_vs_crowd demeaned) | FTMO 2-step | 0.75 | 32% | 25% | 107 | 2,153 |
| zero edge | Topstep 50K (CME benchmark) | 0.75 | 31% | 16% | 18 | 551 |

FTMO's fee (EUR 540, about USD 620, refunded with the first payout) is the only crypto-relevant price captured; HyroTrader
starts from USD 59 for small accounts. Break-even fees are in `results/best.csv`.

**Sizing matters more than the firm**: for top_vs_crowd under FTMO 2-step the pass rate goes 15% (size 0.1), 81%
(0.2), 96% (0.5), 88% (0.75), 61% (1.0), 33% (2.0); payouts peak at 0.75. Too small never reaches the target within the
year; too large breaks the 10% drawdown.

## Own capital, same streams
| stream | per year | Sharpe | max DD | size for a 10% max DD | per year at that size | that size / Kelly |
|---|---|---|---|---|---|---|
| top_vs_crowd, holdout | +71% | 2.49 | 16% | 0.63 | +45% | 0.07 |
| flow book A, holdout | +83% | 1.05 | 47% | 0.21 | +18% | 0.16 |
| flow book A, in-sample | +43% | 1.54 | 27% | 0.37 | +16% | 0.07 |
| carry, in-sample | +10% | 5.44 | 0.8% | | | |

USD 10,000 of own capital at a 10% drawdown budget earns about USD 4,500 a year on top_vs_crowd (if it holds); one
challenge at a few hundred dollars puts about USD 15,000-19,000 of expected payouts on the table over the same months.
The challenge is a cheap option on the edge; own capital is the expensive way to hold it.

## Reading the zero-edge rows
The rules alone are worth USD 900-2,400 per attempt at the best size in this model, more than most fees. Real buyers
do far worse (FPFX: 7% of accounts paid, mean payout about 4% of plan; Topstep: 16.8% pass), so this model is
optimistic: daily data hide intraday excursions (the daily loss rules bind harder intraday), firms add payout rules,
caps, consistency in the funded stage and discretion, and real traders do not size optimally or trade a stationary
stream. Read the absolute USD as upper bounds and the ranking (top_vs_crowd > flow book > zero edge) as the result.

## Feasibility
- The books short 6-20 alt perps against a basket. That needs a crypto prop firm on exchange perps (HyroTrader on
  Bybit/BloFin with 700+ USDT perps; Crypto Fund Trader; Breakout on Kraken). FTMO's crypto list is short (CFDs), so
  the cross-sectional book does not fit there; the FTMO rows are a rule-set benchmark.
- Carry cannot be run in a prop account (it needs the spot leg), and its edge is about 1%/yr since 2025 anyway.
- Spot: long-only. None of the lab's surviving leads is long-only (the directional atlas edges are long-alt beta;
  maker/pack lost money hedged), so spot has no candidate today.

## Cost sensitivity
The input streams are at 1x costs. At 2x the flow book's holdout mean drops from +83% to +62%/yr and at 3x to +41%
(R198); the prop results scale down accordingly. Not re-simulated here.

## What this does not show
That any stream is real; intraday drawdown paths; firm discretion and payout caps; execution on a firm's demo feed.

## Next
Let the forward test (R200) run. If book B (top_vs_crowd) passes at its 90-day checkpoint, the cheapest real-world
step is one small crypto prop challenge sized from `results/grid.csv`, placed by the owner.
