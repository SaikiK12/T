# tltcarry_fwd (R474)

Forward paper lane for M529: hold the iShares $ Treasury Bond 20+yr UCITS ETF (DTLA, London) and short the same
notional of trade.xyz's TLT perp (xyz:TLT). The bond prices cancel; the book keeps the coupons and the funding that
xyz:TLT longs pay. Decided against the 13-week T-bill.

- `PREREG.md`: frozen rule, reads and power.
- `results/held/`: the read of 2026-09-24 .. 11-11, after the freeze (reported only; the funding was already seen).
- `results/futility/` and `results/final/`: written once by `.github/workflows/claude-tltcarry.yml` on or after
  2027-02-13 and 2027-05-15.
- Code: `scripts/run_tltcarry.py`, `scripts/fetch_tltcarry.py`, `tests/test_tltcarry.py`.

Paper only. No order, no money, no key.
