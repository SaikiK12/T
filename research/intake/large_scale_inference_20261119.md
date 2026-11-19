# Large-scale inference for the program's multiplicity (deep reading, 2026-11-19)

- **Asked by the owner (2026-11-19):** read as a statistician would. One research agent read the sources below; the
  session checked the registry facts.
- **Tags.** VERIFIED = read in the source, or checked by computation or simulation. UNVERIFIED = neither.
- **Efron's book was not read.** "Large-Scale Inference" (Cambridge 2010) is no longer free in full: only its contents
  and prologue (7 pp.) were read. Efron's own free papers covering the same material were read instead.

## What was read (exact scope)
| Source | Read | Not read |
|---|---|---|
| Efron, Large-Scale Inference (2010) | free excerpt only: contents and prologue, 7 pp. | chapters 1-10 |
| Efron (2008), "Microarrays, empirical Bayes and the two-groups model", Stat Sci (preprint) | main text, pp. 1-31 (the material of LSI ch. 2, 4-6) | discussion |
| Efron & Hastie, Computer Age Statistical Inference (author-posted) | ch. 15 (pp. 271-297), §20.3 (pp. 408-412) | ch. 6, 7, 21 and the rest |
| Efron (2011), "Tweedie's formula and selection bias" | pp. 1-20 | the rest |
| Efron (2010), "Correlated z-values and the accuracy of large-scale statistical estimates" | §1-2, pp. 1-8 | the rest |
| Efron (2008), "When should hypothesis testing problems be combined?", AoAS | §1-3, §5 | §4, §6 |
| Harvey, Liu & Zhu (2016), "...and the Cross-Section of Expected Returns", RFS (author copy) | journal pp. 11-37, Appendix B | §1-2, Appendix A, tables |
| Harvey & Liu (2015), "Backtesting", JPM (author copy) | pp. 13-28 | "Evaluating Trading Strategies" (SSRN refused) |
| Bailey & López de Prado (2014), "The Deflated Sharpe Ratio" | eq. 1-2, Appendices A.1, A.3 | the rest |

## The registry, checked by the session [VERIFIED]
- `registry/rounds.csv` holds 291 rounds (R143-R512); 285 carry a trial count, 9,785,753 in total.
- **One round dominates.** R192 (`atlas_ctx`) alone holds 8,320,806 trials (85%). The six largest grids hold 99.84%.
- **Bonferroni bars (one-sided 5%) by the unit counted** [VERIFIED arithmetic]:

  | Unit | Count | z* |
  |---|---|---|
  | all trials | 9.79M | 5.73 |
  | trials outside the six grids | about 15,300 | 4.51 |
  | carry-family trials | about 1,170 | 3.93 |
  | rounds | about 290 | 3.58 |
  | lane families | 14 | 2.69 |

## Results the lab uses
- **Two-groups model [VERIFIED].**
  - f = π0 f0 + π1 f1. Fdr(z) = π0 S0(z)/S(z); local fdr(z) = π0 f0(z)/f(z).
  - Benjamini-Hochberg is the rule estimated Fdr ≤ π0 q. Checked by simulation.
- **Correlation [VERIFIED by simulation].** Fdr estimates stay nearly unbiased when tests are correlated, but their
  variance grows with the root-mean-square correlation.
- **Tweedie's formula [VERIFIED by simulation].** E[µ|z] = z + σ² l′(z), with l = log f. It is the program-level
  shrinkage of an observed z.
- **The deflated Sharpe's effective number of trials, N̂ = ρ + (1−ρ)M, does not depend on the threshold**
  [VERIFIED by simulation].
  - With M = 10⁶ and equicorrelation 0.6, the true effective number is 106 at z = 2 and 82,667 at z = 5.73.
  - The formula gives 400,001 at every threshold.
- **Harvey-Liu-Zhu's adjusted thresholds** (Bonferroni, Holm, BHY; about 3.0-3.9 for their factor zoo) were read.
  - The haircut-Sharpe example was re-computed [VERIFIED]: Sharpe 0.75 over 240 months, N = 200 → 0.32.

## What it says about the lab's practice (the agent's reading, weighed by the session)
- **The 9.8M-trial Bonferroni bar is the wrong family for a confirmatory test.**
  - A frozen single candidate on unread data (R511) was not selected from those trials. Its own p is valid for its
    own null.
  - The grid history changes the prior of the hypotheses the lab chooses to confirm, not the null of the new
    statistic.
  - The agent recommends a family structure:
    - the round as the unit;
    - multiplicity inside a round by a max-statistic bootstrap (Reality Check, SPA, Romano-Wolf);
    - the lane family above it;
    - online FDR over the stream of confirmations (LORD/SAFFRON: not read, UNVERIFIED).
- **A rough empirical-Bayes run** [computed by the agent; precision is low, only 1-4 rounds lie above z = 4.81].
  - **Data:** 114 parsed round t-values.
  - **Probability that R511's t = 4.81 reflects a real positive edge:**
    - about .75-.98 under empirical nulls;
    - above .999 under the theoretical N(0,1) null.
  - **Tweedie shrinkage:** R511's +13.46%/yr shrinks to roughly 5-13%/yr at program level.
  - **Carry-family prior** (12 replication sets): mean Sharpe about 4.3, between-set sd about 1.8.
  - **The decisive input is how well the lab's t-statistic null is calibrated, not the trial count.**
- **R511 confirms breadth, not persistence.** It covers the same year as R508, so a shared 2026 regime would correlate
  them. Persistence has to come from the forward lanes (R509, R510, R512).

## Open (not done)
- **No machine-readable decided z per round.** Free-text notes make extraction error-prone. A `decided_z` field, plus
  flags for selection and data read, would let this run properly.
- **R511's t is not calibrated.** The suggested calibration is a coin- and week-clustered bootstrap plus placebo books
  (random direction, shifted funding dates). R511's top 10 days hold 40% of its P&L.
- **Online FDR for confirmations** is not adopted.
