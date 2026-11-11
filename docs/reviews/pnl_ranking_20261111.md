# The lab's methods ranked by PnL, 2026-11-11

The owner asked for a ranking of the methods by return, and for experiments on the top ones instead of more
work for its own sake. This page ranks rounds R143-R448. It is a reading of the registry and FINDINGS, not a new
test. Each round's FINDINGS stays the authority for its own numbers.

**Method.**
- Four Haiku extractors read `registry/rounds.csv` and the FINDINGS in four slices. The rows quoted below were
  checked by hand against the registry notes.
- Units are net of the lab's costs at 1x unless marked. bp/day is converted to %/yr by ×3.65.
- Figures per trade or per event are not comparable and are left out of the tables.
- Rows are grouped by the evidence behind them:
  - forward: days after the freeze;
  - blind archive: a reserved sample or a one-shot holdout;
  - seen: in-sample, validation, or a gate 0 on data someone had read.

## 1. Forward days (the only evidence that can confirm)
| Round | Method | Venue (France?) | Result so far | Reading |
|---|---|---|---|---|
| R200 | Flow book A (three 72 h flow cells) | Binance (no) | +31.0% over 40 days, t 1.25, DD −17% | to 11-09; 10-01..19 replayed |
| R200 | Flow book B (top_vs_crowd) | Binance (no) | +13.3% over 40 days, t 1.27, DD −5.7% | R216: the replay gain came from stock perps |
| R215/R218 | Flow books on MEXC prices | MEXC (no) | A +7.2%, B +1.4%, X2 +12.6% over 40 days | crypto coins only |
| R371 | C17 intraday relative strength | Binance/MEXC (no) | 3 scored days (6 missed, 11-02..11-09) | decides at 500 days |
| R220, R390 | Funding carry | Binance/MEXC/Gate (no) | about 0 | |

t is a plain daily t (not Newey-West); DD is on compounded daily nets. The flow journals stood still from 2026-11-06
to 2026-11-11 (container stop). `claude-flow-paper.yml` caught them up from Binance's 30-day history on 2026-11-11.

## 2. Blind archive reads
| Round | Method | Window | Net, %/yr | t | Max DD | Verdict |
|---|---|---|---|---|---|---|
| R392 | C17 intraday relative strength | 2020 reserved, 128 days | +315 (86.2 bp/day) | 3.04 | | FAIL by a hair (p 0.0012 vs 0.001); 10 best days 94% of net |
| R217 | Flow book X2 (agreement squared) | holdout 2025-07..2026-09 | +155 | 1.70 | 62% | NULL |
| R198 | Flow book A | holdout | +83 (+104% in 457 days) | 1.22 | 47% | NOT CONFIRMED |
| R216 | Flow book B, crypto only | holdout | +67 (18.3 bp/day) | 2.74 | | split read; BEAT+LAB ~68% of A's gross |
| R241 | SVXY in VIX contango | holdout 2020-26 | +19 (7.5 bp/day) | 1.70 | 45-66% | NULL |
| R189 | New-listing short | holdout | −2.6% per event | −0.78 | squeezes to +710% | NULL |
| R286, R391 | Carry, reserved samples | 2020; long tail | +2.5 to +2.9 | 3.9-4.0 | <0.5% | CONFIRMED (R391) |

