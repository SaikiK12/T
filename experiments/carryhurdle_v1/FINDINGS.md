# FINDINGS: carryhurdle_v1 (R483)

**Verdict: PASS by the frozen rule (registry: DONE, CONFIRMED).** Three of the six forward carry books beat holding
sUSDe at 2x costs with NW t >= 2, and none loses:
- R279 A gate+kucoin +12.80 points a year over sUSDe (t 4.45);
- R278 C gate+mexc +10.03 (t 3.29);
- R279 B binance+kucoin +7.54 (t 3.74).

The other three tie:
- R278 A gate+hyperliquid -0.45 (t -0.35);
- R278 B binance+mexc -0.07 (t -0.05);
- R390 A binance+gate +8.91 (t 1.11). Its sd is high: 78% of its sum over the window comes from its 10 best days.

**What it means for the best-PnL objective.** sUSDe paid 8.81%/yr over 2024-02-17..2026-09-30 and 4.72%/yr from
2025-04-09, by DefiLlama's spot rate. On this backtest R278 A (gate+hyperliquid) and R278 B (binance+mexc) earned about
what the passive token earned. Running them added no measurable value over holding sUSDe, with different
risks. The KuCoin books and gate+mexc are the carry books that cleared the passive hurdle. This is gate 0 on seen
carry rows: only the benchmark side is new, and the forward lanes still decide each book.

## Read
- **Order:**
  - PREREG frozen and registry row R483 appended in `eb328f3f`.
  - Then the sealed bodies were imported (`e16ed783`; `.gitattributes` fix in the next commit so the CRLF headers
    stay byte-exact against `raw/import_receipt.json`).
  - Then one run on 2026-11-13 00:07 UTC with `scripts/run_carryhurdle.py` (exit 0, under 1 s). PREREG 6f0c4369 and
    its 8 inputs matched; the three bodies matched the sealed sha256 and the import receipt.
  - The freeze commit precedes the data-import commit. The #7 CLAIM was not posted before the run: this agent cannot
    post on #7; the orchestrator posts the CLAIM/FYI.
- **Deviation (stated in the PREREG):** DefiLlama's free `/chart` endpoint stopped on 2026-11-13, so the benchmark
  came from bodies fetched once at 2026-11-12T23:41:27Z and sealed unread, not from a live fetch.
- **Outputs:** `results/table.csv` (648 cells: 9 books x 2 engines x 3 costs x 4 benchmarks x 3 windows),
  `results/summary.json`, `run.log`. No benchmark day was missing (0 dropped days in every cell).

## Deciders (engine v2, costs 7/14/21 bp per leg, full window, excess in points a year, NW t in brackets)
| Book | Forward | Days | sUSDe 1x | sUSDe 2x | sUSDe 3x | Aave USDC 1x | Aave USDC 2x | Aave USDC 3x | Bill 2x | Call (sUSDe 2x) |
|---|---|---|---|---|---|---|---|---|---|---|
| gate+hyperliquid L14d th5% K20 | R278 A | 957 | +0.92 (0.73) | -0.45 (-0.35) | -1.81 (-1.40) | +7.13 (5.09) | +5.90 (4.13) | +4.67 (3.20) | +6.73 (4.39) | TIES |
| binance+mexc L14d th10% K20 | R278 B | 507 | +1.31 (0.99) | -0.07 (-0.05) | -1.44 (-1.05) | +2.43 (1.86) | +1.06 (0.80) | -0.32 (-0.23) | +0.55 (0.41) | TIES |
| gate+mexc L7d th10% K20 | R278 C | 514 | +13.35 (4.42) | +10.03 (3.29) | +6.72 (2.18) | +14.47 (4.83) | +11.15 (3.69) | +7.84 (2.56) | +10.63 (3.53) | BEATS |
| binance+gate L14d th10% K20 | R390 A | 957 | +10.77 (1.33) | +8.91 (1.11) | +7.06 (0.88) | +9.97 (1.72) | +8.06 (1.39) | +6.14 (1.06) | +7.49 (1.94) | TIES |
| gate+kucoin L14d th5% K20 | R279 A | 957 | +14.02 (4.88) | +12.80 (4.45) | +11.58 (4.02) | +13.64 (6.23) | +12.33 (5.60) | +11.02 (4.96) | +9.44 (6.00) | BEATS |
| binance+kucoin L14d th5% K20 | R279 B | 957 | +8.74 (4.34) | +7.54 (3.74) | +6.34 (3.14) | +9.80 (6.80) | +8.49 (5.83) | +7.19 (4.86) | +5.71 (4.22) | BEATS |

