# Deviations and fixes: flow72_fwd2 (R200), and the lanes that read its signals (R214, R215, R218, R221)

The PREREG is frozen and is not edited. This file records where the code did not do what it says, the fix, and what
stays in the append-only journal. Source: a read-only audit of the forward pipeline (2026-10-19).

## 2026-10-19, fixed at about 15:30 UTC
1. **The newest hour was averaged over 11 of its 12 five-minute rows.**
   - The PREREG reduces the live rows to hours "as `lab/flow.reduce_metrics` (ratios averaged over the hour)". Two
     problems broke that for the newest hour of each tick:
     - The long/short window ended at the hour's end, exclusive, which dropped the row stamped at that end. That row
       belongs to the hour on the archive clock (live stamp - 5 min).
     - The taker row for the last five minutes is published several minutes after the close.
   - **Affected rows** (still in `journal/signals.csv`; the journal is append-only):
     - all coins at 2026-10-19 08:00, 09:00 and 13:00;
     - 94% complete at 2026-10-04 11:00, 10-04 18:00 and 10-10 22:00 (thin names).
   - **Size** (audit simulation over 59 hours):
     - taker[4] bin-0 membership changed in 50 of 2,950 coin-hours, taker[24] in 6, top_vs_crowd in 2;
     - the set of coins opening a book-A slice changed in 18 of 59 hours.
     - The return effect was not simulated.
   - **Fix:**
     - the long/short window now includes the row stamped at the hour's end;
     - an hour is journaled only when 95% of its eligible coins have 12 rows of both ratios, or 3 h after its close,
       whichever comes first.
     - The PREREG's "at least 12 minutes have passed" still holds; hours now wait until complete, about 30 minutes.
2. **A failed fetch no longer becomes a zero.**
   - Before: a klines failure dropped the coin from the tick's universe, which shifted every rank. A funding failure
     scored as zero funding.
   - Now: the tick or the scoring aborts and writes nothing, and the next run computes those hours.
   - No failure appears in `tick.log` before the fix.
3. **Duplicate protection.**
   - Signal rows for an hour already journaled are dropped before appending. A run killed between the two appends
     would otherwise duplicate them on the next run.
   - `scripts/forward_all.sh` holds a lock, so two ticks cannot overlap.
   - Each tick log now records the git commit.
4. **The status shows the PREREG's PASS.**
   - `status.json` showed `go_real` alone. The PREREG's PASS also needs NW t >= 2; this is now `prereg.pass_now`.
   - The stop rule (book A's cumulative net 50% below its running peak) is now `prereg.stop_rule_hit_day`.

## Known and not changed (frozen design; read the decision with these in mind)
- **`late` is set by date.** Hours before 2026-10-19 are `late=1`. The 2026-10-19 hours are `late=0`, although they
  were computed 22-555 minutes after their close.
- **The decision counts replay days.** It is at 90 scored days, and the 18 replay days (10-01..18) count. Their
  totals (A +22.2%, B +9.7%) were printed after the freeze. R214, R215 and R221 decide on on-time days only.
- **Costs are charged per cell.** R200 charges each cell's slices separately. R214 and R215 net the three cells'
  positions first. Over the 18 replay days, A's cost is 1.061% here vs 0.979% in R214.
- **Exits outside the top 50 pay 20 bp.** The true tier for ranks 51-100 is 12 bp (3.2% of exits). This is
  conservative.
- **The data gate tested common coins only.** It tested bins on the coins common to the archive and live data
  (99.5-99.98%). The all-coin bins the books use agree with the archive 93% (top_vs_crowd), 88% (taker[4]) and
  87% (taker[24]). The PREREG reports this; it does not gate on it.
