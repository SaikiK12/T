# referee (deepseek-v4-pro)

The unlock/ADV < 0.82 filter was derived by inspecting the six worst losses **after** the run. That is textbook post‑hoc conditioning—the filter is a function of the same sample used to measure performance, guaranteeing an inflated in‑sample fit. To be admissible, the filter must be:

1. **Frozen in a pre‑registered rule before any outcome data is seen.** Since the forward lane R266 is already running with fixed tickets, a filter chosen now cannot be retroactively applied to those tickets; doing so would contaminate the clean forward window. A new, separate preregistration must define the filter and a fresh holdout period (e.g., events after a future cutoff) entirely unseen at the time of writing.

2. **Tested on a strictly out‑of‑sample set.** For example, if the filter is to be used in the next phase of unlocks_fwd, the decision rule must be uploaded to the registry before the first event to which it applies. Any overlap with the data that revealed the <0.82 pattern (here, all history through 2026‑09) would invalidate the test.

Beyond the dose filter, the evidence pack invites other false-positive traps:

- **Selection on the same sample:** Ten variants were logged, and the primary was chosen post hoc as the best performer (or at least reported as the “primary”). While gate‑0 preregistration partially mitigates this, the dose splits and the ADV split were all examined after the fact. The clean forward lane must commit to a single predefined rule; otherwise, multiplicity across variants inflates the family‑wise error rate.

- **Tail risk masquerading as edge:** The per‑event returns have a standard deviation of 16.7% and extreme outliers (e.g., RIVER –132% gross). The week‑clustered t‑test assumes roughly symmetric, thin‑tailed distributions. With such kurtosis, the t‑statistic can yield false positives because a few enormous squeezes may drive an apparent edge even if the true mean is zero. Any admissible forward test must pre‑specify a robust metric (e.g., win‑rate or median return) or a non‑parametric test, and must include a per‑event size cap and a written plan for squeezes as the pack itself warns.

- **Multiplicity:** The program has run ~9.8 million trials. Even with a registry, residual data‑snooping bias from the many “harmless” looks can creep in if any post‑hoc tuning is allowed. The only admissible path is a completely hands‑off, preregistered forward evaluation with no interim adjustments.

To avoid a false positive from the unlock/ADV filter, it must be treated as a new hypothesis—not as a rescue for the six bad losses—and validated on events that occur after the filter is invented and frozen.
