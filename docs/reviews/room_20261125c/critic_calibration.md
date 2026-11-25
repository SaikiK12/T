# Critic on the calibration page and its ledger (room 20261125c)

Read: `docs/reviews/reflection_20261125_calibration.md`, `registry/forecasts.csv`, `scripts/score_forecasts.py`,
`docs/reviews/room_20261125c/forecast_extract.md`, `docs/reviews/reflection_20261125_greeks.md`, `docs/reviews/open_questions.md`,
`docs/reviews/december_decision_20261125.md`, the cited PREREG and FINDINGS files, `registry/rounds.csv`, and git history.
Not opened: `experiments/*/journal/`. Nothing written except this file.

## 0. Short verdict
- F023 (O3b scored 0) is the right outcome under the definition committed before the read. The row's own wording is ambiguous, though.
- Several ledger source cites are off by one line, and one is wrong (F015). Two rows have no defined event.
- "Worse than the base-rate reference" is not established at n = 7. Against an out-of-sample base rate the ledger is slightly better.
- The "timestamped in git before the outcome" claim (page section 5) fails for the early rows.
- The proposed status-word rule would have stopped at most one or two of the seven corrections.

## 1. F023: which scoring is right
- The t-threshold definition was committed in `428def4e` (2026-11-25 17:58:30 UTC): `docs/reviews/reflection_20261125_greeks.md:144` in that commit reads
  "**Underpriced** means the mean of (move − premium) is above 16 bp, with t ≥ 2."
  - In the current file the same sentence is at line 201.
  - `git show 8e09c3d2 -- docs/reviews/reflection_20261125_greeks.md` has no +/- line touching it, so it did not change before the read.
  - The O3b script followed in `cd8fa7cf` (18:03:52); the read is in `8e09c3d2` (18:38:22). So the definition predates the read.
- Measured: "Sun +21.00 bp t 1.83" (`docs/reviews/o3b_daily_vrp.md`, Sunday row). Under the committed rule, the event did not happen: outcome 0 is correct.
- The register row is weaker. `docs/reviews/open_questions.md:25` says only "P(underpriced by more than 16 bp) ≈ 0.2", with no t ≥ 2 clause.
  - The same row adds "the mean Sunday straddle premium is at least 90% of the mean Sunday move, so no underpricing beyond costs."
  - Measured premium/move = 159.65/180.64 = 0.88, which is under 0.90. So the 90% clause reads as "underpriced" (outcome 1).
  - Three readings give different outcomes: mean-only gives 1, mean plus t ≥ 2 gives 0, and the 90% clause gives 1.
  - The extractor used the mean-only reading. The lab's own text, `open_questions.md:26`, says "**Not underpriced beyond costs**," which matches 0.
- Fix: cite `428def4e` for the definition in F004's source and event. Do not cite `open_questions.md:24` (that line is O3a, see section 2).
- Clustering shrank the Saturday t (−7.34 plain, −6.32 by month: `docs/reviews/room_20261125c/audit_o3b.md:69`), so the 0 likely survives it for Sunday too (not checked). F023 as 0 contributes 0.2² = 0.04 to the Brier; as 1, 0.8² = 0.64.

## 2. Ledger rows: citations, events, omissions
Checked each cite with `sed -n` and `grep -n`. Quotes match unless noted.
- Off-by-one or worse cites:
  - F004 cites `open_questions.md:24`. Line 24 is the O3a row. The O3b row is line 25.
  - F005, F006, F007 cite `open_questions.md:31`. The O7b row is line 32.
  - F018 cites `:22`; the O2 row is line 23. F019 cites `:38`; the O7d row is line 39.
  - F015 cites `december_decision_20261125.md:66`. "R524 0.10." is at line 67. Line 66 holds R520.
  - The extractor's cite for the O3b reading, `critic_o7.md:47`, is a BTC kline table. The O3b reading is at `critic_o7.md:35-36` (E7).
  - Critic E7 cites `open_questions.md:24` (wrong line) and says the O3b predictions were "not reported". `open_questions.md:29` reports them ("Score of my four predictions: 1 right ... 3 wrong").
