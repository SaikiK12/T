# R232 rebalancing_v1: NULL — fixed rebalance cadences do not clear the buy-and-hold comparison

Frozen 2026-10-20 at 00:41:54 UTC before reading this lane's cached prices. Specification SHA-256 `96f4aa34338eeaacfaae618df0ac7f353a074761e3ea7a5e40f14f8578c79a33`; runner SHA-256 `4251e5d2c179da5ffa29c538b082a29745b6b2591ec11c57098022a36c73bf27`. No parameter changed after outcomes.

## Result

**NULL.** Discovery selects monthly equal-weight rebalancing. Its validation improvement over the initial-identical fixed-unit basket is positive in this historical sample, but misses both the frozen Sharpe threshold and the paired uncertainty test. The mechanism was tested despite weak prior evidence; it was not rejected solely because a source used different assumptions.

After symmetric discovery-only risk scaling, validation gives:

- Selected monthly Sharpe **1.053**, buy-and-hold **0.965**: gain **0.088**, below the required +0.15.
- Paired mean net improvement **+0.965 bp/day**, with 30-day-block 95% interval **[-2.350,+4.764] bp/day**. Its lower endpoint is below zero.
- Selected 2x mean **19.846 bp/day**, which passes the positive-mean requirement.
- Selected 1x compound drawdown **49.49%**, versus buy-and-hold **50.63%**, which passes the no-worse requirement.

Both required failures remain failures. No cadence substitution, alternative cost tier, unscaled result or known-holdout observation rescues the primary. The large exposure and drawdowns also make a positive arithmetic mean a poor substitute for evidence of a safe live strategy.

## Method tested and source provenance

Initial holdings are equal dollars in the identical six surviving Binance spot coins, BTC/ETH/SOL/XRP/DOGE/ADA. Daily, UTC-Monday weekly and UTC-month-first monthly policies reset to equal post-cost weights on their fixed calendar. The comparator buys the same initial basket once and retains its **units and cash**, letting weights drift until the split's final liquidation. It is not reset at month/year boundaries.

Every account starts from cash 1 at its split, pays initial entry and final exit costs, and charges intermediate rebalances against drifted holdings. The exact self-financing solver accounts for post-cost target weights, with no leverage, shorting, funding or interest. Fixed weights/calendar are known before execution: the return ending at C[i] trades at C[i-1], weekly before Monday's return and monthly before the month's first return. There is no newly observed price signal being filled at its own close.

The public [primary SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3982120) for Hanicova and Vojtko's *Rebalancing Premium in Cryptocurrencies* was retrieved successfully. It reports written December 10, 2021, posted December 14 and revised December 20; its abstract describes a 27-coin study. Obtained HTML SHA-256 `797efecbd6be563f564b5b7127a5e7250465cb8dff38c8240dc1245d54e94b5f`. The full paper's executable results were not independently replicated.

