# FINDINGS: pcares_v1 (R287). Hourly PCA residuals revert a little, and trading them hourly costs several times more

**Verdict: NULL (24 trials, gate 0).**
- The reality check gives p = 1.00. The best studentized discovery mean is −1.42, against a null 95th percentile of
  2.75.
- All 24 variants lose at 1x costs, in discovery and in validation.

- **Registry row:** R287 (trials: 24; program trials after it: 9,478,455).
- **Reproduce:**
  - prereg sha 94956f99, frozen before the first statistic.
  - Run `python scripts/run_pcares.py`. It takes about 4 minutes, and its log is in `run.log`.
  - `results/inputs.csv` has the sha256 of the 1,361 files read (680 hourly kline files, their funding files and the
    excluded-names list). Their combined digest is in `results/summary.json` (addd847d8fac…).
  - Tests: `tests/test_pcares.py`. On synthetic data it checks that a planted reverting residual earns gross and a
    random-walk residual earns less, that scores do not read later hours, the universe rule, and funding sign and
    turnover.

## What was tested
Avellaneda and Lee's stat-arb (M298, from the comment dig), on the 50 Binance USDT perps with the most quote volume:
- **Daily model:** each day, a PCA of the last 60 days of hourly returns.
- **Signal:** each coin's residual from K eigenportfolios, scored hourly by an OU fit over the last L hours.
- **Trade:** enter at |s| ≥ e and exit when s crosses back inside ±0.5.
- **Hedge:**
  - **factor:** the eigenportfolio hedge;
  - **dollar:** equal-weight long side against short side.
- **Cost:** 7 bp per side at 1x, plus funding. Discovery is 2021-03 to 2023. Validation is 2024-01 to 2026-09; its
  second half is the spent holdout.

## Numbers (bp per day on a book of gross weight about 1; full table in `results/variants.csv`)
| Variant | Disc gross | Disc cost 1x | Disc net 1x / 2x / 3x | Disc t | Valid gross | Valid net 1x | Valid t | Turnover/day (disc) | Break-even bp/side disc / valid | Mean hold h |
|---|---|---|---|---|---|---|---|---|---|---|
| K1 L168 e2 dollar (j*) | +8.9 | 17.9 | −9.0 / −26.9 / −44.8 | −1.33 | −13.4 | −30.9 | −2.98 | 2.6 | 3.5 / −5.3 | 26 |
| K3 L168 e1.25 dollar | +9.6 | 24.8 | −15.3 / −40.1 / −64.8 | −3.51 | +9.3 | −14.4 | −2.37 | 3.5 | 2.7 / 2.7 | 23 |
| K3 L72 e2 dollar | +9.6 | 37.6 | −28.5 / −66.1 / −103.7 | −4.07 | +9.4 | −25.8 | −2.43 | 5.4 | 1.8 / 1.9 | 12 |
| K5 L72 e1.25 dollar | +18.8 | 46.7 | −28.4 / −75.1 / −121.8 | −5.64 | +0.7 | −44.0 | −7.53 | 6.7 | 2.8 / 0.1 | 11 |
| K5 L168 e1.25 dollar | +12.2 | 25.1 | −13.1 / −38.3 / −63.4 | −3.01 | +4.1 | −20.2 | −3.33 | 3.6 | 3.4 / 1.2 | 23 |
| K5 L72 e2 factor (worst in validation) | +17.2 | 76.4 | −59.6 / −136.0 / −212.4 | −7.55 | −1.3 | −82.2 | −8.01 | 10.9 | 1.6 / −0.1 | 12 |

**Across all 24 variants:**
- **Discovery gross:** −7.0 to +18.8 bp a day, and 21 of 24 are positive.
- **Discovery cost at 1x:** 17.9 to 76.4 bp a day. Turnover is 2.6 to 10.9 times the book a day.
- **Discovery net at 1x:** −9.0 to −69.6 bp a day.
- **Validation gross:** −13.4 to +9.4 bp a day, and 15 of 24 are positive. Net at 1x is −14.4 to −82.2.
- **j*, the variant picked on discovery, by year at 1x:** 2021 −14.5, 2022 +7.6, 2023 −21.0, 2024 −11.1, 2025 −1.1,
  2026 −97.2 bp a day.
- **Validation halves for j*:** −13.2 (2024-01..2025-06) and −52.0 (2025-07..2026-09).
- **Funding** is under 1.3 bp a day in every variant.

## Cost sensitivity
- At 1x (7 bp per side) every variant loses in both windows. 2x and 3x scale the loss (see the table).
- **The highest break-even cost** is 3.5 bp per side in discovery and 2.7 in validation. Only K3 L168 e1.25 dollar
  holds about 2.7 bp in both.
- No execution path the lab has is that cheap at hourly frequency. The lab's API cost assumption is a 6-8 bp fee plus
  the spread (`docs/DIRECTION.md`); the 7 bp used here, spread included, is below that. Maker fills are adversely
  selected (arXiv 2502.18625; R193 NULL).

## What this does show
- **There is a small reversion in hourly PCA residuals of liquid perps.**
  - Two of the four K = 3 dollar variants make about +9.5 bp a day gross in both windows: L168 e1.25 and L72 e2.
  - The other variants fall away in validation.
  - At about one day's hold, that is roughly 2.7 bp per side of turnover.
  - This is a gross-edge fact, not a strategy.
- **The factor hedge loses more than the dollar hedge in 11 of 12 pairs.** The exception is K1 L72 e1.25, where it
  is 0.6 bp a day better. Rebalancing the eigenportfolio hedge each hour adds 11-98% more turnover, and it does not
  raise the gross consistently.
- **Longer windows (L = 168) trade half as much as L = 72** and lose less, but no variant is cheap enough.

## What this does not show
- **One hour missing in the archive** (2024-10-28 20:00 UTC, every symbol) left no symbol with a return in all 1,440
  hours. The frozen rule therefore emptied the universe for the next 60 days, and the book was flat from 2024-10-29
  to 2024-12-27. Those flat days make the validation means less negative, not more, so the NULL stands. A next lane
  should allow a few missing hours.
- **Turnover is charged on target weights.** Price drift between hours is ignored. The order of magnitude is right,
  but the exact cost is approximate.
- **Lower-turnover versions were not tested,** since they were not frozen. That covers a no-trade band, daily
  rebalancing, a wider exit band, and only the 20 most liquid coins. Testing one now would be a gate-0 lane designed
  after seeing this result.
- **Only Binance USDT perps were used.** MEXC fees and spreads were not modelled.

## Next
- **M298 stops here as a taker strategy.** It does not go to a reserved batch: the gross edge is about a third of the
  cost.
- **The gross reversion goes to the fast-profit axis (M264) as a fact.** A residual s-score could be one input to a
  maker or queue model, if one were ever shown to earn its spread. That would be a new lane with its own PREREG, and
  it would need the tape recorder's data, not hourly bars.
