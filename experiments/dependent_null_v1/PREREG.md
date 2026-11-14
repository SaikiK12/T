# R321 — finite null-only calibration of dependent mean inference

- **Registry id:** R321
- **Owner (single writer):** Codex, existing consolidation draft PR49
- **Date registered (UTC):** 2026-10-25
- **Canonical scopes:** M018/M185 evidence controls; M409 input-source requirements

code_inputs.json SHA256: 3c7f94f79ef0d79f5eeb5caddfd9654950cca539c97a63253cae6677a64bf434
inputs.json SHA256: e5437711ddac1a95fab5ad28ac2644b525424d9206db0594127d812ead506dac
design.json SHA256: 106b2332bdfdbcbf8e038b727adab2831075f8de78cee09fcfca74f7e9cbe717
sources.json SHA256: f263330d7f870d2df5ddfc59ad8877102f9ed27b571699b8cf640114956b37a7

## Binding question and strict separation

R320's nominal5percent block-percentile intervals had12/10percent family false
exclusions in its dependent null control. Can a finite,explicitly calibrated
procedure control this error without reducing useful detection to near zero?
This is an independent necessary evidence component while actual executable
quote/session/fee/event-index inputs remain incomplete.

Freeze with lab.prereg.freeze and commit/push specification,implementation,
design,seeds,source/review/input identities BEFORE any new production calibration,
size,power or performance outcome. Unit development uses predetermined hand
fixtures,not generated empirical calibration. Complete required Python tests
before lab-code commit. Old frozen files,journals and source objects stay intact.

No market arrays,new market labels or strategy outcomes enter this runner.
No R311 rerun,old market reclassification,validation-winner replacement,
eligibility/gap relaxation or leverage increase. R310/R311 remain as recorded:
224/273common days and selected policy negative at2x/3x. R320's risk-component
comparison remains without demonstrated skill; a new inference method cannot
retroactively make its known market sample prospective or significant.

## Fixed complete synthetic sample and profile family

Each path has273artificial consecutive integer days and3joint daily mean
comparison coordinates. Missing/nonfinite/gapped/wrapped day IDs or incomplete
shapes are rejected; no dropping,compression,imputation or epsilon variance.
Exact constant columns and unrepresentable moments/intervals are DEGENERATE.
Preserve each failed path as unscored; never replace draws until a quota passes.

Eight calibration profiles: rho in{0,.3,.6,.9},crossed with independent Gaussian
or standardized t5 private/common innovation components. Innovations are
(private+common)/sqrt2,so cross-coordinate correlation is0.5 and each innovation
has variance1. For t5 components,multiply by sqrt(3/5); the mixed innovation is
not itself asserted to be exactly t5. Generate AR1 with sqrt(1-rho²) innovation
scale,zero initial state and128burn-in; nominal long-run marginal SD1. This is
a specified finite burn-in law,not an exact invariant-distribution initialization.

Two held-out null stresses,excluded from the calibration family:
1. Gaussian rho.6 followed by a3x scale step after day136.
2. rho.6 with Gaussian components plus symmetric10-unit jumps with probability.01,
   divided by sqrt2 before private/common mixing; a different heavy-tailed law.

Calibration500independent pseudorandom paths per profile; validation500new paths
per each of10profiles. Calibration seeds321000+10000*profile_index+rep;
validation1321000+10000*profile_index+rep; bootstrap2321000+10000*index+rep.
These integer sets are disjoint. PCG64/library-version behavior is pinned;
probability statements assume the declared independent Monte Carlo sampling law.

Power alternatives add{.1,.25,.5}to coordinate0 only,using the SAME first200held-out
noise paths of each of the8baseline profiles. Other coordinates stay null.
Use algebraic translation of the same intervals; do not rerun RNG or pretend
these matched comparisons are independent samples. Effect units are nominal
long-run daily SD,not monetary return,fee-adjusted edge or market predictions.

## Exactly four procedures and finite calibration

1. iid Gaussian/Bonferroni3coordinate interval: negative control.
2. R320 circular14day percentile/Bonferroni3coordinate interval,400resamples per
   path,registered per-path bootstrap seed: incumbent control,not modified.
3. Calibrated overlapping batch means(OBM),block14days.
4. Calibrated OBM,block28days.

For a complete n273sample,mean is over ALL days. For each b,all n-b+1contiguous
batch means are retained; variance of the full-sample mean is

`se² = b/((n-b)*(n-b+1)) * sum_i(batch_mean_i-full_mean)²`.

Compute centered cumulative sums for numerical stability. This formula has
expectation sigma²/n under iid equal variance,not universal finite-sample
coverage under dependence. The null calibration supplies a finite-family check.

