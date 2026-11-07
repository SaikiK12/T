# PREREG: vixpanic_v1 (R283). Does a VIX panic mark a short-term low? (M278)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R283
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_vixpanic.py`. It calls `verify()` on this file first and records every input file's sha256.
- **Data:**
  - `data/cboe/{VIX,VIX3M,VVIX}.parquet` (`scripts/fetch_cboe.py`, fetched 2026-10-21; provenance in
    `docs/provenance/cboe.json`);
  - Yahoo daily SPY and QQQ through `lab/markets.py`, loaded with `scripts/run_fxindex.py`'s `etf()` (adjusted open
    and close);
  - `data/klines_1h/BTCUSDT.parquet` and `data/fundingRate/BTCUSDT.parquet`, with rows before 2021-01-01 dropped on
    load (2020 is reserved, `docs/GATES.md`).
- **Source of the claim:** Stay Solvent (@ojrenick), TikTok 2026-10-20, in `docs/VIDEO_DIG.md`.
  - The claim: "the combination of VIX and the VIX futures curve for moments of extreme blowout and panic... just don't
    often last", with VVIX at 120 and the curve in backwardation marking a short-term bottom.
  - This lane uses the cash VIX3M index for the curve. Cboe's VX futures files are not held.
- **Gate:** 0. The equity years were read by R239 and R241 in other forms, and BTC 2021-26 by many lanes.

## What the author has seen
- **R239 VIXREV:** QQQ after a 1-day drop of more than 1% with VIX above 25. It had t 1.94 on 2001-12 and was NULL out
  of sample.
- **R241:** that rule had alpha t −0.05 on 2013-19. SVXY held while VIX < VIX3M had t 1.7-2.4 in every window, with
  45-66% drawdowns. So the VIX/VIX3M state was read as a short-vol signal, never as a long-equity or long-BTC trigger.
- **Never computed by this lab:** any statistic of VVIX, and any return after a VIX > VIX3M day.
- **Data structure only:** VIX3M starts 2009-09-18 and VVIX 2006-03-06. The video says VVIX reached 120 and VIX 22 on
  2026-10-16.

## Rules
**Signal day D** is a Cboe trading day with VIX, VIX3M and VVIX closes. Cboe's closes are the 16:15 New York
settlements, public by about 21:15 UTC on D. Three triggers:
- **BACKW:** VIX close of D > VIX3M close of D.
- **VVIX95:** VVIX close of D ≥ the 95th percentile (numpy linear) of the 252 VVIX closes ending at D, D included.
- **BOTH:** BACKW and VVIX95 on the same D.

**Onsets.** An onset of a trigger is a day D where the trigger holds and held on none of the 20 Cboe days before D.
- Scored onsets have D from 2009-10-19 to 2026-09-01. Exits then fall on or before 2026-09-30, the archive's end.
- Onsets are at least 21 Cboe days apart, so holds of up to 20 days never overlap.

**Trades:** long only, one per onset.
- **SPY, QQQ:**
  - Entry at the adjusted open of the first trading day after D (day 1). Exit at the adjusted close of trading day h.
  - h is 5, 10 or 20 trading days.
  - Return = adjclose(day h) / adjopen(day 1) − 1.
  - Cost: 1 bp one-way at 1x (as R239), so 2 bp per round trip.
- **BTCUSDT perp (Binance):**
  - Entry at the open of the hourly bar starting 22:00 UTC on D. Exit at the open of the bar 7, 14 or 28 calendar days
    later (h = 5, 10, 20 trading days).
  - Return = exit open / entry open − 1, minus the sum of funding rates settled in (entry, exit] (a long pays a
    positive rate).
  - Cost: 7 bp one-way at 1x (R275's leg cost), so 14 bp per round trip.
  - Scored only for D from 2021-01-04 to 2026-09-01. An onset needs both bars to exist.
- Costs at 2x and 3x are twice and three times the 1x cost.

**Trials:** 3 triggers × 3 horizons × 3 assets = **27**.

## Test
For each cell (trigger, h, asset):
- **Eligible days:** every Cboe day D in that asset's scored window whose trade can be computed. Each one's h-day
  return is formed exactly like an onset's.
- **Observed:** the mean gross return over the cell's n onsets.
- **Null:** 20,000 draws of n distinct eligible days (numpy default_rng, seed 283), each draw's mean.
  - p = (1 + #draws with mean ≥ observed) / (1 + 20,000), one-sided.
  - n < 5: the cell is reported, not tested (p = 1).
- **Excess:** observed mean − the mean over all eligible days.
- **Pass:** p ≤ 0.05 / 27 = 0.00185, and the mean net at 2x > 0, and the mean without the single best onset > 0.

**Verdict:**
- **PARTIAL** if any cell passes. Gate 0: a pass earns a forward paper lane under a new id. The BTC cells are also
  candidates for a reserved 2020 read.
- **NULL** otherwise.

M278's own claim is the BOTH row. It gets no separate alpha.

## Reported (not decided on)
- **Per cell:**
  - n, and mean net bp at 1x, 2x and 3x;
  - mean gross, eligible-day mean, excess;
  - median, hit rate, worst onset, mean without the best onset;
  - the halves: onsets before and from 2018-01-01;
  - p.
- **Family view:** the count of the 27 p-values ≤ 0.05, against 1.35 expected under the null.
- **The onset dates of each trigger.**
- **After the window:** trigger days from 2026-09-02 on are listed (2026-10-16 included) without returns. A future
  lane may score them.
- **Read against** `registry.program_trials()`.

## Outputs
`experiments/vixpanic_v1/results/`:
- `cells.csv` (one row per cell);
- `onsets.csv` (one row per onset, trigger, asset and h, with gross and net);
- `summary.json` (verdict, input sha256s, family count);
- `FINDINGS.md` by hand after the run.
