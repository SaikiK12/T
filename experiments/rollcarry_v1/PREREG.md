# PREREG: rollcarry_v1 (R478). Does funding on trade.xyz's futures-priced perps exceed the futures roll it pays for?

- **Registry id:** R478
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M532. This file is frozen by `lab.prereg.freeze()` before the data are fetched. After the freeze it is never
edited.

## Question
- trade.xyz prices NATGAS, CL (WTI) and BRENTOIL from futures. On business days 5-9 of each month the oracle moves
  from the front contract to the next in 20% steps (17:30-18:00 ET, documented roll schedule).
  - In contango that adds the calendar spread to the perp's price, so longs gain it.
  - Longs pay for it in funding (`F = 0.5 [P + clamp(r − P, ±0.0005)]` per 8 h, P the premium of the mark over the
    oracle).
- Short the perp and hold a fund that owns the same front futures (UNG for NATGAS). The fund earns the futures' excess
  return plus T-bill income, with no roll jump.
- The pair therefore earns funding minus the roll-up, minus costs and mark noise.
- **Decision:** in sample A (weeks ending by 2026-07-22), does NATGAS-UNG earn at least 2 points a year over the
  13-week bill, with Newey-West t ≥ 2.0 and a positive excess at 2x cost?
- **What arbitrage predicts:** funding ≈ roll-up, so excess ≈ −(costs + the fund's fee), a NULL. A PASS would mean
  NATGAS longs overpay for the roll.

## Why run it
- xyz:NATGAS funding was very large in B (below). M532 asks whether that is a premium or the price of the curve.
- No lane has compared xyz's commodity funding with the roll it pays for. R464 used these perps for a weekend fade,
  and R477 left them out for this reason.
- The pair is hedged in price. If longs overpay, the edge is mechanical, like R474's coupon.

## What the author has seen
- **B-period funding, from R475's scans (2026-11-12):** an 8-week scan of every HIP-3 market and four 4-week blocks
  of xyz markets from 2026-07-23.
  - xyz:NATGAS's 4-week means were 28.7, 59.8, 123 and 141%/yr (M532's queue note).
  - CL and BRENTOIL were in the same scans; their levels were not written down here and are treated as seen.
  - B is therefore reported only.
- **R464** (weekend fade) put NATGAS, CL and BRENTOIL funding into weekend returns from 2026-05-01 (mean +0.5 bp per
  weekend across markets). No level was ranked or read per market.
