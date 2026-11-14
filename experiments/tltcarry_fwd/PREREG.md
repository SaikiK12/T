# PREREG: tltcarry_fwd (R474). Does a hedged carry on trade.xyz's TLT perp beat T-bills, forward?

- **Registry id:** R474
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12); the forward reads are run by
  `.github/workflows/claude-tltcarry.yml`
- **Date registered (UTC):** 2026-11-12

Method M529 (new). Found through R473 (M528), whose post-hoc funding check showed xyz:TLT longs paying far more than
the base rate. This file is frozen by `lab.prereg.freeze()` before any DTLA or bill price is read and before the first
forward day (2026-11-16). After the freeze it is never edited; a changed idea is a new lane.

## Question
- Hold the iShares $ Treasury Bond 20+yr UCITS ETF (DTLA, London, USD, accumulating) and short the same notional of
  trade.xyz's TLT perp (xyz:TLT, Hyperliquid HIP-3), keeping a third of the notional as USDC margin.
- The bond prices cancel. The book keeps the bonds' coupons (the ETF accumulates them; the perp follows TLT's
  unadjusted price, which drops on each ex-date) plus the funding that xyz:TLT longs pay shorts.
- Over 2026-11-16 .. 2027-05-14, does this book earn at least 2 points a year above the 13-week T-bill, net of
  trading and transfer costs, with Newey-West t ≥ 2.0?

## Why this could pay, and why it may not last
- **Mechanics (trade.xyz docs, read 2026-11-12):**
  - Hourly funding is 1/8 × 0.5 × [P + clamp(r − P, ±0.0005)], where P is the impact-price premium over the oracle
    and r = 0.0001 per 8 h. The cap is 4% an hour.
  - With no premium this is 6.25e-6 an hour (5.475%/yr), the base rate measured on xyz:TLT.
  - Payments are position × oracle price × rate; longs pay shorts when the rate is positive.
- **Measured since listing (R473 post hoc, `experiments/tlteom_v1/posthoc/xyz_tlt_funding.csv`):**
  - 2026-09-17 .. 11-12, 1,329 hours. Mean 20.1%/yr, median 5.5%/yr; longs paid in 80% of hours.
  - Seven full weeks: weekly sums 0.04, 0.54, 0.52, 0.22, 0.36, 0.32 and 0.43% (mean 0.35%, sd 0.17%).
  - The premium persists because a short needs bonds held elsewhere (a broker account plus a USDC margin on a DEX).
    That friction is the reason the carry exists. It also means the funding can fall to base, or below, as soon as
    more capital crosses it.
- **Coupons:** TLT paid $0.312 (ex 2026-10-01) and $0.343 (ex 2026-11-02), about 4.9%/yr on its price.
  - The perp/TLT close ratio over the listing span: mean 0.99997, sd 0.00096. No jump on either ex-date and no
    compensating funding, so the short keeps the dividend.
  - DTLA's expense ratio is 0.07%/yr (justETF, BlackRock, Hargreaves Lansdown); TLT's is 0.15%.
- **Expected excess on capital** (notional 3/4, USDC 1/4; bill near 3.7%, not read here):
  - Funding at the listing mean: about 0.75 × (4.9 + 18) − 3.7 ≈ +13 points a year.
  - Funding at base: about 0.75 × (4.9 + 5.5) − 3.7 ≈ +4 points.
  - Funding at zero: about 0.75 × 4.9 − 3.7 ≈ 0. **The coupon alone does not beat the bill** once a quarter of
    the capital sits idle as margin. The lane is a bet that funding stays above base.
- **Related nulls:**
  - R442 (OKX stock X-perps hedged at an EU broker) was NULL on rotation costs. This book is one static pair.
  - R470 (xyz against Lighter stock funding) was NULL; stock funding there sits near base. TLT's does not.

## What the author has seen
- xyz:TLT hourly funding and candles 2026-09-17 .. 11-12, the perp/TLT ratio, TLT's dividends (R473's data) and
  xyz's market metadata on 2026-11-12: maximum leverage 20, open interest 84,734 units, mark 81.2, day volume about
  $0.75M.
- DTLA.L and ^IRX: Yahoo's chart metadata only (currency USD, exchange LSE and CGI, names, first trade dates) and
  the row counts and date spans of a probe fetch (DTLA 39 rows to 2026-11-10, ^IRX 40 rows to 2026-11-11). No DTLA
  or bill price was printed or read.
- A BitMEX post titled "Equity Perp Funding Arbitrage on Hyperliquid" turned up in a search; every URL tried returned
  404, so it is unread.
- The runner was run only on synthetic data (`tests/test_tltcarry.py`).

## The book (`scripts/run_tltcarry.py`)
- **Start:** 2026-11-16 at the London close. Equity 1: DTLA worth 1/(1 + M), a short of the same notional, USDC
  M/(1 + M) on xyz, with M = 1/3 (3x on the perp; xyz allows 20x, maintenance 2.5%).
- **Marks:** each LSE trading day at 16:30 Europe/London (DST-aware).
  - DTLA: Yahoo's daily close.
  - Perp: the mean of the open and close of the 1 h candle containing 16:30. Hourly candles are all the venue keeps
    for months, and 16:30 is mid-candle.
  - A London close with no perp candle is skipped; funding and price carry to the next mark.
