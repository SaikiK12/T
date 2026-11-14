# FINDINGS: pairs_v1 (R250). Pairs trading on crypto perps: distance and Engle-Granger selection

**Verdict: NULL.** None of the 4 books passed discovery (2021-2023). Gross was close to zero in every book, from -1.6
to +2.5 bp/day. Validation was not computed and the holdout was not read.

- **Registry row:** R250 (trials 4). Program trials after it: 9,471,991.
- **Gate:** 0.
- **Reproduce:** prereg sha a0dc3444, frozen in commit f850cf3 before the run. Run `python scripts/run_pairs.py`
  (about 30 seconds).
- **Origin:** queue M045 (the classic quant method the owner's brute-force ask names).

## Numbers (discovery 2021-01..2023-12; 30-day formation, 7-day trading, K = 10, entry |z| > 2, exit at 0)

| Book | Net bp/day 1x / 2x / 3x | NW t (1x) | Gross / cost (1x) | Gross exposure | Trades | Mean hours held | Exit: reverted / week end / eligibility |
|---|---|---|---|---|---|---|---|
| DIST/TOP20 | -2.6 / -3.8 / -5.1 | -1.25 | -1.4 / 1.2 | 0.39 | 1,797 | 103 | 22% / 78% / 0% |
| DIST/TOP50 | +0.7 / -1.0 / -2.8 | 0.37 | +2.5 / 1.8 | 0.41 | 2,125 | 89 | 27% / 67% / 6% |
| EG/TOP20 | -1.5 / -2.6 / -3.7 | -0.67 | -0.3 / 1.1 | 0.31 | 1,529 | 86 | 30% / 70% / 1% |
| EG/TOP50 | -3.6 / -5.7 / -7.7 | -1.06 | -1.6 / 2.0 | 0.42 | 2,391 | 77 | 35% / 59% / 7% |

- **EG pairs selected per week:** 7.5 on average in TOP20 (fewer than 10 passed DF < -3.34) and 10.0 in TOP50.
- **Per year at 1x (bp/day):**
  - DIST/TOP20: 2021 -1.1, 2022 -4.1, 2023 -2.7.
  - DIST/TOP50: +6.9, -7.1, +2.4.
  - EG/TOP20: -2.2, -2.6, +0.5.
  - EG/TOP50: -5.5, -3.6, -1.7.

## Cost sensitivity
- Two legs, but a pair opens about twice a week and is held 3-4 days, so costs are 1.1-2.0 bp/day at 1x.
- Cost is not what kills the books. Gross is near zero, so no book is positive at 2x.

## Reading
- **The spreads do not revert.** Most trades end at the end of the week with the spread still open: 59-78% of trades.
  - Only 22-35% close by crossing zero.
  - A 30-day window of hourly crypto prices makes many pairs look cointegrated, because coins share one dominant
    factor. The idiosyncratic part then drifts instead of mean-reverting at a 1-7 day horizon.
- **The Engle-Granger filter adds nothing over the distance method.** EG/TOP50, the 10 most significant DF statistics
  among about 1,200 pairs a week, has the worst gross (-1.6). A Dickey-Fuller t below -3.34 among 1,225 tested pairs
  is expected by chance, so the selection is close to a multiple-testing artefact.
- **This agrees with the literature for crypto.** Pairs profits found at minute frequency shrink at hourly and daily
  frequency (Fil and Kristoufek 2020). It also fits R238/R245: idiosyncratic one-week moves in crypto continue rather
  than revert.

## Not checked
- Minute-frequency pairs (needs 1-minute bars).
- Longer formation (90-180 days) or sector-restricted pairs (L1s, memes): M183/M046 cluster ideas.
- Johansen baskets of 3+ coins.
- Stop-losses on diverging spreads.
- Validation and the holdout.
