# FINDINGS: book_costs_v1 (R404). Taker cost from public order books on dYdX, KuCoin and MEXC perps

**Verdict: PARTIAL, 29 snapshots with all three venues** (the frozen rule needs 40 for DATA_PASS).
- This is a measurement with 0 trials. It is the cost input M469 needs; it tests no strategy.
- The window ran from the first snapshot to 2026-11-18 00:00 UTC.

- **Registry row:** R404 (trials: 0). The row stays RUNNING/PENDING because journal rows are never rewritten; the
  close lives here and in `registry/methods.csv` (M469).
- **Reproduce:**
  - PREREG sha256 `a6c157be…`;
  - recorder `scripts/record_book_costs.py`, unchanged;
  - data: the 30 files on `claude/book-costs-data` (`book_costs/<day>/<hour>.parquet`). Every file matches its row
    in `experiments/recorders/journal/digests.csv`.
- Closed on 2026-11-18 by Claude. The files were read from the data branch into a scratch folder, and the recorder's
  own `summarize()` was re-run on them. It reproduces the committed `journal/status.json` exactly.

## The count, both ways (`DEVIATIONS.md`, "Close")
| Count | Snapshots | Note |
|---|---|---|
| (a) files on the data branch with rows from all three venues | **29** of 30 | the 2026-11-16 18:00 slot has dYdX and KuCoin but no MEXC row |
| (b) count (a) plus the six snapshots lost with the old container | 35 at most | only the first of the six is shown to have all three venues |

- **Neither count reaches 40, so the verdict is PARTIAL whichever count is used.** It rests on count (a), which can be
  checked file by file.
- **Why it fell short.** The local writer stopped on 2026-11-10 with the container. The GitHub writer started on
  2026-11-14 06:58 UTC. The slots in between are missing and are not filled in.
- **Per file:** dYdX 57 books every time; KuCoin 710-715; MEXC 405-577 books, or 0 in one slot. The MEXC gaps match the
  rate-limit failures seen in the dry run.

## Cost per side, median over symbols of each symbol's median (bp; frozen rule)
All 30 files pooled, as in `status.json`. 57 dYdX, 716 KuCoin and 578 MEXC symbols.

| Venue | 24 h volume band (USD) | Symbols | Half-spread | $1k | $5k | $10k | Unfilled share at $1k / $5k / $10k |
|---|---|---|---|---|---|---|---|
| dYdX | 0-50k | 52 | 42.0 | 42.0 | 46.2 | 50.8 | 0% / 0% / 0% |
| dYdX | 50k-500k | 2 | 15.3 | 18.1 | 21.0 | 21.2 | 0% / 0% / 0% |
| dYdX | 500k-5M | 2 | 2.6 | 2.7 | 2.7 | 2.7 | 0% / 0% / 0% |
| dYdX | 5M and up | 1 | 3.3 | 3.5 | 3.6 | 3.6 | 0% / 0% / 0% |
| KuCoin | 0-50k | 214 | 16.6 | 30.4 | 104.1 | 329.3 | 0% / 3% / 9% |
| KuCoin | 50k-500k | 175 | 11.5 | 25.7 | 78.8 | 206.8 | 0% / 4% / 9% |
| KuCoin | 500k-5M | 242 | 8.9 | 27.1 | 88.0 | 284.3 | 0% / 6% / 12% |
| KuCoin | 5M and up | 85 | 4.0 | 6.9 | 11.1 | 15.5 | 0% / 0% / 1% |
| MEXC | 0-50k | 1 | 31.8 | 39.8 | 100.3 | 183.8 | 0% / 0% / 0% |
| MEXC | 50k-500k | 453 | 3.1 | 5.5 | 9.2 | 13.0 | 0% / 0% / 0% |
| MEXC | 500k-5M | 87 | 1.6 | 2.4 | 3.9 | 5.0 | 0% / 0% / 0% |
| MEXC | 5M and up | 37 | 0.7 | 0.7 | 1.2 | 1.6 | 0% / 0% / 0% |

Fees are not included. M469 adds each venue's taker fee by its own rule.

## What this says, and what it does not
- **dYdX's long tail is expensive and thin.** 52 of its 57 markets trade under $50k a day, at about 42 bp a side at
  $1k. The three higher bands hold 2, 2 and 1 markets, under the PREREG's 5-symbol floor, so they are reported as thin.
- **KuCoin's books are shallow beyond $1k.** Below its top band, $5k costs 79-104 bp a side and $10k costs 207-329 bp,
  with 3-12% of symbols unfilled. At $1k, 26-30 bp a side.
- **MEXC is cheap at these sizes.** Most of its symbols cost 2-10 bp a side up to $5k. Its volume field puts 453
  symbols in the $50k-500k band; whether MEXC's reported volume is comparable with the other venues' was not checked.
- **These are shown books, not fills,** from four days of 2026-11. Applying them to 2024-2025 trades assumes the
  cost-volume relation held then (PREREG, known limits).
- **The count is short of the frozen 40.** M469 may still use these rows, but must cite this PARTIAL and the 29-file
  base.

## Close of the writer
- `.github/workflows/claude-book-costs-recorder.yml` exits before reading anything at or after 2026-11-18 00:00 UTC,
  as designed. It writes and commits nothing now. Removing its schedule is upkeep and changes no result.
- No local writer may restart R404 (`DEVIATIONS.md`).
