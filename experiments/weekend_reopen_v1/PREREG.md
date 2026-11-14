# PREREG: weekend_reopen_v1. Do Binance's 24/7 TradFi perps fade or follow their weekend move when the CME week reopens?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R432
- **Owner (single writer):** Claude (hunt-mode fork of the 2026-11-09 session); the orchestrator commits and closes the row.
- **Date registered (UTC):** 2026-11-09

Methods: M321 (index perp weekend gap at the CME reopen) and M188 (TradFi perps over the weekend). Gate 0.

## Disclosure: one outcome line seen before this freeze
At 22:55:56 UTC the synthetic dry-run read the real archive by mistake. `build(data=DATA)` binds its default argument
when the function is defined, so the dry-run's path override did not apply. It printed one line about the primary cell
below:

- n 90 trades on 28 weekends;
- gross +6.78 bp;
- net at 1x −5.22 bp, bootstrap interval −38.09 to +25.70;
- verdict NULL.

**What was not seen.** No other cell, slope, split, placebo or per-asset number was printed or read. The scratch outputs
were deleted unread at 22:56:24 UTC.

**What was fixed before the exposure.** The whole design below: the primary cell, set at about 22:54, and every grid,
cost and rule. It is unchanged after the exposure.

**The fix.** `load`, `build` and `plumbing` now resolve the data path at call time. The dry-run was repeated with a guard
that fails if it opens any real file.

**How to read this lane.** As a gate-0 screen, whose primary verdict was seen once before the freeze. It is not a blind
test.

## Question
At the CME Globex reopen (Sunday 18:00 New York), does each Binance TradFi perp give back part of its weekend move
(fade) or extend it (follow), by more than a taker round trip?

## Universe
Seven Binance USD-M TradFi perpetuals:
- **equity:** QQQUSDT, SPYUSDT;
- **metals:** XAUUSDT, XAGUSDT;
- **energy:** CLUSDT, BZUSDT, NATGASUSDT.

These are all the TradFi perps the lab holds as 1-minute history. They are current listings; none was delisted in the
window.

## Data
`data/tradfi_perps/klines_1m`: data.binance.vision 1-minute klines, each file checked against its published SHA-256 by
`scripts/fetch_tradfi_perps.py`.
- The manifest sha256 `da4c8b70…` (the file hash is in the inputs block).
- History runs from listing to 2026-10-27 23:59 UTC: XAU from 2025-12-11, XAG from 2026-01-07, CL/BZ/NATGAS from
  2026-04-01, QQQ/SPY from 2026-04-06.
- **Backtest data and trade venue are the same** (Binance).
- No CME or cash reference price is held, so the perp is its own reference.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| P(τ): close of the last 1-minute bar with trades that opens at or before τ − 1 min, at most 60 minutes old | kline open time t, close, count | Binance USD-M kline, USDT, price | the bar ends at or before τ | bar close; archive published the next day | yes, at τ | archive as published, listing to 2026-10-27 | missing or older than 60 min: the asset's weekend is dropped |
| W_pre = 1e4 ln(P(Sun 17:55 ET) / P(Fri 17:00 ET)) | P | bp | Friday CME close to 5 minutes before the reopen | at Sunday 17:55 ET | yes (decision at 17:55) | same | as P |
| W_post = 1e4 ln(P(Sun 18:00 ET) / P(Fri 17:00 ET)) | P | bp | Friday close to the reopen | at Sunday 18:00 ET | yes (decision at 18:01) | same | as P |
| Exit returns R = 1e4 ln(P(X) / P(E)), X ∈ {S+15 min, S+60 min, Mon 09:30 ET} | P | bp | entry to exit | outcome | n/a (outcome) | same | as P |
| Holiday flag: Friday or the following Monday is an NYSE holiday | `lab.sessions.NYSEHolidays` | calendar | | known in advance | yes | rule-based | |

All inputs are point-in-time trade prints. There is no cross-sectional ranking, so there is no survivorship question
beyond the seven listed contracts.

## Rule or search space
- **Anchors, in New York local time (DST-aware):**
  - F = Friday 17:00 ET;
  - S = Sunday 18:00 ET;
  - entries E_pre = S − 5 min and E_post = S + 1 min;
  - exits x15 = S + 15 min, x60 = S + 60 min and cash = Monday 09:30 ET.

  Fridays run from 2025-12-12 to 2026-10-23 (46). The 7 weekends touching an NYSE holiday are dropped: 2026-01-16,
  02-13, 04-03, 05-22, 06-19, 07-03 and 09-04.
- **A trade:** |W_e| ≥ θ, with W ≠ 0.
  - Fade gross = −sign(W) · R_{e,x}. Follow gross = +sign(W) · R_{e,x}.
  - Equal weight, one trade per asset per weekend.
- **Book grid (144 cells):** entry {pre, post} × exit {x15, x60, cash} × θ {0, 50, 100 bp} × group {all, equity,
  metals, energy} × direction {fade, follow}.
- **PRIMARY (decides the verdict):** entry pre, exit x15, θ = 50 bp, group all, direction fade.
  - **Why fade:** a source reported in M442 (unread here) maps a 1% weekend perp move to about 0.7-0.9% of the later
    reference-market move. The perp overshoots, so it should give back 10-30% of its move when the CME price returns.
  - **Why the pre entry:** the re-anchoring happens at the reopen itself, and only a position held through 18:00 ET
    captures it.
  - **Why x15:** the re-anchoring is fast, and a short exit keeps the noise of the Asian Monday session out.
  - **Why θ = 50 bp:** a 10-30% giveback of 50 bp or more is of the order of the 12 bp cost unit. Plumbing (the signal
    only) gives 90 eligible asset-weekends.
