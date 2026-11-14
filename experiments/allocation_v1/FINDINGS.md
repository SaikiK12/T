# R228 allocation_v1: NULL — static flow-book reweighting adds little in validation

Frozen spec `4627ac3649db6f7be4d02e1af3edcbee037a47e93fdbf66bb41a10b564656bd8`; runner `2e0bd37ec44587b3e152418e7925183d688278fbaf0d4550624125b0f3d854f9`. Run 2026-10-19. All input hashes, reconstructed day counts, source means and linear cost-tier checks passed before candidate scoring. Results are exploratory on already-viewed historical dates.

## Decision and practical implication

Thirty alternatives were evaluated: A, B and X2 plus 27 pairwise convex mixtures in 10% steps. Discovery alone chose **30% B / 70% X2**, against the discovery-selected single-book control X2. Its validation Sharpe gain is **0.0073**, below the frozen 0.15 minimum. The primary paired 30-day-block 95% interval is **[-0.1683, +0.1683]**. Both required improvement checks fail: verdict **NULL**.

The lower drawdown against full-size X2 mostly reflects lower risk. Using the discovery-fixed risk scale of 0.76854, the constant-scaled X2 control has a **21.11%** additive validation drawdown versus **23.29%** for the mixture. This validation window offers no compelling reason to add the allocation machinery.

## Selected candidate versus fixed control

| Split | Mixture mean, 1x bp/day | X2 mean, 1x bp/day | Mixture Sharpe | X2 Sharpe | Mixture / X2 additive DD |
|---|---:|---:|---:|---:|---:|
| Discovery 2021–2023 | 12.00 | 15.47 | 1.977 | 1.959 | 18.92% / 24.56% |
| Validation 2024–2025H1 | 15.88 | 19.68 | 1.688 | 1.681 | 23.29% / 27.47% |
| Known holdout 2025H2–2026Q3 | 35.15 | 42.51 | 1.675 | 1.494 | 43.44% / 61.59% |

The known holdout looks better on Sharpe and drawdown, but it was already viewed by the project and explicitly cannot rescue the failed validation screen. No weight was selected on validation or holdout.

The bootstrap used 5,000 paired circular-block replicates per block length (15,000 total). Ten-day and 60-day interval sensitivities were respectively [-0.1748,+0.1862] and [-0.1524,+0.1513], also spanning zero. They are conditional/descriptive intervals, not program-wide false-discovery guarantees.

## Cost stress: means available, daily stress paths unavailable

| Split | Mixture mean bp/day, 1x / 2x / 3x | X2 mean bp/day, 1x / 2x / 3x |
|---|---:|---:|
| Discovery | 12.00 / 9.30 / 6.61 | 15.47 / 11.85 / 8.24 |
| Validation | 15.88 / 10.66 / 5.44 | 19.68 / 12.75 / 5.82 |
| Known holdout | 35.15 / 30.58 / 26.00 | 42.51 / 36.34 / 30.17 |

The archive saves only 1x daily nets. Fixed positive sleeve weights permit exact 2x/3x split means from R217's cost-tier summaries, but not stressed daily Sharpe, drawdown, NW tests or bootstrap intervals. Those fields remain NA. An average daily fee was not invented to fill the missing paths.

## What this excludes, and what remains open

This closes this registered 30-alternative static grid on these three archived books as a promising validation improvement. It does not exclude all ensemble designs, context gates, partial execution or independent economic signals. A contains B's positioning component, and X2 reweights A's same cells: these are overlapping sources. A/X2 correlation is 0.972 in discovery and 0.975 in validation; B/X2 is 0.539 and 0.635. New names and weights do not create new information.

The arithmetic models segregated sleeves at fixed reference notional, no cross-netting benefit, no NAV rebalancing and no fill/capacity claim. Early positioning coverage is limited, inherited from R217. Historical PnL is not a current MEXC result. No forward lane or real-money action is justified by this null.

## Reproduce and artifacts

`python3 scripts/run_allocation.py --out /tmp/allocation_fresh_output` requires the frozen spec, exact runner/source hashes and a fresh output directory. Fifteen synthetic unit tests cover selection isolation, cost-path limits, data contracts, paired blocks and hash guards. See `results/candidates.csv` (270 candidate/split/cost rows), `selection.json`, `bootstrap.json`, `correlations.csv`, `risk_matched.csv`, `verdict.json` and `manifest.json`.

Trials: 30 (including three already-seen endpoints, disclosed computational count). Raw program trials before this lane: 9,471,756; afterward: 9,471,786. This is not a count of independent hypotheses. No earlier registry row, frozen lane or journal changed.