The calibration statistic is max(abs(mean_j/se_j),j=1..3). For each of16
profile/block cells,sort500statistics. Pick the smallest order k whose
P[Binomial(500,.95)>=k] <= .01/16. Hand arithmetic/independent SciPy oracle
already establish k490; that is a deterministic tolerance calculation,not an
observed Monte Carlo cutoff. For each block take the MAXIMUM of its eight
profile k-th statistics. No favorable-profile selection or threshold tuning.

For a fixed continuous null CDF F and independent calibration paths,
P[F(T_(k))<.95]=P[Binomial(500,.95)>=k]. Bonferroni over16cells thus gives at
least99percent confidence OVER calibration draws that all specified null CDFs
have at least95percent coverage using their relevant block cutoff. The maximum
across profiles preserves each bound. This is not99percent path coverage or
coverage for an unknown market process,an unlisted distribution,or arbitrary
within-path mixtures. A missing/degenerate calibration cell withholds new-method
intervals; it does not create an infinite cutoff or a fallback success.

Per-block three-coordinate family coverage is separate. Choosing whichever
block rejects would create another multiplicity problem. No such choice occurs
here. Any future market application needs a separately frozen method choice or
predefined concordance and its cost/timing/capital/null controls; all actual
market-eligibility/order flags remain false.

## Held-out checks and predeclared acceptance

Retain5000base held-out path rows and all136held-out cells:
8profiles×4effects×4procedures=128cells,plus2null stresses×4procedures=8.
Calibration contributes16cells: **152 diagnostic trials** in the registry.
There are4procedures,9000unique generated noise paths,0strategy trials and
0new prospective paper days. Resamples/reproductions are not extra strategy
variants; no parameter/profile/procedure cell is hidden.

For each null cell report family exclusions,count,all original/unscored paths
and exact Clopper-Pearson95percent intervals with Bonferroni over40null cells.
Do not use Wilson/normal-score intervals as exact confidence statements.
For each non-null cell report positive detection of coordinate0,wrong signs,
false exclusions of coordinates1/2 and exact detection intervals with96-cell
adjustment. Power cells share their stated null-path noise; between-cell
independence is not assumed by Bonferroni.

A calibrated method is only a finite synthetic candidate if ALL10null profiles
are present/complete,no duplicate profile,each point estimate <=5percent and
each adjusted exact interval upper bound <=5percent. The nominal size target
is not loosened. It must also detect at least20percent at the PRESELECTED
Gaussian rho.6/effect.5 cell. Retain failure or low power,including if neither
new procedure qualifies. iid/incumbent controls cannot become accepted by a
new name. No winner is selected or deployed from these diagnostics.

Cost sensitivity1x/2x/3x is not applicable to these statistical-loss experiments:
monetary net returns remain unknown,not0. New market work must separately
freeze all three executable-cost labels and compare equal capital/risk.
Read all conclusions against the prior program9,478,786trials,not just this
finite family; no global adaptive false-discovery control is claimed.

## Primary input investigation and review limits

One bounded source agent used4static GETs/91,022response-body bytes/about1.43s,
within1MiBcombined/256KiBper body/90s,no redirect/retry/login. Selected official
protocol constants,collateral helpers,public prefix layout and generated SDK
models narrow the input gap. Historical Funding.value remains an unscaled
string without API/deployed cash mapping; generic funding-rates client is not
the historical fundings serializer. Conditional prefix unit algebra is NOT an
implemented/verified cash converter. Public circuit fields do not imply an
authentic freely accessible historical endpoint. All weak interpretations and
exact received/read/unread/deployment/scale gaps stay in sources/review notes.

No new source-method/alias row is needed; supplementary evidence joins the
existing canonical records. BUSL/SDK bodies remain ignored cache,not installed
or mirrored. No subscription/login bypass,market/history/account/RPC request,
weights,secret,order or money movement. Historical allowance remains one7757/
8000requests and reported229.85/250MiB spent,not a renewed budget.

The same single reviewer independently checked OBM coefficient,tolerance order,
Clopper-Pearson/numerical edge cases BEFORE freeze; deterministic counterexamples
were corrected. This limited signoff does not audit the generator/runner/max-t
construction or promise market coverage. Exact reviewed hashes are retained.
An independent literal checker uses SciPy binomial tails,direct windows and
selected literal resamples,with the SAME registered generator(separate scope).

Reproduce all deterministic output bytes in a fresh directory and run the audit.
Preserve every failed/negative/control result. Verdict may establish PARTIAL
inference engineering in a finite synthetic family,never positive net alpha or
permission for a prospective paper strategy. No existing journal or gate changes.