## 3. Seen windows: the robust books, and those reachable from France
| Round | Method | Venue (France?) | Net, %/yr | NW t | Max DD |
|---|---|---|---|---|---|
| R439 | Five-venue funding carry | Binance, Gate, HL, MEXC, KuCoin (mostly no) | +18.5 | 8.71 | −4.4% |
| R277 | Gate+KuCoin carry | (no) | +11.8 | 11.41 | −0.7% |
| R446 | HLP deposit | Hyperliquid (yes) | +14.3 | 1.87 | −0.8% |
| R445 | HYPE/BTC spot-perp carry, portfolio margin | Hyperliquid (yes) | +10.1 | 3.67 | −0.6% |
| R447 | LLP + hedged LIT stake | Lighter (yes) | +10.0 | 3.94 | −0.35% |
| R288 | HL+Lighter cross-venue carry | DEXes (yes) | +3.5 | 7.34 | |
| R441 | OKX Europe X-Perp carry | OKX EU (yes) | +5.4 | 0.62 | |
| R443 | OKX X-Perps vs Hyperliquid carry | (yes) | +1.0 | −0.55 | |
| R444 | Hyperliquid spot-perp carry | (yes) | +2.6 | (excess t −3.66) | |
| R442 | OKX stock X-Perp carry | (yes) | −0.5 | | |

R280 found that the carry books cannot take leverage: short legs on small coins were liquidated even at 1x on
isolated margin. They stay at 1x on cross margin.

## 4. Large figures that did not hold
- **GBM rankers (R299, R304):** +202 to +215%/yr in validation, t 4.0-4.2. R332 earned as much with a random rule
  on the same leaking panel, so the columns leaked. NULL.
- **Level models (R336, R337):** +540 to +626 "%/yr" in the extraction, but per trade notional, not on capital.
  R337 is NULL on Lighter. R336 earned only a forward lane on MEXC's zero-fee perps, which are closed to France.
- **Strategy switching (R414):** follow-the-leader +69.7%/yr in sample with a 49% drawdown. It beats equal weight
  with t 1.28: NULL.
- **New-listing short:** about −9% in every year of the in-sample period (R188). The holdout gave −2.6% a listing
  with squeezes to +710% (R189).

## 5. What the high returns have in common
- **Concentration.** C17's 2020 net comes 94% from its 10 best days.
  - The flow books' crypto gain sits in a handful of collapsing small caps. On 2026-11-11 (post-hoc, spent data),
    removing the 10 largest-contributing coins leaves:
    - book B: −0.1 bp/day gross in 2021-25 and +2.4 in the 2025-26 holdout;
    - book A: +8.2 in 2021-25 and −0.6 in the holdout.
  - The coins are GOAT, USUAL, AEVO, MELANIA, POPCAT, then LAB and BEAT.
  - R200's forward gain came from stock perps (R216).
- **Venues.** Every high return was measured on Binance, MEXC, Gate or KuCoin, all closed to the owner from France
  (`docs/reviews/venue_access_fr_20261110.md`).
- **Seen windows.** Apart from C17's 2020 read, none of them has blind evidence above t 2 at the decision.

## 6. Experiments on the top methods (2026-11-11)
- **R448, flow books on Hyperliquid** (the top family moved to a venue the owner can reach):
  - Gate 0, 2026-04..09: A +4.9 bp/day (+17.9%/yr, t 0.91), CONTINUE; B −0.7 bp/day, NULL.
  - Hyperliquid prices equal Binance's on the same coins (correlation 0.9996). The gap is coverage: 54 of 133
    coins are listed on Hyperliquid, and the gain sat in LAB and BEAT, which neither Hyperliquid nor Lighter lists.
  - A runs forward from 2026-11-12; the expected answer is NULL.
  - See `experiments/flow_hl_v1/FINDINGS.md`.
- **R449 (frozen next), Hyperliquid user vaults picked by their past record:** France-reachable. It reads every
  vault, closed ones included, from `claude/hl-vaults-data`.
- **Research, not yet a lane:** other perp-DEX liquidity pools (Jupiter JLP, GMX GM pools), hedged.

## 7. Reading for the owner
- No method has yet shown a high return (above about 30%/yr) on days nobody had seen, net of costs, on a venue
  reachable from France.
- What holds up, and is reachable, earns about 10-14%/yr: the HLP and LLP deposits, and HYPE spot-perp carry. These
  are seen windows, short the venue's tail.
- The flow books and C17 keep running forward. They decide on their frozen dates (R200 on 2026-12-29; R371 after
  500 scored days).
