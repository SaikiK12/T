# FINDINGS: settlelit_1h_v1 (R387). R363's Lighter scalp on Binance's hourly-cycle settlements: NULL (t 1.64)

**Verdict: NULL by the frozen rule (gate 0, 6 trials).** The run was frozen and registered before it, run once
(2026-11-03 09:45 UTC), inputs verified: `experiments/settlelit_1h_v1/run.log`.

## What was tested
- **Events:** 222 Binance settlements whose interval was 1 hour and whose previous settled rate was at least 0.3% in
  size. They come from 9 Lighter-listed coins, 30 coin-days, 2025-10..2026-09. No settlement lane had read these.
- **Trade:** R363's position on Lighter against the side that received the previous lump. Entered at the last trade
  before T, covered at the last trade before T + 1 min.

## Primary (enter before T, exit T + 1 min), bp a hop of notional

| | Value |
|---|---|
| Price | **+54.5** |
| Lighter funding at T | **−42.4** |
| Round-trip band cost | 2.9 |
| Net 1x / 2x / 3x | **+9.2 / +6.4 / +3.5** |
| CR1 t, coin-day clusters (30) | **1.64** / 1.08 / 0.56 |
| CR1 t, by settlement time | 1.65 |
| Hit rate 1x | 56% |
| Median 1x | +8.3 |
| Per calendar day | +6.1 |

| Check | Bar | Result | Pass |
|---|---|---|---|
| 1. CR1 t of the 1x net (coin-day) | ≥ 2.0 | 1.64 | **no** |
| 2. 2x mean net | > 0 | +6.4 | yes |
| 3. 3x mean net | > 0 | +3.5 | yes |
| 4. Each half | > 0 | +10.7 / +4.0 | yes |
| 5. Without the best coin (0G) | > 0 | +3.1 | yes |
| 6. Trimmed mean | > 0 | +11.0 | yes |
| 7. Leave two coins out | > 0 | +0.7 | yes |

**Reported:** with RIVER at the $1k round trip R364 measured on its live book (61 bp), the primary 1x net is **−7.2 bp**
(t −0.85).

## All six trials (1x net, coin-day CR1 t)

| Trial | Hops | Price | Funding | Net 1x / 2x / 3x | t 1x | t by T |
|---|---|---|---|---|---|---|
| **in before T, out T + 1** | 222 | +54.5 | −42.4 | +9.2 / +6.4 / +3.5 | **1.64** | 1.65 |
| in before T, out T + 2 | 222 | +56.0 | −42.4 | +10.7 / +7.8 / +5.0 | 1.42 | 1.35 |
| in before T, out T + 5 | 222 | +57.7 | −42.4 | +12.4 / +9.5 / +6.6 | 1.40 | 1.11 |
| in before T − 5, out T + 1 | 220 | +63.4 | −42.6 | +18.1 / +15.4 / +12.8 | 1.68 | 2.02 |
| in before T − 5, out T + 2 | 220 | +63.0 | −42.6 | +17.7 / +15.1 / +12.4 | 1.34 | 1.64 |
| in before T − 5, out T + 5 | 220 | +64.9 | −42.6 | +19.6 / +16.9 / +14.3 | 1.33 | 1.45 |

None reaches the family's Bonferroni t of 2.39.

## Per coin (primary)

| Coin | Hops | Price | Funding | Round trip | Net 1x |
|---|---|---|---|---|---|
| 0G | 61 | +68.2 | −41.6 | 1.2 | +25.4 |
| RIVER | 65 | +57.4 | −46.7 | 4.9 | +5.8 |
| SKR | 43 | +48.0 | −39.6 | 2.3 | +6.0 |
| AZTEC | 22 | +61.9 | −41.7 | 1.9 | +18.4 |
| ZK | 16 | +27.7 | −40.8 | 2.2 | −15.2 |
| PIPPIN | 7 | +16.4 | −39.1 | 3.1 | −25.8 |
| BIRB, STABLE, PROVE | 8 | | | | −32.6 / +17.8 / −37.8 |

## What it means
- **The move is there; the venue's own settlement takes it.**
  - On hourly-cycle coins the capture crowd's exit after T is as large as on 4 h and 8 h lumps: +54.5 bp here against
    R363's +40.1.
  - But Lighter settles at the same T, and on these coins its own rate sits near its clamp (0.5%/h). The short paid
    −42.4 bp on average, leaving +9.2 bp at band cost, not distinguishable from zero on 30 coin-days.
  - At the measured cost of the busiest coin, the edge is negative.
- **The trigger is almost perfectly persistent.** Binance's rate at T had r_prev's sign on 99.5% of hops, so the event
  is easy to see coming; the problem is the venue, not the forecast.
- **This does not refute R363** on 4 h and 8 h lumps, where Lighter's hourly rate is a small part of the lump.

## Next (not tested, and now not blind)
- A venue that does not settle at T would keep the price part without the funding.
  - Example: a MEXC perp still on a 4 h or 8 h cycle while Binance is hourly.
  - MEXC also charges a taker fee and its own per-pair interval changes (SRC1103-012..016 context).
- These 222 hops' direction and size are now seen, so a MEXC archive check on them would be gate 0 at best. A frozen
  forward lane on live hourly-cycle settlements is the honest test.
- First check, 0 trials: whether MEXC's funding interval on these coins differed from Binance's at these times.

## Not checked
- Lighter's book depth at these minutes (band cost from R353's snapshots).
- Fills at the last-trade price.
- Latency. R363's order is placed before T and needs no speed.
- Whether the owner can trade Lighter.

## Multiplicity
- Trials: 6 (R387).
- Program trials: 9,782,841 before this lane, 9,782,847 after (`registry.program_trials('registry/rounds.csv')`).
- Against the program's ~9.8M trials, a t of 1.64 carries no evidence. A PASS would have needed the forward lane anyway.
- The rounds row stays RUNNING, as for R286 and others; this FINDINGS holds the verdict.

## Follow-up check after the verdict (2026-11-03, read-only, no new statistic on returns)
- The idea in "next" was to trade the same lumps on a venue that does not settle at T. MEXC does settle at T on 205 of
  the 206 hops that have a MEXC funding file (`data/mexc_hist/funding`, `t` and `cycle_h` only). ZK (16 hops) has no
  MEXC file.
- So MEXC was hourly on these coins at these times, and a MEXC version would pay MEXC's own settlement at T, the same
  drag as Lighter's. No MEXC lane is opened (M460 note).
