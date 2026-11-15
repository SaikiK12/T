# Where the value is: a ranked read of the program, 2026-11-15

> **CORRECTION, same day, after reading `experiments/reserved_batch1/FINDINGS.md` (R286).**
> The ranking below put the unlock short first on the strength of its gate-0 archive numbers. That
> was wrong: **R286 already read it on reserved samples and it FAILED** — 57 fresh events, mean
> **-3.45%**, week-cluster t **-0.87**, leave-two-coins-out **-4.59%**, 2x **-3.65%**. Four 2020
> events lost **-55.7%** on average. The one reserved-sample **PASS is C14, cross-venue funding
> carry binance+gate** (+2.86%/yr at 1x, NW t 4.03, p 2.8e-5, trimmed +0.68 bp, L2CO +0.59 bp,
> 2x +1.86%/yr) — at about a quarter of its archive size.
> I had read `docs/EDGE_SCOREBOARD.md` (as of R363) and the lane's own FINDINGS, but not R286's
> decision table. The scoreboard's "largest per-event edge on file, in-sample only" line is what
> misled me. **R494's sizing work is still valid as a risk description, but it sizes a book that has
> failed its one out-of-sample test.** See `research/EDGE_HUNT_20261115.md` for the corrected read.
> The original text is kept below, unedited, so the error is visible rather than buried.

Coordinator synthesis after a four-worker independent review (different models, one shared
evidence pack, no worker wrote to the repo). Every number below was recomputed by the coordinator
from committed files; worker claims that failed verification are marked as rejected.

Inputs: `docs/EDGE_SCOREBOARD.md`, `docs/CRITIQUE.md`, `docs/GATES.md`,
`experiments/unlocks_v1/FINDINGS.md` and its committed `results/events_priced.csv` (422 events).
Reproduce the arithmetic with `scripts/value_review.py`.

## The shape of the problem

About fifty registered nulls, one edge confirmed out of sample (funding carry, ~1%/yr, below a
T-bill), and no on-time forward day for anything. The holdout 2025-07..2026-09 is spent at program
level. Another cross-sectional signal search is therefore low value: R493 this session added a
51st null, and `docs/CRITIQUE.md` already says the process is serious while the decisions are not.

The binding constraint is **not** finding another signal. It is that the strongest edge on file is
blocked on a risk model, and nothing can be confirmed quickly by daily-book paper (a Sharpe-1.5
book needs ~1000 days for 80% power).

## Ranked work items

### 1. Unlock-short risk model — highest value, and testable today with zero downloads
`experiments/unlocks_v1/FINDINGS.md` ends with: *"any forward or real version needs a per-event
size cap and a written plan for squeezes. That is decided in the next PREREG, not here."* That
PREREG does not exist. This is the explicit blocker on the largest per-event edge in the lab.

**The edge survives a hostile statistical attack.** Recomputed on the committed 422 events:

| check | value | why it matters |
|---|---|---|
| mean net 1x | +3.24% | as published |
| median | +4.61% | above the mean: not tail-driven |
| trimmed mean (10%) | **+4.06%** | trimming the tails *raises* it |
| sign test (one-sided) | **p = 1.6e-8** | no normality assumption |
| week-clustered bootstrap 95% CI | **+1.21% .. +5.24%** | excludes zero; P(mean<=0)=0.001 |
| skew / kurtosis | -1.66 / 11.91 | the referee's kurtosis worry is real, and answered |

The referee worker argued the week-clustered t could be a false positive under this kurtosis. The
sign test and the trimmed mean settle it: the edge is in the body of the distribution, not the tail.

**Sizing arithmetic (new, decisive).** Sequential fixed-fraction compounding over all 422 events,
gross + funding, **including** the -132% RIVER squeeze, no stop assumed:

