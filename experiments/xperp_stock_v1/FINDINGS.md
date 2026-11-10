# FINDINGS: xperp_stock_v1 (R442), gate 0 — NULL (stop)

**Verdict: NULL (stop), by the frozen gate-0 rule (1x annualized excess below 0).** Gate 1 is not run as a decision.
The weekly reads workflow still writes status reads, which carry no decision.

- **Frozen:** PREREG sha256 `dd8f5d77…`, before any stock X-Perp number was read.
- **Data:** commit `013dc728946cc5cf7c3177050a01ae7167049826` of `claude/okx-xperp-data`, the same as R441's gate 0.
- **Run:** `python scripts/run_xperp_stock_carry.py --data <worktree at that commit> --window gate0`. Output is in
  `results/gate0/`.

## Gate 0: 2026-08-20..2026-11-10, 83 days, 62 US stocks, unseen data
| Cost | Net on capital, %/yr | Excess over 4.0%, points | NW t (lag 10) |
|---|---|---|---|
| 1x | −0.50 | −4.50 | −4.65 |
| 2x | −4.76 | −8.76 | −7.22 |
| 3x | −9.01 | −13.01 | −8.59 |

- **Parts, at 1x on capital:**
  - funding received: +3.71%/yr;
  - price (−Δmark + Δindex): +0.04%/yr;
  - costs: −4.25%/yr.
- **Book:**
  - 5.4 of 10 slots held on average;
  - 31 entries and 27 exits over 17 names (AAOI 4 entries; MSTR, CRCL, GOOGL 3 each);
  - mean hold 13.4 days;
  - 0 forced exits;
  - maximum drawdown −0.25% of capital.
- **Halves:** −1.42 and +0.39%/yr net at 1x.
- **Read:** stock X-Perp funding does cross 10%/yr, but not for long.
  - Names fall back under 5%/yr after about two weeks.
  - A round trip costs 50 bp across both legs at 1x, so the book pays about as much in costs as it collects.
  - Half the capital sits idle against the hurdle.
  - The hedge itself works: the price part is flat (+0.04%/yr) and its noise is small (sd 0.037% a day).
  - What fails is the economics: too little funding for too short a time at this cost.
- **Power:** the detectable excess is +6.0 points at 90 days and +4.3 at 180, on the daily sd of 0.047%. The −4.5
  point result is well outside noise (t −4.65); this is a firm null for this rule at these costs, not a power failure.

## What this does not say
- It does not test a cheaper route: maker orders on the X-Perp, a 0-commission broker, or holding through low
  funding. Any of these would be a new lane, read against this one.
- It does not test the opposite side (long X-Perp, short stock) when funding is negative. That needs a stock
  borrow fee, which is not modelled.
- Survivor universe; names listed from June to November 2026, so early days held few candidates.

## Program
- One trial; program total 9,784,985 with R441.

## Limits
- The hedge price is OKX's index, not a broker fill. At 00:00 UTC US stocks trade only in extended or overnight
  sessions.
- Dividends and withholding tax are not booked; neither are EUR/USD on the capital, or transfers and custody.
- Gate 0 charged 5 bp impact per leg; no books were held for the window.
