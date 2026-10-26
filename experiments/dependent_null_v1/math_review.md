# R321 pre-freeze mathematical review

**Targeted recheck: no known blockers in the latest reviewed module/tests.** This is limited mathematical/numerical signoff for the two files and hashes below, under the specified synthetic-null assumptions. It does not audit the generator, registration/freeze wrapper, RNG policy, max-statistic construction or production run. No Monte Carlo paths, production calibration, market statistics, network calls or production edits were used.

## Exact revisions and checks

Latest full read: `lab/dependent_null.py` lines1-136, SHA256 `9065b71bc338accd9bf3ce3ea9117c32193338bccf58fb84e030d0f70bd7f577`; `tests/test_dependent_null.py` lines1-68, SHA256 `63ac28486bf4b5c2b7bad1ec0d1c3baedb6dcb3002c2a9a8f95030871cebe9d2`.

Initial full read: module1-116 SHA256 `4e9143b4fbb54f98e4459ed37a4778056635ea045dcc75b64395252d2d567396`; tests1-54 SHA256 `cafa3503d00d76c3737506197aeb33b75f80cd2d2618dbef3f28af34b7a6c87d`. Counterexamples below were sent to root and corrected before freeze. Initial5tests and revised6tests all passed; revised command `python3 -m unittest tests.test_dependent_null -v` completed6tests in0.006s. These were deterministic tests. Hand calls to calibrate used explicitly filled ones/zeroes only, not generated Monte Carlo statistics.

## OBM equation: correct, retaining all273 observations

The implemented variance of the full-sample mean is

`v_hat_mean = b/((n-b)*(n-b+1)) * sum_{i=0}^{n-b} (mean(x_i...x_{i+b-1}) - mean(x_0...x_{n-1}))^2`.

The usual OBM long-run variance estimate has an extra factor n; division by n for variance of the mean gives this coefficient. There are260 windows for b14 and246 for b28 at n273. Every observation enters the full mean and at least one variance window; endpoints have fewer windows but are retained. Under iid equal-variance data, each centered batch term has expected square sigma2*(1/b-1/n), giving expectation sigma2/n. This is not exact unbiasedness or finite-sample coverage for arbitrary dependence.

Independent literal-window calculations for impulses at indices0,136,272 and coordinate scales1,2,-1 agree for both blocks; maximum observed absolute variance discrepancy1.16e-19. The existing central-impulse fixture uses the correct count b of containing windows and correct denominator. Shift/scale invariance holds in exact arithmetic.

## Order statistic and maximum over profiles: correct under assumptions

For independent path statistics T_1...T_m from one fixed continuous null CDF F, q=1-alpha and U_i=F(T_i) iid Uniform(0,1):

`P[F(T_(k)) < q] = P[Binomial(m,q) >= k]`.

The tail direction and sorted index k-1 are correct. Bonferroni over16cells bounds the probability that any declared cell has CDF coverage below1-alpha. Cross-cell independence is unnecessary; independence within each cell's m paths and the specified null law are required. Continuity gives the displayed equality; ties require a weak/conservative formulation with a consistent rejection rule.

With defaults m500, alpha.05, confidence.99,16cells: **k490**. Cell budget0.0006250000000000006. Independent SciPy `binom.sf(489,500,.95)` gives0.0004600071542669869; code gives0.000460007154266826 (absolute difference1.61e-16). Previous k489 fails with tail0.001143788133601848. The resulting union-bound confidence is at least0.9926398855317282. These are exact-binomial-formula probabilities evaluated in floating arithmetic.

Additional deterministic oracle checks: m20/alpha.499/confidence.9/onecell gives k14/tail0.05870141854299703; m2000/alpha.05/confidence.99/16cells gives k1931/tail0.0005062728402873203; m500/alpha.1/confidence.999/32cells gives k476/tail0.000016176579643574928. Each preceding order exceeds its budget. Insufficient m20/default and m500/alpha.01/default cases correctly raise rather than supply an infinite cutoff.

For each block b, c_b=max over8profile order statistics. On the simultaneous calibration event, `F_(p,b)(c_b)>=F_(p,b)(T_(k,p,b))>=.95` for every declared profile p. The maximum thus preserves each per-profile bound. It does not validate an unlisted process or a dynamic within-path mixture.

