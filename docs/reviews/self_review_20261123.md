# Self-review, 2026-11-23: my own research choices as data (R507-R525)

- **The owner.** I must not only follow advice. I must improve myself and see, on my own, what would be even better to
  do.
- **Method.** Every round I ran from R507 to R525 is classified by the lens that chose it and by its outcome. Then:
  what a better researcher would have done, and the rules that follow.

## Outcomes by lens (decided historical tests; forward lanes are still running)
| Lens | Rounds | Outcome |
|---|---|---|
| Follow the plumbing (funding-design gap) | R507, R508, R511, R519 (reported book), R518 | 4 of 5 earned; R518's gap was real but the rule churned |
| Change the scale (class, portfolio) | R525, framework note | The lab's broadest result: Sharpe 5.5 over 5.7 years, in 40 minutes |
| Engine blind spot | R516 | Passed, but its events were drying up |
| Transfer a mechanism to a new venue type | R517, R518 | 0 of 2: the cause did not travel |
| Turn cost into income | R513, R522 | 1 of 2: R522's fill rule kept the toxic fills |
| The owner's reach (regulated pair) | R515 | Thin: about cash |

## Failure modes, counted
- **Design flaws I could have seen before the freeze: 4 of 5 FAILs.**
  - R518: churn against a thin gap (the break-even was written but ignored).
  - R519: the sign was left to a 30-day window.
  - R522: the fill rule selected informed flow.
  - R516: supply was counted in total, not per year.
- **Plumbing bugs: 6.**
  - R519: a perp that was "not open", and Deribit's 08:00 UTC day boundary.
  - R522: a path overwrite.
  - R520: the readiness ratio on thin coins.
  - R509: the read raised on an empty journal.
  - The shared cache key.
- **Process misses the owner had to correct: 5.**
  - Subagents.
  - The Kraken tunnel.
  - Waiting on workflows.
  - Not retaining their advice.
  - Not auditing good results.

## What a better researcher would have done
1. **Solve the class at once** (Hamming). After R507 and R508, map every floorless × floor pair. R525 came three
   days late.
2. **A pre-mortem before each freeze** (Klein's premortem, queue item 2 in `docs/METHOD_LIBRARY.md`): "it failed; why?"
   Three of the four design flaws above would have been named.
3. **Audit the pleasing result at once** (Feynman). R525's delay test found LUNA's broken hedge within an hour.
4. **Spend less on access.** The owner said it was theirs.
5. **Measure correlations as soon as a mechanism replicates.** The framework was visible from R507/R508/R511.

## Unasked work worth more than the plan, chosen by me
Ranked by expected value for real money:
1. **Price the risk limits.** Simulate the hourly divergence stop and the per-coin cap on R525's pairs, to see what
   they cost and whether they stop the LUNA-type tail. Money cannot start without them.
2. **Turn a PASS into trades.** A tool that turns a forward PASS into the owner's exact order list per venue: coins,
   sizes, stops and margin split (`lab/margin.py`), so a pass becomes a stake the same day.
3. **Capacity.** From the recorded book walks (R509/R512/R520), the dollar size at which costs double, per pair.
4. **The forward sleeves** (already planned).

## Rules that follow (added to `CLAUDE.md`)
- **Choose:** name one unasked item with higher expected value than the planned one; do it if it wins.
- **Before every freeze:** a five-line pre-mortem ("it failed because…"); fix the design if a reason is likely.
- **Every tenth cycle:** a self-review like this one, with outcomes by lens. Choose lenses by their measured yield.
