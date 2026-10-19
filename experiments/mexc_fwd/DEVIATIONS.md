# Deviations and fixes: mexc_fwd (R215), and mexc_fwd_sq (R218), which loads through the same code

R215 reads R200's signals, so R200's `DEVIATIONS.md` applies here too.

## 2026-10-19, fixed at about 15:35 UTC
1. **XAUUSDT was traded as crypto.**
   - **Cause:** MEXC lists XAU_USDT as type 1 (crypto), so `lab.mexc.map_symbols` matched Binance's XAUUSDT, a
     TRADIFI_PERPETUAL. The PREREG says TradFi symbols are excluded.
   - **Affected:** the replay tickets 2026-10-01..18, already written and append-only, include XAU. It was in bin 0 in
     98 (top_vs_crowd), 25 (taker[24]) and 51 (taker[4]) of 446 hours.
   - **Fix:** from the 2026-10-19 ticket on, Binance TradFi contracts are excluded before mapping (R216's list plus
     today's exchangeInfo).
2. **A day could close on a forming MEXC bar.**
   - **Cause:** prices were requested through the bar after the last journaled hour, which can still be open. A day
     could then be ticketed on a price 12 minutes into its last bar.
   - **Fix:** only closed bars are fetched.
   - **Tickets affected:** none. Every ticket so far was written long after its day closed.
3. **A failed MEXC fetch** now aborts the run instead of scoring the contract at a zero return.

## Known and not changed
- **One contract snapshot (2026-10-19) maps all replay days.** The PREREG says "that day's snapshot"; only one
  existed.
- **A missing MEXC close zeroes two hourly returns**, not one: the bar into it and the bar out of it.
- **A slice needs a MEXC close at its signal row as well as its entry row.** The PREREG names the entry row only.

## Codex follow-up (proposed in PR #5)
- Coverage diagnostics count both requested and available signals on their delayed **entry** day. This fixes the
  midnight denominator mismatch; it does not change any portfolio target or return. The scorer reads both indicator
  dictionaries from its state, with loader-to-temporary-journal regression coverage.
- The loader rejects ambiguous source mappings before fetching prices. Two Binance aliases cannot silently become two
  independent positions or basket members in one MEXC contract. No collision-dependent historical adjustment is made.
- `lab.slices.run_exact` is available for a new lane with strict missing-price and constituent-cost accounting. R215 and
  R218 continue using their frozen `slices.run` convention. Existing tickets are not rewritten.
