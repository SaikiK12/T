# Forecast extract, room 20261125c (auditor)

Scope: every explicit numeric probability the lab wrote about an event that can be scored. Read from `docs/reviews/*.md`,
`docs/reviews/room_20261125/*.md`, `docs/LESSONS.md`, `docs/STATUS.md`, `docs/reviews/open_questions.md`,
`registry/rounds.csv`, and `experiments/*/PREREG.md` (glob grep only, with `experiments/*/FINDINGS.md` checked the same
way). `experiments/*/journal/` was not opened. Nothing was run on data, no order, no credential, no network.

Method: a line counts when it gives a number in 0-1 (or a percent) for an event that a round or a question can
resolve (PASS, a t threshold, a sign, a size rule). Ranges are not used here (none were written as a range for a
single event). Priors, power calculations and ranking scores are listed in the exclusions section, not scored.

## Scored forecasts (one headline row per event)

| # | Id | Event forecast | p written | Where written (path:line, quote) | Date written | Outcome | Where the outcome is written |
|---|----|----------------|-----------|----------------------------------|--------------|---------|------------------------------|
| 1 | R529 | Index-roll front-run passes the PASS bar (NW t >= 2.8 at 2 bp) | 0.15 | `experiments/roll_frontrun_v1/PREREG.md:70` "P(PASS) ≈ 0.25 × 0.6 + 0.75 × 0.0026 ≈ 15%" (also `FINDINGS.md:8`) | 2026-11-24 (`rounds.csv:309`) | 0 (NULL/FAIL) | `docs/LESSONS.md:460` "The forecast written before the freeze said 15%. The outcome is a miss"; `docs/reviews/self_review_20261124.md:33` "R529 \| 0.15 \| FAIL \| 0.023". **`rounds.csv:309` still says RUNNING/PENDING: the registry is stale for R529.** |
| 2 | R472 | Balanced-fund rebalancing, PASS at net Sharpe 0.8 | 0.70 | `experiments/rebalfront_v1/PREREG.md:100` "so P(PASS) is about 0.70" | 2026-11-12 (`rounds.csv:259`) | 0 | `registry/rounds.csv:259` verdict NULL ("NULL by the frozen rule") |
| 3 | R473 | End-of-month TLT rally, PASS at 35 bp gross | 0.60 | `experiments/tlteom_v1/PREREG.md:96` "P(PASS) about 0.6" | 2026-11-12 (`rounds.csv:260`) | 0 (verdict PARTIAL, no forward lane) | `registry/rounds.csv:260` "PARTIAL: no forward lane" |
| 4 | O7b-a | ETH Deribit Saturday 2022-26 at or below −30 bp with t ≤ −3 | 0.75 | `docs/reviews/open_questions.md:31` "Saturday 2022-26 ≤ −30 bp with t ≤ −3: P ≈ 0.75"; same in `reflection_20261125_o7.md:157` | 2026-11-25 (before the read) | 1 | `open_questions.md:31` "Saturday −40.6 bp (t −3.9)" |
| 5 | O7b-b | ETH Deribit 2026 Saturday within ±20 bp | 0.55 | `open_questions.md:31` "2026 within ±20 bp: P ≈ 0.55"; `reflection_20261125_o7.md:158` | 2026-11-25 | 1 | `open_questions.md:31` by-year list ends "**+8**" |
| 6 | O7b-c | ETH Deribit Sunday not underpriced beyond costs | 0.75 | `open_questions.md:31` "Sunday not beyond costs: P ≈ 0.75"; `reflection_20261125_o7.md:159` | 2026-11-25 (before the read) | 0 | `open_questions.md:31` "**Sunday +52.1 (t 3.0)**" |
| 7 | O3b | BTC Sunday straddle: P(move minus premium > 16 bp) | 0.20 | `docs/reviews/open_questions.md:24` "P(underpriced by more than 16 bp) ≈ 0.2" | 2026-11-25 (before the data) | 1 under the written rule (+21 bp > 16 bp), **disputed** | `open_questions.md:25` "+21 bp (t 1.83)... **Not underpriced beyond costs**". The lab's own count (`open_questions.md:28`, `STATUS.md:113`) says "1 right of 4". My reading of the row's own definition gives 1; the lab's text reads it as 0. Both shown below. |

Counts for this table: 7 scored, 0 pending, 0 unscoreable.

## Pending or not scorable (headline rows)

