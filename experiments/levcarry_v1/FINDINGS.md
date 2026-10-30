# FINDINGS: levcarry_v1 (R280). The carry books cannot carry leverage: stay at 1x, on cross margin per venue

**Verdict: a measurement (0 trials).**
- **Pre-committed action: the forward lanes stay at 1x.** No book has a safe leverage of even 1 under `iso_daily`
  at mm 5%: every book has legs liquidated at L = 1. The rule needed a safe leverage of at least 3.
- **Isolated margin per leg is the wrong setup for these books at any leverage.** On 155 days between 2021 and 2026,
  a coin the books held short rose about 95% or more within the day. 149 of them were real pumps seen on other
  venues, not bad prints.
- **On one cross-margin account per venue, 1x never liquidates.** That is the accounting R275, R277, R278 and R279
  already use. Two books also survived 2x: R278 B (binance+mexc) and R279 B (binance+kucoin). No book survived 3x.

**Reproduce**
- prereg sha f776cc38, frozen in commit 645aa0c before any range, move or liquidation was computed on market data.
- `nice python scripts/run_levcarry.py` takes about 9 minutes. The parity guard passed on all 5 books: at L = 1
  with no liquidation, each book's daily net equals its engine run's within 1e-9.
- `python scripts/audit_levcarry.py` writes `results/audit_l1.csv`.
- `results/events.csv` (467,315 liquidated legs, 40 MB) is not committed. Its sha256 is in `results/hashes.json`.

## What the owner is told (mm 5%)
Safe leverage is the largest L in {1, 2, 3, 5, 10} with zero liquidated legs over the book's whole window. "< 1"
means legs were liquidated even at 1x; the count is in brackets.

| Book | Days | `iso_hold` | `iso_daily` | `cross_daily` | Net at the cross safe L, %/yr (1x / 2x / 3x cost) | NW t | Max DD |
|---|---|---|---|---|---|---|---|
| R278 A gate+hyperliquid L14 th5% K20 | 1225 | < 1 (70) | < 1 (13) | **1** | +9.73 / +8.51 / +7.28 | 8.63 | −2.1% |
| R278 B binance+mexc L14 th10% K20 | 507 | < 1 (40) | < 1 (17) | **2** | +12.65 / +9.92 / +7.19 | 4.80 | −0.7% |
| R278 C gate+mexc L7 th10% K20 | 514 | < 1 (113) | < 1 (52) | **1** | +16.29 / +12.99 / +9.69 | 7.38 | −0.9% |
| R279 A gate+kucoin L14 th5% K20 | 2078 | < 1 (156) | < 1 (48) | **1** | +11.76 / +10.34 / +8.92 | 11.41 | −0.7% |
| R279 B binance+kucoin L14 th5% K20 | 2078 | < 1 (162) | < 1 (42) | **2** | +21.59 / +18.72 / +15.85 | 11.17 | −4.5% |

- **At mm 1%** the table is the same, except R278 C is safe at 2x under `cross_daily`.
- **R279 B at 2x** draws down 4.5%, below the −3% kill switch its lane uses at 1x. A 2x version would need its own
  stop.
- **These safe leverages are in sample**, over windows whose worst day decides them. One pump larger than any seen
  breaks them.

## Kept share (net at L ÷ (L × net at 1x), same policy and mm; 1 = liquidations cost nothing)
| Book | `iso_daily` L2 (mm 1% / 5%) | `iso_daily` L3 | `cross_daily` L2 | `cross_daily` L3 |
|---|---|---|---|---|
| R278 A | 0.72 / 0.46 | 0.43 / −0.92 | 0.58 / 0.58 | 0.56 / −0.28 |
| R278 B | 0.94 / −0.69 | −0.48 / −6.96 | 1.00 / 1.00 | −0.28 / −0.28 |
| R278 C | 0.49 / −0.20 | 0.10 / −2.10 | 1.00 / 0.20 | −0.09 / −0.29 |
| R279 A | 0.78 / 0.39 | 0.16 / −1.58 | 0.29 / −0.06 | −0.03 / −0.78 |
| R279 B | 0.26 / −0.25 | −0.45 / −2.67 | 1.00 / 1.00 | 0.34 / −0.74 |

From 5x up, every book and policy loses money, except R278 C under `iso_daily` at mm 1% (+0.97%/yr at 5x).

## What liquidates a leg (audit of the 1x liquidations, `results/audit_l1.csv`)
All 155 leg-days liquidated at L = 1 under `iso_daily` (mm 5%) are **short legs**. Each was hit by a rise of about
95% or more within one day.

| Kind | Leg-days | Test |
|---|---|---|
| Real pump | 149 | another venue moved at least 50% the same way that day |
| One-venue print | 2 | no other venue moved 20%; the leg's own close moved less than 20% |
| Mixed | 4 | the rest |

- **The pumps are low-cap coins with high funding, which is what the short leg is chosen for.** Examples: MYX
  (2025-09), TNSR (2025-11), HYPER (2025-07), ZEREBRO (2025-10), TAIKO (2026-07, +540% intraday), AKE, SIREN, RAVE,
  ESPORTS.
  - 114 of the 155 also closed the day at least 50% higher, and 61 at least 100% higher.
  - They are concentrated in 2025 (67) and 2026 (70), against 18 in 2021-2024.
- **The two one-venue prints** are both Gate wicks: BCH on the day ending 2021-02-21 (a 1,580 high against 752 on
  Binance) and OGN on the day ending 2023-10-24. Three of the four mixed days are also one-bar wicks (BICO and SCR on
  Gate, AIO on Binance).
