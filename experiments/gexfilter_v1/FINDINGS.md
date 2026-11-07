# FINDINGS: gexfilter_v1 (R416). The S&P 500 dealer gamma adds nothing to BTC or ETH volatility forecasts once VIX and their own recent volatility are known

**Verdict: NULL for BTC and for ETH by the frozen rule.** 2 trials, gate 0 for the in-sample window; the holdout
(2025-07..2026-09) was unread for this family.

- **The run:** `run.log`, 2026-11-06 15:47 UTC, PREREG `85841cba6eed`, 8 inputs matched. One run.
- **Results:** `results/summary.json`, `results/rows_BTC.csv`, `results/rows_ETH.csv`.
- **Program trials:** read against 9,784,343 (`registry.program_trials()`).
- **Data:** SqueezeMetrics' free daily S&P 500 GEX (`docs/provenance/squeezemetrics.json`), with Binance hourly bars
  read from 2021 only.

## The signal's coefficient (rank of GEX over 252 days; c < 0 means low gamma predicts more volatility)

| Coin | Window | Days | c | NW t | Vol ratio, rank 0.9 vs 0.1 | R² with / without | Bar | Pass |
|---|---|---|---|---|---|---|---|---|
| BTC | IS 2021-01..2025-06 | 1,123 | −0.045 | −0.78 | 0.965 | 0.424 / 0.423 | t ≤ −2.5 | no |
| BTC | HOLD 2025-07..2026-09 | 314 | −0.105 | −1.30 | 0.920 | 0.310 / 0.307 | t ≤ −2.0 | no |
| ETH | IS | 1,123 | +0.010 | +0.21 | 1.008 | 0.486 / 0.486 | t ≤ −2.5 | no |
| ETH | HOLD | 314 | +0.000 | +0.00 | 1.000 | 0.271 / 0.271 | t ≤ −2.0 | no |

The signal adds at most 0.003 to R².

## Reported checks (not decided)

| Check | BTC IS | BTC HOLD | ETH IS | ETH HOLD |
|---|---|---|---|---|
| Signal one trading day later, t | +1.40 | −2.28 | +2.21 | −0.30 |
| GEX < 0 dummy instead of rank, t | −0.83 | −1.72 | −1.27 | −2.10 |
| Without VIX, t | −1.67 | −1.84 | −1.41 | −0.34 |
| Mean \|return\| over W, rank ≤ 0.2 / rest | 2.95% / 2.21% | 2.14% / 1.58% | 3.93% / 2.76% | 2.72% / 2.46% |

**S&P 500 self-check:** log |S&P 500 return on d'| on log VIX and the rank. c = −0.61, t −3.87 in IS; c = −0.26,
t −0.91 in HOLD.

## Reading
- **Low gamma days are wilder days for crypto, but GEX is not what says so.**
  - On days when the S&P 500 gamma ranked in its bottom fifth, BTC moved 2.95% on average over the next session, against 2.21%
    otherwise (IS).
  - That gap disappears once VIX and BTC's own last-day and last-week volatility are in the model. The forecast already
    knew those days were risky.
- **The equity mechanism itself shows up in-sample.**
  - On the S&P 500, low gamma predicted bigger moves beyond VIX in 2021-2025 (t −3.9).
  - It weakened in the holdout (t −0.9). It does not carry over to BTC or ETH.
- **The checks do not rescue it.**
  - The one-day-later signal flips sign between windows (BTC +1.40 then −2.28; ETH +2.21 then −0.30).
  - The negative-GEX dummy rests on 9 holdout days.
  - Picking a variant after reading them would be post hoc.
- **What follows.**
  - No GEX risk filter for the crypto books.
  - The free per-strike maps (QQQ, SPY, SPX) are now recorded twice per weekday from Cboe (`scripts/record_cboe_chain.py`, REC_CBOE). A
    levels test ("660 node" style) needs months of those maps, and is not this lane.
  - M300, the Deribit GEX test for crypto, keeps its own recording.

## Limits
- **SqueezeMetrics' GEX is its own estimate.** The dealer sign convention and method are theirs and are not replicated
  here.
- **Publication time is unstated.** The one-day-later signal was reported for that reason.
- **One market, one cycle:** 2021-2026, with 2020 reserved and unread.
- **No costs:** this is a volatility forecast, not a trade, so there is no 1x/2x/3x. A filter built on it would inherit
  the books' own costs.

## Note added after the run (2026-11-06)
`tests/test_run_gexfilter.py` was changed after the run, and this is disclosed as a deviation from the frozen inputs.
- **Why:** CI failed because one test read the gitignored `data/cboe/VIX.parquet`.
- **What changed:** that test now writes a synthetic VIX file in a temporary directory. No assertion changed, and the
  runner is unchanged.
- **What the run used:** the version frozen in the PREREG (sha256 `e6734527…`, commit 689bec1). It matched at run time
  (`run.log`: 8 inputs match).
- **Consequence:** a re-run would now fail the input check on that file. R416 is closed and is not re-run.