| # | Id | Event forecast | p written | Where written | Date | Outcome | Status |
|---|----|----------------|-----------|---------------|------|---------|--------|
| 8 | R510 | Early read of R509 passes | 0.60 | `docs/reviews/december_decision_20261125.md:66` "R510 0.60" | 2026-11-25 | pending | `rounds.csv:290` RUNNING, reads about 2026-12-20 (`STATUS.md:369`) |
| 9 | R509 | Kraken + Hyperliquid carry passes the 90/180-day looks | 0.45 | `december_decision_20261125.md:66` "R509 0.45" | 2026-11-25 | pending | `rounds.csv:289` RUNNING |
| 10 | R512 | Three-venue carry book passes the sequential monitor | 0.40 | `december_decision_20261125.md:66` "R512 0.40" | 2026-11-25 | pending | `rounds.csv:292` RUNNING |
| 11 | R523 | Combined fast read R509 + R520 passes | 0.45 | `december_decision_20261125.md:66` "R523 0.45" | 2026-11-25 | pending | `rounds.csv:303` RUNNING |
| 12 | R527 | Combined read of three floorless lanes passes | 0.40 | `december_decision_20261125.md:66` "R527 0.40" | 2026-11-25 | pending | `rounds.csv:307` RUNNING |
| 13 | R521 | Fast read of R520 passes | 0.30 | `december_decision_20261125.md:66` "R521 0.30" | 2026-11-25 | pending | `rounds.csv:301` RUNNING |
| 14 | R520 | Deribit + Hyperliquid book passes at 90 days | 0.10 | `december_decision_20261125.md:66` "R520 0.10" | 2026-11-25 | pending | `rounds.csv:300` RUNNING |
| 15 | R524 | Binance + Bitfinex book passes at 90/180 days | 0.10 | `december_decision_20261125.md:67` "R524 0.10" | 2026-11-25 | pending | `rounds.csv:304` RUNNING |
| 16 | R530 | Balanced weekend fade PASS (frozen PREREG) | 0.36 | `experiments/xyzbal_fwd/PREREG.md:149` "P(PASS) = 0.35 × 0.92 + 0.65 × 0.06 ≈ 0.36" | 2026-11-25 | pending | `rounds.csv:310` RUNNING |
| 17 | R530 (revised) | Same event, prior revised to 0.20 | 0.23 | `docs/reviews/room_20261125/synthesis.md:129-130` "π ≈ 0.20" and "P(PASS) ≈ 0.20 × 0.92 + 0.80 × 0.06 ≈ 0.23" | 2026-11-25 | pending | as #16. The revision is a dated change to a prior; the PREREG number stays frozen (`synthesis.md:129`). |
| 18 | R503-R505 | CME commodity term carry PASS, if the published Sharpe held | 0.65 | `experiments/cmeterm_v3/PREREG.md:201` "the chance of a PASS is roughly 65%" (same text in v1:138, v2:171) | 2026-11-17 | pending | `rounds.csv:283-285` PENDING |
| 19 | R503-R505 | Same, after the decay | 0.35 | same lines, "roughly 35% after decay" | 2026-11-17 | pending | as #18 |
| 20 | Q01 | Variational weekend gap above 100 bp on at least 20% of weekends and closed by the open | 0.25 | `docs/reviews/open_questions.md:19` "P ≈ 0.25" | 2026-11-25 | pending | "first weekend 11-28/29" (`open_questions.md:19`) |
| 21 | O2 | TSLA dealer gamma per 1% above 2% of daily volume on at least half of expiry Fridays | 0.50 | `open_questions.md:22` "P ≈ 0.5" | 2026-11-25 | pending | One Friday measured (18% gross, dealer net unknown, `open_questions.md:22`); not enough Fridays |
| 22 | O7 | Younger weekend book shows Saturday IV above 0.55 × weekday IV | 0.40 | `open_questions.md:32` "P ≈ 0.4" | 2026-11-25 | **unscoreable** | `open_questions.md:32` "no independent younger book": the test cannot run |

Counts for this table: 15 pending (rows 8-22; row 22 is pending as unscoreable, not as open).

## Totals

- Headline forecast rows: 22.
- Scored (outcome known): 7 (rows 1-7).
- Pending: 15 (rows 8-22; row 22 is unscoreable until a younger book exists).
- Alternative numbers for scored rounds, not in the Brier (same event, other scenario):
  - R472: 0.48 at S = 0.5 (`rebalfront_v1/PREREG.md:101`), 0.16 at Sharpe 0 (`rounds.csv:259`). Both outcome 0.
  - R473: 0.38 at 25 bp gross (`tlteom_v1/PREREG.md:97`), 0.04 at 0 gross (`PREREG.md:98`). Both outcome 0.
  - R529: the self-review notes that R528 "would have said 5-10% if I had written one" (`self_review_20261124.md`, scored section). Nothing was written, so it is not counted.

## Brier score and calibration (headline scored rows)

Brier = mean of (p − outcome)² over the 7 scored rows: **0.334**.
If row 7 (O3b) is scored 0 as the lab's text reads it: **0.249**.

