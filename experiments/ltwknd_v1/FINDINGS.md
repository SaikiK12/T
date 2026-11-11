# FINDINGS: ltwknd_v1 (R465), R462's weekend fade on Lighter's US-stock perps at zero fee

**Verdict: PARTIAL.** R462's weekend overshoot replicates on Lighter in samples A and B: +45.3 bp per market-weekend
before costs in A (p 0.005) and +35.6 bp in B. After the 4 bp cost unit it nets +41.3 bp in A. Sample C, which no
lane had read, is flat at the Sunday 22:00 exit (-1.3 bp), so the frozen PASS bar is not met.

**This is a venue replication, not new evidence on fresh weekends.**
- On the 706 market-weekends shared with R462, Lighter's and xyz's weekend moves correlate at 0.96.
- Their fade returns correlate at 0.92.
- What R465 adds is the same effect at Lighter's zero fee, a venue reachable from France.

**Why C differs: a likely mechanism, found after the run and not decided on.** C's weekends (February to April)
gave the overshoot back on Monday morning, not on Sunday evening. Its Monday 10:00 exit is +194 bp (p 0.09).

Run: `python scripts/run_ltwknd.py`, 2026-11-11, after the freeze (PREREG sha256 `874ffe52`, commit `cd46a704`).
- The PREREG verified and its 10 inputs matched.
- 100 bar and funding files matched `data/lighter_wknd/manifest.json` (`results/run.log`).
- The bars were fetched after the freeze by the frozen `scripts/fetch_lighter_wknd.py bars`. Provenance is in
  `docs/provenance/lighter_wknd.json`: 50 markets, 199,448 hourly candles from 2026-02-13 to 2026-11-09 23:00 UTC,
  no holes.
- **Events** (market-weekends with W ≠ 0):

  | sample | events | markets | weekends |
  |---|---|---|---|
  | A | 510 | 38 | 18 |
  | B | 214 | 39 | 6 |
  | C | 117 | 17 | 8 |

- **Skipped:**
  - 614 market-weekends where the market was listed on Lighter less than 7 days before Friday (many were listed in
    2026);
  - 145 unpriced (no trade in the window).

## Decision cell
`all` markets, |W| ≥ 50 bp, exit X1 (Sunday 22:00 New York), fade side, g = price + funding, bp per market-weekend.

| sample | n | weekends | mean | sd | hit | p (cluster) | MDE80 |
|---|---|---|---|---|---|---|---|
| A | 308 | 18 | +45.3 | 139 | 66% | 0.005 | 22 |
| B | 128 | 6 | +35.6 | 151 | 58% | 0.53 | 37 |
| C | 80 | 8 | -1.3 | 144 | 55% | 0.97 | 45 |

- **Frozen rule:**
  - A has its sizes, p ≤ 0.05 and a mean above 2 units (8 bp);
  - B has its sizes and a mean above 1 unit;
  - C has its sizes and a mean ≤ 0.
  - So the lane is PARTIAL, not PASS.
- **Costs** (unit 4 bp: 0 fee and 4 bp of assumed slippage): A nets **+41.3 / +37.3 / +33.3 bp** at 1x / 2x / 3x.
  - Lighter's weekend books for these markets were not measured.
- **Funding** is small: the mean f_x1 is +0.2 bp in A.
- **Read against the program's 9,785,174 trials,** a p of 0.005 alone is weak.
  - R462's PASS on the same weekends with xyz prices (p 0.004) is the same event set, not a second sample.
  - R463 (xyz) and a Lighter forward lane, on fresh weekends, decide.

## Other cells (reported, not decided on; all 32 in `results/cells.csv`)
- **A, X1:**
  - the fade grows with |W|: +30.7 bp at θ 0, +53.8 at θ 100, +79.3 at θ 200;
  - every `all` and `single` X1 cell has p ≤ 0.005.
- **Funds** (5 markets) are noisy (n 26 at θ 50, p 0.23).
- **The `rel` book** (each market against the weekend median) is the strongest:
  - A: +62.1 bp at θ 50, X1, p < 0.001;
  - C: +47.7 bp at θ 50, X1, p 0.07, positive where the outright book is flat.
- **Exit X2 (Monday 10:00)** is noisy (sd about 400 bp):
  - A: +46.1 bp, p 0.24;
  - B: +187 bp, p 0.16;
  - C: +194 bp, p 0.09.

## When the overshoot is given back (computed after the run, not pre-registered)
The fade-signed mean move from Sunday 19:00, by hour (New York), for the decision events (|W| ≥ 50 bp). Each price is
the last trade before the hour.

| sample | 20:00 | 21:00 | 22:00 | 23:00 | Mon 01:00 | 04:00 | 05:00 | 06:00 | 07:00 | 10:00 |
|---|---|---|---|---|---|---|---|---|---|---|
| A | +5 | +32 | +45 | +33 | +32 | +13 | +5 | +7 | +20 | +45 |
| B | +26 | +32 | +35 | +20 | -9 | +11 | +23 | +7 | +27 | +185 |
| C | 0 | -17 | -4 | +4 | -9 | +6 | +40 | +52 | +35 | +191 |

**May to November (A, B).** The give-back comes between 20:00 and 22:00 on Sunday. That is when the Blue Ocean
overnight session resumes and trade.xyz's external price returns (Sunday 20:05).

**February to April (C).** Nothing happens on Sunday evening. The give-back comes between 04:00 and 06:00 on Monday,
when the pre-market session opens.

**Most likely reading.** Lighter's equity oracle, Pyth Pro for 46 of these markets, did not carry the overnight session
before mid-2026, so the external price returned only at the pre-market.
- Pyth moved its overnight feeds to Pyth Pro on 2026-06-15 (wave 7, lens 6 [V]).
- Lighter's docs give no Sunday time [A].
- This reading was not pre-registered and does not change the verdict.

What it says for a forward lane: exit after the venue's external price returns. On Lighter today, that is Sunday
evening, as in A and B.

## What this changes
- **M515** gets a second venue at zero fee: the effect is not specific to xyz's oracle.
- **The frozen stop rule:** a PARTIAL earns a forward paper lane on Lighter under a new id, with tickets at E and
  recorded Lighter book costs, never a trade.
  - R463 (xyz) stays as frozen.
  - Lighter's and xyz's weekend moves correlate at 0.96, so the two forward lanes would largely trade the same
    events at two costs.
- **R466** (the xyz-versus-Lighter gap pair, M524) ran on the same data. It was INCONCLUSIVE because the two venues'
  Sunday prices sit close together (median gap 7.6 bp).
