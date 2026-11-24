# FINDINGS: closing_momentum_v1 (R528). Intraday momentum into the US cash close does not pay on ES at the last hour: NULL

**Verdict: FAIL for both rules** (NULL). Neither rule clears its decided checks on 2018-01..2026-11.

- **Registry:** R528, 2 trials. Program trials become 9,785,790.
- **Reproduce.** The PREREG (sha 3cfd3516) was frozen in commit 08e5ec86 before the data was downloaded.
  - **Data:** Databento GLBX.MDP3 ohlcv-1h for ES.v.0, 2010-06-06..2026-11-20: 34 pulls, $0.9721 quoted, at most
    $0.0306 a pull. `docs/provenance/es_1h.json` records each file's sha256.
  - `run_closing_momentum.py run` ran once on 2026-11-24.
- **Days.** 4,239 New York dates have bars, and 3,922 have all four closes on one contract. The last hour's return has a
  standard deviation of 37 bp. The daily volatility of the 16:00 closes is 1.09%, a plausible level for ES.

## Results (bp a trade on notional; one trade a day, held 15:00-16:00 New York)
| Rule | Period | 1 bp cost | 2 bp | 3 bp | NW t at 1 bp | Hit rate | Sign correlation with the last hour |
|---|---|---|---|---|---|---|---|
| A: sign(previous close → 10:00) | 2010-2017 (reported) | −0.80 | −1.78 | −2.76 | −0.98 | 47.0% | 0.003 (whole sample) |
| A | **2018-2026 (decided)** | **−0.97** | −1.97 | −2.96 | −0.91 | 47.0% | |
| B: sign(previous close → 15:00) | 2010-2017 (reported) | −0.52 | −1.51 | −2.50 | −0.79 | 46.3% | 0.033 (whole sample) |
| B | **2018-2026 (decided)** | **+0.78** | −0.21 | −1.21 | +0.76 | 48.9% | |

- **Annualized on notional** (about 250 trades a year), 2018-2026 at 1 bp: A −2.5%/yr, B +2.0%/yr (t 0.76).
  - Compare with cash (4.1%/yr): the money is committed one hour a day, so the margin also earns cash. Even so, B's
    gross edge does not clear 2 bp of cost.
- **Halves of the decided period** (1 bp): A −1.81 / −0.13 bp, B +1.42 / +0.15 bp.
- **By year** (B, 1 bp): −5.0, +1.2, −3.6, +2.4, +1.4, +3.0, −2.8, −2.7 (2010-2017); +0.8, −0.7, +6.8, −2.5, +4.6,
  +4.3, −2.5, −0.4, −3.7 (2018-2026). Positive years cluster in volatile years (2020, 2022).

## Post hoc, descriptive (not decided; no new trial)
- **Magnitude vs sign.** The returns themselves correlate:
  - first → last hour, 0.078;
  - rest of day → last hour, 0.107.
  That is the literature's regression evidence. A sign rule captures little of it, because the correlation comes from
  the large-move days.
- **Rule B on the largest 20% of moves** (by |rest of day|), gross:
  - 2010-2017: +4.9 bp (t 2.0);
  - 2018-2026: +2.4 bp (t 0.7).
  The big-day effect roughly halved after publication. That fits Baltussen et al.'s result that it lives on
  negative-gamma days, and with 0DTE-era dealer positioning, which this lane does not measure.

## What it means
- **For money:** nothing to trade. A sign rule on the last hour is under 1 bp a trade before costs on 2018-2026.
- **For the lab:**
  - The closing-flow family's simple form is closed on ES at hourly resolution.
  - Two open questions remain:
    - the true last half hour (minute bars, $9.7-$21 of data, an owner decision);
    - conditioning on dealer gamma (M451, blocked for data).
  - Both start from a post-publication decay, so their prior is low.

## What could invalidate this
- **The target is the last hour, not the last half hour.** The literature's strongest window (15:30-16:00) is mixed
  with 15:00-15:30, so a half-hour effect is diluted.
- **ES.v.0 follows the volume-leading contract.** Days with a contract change inside the window are excluded
  (317 days dropped for missing bars or rolls).
- **Costs are an assumption** (one MES tick plus fees, about 0.8-1 bp). They are not measured here.
- **One instrument.** The literature finds the effect across 60 futures markets; only ES was tested.

## Pre-mortem against outcome
| Prediction before the freeze | What happened |
|---|---|
| 1. Decay after publication | Yes on the big-move days (+4.9 → +2.4 bp); the sign rules were already ≈ 0 in 2010-2017 |
| 2. 0DTE reversal from 2022 | Not seen: B was +4.6 and +4.3 bp in 2022-2023, then negative in 2024-2026 |
| 3. Last-hour dilution | Likely part of the null; untested |
| 4. Roll or bad-bar outliers | Not seen: hit rates 46-49%, a smooth year table |
| 5. Costs above one tick | Irrelevant: the gross edge is under 1 bp |
