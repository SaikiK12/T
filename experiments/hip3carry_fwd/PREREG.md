# PREREG: hip3carry_fwd (R479). Does R475's hedged funding carry pay forward, on every HIP-3 deployer and on xyz's London twins?

- **Registry id:** R479
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12); the reads are run by
  `.github/workflows/claude-hip3carry.yml`
- **Date registered (UTC):** 2026-11-12

Methods M530 and M531. Earned by R475 and R476 (frozen PASS, recorded PARTIAL) and R477 (PARTIAL with a positive 2x
excess). This file is frozen by `lab.prereg.freeze()` before the first forward mark (2026-11-16, 16:00 New York) and
before any data of the forward window exists. After the freeze it is never edited; a changed idea is a new lane.

## Question
Two books run R475's frozen weekly rule forward from 2026-11-16:
- **S (stocks):** short the US-stock perps of every HIP-3 dex (xyz, Paragon, EntropyIO and any dex listed when a read
  runs) that the rule picks, and hold the same stock. A French retail account can hold US single stocks.
- **T (twins):** R477's xyz index, ETF and metal perps, each hedged with its USD UCITS ETF or ETC on the LSE.

Over 2026-11-16 .. 2027-05-14, does each book's **carry** exceed 2 points a year with Newey-West t ≥ 2.0, while its
total (price included) stays positive at assumed and at measured costs?
- **Carry:** funding received + 85% of the stock dividends − costs − the 13-week bill on the capital in slots.
- **Total:** the book's whole return over the bill, net of a 15% dividend withholding.

## Why decide on the carry
- The hedge cancels the price in expectation. In R475-R477 the price leg was most of the weekly noise: weekly sd of
  the total 0.10-0.73%, of the carry 0.09-0.24% (active weeks, decide books).
- Carry is also what moved across venues: positive in A on all three lanes. Price was +5.62 points in R475's A,
  −0.86 in R477's.
- A book that earns carry but loses it on price, liquidations or shutdown exits is not a gain. The total must
  therefore be positive at assumed and at measured costs for a PASS. That condition is a sign, not a significance
  test.

## The evidence so far (all read before this freeze)
| Lane | Venues | A carry only | A total (t) | B carry only | B total |
|---|---|---|---|---|---|
| R475 | xyz US-stock perps | +5.56 | +11.18 (2.03) | −0.84 | +8.86 |
| R476 | Felix, Kinetiq, Dreamcash (A); Paragon (B) | +3.05 | +3.12 (2.14) | +9.65 | +10.63 |
| R477 | xyz index, ETF, metal; LSE twins | +2.48 | +1.62 (0.50) | +3.88 | +12.92 |

- Points a year over the bill. "Carry only" here is R475's statistic (funding − cost − bill, no dividends).
- **Identity fix, post hoc:** the frozen identity checks dropped markets with under 60 marks through a NaN. Fixed, A
  is unchanged in all three; B moves to +8.62, +9.45 and +13.12
  (`experiments/hip3stock_v1/posthoc/identity_nan.py`).
- **Against:**
  - R475's B carry was negative after xyz's funding halved.
  - R476's A venues (Felix, Kinetiq, Dreamcash) all shut in June 2026; six of its nine A trades ended at a shutdown.
  - Paragon's B funding was scanned before R476's freeze.

## What the author has seen
- Everything in R475, R476 and R477, through 2026-11-06 (B), including their post-hoc files.
- **A plumbing check on 2026-11-12** (`fetch_hip3carry.universe` and three names, decides nothing):
  - The universe has 327 listings on 10 dexes; 154 are US equities by Yahoo's metadata, 98 of them live (xyz 72,
    Paragon 19, EntropyIO 7).
  - For xyz_NVDA, para_AVGO and io_NBIS:
    - funding and 1-hour candles 2026-10-01 .. 11-12, with 30 marks at 16:00 New York each;
    - each passed the fixed identity check; the perp cost came to 2.9 bp;
    - the share of marks meeting the capacity floor: 1.00, 0.03 and 1.00.
  - No return, funding level or price of that check was printed or read.
- **Book snapshots** (`claude/xyz-books-data`): no cost value read. Only the recorder's columns are known
  (`scripts/record_xyz_books.py`). Paragon and EntropyIO recording starts 2026-11-12 (`hip3/`, this lane's change to
  `claude-xyz-books.yml`).
- **Code:** run only on synthetic data (`tests/test_hip3carry.py`) and in the plumbing check.
- Nothing of the forward window exists at the freeze.

