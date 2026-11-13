# FINDINGS: adlstress_v1 (R487). A worst-case ADL day costs the carry books 21% to 55% of book capital

**Verdict: PARTIAL** (registry PARTIAL). Under S1, where only Hyperliquid counts as an ADL venue (the only venue
documented to have run ADL on 2025-10-10), five of the six forward books SURVIVE with a bound of 0, by construction:
none of them has a Hyperliquid leg. R278 A (gate+hyperliquid) is EXPOSED: its S1 bound at 2x is 29.35% of book
capital, 32.4 months of its v2 2x net. Under S2 (every venue runs ADL) every one of the nine books is EXPOSED, at 21%
to 55% of book capital, 29 to 132 months of 2x net.

- **Registry:** R487, 6 trials. Program trials become 9,785,297 (`registry.program_trials()`). A bound tests no
  return and selects nothing; the count is bookkeeping.
- **Reproduce:** PREREG sha256 `748a0972...`, frozen in commit `a3159620` before any candle was fetched or read.
  Candles fetched once in commit `12ee748c` (653 bodies, 246 legs, `raw/manifest.json` sha256 `7c550728...`). Then
  `python scripts/run_adlstress.py` (about 4 s): it checks the PREREG, the 13 frozen inputs and every raw body's
  sha256. Results in `results/books.csv`, `results/pairs.csv`, `results/report.json`; one run in `run.log`.
- **This is a bound, not an estimate.** It assumes every eligible pair was hit, the ADL'd leg's gain offsets nothing,
  and the naked leg lost its venue's full high-low range of the day. Per-account ADL incidence is not public keyless.
  No margin cap is modeled because the engine defines no margin.

