# PREREG: gap_combo3_fast (R527). A combined fast read of the three floorless venues' design-gap lanes: R509, R520 and R524

Freeze with `lab.prereg.freeze()` before R524's first scored day (2026-11-25). Zero common scored days exist at
this freeze. Never edited afterwards.

- **Registry id:** R527
- **Owner (single writer):** none. The read writes nothing.
- **Date registered (UTC):** 2026-11-23

**Methods:** M553, M560 and M552 together (the framework of `docs/reviews/framework_20261123.md`). Carry, candidate C13.
- **Paper only.**

## Why
- **R525:** the design gap is a property of floorless venues. Its effective breadth is the three floorless venues
  (Kraken, Deribit, Bitfinex), whose books are nearly uncorrelated.
- **One forward lane runs on each floorless venue:**
  - R509 (Kraken + Hyperliquid);
  - R520 (Deribit + Hyperliquid);
  - R524 (Bitfinex + Binance, scored from 2026-11-25).
- **R523 combines only the first two.** Adding the third raises power at the first look from 0.74 to 0.86 in sample
  (below).
- **Beat the plan** (`CLAUDE.md` step 2). The planned forward sleeves (each floorless venue against all floor venues)
  would add pairs that share a floorless venue. Those correlate up to 0.94 in R525 and add little evidence. This read
  adds the one independent piece.

## Rule (`scripts/read_combined_gap3_fast.py`)
- **Inputs:**
  - R509 from R510's `series`;
  - R520 from R512's `series` with Deribit's fee (through R520's read);
  - R524 from R512's `series` with Binance's and Bitfinex's fees (through R524's read).
- **Combined day:** the equal-weight mean of the three lanes' fund_book and net_book, on days all three scored.
- **Looks: 20 and 30 common scored days** (about 2026-12-15 and 2026-12-25).
  - **PASS** if NW t (lag 5) of the combined fund_book ≥ 3.0 and the combined cumulative net_book > 0.
  - **FAIL** if the mean combined fund_book ≤ 0, or if any lane's cumulative net_book falls below −3%.
  - Otherwise **NOT YET** at look 1 and **NO EARLY PASS** at look 2. R510, R521, R523 and the lanes' own looks then
    decide.
- **A verdict is final.**

## Calibration (before the freeze)
- **Data:** `calibration.py`. In-sample funding net of 7 bp a leg, on R525's engine, for kraken+hyperliquid,
  deribit+hyperliquid and bitfinex+binance.
- **Window:** 304 common days (2025-12-01..2026-09-30), sliding windows every 3 days.
- **Correlations:** −0.05 to +0.11.

| Read | Power at 20 days | Power at 30 days | Size at 20 / 30 (demeaned) |
|---|---|---|---|
| **Three lanes, equal weight (this rule)** | **0.86** | **0.95** | **0.032 / 0.000** |
| Two lanes (R523's), equal weight | 0.74 | 0.88 | 0.042 / 0.033 |
| Three lanes, inverse-volatility weights (not used) | 0.88 | 0.99 | 0.021 / 0.000 |
| Kraken / Deribit / Bitfinex alone | 0.69 / 0.61 / 0.60 | 0.82 / 0.74 / 0.61 | |

- **Why equal weight:** the inverse-volatility weights (Deribit 0.69) would be estimated on 10 months and give up
  most of Kraken's return, for a small gain in power.

## Supply, break-even and power (`CLAUDE.md` step 4)
- **Supply:** one combined day per calendar day once all three lanes score.
- **Break-even:** fund_book is already net of measured costs. A PASS needs the mean to clear zero by about 3 standard
  errors in 20-30 days.
- **Power:** 0.86 / 0.95 at in-sample levels (above). If forward funding is half the in-sample level, power falls,
  and R509's and R520's own reads remain.

## Pre-mortem: "it failed because…"
1. **Bitfinex's thin books cost more** forward than the 7 bp of the calibration, so the third lane dilutes the
   combined t. R523 runs without it, so the dilution costs one of two related reads, not the evidence.
2. **A lane stops scoring** (a workflow or cache failure), so common days stall. The lanes have separate caches.
   Readiness is checked at each wake.
3. **Kraken's variance dominates** the equal-weight mean. It is in the calibration (power 0.86 includes it).
4. **The funding premium collapses** as BTC falls (about $58k from $80k). The floor part of the gap is by design
   and does not fall, but Kraken's premium-driven spread shrinks. A null then says the forward regime pays less.
5. **R523 and R527 share R509 and R520.** The two reads are correlated. Both lead to the same small stake, so the
   chance of a false stake is at most the sum of their sizes at the first look (about 0.046 + 0.032).

## What a PASS earns
- **A small stake on the three pairs** through `lab.gate.go_real()`, placed by the owner: at most $2,000 in total,
  leverage at most 2.5 under `lab/margin.py` with daily rebalancing.
- **R526's entry filters:** price agreement at entry on book mids, and a two-sided book on both legs.
- It decides nothing about any lane's own verdict.

## What the author has seen
- The in-sample histories above, and R525/R526.
- The count of R524's scored days (0). No forward value of R524 was read; R509's and R520's forward values were not
  read for this round.

## Trials
- **This round:** 1.
- **Program trials:** 9,785,787 before, 9,785,788 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/read_combined_gap3_fast.py` | 7afcdc58e527f29a86b285a2553b32cf90d7d61b02715283c9306e757b83f687 |
| `tests/test_read_combined_gap3_fast.py` | 9099c5378280376909b93c3f98eb079c7f5524a8ca3ea32ee4939d9ac7e6eb63 |
| `experiments/gap_combo3_fast/calibration.py` | be8ce516ec9f208c589a6cba68f0f4d87f5f951fa7d57fa491a2c1096cd9dea5 |
| `scripts/read_xfund_eea_fast.py` | 4a8236d533262f1c0a0a520a666b28d37a9f873b3a76010704ed7ccaf1bfdfc1 |
| `scripts/read_xfund_dhl_fwd.py` | 71b0dd622e1a5ddfc0c5c410358ff8f7786c1900b75dad1b11845e771c429735 |
| `scripts/read_xfund_bfx_fwd.py` | bcecaf8616a91207e94ad932f03f28c3eee4a9d083973454a7ccdc7602e9004b |
| `scripts/read_xfund_eea3_fwd.py` | e20f356fc55980e4ff2a0c7fb02f846b9ce6f7151b2951478dad169e4b38ae3d |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