## Data (`scripts/fetch_hip3carry.py`, run inside each read)
- **Hyperliquid (public, keyless):**
  - perpDexs and meta for every dex, delisted markets included;
  - for every US-equity listing (R475's Yahoo filter: EQUITY, USD, US exchange), hourly funding from 2026-10-12 and
    1-hour candles from 2026-10-01. The venue keeps the latest 5,000 hourly candles, so a read can be up to about
    four weeks late and still cover the window.
- **Yahoo chart, daily:** each stock and ^IRX from 2026-07-01.
- **T:** R477's frozen fetcher (`fetch_xyztwin.fetch`) from 2026-08-01: 4-hour candles, funding and the twins.
- **Measured costs:** the hourly book snapshots and daily fee settings on `claude/xyz-books-data`. These are `books/`
  and `markets/` for xyz, and `hip3/books/` and `hip3/markets/` for Paragon and EntropyIO. Only days in the window
  are read.
- **Manifest:** sha256 of every fetched file, copied into `results/<read>/manifest.json`.
- **Retries:** a dropped connection or a 5xx is retried with the same client and request, up to 4 times. R475's
  client already waits out HTTP 429.

## The books (`scripts/run_hip3carry.py` around R475's frozen `scripts/run_hip3stock.py`)
**R475's rule, unchanged:**
- 5 slots of 1/5 of capital. Enter at ≥ 12%/yr trailing 28-day mean funding (at least 80% of hourly prints, 28 days
  listed). Exit below 6%/yr. Decide on the last trading day of each ISO week.
- A slot holds the stock (or twin) worth 3/4 and USDC margin of 1/4 of the slot (M = 1/3).
- Re-split when the hedge drifts 10% or the margin leaves [M/2, 1.5 M].
- Liquidation: when a candle high between marks takes the margin below maintenance (half the initial margin at
  maximum leverage), the margin is lost.
- The 15% split guard. The bill accrues on slot capital; idle capital earns the bill.
- Entry guard: perp/close within 10%.
- A held name with no mark left (delisted, its dex shut) is closed at its last mark on the next decision day.

**S's changes from R475, each forced by the forward setting or by R475-R477's findings:**
- **Marks at 16:00 New York:** the stock's close and the open of the perp's 1-hour candle starting at 16:00. In
  winter R475's 20:00 UTC mark is 15:00 New York.
- **Identity:** R475's check with the NaN dropped before correlating: median perp/close within 3% over the last 60
  marks, and return correlation ≥ 0.5 when 19 or more returns exist.
- **Capacity floor:** a name is eligible, and stays held, only while the median 24-hour perp notional of its last 7
  marks is at least $150,000. That keeps a $10,000 book's slot ($1,500 of perp) at or under 1% of a day's volume. A
  held name that falls below the floor is closed on the next decision day.
- **Perp cost:** each market's taker fee from its growth mode and deployer fee scale, plus 2 bp of slippage. The fee
  formula is Hyperliquid's for HIP-3, as in R453; R475's 2.9 and 11 bp are this formula at xyz's settings.
- The same stock can be held on two dexes at once. Each listing is its own name, as in R476.

**T is R477's book (16:00 UTC marks on 4-hour candles, scaled twin, R477's costs),** with the same NaN fix.

