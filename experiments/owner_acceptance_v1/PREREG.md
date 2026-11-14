# R320: common paper controls, risk-component validation and owner100 acceptance

- **Registry id:** R320
- **Owner (single writer):** Codex, existing consolidation draft PR49
- **Date registered (UTC):** 2026-10-25
- **Canonical scopes:** M018/M185 risk component; M037/M193 source variants; M239/M240/M241/M409 accounting controls. No second methods queue.

code_inputs.json SHA256: 8dff3f3bde4ff178f584c2029ebd0a19e2b14edbbcd72fe489803a89ee1425c0
data_inputs.json SHA256: 8b592585011215addb7ecf62904d1d17d38e98456ec4da0b588a7222fc7f6777
fixtures.json SHA256: 20e37a41250b4689e6b9cf97251e02b44c69a6b0de548150ab46b5887d8cdeea
requirements.json SHA256: 8fee48fd33fdd6234b2579467e8e544076d381432b04dd78f031c975220a1856
requirements_evidence.json SHA256: 5bca26ad3f3cb4c91ea3a0062a8d50336db8d5a3dbfad7de30d983ba80efe65a
sources.json SHA256: b064cda87406f0d988341ae8b64bbafe648b83bc87e5df37c9ec4de65ccdbe84
benchmark_environment.json SHA256: 282064111ecdef75ba7ee4b72099c614f981eeab3cd1a4ba9b5a56ab41d8f4a3

## Question, boundaries and freeze

Can incomplete or risky simulated inventory be prevented from looking like an
admissible net-profit candidate, while the common view explains capital,costs,
provenance and missing evidence? Separately, does the existing univariate EWMA
risk component forecast next-day realized variance better than simple fixed
controls, and is a new data engine justified on the actual small held input?

Freeze with lab.prereg.freeze and commit/push the finite specification,75-file
computational closure,source/input identity and all100 exact owner requirements
BEFORE any new held-price forecast,benchmark or lifecycle-risk aggregate.
Development assertions use invented facts only. The recorded full-suite gate
must pass before the lab-code commit. Old frozen files and journal prefixes
are never rewritten. Shared CLI/export/index/HTML are Git-versioned mutable
views; they do not compute the registered risk outcomes or change native
journals. Their tests are included and their observed revision is the freeze
commit, not a claim that those shared views can never evolve.

R310/R311 remain as recorded:1,318 actual missing funding events repaired,
all12models calibrated,224/273common validation days and negative selected
policy at2x/3x. No R311 rerun,winner change,gap/tradability relaxation or leverage
increase. One BTC hourly-trade-close file is not executable quote history,
a funding-notional proof,an unseen sample or the PIT top20 APSI universe.

## Paper controls and exact owner scope

Reuse frozen R318/R319 accounting and all48 invented lifecycle paths
(16cases×three fixed cost tiers),with5,000USDT MEXC and5,000USDC Lighter kept
separate. R320 applies the same unlevered fixed limits: loss3percent of initial
capital,drawdown2percent,venue gross at most100percent,symbol gross at most
25percent. Both sides count toward gross; no currency/venue netting or leverage.

Pin contract/rule identity and the exact initial account set in the persistent
hash-chained risk header. Missing accounts/positions/marks,unknown fees or
sessions,rule drift,future/stale/stepped clocks,pending/unreconciled pair
orders stop new model entries. Preserve positions and possible orphan risk;
never invent flattening. Stops and high-water loss survive reopen/deposits;
net economic loss subtracts external flows. Historical mode always stops.
Supplied fixture completeness is not authenticated source/account evidence.

The independent bounded financial review found two fail-open cases: comparing
only two caller-supplied rule IDs,and accepting omitted accounts/positions as
zero. Both were corrected and independently rechecked before freeze. That
review covers the stated financial cases,not new forecasting,source
authenticity,bootstrap validity or all100 requirements.

Entry threshold is gross profit in settlement quote minus tier*(nonoverlapping
cost+reserve) minus measured forecast-error allowance. Tier is1/2/3. Missing
inputs,uncalibrated error or variance/base units cannot pass. R320 supplies no
actual gross-profit forecast/error estimate: all actual entries stay blocked.

requirements.json retains the owner's exact100numbering/text. The acceptance
input maps every request to concrete evidence and an honest verified/partial/
blocked/not_selected state; the derived coverage is not a queue or a claim100
are implemented/market validated. Verify new output existence and actual
cache/export/full-test checks. Missing DuckDB in a reproduction downgrades its
comparison; no success substituted. Verified means only the stated bounded
engineering/read scope. Keep all external input and prospective-time blockers.

A conservative separate adapter retains native historical net/on-time labels,
missing values and journal rows. No Boolean flag upgrades them into executable
account evidence. New strict scored days remain0 until a separately supported
frozen protocol/source contract can supply six required identities. New
prospective scoring is not authorized by any historical component result.

