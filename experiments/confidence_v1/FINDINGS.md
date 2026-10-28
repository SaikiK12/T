# R331 completed by R342 — NULL_INACTIVE for the preselected confidence policy

**The frozen selection chose the training-frequency prior. It opened no validation
trade at any cost tier. Zero PnL is inactivity, not a profitable edge.** All six
learned variants, old references, controls and dependent-null failures remain.
Actual executable expected net return and calibrated market uncertainty are
UNKNOWN; no new prospective day or activation is claimed.

R331's original code/specification and committed training/calibration were resumed
unchanged. R342 freeze `097a107` preceded selection; selection commit `94e7ce2`
preceded any R331 validation computation; complete evaluation is `e0de8f5`.
This is Gate0 on dates/prices/labels already seen by the project, not a fresh
project holdout. No validation winner, threshold, fee, asset or size was substituted.

## Recovered inputs and chronology

All41pinned input hashes verify.37missing local files were recovered byte-exactly
from another existing workspace,5,590,818bytes copied locally,0HTTP/downloads.
No source was refetched or replaced. Full package/code/committed-model identities
verify before/after each stage. The original116financial-known training events
have class counts16/26/74; calibration has55labels with counts14/8/33.

November–December2025 selection has46eligible labels and no missing candidate.
Mean multiclass NLL is0.931811 for frequency,0.936200 ridge raw,0.948714 ridge
temperature,0.955500 ridge identity-Dirichlet,0.985933 tree temperature,1.005447
tree raw and1.011435 tree identity-Dirichlet. The original lowest-NLL rule and
1e-6 simplicity tie criterion were used, with no selection by PnL.

January–September2026 validation retains1,092coin/day records,178qualified events,
0missing feature vectors and2events beyond the registered training-scale OOD
limit. Each of39account/cost cells retains273calendar days and complete PROXY
accounting. This is not certified complete execution/funding cash evidence.

## Every validation account at fixed costs

Amounts are historical close/funding-notional **proxy USDT PnL**, rounded here;
exact amounts and full events remain in evaluation artifacts. Each alternative
has the SAME10,000USDT account across BTC/ETH/SOL/WIF,500entry notional per coin,
common3x shadow admission and no leverage-up. Single lumped execution charge is
8bp/side at1x,16bp at2x and24bp at3x; no additive spread double count.

| Registered policy | Closed trades | 1x | 2x | 3x |
|---|---:|---:|---:|---:|
| **Selected frequency** | **0** | **0.00** | **0.00** | **0.00** |
| Ridge raw | 4 | +23.52 | +20.30 | +17.08 |
| Ridge temperature | 0 | 0.00 | 0.00 | 0.00 |
| Ridge identity-Dirichlet | 7 | +54.64 | +48.99 | +43.35 |
| Tree raw | 0 | 0.00 | 0.00 | 0.00 |
| Tree temperature | 0 | 0.00 | 0.00 | 0.00 |
| Tree identity-Dirichlet | 0 | 0.00 | 0.00 | 0.00 |
| Original R330 conditional | 0 | 0.00 | 0.00 | 0.00 |
| Original R330 frequency | 0 | 0.00 | 0.00 | 0.00 |
| Always break | 178 | +53.86 | -88.73 | -231.32 |
| Always rebound | 178 | -339.03 | -481.62 | -624.21 |
| Long control | 178 | +93.23 | -49.36 | -191.95 |
| Cash | 0 | 0.00 | 0.00 | 0.00 |

The two positive learned-policy rows are UNSELECTED and have only4/7trades. They
are retained as exact tested scopes, not promoted as expected-return evidence or
used to rescue the selector. All other inactive rows also stay. Selection-period
economic results remain in the same artifact: raw ridge had3trades and+20.39 at2x,
raw tree1trade and-3.21; those PnLs did not change the NLL selection criterion.

## Probability results and uncertainty

All six learned variants and new frequency score the same178validation labels.
Paired changes below are relative to new frequency; negative is descriptively
better. They are not p-values, confidence intervals or calibrated market skill.

| Model | NLL | Paired NLL change | Brier |
|---|---:|---:|---:|
| Selected frequency | 1.026822 | 0.000000 | 0.607241 |
| Ridge raw | 1.090639 | +0.063817 | 0.621387 |
| Ridge temperature | 1.012785 | -0.014037 | 0.599827 |
| Ridge identity-Dirichlet | 1.017787 | -0.009035 | 0.601521 |
| Tree raw | 1.039460 | +0.012638 | 0.604525 |
| Tree temperature | 1.004515 | -0.022308 | 0.593353 |
| Tree identity-Dirichlet | 0.997443 | -0.029379 | 0.594782 |

Original R330 conditional probabilities have177available labels; their paired
NLL change on their OWN common subset is+0.002643, Brier change+0.001168. Do not
compare available-case means as if they use identical labels. Fixed five-bin
per-class reliability retains empty bins, counts, days and14day blocks; market
intervals remain null. Improved validation rows cannot replace the model frozen
before validation.

The100dependent/no-information synthetic paths retain62SCORED and38UNAVAILABLE
(sparse training classes, no redraw). Among scored paths, frequency is selected36
times and a learned model26times. This diagnoses selection/fit behavior only;
it is not a market false-positive rate, FWER calibration, valid p-value or repair
of R321's inference limitations. Descriptive14day calendar shifts also remain
descriptive, not exchangeable p-values.

## Independent audit, reproduction and limits

The unchanged independent checker PASS reconstructs395new OHLC feature vectors,
1,344base/calibrated probability vectors, selection on the correct window,
78unique shared accounts and6,183financial events, matching2,072old opportunity
identities. Cash/fill costs/source funding use its separate Fraction accounting;
2,061closed-position repetitions across windows/costs are not2,061new trades.
It imports no production feature/learner/calibrator/selector/financial function.

Seven relevant existing tests PASS before selection. Both actual phases reproduce
all9sealed output files byte for byte in fresh directories; the independent audit
also byte-reproduces. R342 stores exact output hashes/local recovery and audit.
Eightadapter calls per window verify then deduplicate105control/cost repetitions;
all78distinct window/policy/cost cells remain, not a selected positive subset.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_confidence.py --stage select --out /fresh/selection
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/run_confidence.py --stage evaluate --out /fresh/evaluation
python scripts/check_confidence.py /fresh/evaluation
```

Evaluation uses the already committed canonical R331 selection. A fresh clone
needs the pinned private raw market caches; a future API fetch is not promised to
recreate them. Local copying did not consume or reset any download allowance.

The final registered screen is **NULL_INACTIVE**. R331's fixed generic artifact
verdict PARTIAL is unchanged; R342 records NULL for that exact screen. Fourteen
distinct variants were already reserved in R331; R342 adds0, program9,479,013
unchanged. Historical7757requests/reported229.85MiB and both closed source/current
budgets stay unchanged. R310/R311/old provenance, Claude R337/forward and M412's
claimed queue row stay intact. Current executable quotes/depth, owner fees,
fair/index funding, fills/sessions, margin, capacity and matched realized risk
remain unverified. No orders, money, secrets, new dataset/weights, merge/closure,
new paper day, activation or permanent/scheduled-execution promise.
