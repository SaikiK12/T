# R361 — DATA_PASS for offline execution engineering; no executable edge validated

**Exit-stage median processing/IO falls from295.667/311.446ms to24.505/33.301ms
on the same sealed R359trace.** All20candidate stage samples are below40.213ms,
against the unchanged250ms bound. Every old report/journal/account result stays
byte-identical, including the two ACTUAL late R359exit receipts. These are
offline local-service measurements, not new first-seen or strategy evidence.

Source/code/protocol freeze **cd02a26d3096590b5f0c5298b00ea67497ce2f35** preceded
the changed-code experiment. PREREG SHA256
`924f1d89866c2a7931f846906658a3b72784d2b525433b9235f349abcaf14f6c`.
R360's complete failure evidence was sealed in that same commit BEFORE R361
measurement. No frozen file, old journal or old acquisition allowance changed.

## What changed and why the first implementation failed

R360 incrementally applied source updates but still exported all six full
books on every received frame, including another export in freshness_flags.
Its fixed180s experiment completed all ten account-equivalence runs but stopped
prefix-state checking. Its per-stage timings were only held in memory until
completion and were lost. The original log/failure and391retained files remain
in [R360](../incremental_pair_control_v1/FINDINGS.md); no R360 timing is reconstructed or speedup claimed.

R361 keeps immutable source fields/canonical raw bytes and the original
Replay decoder, atomic Lighter nonce/epoch state and financial controller.
Receive updates parser/state once without exporting the complete books. Only
an observation materializes through original DepthReplay. Its cache is one
current generation/asof/profile/connection-boundary key: a new frame, later
asof, full/top profile or changed unusable boundary forces materialization.
Quantity/cost/admission checks still run for every observation. An idle cached
book cannot remain fresh at a later asof. Reconnect needs a new adapter.

The controller's financial methods stay byte-unchanged R359 in an instance-
private dependency namespace; shared imports are never patched. No collector,
Claude R355/R356 file, forward ticket, session rule or financial model is edited.
Each completed benchmark profile now persists its measured receipt immediately,
so a later failure cannot silently discard completed measurements.

## Registered finite comparison and actual service times

Same2352sealed R359frames, original four decision/evaluation and issued clocks,
original final report clock. Five paired baseline/candidate repetitions in a
fixed alternating order; all samples retained. Both share the same loaded
input. Actual source read/decompression precedes stage timing, and constructor/
report/whole run are measured separately. Native journal IO remains included.
No fastest-run or outcome-dependent variant is selected.

| Original stage | Baseline median ms | R361 median ms | Baseline maximum ms | R361 maximum ms |
|---|---:|---:|---:|---:|
| Entry decision |178.660|26.995|190.871|35.556|
| Entry model evaluation |182.378|32.524|198.572|40.213|
| Exit decision |295.667|24.505|328.944|29.296|
| Exit model evaluation |311.446|33.301|327.475|39.447|

Moved receive work is counted:2352candidate receive services total
**302.108–340.922ms per run**, p99 **0.401–0.524ms**, maximum **8.751ms**.
Whole-run CPU, including receive and original account/report work, is
**456.900–508.533ms**, versus baseline986.532–1039.341ms; median496.124versus
1018.703ms. Whole-run wall median524.124versus1056.204ms. The improvement is not
created by excluding receive work from the total. Exact samples and nearest-
rank summaries are in benchmark.json and the ten original timing receipts.

The old-arrival serial-service illustration gives candidate max source-queue
lag2.103492ms, max stage queue0.056293ms and max queue+stage finish40.212867ms.
Those modeled resource-service clocks NEVER replace account/source clocks.
Different live receive work may change physical first-seen arrival; this finite
trace cannot certify live schedulability or any venue/order latency.

The whole experiment completed in **30.286099907s**, within the SAME180s bound.
Shared process RSS high water40028KiB is below655360KiB, but is not isolated
profile memory attribution. Recorded environment:Python3.12.14,
Linux6.18.55/x86_64/glibc2.41,3logicalCPUs. Hardware repetitions are not independent
market days and imply no strategy confidence interval or market p-value.

## Economic and source equivalence

All ten fresh profile runs reproduce the complete original R359result and
all38native account/reference-journal and receipt files EACH, byte for byte.
All64fixed prefixes pass all6symbols xfull/top profiles:768row/full-book plus
128error/assembly-counter checks = **896comparisons**. State equivalence uses
the same frozen venue parser on both sides; it is not an independent parser.

The independent standard-library checker passes **9995checks**, including the
complete retained R360failure/output inventory, all ten old and ten new account
reports, native cash, gross price movement, all fees, original q, exact flat
positions, whole segregated capital, hashes and unchanged original timing.
It imports no production account, pricing, risk, state or controller function.
The actual invocation is bracketed by the frozen committed-input verifier.