- Correct cites (checked): F001 `rebalfront_v1/PREREG.md:100` "so P(PASS) is about 0.70"; F002 `tlteom_v1/PREREG.md:96` "P(PASS) about 0.6"; F003 `roll_frontrun_v1/PREREG.md:70`; F016 `xyzbal_fwd/PREREG.md:149`; F008-F014 December line 66; F017 `open_questions.md:19`.
- Outcomes (checked): R472 `rounds.csv:259` status DONE, verdict NULL; R473 `tlteom_v1/FINDINGS.md:3` "PARTIAL", with "U's 1x net is +13.0 bp a month at t 0.95" (line 6); R529 `roll_frontrun_v1/FINDINGS.md:3` "FAIL (NULL)"; O7b Sat −40.57 t −3.88, 2026 Sat +7.8, Sun +52.11 t 2.99 (`o7_eth_daily_vrp.md:12-13`, `:23`). All resolve outcomes are correct.
- Events that are not defined:
  - F009 "R509 passes at its read": R509 is a forward paper with 90/180-day looks (`rounds.csv:289`), not a read. Undefined.
  - F018 "numerator to be fixed before scoring": the ledger holds a forecast whose event is not fixed. It should not be a row yet.
  - F017 pairs P 0.25 with "quotes stay near the frozen index", but the question is "gap above 100 bp on at least 20% of weekends" (`open_questions.md:19`). These are not the same event.
- Written probabilities left out of the ledger:
  - R503-R505 CME: 0.65 and 0.35 (`cmeterm_v3/PREREG.md:201`, "roughly 65%" and "roughly 35% after decay"). Pending, not scored.
  - O7 unscoreable 0.40 (`open_questions.md:33`). Fine to leave out if marked unscoreable.
  - R530 revised 0.23 (`room_20261125/synthesis.md:129-130`). Only a note on F016 says it.
  - O3b side predictions: "4 of 5 weekdays" and "Saturday within ±10%" (`open_questions.md:25`). Not probabilities, but scored "wrong" in the lab's count.
- Rows that are not written forecasts:
  - Q26 "held" and Q16 "held" (page section 0). `open_questions.md:15` gives "H1 (>0.6) not supported", and line 17 says "(none written: answered the same hour)". These are hypotheses with no p.

## 3. Scoring and the "worse than base rate" claim (I ran the code)
- `python3 scripts/score_forecasts.py` prints: forecasts 19, resolved 7, pending 12; Brier 0.249 against 0.204 for always forecasting the hit rate (0.29).
- Fair reading, with reservations:
  - The 0.204 reference uses the hit rate of the same seven rows. It is the best constant in hindsight, so it is a tough benchmark.
  - Against a constant 0.5 (fixed in advance), the ledger scores 0.250 versus 0.249. Indistinguishable from a coin.
  - Leave-one-out base rate (out of sample): model 0.249, reference 0.278.
  - So "worse than the base rate" depends on the reference chosen. At n = 7 there is no detectable skill either way.
- Bootstrap, `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/boot.py` (seed 1, 20,000 resamples of rows, skipping one-class resamples):

```python
def boot(rows, B=20000, seed=1):
    rnd = random.Random(seed); d = []
    for _ in range(B):
        s = [rows[rnd.randrange(len(rows))] for _ in rows]
        if len({o for *_, o in s}) < 2: continue
        d.append(brier(s) - ref(s))          # ref = Brier of always forecasting the resample's hit rate
    d.sort(); n = len(d)
    return d[int(.025*n)], d[int(.975*n)], sum(x > 0 for x in d)/n
```

| Variant | Brier | In-sample ref | Brier − ref, 95% CI | Share of resamples model worse |
|---|---|---|---|---|
| Ledger (F023 = 0) | 0.249 | 0.204 | [−0.131, +0.263] | 0.67 |
| Extractor (F023 = 1) | 0.334 | 0.245 | [−0.061, +0.319] | 0.90 |
| Leave-one-out base rate (ledger) | 0.249 | 0.278 | [−0.328, +0.250] (row-bootstrap of LOO differences) | n/a |

