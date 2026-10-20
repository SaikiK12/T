# R265 implementation handoff (Codex)

The last pushed Claude commit, `83554e1`, contains a frozen PREREG, events and
symbol map. It contains no `run_unlocks.py`, result files or FINDINGS. The owner's
pasted handoff mentions 422 priced events and a gate-0 replication, but those
numbers cannot be authenticated or reproduced from the committed state alone.
They are not recorded as measured results here and no DONE row is appended.

This PR supplies the missing runner and synthetic tests against the unchanged
frozen specification. Its implementation is committed before any archive outcome
is computed by Codex. The original calendar snapshot and hourly perp archive are
absent from this workspace. The runner fails before loading a panel or creating
an output directory if either is absent; there is no substitute dataset or fetch.
No reserved 2020 or MEXC outcome is read.

Implementation details to review before running:

- The exact frozen event/map bytes must rebuild from the original snapshot and
  symbol-check archive, as required by the PREREG. CSV/software differences fail
  rather than changing the frozen files.
- The primary cohort alone supplies the nine logged variants. Horizons and BTC
  hedge retain only independently priceable rows from that priced cohort; each
  summary reports its own n. No result-based inclusion or alternative cohort is
  selected. Missing 20-day volume history is excluded from both volume bands.
- A missing funding rate is zero by the frozen rule. This is an explicitly limited
  replication, not an endorsement of zero-filled funding in a trading account.
- The prescribed BTC hedge adds its price return without modeling a second leg's
  fee/funding; it is a diagnostic, not an executable hedged portfolio.
- The short can lose more than 100% of entry notional; those observations are
  retained. There is no collateral, maintenance margin, liquidation, concurrency,
  position sizing or path-dependent portfolio simulation. Event means and t
  statistics cannot establish a tradable account return or a go-real decision.
- Null dates exclude every kept event for that symbol (including nonarchive
  labels), with a strict distance greater than 14 days, and reuse the primary
  priceability/cost rule. NumPy RNG seed is 265; candidate days are chronological.
- Both half samples are split by event count after date/symbol sorting; an odd n
  gives the extra observation to the second half. Top-three summed-net ties use
  alphabetical symbol order. These deterministic mechanics are explicit before
  Codex outcomes; they are not changes to the frozen strategy.

Run only with the original local data, after review:

```sh
python scripts/run_unlocks.py --root /original/data \
  --snapshot /original/data/unlocks/2026-10-20 --out /new/r265-output
```

Recover Claude's uncommitted runner/results if possible before running again;
retain them separately for comparison instead of overwriting their provenance.
Do not report a fresh independent confirmation: the sample is gate 0 and the
calendar is retrospectively revised. A prospective lane requires a new prereg,
point-in-time event deadlines and explicit tail/liquidation/execution mechanics.

## Frozen implementation declaration

Runner SHA-256: `ae0706622985c160d357f7cf0342611b3806bd790b5931d9d1dd958e3b3b5fd0`.

This implementation note is frozen before any Codex market outcome; the runner
checks its digest and declaration in addition to the original R265 prereg.