- **Spans only:**
  - `data/xyz_ns` (R464's fetch) holds xyz:NATGAS funding from 2026-04-01 and hourly candles from 2026-04-17. No
    value was read.
  - R475's universe file lists xyz:CL's first funding print as 2026-01-06; xyz:NATGAS's listing date is not known at
    the freeze.
- **Probes (dates and row counts only, no prices):**
  - Yahoo serves live futures contracts (NGZ26.NYM from 2025-06-02) but no expired ones (NGV26, NGQ26, NGF26,
    CLX26, CLQ26 return nothing), so the roll cannot be priced from contracts.
  - EIA's NYMEX contract 1-4 series end in April 2024 (EIA page structure read on 1994 rows).
  - No UNG, USO or BNO price was read.
- **Web (2026-11-12):**
  - trade.xyz docs (llms-full.txt): roll schedule and weights, designated contracts, the 0.5 funding scale (from
    2025-12-19), NATGAS max leverage 10x isolated, CL and BRENTOIL 20x cross.
  - Search results: UNG holds front-month NYMEX natural gas futures and rolls monthly. USO and BNO hold near-month
    WTI and Brent. The funds' exact roll days were not confirmed; they are thought to be about two weeks before
    expiry, a few days after xyz's.
- **Code:** run only on synthetic data (`tests/test_rollcarry.py`).

## Data (`scripts/fetch_rollcarry.py`, run once after this freeze)
- **Hyperliquid (public, keyless):** xyz:NATGAS, xyz:CL and xyz:BRENTOIL from 2025-12-01 to 2026-11-12:
  - hourly funding (with premium);
  - 4-hour candles back past each listing;
  - the latest 5,000 hourly candles (from about mid-April 2026).
- **Yahoo chart, daily:** UNG, USO, BNO and ^IRX.
- **Manifest:** sha256 of every file. Provenance goes in `docs/provenance/rollcarry.json`.
- Not run before R476's and R477's fetches finish (one Hyperliquid fetcher at a time).

## Feature lineage and point-in-time availability
| Feature | Parent fields | Provider, instrument, units | Window and close rule | Available at decision time? | Vintage |
|---|---|---|---|---|---|
| Fund mark | Yahoo close | UNG/USO/BNO, USD | New York close, 16:00 ET | yes, same instant | point-in-time (daily close) |
| Perp mark | 1 h candle close, else 4 h | Hyperliquid xyz perp, USD | candle ending at 16:00 ET; 4 h fallback ending within 4 h | yes | point-in-time |
| Funding | fundingRate per hour | Hyperliquid, fraction per hour | credited at the hour's candle close | yes (paid hourly) | point-in-time |
| Bill | ^IRX close | Yahoo, % discount yield | the latest close on or before the mark | yes | point-in-time |
| Liquidation | candle highs between marks | Hyperliquid | 1 h where the history covers the interval, else 4 h | yes | point-in-time |

There is no selection: each pair is held continuously from its first mark, so survivorship is not an issue. All
three perps are listed today.

## The book (`scripts/run_rollcarry.py`)
- **Per pair:** long the fund and short the same notional of the perp, with USDC margin M = 1/3 of notional (R474's
  structure). Start equity 1. The first mark is the first fund close at least 7 days after the perp's first funding
  print. The last is the close of 2026-11-11.
- **Marks:** the fund's close at 16:00 New York.
  - The perp is marked at the close of the 1 h candle ending at 16:00.
  - Before the 1 h history starts, it is marked at the latest 4 h candle that ended within 4 h before 16:00. In
    winter that is 15:00 ET, an hour early; the count is reported.
- **Funding:** each hourly print is credited to the short on notional × the price of the candle ending at that hour.
- **Re-split:** when the hedge drifts 5% or the margin leaves [M/2, 1.5 M]. The target is fund = perp notional =
  equity / (1 + M).
- **Liquidation (isolated margin, R475's policy):**
  - Trigger: a candle high between marks takes margin − u × (high − last mark) below maintenance × u × high.
  - Maintenance is half the initial margin at maximum leverage: NATGAS 5%, CL and BRENTOIL 2.5%.
  - Consequence: the whole USDC margin is lost and funding stops at that candle. The fund leg is kept, and the book
    re-splits at the next mark.
- **Costs:** 5 bp of fund traded, 2.9 bp of perp notional traded (growth mode, read in R475's universe), and 10 bp of
  USDC moved. Entry and exit are included. 2x and 3x add one or two extra weekly cost charges.
- **Statistics:**
  - Weekly (ISO week) equity return minus the bill accrued (^IRX).
  - Newey-West t, lag 4; annualized × 52.
  - Legs as annual points: funding, perp price, fund price, cost, bill.
- **Samples:** A = weeks whose last mark is on or before 2026-07-22 (decides); B = later weeks (reported).

## Verdict (NATGAS-UNG, sample A)
- **INCONCLUSIVE:**
  - fewer than 12 weeks in A;
  - or more than 10% of fund closes without a perp price.
- **PASS:** excess ≥ 2.0 points a year, NW t ≥ 2.0 and 2x excess > 0.
- **PARTIAL:** excess > 0. **NULL:** excess ≤ 0.
- If the excess is negative with t ≤ −2.0, longs underpay the roll. The reverse book (long perp, short futures) is
  then recorded as a new idea, not a result.
- **Reported:**
  - CL-USO and BRENTOIL-BNO (A and B);
  - B for all three pairs;
  - per-cycle legs between roll completions (the mark of business day 10 to the next);
  - liquidations, the minimum margin and the 4 h mark count.
- **What it earns:**
  - A PASS or a PARTIAL with a positive 2x excess earns a forward paper lane under a new id.
  - That lane must name an executable hedge for a French account: CME futures on xyz's roll days through a futures
    broker, or a UCITS ETC with its own roll schedule.
  - UNG, USO and BNO are US funds a French retail account cannot buy (PRIIPs). They measure front-futures excess
    return here; they are not the owner's hedge.

## Power
- The weekly sd of the hedged pair is not known. Assumed 1.0-1.5%: the roll-timing mismatch (fund versus xyz, a few
  days of one month's spread), premium swings, and the 4 h winter marks.
- If NATGAS listed in early January, A has about 27 weeks. The se of the annualized mean is then about 10-15
  points, so a PASS needs an excess of roughly 20-30 points a year.
- B's NATGAS funding (29-141%/yr) is large enough that a gap of that size is possible. It is equally possible that
  the roll took all of it.
- An effect under about 20 points will read PARTIAL or NULL here.

## Trials
- Three pairs computed; one decides. Registry trials 3.
- Program trials: 9,785,259 before this lane, 9,785,262 after.

## Risks
- **Roll timing:** the funds roll a few days after xyz. Within a month this is mark noise; across months it nets out.
  Any persistent difference shows in the per-cycle table.
- **Venue:** trade.xyz and Hyperliquid, USDC, the oracle relayer (23/5 with a 17:00-18:00 ET gap), auto-deleveraging
  and halts.
- **Thin weekends:** the perp trades through the weekend on an internal price while the fund does not. Weekly marks
  span it.
- **Execution:** the US funds stand in for the hedge. CME micro contracts or a UCITS ETC add their own roll and
  basis.

## Code
```inputs
f8ce0b423e975a4c228bb9dc72820da96c5e698fbdb7947c267479155634659a  scripts/run_rollcarry.py
2ac5738526b6613df648b5614ebae0798811ac087282fe0c39fd2904118c8058  scripts/fetch_rollcarry.py
d95d77bb9aa0bf01f20422ac632d1c74394a4afddeafb79e998af4af46ff06cc  tests/test_rollcarry.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```

## Evidence lineage and admission
- **Method:** M532. **Related:** R474 (hedged xyz:TLT carry), R475-R477 (funding carry on xyz), R464, M462.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one pre-named decision; trials counted; costs at 1x, 2x and 3x; decision data (A funding, fund prices) unread;
    hashed public fetch.
  - Not met: measured costs, an executable hedge, forward evidence.

## Stop rules
- One run after the fetch. Nothing is retuned; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/rollcarry_v1/results/`.
