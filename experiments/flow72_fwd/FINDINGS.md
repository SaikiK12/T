# FINDINGS: flow72_fwd (R199)

**Verdict: ABANDONED before any forward statistic: the data gate failed as written.** No forward return, mark or
ticket was computed. Superseded by flow72_fwd2 (R200).

- **Registry row:** R199 (trials: 2 registered, 0 run)
- **Evidence:** `parity.json`, `parity.log` (prereg sha b9b91407)

## What the gate measured (2026-09-24..2026-09-30, 56 eligible coins, archive eligibility)
| spec | live bin = archive bin | within one bin | bin 0: archive / live / both |
|---|---|---|---|
| top_vs_crowd/xs8 | 93.4% | 100% | 1008 / 1008 / 1008 |
| taker[4]/xs8 | 88.0% | 100% | 1008 / 912 / 911 |
| taker[24]/xs8 | 86.8% | 100% | 1008 / 916 / 915 |

Gate: >= 99% for each spec. Failed.

## Why
1. **Coverage, not data.** The archive has no metrics for coins with non-ASCII names (币安人生USDT, 我踏马来了USDT,
   牛来USDT, 龙虾USDT; two of them were eligible in the window, 336 eligible cells). The live endpoints have them, so the
   live cross-section has two more coins and the rank buckets shift. With live values kept only where the archive has
   the raw input, the bins match 99.98%, 99.53% and 99.58%, and bin 0 agrees on 1008, 1007 and 1004 of 1008 cells.
   Historically these coins are 0.16% of eligible cells, all from 2025-10 on.
2. **Clock.** The archive stamps the snapshot rows (top-trader and all-account ratios, OI) 5 minutes before the live
   API does; taker windows carry the same stamp. With that alignment the hourly ratios match the archive to a median
   relative difference of 3e-6 (top traders) and 3e-5 (all accounts); before it, about 6e-4.
3. **Universe.** The live symbol filter kept only `PERPETUAL` contracts; the archive (and the top 50) also hold
   Binance's `TRADIFI_PERPETUAL` contracts (crude oil, Brent, gold, silver, NVDA, MSTR...; CLUSDT ranked 8th). The live
   top 50 overlapped the archive's by 67% because of this. Reported, not gated.

## Next
flow72_fwd2 (R200): the same books and forward period, with the TradFi contracts in the live universe, the clock
alignment fixed, and the gate measured on the cells where both sides have the raw input. The gate's definition was
changed after seeing the diagnosis above; it is a data check (no returns were read), and the threshold is unchanged.
