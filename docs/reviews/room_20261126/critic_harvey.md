# Critic: Harvey (2017) Bayesianized passes (addendum 2026-11-26b)

Scope: METHOD_LIBRARY Harvey entry (docs/METHOD_LIBRARY.md:156-176), addendum (docs/reviews/december_decision_20261125.md:129-137), CLAUDE.md Harvey bullet (CLAUDE.md:137-139), the eight PREREG.md files, forecasts.csv rows F008-F016 and F036. No journals opened. Code I ran: /tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/critic/harvey_check.py, extra.py, tdf.py (normal and Student-t p-values; a Simpson integral, since scipy is absent).

## Verdict

The formulas and nearly all table cells are right. Three things are wrong or unsupported: (1) the R530 prior is the pass probability, not the prior the lab's own revision gives; (2) the addendum misreads section 2 for R520 and R524 and is silent on R509's look-1 stake; (3) the rule lets a bound below 10% license money, and the Kraken stake sits on a knife edge that depends on a normal reference.

## 1. Formulas against harvey.txt

- "the MBF is simply exp(–Z2 /2)" (harvey.txt:1254); "a z-score of 2.0 ... corresponds to an MBF of 0.14" (1255-1256). Recomputed: exp(-2) = 0.1353. Correct.
- "The MBF is the lower bound among all Bayes factors" (1199). So "P(null) ≥ MBF·PO/(1+MBF·PO)" is right as a bound. Harvey writes it as an equality (1436-1441), which is looser than the lab's wording.
- SD-MBF "–exp(1) × p-value × ln(p-value)" (1277; caption 1302). Matches the lab.
- p is two-sided. "a z-score of 2.0, which has a p-value of 5%" (1255) is two-sided. Table III Panel B: "find the test statistic, S, corresponding to p-value/2" (1593-1594). Solving the SD-MBF threshold at 1:1 and 5% gives z = 2.928 only with the two-sided p, which matches Harvey's "2.93" (1704). The lab's `2*(1-Phi(z))` is the right convention. R530's bootstrap p is one-sided ("The bootstrap p is the share of 10,000 means ... at or below 0", xyzbal_fwd/PREREG.md:104), so doubling it (0.02 at p<0.01) is correct.
- Table III reproduces: 2.4267 (1:1) and 2.943 (4:1) for MBF, against "2.43" and "2.94" (1697-1701). SD-MBF 2.928 against "2.93" (1704, 1717).
- Harvey errors not to copy: 1259 "exp[–2.62 /2]" should read 2.6 (exp(-2.6²/2) = 0.034; 2.62 gives 0.032). His example "t of 2.6 ... p-value of 0.014" (1258) is not the two-sided normal p for 2.6 (0.0093). His SD-MBF of 0.162 (1707) uses 0.014; with 0.0093 it is 0.118. The lab must compute p from z, not copy Harvey's example. Line 1591 "S = (−2 × ln(...))" lacks the square root; the root reproduces 2.43 and 2.94.
- METHOD_LIBRARY table, recomputed (harvey_check.py): R510 2.8% / 9.0%; R509 5.1% / 15.3%; R523 1.3% / 5.0%; R527 1.6% / 6.1%; R521 9.3% / 25.7%; R530 18.3% / 41.6%. The table prints R530 SD as 41%; it rounds to 42%.

## 2. Bars, looks and priors