| Bin (p written) | n | Mean p | Hit rate | Rows |
|-----------------|---|--------|----------|------|
| p < 0.3 | 2 | 0.175 | 0.50 | R529 (0.15 → 0), O3b (0.20 → 1) |
| 0.3 to 0.6 (inclusive) | 2 | 0.575 | 0.50 | R473 (0.60 → 0), O7b-b (0.55 → 1) |
| p > 0.6 | 3 | 0.733 | 0.33 | R472 (0.70 → 0), O7b-a (0.75 → 1), O7b-c (0.75 → 0) |

Reading: with 7 rows this is noise, not calibration. The two PASS-type misses at 0.60 and 0.70 are the ones the lab
should look at first. Every PASS forecast on the lab's rounds so far (R472, R473, R529) resolved 0, so the lab's
PASS-type numbers have been too high on that small set, which matches the base-rate note in `approach_20261124.md`.

## Code run (scratchpad `brier.py`)

```python
scored = [
    ("R529 roll_frontrun_v1", 0.15, 0),
    ("R472 rebalfront_v1",    0.70, 0),
    ("R473 tlteom_v1",        0.60, 0),
    ("O7b Sat <=-30bp t<=-3", 0.75, 1),
    ("O7b 2026 Sat +-20bp",   0.55, 1),
    ("O7b Sun not beyond cost", 0.75, 0),
    ("O3b Sun underpriced >16bp", 0.20, 1),   # literal rule: +21 bp > 16 bp
]
def brier(rows):
    return sum((p - y) ** 2 for _, p, y in rows) / len(rows)
print("n scored =", len(scored), " Brier =", round(brier(scored), 4))   # 7, 0.3343
alt = [r if r[0] != "O3b Sun underpriced >16bp" else (r[0], r[1], 0) for r in scored]
print("sensitivity (O3b as 0): Brier =", round(brier(alt), 4))           # 0.2486
bins = [("p<0.3", lambda p: p < 0.3), ("0.3-0.6", lambda p: 0.3 <= p <= 0.6), (">0.6", lambda p: p > 0.6)]
for name, f in bins:
    rows = [r for r in scored if f(r[1])]
    print(f"{name:8s} n={len(rows)} mean_p={sum(r[1] for r in rows)/len(rows):.3f} hit={sum(r[2] for r in rows)/len(rows):.3f}")
```

Output: `n scored = 7  Brier = 0.3343`; `sensitivity ... Brier = 0.2486`; bins as in the table above.

## Exclusions (explicit numbers that are not forecasts of a scored outcome)

- Power calculations, which state how often a test would pass at a given effect, not a forecast of the real outcome.
  Listed so the self-review can decide: `cmecarry_v1/PREREG.md:131` "about a 40% chance of t ≥ 2" (R501, pending);
  `closing_momentum_v1/PREREG.md:62` "power roughly 40-60%" (R528, pending); `xfund_bfx_fwd/PREREG.md:41` "power 0.77
  at 90 days" (R524, pending); `rounds.csv:307` "in-sample power 0.86/0.95" (R527, pending); `STATUS.md:85` "92 % de
  chances" (a fast-read design claim, pending).
- Priors that feed a P(PASS) and are not scored on their own: `roll_frontrun_v1/PREREG.md:67` "prior π ≈ 0.25";
  `xyzbal_fwd/PREREG.md:145` "Prior π ≈ 0.35".
- Ranking inputs: `docs/reviews/room_20261125b/open_questions.md` lines 43-45 (Q10 0.1, Q11 0.1, Q12 0.05). These are
  probabilities of a decision change in a ranking score, not outcome forecasts.
- One reader's view: `room_20261125b/weekend_vrp_reading.md:257` "I would put a 60% probability". It is not tied to a round
  or question and has no resolver.

## Flags for the reader

1. **Registry stale for R529.** `rounds.csv:309` says RUNNING/PENDING. Lessons, self-review and x100 say NULL/FAIL.
2. **O3b scoring is disputed.** Row 7 is 1 under the row's own rule (+21 bp > 16 bp), and 0 under the text's reading
   ("not underpriced beyond costs"). The critic in `room_20261125c/critic_o7.md:47` reads it as the event happening.
3. **R530 has two numbers.** 0.36 (frozen PREREG) and 0.23 (revised prior, `synthesis.md:129-130`). Only 0.36 is in the
   frozen record; the room's revision is dated.
4. **Pending dates.** The December reads (rows 8-15) are due 2026-12-13 to 2026-12-25 (`STATUS.md:367-369`). Nothing in
   this extract can be scored before then.
5. **Event definitions for rows 8-15.** `december_decision_20261125.md:66-67` gives only the numbers. I took each
   round's event to be its own PASS or FAIL rule in `rounds.csv` (for R509-R527 the "fast read" or "combined read" rule
   is in the registry notes). If the lab meant something else, the row needs a rewrite before scoring.
6. Not checked: the full text of every `FINDINGS.md` beyond the grep for forecast phrases; `experiments/*/journal/`
   was sealed by rule and not opened.
