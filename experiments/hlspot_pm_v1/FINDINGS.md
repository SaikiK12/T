# FINDINGS: hlspot_pm_v1 (R445), gate 0

**CONTINUE to gate 1, by the frozen rule (1x excess not below 0).** Gate 0 can only stop this lane, and it does not.
It decides nothing in favour: the two pairs were chosen after R444 had shown their returns. Gate 1 runs forward from
2026-11-11. `.github/workflows/claude-xperp-reads.yml` writes weekly status reads, then the frozen decisions once
2027-02-08 and 2027-05-09 have passed.

- **Frozen:** PREREG sha256 `6d38bc98…`, after R444's gate 0 and before any statistic of this book.
- **Data:** commit `814573be827553b62b286a73f66c8f649c69606c` of `claude/okx-xperp-data` (R444's).
- **Run:** `python scripts/run_hlspot_pm.py --data <worktree at that commit> --window gate0`. Output is in
  `results/gate0/` (daily.csv, trades.csv, report.json).

## Gate 0: 2025-01-01..2026-11-10, 679 days, HYPE and BTC, seen
| Capital | Cost | Net on capital, %/yr | Excess over 4.0%, points | NW t (lag 10) |
|---|---|---|---|---|
| N × 1.1 (decides) | 1x | +10.06 | +6.06 | 3.67 |
| | 2x | +7.21 | +3.21 | 1.65 |
| | 3x | +4.36 | +0.36 | 0.16 |
| N × 1.5 (reported) | 1x | +7.38 | +3.38 | 2.79 |
| | 2x | +5.29 | +1.29 | 0.90 |
| | 3x | +3.20 | −0.80 | −0.47 |

- **Parts, at 1x on capital N × 1.1:**
  - funding received: +12.69%/yr;
  - price (−Δperp + Δspot): +0.22%/yr;
  - costs: −2.85%/yr. Each entry or exit also reweights the pair already held, so the book trades 10.8 times its
    capital a year.
- **Book:**
  - pairs held: none on 77 days, one on 258 and both on 344 (1.39 on average);
  - 12 entries and 10 exits, 0 forced;
  - mean hold of the closed positions 82 days (median 28);
  - HYPE held 580 days, BTC 364 (the same signal as R444, so the same days).
- **Risk:** worst day −0.34% of capital (2025-05-09), best +1.29% (2025-01-21); maximum drawdown −0.62%; top-10-day
  share 22%.
- **The level is falling. Read this before the headline:**
  - 2025: +15.15%/yr (1.60 pairs held). 2026: +4.15%/yr (1.16 pairs held), an excess of about +0.15 points.
  - By half: +15.75 and +4.39%/yr.
  - By quarter: +29.0, +12.6, +13.1, +6.2 in 2025; +4.1, +2.2, +4.0, +8.9 in 2026 (the last quarter is 41 days).
  - The full-window excess comes from 2025, when HYPE's funding was high. At 2026's level the book earns about the
    hurdle.
- **The hedge holds:** the price part has sd 0.074% a day with lag-1 autocorrelation −0.33. The funding part has
  sd 0.044% a day with lag-1 autocorrelation +0.68, so funding regimes, not price noise, drive the long-run variance.

## Power: can gate 1 decide?
- **Frozen statistic** (daily sd of the excess): 0.097% a day. The detectable excess (t 2.5, 80% power) is +12.5
  points at 90 days and +8.8 at 180.
- **Long-run sd implied by the NW t:** 0.118% a day, which gives +15.2 and +10.7 points.
- **At gate 0's full level** (excess +6), the standard error of the excess is about 4.5 points at 90 days and 3.2 at
  180. EARNED at 90 days (t ≥ 2.0) then has about a one-in-four chance, and so does CONFIRMED at 180 (t ≥ 2.5).
- **At 2026's level** (excess near 0), gate 1 would most likely read CONTINUE at 90 days and NULL at 180.
- So gate 1 can confirm this book only if forward funding returns to about 2025's level. A NULL at 180 days would not
  rule out a smaller true excess.

## Program
- One trial; program total 9,784,988 (`registry.program_trials()`).
- Gate 0 is a seen read: the pair choice used R444's per-pair returns. Its t 3.67 is not evidence on its own.

## Against R444
- R444 (10 slots, 12 pairs, capital N × 1.5): +2.57%/yr, excess −1.43.
- This book, without portfolio margin (N × 1.5): +7.38%/yr, excess +3.38. Full deployment and the two pairs account
  for about +4.8 points; costs rise from 1.07 to about 2.1%/yr.
- With the spot backing the perp (N × 1.1): +10.06%/yr. The capital change adds about +2.7 points.

## Limits
- **Seen:** gate 0 reads the window whose per-pair returns picked the pairs.
- **Portfolio margin unconfirmed for this account:**
  - Fetched docs (summarized) ask for an account value above $10,000 and list caps.
  - They do not say that the spot backs the perp's margin with no borrow.
  - Liquidation is not modelled, and the 10% buffer is an assumption.
- **Wrong-way risk:** HYPE is the venue's own token, and UBTC is a claim on Unit's bridge. A venue or bridge failure
  hits both legs at once; the window holds none.
- **Concentration:** on 258 days all the capital sat in one pair.
- **Flat costs:** no book was recorded, so impact is a flat 5 bp on the perp and 10 bp on spot.
- **Fills:** at daily last-trade closes. No live fills.
- **Venue status:** Hyperliquid is authorised nowhere; its own terms were not read (403).
- **Forward reads:** a look reads every calendar day to the look date. If the recorder stops, the missing days count
  as cash and pull the excess toward −4 points.