| Lane | Bar, quoted (PREREG path:line) | Looks | Table row | Check |
|---|---|---|---|---|
| R510 | "PASS if all hold: • Newey-West t (lag 5) of fund_book ≥ 2.5" (xfund_eea_fast/PREREG.md:42), same at look 2 (:43) | 30, 45 days | 2.5, prior 0.60 | bar right |
| R523 | "PASS if NW t (lag 5) of the combined fund_book ≥ 3.0" (gap_combo_fast/PREREG.md:27) | 20, 30 | 3.0, 0.45 | right |
| R527 | "PASS if NW t (lag 5) of the combined fund_book ≥ 3.0" (gap_combo3_fast/PREREG.md:33) | 20, 30 | 3.0, 0.40 | right |
| R521 | "PASS if NW t (lag 5) of fund_book ≥ 2.5" (xfund_dhl_fast/PREREG.md:28) | 30, 45 | 2.5, 0.30 | right |
| R509 | "Newey-West t (lag 10) of net_book ≥ 2.5" (xfund_eea_fwd/PREREG.md:66), same at look 2 (:67) | 90, 180 | 2.5, 0.45 | right; look 2 has no row |
| R520 | look 1 "PASS if NW t (lag 10) ... ≥ 2.5" (xfund_dhl_fwd/PREREG.md:46); look 2 "PASS if NW t >= 2.0" (:49) | 90, 180 | absent; addendum uses 2.0 | missing row |
| R524 | "PASS if NW t (lag 5) of fund_book ≥ 2.5" (xfund_bfx_fwd/PREREG.md:38); "otherwise CONTINUE after look 1, and FAIL at look 2" (:40) | 90, 180 | absent | look-2 bar not written |
| R530 | "PASS at a look (20 traded weekends with p < 0.01, or 30 ... with p < 0.04)" (xyzbal_fwd/PREREG.md:108) | 20, 30 weekends | 2.33, 0.23 | look 2 (z 1.75) missing |

- Sequential rules. Every lane has two looks. R510, R509, R521, R523 and R527 use one bar at both looks; R510's Bonferroni note is "needs z ≥ 1.96; 2.5 is used" (xfund_eea_fast/PREREG.md:69). R520 uses a 2.0 bar at its last look and states "about 0.006 + 0.023 ≈ 3%" (xfund_dhl_fwd/PREREG.md:50). R530's alphas "sum to 0.05" (xyzbal_fwd/PREREG.md:114), and its PASS is a conjunction with three extra conditions (:109-112), so the table's p-alone number is not the PASS. R512's anytime e-value (E ≥ 40) is "Reported, not decided" (xfund_dhl_fwd/PREREG.md:42-43, :53).
- Is the fixed-t translation exact? Bayes factors are likelihood statements, so optional stopping does not invalidate the MBF of the observed statistic. It is not exact here because the z is a Newey-West t on 20-45 overlapping daily values, read against a normal reference. That matters (section 3e).
- Priors. The ledger rows are F008 R510 0.60 (registry/forecasts.csv:9), F009 R509 0.45 (:10), F010 R512 0.40 (:11; no bar or read in the table or addendum), F011 R523 0.45 (:12), F012 R527 0.40 (:13), F013 R521 0.30 (:14), F014 R520 0.10 (:15), F015 R524 0.10 (:16), F016 R530 0.36 (:17), revised by F036 to 0.23 (:37). F008-F015 match "R510 0.60, R509 0.45 ... R524 0.10" (docs/reviews/december_decision_20261125.md:66-67). F016 matches "P(PASS) = 0.35 × 0.92 + 0.65 × 0.06 ≈ 0.36" (xyzbal_fwd/PREREG.md:149).
- The conflation. The table sets PO = (1−P)/P with P the pass probability. Harvey needs π, the prior that the effect is real. The lab's own identity is P(PASS) = π·power + (1−π)·α (xyzbal_fwd/PREREG.md:149). The revised R530 is "π ≈ 0.20, so P(PASS) ≈ 0.23" (docs/reviews/room_20261125/synthesis.md:129-130). With π = 0.20, PO = 4.0, MBF 21.1%, SD 46.0%. The table's 18% and 41% are too low. With the PREREG's π = 0.35 ("Prior π ≈ 0.35", xyzbal_fwd/PREREG.md:145), it is 11.0% and 28.3%. For R510, with power 0.84 at 2.4x ("| 2.4x ... | 84% | 66% |", xfund_eea_fast/PREREG.md:61) and α ≈ 0.006, π ≈ 0.71, PO 0.40, SD 5.7% (the table says 9.0%). The sign of the error flips between lanes, so the table is on no single basis.

## 3. Is the rule right?

Sensible: a floor that keeps weak passes out of money, fixed before the reads, and cheap to apply.

a. Wrong R530 numbers. The rule still triggers (SD 46% > 10%), so the decision holds, but the addendum's figures are off (section 2). The addendum's ranges "9-55%" and "26-78%" (december_decision_20261125.md:134) do recompute (R521 9.3 / 25.7; R520 look 2 54.9 / 77.5), but the top of both comes from R520's 2.0 look, which is not in the table.

