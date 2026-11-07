# PREREG: dvolbeta_v1 (R385). Each coin's return beta to Deribit DVOL changes as a weekly sort on the top-150 perps (M456, sort half only)

Frozen with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R385
- **Method M456:** DVOL-beta sorting (the gamma-weighted option-inventory half is out of scope; see below).
- **Owner (single writer):** the Claude lane worker that froze it, 2026-11-02 (UTC).
- **Execution mode: API,** as R299, R304 and R332.
- **Gate: 0, on seen data.** The panel's windows were read by R299, R304, R305 and R332 with other signals.

## Question
Does sorting the top-150 Binance perps each week on their trailing 90-day return beta to daily BTC or ETH DVOL changes
(long one fifth, short the other, held 7 days) earn a positive net return at API costs in 2024-01..2026-09, after the
sort was picked on 2022-23?

## What is held (checked before writing this file; no return and no DVOL value was computed)
- `data/deribit/dvol_BTC.parquet` and `dvol_ETH.parquet`: hourly OHLC of Deribit's DVOL, 48,851 contiguous hourly
  bars each, 2021-03-24 00:00 UTC .. 2026-10-19 10:00 UTC. Daily history before 2021-03-24 is not held (not needed:
  the first decision is 2022-01-01 and the first full 90-day window ends 2021-06-22).
- `data/daily/panel.parquet` (R304's panel, 591,598 rows, 2021-01-02..2026-09-30): row D is a decision at 00:00 UTC of
  day D and holds day D-1. `ret`, `close`, `fund`, `rank_qvol30`.
- Per-coin DVOL does not exist. The beta is to the BTC or ETH index only, as the M456 row says.

## Data and point-in-time rule
- **Coin returns:** the panel's `ret` on row D (the simple return of day D-1, UTC, close to close). Point in time.
- **DVOL change on row D:** x_D = ln(DVOL_D) - ln(DVOL_{D-1}), with DVOL_D the close of the last hourly bar of day D-1
  (the bar opening 23:00, closing 00:00 of D); the panel's own rule for hourly bars (bar opening at t goes on row
  ceil((t + 1 h) / 1 day)). Row D's return and x_D cover the same 24 hours. A missing row gives NaN, never zero.
- **Beta of coin i on row D:** the OLS slope of `ret_i` on x over rows D-89..D (90 calendar rows, row D included),
  using rows where both exist; needs at least 60 pairs and a positive variance of x on them, else the coin has no score
  and is not ranked on that day. Univariate: no market control, no winsorizing.
- **Signed beta, not absolute.** "Low beta" is the most negative slope. Crypto returns fall when DVOL rises, so most
  betas are negative and the low-beta fifth is, in practice, the high-market-beta fifth. This is expected and is
  reported (descriptive correlation with the equal-weight top-150 return); it is not removed.
- **Universe:** R299's: top 150 Binance perps by trailing 30-day volume (`rank_qvol30` <= 150) with a close on row D.
  Rows exist only when the perp traded, delisted perps are included up to their last trading day. Mexc-only coins, 2020
  rows and `reserved/` folders are not read.
- **Survival:** later-delisted share per leg is not computed in this lane (listed under "not checked").

## Books (4 trials)
Sort score on each universe row with a beta, from 2022-01-01:
1. **BTC LH:** long the fifth with the lowest BTC-DVOL beta, short the fifth with the highest.
2. **BTC HL:** the reverse (long high, short low).
3. **ETH LH:** as 1 with ETH DVOL.
4. **ETH HL:** as 2 with ETH DVOL.

Common to all four, unchanged from `scripts/run_mlrank.py` (frozen, imported): legs = top and bottom `n // 5` of the
scored universe rows (at least 30 scored names, else no trade that day), equal weights, seeded random ties (seed 299);
decisions every 7th day from the first prediction day (2022-01-01), hold 7 days; entry at row D's close; exit at the
last close in rows D+1..D+7 (none: 0); funding over the hold paid by longs; costs per side on each rebalance's turnover
(`run_lotcap.costed`, first entry from zero). No other feature, horizon, quantile, window or DVOL transform is tried.
LH and HL of the same DVOL are exact mirrors in gross return; they differ only through costs and are both counted.