Fraction arithmetic preserves the financial contract's SUPPLIED descriptive
float-midpoint converted to decimal text as its stress anchor. It does not
substitute a different exact-decimal mean. That distinction and native-cash
corruption rejection were tested on invented data BEFORE R361freeze; no money,
cost multiplier, quote or tolerance was changed to fit real-trace outcomes.
R360's original independent helper/code stays unchanged.

All36original cost cells remain:12fixed direction controls, each at1x/2x/3x.
Only BTCentered;30cost cells remain blocked by old stale/skew/session/unknown-q
guards. Fixed q is0.0030BTC per leg,10000capital per alternative segregated
5000USDT/5000USDC,250quote leg budget, original10/4bpfee-reserve scenarios and
explicit1:1USDT/USDC FX. Alternatives are not pooled into a larger portfolio.
Spread is embedded once and no thin-book extrapolation or later resizing occurs.

| Same BTC control, known price-minus-scenario-fee component |1x|2x|3x|
|---|---:|---:|---:|
| ShortMEXC / longLighter |−0.653486|−1.338171|−2.022857|
| LongMEXC / shortLighter |−0.729927|−1.428643|−2.127347|

These are model quote-equivalent components on all10000capital. Full funding
cash, full net, full account NAV and actual expected executable net stay UNKNOWN
in every cell. Fees/FX are scenarios, not owner entitlement/parity evidence.
No-action cash uses the same whole capital and original zero-interest scenario.
Source/account/risk qualification is unchanged, including XPD's negative control.

R359's actual entry receipts remain on time and its actual two exit receipts
remain late. Faster offline service does not repair them. No new observations,
qualified strategy days, alpha refits, validated positive expectancy or activation.

## Validation, preservation and reproducibility

- Full suite BEFORE R361code commit: **1650tests,0failures,3existing skips,
  198.441s**. Sixteen invented regression cases extend ownership/clock/nonce/
  corruption/fixed-q/account guards with deferred/cache/boundary/stale-asof,
  instance isolation and independent midpoint/cash checks. Full R360suite was
  1634tests/0failures/3skips/205.602s. Exact compressed logs are retained.
- Recorded402R361output files are losslessly packed as22content-addressed
  objects plus an index; all402restored byte strings were checked against the
  actual originals. This is deduplication only; no receipt, journal or timing
  is rebuilt. Original objects are also preserved locally. See recorded_outputs
  manifests and recorded_outputs_check.json. R360's391file archive remains intact.
- 109 code/dependency and 75 sealed older-input hashes verify before/after the
  run and independent audit. Old registry byte prefix,530method objects and
  27source records remain; only the existing M409note and one supplemental
  intake extend. No duplicate queue or panel, no collector/forward rewrite.
- R360andR361append with the registry helper,0new predictive trials each.
  Three unique engineering implementations are explicit: original baseline,
  R360eager export and R361deferred/cache candidate. Five hardware repetitions
  do not multiply economic variants. R359's12diagnostics remain counted there.
  Program reported trials stay**9479034**; the old six-trial cross-branch
  discrepancy is preserved. No dependent-null/multiplicity efficacy claim.
- 0 new market/source/history/media/weight acquisitions. Historical7757/8000
  requests and reported229.85/250MiB remain ONE accumulated allowance; R359's
  separate live allowance and both benchmark reservations are CLOSED.

Final integrity: **169 registry rows / 164 local specs / 163 verified frozen /
1 planned**, zero errors and the same14legacy warnings. Intake remains
530aliases / 340queue rows / 27source manifests, zero errors/warnings. PANEL's
bytes and timestamp are unchanged. Source/test logs, hashes and detailed scope
checks are retained beside these findings.

The original benchmark can be reproduced OFFLINE in an isolated checkout of
the pre-outcome freeze cd02a26, where its R361run marker does not yet exist.
Use the frozen runtime/dependencies and a fresh output directory. Such a replica
may have different local service times; it cannot overwrite the original cohort,
renew collection, add strategy evidence or repair old timing. Current-head
run_started.json deliberately refuses another scheduled run.

```sh
python -m unittest tests.test_deferred_pair_control
# Offline replica ONLY, from an isolated cd02a26 checkout:
python scripts/benchmark_deferred_pair_control.py --out /fresh/R361-replica
python -c "from pathlib import Path; from scripts.benchmark_deferred_pair_control import helpers; helpers().verify(); from scripts.check_deferred_pair_control import run; run(Path('/fresh/R361-replica'), Path('/fresh/R361-audit')); helpers().verify()"
python -m lab integrity
```

R310/R311remain INCONCLUSIVE and their preselected2x/3xpolicy loses; no rerun or
validation-winner switch. The local processing blocker is reduced in this finite
trace. Next actual input blockers are publisher-certified current validity for
idle books under unchanged freshness rules, authentic fee/session/access and
event-effective fair/index funding values, plus actual margin/execution risk.
Any prospective strategy/control capture needs its OWN frozen finite protocol
and genuinely new on-time inputs. No order, money, secret inspection, merge,
closure, permanent process or guarantee of profit.
