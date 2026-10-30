# FINDINGS: lmw_v1 (R251). Lo-Mamaysky-Wang kernel chart patterns on daily crypto, forex and indices

**Verdict: NULL.** One of 6 books passed discovery and failed validation.
- **REV2/IDX** (head-and-shoulders short, inverse long, on world indices) passed discovery 2001-12 with alpha
  +0.32 bp/day, t 2.27. In validation 2013-19 it made -0.02, t -0.18.
- Every other book stopped at discovery. The best was ALL8/IDX, alpha t 1.42.
- The crypto holdout was not read, and the forex/index holdout was not reached.

- **Registry row:** R251 (trials 6). Program trials after it: 9,471,997.
- **Gate:** 0.
- **Reproduce:** prereg sha 719dc991, frozen in commit c2e72a9 before the run. Run `python scripts/run_lmw.py` (about
  4 minutes).
- **Origin:** queue M201.

## Numbers (1x; per-unit books, so means are small where patterns are rare)

| Book | Window | Net bp/day 1x / 2x / 3x | Gross / cost | Invested or exposure | Alpha bp/day (t) |
|---|---|---|---|---|---|
| ALL8/FX | discovery | +0.08 / +0.04 / -0.00 | +0.13 / 0.04 | 60% of days | +0.09 (0.53) |
| REV2/FX | discovery | +0.01 / -0.00 / -0.02 | +0.03 / 0.02 | 34% | +0.01 (0.13) |
| ALL8/IDX | discovery | +0.33 / +0.31 / +0.28 | +0.36 / 0.02 | 44% | +0.35 (1.42) |
| **REV2/IDX** | discovery | +0.30 / +0.29 / +0.29 | +0.31 / 0.01 | 22% | **+0.32 (2.27)** |
| REV2/IDX | validation | -0.05 / -0.06 / -0.07 | -0.04 / 0.01 | 25% | -0.02 (-0.18) |
| ALL8/CRYPTO-1d | discovery | +0.74 / +0.64 / +0.53 | +0.84 / 0.10 | 0.04 gross | +0.89 (1.26), NW t of net 1.03 |
| REV2/CRYPTO-1d | discovery | -0.05 / -0.05 / -0.06 | -0.04 / 0.00 | 0.00 gross | -0.05 (-0.57) |

Alpha per year at 1x (bp/day):
- REV2/IDX discovery: 2001 +0.6, 02 +0.5, 03 +0.1, 04 +0.4, 05 +0.5, 06 -0.1, 07 +0.6, 08 +0.3, 09 -0.2, 10 +0.0,
  11 +1.4, 12 -0.3.
- REV2/IDX validation: 2013 -0.3, 14 -0.3, 15 +0.6, 16 -0.3, 17 -0.3, 18 +0.2, 19 +0.3.
- ALL8/CRYPTO-1d: 2021 -0.9, 2022 +1.6, 2023 +1.5.

## Detections and the raw 5-bar forward return after each pattern (discovery; sign not applied)

| Pattern (book side) | FX n | FX fwd bp | IDX n | IDX fwd bp | Crypto n | Crypto fwd bp |
|---|---|---|---|---|---|---|
| HS (short) | 279 | -3.7 | 210 | **-81.7** | 17 | +257.9 |
| IHS (long) | 276 | +3.9 | 160 | +24.4 | 19 | -145.9 |
| BTOP (short) | 91 | -1.4 | 151 | +23.0 | 159 | -45.9 |
| BBOT (long) | 91 | +27.6 | 97 | -73.2 | 146 | -262.2 |
| TTOP (short) | 95 | +19.4 | 81 | -41.7 | 348 | **-202.2** |
| TBOT (long) | 158 | +13.9 | 135 | +32.0 | 284 | **+161.4** |
| RTOP (short) | 350 | -0.7 | 150 | -41.9 | 10 | -376.5 |
| RBOT (long) | 369 | +14.1 | 119 | -3.1 | 1 | -918.5 |

## Cost sensitivity
- Patterns are rare and held 5 bars, so costs are at most 0.1 bp/day of book at 1x. The 3x results barely differ from
  1x.
- **Costs do not decide anything here.** The question is only whether the patterns predict.

## Reading
- **Head-and-shoulders on world indices did predict in 2001-12, and did not afterwards.**
  - After an index HS, the next 5 days averaged -82 bp (210 cases); after an inverse HS, +24 bp. That is the
    chartist's reading, and close to LMW's finding of information in the pattern.
  - In 2013-19 the same book earned nothing. The pattern's information did not persist, as with the pivot reversal
    (R248).
- **On crypto daily bars, the 1.5% and 0.75% tolerances are too tight for HS and rectangles** (17 and 10 cases in
  three years). Broadening and triangle shapes dominate.
  - Triangle tops were followed by -202 bp over 5 days, and triangle bottoms by +161, which is the chartist's sign.
  - This is not market-adjusted. TTOP needs falling highs, so it is partly a statement about recent trend, and the
    ALL8 book's alpha is t 1.26.
  - Broadening bottoms went the wrong way (-262 bp). Taken together, the patterns do not add up to a book.
- **On forex, nothing:** forward moves after every pattern are within ±28 bp, and the books are flat.
- The descriptive table is a discovery-window description over 24 cells. It is not evidence for any one pattern.

## Not checked
- Other bandwidths, window lengths and tolerances (LMW's cross-validated bandwidth; wider tolerances for crypto).
- Double tops and bottoms (they need more than five extrema).
- Volume confirmation.
- Intraday bars.
- Market-adjusted forward returns per pattern.
- The forex/index holdout (not reached).
