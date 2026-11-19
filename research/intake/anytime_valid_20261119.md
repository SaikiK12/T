# Anytime-valid inference for forward paper lanes (deep reading, 2026-11-19)

- **Asked by the owner (2026-11-19):** read whole books and papers as a statistician would, and cut the waiting time
  of forward lanes.
- **Who did it.** One research agent read the sources below, from legally free arXiv versions. The session re-ran its
  simulations, wrote `lab/anytime.py` and its tests, and adopted the rule in R512.
- **Tags.** VERIFIED = read in the source, or checked by computation or simulation. UNVERIFIED = neither.

## What was read (exact scope)
| Source | Read | Not read |
|---|---|---|
| Ramdas, Grünwald, Vovk, Shafer, "Game-theoretic statistics and safe anytime-valid inference", Statistical Science 2023 (arXiv 2210.01948v2) | all 25 pages, Appendices A-B | the reference list, skimmed only |
| Waudby-Smith & Ramdas, "Estimating means of bounded random variables by betting", JRSSB 2024 (arXiv 2010.09686v7) | pp. 1-25 (Sections 1-7), Appendix B.1-B.8, C.1, E.4-E.6 | proofs (App. A), C.2-D, E.1-E.3, F |
| Howard, Ramdas, McAuliffe, Sekhon, "Time-uniform, nonparametric, nonasymptotic confidence sequences", AoS 2021 (arXiv 1810.08240v9) | pp. 1-14 (sub-ψ definitions, linear and stitched boundaries, mixtures, empirical-Bernstein CS, Thm 4) | §4.3 onward and all appendices, including its one-sided normal mixture |
| Waudby-Smith et al., arXiv 2103.06476v9 | pp. 4-12 (Def. 2.1, Thm 2.2, Prop. 2.5) | the rest |
| Ge & Liu, arXiv 2610.29288v2 (HAC asymptotic confidence sequences) | pp. 1-3, 8-14 (Thm 3.1, Cor. 3.1, Conditions 3.1-3.3, Thm 3.3) | the rest |
| Han & Qu, arXiv 2608.30502 | abstract only | everything else |

These are not whole books: three papers were read in the scopes above, and two others in part.

## Results the lab uses
- **Ville's inequality [VERIFIED].** For a nonnegative supermartingale with M₀ = 1, P(∃t: M_t ≥ 1/α) ≤ α.
- **Exact one-sided test of a mean [VERIFIED].**
  - K_t = ∏(1 + λ_i X_i), with predictable λ_i in [0, 1/L], is a test supermartingale for H0: E[X_t | past] ≤ 0
    when X_t ≥ −L.
  - Only the loss side needs a bound. It holds under any dependence, for the conditional null.
- **Dependence [VERIFIED by simulation].**
  - The economic question (unconditional mean ≤ 0) is larger than the conditional null.
  - With autocorrelated daily nets, exact betting is conservative at negative autocorrelation (size 0.002 at
    AR(1) −0.2) and anti-conservative at positive autocorrelation (0.068 at +0.2).
  - Weekly batching costs about 7x in the bet cap, so it was rejected.
- **Speed [VERIFIED by simulation].** Exact betting with a loss bound L = 1% is not faster than a fixed 90-day
  Newey-West look on a series like R508's (mean 6.6, sd 18 bp/day):
  - median 80 days at E ≥ 20;
  - only 0.16 of paths decided by day 90 at a size matched to the fixed rule (about 0.014).
  - The bound caps the bet far below the Kelly bet.
- **What is faster [VERIFIED by simulation, re-run by the session].** The asymptotic HAC mixture monitor (`lab.anytime`):
  - **Method:** a one-sided normal mixture on S_n / σ̂_LR, with ρ tuned for n = 90 and α = 0.025, a 30-day burn-in,
    and E ≥ 40.
  - **Size over 720 days:** 3.0% i.i.d., 2.2% at AR −0.2, 4.2% at AR +0.2.
  - **Median crossing** at a mean of 6.6 bp/day: day 47 (i.i.d.) or day 38 (AR −0.2).
  - It is asymptotic only. Its size is a simulation figure, not a guarantee.
- **The funding part alone (mean about 6, sd about 8 bp/day) [VERIFIED by simulation].** R510's fixed 30-day look
  already decides in about 30 days. No sequential method was materially faster.
- **Several lanes at once [VERIFIED in the source].**
  - Multiply e-values only for conditionally independent lanes; crypto lanes are not.
  - Averaging with pre-set weights is valid under any dependence.
  - For claims about individual lanes among K, use e-BH or a threshold of K/α.

## Adopted
- `lab/anytime.py`: the HAC mixture monitor, with tests (`tests/test_anytime.py`), including a check of the closed form
  against numerical integration.
- R512 `xfund_eea3_fwd` decides by it.
- R509 and R510 keep their frozen fixed-sample looks.

## Open
- **A heavy-tail book.** A book with rare large losses (for example −10% days at p = 0.0066) passes both the betting
  rule and the fixed Newey-West rule about half the time in 90-180 days [VERIFIED by simulation]. No short test
  excludes it. Small stakes and the kill switch are the guard.
- **Regime monitoring after a pass.** An e-detector (Ramdas et al. §5.7) is not built.
