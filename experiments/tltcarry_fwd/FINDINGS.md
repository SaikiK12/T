# FINDINGS: tltcarry_fwd (R474). Hedged carry on trade.xyz's TLT perp

**Verdict: PENDING.** The futility read is due on 2027-02-13 and the final read on 2027-05-15
(`.github/workflows/claude-tltcarry.yml`). PREREG `b6d045f8`, frozen and pushed (`090f5858`) before this held read.

## Held read (2026-09-24 .. 2026-11-10; reported, decides nothing)
Run 2026-11-12 05:17 UTC after the freeze (`results/held/`; data `docs/provenance/tltcarry_held.json`). The funding in
this span had already been seen in R473, so this read checks the accounting and the noise. It is not evidence.
Yahoo had no DTLA bar for 2026-11-11 at the fetch, so the span ends on 11-10.

| | Value |
|---|---|
| Weeks (ISO) / London closes | 8 / 34, no close without a perp candle |
| Annualized return | +17.9% |
| Annualized excess over the 13-week bill, 1x | **+14.5 points** (NW t 7.69) |
| Excess at 2x / 3x cost | +13.4 / +12.3 points |
| Annualized vol of weekly excess | 1.7% |
| Funding received (on capital) | +2.19% |
| ETF minus perp price (coupons, fees, basis) | +0.76% |
| Costs (entry and exit) | 0.17% |
| Bill over the span | 0.52% |
| Re-splits / minimum margin ratio | 1 (the entry) / 0.317 (start 0.333) |
| Maximum drawdown of equity | 0.22% |
| Funding hours / share where shorts paid / mean rate | 1,129 / 16.7% / 22.7%/yr |

- **The hedge holds.** Daily price PnL (ETF + perp) has an sd of 0.13% of capital; the worst week's was −0.21%. The
  perp ranged from 77.3 to 81.9 (about 6%) over the span.
- **The coupons arrive.** The perp/ETF price ratio fell 1.0% (18.40 to 18.22), close to TLT's two distributions
  ($0.312 and $0.343, about 0.8%) plus the 0.08%/yr fee gap and noise. The ETF/perp price leg returned +0.76% of
  capital (0.75 notional).
- **Weekly excess** ranged from −0.02% to +0.58%. Its sd (about 0.24%) is inside the 0.15-0.3% assumed in the
  PREREG's power section.

## What would change the reading
- Funding is the whole case: 2.19% of the 2.95% gross came from it. At base funding the same span would have earned
  about +4 points over the bill; at zero, about 0.
- Costs here are assumed (5 bp ETF, 2.9 bp perp, 10 bp per transfer). Neither book's cost was measured.
- Venue, transfer, currency and tax risks are not in the paper book (PREREG, Risks).
