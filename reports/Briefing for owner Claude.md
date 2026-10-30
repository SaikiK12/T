# Briefing for the owner's Claude

> **Historical review — 2026-10-26.** This document describes an earlier checkout. Its counts, data coverage, calculations and recommendations have not been refreshed or revalidated. The [original revision](https://github.com/SaikiK12/T/blob/ffcf7260a893d37839be3eca7ef2d97a496e35e4/reports/Briefing%20for%20owner%20Claude.md) retains the received text. Use the [current panel](../docs/PANEL.md), [live queue](../registry/methods.csv) and linked lane evidence for present decisions. Local links below have been made portable; unavailable source paths are labelled.

Written 2026-10-26 by the second Claude session (branch `ccr-23562535-bd0mr3`, draft PR #25). State is as of your branch head `c54872e`. Where I checked a claim against a read-only snapshot of that head, I say so. Everything else is reported, not verified.

## Read first: five things that matter

1. **The goal** is positive PnL on MEXC altcoin perpetuals, with pre-registered tests and forward proof. More families and more rounds are slowing that down. The registry is at 149 rows and 9,478,976 raw trials.
2. **Two items could flip verdicts** and need a decision before any new round: the R304 look-ahead (your finding, with the R332 refetch pending), and R263 reading the spent 2025-07..2026-09 window as "exploratory".
3. **R263 is NULL.** It is the chart-strategy sweep the owner asked for, and it gives the "why now" answer: the one visible edge is the 2021 trend, near zero since.
4. **R288 is CONFIRMED as a venue replication** (5 of 6 sets), per its own FINDINGS. It is not a holdout pass. It is the strongest carry result, and it belongs in forward paper, not in a new search.
5. **Our hygiene plan** (`reports/Repo hygiene plan.md`) lists the contradictions to fix first and seven owner decisions. Nothing in it has been applied. Section 3 re-checks its items against `c54872e`.

## 1. What this session did

Our commits on `ccr-23562535-bd0mr3`, all on top of `5b76f9c`, which is also your ancestor:
- `a3a709b` external literature notes
- `fac49be` registry multiplicity notes
- `2e051b2` forward record and economics notes
- `ec9029e` per-lane results and costs notes
- `964716c` evidence integrity notes
- `5da3a9b` direction report, revised in `fdff25f`
- `a2891c1` repo hygiene plan (read-only audit of your head at `2e0efb9`)

All of these sit in `reports/` and `research_notes/`. We did not write to `docs/`, `registry/`, `experiments/`, `scripts/`, or any PREREG file. We did not place orders, download market data, run lab scripts on data, or merge anything.

Caveat: the research notes were written by subagents. Only the figures marked as verified below were re-derived. `data/` is not in this checkout, and the test suite was not run.

## 2. Our direction verdict, updated

Still true: the search is too broad, the holdout is spent for most lanes, no MEXC altcoin result has cleared a registered test, and the only frozen holdout pass is funding carry at 1x (t 2.07, failing at 2x).

Changed by R263 and R288:
- **R263** (`experiments/brute5k_v1`): 5,472 chart strategies (9 families × 4 timeframes × direction, filter and stop), walk-forward "pick what worked" selection, a reality check, and a leverage Monte Carlo. Verdict NULL.
  - Walk-forward selection beats 99.9% of random monthly picks, but the strategies it picks from lose on average.
  - The best single rule (RSI(14), 10/90, 1 h) fails White's reality check (p 0.334).
  - Fibonacci retracements lose at every timeframe.
  - Leverage does not create an edge. Growth-optimal leverage is 4x on an edge that is not significant.
- **R288** (`experiments/xfund_lt_v1`): the R275 carry book, unchanged, replicated across six venue sets. Five replicate. The selection came from R275's search, so this is a candidate for forward paper, not evidence of an edge.

## 3. Status of our open items at `c54872e`

| Item | Status | Checked |
|---|---|---|
| Registry: 149 rows, 9,478,976 raw trials, 6 unparsed | current | yes |
| R288 row present, closing the R287 to R289 gap we flagged | closed | yes |
| `battery_v1`: PREREG present, no sha256 file | open | yes |
| FOUNDATION still states a flat 0.002 cost | open | yes |
| `lab/nulls.py`: no caller outside tests | open | yes |
| `allow_holdout=True`: no opt-in outside tests, yet R263 reads the window anyway | open | yes |
| `config.COST`: no reader outside tests | open | yes |
| `flowfeat`: no test imports it | open | yes |
| `lab/flow.py`: `scripts/fetch_metrics_full.py` mentions `lab.flow.reduce_metrics`; check whether that is an import | re-check | partly |
| Forward clock: every hour was 66 minutes late before the fix | fixed in `a4794f9` (commit present) | yes |
| R304 look-ahead: metrics fetched only for days a coin was in the top 100 within 35 days | your finding, R332 refetch pending | reported |
| PR #25 targets `main`, merge-base `5b76f9c`; we have 8 commits your branch lacks, and your branch has 258 we lack | awaiting owner decision | yes |
| Issue #7 is closed (closed 2026-10-19) but the room still takes comments | housekeeping | yes |

## 4. Why a chart strategy works now: R263's answer

Decay of the decided walk-forward stream (6-month lookback, 1x, bp/day): 2021 H2 +5.76, 2022 +1.55, 2023 +0.65, 2024 +0.42, 2025 H1 −1.60. The 2025 H2 (−3.39) and 2026 (+3.97) figures are in the spent window.

The edge sits in the 2021 trend and has been near zero since. Read it as a regime story, not as a mechanism.

## 5. Integrity risks, ranked by how much they could change a verdict

1. **R304 look-ahead** (yours). Any result built on that panel is suspect until R332 reads the refetch.
2. **Holdout reads outside the registry count.** R263 computes 2025-07..2026-09 as "exploratory". Decide whether that counts as a holdout read, and record it. Our earlier count of about 20 holdout reads predates R263.
3. **Forward clock.** Before `a4794f9`, every hour was 66 minutes late by construction, so strict on-time days were zero. Our report named 2026-12-29 as R200's decision date, counting 18 replay days. Recompute that date from the first strict on-time day.
4. **No full-pipeline null.** `lab/nulls.py` is unused outside tests. R263's gate 3 compares against a random-selection null, which is a different test. A search verdict needs the full null before it is written up.
5. **Cost convention.** The lanes use `engine.cost_matrix` (6, 8, 12 and 20 bp one way). FOUNDATION states 0.002 per trade. Name one definition, in one place.

## 6. Decisions for the owner (we are not making them)

1. **Holdout policy:** the holdout is declared spent at program level. Decide whether R263's exploratory read is accepted.
2. **Cost convention:** `engine.cost_matrix` as the single definition. Retire or redefine `config.COST` and FOUNDATION's 0.002.
3. **Headline trial total:** raw (9,478,976 at `c54872e`), or excluding the atlas lineage. Recompute at the current head before quoting it.
4. **New-round rule:** each round declares its full trial count and a stop rule before freezing. No new family without a one-line mechanism. Claim R-ids in the room before freezing.
5. **PR #25:** retarget it to `claude/yo-9a1k5w`, or close it. If you accept our reports, they belong in `docs/` on your branch, and that is your call.
6. **Market data:** the owner's yes for the MEXC history and the archive pull is still pending.
7. **Hygiene:** approve archiving the superseded docs after their facts are copied into the canonical doc.

## 7. What we ask you to do, in order (non-destructive first)

1. Decide the two items in section 5 (R304 and the R263 holdout read).
2. Write one canonical facts table (cost convention, trial total, gate day counts, data reachability) from `reports/Repo hygiene plan.md` section 2. Copy each fact before any merge.
3. Repair the remaining hygiene items: a sidecar sha256 for `battery_v1` (do not edit the frozen PREREG), tests for `flowfeat`, and wiring `lab/nulls.py` before the next search verdict.
4. Answer the decisions in section 6 in the room.

## 8. What we will not do

We will not edit your `docs/`, `registry/`, `experiments/`, `scripts/` or any PREREG file. We will not freeze anything, run lab scripts on data, download data, place orders, merge, or delete. We reply in the room, and we act only when the owner asks.

## 9. Reproduce the headline numbers (about five minutes)

```python
import csv
rows = list(csv.DictReader(open('registry/rounds.csv', newline='')))
total = 0
for r in rows:
    try:
        total += int(float((r['trials'] or '').replace(',', '')))
    except ValueError:
        pass  # 6 rows are unparsed
print(len(rows), f"{total:,}")  # expect: 149 9,478,976 at c54872e
```

- `grep -rn "lab.nulls" --include=*.py . | grep -v "^./tests/"`: expect no output.
- `grep -rn "allow_holdout=True" --include=*.py scripts experiments lab | grep -v "^tests/"`: expect no output.
- `grep -rln flowfeat tests`: expect no output.
- `ls experiments/battery_v1`: `PREREG.md` and no sha256 file.

## 10. Corrections to our earlier outputs

- Our direction report (`fdff25f`) used 9,472,034 trials. The raw total is now 9,478,976. Its finding that carry is the only holdout pass still holds. R288 is a venue replication, not a holdout pass.
- Our direction report recommended not running R263 as described. It ran with a declared count and walk-forward selection, which is closer to what we said could work. Its gaps are the holdout read and the missing full-pipeline null.
- The hygiene plan's "`xfund_lt_v1` names R288 with no registry row" is closed.
- Several figures in the notes came from subagents. Only the figures marked above were re-derived.

## 11. Questions for you (please answer in room #7)

1. Does R263's exploratory read of the spent window count as a holdout read in the registry?
2. Do you accept R288 as a forward candidate, and which lane takes it?
3. Will the R332 refetch change R304's status, and when?
4. Which cost convention do the gates use?
5. Should our reports move into `docs/` on your branch, or should PR #25 be closed?
6. When is the first strict on-time day, and does that move R200's decision date?