## ADL venues (fixed before the freeze, `research/intake/adl_venues_20261113.md`, WS0027-WS0032)
| Venue | Class | Evidence |
|---|---|---|
| Hyperliquid | documented | Fill-data studies [arXiv 2603.15963v2](https://arxiv.org/html/2603.15963v2) ($2.047bn within 21:16-21:21 UTC) and [arXiv 2512.01112](https://arxiv.org/html/2512.01112) (at least 40 ADL events in 10 minutes); rule: close at the previous mark ([docs](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/auto-deleveraging)) |
| Binance | not documented (one source) | arXiv 2512.01112 says ADL ran on Binance too, with no public account data; Binance's four statements of 2025-10-11..14 do not mention ADL; Cointelegraph only repeats a rumour. Scenario S1B |
| Gate | not documented | announcement pages 403 here (not bypassed); no source found |
| MEXC | not documented | announcement pages 403; [ADL FAQ](https://www.mexc.com/support/article/faq-on-auto-deleveraging-adl-8127010829081) gives the rule only (fills at the bankruptcy price) |
| KuCoin | not documented | all 55 KuCoin announcements of 2025-10-10..14 read: none on ADL or compensation |

"Not documented" means no source was found, not that the venue ran no ADL. S1's five zero bounds rest on that gap.

## Data
- 174 pairs exposed over 2025-10-10 (`entry_day <= D < exit_day`; engine day d is 00:00 UTC). The plan's inclusive
  rule adds the 3 pairs closed at 00:00 UTC on D; their bounds are in `books.csv` (`incl_*`) and change no call.
- Every leg's daily bars open at 00:00 UTC (binance 64/64, gate 53/53, hyperliquid 40/40, kucoin 31/31, mexc 49/49),
  so the daily candle of D was used everywhere; no day was rebuilt from 1h bars.
- 9 legs have no public candle (8 Gate contracts, 1 MEXC: delisted markets return an empty list). Under S1 one
  stressed pair needed a fill (R278 A IPUSDT: Hyperliquid's candle and notional); under S2 5 (R390 A), 3 (4-venue
  book), 1 (R278 A), 1 (R279 A). No pair needed the book-maximum fill.
- Stressed legs' daily range r: S2 median 0.66 (quartiles 0.54 to 0.78; max 1.77 on a naked short, (H - L) / L).
  Naked notional N (in entry notional): median 0.99, max 5.3.

## Bounds (% of book capital; months of the book's v2 net at the same cost)
| Fwd | Book | Pairs | S1 stressed | S1 1x / 2x / 3x | S1 2x months | S1B 2x | S2 stressed | S2 1x / 2x / 3x | S2 2x months | S2 2x / annual 2x net | Month of net 1x / 2x / 3x | Realized 2x net on D | Call (S1) | S2 call |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R278 A | `gate+hyperliquid L14d th5% K20` | 20 | 17 | 29.29 / 29.35 / 29.41 | 32.43 | 29.35 | 20 | 38.75 / 38.82 / 38.90 | 42.9 | 3.58 | 1.008 / 0.905 / 0.802 | +0.036 | **EXPOSED** | EXPOSED |
| R278 B | `binance+mexc L14d th10% K20` | 14 | 0 | 0 / 0 / 0 | 0 | 10.13 | 14 | 20.92 / 20.97 / 21.02 | 53.8 | 4.48 | 0.504 / 0.390 / 0.275 | +0.079 | SURVIVES | EXPOSED |
| R278 C | `gate+mexc L7d th10% K20` | 20 | 0 | 0 / 0 / 0 | 0 | 0 | 20 | 35.45 / 35.54 / 35.62 | 28.9 | 2.41 | 1.507 / 1.230 / 0.954 | +0.390 | SURVIVES | EXPOSED |
| R390 A | `binance+gate L14d th10% K20` | 20 | 0 | 0 / 0 / 0 | 0 | 18.56 | 20 | 33.76 / 33.85 / 33.93 | 34.9 | 2.91 | 1.118 / 0.969 / 0.819 | +0.474 | SURVIVES | EXPOSED |
| R279 A | `gate+kucoin L14d th5% K20` | 20 | 0 | 0 / 0 / 0 | 0 | 0 | 20 | 54.73 / 54.83 / 54.93 | 48.5 | 4.04 | 1.248 / 1.131 / 1.014 | +0.571 | SURVIVES | EXPOSED |
| R279 B | `binance+kucoin L14d th5% K20` | 20 | 0 | 0 / 0 / 0 | 0 | 21.35 | 20 | 34.31 / 34.40 / 34.48 | 41.9 | 3.49 | 0.940 / 0.820 / 0.700 | +0.383 | SURVIVES | EXPOSED |
| - | `binance+hyperliquid L14d th10% K20` | 20 | 16 | 30.02 / 30.08 / 30.13 | 41.40 | 37.90 | 20 | 37.83 / 37.90 / 37.97 | 52.2 | 4.35 | 0.861 / 0.727 / 0.592 | -0.077 | reported | EXPOSED |
| - | `binance+gate+hyperliquid+mexc L14d th10% K20` | 20 | 1 | 1.20 / 1.20 / 1.20 | 0.94 | 10.96 | 20 | 36.54 / 36.63 / 36.71 | 28.5 | 2.38 | 1.416 / 1.284 / 1.152 | +0.394 | reported | EXPOSED |
| - | `hyperliquid+mexc L3d th5% K20` | 20 | 18 | 31.16 / 31.22 / 31.28 | 118.8 | 31.22 | 20 | 34.65 / 34.72 / 34.79 | 132.1 | 11.01 | 0.676 / 0.263 / -0.151 | -0.086 | reported | EXPOSED |

Cost sensitivity is small: the re-hedge round trip adds 2 x 7 bp per stressed pair per cost step, under 0.1 points
of book capital between 1x and 3x. The comparison side moves more: at 3x one month of net falls (hyperliquid+mexc's
3x net is negative, so its months are undefined at 3x). In months of net at 1x / 3x: R278 A S1 29.1 / 36.7; S2
ranges 23.5 (R278 C) to 43.9 (R279 A) at 1x and 37.3 to 76.4 at 3x for the forward books.

## Reading
- The decisive number is not S1's verdict, which mostly restates the documentation gap, but the size of the range:
  on that day the long-leg altcoins moved 37% to 90% from high to low (16 on Gate, 1 filled from Hyperliquid; R278 A's 17 stressed pairs, median r
  about 0.70). Any leg left naked through that wick, on any venue, costs about a third of a K20 book's capital. That is
  several years of these books' 2x net (2.4 to 4.5 years under S2 for the forward books).
- The realized books lost nothing on D (2x net between -0.09% and +0.57%), because both legs stayed on and the
  archive marks daily last trades. The bound is the gap between that record and a leg-failure path.
- Books with a Hyperliquid leg are the ones exposed under what is documented: R278 A had 17 of 20 exposed pairs with a
  profitable Hyperliquid short on D, binance+hyperliquid 16, hyperliquid+mexc 18.
- Against `registry.program_trials()` (9,785,297) this is a risk bound, not a return claim: it neither confirms nor
  refutes R483's PASS. It says R483's sUSDe comparison (where sUSDe's own 2025-10-10 risk, the Binance USDe print of
  about 0.65, is also unpriced) is between two unpriced tails.

## Post hoc (labelled, no decision)
- Window check for R278 A under S1, from Gate 1h bars (16 of 17 stressed pairs; IPUSDT has no Gate candle): if the
  naked long runs only from the high of the 21:00 UTC hour (Hyperliquid's ADL bursts were 21:16-21:21) to the lowest
  low of 21:00-24:00, the bound is 19.97% of book capital at 2x, against 26.14% for the full-day range on the same 16
  pairs. Most of the day's range sits in the ADL hour, so the full-day bound is not mainly a timing artefact.
- Not modeled and possibly tighter in practice: the ADL'd short's realized gain (closed at Hyperliquid's previous
  mark, near the low), which offsets the naked long's loss up to that moment; liquidation of the naked leg at its
  margin; a faster re-hedge. Possibly looser: exchange outages that delayed re-hedging past the day, a second ADL day,
  ADL on Bybit or OKX (no book uses them).

## Not checked
- Whether Gate, MEXC or KuCoin ran ADL on D (their announcement pages were blocked or silent); Binance has one source.
- Mark-price versus last-trade differences in P_e (the engine values held legs at the mark).
- CoinDesk (429) and The Block (403) articles cited by arXiv 2512.01112 were not read.
- The 2025-10-11 day and any other crash day.