- **Days are dated by their end:** the day dated D runs from 00:00 UTC on D − 1 to 00:00 UTC on D.
- **Adverse move per held leg-day** (`results/moves.csv`). Short legs carry the tail.

  | Book | Long median | Long 99% | Long 99.9% | Short median | Short 99% | Short 99.9% | Short max |
  |---|---|---|---|---|---|---|---|
  | R278 A | 3.3% | 22% | 47% | 3.0% | 30% | 67% | 423% |
  | R278 B | 3.7% | 32% | 73% | 3.3% | 42% | 113% | 369% |
  | R278 C | 4.0% | 40% | 81% | 3.8% | 68% | 196% | 541% |
  | R279 A | 3.4% | 28% | 58% | 3.1% | 36% | 105% | 1415% |
  | R279 B | 3.4% | 27% | 56% | 3.1% | 34% | 95% | 543% |

## The days that wipe a cross account
Under `cross_daily`, an account is lost when its legs' summed worst moves reach its equity (1/L per leg).

- **2025-10-11, the 2025-10-10 crash.**
  - At 2x it took the Gate account of R278 A (both mm), R278 C (mm 5%) and R279 A (mm 5%).
  - The crash was real on every venue. The 20 legs' intraday moves on Binance, Gate, Hyperliquid and MEXC agree to
    a few points (for example IP −89%, FARTCOIN −86%, PIPPIN −89%, NAORIS −91%).
  - The account was one-sided: R278 A held 19 longs and 1 short on Gate, because Gate is the venue that pays less
    funding. The hedges sat on the other venue and could not offset the crash inside the Gate account.
- **2022-11-14 and 2023-10-25 (R279 A at 2x, both mm).** These are Gate one-bar prints:
  - AXS traded at 82 on Gate against a real high of 13.3 on Binance;
  - MINA traded at 7.0 on Gate against 0.86 on Binance.

  A venue that liquidates on a mark price near the index would not have seen them. At 2x and mm 1%, R279 A had no
  other liquidation. This is read off the events, not a pre-registered rule.
- **At 3x** every book loses at least one account, mostly on 2025-10-11 and on single-coin pumps (TNSR, HYPER,
  ZEREBRO, MYX, TAIKO, TAC).

## Isolated margin at 1x: higher mean, much worse risk
At L = 1, `iso_daily` caps a leg's loss at its margin. When a short leg's coin more than doubles and stays there, the
liquidated short loses 1 while the long keeps its gain.

| Book | `cross_daily` L1 (R275's accounting) | `iso_daily` L1, mm 5% |
|---|---|---|
| R278 A | +9.73%/yr, NW t 8.63, DD −2.1% | +11.99%/yr, NW t 4.44, DD −3.6% |
| R278 B | +6.33, NW t 4.80, DD −0.4% | +2.97, NW t 0.52, DD −4.5% |
| R278 C | +16.29, NW t 7.38, DD −0.9% | +25.98, NW t 2.19, DD −8.1% |
| R279 A | +11.76, NW t 11.41, DD −0.7% | +11.34, NW t 3.54, DD −5.7% |
| R279 B | +10.80, NW t 11.17, DD −2.3% | +9.29, NW t 5.18, DD −4.7% |

- **Where the mean is higher (R278 A and C), it comes from a handful of pumps** (TAIKO, HYPER, ZEREBRO, AKE,
  JELLYJELLY, TNSR). Pumps that fade by the close cost a whole margin instead. The t falls on every book.
- **It is not an edge to pursue.** Its sign depends on how many pumps close above +100%.

## Not modelled (from the PREREG; what the results above lean on)
- **Marks:** liquidation here uses trade highs and lows. Gate's one-bar prints (AXS, MINA, BCH, OGN) overstate it.
- **Tiers and caps:**
  - per-coin maximum leverage, which is often 3-10x on these low caps, so 5x and 10x could not be opened anyway;
  - tiered maintenance by position size.
- **Partial liquidation, liquidation fees, ADL.**
- **Transfer cost and delay** of the daily margin moves that `iso_daily` and `cross_daily` assume.
- **The cross bound:** `cross_daily` adds every leg's worst move as if they all happened at the same moment. That
  overstates the risk on pump days, when one leg moves. It is close to exact on 2025-10-11, when every long fell
  together.

## Reading
- **Against program trials (9,478,328):** nothing to read. This is a measurement with 0 trials, and it changes no
  book.
- **For the owner's leverage ask (2026-10-21):**
  - the carry books are slow by construction: about 10-20%/yr on capital at 1x;
  - leverage does not change that safely. At most 2x, on cross margin, on the two Binance-paired books, and only in
    sample;
  - the risk is not the hedge drifting. It is a single pump or crash day on one venue's account.
- **Costs:** the 1x / 2x / 3x columns above scale with L, as notional does.

## What this suggests (not pre-committed; each needs its own PREREG and id)
1. **Venue-balanced books.** Choose pairs so each venue's account holds about as many longs as shorts. A crash then
   offsets inside the account instead of wiping it. To measure it, model the cross account on its hourly
   mark-to-market path, not on summed extremes.
2. **Mark-price data.** Binance publishes mark-price klines on data.binance.vision, and Gate serves mark candles
   (`mark_` contracts). Rerunning the measurement on marks would separate venue prints from real moves.
3. **Short-leg squeeze exposure as a factor.** The 2025-26 pumps hit exactly the coins whose funding put them on
   the short side. Whether a pump-risk filter costs more carry than it saves is a question for a new family.

Registry: R280, DONE, DATA_PASS, 0 trials. Method M265: TESTED.
