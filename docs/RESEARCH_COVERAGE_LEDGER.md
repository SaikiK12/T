# Research coverage: tested cells, open mechanisms and data dependencies

Read-only coverage audit dated 2026-10-19, after R226; R228 is specified separately below.
This ledger reports existing evidence and specifications. It computes no new market result.
“Closed” means do not repeat the tested rule unchanged; it does not falsify every rule in its broad family.
Calendar dates examined by prior research are spent for program-level confirmation, even for a new feature.

## Exact tested rules to exclude

| Mechanism | Tested scope and evidence | Boundary of the conclusion |
|---|---|---|
| Indicator aggregation | R186: additive cell means, hysteresis and registered parameter grid; R187: episode statistics, shorter training and session pooling. [R186](../experiments/merge_v1/FINDINGS.md), [R187](../experiments/merge_v2/FINDINGS.md) | Those combiners did not establish a net edge. They are not tests of every portfolio allocation or interaction. |
| Context-pair portfolios | R201: selected replicated pairs as slice books; R204: slow 12–24 h pairs on the holdout. [R201](../experiments/ctxslice_v1/FINDINGS.md), [R204](../experiments/ctxslice_v2/FINDINGS.md) | Do not repackage the failed pair pack. Gating an existing flow portfolio is a different construction. |
| Flow levels | Three fixed 72 h cells, entry-only and overlapping-slice constructions, plus holdout. [R196](../experiments/flow72_v1/FINDINGS.md), [R197](../experiments/flow72_v2/FINDINGS.md), [R198](../experiments/flow72_holdout/FINDINGS.md) | Primary combined holdout did not confirm; selected component results cannot become fresh confirmation. |
| Positioning decomposition | R211 splits top-vs-crowd; R212 tests contrarian top-account headcount. [R211](../experiments/posfam_v1/FINDINGS.md), [R212](../experiments/posfam_v2/FINDINGS.md) | Added headcounts failed validation. These are level/component tests, not positioning-impulse tests. |
| Slow altcoin factors | R222: low beta, residual/ordinary skip-month momentum, hourly MAX in both directions, premium residualized on funding. [Specification](../experiments/xsalt_v1/PREREG.md), [findings](../experiments/xsalt_v1/FINDINGS.md) | All six failed discovery; later portfolio stages were not run. This is not all slow momentum. |
| Big-coin lead-lag | R219: five specified lead-lag/catch-up books at 1/4/24 h holds. [Findings](../experiments/seesaw_v1/FINDINGS.md) | Standalone taker books failed discovery. An entry overlay was proposed, not tested. |
| Unsigned trade activity | R226: 24 h mean print-size level/change and count surge, each in both directions, 72 h books. [Specification](../experiments/tradesize_v1/PREREG.md), [findings](../experiments/tradesize_v1/FINDINGS.md) | Close these six cells. Signed flow and other windows were not tested; extra unsigned windows have weak priority. |
| Funding carry | Trailing settled-funding rule and one holdout: R190/R191. [R190](../experiments/carry_v1/FINDINGS.md), [R191](../experiments/carry_holdout/FINDINGS.md) | Confirmed by its original holdout rule, economically small; exact spot/perp execution remains a limitation. |
| Settlement capture / crash timing | R223 extreme last-settled-rate capture; R207 high-carry BTC crash rule. [R223](../experiments/settle_v1/FINDINGS.md), [R207](../experiments/carrycrash_v1/FINDINGS.md) | Both specified rules failed; rate revisions and basis-triggered carry are different questions. |
| Sizing and stops | R217: X1/X2 agreement and four time-series overlays; R208: registered daily stops. [R217](../experiments/sizing_v1/FINDINGS.md), [R208](../experiments/daylimit_v1/FINDINGS.md) | No sizing rule passed R217's bar; own-profit/Kelly scaling and daily stops lacked support. A risk reduction alone is not alpha. |
| Other external claims | Gate positioning transfer, liquidation fade, intraday momentum, DVOL timing, Coinbase premium, new-listing short. [Scoreboard](EDGE_SCOREBOARD.md) and each linked lane | Preserve each rule's venue, period, frequency and stopping stage. Do not generalize the null to every new data mechanism. |

## Important correction: weekly momentum is not R222's MOM control

