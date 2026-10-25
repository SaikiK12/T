# R321 — NULL: fewer false signals, no procedure meets the full acceptance rule

Frozen code/specification/input commit **eb8349eb52ac6cd1be84e760eefb615e76d26270**
was pushed before any production Monte Carlo outcomes. This study is entirely
synthetic: no market policy/label/PnL was re-evaluated. R311 remains INCONCLUSIVE
and its selected policy negative at2x/3x. R320's known market comparison remains
without demonstrated skill. No strategy or prospective paper lane is activated.

The new controls reduce observed false family exclusions, but neither passes
the complete preregistered acceptance criterion. Their worst observed rate is
3%; its simultaneous exact upper bound is6.3103%,above the unchanged5%limit.
Do not raise the limit to turn the result into a pass. This is insufficient
validation precision under the chosen protocol,not evidence that the true
rate exceeds5%or that OBM can never be useful.

| Procedure | Worst observed null rate | Worst exact adjusted upper bound | Detection at preselected effect.5 | Accepted |
|---|---:|---:|---:|---|
| iid Gaussian negative control |90.2%|93.99%|100%|No|
| Incumbent circular14 percentile |36.4%|43.61%|97.5%|No|
| Calibrated OBM14 |3.0%|6.3103%|40.0%|No|
| Calibrated OBM28 |3.0%|6.3103%|49.5%|No|

These are maximums across the ten registered simulated null profiles,not
estimates of real trading false-positive rates. The same preselected power
case uses Gaussian-component rho.6,effect0.5in nominal daily long-run SD units,
not0.5percent returns or a forecast of money. Lower apparent power in the
naive controls is not the problem: their detection is high partly because
exclusions are badly uncontrolled. A rigorous method pays for fewer false
signals through wider intervals and lower detection.

For that SAME Gaussian rho.6case,power at effects.1/.25/.5is:

- OBM14:0.5% /2.5% /40.0%.
- OBM28:1.0% /7.0% /49.5%.

All other profile/effect/procedure cells,including wrong signs,null-coordinate
exclusions,zeros,stress results and exact uncertainty intervals remain in
results.json. Zero observed exclusions never becomes known zero risk: with
500paths and this40-cell adjustment,the zero-count upper bound is1.4647%.
No low-power case,failed criterion or unfavorable procedure was omitted.

The500independent calibration paths per each of8profiles give tolerance order
490/500. Worst-profile max-abs-t cutoffs are4.67175646(block14)and4.20707166
(block28). The deterministic binomial tail is0.0004600071543,below the per-cell
budget0.000625;order489does not meet it. Under the specified independent path/
continuous-CDF assumptions,Bonferroni over16calibration cells gives at least
99%confidence over calibration draws that EACH declared null CDF has at least
95%coverage using its relevant block cutoff. This is distinct from the held-out
precision veto that failed. It is not99%future-path coverage,unknown-market
coverage or a license to choose whichever block rejects.

All eight baseline profile point estimates for both OBM methods are <=3%.
The14-day method fails the upper-bound criterion at Gaussian/t5rho.9;
the28-day method fails it at Gaussianrho.9. The two unmodeled scale-step/jump
stresses also remain visible; they do not extend the formal calibration family.
The preselected20%power floor was met by both,but cannot override a failed
size/precision criterion. No winner,alternate threshold,extra look or larger
simulation budget was selected after outcomes.

This provides one reusable constrained inference kernel: every273daily
observation enters the mean and overlapping variance estimate; wrong shapes,
missing/nonfinite/gapped or overflowing day IDs are refused. Exact constant
columns(including decimal.1)and unrepresentable moments/endpoints fail closed.
There is no epsilon repair,infinite-interval success or replacement sampling.
The same bounded independent reviewer checked the OBM coefficient,tolerance
calculation and exact binomial construction before freeze. Counterexamples
were fixed before registration; the stated review does not cover the generator,
runner,max-statistic construction,source truth or future-market validity.

Verification:

- Full required unittest discovery passed1,294tests/2skip entries in177.729s;
  ten new predetermined hand-fixture tests pass. No production calibration was
  performed during test development or peer review before freeze.
- The frozen literal checker independently checked120selected OBM coordinates,
  30selected resampling coordinates and the binomial tolerance order against
  SciPy. It shares the registered generator and does not independently verify
  the full DGP or source availability.
- The explicitly POST-OUTCOME count auditor reconstructs all136held-out cell
  counts from all5000saved base-path records,and checks248exact binomial
  endpoints. It validates fixed report arithmetic,not a new hypothesis or an
  excuse to change results.
- Four deterministic artifacts byte-reproduce in a fresh directory:calibration
  statistics,calibration contract,all held-out path intervals and results.
  The independent numerical audit also reproduces exactly.

The registry counts **152diagnostic cells**:16calibration cells plus136held-out
cells(128baseline/effect/procedure+8stress). These are4procedures and9000unique
noise paths;the5000held-out paths include the first200shared-noise power paths.
Shifts/resamples are not independent market samples.152diagnostic trials are
added conservatively to the prior9,478,786program total,not hidden as0simply
because they are methodological. Strategy trials0,new prospective paper days0.
No program-wide adaptive false-discovery guarantee is claimed.

Cost sensitivity1x/2x/3x: **not applicable to this statistical-loss diagnostic**;
monetary net returns remain unknown at all three tiers,not0. Nothing here
supplies executable fills,proves fees or improves R311's actual expectancy.
A market study still needs separate frozen cost/timing/capital/dependence and
multiplicity controls and genuinely new on-time paper observations.

The bounded parallel input investigation narrows the Lighter source gap but
leaves the cash bridge UNVERIFIED. Four static GETs/91,022body bytes/about1.43s
read exact pinned internal funding/USDC constants,generic collateral helpers,
SDK string fields and the distinction between rates and historical endpoints.
Previously unread cached public-prefix/checkpoint sections were also inspected.
Six distinct scopes,old reconfirmations and weak alternative interpretations
are enumerated in sources.json/source_review.md;no extra method/alias queue
rows are manufactured. Existing canonical intake/queue receives supplementary
source evidence with all407previous objects/alias bytes preserved.

Internal price-weighted prefix arithmetic and circuit public-input exposure do
not establish normalized API Funding.value,account funding application,base/
price conversions,deployed correspondence or an authentic public historical
prefix endpoint. No cash converter is implemented from these missing mappings.
Source bodies remain ignored cache;no copyrighted repository was mirrored or
installed. Source-only mechanism interpretation is not settled PnL evidence.

Zero market/history/account/RPC requests,orders,money movement,secrets,weights,
subscription/login bypass,merge or PR closure. Historical approval remains
7757/8000requests and reported229.85/250MiB spent,without a reset or invented
exact remaining bytes. No permanent process or remote delivery is promised.

Reproduce from this result checkout and frozen numeric environment:

```sh
.venv/bin/python scripts/run_dependent_null.py --out /tmp/R321-reproduction
.venv/bin/python scripts/check_dependent_null.py --directory /tmp/R321-reproduction
.venv/bin/python experiments/dependent_null_v1/audit_counts.py --directory /tmp/R321-reproduction
```

There is no market-cache prerequisite. Existing outputs are retained;an explicit
fresh directory is required for reproduction. The next market-input gates remain
synchronized first-seen executable books,source-bound fees,sessions and correctly
bound fair/index(or authenticated normalized prefix)funding data.
