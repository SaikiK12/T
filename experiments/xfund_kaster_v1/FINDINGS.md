# FINDINGS: xfund_kaster_v1 (R511). R508's mechanism replicates on 31 Kraken coins nobody here had read, against Aster

**Verdict: PASS (R391's rule, gate 1).** All four checks hold on the decided book: the one-sided NW p is 7.6e-7, the
2x mean is above 0, the 10% trimmed mean is above 0, and so is the mean without the two best coins.

- **Registry:** R511, 1 trial. Program trials become 9,785,752.
- **Reproduce.**
  - The PREREG (sha 7dbe917d), `symbols.csv` and `data_manifest.json` were frozen in commit 9e1a48f before any Aster
    data inside the window was fetched.
  - `run_xfund_kaster.py fetch`: 132 symbols with receipts, none empty.
  - `run`, once, on 2026-11-19. All 10 inputs and 730 data files matched.
- **The decided book:** R275's L14d th5% K20 on kraken + aster, on the 31 Kraken coins outside R508's table.

## Decided book: 31 never-read coins, 2025-12-31..2026-11-15
| Cost | %/yr on book capital | bp/day |
|---|---|---|
| 1x (7 bp a leg) | **+13.46** | +3.69 |
| 2x | +11.86 | +3.25 |
| 3x | +10.25 | +2.81 |

- **Book days and t.** 320 book days. NW t (lag 10) 4.81; iid t 3.87; annualised daily Sharpe 4.1.
- **Robustness.** Trimmed mean +3.05 bp/day. Without DEXE and ZBT, the two best coins: +2.72 bp/day (+9.9%/yr).
- **Halves:** +2.64 and +4.73 bp/day. Unlike R508, the second half is the stronger.
- **Risk.** Max drawdown (running sum) -0.57%. The top 10 days hold 40% of the total, more concentrated than R508's 25%.
- **Where the return comes from.** Funding share 1.06. Costs take 1.6%/yr per 1x; the book breaks even near 9x costs
  (about 66 bp a leg).
- **The book.** 12.9 of 20 slots held on average; 201 trades on 29 coins, 27 of them net positive.
  - **Direction:** both ways. Long Kraken 103 trades, long Aster 98.
  - **Best (bp/day of book):** DEXE +0.64, ZBT +0.32, OPEN +0.32, ROSE +0.27, SOON +0.22.
  - **Worst:** SYN -0.08.
- **Read against the program.**
  - The one-sided Bonferroni threshold over 9,785,752 trials is z 5.73. The NW t of 4.81 does **not** clear it.
  - The decided book is one pre-registered candidate on data never read, so R391's rule is the decision. The program
    bar is reported as the stricter reading.

### By month (% of book capital, 1x)
| 2025-12 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 (to 15th) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| -0.02 | -0.01 | +0.31 | +0.71 | +0.84 | +1.59 | +3.52 | +1.33 | +1.65 | +0.59 | +0.40 | +0.88 |

- Few slots were filled in the winter; the book grew into the year.
- June alone holds a quarter of the total.

### By Kraken liquidity (diagnostic)
Liquidity is each coin's median daily USD volume over the window, from daily candles (`diagnostics/volume.csv`).

| Kraken volume per day | Coins | Traded | %/yr of book at 1x |
|---|---|---|---|
| under $10k | 20 | 20 | +9.80 |
| $10k-100k | 10 | 8 | +3.43 |
| $100k-1M | 1 | 1 | +0.23 |

- These coins are thinner than R508's: 20 of 31 trade under $10k a day on Kraken.
- Aster's median for the 31 is about $9k a day.

### Funding profile (the 31 coins, annualised means)
- Kraken: median -22%, interquartile range -54% to +3%.
- Aster: median -8.5%, interquartile range -27% to +2%.
- Both venues run negative on these coins; Kraken more so. The book is long the venue paying more negative funding
  as often as the reverse.

## Reported books (not decided)
| Book | Coins | %/yr 1x / 2x / 3x | NW t | Trades | Max DD | Long venue (trades) |
|---|---|---|---|---|---|---|
| kraken + aster | 132 | +18.81 / +17.60 / +16.38 | 4.92 | 163 | -1.83% | kraken 82, aster 81 |
| kraken + hyperliquid + aster | 132 | +25.04 / +23.43 / +21.81 | 6.23 | 217 | -1.69% | kraken 104, aster 66, hyperliquid 47 |

- The three-venue book matches R508's level (+24.3%/yr) with a second counter-venue.
- Its 20 slots were always full.

## Live cost snapshot (diagnostic, 2026-11-19 08:44 UTC)
Source: `diagnostics/books_20261119.json`, the 31 decided coins. Medians, per side, half-spread plus walk, fees
excluded.

| | Quoted spread | $1,000 | $2,500 |
|---|---|---|---|
| Kraken | 23.4 bp | 15.8 bp | 22.5 bp |
| Aster | n/a | 11.1 bp | 17.0 bp |

- **Adding fees.** Taker fees are 5 bp on Kraken and 4 bp on Aster (its docs). A leg-side then costs about 18 bp on
  average, about 2.6x the test's 7 bp. The book made +10.25%/yr at 3x.
- **The costliest:** LPT 33 bp a side on Kraken at $1,000; LUNA2 32; ZBT 26.
- **Funding still extreme today** on Kraken for some: LUNA2 -140%/yr, LPT -70%/yr.

## What this does not show
- **Capacity.** $1,000-2,500 a leg is about what these books hold. The 31 coins add perhaps $20k-50k of two-leg
  capital to R508's, not more.
- **Out of sample in time.** It is the same year as R508. The coins are new, the period is not.
- **Access.** Aster is authorised nowhere, like Hyperliquid. Its terms do not name France. Not checked further.
- **Survivorship.** Kraken's list is today's; Aster's fully delisted contracts are missing.
- **Fills.** As in R508: daily closes plus a flat cost in the test, one book snapshot here.

## Next
- A forward paper lane on the three-venue book, with measured costs, would add these coins to R509's evidence and
  slots. It needs an Aster client in the paper engine (a new id).
