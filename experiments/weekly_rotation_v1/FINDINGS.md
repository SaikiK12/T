# R230 weekly_rotation_v1: NULL — 96-rule search fails its train-selected validation test

Specification frozen at 2026-10-20 00:34:09 UTC, SHA-256 `0af8c351c90aba9b995b10d3070c488d24b2ba744eb85df1b3eb4600b586e9e4`. Runner SHA-256 `9084d30faa615d8e02a0b482f60d774537adc868c90cd13f95f23486cda7e8c3`. Commit `3027f68` preserves the specification, code and synthetic tests before this lane's first market calculation. No grid, selection score or decision criterion changed after outcomes.

## Verdict

**NULL.** Discovery selects 28-day momentum, the top three of six coins, a fixed positive 56-day BTC gate, and full weekly adjustment. It does not beat the discovery-risk-scaled passive control on validation:

- Sharpe **0.833 versus 1.105**, a change of **-0.272**, below the required +0.15.
- Compound drawdown **53.63% versus 36.13%**, failing the no-worse requirement.
- Paired mean excess **-0.129 bp/day**, with 30-day-block 95% interval **[-16.717,+19.032] bp/day**.
- The 96-member recentered max-statistic diagnostic gives **p=1.000** for the selected candidate.
- The positive 2x mean condition alone passes: **13.374 bp/day**. A positive market-exposed return is insufficient evidence of incremental skill.

The historical known holdout also loses, but is descriptive and cannot change the decision. Other candidates' validation or holdout performance cannot replace the discovery winner. This result does not nominate a forward bot.

## What was searched

Exactly **96** candidates: lookbacks 7/14/28/56 days × momentum/reversal × top 1/2/3 × fixed BTC56 gate off/on × execution adjustment 1/.5. Each portfolio holds spot and cash, with no borrowing, shorting or funding. Rank ties use fixed symbol order. Signals precede entry by a full daily bar. Accounts rebalance on Monday-labeled return days and initialize at each split's first return; between rebalances, units drift. Partial execution blends actual pretrade holdings with the unchanged target, rather than multiplying returns or assuming cheaper fills.

The existing R229 cache supplies 414 verified daily spot archives: BTC, ETH, SOL, XRP, DOGE and ADA, 2,099 dates per coin. This lane made **no network requests or new market-data downloads**. All source bytes and dependencies are checked before parsing. These six survivors and already-examined calendar dates provide an exploratory adaptation, not the original C14 point-in-time 50-coin long/short study.

Discovery-only selection maximizes unscaled 2x net Sharpe; its winning score is **0.871484**. Discovery 1x sample volatilities fix capital scales: candidate **1.0**, passive **0.648320**. Neither account is levered up. Targets, fees and drift are resimulated under these scales, rather than scaling finished PnL. Discovery realized annualized risks are 45.26% / 44.42%; validation risks are **62.36% / 47.43%**. Training-based scaling does not guarantee equal future risk, and the candidate's larger validation drawdown accompanies higher realized risk.

## Selected candidate and scaled passive, 1x

| Period | Days | Mean bp/day, candidate / control | Sharpe, candidate / control | Compound DD, candidate / control |
|---|---:|---:|---:|---:|
| Discovery 2022–2023 | 730 | 11.398 / 2.377 | 0.919 / 0.195 | 45.85% / 53.83% |
| Validation 2024–2025H1 | 547 | 14.229 / 14.357 | 0.833 / 1.105 | 53.63% / 36.13% |
| Known holdout 2025H2–2026Q3 | 457 | -4.811 / -1.718 | -0.435 / -0.158 | 56.84% / 53.12% |

Validation ending NAV from cash 1 is **1.63442** for the candidate versus **1.85514** for the control. Mean invested exposure is 69.29% versus 65.27%, with much more turnover: **38.58 versus 2.65** marked-NAV units over the split. Known-holdout NAV is **0.72419 versus 0.83771**. Arithmetic mean, compounded return and Sharpe measure different things; the saved metrics retain all three.

## Complete cost stress

