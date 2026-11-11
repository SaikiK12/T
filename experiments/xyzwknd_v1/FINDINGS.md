# FINDINGS: xyzwknd_v1 (R462), trade.xyz US-stock perps over the weekend

**Verdict: PASS (gate 0, exploratory). It earns a forward paper lane, not a trade.**
- **D2 passes.** Fade the weekend move (Friday 20:00 to Sunday 19:00 New York) from Sunday 19:00 to Sunday 22:00,
  about two hours after Blue Ocean's overnight prices return.
  - Sample A: +42.4 bp per market-weekend before trading costs; Holm p 0.004 over the two decision cells; 66% of
    trades win; net +28.8 bp at 2x cost.
  - Sample B: +36.2 bp, the same sign.
- **D1 is NULL.** The same fade held to Monday 10:00 earns about the same mean (+42 bp), but the Monday session nearly
  triples the noise (sd 381 bp). Holm p 0.27.
- **Read against the program's 9,785,101 trials, this is not a discovery.** It is a strong gate-0 screen, and the
  PREREG gives it a forward lane on fresh weekends at measured book costs. The cost and fill caveats below decide
  whether it survives.

Run: `python scripts/run_xyzwknd.py`, 2026-11-11, after the freeze (PREREG sha256 `45efb6ff`, commit `449f959a`).
- The PREREG verified and its 7 inputs matched.
- 152 bar and funding files matched `data/xyz_wknd/manifest.json` (`results/run.log`).
- The bars were fetched after the freeze by the frozen `scripts/fetch_xyz_wknd.py bars`. Provenance is in
  `docs/provenance/xyz_wknd.json`: 76 markets, hourly candles from 2026-04-17 (the API's 5,000-candle limit) or the
  market's listing, to 2026-11-09 23:00 UTC.
- **Events:** A 928 market-weekends (72 markets), B 447 (76 markets).
- **Skipped:** 439 market-weekends where the market was listed less than 7 days before Friday, 5 Pre-IPO weekends,
  and 5 unpriced.

## Decision cells
`all` markets, |W| ≥ 50 bp, bp per market-weekend, fade side. g = price + funding, before trading costs.

| cell | n A | weekends A | mean A | sd A | hit A | p A | Holm p | MDE80 A | unit A | net 1x / 2x / 3x (A) | n B | weekends B | mean B | p B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D2 Sun 22:00 | 556 | 18 | **+42.4** | 140 | 66% | 0.002 | **0.004** | 17 | 6.8 | +35.6 / **+28.8** / +22.1 | 260 | 6 | +36.2 | 0.59 |
| D1 Mon 10:00 | 556 | 18 | +42.1 | 381 | 55% | 0.27 | 0.27 | 45 | 6.8 | +35.3 / +28.6 / +21.8 | 260 | 6 | +189.5 | 0.16 |

- **D2 meets every PASS condition:**
  - 556 ≥ 100 events over 18 ≥ 10 weekends;
  - Holm p ≤ 0.05;
  - |mean| above 2 units;
  - B: 260 ≥ 30 events over 6 ≥ 4 weekends, the same sign, and |mean| above 1 unit.
- **B is weak on its own.** Its p is 0.59 because 6 weekend clusters cannot reach significance, and only 3 of its 6
  weekends are positive (-5, +31, -62, +64, -69, +219 bp).
- **Where the return comes from (A):** price +41.2 bp, funding +1.1 bp.

## Diagnostics (not decided on; 30 more cells, `results/cells.csv`)
- **Dose-response with the threshold** (`all`, Sunday 22:00, A). Every one has p ≤ 0.002:

  | θ | mean | n | hit |
  |---|---|---|---|
  | 0 | +30.8 | 928 | 62% |
  | 50 | +42.4 | 556 | 66% |
  | 100 | +51.7 | 346 | 66% |
  | 200 | +73.4 | 152 | 71% |

- **Market-neutral version (`rel`).** Fade each market's weekend move net of that weekend's median: +55.8 bp at
  θ = 50 (hit 74%, p < 0.001); B +36.9 bp (p 0.06). It is charged two units (13.8 bp), and its 2x net is +28.1 bp.
  The overshoot is not only market-wide.
- **Companies and funds:**
  - companies +42.1 bp (n 476, p 0.001);
  - funds +44.2 bp (n 80, p 0.09);
  - B: +41.4 and +10.5.
- **Monday 10:00 exits** carry the same mean in A, with sd 330-440 bp, and are much larger in B (+123 to +400 bp,
  p 0.03-0.16). They are noisy and are not decided on.

**Post-hoc checks.** These were run after the result, are not registered, and only probe artifacts.
- **Bid-ask bounce at the entry trade.** If the edge were the last trade before 19:00 bouncing off the bid or ask,
  measuring W one hour earlier (to 18:00) and still entering at 19:00 would kill it. It does not: +53.9 bp (n 571,
  hit 68%). The median entry-hour candle has 230 trades.
- **Liquidity.** Entry candles with more trades than the median give +44.9 bp (n 294); fewer, +37.1 bp (n 262).
- **Large liquid names** (TSLA, NVDA, AAPL, MSFT, META, AMZN, GOOGL, AMD, PLTR, COIN, HOOD, MSTR): +23.2 bp (n 120,
  hit 65%). Smaller than the average but above 2 units.
- **By weekend:** A has 13 of 18 weekends positive. The negatives are 05-01, 06-12, 07-10, 07-31 and 09-18.
- **By market:** the largest positive sums are INTC, DRAM, GME, CRWV, RKLB, SKHY, SNDK and NBIS. The largest negative
  are SOXL, BABA, ARM, AMAT, MU and ASML. Volatile retail names carry more of it.

## Costs (1x, 2x, 3x)
- **The unit is a round trip:** growth-mode taker fees (2 × 0.9 bp) plus 4 bp of assumed slippage = 5.8 bp. MSTR,
  PURRDAT, STRC and BMNR are not in growth mode and are charged 22 bp. The mean unit in D2 is 6.8 bp.
- **D2:** +35.6 / +28.8 / +22.1 bp at 1x / 2x / 3x. **D1:** +35.3 / +28.6 / +21.8.
- **Break-even cost:** about 42 bp per round trip, against 5.8 bp assumed. The edge survives a 7x worse fill than
  assumed.

## What is not established (fidelity)
- **Prices are last trades** (hourly candle closes), not the bid and ask a $1k order would meet on Sunday at 19:00 and
  22:00. The bounce check above argues against a pure spread artifact. Measured weekend books on xyz exist only from
  2026-11-11 (`record_xyz_books.py`, hourly). The forward lane uses them.
- **Fee history.** Growth mode is as of 2026-11-11. Weekends where a market paid the 9 bp standard fee would cost
  more, though still under break-even.
- **Execution timing.** Entry needs an order at Sunday 19:00 New York and an exit at 22:00 (00:00 and 03:00 UTC in
  winter). Both are automatable; nothing here was executed.
- **Capacity:** not measured. Weekend depth on thin names may cap size well below $10k per market.
- **Survivorship:** delisted markets are absent.
- **Short history:** 24 weekends in all (April to November 2026), all under the 30-minute oracle constant. A rule
  change by trade.xyz (oracle constant, session hours, bounds) could end the effect.

## What it means
- On trade.xyz, the perp-only weekend move of US stocks overshoots. About a quarter to a third of a move of 50 bp or
  more is given back within two hours of external prices returning on Sunday evening.
- This fits the mechanics: a thin weekend book drives a 30-minute EMA oracle with no external anchor. It also fits
  the venue-commissioned study's slope of 0.83 [V], and R432's fade slopes on Binance's TradFi perps.

## Next (from the PREREG stop rules)
- **Earned:** a forward paper lane under a new id (R463) on fresh weekends from 2026-11-13:
  - the same frozen rule (θ = 50 bp, Sunday 19:00 to 22:00 New York, all 76 markets);
  - fills priced at the recorded xyz book cost of a $1k order nearest each instant;
  - its own PREREG frozen before the first weekend;
  - at least 15 weekends before any verdict.
- **Nothing is retuned.** θ, the instants and the universe stay as frozen here. The `rel` book and the 100/200 bp
  thresholds stay diagnostics.

## Registry
R462, DONE, recorded PARTIAL in the registry (the frozen verdict is PASS at gate 0, recorded as for R349, R354 and
R363), 32 trials. Program trials: 9,785,069 before, 9,785,101 after.
