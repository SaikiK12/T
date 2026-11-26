# Self-review 4, 2026-11-26: nine cycles, 102 accepted errors, and which way they leaned

- **Previous:** `self_review_20261125.md`.
- **The numbers come first.** They are from the room's audit (`room_20261126/audit_corrections.md`, every count
  traced to a critic report and a corrections section) and from the forecast ledger.

## The cycles
| # | Subject | Lens | Kind | Outcome | Money decision changed? |
|---|---|---|---|---|---|
| 1 | Greeks: what decides a forced-flow idea | Follow the plumbing | reflection + measurements | Net forced trade ÷ window liquidity decides; crypto 0.13%; TSLA gross 18% (dealer net unknown) | no |
| 2 | Weekend option clock (O3b) | Count the chances | registered read | Saturday one-day BTC options rich in 2022-25 (−48 bp, t −7.3), closed 2026; predictions 1 of 4 | no (historical) |
| 3 | O7: widen to ETH and venues | Change the scale | registered read + screen | Same on ETH; one shared weekend model; BTC Sunday rich in 2026 (O7d, forward) | no |
| 4 | Calibration (Q25) | Invert, on myself | tool + reflection | Forecast ledger; status-word habit | method |
| 5 | Breadth sweep 11-25 + L1 | Owner: "se varier" | room + registered read | L1 no rent; Korea's premium sits in USDT; nothing reachable | no |
| 6 | Strategy book, R531 ML, S1 | Owner: "précise… ML" | lane + read | R531 FAIL; S1 no difference; strategy cards | no (keeps the rule) |
| 7 | Tail risk of stake 1 | Invert | reflection + replay + tool | Venue failure binding (about 2%/yr of the stake); HL hedge-breakers instant; T1 watch script | **yes** (addendum: entry rules, action list) |
| 8 | Sweep 11-26 + Harvey | Reading | room + reading | Nothing above 0.2; the Bayesianized money rule | **yes** (blocks R520, R521, R524, R530, R527 at 20 days) |
| 9 | This review | — | review | below | **yes** (skeptical prior for scaling) |

## What the critics found (audit, 7 pages)
| Page | Findings | Accepted as errors | Changed a number told to the owner | Changed a money rule |
|---|---|---|---|---|
| Greeks | 23 | 15 | 5 | 0 |
| O7 | 18 | 12 | 5 | 1 |
| Calibration | 18 | 11 | 2 | 0 |
| Sweep triage 11-25 | 25 | 19 | 2 | 0 |
| R531 + strategy book | 22 | 15 | 4 | 0 |
| Tail | 22 | 19 | 3 | 3 |
| Harvey | 16 | 11 | 8 | 2 |
| **Total** | **144** | **102** | **29** | **6** |

- **By type (102):**
  - a status word before the deciding observation: 21;
  - unlike numerators or mixed samples: 15;
  - an unverified scout or reader claim: 12;
  - a formula input mapped to the wrong quantity: 10;
  - a misread of the lab's own file: 9;
  - a re-estimated number the lab already held: 7;
  - other (arithmetic, unfetched inputs, citation drift): 28.
- **Direction: of 67 errors with a direction, 60 (90%) leaned toward a cleaner or more favorable story.**
- **The ledger agrees.** 27 forecasts, 10 resolved; Brier 0.199 against 0.198 leave-one-out, so no skill is shown yet.
  My p ≥ 0.6 forecasts hit 1 in 4.

## What this means
- **My first drafts are not data.** About 15 accepted errors a page, 90% of them favorable. Every page needed the
  critic, and the critic was right two thirds of the time (102 of 144).
- **The bias reaches money.** The auditor's flag: my corrected Harvey table moved R510, R523 and R509 below the 10%
  block (5.3-7.4%) only because the prior came from my own P(PASS) (0.45-0.60), and those are the numbers the ledger
  says run high.
  - **Under a skeptical prior (π halved), the same passes leave 20-26%.** All three would be blocked.
  - The "decisive" Kraken reads were decisive because I believed in them.
- **What worked:** the room. Every critic report changed something, and the audit made the bias measurable. Cheap
  measurements on held data (L1, S1, O3b, O7b, the tail replay) settled questions in minutes.
- **What did not:** first Fermi sizes, and every word like "closed", "handled" or "priced right".

## What a better researcher would have done
- **Put the numbers in a table first, from code or quoted lines, and only then write the prose.** Most of the 102 errors
  sat in prose written around numbers still moving.
- **Sent the numbers table to the critic before writing conclusions,** not the finished page. That is cheaper than
  correcting afterwards.
- **Used a skeptical prior for anything that moves money,** knowing the measured direction of the error.

## The change in how I think (rule 11), and the decision it makes now
1. **Numbers before narrative.** A page's numbers table is built first, from code or quoted lines. The critic reads
   it before any conclusion is written. Prose may only interpret rows that exist.
2. **A skeptical prior by default for money.** My own probabilities are halved (π/2) when they feed a money rule,
   until the ledger shows calibration (Brier clearly below the leave-one-out reference at 30 or more resolved).
3. **Decision, written before the December reads** (`december_decision_20261125.md`, addendum c):
   - **stake 1 stays allowed** by its own row in §2, because it is a calibration stake: €2,000, its loss bounded by
     the 25% stop, its value the measured costs and funding;
   - **any step beyond stake 1 needs a floor below 10% under the skeptical prior.** That means far more evidence than
     one pass: the R509 180-day look well above its bar, or several independent reads.

## Unasked work worth more than the plan
- **Make the critic structural.** It is cheap (about five minutes) and right two thirds of the time. A numbers-first
  template for every reflection page would let it check rows, not prose.
- **The forecast ledger now prices my bias.** Score it at every resolution, and let the halving rule lapse only when
  the data says so.

## Corrections after the room's critic (`room_20261126/critic_self_review4.md`; checked by me)
1. **"The critic was right two thirds of the time"** should read "102 of 144 findings (71%) were accepted by me as
   errors". Acceptance is my own judgment. The audit's counts are its own enumeration, each with a quote.
2. **The ledger's "1 in 4" rests on four non-lane forecasts.** No lane-pass forecast has resolved, so "my lane
   P(PASS) runs high" is a lean, not a measurement. The in-sample reference (0.160) also beats my 0.199.
3. **Halving was a crude correction.** It is replaced by robustness across three priors: mine, mine halved, and the
   family base rate (addendum c, corrected). Under the base rate, R523's floor is about 5-12%.
4. **The exemption for stake 1 read as a rationalization.** It is now priced: about €60-100 a year at worst against
   the measurements it buys. It is written before the read, and limited to stake 1.
5. **Row errors in my own table:**
   - cycle 2's −47.8 bp (t −7.3) is the 2022-26 sample, not 2022-25;
   - cycle 1 put crypto's net 0.13% beside TSLA's gross 18% (like for like, about 2×);
   - cycle 3's "BTC Sunday rich in 2026" is post hoc (O7d is a forward question).
   - Five errors in the review of my errors: the bias is not fixed by naming it.