The [public Quantpedia profile](https://quantpedia.com/strategies/rebalancing-premium-in-cryptocurrencies/) was also retrieved, HTML SHA-256 `4418e119a07887ca0e77ed31900a8406ea7b79f7604df2d0524e7b6abc082a8d`. It explicitly labels transaction costs unreported and its 100%-long/70%-short illustration an in-sample short-weight comparison. This lane is a long-only spot adaptation with explicit modeled costs, not that hedge, a dollar-neutral spread, a broader point-in-time universe, or confirmation of a source rating. The original long-short mechanism remains outside this test.

Monthly rebalancing already appears as R229's passive comparator. Its prior use is disclosed; its relative performance against fixed-unit buy-and-hold was the unresolved question. The two other schedules are fixed before outcomes, and no optimized weekday or extra frequency was searched. The trial count is three policy comparisons, including this reused monthly policy relative to the new comparator, rather than a claim of three independently invented signals.

## Discovery selection and risk controls

Discovery 2x Sharpe is **0.137** daily, **0.170** weekly and **0.192** monthly. The highest score selects monthly; exact ties would favor monthly, then weekly, then daily. Selection uses discovery only. All unselected paths remain saved diagnostics.

From discovery 1x sample standard deviations, capital fractions are **0.9582598187** for selected monthly and **1.0** for buy-and-hold. Each is at most one; the higher-risk account is reduced rather than levering up the lower-risk account. Re-simulation applies those same fractions to every future split and cost tier, with complete new fee paths.

This fixes initial/target capital fractions rather than future realized risk. Discovery annualized volatility is **66.708%** selected versus **66.902%** buy-and-hold after scaling. Validation volatility is **69.048%** versus **71.702%**, and mean invested exposure **95.874%** versus **100%**. The residual validation risk mismatch is reported, not removed with a scale fitted to the future. A scaled buy-and-hold account would retain fixed cash rather than continuously restoring its initial investment fraction.

## Primary pair, 1x costs

| Period | Days | Mean bp/day, monthly / buy-and-hold | Sharpe, monthly / buy-and-hold | Compound DD, monthly / buy-and-hold | Ending NAV, monthly / buy-and-hold |
|---|---:|---:|---:|---:|---:|
| Discovery 2022–2023 | 730 | 3.572 / 0.076 | 0.195 / 0.004 | 70.84% / 71.85% | 0.82955 / 0.64111 |
| Validation 2024–2025H1 | 547 | 19.929 / 18.965 | 1.053 / 0.965 | 49.49% / 50.63% | 2.08900 / 1.92630 |
| Known holdout 2025H2–2026Q3 | 457 | -2.144 / -2.262 | -0.133 / -0.135 | 68.33% / 69.90% | 0.73017 / 0.71393 |

Monthly here means the selected risk-scaled account. The discovery mean is positive while ending NAV is below one: arithmetic average return and compound profit differ at this volatility. Both accounts lose capital in discovery and the named holdout, despite the sizable validation advance. All these historical dates were already viewed by the project; none provides fresh confirmation.

At unscaled validation 1x, daily/weekly/monthly Sharpe is 1.001/1.032/1.047, versus buy-and-hold 0.965. Their mean returns are 19.493/20.184/20.643 bp/day, versus 18.965. These remain diagnostics, not a new selection pass or evidence that a differently chosen cadence cleared the frozen screen.

## Complete cost stress and mechanism decomposition

The 1x/2x/3x models charge **12/24/36 bp one way**, the same frozen assumption as R229. These are modeled fee/slippage costs, not live account-specific fees, capacity estimates or recorded fills.

| Period | Selected scaled mean bp/day, 1x / 2x / 3x | Selected scaled compound DD, 1x / 2x / 3x |
|---|---:|---:|
| Discovery | 3.572 / 3.503 / 3.433 | 70.84% / 70.88% / 70.92% |
| Validation | 19.929 / 19.846 / 19.763 | 49.49% / 49.51% / 49.53% |
| Known holdout | -2.144 / -2.215 / -2.286 | 68.33% / 68.35% / 68.37% |

For the raw **unscaled** monthly-versus-buy-and-hold validation pair, net improvement decomposes as gross difference minus extra transaction cost:

| Cost tier | Gross improvement bp/day | Extra costs bp/day | Net improvement bp/day |
|---|---:|---:|---:|
| 1x | 1.72029 | 0.04148 | 1.67881 |
| 2x | 1.71991 | 0.08294 | 1.63697 |
| 3x | 1.71954 | 0.12440 | 1.59514 |

The rebalance mechanism adds cost relative to untouched units; its historical gross contribution more than offsets that cost here. Daily rebalancing costs more: at validation 1x mean cost is 0.23241 bp/day daily, 0.12417 weekly, 0.08527 monthly and 0.04380 buy-and-hold. This does not establish statistically reliable incremental return. Each contribution uses its own account's preceding NAV; the difference is not a common-notional tradable long-short PnL or an identified market-neutral alpha.

## Verification and retained evidence

All **54 accounts** and **31,212 daily rows** are retained with holdings, execution flags, net/gross/cost components, cash, NAV, turnover and exposure. The complete daily and paired tables use deterministic gzip CSV, totaling **2.02 MB** compressed; no raw market archive is copied into Git. Small metrics/decomposition/verdict and source/output manifests are also retained.

Every one of the **5,202 unscaled monthly daily rows** reproduces frozen R229's passive accounts **exactly** across all splits and all cost tiers, including fees, units, NAV and cash. A distinct analytic piecewise-linear transaction-cost solver reconstructed all 54 accounts and 31,212 rows: maximum absolute discrepancy **7.29e-14**. It independently recomputed the selected cadence and discovery scales from saved net returns. A fresh-directory rerun reproduced all six result artifacts byte for byte, including compressed CSV bytes and the manifest; all output SHA-256 values verify.

The full suite on this branch passes **223 tests** in 67.547 seconds, including eighteen new synthetic tests. They cover fixed-unit holdings, pretrade drift, calendar timing, off-cadence initialization, exact fees and exits, no borrowing, a reversal example where rebalancing can help, monthly equivalence, no future-price leakage, discovery-only selection/scaling, ties, deterministic compression/bootstrap and source/output guards.

A separate read-only reviewer independently checked the frozen specification against code, all 54 saved calendars and account metrics, discovery selection/scales, all three bootstrap intervals with a separately generated RNG index matrix, and the four decision gates. These reproduced exactly. Direct source-ZIP close endpoints and closed-form buy-and-hold units/NAV checked all 18 raw/matched buy-and-hold accounts, maximum discrepancy **4.45e-16**. No material specification mismatch was found; the reviewer also confirmed that realized risk differs after training-fixed scaling.

The primary circular 30-day bootstrap has 5,000 replicates. Nondecisive 10/60-day intervals are **[-2.417,+4.850]** and **[-1.798,+4.163] bp/day**; both include zero. Fixed seeds are `20261020232+block`. The starting branch already contains **9,471,884 raw program trials**, before separately registered parallel additions. This experiment adds three policy comparisons; its conditional intervals are not a program-wide multiplicity correction.

Reproduce offline with the original verified R229 cache present:

```sh
python3 scripts/run_rebalancing.py --out /tmp/rebalancing_fresh_results
```

The output directory must be fresh and empty. The runner verifies its frozen specification/dependencies and original R229 source snapshot before parsing values; it performs no network access. `results/run_manifest.json` preserves exact executable/source/output hashes, selection scores and software versions. Frozen R229/R230/R231 specifications, previous results and append-only journals are untouched.

## What remains open

The bounded comparison of these three fixed long-only cadences versus identical-initial fixed units on this six-surviving-coin snapshot is now tested and NULL under its registered decision. The source's long-short construction, full universe, point-in-time eligibility, futures funding and prospective behavior remain untested. Traded closes with assumed costs provide neither execution-capacity evidence nor a live trading strategy. The positive historical paired mean can inform a separately registered hypothesis; it cannot change this experiment's frozen verdict.
