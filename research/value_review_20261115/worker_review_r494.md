# Worker review of the R494 risk rule, 2026-11-15

Four independent workers, four different models, one shared pack (`evidence_pack.md`), none writing
to the repo. Harness: `scripts/ai_workers.py`. The coordinator verified every claim before acting.

| role | model | chars | verdict on the design |
|---|---|---|---|
| value | qwen4-max-preview | 19874 | ranked the forward lane + risk prereg first; two sharp catches, both verified |
| referee | deepseek-v4-pro-0813 | 2036 | the cap grid is itself selection; accepted, and the lane was redesigned |
| risk | qwen3.8-max | 2334 | concrete rule set, but a 25x units error; one useful stress idea |
| prop | qwen3.8-flash | 2178 | prop feasibility |

## Accepted: the grid was selection (referee)

> "Searching c x G x K x funding-veto/stop choices for the best terminal equity or max drawdown
> overfits, because any cap chosen to survive the known tail does so by construction."

This was correct and changed the design. R494 pre-registers **one** primary cell, fixed by the
owner's existing Gate-4 2% proposal rather than by what looks best, and demotes every other cell to
labelled sensitivity. The referee also required that the ADV filter be excluded "in any form: no
excluding, no split, no tail-exemption, no covariate, no sizing adjustment" — the PREREG says exactly
that.

## Verified: two catches from qwen4-max-preview

1. **G=20% and G=30% are theatre at c=2%.** Peak concurrency is 9, so peak gross is 18%; both caps
   bind on **0 days**. Recomputed: G=10% binds on 98 days, G=20%/30% on 0. This is why G=10% is the
   primary and why the two larger caps appear only as identical sensitivity rows.
2. **The owner's proposed stop is incompatible with the tail.** 25% of a 2% stake is -0.50% of
   equity, while the worst archived event is -3.55%. Recomputed at c in {1%, 2%, 3%}: the stop is
   breached at every one. R494 surfaces this as an owner decision and does not resolve it.

## Rejected: a 25x units error (qwen3.8-max)

The worker read Gate 4's "at most 2% of the account's trading capital **per book**" as a book stake
`B = 2% E`, then sized each event at `4% of B` = **0.08% of equity** — 25x smaller than the proposal
it was citing. Its survival arithmetic (-7.1% of B, -0.14% of equity) is internally consistent but
answers a different, far smaller book. Not adopted. Its ADV-notional and trailing-funding-veto rules
are also untestable on the committed file, which it correctly acknowledged.

## Adopted as a robustness note: stress beyond the archive

The same worker suggested stressing the worst cluster with an *additional* funding shock rather than
trusting the archived maximum. Recomputed at the frozen c=2%, G=10%. The worst cluster has **4**
positions open (not the peak-concurrency 9), so `min(c, G/n)` = 2% each:

| cluster scenario | cluster return | equity hit |
|---|---|---|
| as archived | -179.5% | **-3.59%** |
| plus one extra RIVER-sized funding shock | -224.5% | -4.49% |
| plus a 100-point stress | -279.5% | -5.59% |

The archived cluster is survivable; a 100-point stress beyond anything observed would breach a 5%
daily-loss limit. That is a real limit of the rule, stated rather than hidden. Reproduce with
`python scripts/value_review.py` (`cluster_stress_beyond_archive`). This is a description, not a new
gate: R494's frozen conditions were decided before these numbers existed.

An earlier draft of this note used n=9 for the worst cluster and reported -1.99%. That was wrong: the
peak-concurrency day and the worst-cluster day are different days. The code always used the correct
n; the prose was corrected.

## What no worker could know

Point-in-time unlock calendar accuracy, intrabar MAE/MFE and liquidation paths, entry-time trailing
funding, MEXC maintenance-margin ladders, real fill quality above $10k, and the joint dependence of
concurrent unlock shorts. Every one of these is listed as a limit in the lane rather than assumed away.

## Tooling note

`glm-5.2` returned empty `content` twice, spending its whole token budget on reasoning even at 6000
tokens; the role was moved to a model that answers. `qwen4-max-preview` returned its reasoning trace
rather than a finished answer — usable, but it had to be read as a draft, not a verdict. An empty or
rambling response is a tooling artefact, not an opinion.
