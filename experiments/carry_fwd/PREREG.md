# PREREG: carry_fwd (R220), the confirmed funding carry, forward on paper on Binance and on MEXC

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R220
- **Owner (single writer):** the session that froze it; it writes only `experiments/carry_fwd/journal/`,
  `data/live/` and `data/mexc/`
- **Code:** `lab/carry.py` (`run`, `trailing_apr`, `spot_pair`), `lab/live.py`, `lab/mexc.py`,
  `scripts/forward_carry.py`
- **Source:** carry_holdout (R191), the only lane CONFIRMED on the holdout: +1.45% over 457 days, NW t 2.07. Its
  FINDINGS names a forward paper monitor as the next step. The edge scoreboard (2026-10-19) lists it as the third
  achievable edge with no forward lane.

## What the author had seen
R190 and R191 in full: carry earned +35% in 2021, about 0 in 2022-23, +8% in 2024 and about 1%/yr since. The mean
trailing funding of the top-50 perps was negative over the holdout. Since 2026-10-01 the author has seen the flow
books' forward tickets, which include funding as a cost of the short slices. The author has computed no trailing
funding APR, basis or carry position on any day after 2026-09-30. The author probed the public endpoints for one
symbol each: Binance premium index klines, Binance and MEXC spot symbol lists, and MEXC index price klines. A research subagent reported on 2026-10-19:
- MEXC's settled funding matched Binance's for BTC, SAND, DOGE and SOL over Sep 17-30, 2026 (correlation 0.9997 or
  more; mean gap under 0.02 bp). Every contract it sampled settles every 8 h.
- Current MEXC funding is far from zero on a few names. SAND, BTW and CT are around -0.2% per 8 h; SAND's last five
  settlements were negative. A few TradFi stock tokens are around +0.77%.
- MEXC's spot taker fee is 5-8 bp.

## Rule (R191's primary, entered one bar late)
- **Signal:** trailing 72 h funding APR = (sum of the funding rates settled in the last 72 hours) x 365 x 24 / 72,
  per contract, on its own venue's settlements.
- **Entry and exit:** short perp plus long spot when the APR is above 20%; exit when it is below 10%, or when the
  symbol stops being tradable.
- **Size:** 1 / max(number open, 10) per position.
- **One bar late (new here, as R214 and R215):** a decision made on the bar closing at row t's close is executed at
  row t + 1's close. Live runs start 12 minutes after a close, so the settlement at that close would be missed.
  R191's same-close timing is reported as `r191_timing`.
- **Tradable at row t:**
  - the symbol is in R200's eligible set at t (live top-50 by trailing quote volume, finite close);
  - a USDT spot pair is open for trading on the same venue;
  - the venue's basis is finite.
  - On MEXC, the symbol must also map to a MEXC crypto contract, as R215 (`lab.mexc.map_symbols`), and have a MEXC
    close.
- **Spot pair:** the first of these that the venue lists today (`lab.carry.spot_pair`): the base, the base without a
  1000/1000000 prefix, and on MEXC also the MEXC contract's base. Today's spot snapshot is used for the replay days.
- **Accrual per hour:**
  - **Funding:** shorts receive the rate settled in the next hour.
  - **Basis:** the position loses the next hour's change in basis.
    - Binance: basis = premium index close (as the archive).
    - MEXC: basis = MEXC last close / MEXC index price close - 1.
  - **Costs:** perp tier cost by Binance liquidity rank (`lab.engine.cost_matrix`, as R200) plus 10 bp for the spot
    leg, on every change of weight. The rank is carried forward from the last eligible hour, so an exit pays the tier
    the symbol last had.
- **Books (the trials):**
  - **BIN:** Binance funding, premium index and spot.
  - **MEXC:** MEXC funding, index and spot. This is the owner's venue.
- **Days:**
  - **Replay:** 2026-10-01..19 (UTC), with the signal warmed up on the 72 hours before 2026-10-01.
  - **On-time:** from 2026-10-20.
  - Only hours whose next close and next settlement are known are scored. A day is ticketed once all of its 24 hours
    are scored.

## Decision
At 90 on-time days (2027-01-17 at the earliest), each book on its own:
- **PASS** if two conditions hold:
  - the on-time daily 1x net has total > 0 and NW t (lag 10) >= 2 (R191's rule);
  - `lab.gate.go_real()` passes on the on-time days that held a position.
- **INCONCLUSIVE** if fewer than 20 on-time days held a position. Too little carry was on offer to judge; this is not
  a failure of the edge.
- **FAIL** otherwise.

The 30 and 60 on-time day checkpoints are monitoring only.

## Reported, not decided on
- 2x and 3x costs (perp and spot both scaled);
- spot leg at 5 bp;
- `r191_timing`;
- funding, basis and cost parts;
- average positions open and the share of days invested;
- coverage: eligible symbols with a spot pair, and on MEXC, mapped ones;
- the market mean trailing APR over eligible symbols;
- the symbols open now;
- MEXC's listed spot taker fee next to the modeled 10 bp;
- daily correlation of BIN and MEXC.

## Multiplicity
Trials = 2. Program trials before: 9,471,734 (after R219).

## Expectations
- Funding has been low since 2025, so both books will be flat most days. A PASS needs a funding regime like 2021 or
  2024. INCONCLUSIVE is the likeliest outcome at 90 days.
- MEXC's funding tracks Binance's closely (the subagent's check above), so the two books should be close. They
  will differ through spot-pair availability, coverage (mapping), and the basis definition. MEXC's last/index basis
  is noisier than Binance's premium index.
- Carry's daily returns are smooth: holdout Sharpe 2.5, max drawdown 0.07%. Unlike the flow books (at 90 days the
  gate only detects Sharpe above about 5; `docs/PAPER_REFINEMENT.md`), a real carry is detectable in 90 days, provided
  funding is on offer.