- Reading: the ledger is not shown to be worse than a base rate. The F023 choice is the largest single driver.

## 4. The proposed rule against the seven corrections (page section 0)
The rule: a status word (answered, killed, alive, closed) may follow only the decisive observation the page names; before that, "leaning" with a probability that enters the ledger.
- TSLA "15-45×" (status "alive at Fermi", `open_questions.md:23`): partly. The word is blocked. The numerator error is not: "leaning" with a 15-45× ratio is still wrong. Needs a same-numerator check (L053).
- $40bn assumed volume: not prevented. It is an input, not a status word. Needs "every input is a fetched number with a source."
- Snapshot called a "fit": not prevented. "fit" is not in the word list.
- SPX charm "closed at Fermi": prevented. "closed" is listed.
- Saturday "priced right": not prevented. "priced right" is a verdict outside the list.
- "The makers priced it away", then "mostly the world": not prevented. It is a causal claim. Needs "both sides measured before naming a cause" (L055).
- "Makers chase last year: fits Sunday only": not prevented. It is a pattern claim from a subset. Needs the by-year table before the headline.
- Earlier cases in §2 (O3a "answered", O1 "closed"): prevented.
- Count: one clearly prevented, two partly, four not. The rule also depends on the writer naming the decisive observation after seeing the data, so the trigger can be chosen after the fact.
- What would have caught more: a same-numerator and same-unit check for every ratio; a rule that labels any inputs not fetched as "assumed"; a rule that every verdict word (fit, priced right, explains) carries its measured window and both sides.

## 5. Where the page is cleaner than the evidence
- Section 0: "every time toward a cleaner story." Not true for the volume fix. At $40bn the TSLA ratio was about 6% (`cd8fa7cf`); at $13.2bn it is about 18% (`200bffea`). That is a more striking story, not a cleaner one. The 15-45× to 2× correction went the other way. The direction was not measured.
- Section 0: "Q26 and Q16: held" listed as today's "scored predictions." No probability was written (section 2 above).
- Section 0: "O3b: 1 of 4 right" counts side predictions that are not in the ledger, so the count is not comparable with the Brier.
- Section 2: "the status word comes before the decisive observation" is called the common root. Only about four of the seven corrections involve a status word (TSLA "alive", SPX "closed", Saturday "priced right", snapshot "fit").
- Section 5: "every forecast is timestamped in git before its outcome, so the score cannot be fooled after the fact." Not true for the early rows (section 6 below).
- Section "The field": Tetlock's finding ("update in small steps, keep wide bands early") is stated from memory. The page admits the text was not read, but still states the finding as fact.

## 6. Git timestamps
- The repository's root commit is `deae1dc9` (2026-11-17 03:18:35 UTC; zero parents; 5,302 files added). Git cannot date anything written before that.
- R472's 0.70 and R473's 0.60 first appear in `deae1dc9`. Their PREREG text says "frozen 2026-11-12" and the run was 2026-11-12. Their probabilities are unverifiable by git. The same holds for F020-F021 and the R503-R505 rows.
- `registry/forecasts.csv` was first committed in `c407ea11` (2026-11-25 22:33:05) with all seven resolved rows already present. So the ledger was built after the outcomes, not as a live log. The scorer's docstring says rows are "never edited" and "written before the outcome," which the history does not show.
- R529: the PREREG with P 0.15 is committed in `ae202dbc` (10:30:00 UTC). The results files are dated 10:30:13 (`experiments/roll_frontrun_v1/results/`), 13 seconds later. The rounds note says "data held, no download" (`rounds.csv:309`), so the forecast was written with the data already on disk. It is git-earlier than the run, but it was not blind.
- O3b and O7b forecasts are committed before their reads (`428def4e`, `8ed5a69d`).

## 7. Fine
- The scorer's checks run clean. Power calculations, priors and R472/R473 alternative numbers are correctly kept out of the Brier.
- The extractor's flags (stale R529 row, R530 revision, undefined December events) are good.