## Splits and cost
- **Discovery** 2022-01-01..2023-12-31; **validation** 2024-01-01..2026-09-30. A period counts only when its hold ends
  inside the window (`run_mlrank.window_mask`). Validation is read once.
- **Costs:** API 8.5 bp per side at 1x, 17 at 2x, 25.5 at 3x. Net series are reported at all three.
- **t** is Newey-West on a calendar grid of weekly periods, lag 2 (`run_lotcap.series_stats`).

## Decision (written before any statistic)
- **The pick:** among the four books with a positive discovery net 1x mean, the one with the highest discovery net 1x t
  (R299's `decide`). If none has a positive discovery mean, there is no pick and the verdict is NULL.
- **It passes** only if, in validation, all three hold:
  1. net 1x t >= 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best periods is positive.
- **Verdict:** PARTIAL if the pick passes, NULL otherwise. Nothing is read from the three books that are not picked.
  A PARTIAL here is a lead only (gate 0, seen data): no real money, no forward lane without a separate registration.

## Descriptive, not trials, never picked
Per book: gross and net per leg, rank IC of the score against the ranked forward net return (Newey-West), turnover,
names per leg, the median beta and its share below zero, scored names per day, and the correlation and slope of the
book's gross on the equal-weight top-150 return over the same hold.

## Out of scope
- **Gamma-weighted option inventory** (the other half of M456, a state flag by net option inventory) needs chain-priced
  option data over years. `data/deribit_trades` holds trades, not marked chains, and `data/option_expiry` starts
  2026-10-29. Not tested, not approximated.
- The M456 row's "state filter on a strategy that already passes" framing: no parent strategy passes gate 1, so this lane
  tests the sort as a stand-alone book, which the row says is not the intended use. A NULL here is a NULL of that
  stand-alone reading only.

## Multiplicity
- **This lane:** 4 trials, registered as 4. **Program trials so far:** 9,479,252 (`registry.program_trials()` on the
  rounds file at 2026-11-02, before this row); the program total after it is 9,479,256. The raw sum is bookkeeping, not
  an effective independent-test count.
- **Lineage:** method M456 (queue row untested). Related, not parents: M138/R209 (DVOL minus realized, NULL), M300,
  M099. Samples already seen by any parent: the panel's windows (R299, R304, R305, R332); none of them used DVOL. No
  fresh sample; the result is exploratory and gate 0.
- `docs/GATES.md` sha256 at freeze: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. The
  dependent-null, strict on-time clock, 10-day trimming, leave-two-coins-out and power items of that gate are not done
  here; the frozen lane-native verdict is separate from gate admissibility.

## Code
`scripts/run_dvolbeta.py` (this lane's runner), tested on synthetic data in `tests/test_run_dvolbeta.py` (beta recovers
a known slope and matches `polyfit`, a future change does not move row D, the 60-pair minimum, the DVOL daily timing,
and the four books on a synthetic panel; no real return or DVOL value is read). It calls `prereg.verify()` first and
checks the inputs block below with `scripts.run_clockflow.check_inputs`.

## Stop rules
One run. No new features, windows, quantiles, DVOL transforms or coins after seeing results; a changed idea is a new
lane with a new id. A null is recorded with the same care as a hit.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
71d38f83f20280519b2e10ecabaf90ed42d99c7fbb5cdd7e0cded42d49437aee  data/deribit/dvol_BTC.parquet
d966bc0c02c07b8533888eb2f366ea8159b4a9f5fa1d83fdb552fa9d4212575e  data/deribit/dvol_ETH.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe  lab/data.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
29546559f884d584fa1ab0e265bf51b4d46d7fceb671e08f31e3bf1ca3d94d3b  scripts/run_dvolbeta.py
```
