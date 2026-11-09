# R367 hftlead_v1: INCONCLUSIVE (1 usable day of the 3 the frozen rule needs)

**Registry:** R367, 16 trials registered (program total unchanged by this close).
**Final read:** 2026-11-09 17:28 UTC, by the frozen runner `scripts/run_hftlead.py` (PREREG `0dbbbffe…`, 2 inputs
matched). The frozen window is whole UTC days 2026-10-29..2026-11-08; reading it after 11-08 cannot add a day.

## Result
- **Merged days in the window:** 2026-10-29, 10-30, 11-02, 11-03, 11-04, 11-05.
  - 10-31 and 11-01 have no file.
  - 11-06 has about 1.5 h of unmerged parts.
  - 11-07 and 11-08 have nothing, because the container was down from about 21:00 UTC on 11-06 to 16:40 UTC on 11-09.
- **Usable days** (≥ 80% coverage on both coins and trades present): **2026-10-29 only.**
  - 10-30 reached 65%.
  - Every November day stayed between 10% and 12% (`results/coverage.csv`), because the recorder only ran in the
    short windows when the chat container was awake.
- **Verdict by the frozen rule: INCONCLUSIVE.** It needs at least 3 usable days. No rule was scored, so there are no
  fills, markouts or p-values.

## Costs (1x, 2x, 3x)
Not computed: the rule stops before scoring. The 0.1 bp cost unit and the 2-unit bar stay as frozen.

## Read against the program
Program trials stand at 9,784,361 (`registry.program_trials`). An inconclusive screen claims nothing either way.

## What this means
- **No evidence for or against** M427 (lead from Binance USDT or Bybit into Binance USDC with a 0%-maker quote).
- **The binding constraint was the recorder, not the idea.** A 100 ms recorder needs a host that stays up for whole
  UTC days. The chat container did not: it slept between sessions.
- **The lane does not restart under this id.** A retry would be a new lane with a new id, its own window, and an
  always-on host for the recorder.
  - Codex's GitHub Actions runtime (R420) runs hourly jobs, not a continuous 100 ms stream, so it cannot host this
    recorder as it stands.