**Costs:**
- Assumed: 5 bp of stock or twin traded; the perp cost above (R477's for T); 10 bp of USDC moved. Entry and exit are
  charged.
- 2x and 3x add one or two more weekly cost charges.
- **Measured:** the same books rerun with each perp's cost set to its median recorded fee plus the median slippage of
  a $5,000 market order (mean of buy and sell) over the window's snapshots.
  - A name with no snapshot keeps the assumed cost.
  - A name whose book never held $5,000 is charged 25 bp.

**Statistics:**
- Weekly (ISO week) sums from R475's book.
- Carry = excess − price + 0.85 × dividends; total = excess − 0.15 × dividends.
- Annualized × 52, NW t at lag 4 (`lab.stats.newey_west_t`).

## Reads and verdicts (each book decides alone)
| Read | Window | Runs | Verdict per book |
|---|---|---|---|
| futility | 2026-11-16 .. 2027-02-12 | from 2027-02-13 | NULL (stop) if the carry is below 0; else CONTINUE |
| final | 2026-11-16 .. 2027-05-14 | from 2027-05-15 | PASS if all hold: carry ≥ 2.0 points, carry NW t ≥ 2.0, carry at 2x cost > 0, total > 0 at assumed and at measured costs. PARTIAL: carry > 0. NULL: carry ≤ 0, or stopped at futility |

- **INCONCLUSIVE:** fewer than 6 weeks with a slot held (futility) or 13 (final).
- The runner refuses a read before its date and does nothing once `results/<read>/summary.json` exists. The final
  read runs even if a book stopped; that book's final numbers are reported and its verdict stays NULL.
- **Reported:**
  - totals at 1x, 2x and 3x;
  - both books at measured costs, with the share of names measured;
  - S without the capacity floor;
  - a 50/50 combination of S and T;
  - trades by dex;
  - liquidations;
  - exits at a dead market, with a stress line (a 5% adverse settlement on the perp leg of each);
  - median traded notional of held names;
  - dropped names and reasons.
- A PASS is paper evidence only. Real money needs `lab.gate.go_real()` and the owner, in small stakes.

## Power (stated before any forward data)
- **S:** carry weekly sd 0.09-0.24% (R475-R476). Over 26 weeks the se of the annualized carry is 1.0-2.4 points.
  - A carry of +4 (between R475's and R476's A): PASS on the carry conditions with probability about 0.6-0.95.
  - Like R475's B (−0.6): NULL.
  - The total must also be positive: with a weekly total sd of 0.1-0.7%, its se is 1-7 points. That condition
    fails about 0.05-0.3 of the time when the true total equals a +4 carry.
- **T:** carry sd 0.13%, se 1.3 points. A carry of +2.5 to +3.9 (R477's A and B) gives PASS on the carry conditions
  with probability about 0.4-0.85. The total (sd about 0.5%, se about 5 points) is positive about 0.7 of the time.
- **Futility (13 weeks):** stops a true +3 carry with probability about 0.03-0.2, and a zero carry with 0.5.
- **The capacity floor can starve S.** If few names are both liquid and over 12%/yr, S may hold fewer than 13 active
  weeks and read INCONCLUSIVE. S_nofloor is reported to show what the floor excluded.

## Trials
- Two decisions (S and T, final read). Registry trials 2.
- Program trials: 9,785,262 before this lane, 9,785,264 after.

## Risks the paper book does not carry
- **Deployer shutdown:** a dex can delist and settle at its own price. The paper closes at the last 16:00 mark. The
  stress line prices a 5% adverse settlement.
- **Venue:** Hyperliquid and each deployer; USDC; oracles; auto-deleveraging; halts; HIP-3 deployer stake slashing.
- **Execution:** stock at the closing auction against a perp order at 16:00; half-days (the stock closes at 13:00);
  transfers between a broker and Hyperliquid take time. The 10 bp transfer cost is assumed.
- **FX and tax:** the book is in USD against a USD bill. An owner in euros bears EUR/USD unless hedged. The 15% is
  the treaty withholding with a W-8BEN; French taxation is out of scope.
- **Capacity above $10,000:** the floor is set for that size only.

## Code
```inputs
fd1b2966a98e1e5563b9568d8917a18c446b6aacedb2129d9be605eaf978c3e3  scripts/run_hip3carry.py
982455215c58232fda91a3193222f6afb268a87612685ab86848f1773d26dd1a  scripts/fetch_hip3carry.py
36f0c0f665f6ec391e4d79a0f183fab0e7b65be6b9e2ecf47186c46c289eecc9  tests/test_hip3carry.py
913d5ecffe837ed6a51bc2b078d655ac263ddee9de86ec525abaae92e5d6dfa4  .github/workflows/claude-hip3carry.yml
a3f7e3e9b90f6371fe2577617a692068c73fdaa8081a3b5fa84cf68b6110fe77  scripts/run_hip3stock.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
15d7789618ae679aa9fae23fa049820b4579044bcb95ec223a02650b6a13bb96  scripts/run_xyztwin.py
f0cb42452354307bbf5bbbc4e6abad60b7ac2a41149118867fc4d487195ea79f  scripts/fetch_xyztwin.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5  scripts/record_xyz_books.py
```

## Evidence lineage and admission
- **Methods:** M530 (stock-perp funding carry), M531 (twin-hedged carry).
- **Related:**
  - R475, R476 and R477 (the history);
  - R474 (TLT forward carry, overlapping T's TLT pair);
  - R470 (xyz against Lighter, NULL);
  - R442 (OKX stock X-perps, NULL on rotation costs).
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - **Met:** pre-named decisions; trials counted; costs at 1x, 2x and 3x; measured perp costs; a forward sample that
    does not exist at the freeze; hedges a French account can hold; public data with hashed fetches.
  - **Not met:** real fills and account-level risk (venue, transfer, FX). A PASS earns that review, not real money.

## Stop rules
- The futility read can stop a book. Nothing is retuned; a changed idea is a new lane.
- No orders, no money, no credentials. The reads write only `experiments/hip3carry_fwd/results/`.
