# Critic on self-review 4 (2026-11-26)

Critic: adversarial Haiku room member. Read: `docs/reviews/self_review_20261126.md`, `room_20261126/audit_corrections.md`,
`december_decision_20261125.md` addendum 2026-11-26c, the "Numbers before narrative" habit in `CLAUDE.md:227`. Ran:
`python3 scripts/score_forecasts.py` and a Student-t tail (numerical integration) plus the SD-MBF floor. Not opened:
`experiments/*/journal/`. Nothing else edited.

## 1. Numbers against the audit and the ledger

| Number | Self-review | Check | Verdict |
|---|---|---|---|
| 144 / 102 / 29 / 6 | `self_review_20261126.md:30` "**Total** | **144** | **102** | **29** | **6**" | `audit_corrections.md:33` same row; I re-summed the page rows: 144, 102, 29, 6 | matches |
| Type counts | `self_review:33-39` (21, 15, 12, 10, 9, 7, 28) | `audit_corrections.md:48-54` same; sum 102 | matches |
| 60 of 67 | `self_review:40` "60 (90%)" | `audit:65` "**60** of 102", `audit:70` "**7**", `audit:74` "**35**"; 60/67 = 89.6% | matches; C/L/N labels are the room's judgement, not a script |
| Brier 0.199 vs 0.198 | `self_review:41` "Brier 0.199 against 0.198 leave-one-out" | script: "Brier 0.199; ... leave-one-out 0.198" | matches, but omits the script's in-sample reference "always the hit rate 0.160" that 0.199 is worse than |
| "p >= 0.6 hit 1 in 4" | `self_review:42` | script bin "0.6-1.0 | 4 | 0.70 | 0.25" | matches (n = 4) |

Two wording points in the same section:
- `self_review:4-5` "every count traced to a critic report and a corrections section". `audit:20` says "Counts are my own
  enumeration ... I did not re-run the critics' code", and `audit:104` says the critics' numbers were not checked.
- `self_review:46` "the critic was right two thirds of the time (102 of 144)". 102/144 = 71%. "Right" means "accepted by
  the page's author" (`audit:13-14`, "the page's correction section names the point"), not independently verified.

## 2. Skeptical-prior floors (my code; SD-MBF = -e·p·ln p; floor = BF·PO/(1+BF·PO); PO = (1-pi)/pi)

| Read | t (df) | p two-sided | SD-MBF | table pi -> floor | pi/2 -> floor | pi/2 with the prompt's pi |
|---|---|---|---|---|---|---|
| R510, 30 days | 2.5 (29) | 0.0183 | 0.199 | 0.71 -> 7.5% (table "**7.4%**", `METHOD_LIBRARY.md:174`) | 0.355 -> 26.6% | 0.36 -> 26.2% |
| R523, 20 days | 3.0 (19) | 0.0074 | 0.098 | 0.55 -> 7.4% (`METHOD_LIBRARY.md:175`) | 0.275 -> 20.6% | 0.28 -> 20.2% |
| R509, look 1 | 2.5 (89) | 0.0143 | 0.165 | 0.75 -> 5.2% (table "**5.3%**", `METHOD_LIBRARY.md:177`) | 0.375 -> 21.5% | 0.73 -> 5.7%; halved 0.365 -> 22.3%; 0.36 -> 22.6% |

- Verdict: the prompt's 26%, 21% and 22% hold (20.2-26.6%). The unhalved values reproduce the table within 0.1-0.2 points.
- The pi values are not one rule. R509's 0.75 is alpha = 0 (0.45/0.60). The prompt's 0.73 is alpha = 0.05
  (`audit_corrections.md:93-94`). R510's 0.71 implies alpha about 0.01, and R523's 0.55 implies alpha about 0.05. The
  table does not write alpha per row, as `audit:106-107` also notes.
- Sensitivity the self-review omits. Base-rate priors from `docs/LESSONS.md:638` ("carry 64%, settle 43%"): pi 0.43 gives
  R510 20.9%, R523 11.5%, R509 17.9%; pi 0.64 gives 10.1%, 5.2%, 8.5%. Those family figures are pass shares of decided
  tests (a P(PASS)-type quantity), so using them as pi repeats the mapping error. Still, R523's block depends on the prior.

