# referee (deepseek-v4-pro-0813)

1. **The unlock/ADV<0.82 filter is inadmissible as used.** It was observed after the run on the six worst losses, and Fisher exact one-sided p=0.101 on n=6 is not significant. For admissibility it must not be used in any way: no excluding low-ADV events, no high-ADV split, no tail-exemption, no covariate, no sizing adjustment. To test it now, it must be treated as a new hypothesis: pre-register a single cutoff chosen before seeing R265 losses, assign its own trial/multiplicity budget, and evaluate only on the R266 forward tickets or a never-read split. The 422 R265 events are spent; using them to validate the filter is circular.

2. **The risk-model grid is selection on the same sample.** R265’s 422 events, worst concurrent cluster (−179.5% notional, 2026-01-17), and worst week (−124.6% over 5 events) are already known. Searching c × G × K × funding-veto/stop choices for the best terminal equity or max drawdown overfits, because any cap chosen to survive the known tail does so by construction. Pre-register one primary risk rule and objective on R266; R265 can only be descriptive motivation, not parameter selection.

3. **Tail risk can masquerade as a survivable edge.** Sequential c=2% max DD −4.04% is not the portfolio path; concurrent positions must be marked jointly. A rule that survives only by avoiding the same six >40% gross losses is post-hoc conditioning, not evidence.

4. **Multiplicity:** c {1,2,3}, G {10,20,30}, cluster limits, and funding vetoes create many hidden tests. If the best combination is reported, its Sharpe/DD is inflated. Pre-specify one primary combination; others are sensitivity only.

5. **R4 funding veto cannot be tested on the committed file.** The file has realized funding over the hold, not trailing funding at entry; choosing a veto using realized funding leaks the outcome. It needs forward entry-time data.

**Cannot know from pack:** joint dependence of concurrent unlock shorts, entry-time trailing funding, intrabar liquidation/MAE path, and actual squeeze fill capacity.