R222's label “MOM (30 d)” denotes a **30-day holding period**. Its signal sums daily returns
from `d-179` through `d-30`: a 150-day formation window skipping the most recent 30 days
([frozen definition](../experiments/xsalt_v1/PREREG.md)). Calling it a 30-day-lookback test is incorrect.
[C14](CLAIMS.md) instead proposes a 7-day-lookback/7-day-hold portfolio and 28-day reversal.
The atlas includes weekly return features but target horizons only through 72 hours
([R185 specification](../experiments/atlas_v1/PREREG.md)); it does not close C14's weekly portfolio.

## Genuine open questions, with dependencies

| Question | Why existing results do not settle it | Required next input or control |
|---|---|---|
| One 24 h positioning impulse beyond its level | R211/R212 test components, not changes. | Complete timestamped ratios, principally 2023 onward; fixed level-B and price/taker controls; one horizon, no change/acceleration grid. |
| One context gate on a frozen 72 h flow book | R201/R204 trade context pairs as their own portfolios. | Original signals/positions plus one predeclared context; charge exits/reentries and compare matched risk, not just lower exposure. |
| Lead-lag entry timing for already-planned flow slices | R219 tested standalone books and explicitly left the overlay open. | Historical flow slices and lead scores; fixed delay/expiry, timing placebo and exact turnover. |
| C14 weekly momentum | Different formation/holding definition from R222 and longer holding than atlas targets. | Survivorship-free daily prices, point-in-time liquidity, funding and lifecycle exits; one literature-defined rule first. |
| Multi-timeframe agreement or cluster-relative returns | R195 studies contexts; R217 stacks three flow signals rather than timeframe signs. No cluster portfolio was found in lane specs. | Raw feature panels; an economic rationale and small frozen family, not the legacy broad grammar. |
| Aggressor-signed event flow | R226 is unsigned; coarse taker measures already exist. | Timestamp/side-validated event capture; incremental comparison with coarse taker flow and realistic executable delay. Large archive downloads need owner approval. |
| Basis-triggered carry / next-rate revisions | C09 is unrun; settled funding is not the displayed next-rate forecast. | Exact spot/perp prices and units, settlement ledger; prospective next-rate snapshots and a no-change forecast baseline. |
| Copy-trader/whale persistence | Collection is not a target-return test. | Further dates after frozen selection; survivor/beta controls and visible-position coverage. |
| Maker flow overlay | R193/R194 tested directional OHLC trade-through entries, not this queue-aware flow overlay. | Prospective book/arrival evidence and adverse-selection controls; manual and API fees differ. |

## What can actually run in this checkout

- Raw candles, research feature tensors, funding parquet, eligibility panels and historical spot tapes are absent
  from the inspected worktrees. Literature phrases such as “have” in older docs describe Claude's original
  data environment, not proof that those inputs exist here. Do not launch a nominal backtest against absent data.
- `experiments/sizing_v1/results/daily.npz` contains 2,099-entry daily arrays for A/B controls and overlays,
  X1/X2, plus multiplier arrays. It stores **1x net paths only**, with no date, position, cost or exposure arrays
  ([writer](../scripts/run_sizing.py)). Split summaries at 1x/2x/3x are in its `results/results.csv`.
- Fixed positive sleeve weights permit exact isolated-sleeve 1x net mixtures and 2x/3x split means.
  They do not permit stressed daily paths, cost-netting gains, new fills or capacity claims.
  Subtracting B's net from A would incorrectly subtract B's transaction costs.
- MEXC flow/carry journals contain only the 18 replay dates October 1–18; copy/whale snapshots cover one date.
  These are collection seeds, not enough evidence to choose or confirm a new mix.
- [R228 allocation_v1](../experiments/allocation_v1/PREREG.md) specifies a bounded convex allocation study on the
  existing A/B/X2 archive. Its own frozen protocol governs measurement and verdict; this ledger claims no outcome.
  A already includes B's positioning signal and X2 reweights A's three signals: this tests allocation among
  overlapping sleeves, not diversification across independently discovered economic edges.

## Search accounting and stopping

The [registry](../registry/rounds.csv) totals 9,471,756 raw trials after R226, dominated by correlated atlas cells.
That count is neither 9.47 million independent mechanisms nor evidence that every family above is exhausted.
New weights, venues, time windows and research choices still require explicit trial accounting.
Read the actual frozen specification and findings before reopening a rule; preserve null outcomes and stop rules.
Freeze each changed question before measuring, report 1x/2x/3x and missing inputs honestly, and reserve confirmation
for prospective outcomes collected after the specification. No real orders or capital decision follows from this audit.
