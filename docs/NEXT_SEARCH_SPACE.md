# Next brute-force search space (2026-10-19)

Written by a research subagent after a read-only pass over the repo (MAP, CLAIMS, registry, lab/, the atlas and flow
scripts and PREREGs) and filed by the lab. No statistic was computed. Nothing here is registered; a round built from
it needs its own frozen PREREG.

## What is spent
9.47M program trials, 8.3M of them context-lift cells (atlas_ctx). Combining already-searched cells has been tried
three ways, and none paid net of costs:
- additive merge (R186, R187);
- pair slice books (R201, R204);
- AND conjunctions in the daily hypermine search (R182).

New information is the lever left.

| Family | Searched | Outcome |
|---|---|---|
| Price, oscillators, structure (284 views; 1/4/24 h bars; horizons 1-72 h) | atlas_v1 R185 | reversal replicates raw; excess weak; below costs |
| Clocks, sessions | 6 views, 6 session groups | null alone |
| Market state (btc_ret, dispersion of returns, breadth), crowding | atlas_ctx R192 | timing only; crowding replicates |
| Flow levels (OI change, positioning levels, taker, book) | 37 views; flow72 books R196-R198 | in-sample +42.6%/yr; holdout not confirmed |
| Coin's own 4 h / 24 h state as context | atlas_mtf R195 | replicates as context; no agreement score |
| Books, sizing | 72 h slices, hedges, limit entries, merge, day stops | unit size everywhere |

## Not searched (checked in code)
- **Cross-coin:** no per-coin beta, residual, catch-up or lead-lag against BTC or ETH; no clusters.
- **Positioning changes:** only OI changes exist. There are no differences or acceleration of top_ls, crowd_ls,
  top_vs_crowd or taker.
- **Trade count:** `count` is loaded and unused, so average trade size has never been tried.
- **Agreement and dispersion:** no sign agreement across lookback windows; no cross-sectional dispersion of positioning.
- **Horizon:** weekly cross-sectional momentum (C14) has never been run.

## Proposed grammar
| Block | Views | Excess trials | Data from |
|---|---|---|---|
| A cross-coin: residual r - beta x r_BTC/ETH (n 1/4/24 h); cluster-relative return (monthly correlation clusters, k 5/10); catch-up beta x r_ref(L) - r(L), L 1-24 h; own-history percentiles | 54 | 1,900 | 2021 |
| B positioning change: d1/d4/d24 and acceleration of top_ls, crowd_ls, top_vs_crowd, whale_vs_top, topacct_vs_crowd; xs8 / z168 / z720 | 60 | 2,250 | 2023 only (coverage) |
| C trade size: log(quote volume / count), log count, per-trade signed flow; 6/24/72 h means | 18 | 675 | 2021 |
| D multi-timeframe sign agreement of ret, ema_cross, taker, volz, top_vs_crowd, funding over {1,4,24}, {4,24,72}, {1,4,24,72} h | 36 | 900 | 2021 |
| E typed pair interactions (positioning x funding, OI change x price, taker x volatility, ...), terciles, interaction contrast | 36 pairs | 1,620 | 2021 |
| F dispersion regime of ret, taker, top_vs_crowd as context (cut to one context: about 29k) | 3 | 85,875 | 2021 |
| G confidence multipliers on three fixed books (see `SIZING_EVIDENCE.md`) | 24 runs | 24 | - |

About 93k trials if only excess returns are screened. That is 1% of the program.

## Staged plan
- **Freeze:** freeze the grammar first.
- **Discovery:** 2021-2023 (positioning blocks: 2023 only, flagged underpowered), with at least 4 circular placebo
  shifts and FDR ≤ 0.10.
- **Validation:** 2024 to 2025-06, using the atlas_ctx replication rule.
- **Book test:** replicated cells become 72 h slice books at 1x/2x/3x.
- **Holdout:** at most three candidates on 2025-07..2026-09. That is unread for these families but is the calendar of
  the spent books.
- **Forward:** a MEXC paper test from the freeze date.
- **Multiplicity:** White's Reality Check or Hansen's SPA for each family's best candidate.
- **Costs:** report MEXC's 8 bp API taker (unconfirmed) alongside the lab's tiers.

**Start with:** A3 catch-up, C trade size and F dispersion, which have a mechanism and no prior test. Exclude BTC and
ETH from the screened set (report them as a group) and add a rank 51-150 tier as a grouping.