b. Misreading of section 2. The addendum says "§2 already gives no stake on R521, R520 or R524 alone" (:136). §2 says "No stake on this pass alone" only for R521 (december_decision_20261125.md:39). For R520 and R524 full looks it says "Scale decisions, at the bar of §1" (:40). So the new rule is the first control on R520 and R524, and "this binds mostly R530" (:136) is wrong.

c. R509 is not mapped. R509's look-1 pass (t 2.5, prior 0.45) gives SD 15.3%. By the rule that is a second period, not money. But R509's PREREG says "A frozen small-stake plan, run through `lab.gate.go_real()`" (xfund_eea_fwd/PREREG.md:75). The addendum does not say which wins. Its look 2 is the last look, so "a second forward period" has no meaning there.

d. A floor used to license money. Harvey's bound is a floor on P(null). Below 10% it shows only that the null is not ruled out. It does not show the null is unlikely. The addendum keeps the Kraken stakes on 5-9% ("The mapping in §2 stands", :133). Blocking on a high floor is valid. Licensing money on a low one is not. This is the main logical flaw.

e. Knife edge for R510, and a dependence on the reference distribution. R510 gives SD 8.99% at prior 0.60. The rule flips to "no money" at a pass probability of 0.571 (extra.py). Read the same t against a Student-t with 29 degrees of freedom (30 days), the two-sided p is 0.0183 and SD is 11.7%, which flips it. R523 at 19 df gives 10.7%, which also flips (tdf.py). The lab's bars are normal (xfund_eea_fast/PREREG.md:69, "z ≥ 1.96"), so the table is consistent with them. But the Newey-West t on 20-45 overlapping days is not normal. The Kraken money decision rests on this choice, and the addendum does not state it.

f. Correlated reads not combined. R509, R510, R523 and R527 all read the Kraken + Hyperliquid book. The addendum sends the same €2,000 from whichever passes first (december_decision_20261125.md:41). Each read gets its own floor, but the chance of a false stake is not the smallest of them. The lab's own note says "the chance of a false stake is at most the sum of their sizes" (gap_combo3_fast/PREREG.md:70-71). Harvey gives no joint figure.

g. Time cost. A second period of 180 days after R520's look 2 at t 2.0, and a second period for R530 (about April 2027 per :136), are real delays. They are not money losses.

## 4. Decisions the rule makes worse

- R509 look 1: a pass that its PREREG says earns a stake now earns a second period. That changes a frozen outcome without a dated note. If that is intended, the addendum has to say so.
- Kraken: the rule allows €2,000 at a 9% floor while it blocks R530 at 18-46%. That asymmetry comes from the knife edge in 3e, not from the evidence.

No other decision is obviously worse.

## 5. Fixes before December

1. Recompute R530 with π = 0.20 (synthesis.md:129), add look 2 (p < 0.04, 42-69%), and correct 41% to 42%.
2. Correct addendum :136 and what §2 row 40 says. State what R509 look 1, R520 and R524 now do.
3. Use the rule as a block only. Do not read a floor below 10% as clearance. Either state the reference distribution used for the NW t (and show R510 under Student-t), or gate the Kraken stake on the measured forward edge.
4. Add the R520 look-2 row (t 2.0) and the R524 look-2 bar to the METHOD_LIBRARY table.
5. Add to the Harvey entry: his p = 0.014 example is inconsistent, so compute p from z.

## Checked and fine

- MBF and SD-MBF formulas, the two-sided p convention, the Table III values (2.43, 2.94, 2.93) and the Table II worked example (0.147 gives 0.37 at 4:1).
- Bars in the METHOD_LIBRARY table match the PREREGs for R510, R523, R527, R521, R509 and R530 (up to the look-2 gaps above).
- Ledger values F008-F015 match december_decision_20261125.md:66-67, and F016 and F036 match xyzbal_fwd/PREREG.md:149 and synthesis.md:130.

Weakest link: the normal reference for the Newey-West t (3e), and the use of pass probability as prior (section 2).
