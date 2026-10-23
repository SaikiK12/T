# FINDINGS: accounting_v1 (R264). Zero-filled gaps do not move the flow books

**Verdict: DATA_PASS.** For books A, B and X2, the legacy zero-fill of a missing next return never touches a
held position in discovery or validation. Bridging the gaps changes nothing in either window, at any cost level.
- **The defect is real in the code** (`lab/slices.run`, legacy mode), but these books never meet it. Their universe is
  the trailing top 50 by volume, and that universe almost never contains a coin about to lose a bar.
- **Diagnostic, computed after the run:**
  - `u.ret` is non-finite in 52% of all cells (coins not yet listed or already delisted).
  - Inside eligible cells, only 93 of 2,509,850 coin-hours lack a next return (41 in 2022, 50 in 2026, 2 elsewhere).
  - 19 columns stop trading before the archive end. Only 3 of them were eligible in the 72 hours before their last bar.
- **Registry row:** R264 (trials 0, a measurement). Program trials stay at 9,472,061.
- **Gate:** 0.
- **Reproduce:** prereg sha c312bb36, frozen in commit 6230f6b before the run. Run `python scripts/run_accounting.py`
  (about 1 minute).
- **Parity:** books A, B and X2 equal R217's `daily.npz` exactly (max |diff| 0).

## Results (bp/day; NW t lag 10)

| Book | Window | Exposed-missing share | Held gap episodes | Legacy 1x / 2x / 3x | Corrected 1x / 2x / 3x | t 1x legacy = corrected |
|---|---|---|---|---|---|---|
| A | discovery 2021-23 | 0 | 0 | +11.19 / +8.20 / +5.21 | same | 2.88 |
| A | validation 2024-25H1 | 0 | 0 | +13.60 / +8.00 / +2.40 | same | 1.90 |
| A | spent 2025-07..2026-09 | 0.0001 | 35 (all at the archive's last row) | +21.85 / +16.83 / +11.82 | same | 1.22 |
| B | discovery | 0 | 0 | +3.90 / +3.35 / +2.81 | same | 2.10 |
| B | validation | 0 | 0 | +6.99 / +5.77 / +4.54 | same | 1.71 |
| B | spent | 0.0000 | 4 (archive end) | +17.99 / +17.13 / +16.27 | same | 2.69 |
| X2 | discovery | 0 | 0 | +15.47 / +11.85 / +8.24 | same | 2.99 |
| X2 | validation | 0 | 0 | +19.68 / +12.75 / +5.82 | same | 2.22 |
| X2 | spent | 0.0001 | 35 (archive end) | +42.51 / +36.34 / +30.17 | same | 1.70 |

- **The spent-window episodes are a boundary artefact.** The last archive row has no next close, so a position held
  there has no return. These are not gaps in the market.
- **None resumed and none never resumed,** so the signed and bound impacts are 0 everywhere.

## Reading
- **For the forward lanes on these books (R200, R214, R215, R218, R221, R225):** their archive record is not inflated
  by zero-filled gaps. The PR #25 audit's open item 4 is closed for these books.
- **Not closed elsewhere:**
  - Wider universes (atlas cells with 150 columns and top-100 eligibility) and event lanes near delistings can meet
    gaps. A lane on those must use `missing="raise"` or bridge.
  - The other defects the audit names are not measured here. These are zero-latency fills (R213 put a 1-hour delay at
    about 1% of A), the idealized hedge, and selection on the holdout.
- **Cost sensitivity** is unchanged from R217/R262. A and X2 are near zero at 3x in validation (+2.4, +5.8 bp/day). B
  is the most cost-robust.

## Not checked
- Delisting settlement prices (no never-resumed episode occurred in these books).
- Carry R191 (its own runner) and R263.
- Funding inside gaps (no gaps occurred).