- **Funding:** every hourly xyz:TLT funding print between marks, rate × units short × the close of the candle ending
  at that hour. The venue pays on the oracle price; the perp tracks it to about 0.1%.
- **Re-split:** when |perp notional − ETF value| / ETF value > 5%, or USDC / perp notional leaves [M/2, 1.5 M].
  Equity E is re-split to ETF E/(1 + M), perp E/(1 + M), USDC the rest.
- **Costs:**
  - 5 bp of ETF value traded (spread and commission);
  - 2.9 bp of perp notional traded (0.9 bp growth-mode taker plus 2 bp slippage);
  - 10 bp of cash moved between the broker and xyz.
  - Entry and exit are both charged, so a read is the return of opening and closing the book.
  - 2x and 3x are reported as extra multiples of the realised cost.
- **Bill:** ^IRX (13-week T-bill, percent) as last known at the previous mark, × calendar days / 365.
- **Weekly series:** ISO weeks; return = last equity of the week / last equity of the previous week − 1, the first
  week against 1. Excess = return − the bill accrued in the week.
- **Annualized excess** = mean weekly excess × 52, with a Newey-West t at lag 4 (`lab.stats.newey_west_t`).

## Reads and verdicts
Each read runs once. The runner refuses a read before its date and does nothing once `results/<read>/summary.json`
exists. The fetch (`scripts/fetch_tltcarry.py`) runs inside the read and writes a sha256 manifest.

| Read | Window | Runs | Verdict |
|---|---|---|---|
| held | 2026-09-24 .. 2026-11-11 | after this freeze | REPORTED; decides nothing (funding already seen) |
| futility | 2026-11-16 .. 2027-02-12 | from 2027-02-13 | NULL (stop) if annualized excess < 0; else CONTINUE |
| final | 2026-11-16 .. 2027-05-14 | from 2027-05-15 | PASS: excess ≥ 2.0 pts, NW t ≥ 2.0; PARTIAL: > 0; else NULL |

- **INCONCLUSIVE:** fewer than 10 weeks (futility) or 22 weeks (final), or more than 10% of London closes without a
  perp candle (a halt or delisting).
- The futility and final reads are decided at 1x cost. The held read is never a verdict.
- A PASS is paper evidence only. Real money needs `lab.gate.go_real()` and the owner, in small stakes.

## Power (stated before any DTLA price)
- **Weekly noise.** Funding on 0.75 of notional moved 0.13% a week (sd) since listing. Price noise between the London
  close and the mid-candle perp is assumed at 0.1-0.2% a mark. It telescopes, and the NW lag-4 variance mostly cancels
  it. Assumed weekly excess sd: 0.15-0.3%.
- **Final read (26 weeks).** The se of the annualized mean is about sd × 52 / √26: 1.5-3.1 points.
  - Funding at the listing mean (+13 points): PASS with probability above 0.95.
  - Funding at base (+4 points): about 0.25-0.75, depending on the noise.
  - Funding at zero (about 0): about 0.02.
- **Futility (13 weeks).** It stops a true +4-point book with probability 0.04-0.18, and a zero book with 0.5.

## Trials
- 1 decision (the final read; the futility read can only stop it). Registry trials 1.
- Program trials: 9,785,249 before this lane, 9,785,250 after.

## Risks the paper book does not carry (each to be listed in FINDINGS)
- **Venue:** HIP-3 deployer (trade.xyz) and Hyperliquid risk; USDC; the oracle; auto-deleveraging; a halt or
  delisting of xyz:TLT.
- **Funding regime:** the premium can vanish. The futility read is the stop.
- **Margin path:** daily marks only. An intraday 30% move in TLT would be needed to reach maintenance at M = 1/3.
- **Transfers:** cash moves between a broker and xyz take time; the 10 bp is assumed, not measured.
- **Currency and tax:** the book is in USD against a USD bill. An owner in euros bears EUR/USD unless hedged; taxes
  are out of scope.
- **Basis:** DTLA's closing auction against a mid-candle perp; DTLA and TLT track the same ICE index but are
  different funds.

## Code
```inputs
d01061ae1d280b20345245126d77afce4f0405a68045af127f6be52c09939226  scripts/run_tltcarry.py
71641e88219d48eee4995193232cc501fad9ec6bef0a287d2916a25d2d5ef01a  scripts/fetch_tltcarry.py
e1fe063ffea5ef7b8b3f2f200b20d2fa2872b7cfbc269d1e2261783732c5df12  tests/test_tltcarry.py
4512c80cc4d0b70f0342e4edb8f083953771360837c62c2bca2dae0707482e74  .github/workflows/claude-tltcarry.yml
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```

## Evidence lineage and admission
- **Method:** M529 (new). **Related:** R473 (M528, the funding fact), R442, R470.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: one pre-named decision; trials counted; costs at 1x, 2x and 3x; power stated; a forward sample that did
    not exist at the freeze; public data with hashed fetches.
  - Not met: measured book costs for DTLA and xyz:TLT (assumed here), and account-level risk (venue, transfer, FX).
    A PASS earns that review, not real money.

## Stop rules
- The futility read can stop the lane. Nothing is retuned afterwards; a changed idea is a new lane.
- No orders, no money, no credentials. The reads write only `experiments/tltcarry_fwd/results/`.
