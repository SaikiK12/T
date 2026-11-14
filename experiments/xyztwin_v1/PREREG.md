# PREREG: xyztwin_v1 (R477). R475's funding carry on xyz index, ETF and metal perps, hedged with a London twin

- **Registry id:** R477
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M531 (new): M530's selected funding carry, where the hedge is a USD UCITS ETF or ETC twin on the London Stock
Exchange instead of the same stock. This file is frozen before the data are fetched and before R475's or R476's
result exists. After the freeze it is never edited; a changed idea is a new lane.

## Question
- Each week, rank 13 xyz perps by trailing 28-day funding with R475's frozen rule. Short up to 5 of them and hold
  each one's twin in London.
- Does sample A (2026-01-16 .. 2026-07-22) earn at least 2 points a year above the 13-week T-bill, net of costs,
  with Newey-West t ≥ 2.0 and a positive excess at 2x cost?

## Pairs (frozen in `scripts/fetch_xyztwin.py`)
| xyz perp | Twin (LSE, USD) | Fit |
|---|---|---|
| SMH | SMH.L, VanEck Semiconductor UCITS | same index (MVIS US Listed Semiconductor 25) |
| URNM | URNM.L, Sprott Uranium Miners UCITS (acc) | same index |
| EWY | CSKR.L, iShares MSCI Korea (acc) | same country index, both in USD |
| KR200 | CSKR.L | KOSPI 200 in points against MSCI Korea in USD: the KRW/USD rate is unhedged |
| EWJ | IJPA.L, iShares Core MSCI Japan IMI (acc) | MSCI Japan against MSCI Japan IMI, both in USD |
| JP225 | IJPA.L | Nikkei 225 in points against MSCI Japan IMI in USD: JPY/USD unhedged |
| NIFTY | NDIA.L, iShares MSCI India (acc) | NIFTY 50 in points against MSCI India in USD: INR/USD unhedged |
| SP500 | CSPX.L, iShares Core S&P 500 (acc) | same index; the ETF keeps the dividends |
| XYZ100 | CNDX.L, iShares NASDAQ 100 (acc) | xyz's US 100 index (modified cap-weighted, non-financial) against the Nasdaq-100 |
| XLE | XLES.L, Invesco Energy S&P US Select Sector | same index |
| GOLD | IGLN.L, iShares Physical Gold ETC | spot gold (xyz lists no gold roll) against physical gold |
| SILVER | PHAG.L, WisdomTree Physical Silver | the same, for silver |
| TLT | DTLA.L, iShares $ Treasury Bond 20+yr (acc) | same index (also R474's pair; listed 2026-09-17, so B only) |

- **Left out:**
  - COPPER, NATGAS, CL and BRENTOIL. xyz prices them on futures rolled over the 5th-9th business day (roll-schedule
    page), so their funding likely prices the futures curve, and the only twins are futures ETCs that roll on other
    days. That is a different question.
  - PLATINUM, PALLADIUM and Samsung (PHPT.L, PHPD.L, SMSN.L): Yahoo history starts on 2026-07-17.
  - EWZ and EWT: their USD-share-class twins are quoted in GBp on Yahoo.
  - Single stocks: R475 covers them.

## What the author has seen
- **Sample B's funding (2026-07-23 .. 11-12), from R475's scans.**

  | | 8-week mean %/yr | 4-week blocks q1-q4 %/yr |
  |---|---|---|
  | KR200 | 37.8 | 65.7, −17.9, 20.3, 55.3 |
  | NIFTY | 47.7 (385 hours) | |
  | TLT | 20.1 | |
  | SMH | 14.2 | 3.8, 22.0, 17.9, 10.6 |
  | URNM | 11.5 | 10.6, 15.9, 15.8, 7.3 |
  | SILVER | 7.6 | |
  | GOLD | 7.1 | |
  | EWY | 7.1 | |
  | EWJ | 5.4 | |
  | XLE | 5.3 | |
  | XYZ100 | 4.8 | |
  | SP500 | 2.3 | |
  | JP225 | −3.3 | |

  The pairs were chosen after this scan, by what a French account can hold. B is reported only.
- **Earlier lanes:**
  - R464 (weekend fade on xyz index, commodity and FX perps) put the funding of SP500, XYZ100, GOLD, SILVER and
    others into weekend returns from 2026-05-01, which overlaps A.
  - R473 and R474 read xyz:TLT's funding since its listing (B).
  - No lane ranked these markets by their own funding level in A.
- **Twins:** Yahoo chart metadata only (type, exchange, currency, name, first trade date). No twin price was read.
- **Docs read 2026-11-12:**
  - trade.xyz roll schedules: COPPER, WTIOIL, BRENTOIL, NATGAS and DIESEL roll futures over 5 days.
  - US equity indices: external spot pricing from the cash index and 23/5 futures quotes.
  - Corporate actions: perp holders get no dividends.
- **Code:** run only on synthetic data (`tests/test_xyztwin.py`).

## The book (`scripts/run_xyztwin.py` around R475's frozen `scripts/run_hip3stock.py`)
- **R475's rule:**
  - 5 slots; enter at ≥ 12%/yr trailing 28-day funding; exit below 6%/yr; M = 1/3.
  - Costs: 5 bp on the twin, 2.9 or 11 bp on the perp by today's growth flag, 10 bp per transfer.
  - Liquidation on 4-hour highs; the 15% split guard; the bill.
  - Book from 2026-01-16 to 2026-11-06.
  - Verdict function with at least 20 active weeks.
- **Three changes forced by the twin:**
  - **Marks at 16:00 UTC**, the open of that 4-hour candle, on LSE trading days. The LSE closes at 16:30 London,
    so this is 30 minutes before the close in winter and 30 minutes after it in summer.
  - **Scaled twin:** prices are multiplied by k, the median perp/twin ratio over the pair's first 20 marks. This
    lets R475's entry guard (perp within 10% of the scaled twin) work; returns do not depend on k.
  - **Identity by returns:** daily log returns must correlate at ≥ 0.5 over the last 60 marks. There is no 3% price
    band, because an accumulating fund drifts from a price-return perp by its yield.
- **Pairs on one twin:** EWY and KR200 share CSKR.L, and EWJ and JP225 share IJPA.L. Each pair is a separate name
  and can take its own slot.
- **Fund fees and dividends** are inside the twin's price (accumulating funds and ETCs), so they are measured, not
  assumed.

## Samples and verdict
- A (weeks ending by 2026-07-22) decides; B (to 2026-11-06) is reported.
- **PASS:** A's excess ≥ 2.0 points, NW t ≥ 2.0 and 2x excess > 0. **PARTIAL:** excess > 0. **NULL:** ≤ 0.
- **INCONCLUSIVE:** fewer than 20 weeks with a slot held in A.
- **Reported:** `slots10`, `enter20`, B, and trades per pair.
- **What it earns:** a PASS, or a PARTIAL with a positive 2x excess, earns a forward paper lane under a new id with
  measured costs. Real money needs `lab.gate.go_real()` and the owner.

## Power (stated before any twin price or A funding)
- **Hedge noise is larger than R475's:**
  - Different funds or indices on several pairs.
  - FX on KR200, JP225 and NIFTY.
  - A 30-minute timing gap.
- Assumed weekly book sd: 0.2-0.4% of capital. The se of the annualized mean over 27 weeks is then 2.0-4.0 points.
- If A resembles B, a few names (KR200, SMH, URNM) would carry the book at roughly +2 to +4 points. PASS probability
  would then be 0.1-0.4.

## Trials
- 3 configurations (decide, slots10, enter20); one decides. Registry trials 3.
- Program trials: 9,785,256 before this lane, 9,785,259 after.

## Risks the paper book does not carry
- **Venue:** trade.xyz and Hyperliquid, USDC, oracles, auto-deleveraging, halts. Six other HIP-3 deployers have
  delisted every market (R474 FINDINGS).
- **Basis between different funds:** KOSPI 200 against MSCI Korea, Nikkei against MSCI Japan IMI, NIFTY against
  MSCI India, xyz US 100 against the Nasdaq-100. The paper measures it; it can change.
- **FX:** KRW, JPY and INR on three pairs. An owner in euros also bears EUR/USD on the whole book.
- **London hours:** a twin of an Asian index is priced by market makers while its home market is closed.
- **Transfers and costs:** assumed, not measured.
- **Taxes:** out of scope. The accumulating funds hold dividends after their own withholding.

## Code
```inputs
15d7789618ae679aa9fae23fa049820b4579044bcb95ec223a02650b6a13bb96  scripts/run_xyztwin.py
f0cb42452354307bbf5bbbc4e6abad60b7ac2a41149118867fc4d487195ea79f  scripts/fetch_xyztwin.py
cf08793b0f64422ece1c2a06e2f435b4e6797d4088fc477648e7ff7705c4d4c9  tests/test_xyztwin.py
a3f7e3e9b90f6371fe2577617a692068c73fdaa8081a3b5fa84cf68b6110fe77  scripts/run_hip3stock.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
53ccaeb382362178a06abb3f88c53e009d0670c28b7b77bd3ef67151215a48e6  tests/test_hip3stock.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```

## Evidence lineage and admission
- **Method:** M531 (new). **Related:** M530 (R475, R476), M529 (R474), R464.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one pre-named decision, trials counted, costs at 1x, 2x and 3x, a decision sample never ranked by
    funding level, hashed public fetch.
  - Not met: measured costs, forward evidence, account-level risk.

## Stop rules
- One run after the fetch. Nothing is retuned; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/xyztwin_v1/results/`.