- **Commodity regime split (4 cells):**
  - A news report says Binance moved commodity TradFi perps' off-hours mark to an order-book EWMA, announced
    2026-05-05. The effective date is UNVERIFIED; the split takes the Friday 2026-05-08.
  - Metals and energy pooled, primary spec, before and after that date, fade and follow.
  - The equity perps keep the fixed method and are the control.
- **Slopes (24 cells):** the OLS slope of R_{e,x} on W_e, per entry, exit and group, with a weekend-block bootstrap
  interval.
- **Placebo (2 cells):** the primary spec with S moved 24 h earlier (Saturday around 18:00 ET, when nothing reopens),
  fade and follow.

## Splits and cost
- **No split.** This is one gate-0 screen on the whole archive.
- **Cost unit:** a 12 bp round trip, as in R368: a 5 bp taker fee each way plus 2 bp of spread and slippage for both
  fills.
  - Launch coverage says the TradFi perps use the fee structure of Binance's crypto perps. The Binance TradFi fee
    page was not read; the regular USD-M taker fee is 0.05%.
  - Weekend books may be thinner than 2 bp suggests. The 2x and 3x levels (24 and 36 bp) cover that.
- **Funding:** not charged. The x15 and x60 holds cross no funding time. The cash exit crosses two 8-hour settlements,
  which are not modelled (a limit).

## Gates
The primary verdict (`verdict()` in the runner):
- **PASS (gate 0):** at least 30 trades on at least 12 weekends; mean net > 0 at 1x and at 2x; the weekend-bootstrap 95%
  lower bound of the 1x net > 0; and a positive gross mean in every group with at least 5 trades.
- **PARTIAL:** mean net at 1x > 0 and the one-sided bootstrap p (share of resampled 1x means ≤ 0) < 0.10, but not
  PASS.
- **INCONCLUSIVE:** fewer than 30 trades or 12 weekends.
- **NULL:** otherwise.
- **What a pass earns:** a forward paper lane with a new id on new weekends, and the history from 2026-10-28 onward
  fetched from the public archive. It earns nothing more.

## Null
- **Bootstrap:** every interval and p resamples whole weekends, 10,000 draws, seed 432. The assets share a weekend's
  news, so the weekend is the unit.
- **Placebo:** a fake reopen 24 h earlier checks that any effect belongs to the CME clock.
- **Power:** with about 90 primary trades on 28-39 weekends and a per-trade standard deviation of tens of bp
  (energy dominates), the 80% minimum detectable mean is of the order of 10-20 bp. A null therefore rules out a
  giveback worth two or more cost units, not a small one. The runner reports its MDE80 from the realised sd.

## Multiplicity
- **This lane:** 174 trials = 144 book cells + 4 regime-split cells + 24 slope cells + 2 placebo cells. Only the
  primary decides.
- **Program trials before this lane:** 9,784,511 (`registry.program_trials()`, 2026-11-09 22:57 UTC).
- **Other cells:** a cell beside the primary is exploratory. No cell can claim significance against the program total.

## Evidence lineage and admission
- **Canonical method ids:** M321, M188. Related: M442 (weekend direction downgraded on two unread papers), M447 (CME
  reopen re-anchoring on the recorder, not used), R244 (BTC's weekend move into QQQ/SPY, NULL; a different question).
- **Parents:** R368 used the same files around EIA releases on weekdays only. This lane reads them over weekends for
  the first time, apart from the disclosed primary line above.
- **Decision group:** TradFi perps' weekend and reopen behaviour.
- **Fresh sample:** none. This is gate 0 on archive data. A pass is confirmed only forward.
- **`docs/GATES.md`:** not a frozen input. Another writer changed it during this session (its sha moved from `e7dd02fa…`
  at 22:57 UTC). The rules applied here are the ones written in this file. Met: a frozen spec, 1x/2x/3x costs and a
  weekend-clustered bootstrap. Unmet: a fresh sample (gate 1).
- **Selection control:** none across families. Any result here is exploratory.

```inputs
fbcb091e1af43aceebfb60dd389b07f0af0990a4be2602a2df8e8948cbd107c3 scripts/run_weekend_reopen.py
804b2cf12621f9a10802963ce947d3189d8072b381fa10fcc36b6ca10f0637a3 tests/test_run_weekend_reopen.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d lab/sessions.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba scripts/run_clockflow.py
d941bffed424c79f2afddce68f9df4086b1fb345830bb35ba46b8a8583137bd0 data/tradfi_perps/klines_1m/manifest.json
0af7519eb54a6c132c6f2d86a90d9c344c28361584e9695b29c54ccb3ef65ef5 data/tradfi_perps/klines_1m/BZUSDT.parquet
2f57530cffdd208fa08fe9e4b2cd8973f040be289a6f93a21aeec5efab5dc729 data/tradfi_perps/klines_1m/CLUSDT.parquet
c4216c50967ef57437ae42db6a81966c8b50a27bfaec3fd2de4d8a135b52d947 data/tradfi_perps/klines_1m/NATGASUSDT.parquet
f994683fe9c5b7ad7ff9103e916b30e5bfb66211c9ffd967a9a1695914451d31 data/tradfi_perps/klines_1m/QQQUSDT.parquet
1a8a6dfe7d4fb808c1bc40fbebb75af41d6017f6ff462d7c2678bac43abf9135 data/tradfi_perps/klines_1m/SPYUSDT.parquet
3ae64576ee84404436b0dd8c6ff21e7373b1605c854b5e990d8f4ccacb3f900d data/tradfi_perps/klines_1m/XAGUSDT.parquet
dceb42700e002af73752cabb070739e02eb1451ca0ef6b890cd0ba163bf4d53a data/tradfi_perps/klines_1m/XAUUSDT.parquet
```
