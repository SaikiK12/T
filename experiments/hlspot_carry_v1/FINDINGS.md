# FINDINGS: hlspot_carry_v1 (R444), gate 0

**NULL (stop) at gate 0, by the frozen rule (1x excess below 0).** The book is steady and positive, but it earns
less than the 4% hurdle on its capital. Gate 1 is not run. Weekly status reads continue in
`.github/workflows/claude-xperp-reads.yml`; they carry no decision.

- **Frozen:** PREREG sha256 `6f4f58ef…`, before any spot price, spot volume or spot-against-perp statistic.
- **Data:** commit `814573be827553b62b286a73f66c8f649c69606c` of `claude/okx-xperp-data`, the first recorder run
  with `hl_spot/` (2026-11-10 19:35 UTC, 0 failures, 12 pairs: HYPE, UBTC, UETH, USOL, UPUMP, UENA, UXPL, UWLD,
  UMON, UMEGA, UZEC, UAVAX).
- **Run:** `python scripts/run_hlspot_carry.py --data <worktree at that commit> --window gate0`. Output is in
  `results/gate0/` (daily.csv, trades.csv, report.json).

## Gate 0: 2025-01-01..2026-11-10, 679 days, today's pairs
| Cost | Net on capital, %/yr | Excess over 4.0%, points | NW t (lag 10) |
|---|---|---|---|
| 1x | +2.57 | −1.43 | −3.66 |
| 2x | +1.49 | −2.51 | −5.91 |
| 3x | +0.42 | −3.58 | −7.45 |

- **Parts, at 1x on capital:**
  - funding received: +3.22%/yr;
  - price (−Δperp + Δspot): +0.42%/yr;
  - costs: −1.07%/yr.
- **Book:**
  - on average 3.8 of 10 slots held (3.0 in 2025, 4.7 in 2026);
  - 60 entries, 53 exits, 0 forced;
  - mean hold of the closed positions 39 days (median 22).
- **Risk:** worst day −0.42% of capital, on 2026-08-24; maximum drawdown −0.42%.
- **Steadiness:**
  - by year: 2025 +2.64%/yr and 2026 +2.48%/yr;
  - by half: +2.74 and +2.39%/yr;
  - top-10-day share 41%.
  - The hedge holds: the price part has sd 0.043% a day with lag-1 autocorrelation −0.52, so it mean-reverts.
- **Why it fails: idle capital.**
  - The book is short of pairs paying at least 10%/yr. About six slots in ten sit in cash, which earns nothing.
  - Per slot actually held, the book earns about +6.7%/yr on that slot's capital (spot fully paid plus perp margin).
  - That is +2.7 points over the hurdle. It is still under the +3.0-point bar gate 1 would ask for, even fully
    deployed.

### Each pair (reported, not deciding; contribution to the book's net, %/yr of book capital)
| Perp | Spot | Entries | Days held | Funding | Price | Costs | Net |
|---|---|---|---|---|---|---|---|
| HYPE | @107 | 6 | 580 | +1.01 | +0.02 | −0.10 | +0.93 |
| PUMP | @188 | 6 | 392 | +0.51 | +0.02 | −0.10 | +0.43 |
| BTC | @142 | 6 | 364 | +0.38 | +0.01 | −0.10 | +0.28 |
| XPL | @210 | 7 | 314 | +0.35 | +0.01 | −0.12 | +0.24 |
| ENA | @206 | 4 | 125 | +0.14 | +0.12 | −0.07 | +0.20 |
| ZEC | @272 | 3 | 172 | +0.21 | −0.00 | −0.05 | +0.16 |
| ETH | @151 | 11 | 288 | +0.29 | +0.03 | −0.20 | +0.12 |
| AVAX | @306 | 1 | 15 | +0.01 | +0.13 | −0.02 | +0.12 |
| SOL | @156 | 8 | 197 | +0.18 | +0.04 | −0.15 | +0.07 |
| MON | @243 | 8 | 135 | +0.13 | +0.05 | −0.15 | +0.03 |

- Every pair held is positive after costs. WLD and MEGA were never entered. The sum matches the book (+2.57%/yr).

### Portfolio margin (reported, never used by a decision)
- Hyperliquid's docs let a spot balance collateralize the short perp (BTC LTV 0.5, HYPE 0.65). Eligibility and caps
  were not confirmed.
- If capital were N × 1/2 instead of N × 3/2, the same book would read +7.70%/yr at 1x, an excess of +3.70 points.
- This changes the capital, not the trades. Liquidation risk on the perp is not modelled.

## Power
- **Frozen statistic** (daily sd of the excess): 0.045% a day, so the detectable excess (t 2.5, 80% power) is +5.7
  points at 90 days and +4.0 at 180.
- **Long-run sd implied by the NW t:** 0.028% a day, which gives +3.6 and +2.5 points.
- With 679 days, gate 0 measures the book's level well. The NULL is a measured shortfall (t −3.7), not a lack of
  power.

## Program
- One trial; program total 9,784,987 (`registry.program_trials()`).

## What a new lane would have to beat
These are not tested here; each would be a new lane, read against this one.
- **A fully deployed variant:** slots sized to the pairs held, or a lower entry band. Measured per held slot, it is
  about +2.7 points over the hurdle before any selection change.
- **Portfolio margin:** this read gives the capital effect, but it needs the venue's eligibility, caps and a
  liquidation model.

## Limits
- **Survivor universe:** today's pairs, by a name rule. Unit coins that were delisted are absent.
- **Seen funding:** Hyperliquid's funding levels were known from earlier lanes, which is why gate 0 could only stop.
- **Flat costs:** no book was recorded, so impact is a flat 5 bp on the perp and 10 bp on spot.
- **Fills:** at daily last-trade closes. No live fills.
- **Bridge risk:** UBTC and the other Unit coins are bridge claims. The window holds no bridge failure, so the hedge's
  worst case is not in the data.
- **Venue status:** Hyperliquid is authorised nowhere; its own terms were not read (403).