## Finite already-seen risk-forecast study

Input: data/equations_v2/mexc/prices/BTC_USDT.parquet,402923bytes,
SHA256fa51ba0038084a3c79ad757402d21129535a37c2c683886f91d78bb53ebb2aa9.
History [2025-04-01,2026-10-01); validation [2026-01-01,2026-10-01),273UTCdays.
Source t is bar-open milliseconds; close time is t+onehour. Require unique
exact hours,positive finite traded close and volume at both return endpoints.
No price interpolation/forward-fill or stale/zero-volume return masquerading
as a zero. A day target is sum of24squared hourly log returns; an incomplete
day remains missing. Genuine zero target is valid; zero/negative predicted
variance has no QLIKE score and is not epsilon-repaired.

Exactly four fixed models: previous1/7/30complete-day RV means and existing
lab.apsi.basket_sigma24's squared univariate168hour EWMA raw second moment,
72hour half-life,times24. Only returns completed at the forecast origin enter.
Reference is mean7 fixed before outcomes; compare mean1/mean30/ewma72 to it.
There is no validation-selected model,holding duration,capital allocation or
new index formula. Full HAR/GARCH/PIT quote-volume basket and APSI utility
remain open. This tests variance forecasting,not expected monetary profit.

QLIKE=log(prediction)+realized_RV/prediction; also report squared error and
per-model/common coverage. Preserve all273rows and nulls. Require all273days
common and contiguous for intervals; otherwise INCONCLUSIVE with no compressed
calendar or post-hoc rescue. Report three paired loss differences (negative is
better than mean7),with circular block percentile bootstrap at fixed7and14day
blocks,2000replications,seed320 and Bonferroni within these three comparisons.
Keep five largest absolute daily contributions as influence diagnostics;
exclude none. This is not program-wide adaptation control after9,478,782tries.

Before interpreting intervals,report finite dependent-null calibration:
100paths of three zero-mean AR1(.6)series,273days after128burn-in,400bootstrap
replications per path,seed1320plus path. Report family false exclusions,
binomial SE and Wilson interval. This one null does not prove universal
coverage or future-regime calibration. No significance claim if a calibration
or incomplete sample undermines it. At most descriptive component skill when
both block choices support the difference; never a net-alpha activation.

Count all four risk models as4trials,not strategy trials0. The prospective-day
increment is0. Report fixed1x/2x/3x as not applicable to variance loss,with
monetary entry controls at all three tiers; do not attach invented PnL to RV.

## Measured tools,source use and audit

Read the same held input through Pandas,Arrow,content-bound LRU and optional
isolated DuckDB1.4.1. Verify values,order,types and NaNs exactly before speed
comparisons. One warm-up then five rotating warmed rounds; each reader hashes
the current source. Record wall nanoseconds,Python traced allocations and
frame bytes,not an invented native RSS or cold-disk benchmark. Optional wheel
and extracted file hashes are pinned outside the core frozen dependency lock.

The risk and export consumers actually share the content-keyed parse but get
independent copies. New Parquet export uses zstd3,strict exact round trip,
source SHA and explicit traded-close/bar-open roles; old source is untouched.
No wholesale format migration or Rust port without measured justification.
Runtime performance is nondeterministic: retain those timings,compare semantic
identities on reproduction,do not demand byte-identical speed or claim a global
speedup on unseen workloads.

Eight finite static source GETs completed with1,316,887response-body bytes,
6.594seconds,within declared4MiB/1MiB each/90s. No redirect/retry/login. Exact
source versions/read/unread scope and all20distinct rules/process/data controls
are retained. QuantStart503means unread. Quantpedia public summaries are not
received full papers; one rebalancing benchmark conflict and unknown image-only
utility coefficients stay open. Official FTMO products/cohort/date loss rules
are distinct; EA allowance does not grant API/MEXC/fee/payout compatibility.
Jane Street/Citadel pages describe process,not private strategies/resources.

Ordinary optional dependency scope:2GETs,20,557,441body bytes,1.551seconds,
within25MiB/90s. No market data/model weights/core environment lock changed.
Historical acquisition stays7757/8000requests and reported229.85/250MiB;
rounded prior bytes do not authorize an exact remaining allowance or a reset.
No market/history/account/RPC request,secret,order or money movement.

Independent literal oracle reconstructs all daily targets,forecasts and losses
without production risk functions; audits report/unknown-money/permission
claims and100scope. It is not independent provider authenticity or general
bootstrap validation. Reproduce deterministic outputs in a fresh directory;
performance.json is separately measured. Check immutable source/export identity,
all old frozen files,source/alias objects and journal prefixes. Verdict may be
PARTIAL engineering/component evidence,never a confirmed profitable strategy.
