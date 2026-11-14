# PREREG: llpstake_v1 (R447). Lighter's LLP pool with the LIT stake it requires, hedged with a short LIT perp

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R447
- **Method:** M506 (R446's LLP deposit as a depositor must hold it: the required LIT stake, hedged with a short perp).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); FYI on issue #7.
- **Why now:**
  - R446 (`experiments/dexvault_v1`) measured LLP per USDC deposited. In 2026 it earned +10.80%/yr (excess +6.80
    points, NW t 3.27).
  - Lighter's docs, read after R446's gate 0, say LLP is "exclusively accessible to LIT stakers", with "up to 10 USDC"
    per LIT staked. Staking earns "a fixed 6% APR"; unstaking has a 3-day lock-up.
  - So a real deposit holds LIT too. Its capital includes the stake, and the stake carries LIT's price unless it is
    hedged. Lighter lists a LIT perp (market 120) and a LIT/USDC spot pair (market 2049), both at 0 fees.
- **Book:** one, so one trial.
- **Gates:**
  - **Gate 0 (stops only):** the held history 2026-01-15..2026-11-10. It can stop the lane; it cannot pass it.
  - **Gate 1 (decides):** days recorded after this freeze, from 2026-11-11, read at 90 and 180 scored days.
- **Paper only.** Nothing here stakes, deposits, orders or moves money.

## What the author has seen
- All of R446's gate 0, including LLP's 2026 level, its quarters, its daily sd, and its −5.35% day on 2025-10-11.
- Lighter's docs and orderBooks listing, as quoted above. A news report (The Block, 2026-01-14, secondary) says the
  stake became mandatory for new depositors on 2026-01-14, with a grace period for existing ones to 2026-01-28.
- In an API probe, the LIT perp's first daily bars, 2026-01-02..2026-01-06. Opens and closes were about $2.5 to $3.1.
  No later LIT price was printed.
- No LIT funding figure has been read. The recorder's smoke test printed only row counts: 7,485 funding hours and
  312 perp bars.
- Because LLP's return over the window was seen, gate 0 stops only.

## Data
- **Source:** `.github/workflows/claude-okx-recorder.yml` (twice a day) on the data branch `claude/okx-xperp-data`:
  - `vaults/llp/share_prices/` from `scripts/record_dex_vaults.py` (R446's);
  - `lit/perp_funding/`, `lit/perp_candles_1d/` and `lit/spot_candles_1d/` from `scripts/record_lit_hedge.py`.
- **Gate-0 data commit:** `cb048a9130ad656500f4eacbfea5cdc1651ff132`
  - It is the data branch after the first run that recorded `lit/`.
  - Gate 0 reads it and nothing else. The script refuses another commit.
- **Gate-1 data:** the same branch at the look date. Rows for days before 2026-11-11 are not scored.

## Rule
Constants are in `scripts/run_llpstake.py`. LLP's return is R446's; the report and the gate-1 decision are R441's
(`run_xperp_carry.py`).
- **One unit, rebalanced daily:**
  - 1 LIT bought on the spot pair and staked, earning 6%/yr, valued at the spot close;
  - 10 USDC in LLP, the most the stake allows;
  - a short of 1 LIT on the LIT perp, with margin equal to its notional at the previous close.
- **Capital on day D:** 10 + the spot close of D − 1 + the margin (the perp close of D − 1). Every part of D's P&L is
  divided by it.
- **P&L on day D:**
  - LLP: 10 × R446's LLP return booked on D (the share price ratio between the last stamps of consecutive UTC days);
  - staking: the spot close of D − 1 × 6% / 365;
  - funding: the perp close of D − 1 × the sum of D's hourly rates received by the short (positive when longs pay);
  - price: the stake's spot change minus the perp's change, from D − 1's close to D's, so only the basis is left.
- **Liquidation check:** the short is liquidated on D if the perp's high reaches the previous close × 2 / 1.2, which
  is a maintenance margin of 20% at 1x. Its whole margin is then lost, the stake keeps its move, and the hedge is put
  back at D's close.
- **Missing inputs:** a missing LLP stamp books 0 for LLP that day, and the gap's move lands on the next stamp, as in
  R446. A missing bar carries the last close forward. A day missing any input is counted as missing.
- **Costs:** one round trip a year, spread over the days:
  - 40 bp of the stake's value: 10 bp a leg a side on the spot buy and sale and the perp's open and close;
  - 10 bp of the LLP deposit (R446's).
  - The 2x and 3x reads multiply both. Lighter charges 0 fees on these markets, so the costs stand for spread and
    impact.
- **Hurdle:** 4.0%/yr on capital, flat.
- **Statistic:** per day, R441's summary: annualized net and excess at 1x, 2x and 3x, NW t of the daily excess at
  lag 10, and the cumulative drawdown.

## Decision
1. **Gate 0:** **NULL (stop)** if the 1x annualized excess is below 0. Otherwise the lane continues to gate 1. Gate 0
   cannot pass it.
2. **Gate 1, at 90 scored days (2027-02-08):**
   - **EARNED** when all of these hold: 1x annualized excess at least +3.0 points, NW t at least 2.0, 2x excess
     above 0, and 1x cumulative drawdown above −5% of capital. The lane continues to 180 days.
   - **NULL (stop)** when the 1x excess is below 0.
   - Otherwise **CONTINUE**.
3. **Gate 1, at 180 scored days (2027-05-09):**
   - **CONFIRMED** when the same conditions hold with NW t at least 2.5.
   - Otherwise **NULL**.
4. A CONFIRMED lane is paper evidence only. It admits nothing to real money. `lab.gate.go_real()` and the owner's own
   check decide, including the venue's status, LLP's tail and LIT's.

## Reported, not deciding
- The parts of the 1x net (LLP, staking, funding, basis, costs), the average share of capital in LLP, liquidation
  days, missing days, by month, and the detectable excess at 90 and 180 days.
- **The stake held without the short:** capital 10 + the spot close, the same LLP and staking, the stake's full price
  change, and half the stake cost. It shows what LIT's price does to an unhedged depositor and decides nothing.
- Gate 1 status reads before a look (`--status`). They carry no decision.

## Trials and reading
- One trial. The program total before this lane is 9,784,990 (after R446).
- Read against `registry.program_trials()`.

## Limits
- **LLP's tail** (R446): one crash day can take months of return, and it fails gate 1's drawdown condition.
- **LIT's tail:**
  - LIT is Lighter's own token, so a venue failure hits the vault, the stake and the hedge at once.
  - A spike can liquidate the short. The check uses daily highs and an assumed 20% maintenance margin; Lighter's own
    LIT margin tiers were not read.
- **Staking:** the 6% is "currently" fixed, as read on 2026-11-10. The rule assumes it held over the whole window and
  that rewards arrive daily. Its payment schedule was not read.
- **Requirement date:** the start date rests on a secondary source. Before 2026-01-14 the stake was not required.
- **Hedge venue:** the short sits on Lighter itself; a funding regime shift on LIT is the lane's main unknown.
- **Clocks:** LLP's stamps fall near 20:00 UTC; funding and bars run by UTC day.
- **Jurisdiction:** Lighter's terms, as read, do not exclude France. That is not legal advice, and the owner checks.

```inputs
ed21596eee86e099a7c2497ee522e9720783c8e8555a227721a275cdfd24e8a5 scripts/run_llpstake.py
a58005353bf406cb84998f12af83384c5b451f72629f5d89356ab651b0903e0f scripts/run_dexvault.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
c8c2f2688029446df476e97026e8795fe3a7a1e8f35313ae2c5b323fc0096aee tests/test_run_llpstake.py
3ba7069fcd6c96ad6e0b6e1308113804c4142eb4f18ac68cb8ad5f1822fb734e scripts/record_lit_hedge.py
f1d1258247a5c3f88c797d1f5746d63555d6ea39cb373bafe156db7e7a58ecdf scripts/record_dex_vaults.py
127382b43bfd688b3d8fca8961492d998560098387351afdee1cd7ca005567c9 scripts/record_hl_daily.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