One-way costs are assumed 12/24/36 bp at 1x/2x/3x, unchanged from R229, not measured fills or account-specific fees. Each path starts from cash and charges drifted-holding transactions plus complete final liquidation.

| Period | Candidate mean bp/day, 1x / 2x / 3x | Candidate compound DD, 1x / 2x / 3x |
|---|---:|---:|
| Discovery | 11.398 / 10.807 / 10.218 | 45.85% / 46.56% / 47.27% |
| Validation | 14.229 / 13.374 / 12.520 | 53.63% / 54.34% / 55.04% |
| Known holdout | -4.811 / -5.462 / -6.113 | 56.84% / 57.77% / 58.69% |

All 96 candidates and their own discovery-scaled passive controls are saved for every split/tier: **1,728 scored accounts and 998,784 daily net-return entries**. The full selected/control paths contain 10,404 daily account rows with units, NAV/cash, gross PnL, costs, turnover and exposure. Preliminary unscaled discovery runs are separately used only for selection and capital scales.

## Search uncertainty and limits

The primary diagnostic resamples shared circular 30-day blocks across all 96 paired validation differences, centering every column and using its fixed original NW(10) mean SE. It compares the selected observed statistic to each resample's maximum over the full family. This is an approximate family-aware diagnostic, not a proof of error control or a correction for the project's prior millions of correlated trials. All 15,000 maximum-statistic replicates are retained across the 30/10/60-day analyses. The 10- and 60-day selected paired-mean intervals are **[-15.517,+16.046]** and **[-17.628,+20.901] bp/day**; the corresponding family diagnostic p-values are also 1.000.

The primary sources motivate questions rather than establish these rules' profitability. The [April 2019 Liu–Tsyvinski–Wu manuscript](https://economics.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf) uses weekly cross-sectional sorts and reports momentum at one through four weeks; it does not justify a universal four-week reversal. Our 56-day extension, reversed sign, BTC gate, concentration and partial adjustment are additional counted hypotheses. [White's 2000 paper](https://doi.org/10.1111/1468-0262.00152) motivates accounting for the searched family; our fixed-SE circular-block implementation is explicitly an adaptation.

This closes the frozen train-selected 96-rule rotation policy on this sample. It does not falsify all momentum, settle a survivor-free C14 replication, or establish anything about futures funding, short execution, MEXC capacity or actual latency. No validation reranking, alternative weekday, new gate or cheaper cost assumption is used to rescue the result. A further changed rule needs a new lane and trial count, and fresh confirmation would require future observations collected after freezing it.

## Verification and reproduction

All **205 repository tests pass**, including 18 new rotation tests. Before freeze, an independent reviewer matched all 96 causal rank constructions, 96 synthetic accounts/12,192 daily rows against a separate piecewise-linear fee solver (maximum discrepancy 3.11e-15), and 117 scalar family-bootstrap draws (maximum discrepancy 1.78e-15). The reviewer caught an undefined-Sharpe decision path, which was corrected and regression-tested before freeze.

An independent market implementation confirmed all 96 discovery scores, capital scales and validation paired paths, plus all 10,404 selected/control account rows (maximum absolute account discrepancy 3.38e-14). It reconstructed all 15,000 bootstrap maxima within 1.31e-13. A fresh-directory runner invocation reproduced all seven artifacts byte for byte, including the compressed NPZ and manifest. These calculations used separately written ranking, calendar-accounting and piecewise-linear fee code, rather than substituting the runner's account implementation.

The run manifest pins the exact code/spec/input snapshot and all output bytes. `search_returns.npz` stores only numeric day-by-candidate net-return arrays and bootstrap maxima; read with `allow_pickle=False`. Its columns follow the manifest's fixed grid order. No raw ZIP archive enters Git. Reproduce offline with the original cache present using `python3 scripts/run_weekly_rotation.py --out /tmp/rotation_fresh_results`; the destination must not exist. Existing outputs cannot be overwritten.

Trials: **96**, including every sign, gate and execution choice. Program raw total before R230: **9,471,788**; after R230: **9,471,884**. Raw trial counts are bookkeeping across correlated research choices, not independent hypothesis counts. Frozen older specifications, findings and append-only journals remain intact.