- Windows: sUSDe from 2024-02-17 (or the book's start, 2025-05-12 for R278 B and 2025-05-05 for R278 C) to
  2026-09-30. Aave USDC from 2023-02-07 or the book's start (R278 A from 2023-05-25). The bill uses the book's whole
  history. So the columns cover different days; compare within a benchmark.
- The rule's outcome is the same at 1x and 3x: the same three books BEAT and none of the six LOSES.
- Aave USDC at 2x: four of six books beat it with t >= 2 (R278 A, R278 C, R279 A, R279 B); R278 B and R390 A tie.

### The same cells, 2x, with book and benchmark %/yr and risk (full window)
| Book | sUSDe %/yr | Book %/yr on those days | Excess sd %/yr | Book max DD | Excess max DD | Top-10-day share | Aave USDC %/yr | Book %/yr on Aave days |
|---|---|---|---|---|---|---|---|---|
| R278 A gate+hyperliquid | 8.81 | 8.36 | 1.53 | -1.68% | -6.84% | 15% | 4.96 | 10.86 |
| R278 B binance+mexc | 4.74 | 4.68 | 1.26 | -0.52% | -1.53% | 48% | 3.62 | 4.68 |
| R278 C gate+mexc | 4.73 | 14.76 | 4.30 | -1.88% | -1.89% | 47% | 3.61 | 14.76 |
| R390 A binance+gate | 8.81 | 17.72 | 12.71 | -6.98% | -11.83% | 78% | 4.72 | 12.78 |
| R279 A gate+kucoin | 8.81 | 21.60 | 3.79 | -0.61% | -4.97% | 25% | 4.72 | 17.05 |
| R279 B binance+kucoin | 8.81 | 16.35 | 2.48 | -0.67% | -5.91% | 19% | 4.72 | 13.22 |

- The benchmark's drawdown is 0 in every cell: the DefiLlama rate never went negative, and the series does not show
  depeg or price risk (see Risk below).
- "Excess max DD" is the largest fall of the cumulative book-minus-benchmark sum: R278 A spent a long stretch below
  sUSDe (-6.84 points).

## Sub-windows (reported, engine v2, 2x)
| Book | 2025+ book %/yr | 2025+ sUSDe | 2025+ excess (t) | 2025-04-09+ sUSDe | 2025-04-09+ excess (t) | 2025-04-09+ vs Aave USDC (t) |
|---|---|---|---|---|---|---|
| R278 A gate+hyperliquid | 4.08 | 5.33 | -1.25 (-0.90) | 4.72 | -0.23 (-0.14) | +0.92 (0.59) |
| R278 B binance+mexc | 4.68 | 4.74 | -0.07 (-0.05) | 4.74 | -0.07 (-0.05) | +1.06 (0.80) |
| R278 C gate+mexc | 14.76 | 4.73 | +10.03 (3.29) | 4.73 | +10.03 (3.29) | +11.15 (3.69) |
| R390 A binance+gate | 24.74 | 5.33 | +19.40 (1.64) | 4.72 | +23.56 (1.70) | +24.71 (1.78) |
| R279 A gate+kucoin | 26.34 | 5.33 | +21.00 (5.69) | 4.72 | +23.85 (5.69) | +24.99 (5.97) |
| R279 B binance+kucoin | 19.85 | 5.33 | +14.52 (5.95) | 4.72 | +16.14 (5.81) | +17.29 (6.22) |

- Since 2025, R278 A (the oldest forward Hyperliquid book) earned 4.08%/yr, below sUSDe's 5.33% and about Aave USDC's
  3.80%. R437 already showed its halves falling from +5.13 to +1.49 bp/day; against a passive token that decay
  leaves nothing.
- The 2025-04-09+ split (the sUSDe adaptor's TVL-pricing fix) changes no call.

## Reported, not deciding
- **Engine v1** (sUSDe, 2x): R279 A +7.76 (t 3.78), R278 C +8.26 (3.60), R279 B +6.74 (3.45) BEAT; R278 A -2.68
  (t -2.10) LOSES; R278 B +0.22 and R390 A +2.98 tie. Under v1's conservative accounting R278 A is significantly
  below sUSDe.
- **Non-forward books** (v2, sUSDe, 2x): binance+hyperliquid -2.46 (t -2.63, LOSES), hyperliquid+mexc -1.57 (t
  -0.78), all four +11.71 (t 1.62).
- **Aave USDT** is within 0.4 points of Aave USDC in every decider cell.
- **Post hoc, approximate, no decision:** R438's diagnostic measured v2's notional drift over each book's whole
  window (+3.28 points a year on gate+kucoin, +1.49 binance+kucoin, +2.40 gate+mexc, +2.65 gate+hyperliquid, +1.15
  binance+gate). Subtracting those full-window figures from the sUSDe 2x excess leaves about +9.5, +6.0 and +7.6 for
  the three books that BEAT, and about -3.1 for R278 A. The drift on the sUSDe window itself was not measured. R390 A
  without blowout and dead-leg trades was +9.69%/yr against v2's +13.42 over its full window (R437); its sUSDe
  excess would fall by a similar amount.

## Read against the program
- Trials: 12 (6 deciders x sUSDe and Aave USDC). Program trials: 9,785,286 (`registry.program_trials`), including
  this lane's 12.
- The books were selected by R275's search (best of 560) and R277's replication rule, then audited by R437/R438 on
  the same rows. This lane adds a benchmark to seen rows; it inherits that selection and cannot confirm an edge.
- The verdict says the backtest of half the forward books clears a passive stablecoin yield. The forward lanes'
  live nets remain the test of whether that survives.

## Risk caveats (not priced by any number here)
- sUSDe: the DefiLlama rate is a spot snapshot of Ethena's latest payment, not the realised sUSDe:USDe exchange-rate
  change. USDe depeg (about 0.65 on Binance on 2025-10-10, venue-specific), the 7-day cooldown (admin can raise it
  to 90 days), sanctions freezing, smart-contract and custody risk, and Ethena's exposure to negative funding
  (absorbed by its Reserve Fund) are not in the series. sUSDe is not offered to EU/EEA residents, so it is a
  benchmark only for the owner, not a holding.
- Aave: contract and oracle risk, withdrawal limits at high utilisation (Aave's docs on these were not read).
- Books: ADL of the profitable leg, liquidation of a leg before convergence, venue failure and collateral haircuts
  (intake note red-team table); none is priced by the daily-close archive.
- No cost is charged to the benchmark side (swap, gas, cooldown), which favours the benchmark.

## Not checked
- Whether DefiLlama recomputed sUSDe's pre-2025-04-08 rows after the adaptor fix (the sub-window only brackets it).
- The realised sUSDe exchange rate (an on-chain archive read needs a keyed RPC; not done).
- The drift and blowout adjustments on the sUSDe window (only full-window figures from R437/R438 exist).
- R294 (mexc+lighter): no committed audited daily net.
- `docs/EDGE_SCOREBOARD.md` was not updated: its rows are edges with holdout and forward columns, updated through
  R363; it carries no gate-0 audit or benchmark lane (R437 and R438 are not in it).

Paper only. No order, no money, no key.
