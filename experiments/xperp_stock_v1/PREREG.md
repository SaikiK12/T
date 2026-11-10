# PREREG: xperp_stock_v1 (R442). OKX Europe stock X-Perp carry: short the X-Perp, hold the same US stock at an EU broker

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R442
- **Method:** M501 (stock X-Perp carry on OKX Europe, hedged with the listed stock).
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); FYI on issue #7.
- **Why now:** `docs/reviews/venue_access_fr_20261110.md` found that every confirmed carry book has a leg on a venue that
  does not serve French residents with perps.
  - OKX Europe's X-Perps are sold under a MiFID licence (OKX Europe Markets Ltd, Malta).
  - A US stock is something a French resident can hold at any EU broker.
  - If stock X-Perps pay steady positive funding, short X-Perp and long stock is a carry book whose two legs are both
    reachable from France.
  - OKX's own X-Perps guide says they are available in "all 30 European Economic Area countries", subject to KYC, an
    appropriateness test and "Availability may vary". No register entry for a French passport was reached.
- **Gates:** two reads.
  - **Gate 0 (decides only a stop):** the rule on the held window 2026-08-20..2026-11-10, survivor universe.
  - **Gate 1 (decides):** the same rule on days recorded after this freeze, from 2026-11-11, read at 90 and 180 scored
    days.
- **Paper only.** Nothing here can place an order or move money.

## What the author has seen
- R430 (`experiments/okxcarry_v1/FINDINGS.md`) reported the funding cross-section of the 167 crypto X-Perps only.
- No funding, price, volume, basis or book number of any stock X-Perp has been looked at by the author or reported in
  the repo.
- Seen before this freeze:
  - the instrument fields of the 2026-11-10 listing (instId, uly, ctValCcy, ruleType, lever, listTime);
  - a count of the recorder's day files, and which stock X-Perps and indices have candle rows on which weekdays
    (row counts only, no values).
- The thresholds below are R441's, set from R275's family (enter at 10%/yr) and round numbers.
- So gate 0 is unseen data, but it is short and survivor-only, and it decides only a stop.

## Universe
- **Listing:** stock X-Perps (instCategory 3) with ruleType `xperp` in the latest listing held at or before D.
- **Allowlist:** the underlying (ctValCcy) must be one of these 62 US exchange-listed common stocks or ADRs. They were
  picked from the 92 stock X-Perps listed on 2026-11-10 by name only, before any of their data was read:
  `AAOI` `AAPL` `ADBE` `ALAB` `AMAT` `AMD` `AMZN` `APP` `ARM` `ASML` `ASTS` `AVGO` `AXTI` `BE` `BMNR` `COHR` `COIN`
  `CRCL` `CRDO` `CRWV` `DDOG` `DELL` `FLNC` `GEV` `GLW` `GOOGL` `GPRO` `HOOD` `IBM` `INTC` `IONQ` `IREN` `KO` `LITE`
  `LLY` `LUNR` `MARA` `META` `MRNA` `MRVL` `MSFT` `MSTR` `MU` `NBIS` `NFLX` `NOW` `NVDA` `OKTA` `ON` `ONDS` `ORCL`
  `PANW` `PENG` `PLTR` `QCOM` `RKLB` `SMCI` `SNDK` `TSLA` `TSM` `USAR` `WDC`.
- **Excluded (30), because the hedge leg is not a single US stock a French retail client can buy:**
  - pre-IPO (ruleType `pre_market`): ANTHROPIC, OPENAI, OURA;
  - US ETFs and indices (no PRIIPs KID, so not sold to EU retail): QQQ, SPY, EWY, EWZ, US100, US500;
  - leveraged or inverse products: SOXL, SOXS, TQQQ, KORU, MUU, SKDD, SNXX;
  - not US-listed: SAMSUNG, SKHYNIX, SOFTBANK, XIAOMI, MINIMAX, ZHIPU, UNITREE, CXMT;
  - not identified with confidence: DRAM, BSP, CBRS, SKHY, SPCX, PURR.
- Names listed after 2026-11-10 are not added. The forward universe is the allowlist only.

## Data
- **Source:** `scripts/record_okx_xperp.py`, written by `.github/workflows/claude-okx-recorder.yml` (twice a day) to
  the data branch `claude/okx-xperp-data`.
  - Funding prints by instrument (realizedRate; fundingRate where realizedRate is blank).
  - Closed 1Dutc candles: X-Perp mark, X-Perp last trades (quote volume) and the X-Perp's underlying index (`uly`).
  - Book snapshots of each stock X-Perp: $1k market-order cost in bp from mid, by side, from the evening of
    2026-11-10.
  - Daily listings.
