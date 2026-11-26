# Audit of the critics' accepted corrections (room 20261126)

Auditor: Haiku room member. Scope: the seven critic reports dated 2026-11-25 and 2026-11-26, and the page
"corrections" sections they produced. Read: the seven critic files, the matching correction sections, the lessons
L052-L063 (`docs/LESSONS.md`, the newest headings in that range), and the lines cited below. Not opened:
`experiments/*/journal/`. No recursive grep of `experiments/`. No network.

## Counting rules

- **Finding** = one labelled bullet or numbered item in a critic report that asserts a fault, a wrong or
  unsupported claim, or a missing check. Restatements in the critic's "cleaner than the evidence" sections count
  as findings only when they add a new point. The "fine" and "checked" lists are not counted.
- **Accepted** = the page's correction section names the point, or the page text visibly changed to match it.
  A point the page explicitly keeps is not accepted. Where a critic is itself wrong, the point is not accepted.
- **Owner was told** = the number sits on an owner-facing page (reflection, triage, decision, book).
- **Money rule** = a rule that sets a trade, a size, a stop, an entry, a stake or a floor-to-money mapping.
- **Direction** of an accepted error: C = the original error made the story cleaner or more favourable to the bet
  (tidier, more decisive, or more in favour of a lead or a stake); L = it made the story less favourable; N = neutral
  or mixed.
- Counts are my own enumeration. They are reproducible from the cited lines, but I did not re-run the critics' code.

## 1. Table

| Page | Findings in critic | Accepted | Changed a number owner was told | Changed a money rule |
|---|---|---|---|---|
| Greeks: `docs/reviews/reflection_20261125_greeks.md` (critic `room_20261125b/critic_greeks.md`) | 23 | 15 | 5 | 0 |
| O7: `docs/reviews/reflection_20261125_o7.md` (critic `room_20261125c/critic_o7.md`) | 18 | 12 | 5 | 1 |
| Calibration: `docs/reviews/reflection_20261125_calibration.md` (critic `room_20261125c/critic_calibration.md`) | 18 | 11 | 2 | 0 |
| Triage: `docs/reviews/room_20261125d/triage.md` (critic `room_20261125d/critic_triage.md`) | 25 | 19 | 2 | 0 |
| R531: `experiments/carry_meta_v1/FINDINGS.md` and `docs/strategies/STRATEGY_BOOK.md` (critic `room_20261126/critic_r531_book.md`) | 22 | 15 | 4 | 0 |
| Tail: `docs/reviews/reflection_20261126_tail.md` (critic `room_20261126/critic_tail.md`) | 22 | 19 | 3 | 3 |
| Harvey: `docs/METHOD_LIBRARY.md` and `docs/reviews/december_decision_20261125.md` addendum 2026-11-26b (critic `room_20261126/critic_harvey.md`) | 16 | 11 | 8 | 2 |
| **Total** | **144** | **102** | **29** | **6** |

Per-page notes:
- Greeks: the not-accepted points are the O2 expiring-day numerator, the threshold move (0.5% vs 2%), the
  sign-as-open point (accepted in part; not counted), CME's 75% premise (`reflection_20261125_greeks.md:126` still
  reads "about 75% of weekdays"), the 16 bp cost unit, and "Denominators differ" (mean day vs median hour).
- O7: not accepted are E7 (see §4), E9 (the page still says "-7 to -8 bp in every band" at
  `reflection_20261125_o7.md:83`), the mark-IV point, "none reachable" wording (`reflection_20261125_o7.md:148`
  still reads "So O7's first answer is no"), and the threshold and internal-tension points.
- Harvey: the money-rule count is the "block only" rule and the R509 look-1 mapping (see §5).

## 2. Classification of the 102 accepted errors

