# PREREG: settle_v1 (R223), funding-settlement capture: hold across one settlement to collect an extreme rate

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R223
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_settle.py`, `lab/research.py`, `lab/events.py` (`clustered_t`)
- **Source:**
  - `docs/MEXC_EDGES.md`, rule 2 (negative-funding long). MEXC's settled rates match Binance's, so the Binance archive
    can test it.
  - A literature subagent (2026-10-19) found no study of price direction around crypto perp settlement times. The
    dividend analogy predicts the price moves against the payment (Lakonishok & Vermaelen 1986, equities).

## What the author had seen
- The atlas (R185) found funding level cells replicate 0%, and clock-only contexts predict nothing.
- atlas_ctx (R192) used "funding_clock" (hour mod 8) as a context for other signals. It never tested a trade across a
  settlement.
- The archive's funding parquet has columns t, interval_h, rate. Settlements fall at 00/08/16 UTC for 8 h contracts.
  Interval counts across the archive: 4 h 907k, 8 h 532k, 1 h 48k, 2 h 1k.
- No settlement-window return has been computed in this lab.

## Events (one per contract and expected settlement)
- **Last settlement.** L is a contract's settlement row (t floored to the hour), with its interval I (`interval_h`) of
  4 or 8 hours. 1 h and 2 h contracts are excluded: a 2-hour window would overlap the previous settlement.
- **Expected next settlement:** row s = L + I.
- **Signal row:** r = s - 2, at the close of r (one hour before s). The event is skipped if any other settlement of
  the contract falls in rows L+1..r: the last rate known at r must be L's.
- **Signal:** the rate settled at L.
  - **LONG_NEG:** rate <= -0.20%: go long.
  - **SHORT_POS:** rate >= +0.20%: go short.
  - One threshold, no sweep. It is the smallest round number at which the funding alone clears the round trip of the
    top two cost tiers at 1x (12 and 16 bp).
- **Trade:** enter at close[r] (time s - 1 h), exit at close[r + 2] (time s + 1 h).
  - Gross = side x (ret[r] + ret[r + 1]). The research returns deduct a long's funding at the settlement inside the
    next bar (`engine.forward_returns`), so this includes whatever actually settled at row s.
  - If the contract settled at a different time than expected, the trade earns no funding and keeps the price move.
- **Costs:** tier cost at entry (rank at r) plus at exit (rank at r + 2), times 1x/2x/3x.
- **Universe:** crypto contracts (R216's TradFi list excluded) with a finite close at r and r + 2.
  - **Primary:** liquidity rank <= 50 at r.
  - Ranks 51-100 are reported, not decided.

## Decision (per variant, primary universe)
Statistic: the per-event net at 1x, with its t clustered by event month (`events.clustered_t`).
1. **Discovery** 2021-01-01..2023-12-31 (by entry time): pass if mean > 0 and t >= 2.
2. **Validation** 2024-01-01..2025-06-30, discovery passers only: pass if mean > 0 and t >= 1.5.
3. **Holdout** 2025-07-01..2026-09-30, validation passers only, one shot (unread for this family): **CONFIRMED** if
   mean > 0 and t >= 2.

## Reported (not decided on), for every window the variant reaches
- Number of events, months and symbols;
- mean funding collected, the price part, and the cost;
- net at 2x/3x;
- hit rate;
- the 5 symbols' share of the net;
- the 4 h and 8 h contracts separately;
- ranks 51-100.
- **Pass-through:** P = -mean(side x price part) / mean(funding collected). P = 1 means the price moves by exactly
  the payment.
- **Excess** over the equal-weight eligible crypto universe across the same two rows.
- **Off-cycle control:** the same events and states, with the 2-row window moved back by I / 2 hours, where it spans
  no settlement. Its mean net is the price part without a payment.

## Multiplicity
Trials = 2. Program trials before: 9,471,745 (after R222).

## Expectations
- Pass-through near 1 for liquid coins: the price falls about by what longs collect (and rises for the short).
- Net about 0 before costs, negative after.
- Events at +/-0.20% cluster in sell-offs (negative) and squeezes (positive), so month clustering will cut the
  effective sample.
- Guess: both NULL at discovery. Gross close to zero.