## 3. Stake 1 under the skeptical prior: consistent, or a rationalization?

- **For (consistent).** Stake 1 is €2,000, and its loss is meant to be bounded by a stop (`december_decision_20261125.md:59`,
  "the stake is closed at a 25% loss of the stake (gate 4 proposal)"). The block rule is written for scaling
  (`december_decision:153`, "Stake 1 is unchanged: §2's rows decide it"). Measurement has value that the unhalved rule
  would throw away.
- **Against (rationalized).** `self_review:66`: "My own probabilities are halved (π/2) when they feed a money rule", and
  `audit_corrections.md:16` lists "a stake" as a money rule. Stake 1 is such a rule, and §3 exempts it. Stake 1 is also
  R510's own pass outcome (`december_decision:38`, "**Stake 1:** €2,000"; `:42`, "the stake is proposed then"). The
  pass whose floor is 26.6% is the pass that releases the money, and `self_review:50` says "All three would be blocked".
  The "bounded loss" rests on a gate-4 proposal, and no value of the measurement is computed.
- **Which is stronger:** the rationalization reading. The calibration-stake argument is reasonable, but it is an exception
  to the halving rule, written in the same addendum that computed the floors. Consistent versions: halve pi for stake 1
  too and call it a measurement cost; or write the exception before the read, with its maximum loss and the value of
  the measurement in euros.

## 4. Is "halve my probabilities" the right correction?

Halving is a uniform, direction-blind shrink. It lowers every pi by the same factor, so it corrects a level without
knowing the pattern, and nothing in the ledger calibrates it. No lane-pass forecast is resolved: F008-F015 (registry
lines 9-16) are all pending. The resolved set is R472, R473, R529, R531, O3b, O7b (three rows), L1, S1. The 60-of-67 bias
(`audit:65`) is about the direction of wording in prose, not the size of probabilities, so the factor 1/2 is a guess.
A better correction shrinks each pi toward its family's measured base rate, with weight zero until the ledger is
calibrated, and writes alpha beside each pi so that P(PASS) -> pi is fixed per row. Under that rule R523 falls to
5-12% (§2). The correction choice therefore decides a block, so the prior and its sensitivity range (pi 0.43-0.71) must
be written before the read, not as one halved number.

## 5. Cleaner than the evidence

1. `self_review:11` "Saturday one-day BTC options rich in 2022-25 (−48 bp, t −7.3)". The -47.8 bp (t -7.3, n 248) is the
   2022-26 figure (`reflection_20261125_o7.md:10`, "over 2022-26 (t −7.3)"), and the by-year row includes "2026 +14.6"
   (`reflection_20261125_greeks.md:211`). The 2022-25 pooled ±2% figure is "about −60" (`o7.md:216`). Wrong window label.
2. `self_review:10` puts "crypto 0.13%" beside "TSLA gross 18%". 0.13% is the dealer net (`greeks.md:83`). The like-for-like
   figure is "TSLA is about 2× crypto (18% against about 8%)" (`greeks.md:111`). The page's own type (c) error.
3. `self_review:12` "BTC Sunday rich in 2026 (O7d, forward)" is listed as an outcome. `open_questions.md:45` says the 2026
   figure is "post hoc", and the forward read is pending (F019, registry line 20). A status word before the observation.
4. `self_review:48-49` "those are the numbers the ledger says run high". The "1 in 4" rests on four forecasts, none a
   lane pass: R472 (0.70, 0; registry line 2), R473 (0.60, 0; line 3), O7b-sat (0.75, 1; line 6), O7b-sun-not (0.75, 0;
   line 8). The 0.45 lanes sit in the 0.3-0.6 bin, n = 3, mean 0.42, hit 0.33. That is weak evidence, not "run high".
   `audit:92` says the formula change is "right in form"; "only because" is the page's sharper claim.
5. `self_review:69` "its loss bounded by the 25% stop". The stop is a "gate 4 proposal" (`december_decision:59`), not an
   adopted rule.

Not checked: the Greeks and O7 numbers beyond the quotes above; `scripts/verify_citations.py`; the C/L/N direction calls.