| Type | Count | Example (path:line, exact short quote) |
|---|---|---|
| (a) status word or conclusion before the deciding observation | 21 | `docs/reviews/room_20261125d/triage.md:29`: "Closed tonight with data:" (critic: "Boros ... closed too cleanly"; page now "largely answered, not closed", `triage.md:41`) |
| (b) number re-estimated or assumed when the lab held a measured one | 7 | `docs/reviews/reflection_20261125_o7.md:53`: "about 25 BTC a day near the money on BTC" (critic measured a median of 98.6 BTC in O3b's set, `docs/reviews/room_20261125c/critic_o7.md:20`) |
| (c) unlike numerators, units or mixed samples | 15 | `docs/reviews/reflection_20261125_o7.md:47`: "About 45 bp a Saturday at the bid" (labelled "2022-25 average"; the figure includes 2026, `reflection_20261125_o7.md:216`) |
| (d) formula input mapped to the wrong quantity | 10 | `docs/reviews/reflection_20261126_tail.md:45`: "1.5-5.5% a year" used as one rate; the deposit-weighted rates are Kraken 2.9% and Hyperliquid 5.5% (`reflection_20261126_tail.md:137-140`) |
| (e) scout's or reader's claim used without verification | 12 | `docs/reviews/room_20261125d/triage.md:54`: "the FX act's 2026-12-03 date (statute not opened)"; also `reflection_20261126_tail.md:159`: "comes from an unverified aggregator" |
| (f) misread of the lab's own file (PREREG, decision rule, prediction) | 9 | `experiments/xfund_eea_fwd/PREREG.md:6`: "Gate: 2 (forward paper)", read as a live rule (critic: `docs/reviews/room_20261126/critic_tail.md:21`, "R509's live rule": wrong); also `docs/reviews/reflection_20261125_greeks.md:175`: "I first wrote that this 'fits' my O3b prediction", against `docs/reviews/open_questions.md:31`: "at least 90% of the mean Sunday move" |
| (g) other | 28 | `docs/reviews/room_20261125b/critic_greeks.md:26`: "straddle 75-88 bp" (corrected to 75-86 at `reflection_20261125_greeks.md:146`) |

(g) breaks down as: arithmetic and transcription (Greeks 2; R531 transcription of R507's t 11.94 is in (b)); assumed
inputs not fetched (Greeks $40bn, `reflection_20261125_greeks.md:109`); design and sign points (Greeks 2; O7 2:
the tripwire's power and false-alarm rate); ledger citation drift (calibration: F004 cites
`open_questions.md:24`, which by the current file is the O3a row; the O3b row is at line 31, so the critic's own
line numbers also drifted, `critic_calibration.md:33`); self-description claims (calibration's status-word rule
and git-timestamp claims); margin and margin arithmetic (O7); and R531's "12 quarters" count of models.

## 3. Direction of the accepted errors

- Cleaner or more favourable to the bet (C): **60** of 102.
  Examples: `reflection_20261125_o7.md:185`, "In 2026 both gaps are about zero on both coins" (error made the
  weekend gap look closed); `docs/reviews/reflection_20261126_tail.md:133`, "already handled by R509's live 3-day
  stale exit" (error made the tail look managed); Greeks "15-45×" at `reflection_20261125_greeks.md:111` (inflated
  the TSLA ratio).
- Less favourable to the bet (L): **7** of 102.
  Examples: capacity "about 25 BTC" (`reflection_20261125_o7.md:53`) understated the scale; the Kraken fee
  "€8-28" (`reflection_20261126_tail.md:45`) and the tail's netting error; Harvey's "no stake" on R520 and R524
  (`december_decision_20261125.md` §2, per `room_20261126/critic_harvey.md:43`) was too strict.
- Neutral or mixed (N): **35** of 102.
- So **90%** of the directional accepted errors (60 of 67) pointed toward a cleaner or more favourable story.
  The one clear case in the other direction is the TSLA $40bn volume: it understated the gross-to-volume ratio
  and so the TSLA idea looked less striking (6% vs 18%, `reflection_20261125_calibration.md:119`). The calibration
  page itself says "Six of seven went toward a cleaner story" (`reflection_20261125_calibration.md:119`).

## 4. Critic points that were not accepted because they were wrong

- O7 E7 ("pre-registered O3b predictions not reported"). The calibration critic says the register does report them
  ("1 right ... 3 wrong" in the O3b row, in its copy at `open_questions.md:29`; I did not re-check that line in the
  current file). So E7's "never reports" was an overstatement. It was not accepted, and that was correct.
- Calibration's own cites: the critic's "open_questions.md:24" cite for the O3b definition is itself off by a line
  set, so the ledger repair should cite the commit (`428def4e`), as the page did.

## 5. Things the audit thinks the owner should see

1. **Harvey: the prior correction moved three lanes from "block" to "not blocked".** The critic used P(PASS) as the
   prior and found R510, R523 and R509 look 1 above 10%. The lead recovered π and the floors fell to 7.4%, 7.4% and
   5.3% (`docs/METHOD_LIBRARY.md`, Harvey table). The formula is Harvey's, so the change is right in form. But it is
   the change that moves money, and it was accepted in the favourable direction. Check: π for R509 is 0.75 in the
   table; with α = 0.05, the stated formula gives (0.45 − 0.05)/(0.60 − 0.05) = 0.73. The α used should be written
   beside each π.
2. **R531's "ML cannot pick the tail" was corrected to "not shown"** (`experiments/carry_meta_v1/FINDINGS.md`
   corrections 1). Eight of the fifteen accepted R531 errors were in the favourable direction for the ML book, and
   the stop-rule conflict is flagged but not resolved (`STRATEGY_BOOK.md:30`).
3. **Tail: the money rules changed** (entry rule on delisting coins, an ordered action list, a 25% buffer), and the
   corrections say so in `december_decision_20261125.md`. Three rules changed in the direction of more caution.

## 6. What this audit did not check

- The critics' numbers themselves (I did not re-run their code or re-fetch their sources).
- The "accepted" status of points the page never mentions. Those I counted as not accepted.
- Whether every π in the Harvey table follows the stated α: several rows do with per-look α (for example R520 look 1
  with α 0.006), but I did not verify every row.
- The cited line numbers in the current files: several critics quote lines that have since moved (calibration
  §2 notes the same drift). Quotes above are from the current file where I could confirm them.
