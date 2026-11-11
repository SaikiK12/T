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

## 2026-11-11, writer change: GitHub Actions
- The local loop ticked this lane until 2026-11-06 13:00 UTC (last journaled hour), when the container stopped. From
  2026-11-11 the only writer is `.github/workflows/claude-flow-paper.yml` (every 2 hours at :41 UTC). It runs the
  frozen scripts unchanged, in the task order of `lab/operations.py`: R200, R214, R215, R218, R221, R225, then R220.
- The hours and days from 2026-11-06 14:00 UTC were computed late, on the first run, from the same public endpoints:
  Binance 5-minute ratio history (kept 30 days), klines and funding, and MEXC klines and funding. Every row still uses
  only data stamped at or before its hour. The frozen code labels these days on-time (`ms >= ON_TIME`). They are
  flagged here as written after the fact.
- The caches `data/live` and `data/mexc` (gitignored) live in the Actions cache. The first run refetches them from the
  public APIs. MEXC contracts are mapped with that day's snapshot, as before.

## 2026-11-11, MEXC requests paced on GitHub's runners (no ticket affected)
- Run 42980224484: MEXC refused R215's funding request for RLC_USDT with code 510 ("Endpoint rate limit exceeded ...
  scope: IP"). The script aborts on any failed fetch, so it wrote nothing that hour, and R218, R221 and R225, which
  read its files, were skipped. R220 met the same refusal earlier (`experiments/carry_fwd/DEVIATIONS.md`).
- The workflow now runs the script through `scripts/run_paced_mexc.py`: MEXC requests at most every 0.25 s, each 510
  retried after 5, 15 and 45 s, and up to 3 attempts 180 s apart. `scripts/forward_mexc.py` and `lab/mexc.py` are
  unchanged; a fetch that succeeds returns the same data, so the rule and every value are unchanged.