- **Gate-0 data commit:** `013dc728946cc5cf7c3177050a01ae7167049826` (the data branch after its first recorder run,
  2026-11-10 17:58 UTC; the same commit as R441's gate 0). Gate 0 reads it and nothing else. The script refuses another
  commit.
- **Gate-1 data:** the same branch at the look date. Rows for days before 2026-11-11 are not scored.

## Rule (constants in `scripts/run_xperp_stock_carry.py`; the book arithmetic is R441's `scripts/run_xperp_carry.py`)
- **Daily axis:** 00:00 UTC. A 1Dutc candle opened on day D − 1 gives the close at D.
- **Prices at D:** the X-Perp mark and the hedge are each the latest close at or before D within 4 days. Markets close
  on weekends and holidays, so a missing day keeps the last price. A price older than 4 days is missing.
- **Hedge price:** the X-Perp's own underlying index (`uly`), standing in for the stock bought at the broker.
- **Action days:** entries and ordinary exits happen only at 00:00 UTC Tuesday to Saturday, the evening after a US
  weekday session. At that hour US stocks trade only in extended or overnight sessions (see Limits).
- **Signal at D:** realized funding over prints with fundingTime in (D − 7 days, D], summed and annualized (× 365 / 7).
  It needs a print at least 7 days before D.
- **Exits at D, first:**
  - Forced, on any day: the name is missing from the listing, or a mark or hedge price is missing for the interval
    just booked.
  - Ordinary, on action days only: its signal is below 5%/yr, or it has no signal.
- **Entries at D, on action days only:**
  - Names not held with signal at least 10%/yr.
  - They also need a mark close at D, a hedge price at D, and X-Perp quote volume of at least $100k on the day closing
    at D.
  - Names are taken by signal, highest first, into free slots. There are 10 slots and no rank exit.
- **Position:** each slot shorts N/10 of the X-Perp and buys N/10 of the stock. Capital is N × (1 + 1/2): the stock is
  fully paid and the X-Perp is margined at 2x. Free slots hold cash, which earns nothing in the book. Notional is held
  constant; rebalancing is not costed.
- **Daily P&L, interval D − 1 → D, booked on day D:**
  - funding: prints in (D − 1, D], received by the short;
  - price: −(mark D / mark D − 1 − 1) + (hedge D / hedge D − 1 − 1).
- **Costs per entry and exit, both legs, at 1x:**
  - fees: 5 bp on the X-Perp and 10 bp on the stock per side (OKX EEA regular taker; broker commission and currency
    conversion);
  - impact: on the X-Perp, the measured $1k cost of the action's side from the latest book snapshot in the 24 h before
    D, floored at 0. When none is held, and always on the stock, 5 bp per leg.
  - Gate 0 has no snapshots, so it uses 5 bp.
  - The 2x and 3x reads multiply the total.
- **Hurdle:** 4.0%/yr on capital, flat.
- **Statistic:** daily net on capital minus hurdle / 365. Its annualized mean and its Newey-West t at lag 10
  (`lab.stats.newey_west_t`).

## Decision
1. **Gate 0:** **NULL (stop)** when the 1x annualized excess is below 0. Otherwise the lane continues to gate 1. Gate 0
   cannot pass the lane.
2. **Gate 1, at 90 scored days (2027-02-08):**
   - **EARNED** when all of these hold: the 1x annualized excess is at least +3.0 points, NW t is at least 2.0, the 2x
     excess is above 0, and the 1x cumulative drawdown is above −5% of capital. The lane continues to 180 days.
   - **NULL (stop)** when the 1x excess is below 0.
   - Otherwise **CONTINUE**.
3. **Gate 1, at 180 scored days (2027-05-09):**
   - **CONFIRMED** when the same conditions hold with NW t at least 2.5.
   - Otherwise **NULL**.
4. A CONFIRMED result is paper evidence only. It admits nothing to real money (`lab.gate.go_real()` and the owner's
   own check of OKX Europe's terms for France decide).

## Power, reported before any read
- Not computed before the freeze, because that would read the data. Gate 0 reports the daily standard deviation of
  the excess and the detectable annual excess (t 2.5, 80% power) at 90 and 180 days. FINDINGS states whether gate 1
  can decide at all at the excess gate 0 shows.

## Reported, not deciding
- Gate 0's full read (1x/2x/3x, NW t, drawdown, top-10-day share, funding and price parts, average names held, forced
  exits).
- Gate 1 status reads before a look (`--status`). They carry no decision.
- 2x and 3x costs at each look.

## Trials and reading
- One trial: one rule, one universe, no variants. The program total before R441 and this lane is 9,784,983.
- Read against `registry.program_trials()`.

## Limits
- **Hedge price:** the hedge is OKX's index, not the broker's fill. At 00:00 UTC the stock trades only in extended
  sessions. A broker fill can differ from the index, most of all on entries and exits.
- **Funding and dividends:** whether the X-Perp's funding-like payment carries dividends is the venue's call. Dividends
  on the stock and US withholding tax are not booked.
- **Currency:** both legs are in USD. The owner's capital in EUR carries EUR/USD, which the book does not hedge.
- **Capital split:** the X-Perp margin sits at OKX and the stock at a broker. Transfers and custody are not costed.
- **Gate 0:** survivor universe; most names were listed from June to October 2026, so early days hold few names.
- **Short history:** the API keeps about three months, so the recorder is the only way to lengthen it.

```inputs
e68d449d36d4895ba7091c07da52a08aea19e67458491d9cfb31b3d616112e65 scripts/run_xperp_stock_carry.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184 scripts/run_xperp_carry.py
550c79aa56b1b0aab4b7587f925012b0cecbdacd49c82cadee1a357dc9b3004d tests/test_run_xperp_stock_carry.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