## Initial blockers and verified corrections

- Constant decimal data originally passed OBM: all0.1 gave artificial se1.0002212394606406e-16 and t9.997788094754361e14; a single constant column alongside impulses also passed. Revised line39 detects exact per-column constancy against the reference row, without an epsilon. Both now return DEGENERATE.
- Finite±1e308 or large constant values originally yielded ASSESSED NaN/Inf iid endpoints. Revised moment/endpoints checks fail closed. Both iid and OBM now return DEGENERATE on these fixtures.
- Finite OBM inputs with a finite huge cutoff originally yielded ASSESSED ±Inf intervals. Revised lines101-105 return DEGENERATE/None endpoints. Confirmed with central1e150 impulses and cutoff1e308; revised test separately covers impulses1000/2000/3000.
- Original Wilson intervals did not have nominal finite-sample simultaneous assurance. For n500/comparisons40/p=.0001, actual one-cell coverage was0.9512270463 versus nominal0.99875. Root removed Wilson and implemented exact Clopper-Pearson with Bonferroni tails.

New Clopper-Pearson formula is correct: lower BetaInv(tail;s,n-s+1), upper BetaInv(1-tail;s+1,n-s), with0/1boundary conventions and tail=.05/(2*comparisons). Independent binomial sf/cdf at interval endpoints, for counts0,1,10,250,499,500 and comparisons1/40, matches target tails with maximum absolute residual5.59e-15. Deterministic binomial enumeration at p=.0001,.001,.05,.5 gives per-cell coverage0.9999800483,0.9998306363,0.9990691370,0.9989243530 respectively, all at least0.99875. The mathematical exact-coverage claim is up to numerical evaluation, not symbolic arithmetic.

## Conditions outside this limited signoff

1. Three-coordinate family coverage requires each supplied path statistic actually be max(abs(t_1),abs(t_2),abs(t_3)) from this same OBM rule. Input shape/finiteness checks cannot certify construction, independence or continuity. Eight unique IDs do not establish the registered named profile family.
2. The16-cell adjustment is for calibration confidence. It does not allocate future rejection alpha across the two block methods. Separate95% family coverage statements are supported; choosing whichever block rejects is not a combined5% test (union bound10% without a further rule). Comparisons with iid/circular methods add multiplicity if selected jointly.
3. At least99% probability over calibration draws that declared synthetic CDFs have at least95% coverage is not99% future-path coverage. Evaluation paths need the declared distribution and appropriate independence from calibration. Tuning profiles, seeds or cutoffs on held-out outcomes changes the argument.
4. Freeze the profiles,2blocks,3coordinates, statistic, path counts, seed policy, failure handling, alpha and comparison family before generated outcomes. Filtering/resampling degenerate paths until500 valid draws calibrates a selected/conditional law unless explicitly part of the target. Array acceptance is not such a proof.
5. Gap checks use Python int differences and correctly reject uint64 wrap, missing rows, nonfinite values and nonconsecutive integer IDs. Consecutive IDs do not independently prove calendar/source integrity. Underflow or unrepresentable moments may fail closed; never silently delete such paths or count them as successful coverage.
6. Exact Clopper-Pearson Bonferroni assurance requires independent Bernoulli path outcomes within each binomial count and a declared total comparison family. Dependence between separate comparisons is allowed by Bonferroni. No interval construction repairs selected stopping or an understated family.
7. Synthetic-family assurance provides no future-market coverage, return, cost or activation guarantee. `actual_order_allowed=False` and `market_evidence_eligible=False` are appropriate. No production outcomes were run in this review.

Review completed 2026-10-25T22:46:21.666927+00:00, SciPy 1.17.0. Final observed hashes:

- `lab/dependent_null.py`: `9065b71bc338accd9bf3ce3ea9117c32193338bccf58fb84e030d0f70bd7f577` (unchanged from latest reviewed version).
- `tests/test_dependent_null.py`: `63ac28486bf4b5c2b7bad1ec0d1c3baedb6dcb3002c2a9a8f95030871cebe9d2` (unchanged from latest reviewed version).