| per-event cap | terminal equity | max drawdown | worst single event |
|---|---|---|---|
| 2% (owner's Gate 4 proposal) | 1.286x | **-4.04%** | -3.55% |
| 3.8% | 1.605x | -7.56% | -6.75% |
| 5% | 1.856x | -9.85% | -8.88% |

At the owner's proposed 2% cap the historical tail cannot ruin the book, and the drawdown sits
inside a typical prop challenge's 5% daily / 10% max limits.

**Concurrency is the risk the per-event cap misses.** Recomputed from the D-7 -> D hold: mean 1.47
positions open, **max 9**; 169 of 2016 days have >= 5 open. The worst concurrent cluster sums to
**-179.5%** of notional (2026-01-17) and the worst single week to -124.6% over 5 events. At a 2%
per-event cap that cluster is -3.59% of equity; at 3.8% it is -6.82%. Peak gross exposure reaches
18% at a 2% cap and 34% at 3.8%. **A per-event cap alone is not a risk model**; the frozen rule needs
a portfolio gross cap and a cluster limit.

**Event frequency is rising**: 11 (2021), 16, 41, 52, 134 (2025), 168 (2026). An event lane reaches
t~2 in ~130 events, so this family can actually decide in useful time, unlike the daily books.

**What this lane must not do.** The tempting move is to filter on unlock/ADV >= 0.82 because all
six >-40% losses sit below it. Verified: that is true, but **Fisher exact one-sided p = 0.101** on
six events — not significant. The *return* split at 0.82 was pre-declared in R265's frozen PREREG
(inherited from R181) and is admissible as a logged variant; the *tail* claim was seen after the run
and is not. Both the referee worker and the coordinator reject using it as a rescue filter. One
worker proposed exactly that filter and was overruled.

**What cannot be tested on committed data.** `events_priced.csv` has no intrabar path (no
high/low/MFE/MAE), so a -25% hard stop cannot be simulated here. R208 already found stops harmful on
the flow books. A stop rule needs hourly bars and its own frozen lane; until then the risk model
should rely on sizing, not on an untested stop.

### 2. Carry execution: the maker/taker gap — cheap, bounded, real
Carry is the only out-of-sample edge and it is small. Measured MEXC costs (R224): API taker 8 bp,
**API maker 6 bp**, web maker 0 on 1106/1200 contracts, median $10k API all-in 9.3635 bp/side with
all 37 coins above 8 bp. The edge's economics are dominated by which side of that spread it pays.
The owner's Gate 4 already proposes 20-30 tiny live calibration orders. That is an owner decision,
not something to start here; the lab-side work is to state the break-even cost multiple at which
carry survives, per venue and order type.

### 3. Prop-firm feasibility — answer it and stop
Two workers agree, and the arithmetic supports them: carry fails on **return velocity** (~1%/yr
cannot reach a 10% target without breaching drawdown limits), and the event edge fails on **tail**
unless size-capped. With the 2% cap the event book's historical max DD is -4.04%, which is *inside*
the limits — so a rules-compliant variant is conceivable on risk, but it still has **no out-of-sample
confirmation**, and at 2% sizing the per-event equity gain is ~0.065%. Reaching a 10% target needs
~150 clean events. At 2026's ~168 events/yr that is roughly a year, not a month. Worth stating
plainly in `docs/` so the question stops being reopened.

### 4. Another cross-sectional signal search — lowest value
R493 (this session) is the 51st null. The scoreboard's pattern is consistent: gross edges exist and
are smaller than taker cost. More of the same is theatre unless it targets a *cost* or *capacity*
constraint rather than a new signal.

## Worker agreement and disagreement

| worker | model | verdict | coordinator check |
|---|---|---|---|
| value | qwen3.7-max | rank: forward unlock validation, carry execution, unlock sizing | agreed; sizing promoted to #1 because it is testable now with zero downloads |
| referee | deepseek-v4-pro | ADV tail filter is post-hoc and inadmissible; kurtosis may fake the t | **agreed and verified** (Fisher p=0.101); kurtosis worry answered by sign test + trimmed mean |
| risk | qwen3.7-plus | 2% cap, ADV filter, funding veto, -25% stop | sizing arithmetic reproduced; **ADV filter rejected** (post-hoc), stop **untestable** on committed data, **concurrency missed** |
| prop | qwen3.7-plus | carry fails velocity, events fail tail; ~3.8% cap implied | agreed; refined with the measured -4.04% DD at 2% and the ~150-event horizon |

Two of four workers initially returned empty text: `glm-5.2` spent its whole token budget on
reasoning and emitted no content, even at 6000 tokens. The role was moved to a model that answers.
This is recorded so a later reader does not mistake a tooling failure for a model's opinion.

## Recommended next lane

A frozen **risk-model PREREG for the unlock family**: per-event cap, portfolio gross cap, cluster
limit, funding veto, and an explicit statement that no stop is assumed. Decided on the committed
422-event file plus the reserved/forward events, with the ADV tail filter excluded as post-hoc.
It removes the one blocker the strongest edge itself names, needs no new market data, and cannot
be accused of mining the spent holdout for a new signal.

Nothing here authorises real orders, money movement or a stake. Gate 4 remains the owner's.
