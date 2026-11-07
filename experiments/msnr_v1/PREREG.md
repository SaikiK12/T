# PREREG: msnr_v1 (R306). Malaysian support and resistance on 4-hour candles: fade or follow the first touch of a fresh level (M323)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R306, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Method: M323**, from the owner's reel DejYIVkhcLQ (2026-10-22). The reel is a prop firm's skit that mocks the
  method. Its definitions come from LuxAlgo's "Malaysian SnR" page and the TradingView script "Malaysian SnR [by
  DanielM]":
  - **A-level (resistance):** the close of a bullish 4-hour candle followed by a bearish one, a line-chart peak.
  - **V-level (support):** the close of a bearish candle followed by a bullish one.
  - **Freshness:** a level is fresh until a wick touches it. The method trades the first touch.
  - **Gaps:** the method's gap levels need session gaps. 24/7 perps have none, so gap levels are not part of this
    lane.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_msnr.py`, tested on synthetic paths in `tests/test_run_msnr.py`:
  - 4-hour candles from hourly rows, with the inputs left unchanged;
  - A- and V-levels from candle bodies, live only once the next candle has closed;
  - the first touch needs the wick to pass the level by 2 bp;
  - fade and break entries;
  - funding, costs and the one-position rule;
  - the bracket's stop-first rule;
  - the cohort window and the trial count;
  - the file-tree hash.

  It calls `verify()` on this file first, then checks every input's sha256 (the `inputs` block) and the two file
  trees (the `trees` block: one sha256 over the sorted list of (file sha256, path) lines; `--trees` prints them).
- **Data:**
  - **Crypto (decided on):** the hourly research universe (`data/research`, 499 Binance perps, 2021-01-01 ..
    2026-09-30). It gives close, the next-bar return net of funding, eligibility, the 30-day volume rank and the cost
    tier. Open, high and low come from `data/klines_1h`.
  - **Secondary (reported, counted, not decided on):** 4-hour candles of:
    - Binance XAUUSDT, XAGUSDT and PAXGUSDT;
    - MEXC EUR, GBP, JPY, SILVER and XAU perps (`data/mexc_hist`, from 2025-04-01);
    - MEXC NAS100, SPX500, US30, HK50, JP225, USOIL, UKOIL, NGAS and QQQSTOCK (`data/mexc_tradfi`, from each
      listing, mostly 2026).

    Rows at or after 2026-10-01 are dropped on read.
- **Not reserved:**
  - No row before 2021 is read; the research universe starts 2021-01-01.
  - No row at or after 2026-10-01 is read.
  - No `reserved/` folder is read.
  - The MEXC instruments here are FX, metals, indices, commodities and one ETF, not coins. GATES reserves MEXC-only
    *coins*, and batch 1 (R286) fixed that set as R265's 41 unlock contracts. SILVER and XAU also have Binance perps
    in the archive (XAGUSDT, XAUUSDT).
- **Execution mode: API.** Entries come at any hour, and a busy day has hundreds of first touches across the top 50.
  That is beyond manual web's ~15 orders a day.
- **Gate: 0, on seen data.** R243, R246, R248 and R263 read these years with related level and chart rules (below). A
  pass earns a place in a reserved batch and a forward paper lane, not a confirmation.

## What the author has seen
- **R243 (`chartist_v1`):** seven chart rules on 4-hour and daily bars of the top 50, NULL. Pivot breaks lose (1d
  −14.5 bp/day, t −1.99). Fades lose (STOCH/4h alpha t −2.07). 4-hour trend rules are eaten by 5.9-8.7 bp/day of
  cost.
- **R246 (`ictlevels_v1`):** round-number crosses and rejections on hourly bars, NULL (t −9.9 and −9.7, mostly cost).
  Its FINDINGS says the round-number books carry the generic one-hour reversal, not a level effect.
- **R247 / R248 (`chartxm_v1`, `pivotfade_v1`):** floor pivots on FX, indices and crypto, NULL; the pivot family is
  closed. M203 (fractal swing levels) is PARTIAL with bounces untested. This lane is the nearest to it.
- **R263 (`brute5k_v1`):** 5,472 chart strategies on the top 20, NULL. 1-hour rules lose to costs. It has breakout
  families, but no body-based level with a freshness rule.
- **R300 (`intrars_v1`):** the first UTC hour reverses in both windows (post hoc). A fade here may load on that.
- **The plumbing run of this script** (counts only, no return read; age 30 candles):

  | Count | Value |
  |---|---|
  | Perps ever in the top 50 | 499 (the universe is the perps that were ever eligible; eligibility is the top 50) |
  | Hours | 50,376 (2021-01-01 .. 2026-09-30) |
  | Levels (A and V, all perps) | 1,422,244 |
  | First-touch fade events in the top 50 | 272,960 |
  | First-touch break events in the top 50 | 124,459 |

  Secondary hours on the 4-hour grid: XAUUSDT 7,048; XAGUSDT 6,396; PAXGUSDT 13,260; EUR 12,996; GBP 12,568; JPY
  12,568; SILVER 6,616; XAU 3,040; NAS100, SPX500 and US30 5,868 each; HK50 5,560; JP225 3,856; USOIL, UKOIL and NGAS
  5,852 each; QQQSTOCK 8,072.
- No return of any book was computed before this freeze.

## The family (12 crypto books, 24 trials)
**Common to all books**
- **Candles:** 4-hour candles from hourly rows 4k..4k+3, aligned to 00:00 UTC. A candle with any missing hour is NaN.
- **Levels:** for each pair of consecutive candles (k, k+1), one bullish and one bearish:
  - bullish then bearish: an A-level at the close of k;
  - bearish then bullish: a V-level at the close of k.

  The level is live from the first hour after candle k+1 closes. It carries the 14-candle ATR at k+1, as a fraction
  of price.
- **First touch:** the first live hour whose high is at least the A-level × (1 + 2 bp), or whose low is at most the
  V-level × (1 − 2 bp), within `age` candles of going live. After that the level is spent, traded or not.
- **Modes:**
  - **fade:** a resting limit at the level fills on the first touch, against the move. That is a short at an
    A-level, a long at a V-level. If that hour opened beyond the level, there is no fill and no trade.
  - **break:** if the 4-hour candle of the first touch closes beyond the level, enter at that close with the move: a
    long through an A-level, a short through a V-level. Otherwise no trade.
- **Age:** 30 candles (5 days) or 180 candles (30 days).
- **Exits:**
  - **t24 / t72:** the close 24 or 72 hours after entry.
  - **bracket:** a stop 1 ATR from entry and a target 2 ATR from entry, else the close after 72 hours. Within an
    hour bar the stop comes first. A fade's entry hour can only stop out, since the order of its moves is unknown.
- **Universe (crypto):** an entry needs the perp eligible and in the top 50 by trailing 30-day volume at the entry
  hour.
- **Position rule:** one position per instrument at a time. Several levels first touched in one hour give one trade:
  the level reached first (the lowest A-level or the highest V-level).
- **Funding:** a long pays the funding that settles after entry and up to the exit hour; a short receives it. For
  crypto it is backed out of the universe's close and return arrays; for the secondary set it is the settled rates.
- **Costs per side:**
  - crypto: the universe's tier, 6 bp (top 20) or 8 bp (21-50);
  - secondary: 8.5 bp;
  - at 1x / 2x / 3x, charged on entry and exit.
- **Books:** mode {fade, break} × age {30, 180} × exit {t24, t72, bracket} = 12. The secondary set runs the same 12
  books once, pooled over its instruments: 12 more trials, report only.

**Windows:** discovery 2021-01-01..2023-12-31, validation 2024-01-01..2026-09-30. A trade counts in a window when it
enters on or after the start and exits before the end.

## Statistics
- **The decided series:** per book and window, each entry day's mean net return per trade, over the days with at
  least one entry. That is the equal-weight book of the day's entries.
- **The t:** Newey-West, lag 3, on that day series. With 10 or fewer days there is no t, and the book cannot be
  picked.
- **Reported per book and window:** trades, days, the mean (bp per trade, by day), the mean per trade, the hit rate,
  and the mean without the 10 best days, at 1x/2x/3x. In validation at 1x, also the A-level and V-level trades
  separately.

## Decision
- **The pick:** the crypto book with the highest discovery net 1x t, among those with a positive discovery mean.
- **It passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best days is positive.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once. No second pick. The secondary
  set decides nothing.
- **What a pass earns:**
  - a place in a reserved batch (2020 rows for about 80 perps, and the MEXC-only coins);
  - a forward paper lane with its own id on MEXC prices.
- **What a NULL means:** fading or following the first touch of a body-based 4-hour level does not pay net of API
  costs on the top-50 Binance perps in 2024-26 by this rule. M323 closes for crypto. M203's bounce variant stays
  untested only in its own fractal form.

## Outputs
- `results/summary.json`
- `results/trades.csv.gz` (every crypto trade)
- `results/secondary_trades.csv`
- `run.log`
- FINDINGS.md with 1x/2x/3x costs, read against `registry.program_trials()`

## Power
- **Fade books** have about 270,000 first touches in the top 50 over 2021-26 at age 30, less after the one-position
  rule. That is about 2,100 entry days.
- **A day series** of about 1,000 days per window detects a per-trade mean of about 5 bp with a 60 bp daily standard
  deviation at t 2. The edge has to survive 12-16 bp of round-trip cost at 1x, so power is not the limit; cost is.

## Known limits
- **Seen data:** the lanes above read these years with related rules.
- **Fills:** a fade assumes a resting limit fills at the level whenever the wick passes it by 2 bp. A queue position
  at a popular level may not fill, and fills on the touch are adversely selected (arXiv 2502.18625). The fade's
  gross is an upper bound.
- **Costs:** the fade is charged the taker tier, which covers an adverse fill but not a missed one.
- **Prices:** Binance only for crypto; MEXC is not checked here.
- **The secondary set** is short (mostly 2026) and pooled, so its read is a sign check, not a test.

## Inputs (frozen)

```inputs
21e8ee4b665d0177eff6eee53bfbc640e80407d33b90131a102590385477a8c0  data/research/meta.json
1acee88308164de0f3a03d3833ef03cc33b54c177a3f430ac45cf1c579cb5108  data/research/t.npy
9293f5bb4ec67ebb34533843fbc3b547bf67008a5beefd326bcc24362737a330  data/research/close.npy
d856af7a5c8cf00dbd7b3ea6892af3048e6300b153e315cd167292c93ce2a634  data/research/ret.npy
8849793b9060dcdc18d34cd7a6790b93deeb3754edbfaa67c7f23236ccae2e4a  data/research/elig.npy
348e3149db50ab30be02615facd54c28448987352fb98b371bac25aeb5f6f94b  data/research/cmat.npy
2f3a43047a900ca85f63afd136459c825c657a4b67e74b7c10e9cf8ed1cb4c35  data/research/rank.npy
a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe  lab/data.py
ea7f9242d508fcf1b94b6ebaf76d5e052f584f23d312eb907cb829f320c5e922  lab/flowfeat.py
fee9835bcc73e14ec277c93d0edf2a1b3f6f1ad739b15e1895dec28a4a186db6  lab/panel.py
7925aa5c0e308c2e4d5ec2c94012242310313846fcdf5cacac2b5c5b669bf1cb  lab/research.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
77632eb621be13d91c3fbe926a2363dc23bf8760df5f0f4229be07164d555946  scripts/run_msnr.py
```

```trees
8ca98def2a97a0b048e5b91512447579856e65a991af11df6f0f8215f1f874fb  klines_1h
bae44f25d308a80aa2f9c8ca7d6aa701a8e93bd35311ea2b1979b59ec308d1b6  secondary
```
