# FINDINGS: oiwick_v1 (R252). Fade liquidation cascades, proxied by an open-interest drop plus a long wick

**Verdict: NULL.** All 4 books stopped at discovery.
- The closest was **ALL/24** (both sides, held 24 h): +2.0 bp/day at 1x, NW t 1.93, against the 2.0 required.
- The validation window was not read, and neither was the holdout.

- **Registry row:** R252 (trials 4). Program trials after it: 9,472,001.
- **Gate:** 0.
- **Reproduce:** prereg sha 30e93574, frozen in commit 821fe02 before the run. Run `python scripts/run_oiwick.py`
  (about 1 minute).
- **Origin:** queue M176.

**Disclosed after the run: discovery is effectively 2022-23.**
- Binance OI metrics cover 10% of eligible coin-hours in 2021, and 99-100% from 2022.
- So 2021 contributes 54 of 658 long-cascade triggers and 2 of 166 squeeze triggers.
- The PREREG did not state this.

## Numbers (per-unit book: s / eligible coins, about 50; exposure is tiny, so read t rather than bp)

| Book | Net bp/day 1x / 2x / 3x | Gross / cost | Gross exposure | NW t (1x) | Alpha bp/day (t) | Trimmed mean |
|---|---|---|---|---|---|---|
| ALL/4 | +0.74 / +0.53 / +0.32 | +0.96 / 0.21 | 0.0025 | 1.73 | +0.77 (1.83) | +0.09 |
| **ALL/24** | +2.00 / +1.78 / +1.57 | +2.21 / 0.21 | 0.0145 | **1.93** | +1.96 (1.88) | +1.33 |
| SQZ/4 | +0.10 / +0.06 / +0.01 | +0.14 / 0.04 | 0.0005 | 0.53 | +0.10 (0.56) | -0.04 |
| SQZ/24 | +0.30 / +0.26 / +0.22 | +0.34 / 0.04 | 0.0029 | 1.03 | +0.33 (1.14) | +0.25 |

Net per year at 1x (bp/day):
- ALL/4: 2021 +0.63, 2022 +0.09, 2023 +1.52.
- ALL/24: 2021 +1.79, 2022 -0.12, 2023 +4.31.
- SQZ/4: 2021 -0.01, 2022 +0.41, 2023 -0.11.
- SQZ/24: 2021 +0.01, 2022 +0.97, 2023 -0.07.

## Triggers and raw forward returns (discovery, price return, sign not applied)

| Side | Triggers | 1 h | 4 h | 24 h |
|---|---|---|---|---|
| Long cascade (OI drop + lower wick) | 658 | +38.9 bp | +65.0 bp | +143.4 bp |
| Short squeeze (OI drop + upper wick) | 166 | -0.6 bp | -219.3 bp | -390.7 bp |

**Both sides reverted in raw price terms.** That is the fade's sign on both sides. R206 (Gate, 2026) found the opposite
on the long side, where long cascades continued.

## Post-hoc diagnostics (after the verdict; descriptive, not decided on)
Script: `posthoc_diag.py` in this folder.

| Side, horizon | Raw mean | Raw median | Market-adjusted mean | Top-5 events' share of the absolute sum |
|---|---|---|---|---|
| Long cascade, 4 h | +65.0 | +45.8 | +4.7 | 6% |
| Long cascade, 24 h | +143.4 | +111.1 | +22.8 | 5% |
| Squeeze, 4 h | -219.3 | -11.1 | -140.3 | 41% |
| Squeeze, 24 h | -390.7 | -162.9 | -190.1 | 28% |

(Market adjustment subtracts the equal-weight mean of eligible coins' returns over the same hours; units are bp.)

- **The long-cascade bounce is mostly the whole market's.**
  - Market-adjusted, it is +5 bp at 4 h and +23 bp at 24 h, against +65 and +143 raw.
  - Cascades cluster in market-wide sell-offs, and the market rebounds afterwards. The book is long only right after
    those hours, so it is a conditional market-timing bet.
  - A daily beta regression does not remove that, which is why the book's "alpha" is close to its mean.
- **The squeeze reversion is coin-specific but rare and lumpy.**
  - The 24 h market-adjusted mean is -190 bp, but on 166 events, with five events carrying 28-41% of the sum.
  - Almost all of the SQZ/24 book's discovery gain is from 2022 (+0.97 bp/day). In 2023, the year with the most
    squeezes (110), it made -0.07.
- **Why the event means are larger than the book.**
  - Seven squeeze triggers re-fired on the same coin within 24 h. Those coins had the largest drops, so the event mean
    counts those drops several times; the book holds one unit and counts each drop once.
  - With only the first trigger per coin per 24 h, the event sum is +0.28 bp/day of book. The book made +0.34 gross.

## Cost sensitivity
- At 1x, cost is 0.21 bp/day on ALL and 0.04 on SQZ. At 3x, ALL/24 still nets +1.57 and SQZ/24 +0.22.
- **Costs do not decide anything here.** No book reached t 2 even before costs.
  - ALL/24 gross t is close to its net t, because cost is a tenth of the gross.

## Reading
- **The cascade signal is real as a description, but not as a coin-level edge.**
  - The long side adds about +23 bp over 24 h relative to the market.
  - The squeeze side is a few large events in 2022.
- **What remains is a market-timing idea:** buy the market after hours with many cascade triggers.
  - This lane did not test it, and its discovery evidence is post hoc.
  - It is queued as **M233** (cascade-count market timing), to be frozen before any statistic. It must be read on
    validation 2024-25 as a new lane, since this run chose it after seeing 2022-23.
- **Read against the program:** 9,472,001 trials. A t of 1.93 is noise at that scale even if it had passed.

## Not checked
- Other thresholds (2% or 5% OI drops; 2 ATR or 4 ATR wicks), and 1 h holds.
- Liquidation data itself: Binance liquidation files end in 2024, and Coinalyze history was R158.
- Market-neutral (hedged) books.
- Maker entries.
- The validation window and the holdout (not reached).
