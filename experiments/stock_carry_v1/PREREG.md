# PREREG: stock_carry_v1, stock-perp funding carry across the crypto/TradFi barrier (M493)

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R436
- **Owner (single writer):** Claude (fork lane of the 2026-11-09 hunt wave; the orchestrator commits)
- **Date registered (UTC):** 2026-11-10

## Question
Does a weekly book that shorts the MEXC 24/7 US-stock and US-ETF perps with the highest trailing realized funding,
each hedged with the same notional of the cash stock bought at an EEA broker, earn at least 2 points a year above the
3-month T-bill on its capital after all costs (MEXC fees and spread, broker commission and spread, 15% US dividend
withholding), from July 2025 to 2026-10-21?

**Who pays:** levered longs on tokenized-stock perps, through funding. **Why fast firms may leave it** (docs/INFRA_GAP.md
point 1 and 5): the hedge sits in a stock brokerage most crypto arbitrageurs lack, and the perps are small (median
trailing daily turnover about $118k across the 401 `*STOCK` contracts at the data end).

## Universe
- **Contracts:** the 481 MEXC TradFi (type 2) USDT perpetuals listed on 2026-10-22 (`data/mexc_tradfi/runs/
  1792671203016652636/contracts.json`). Each base is mapped to a Yahoo ticker by `yahoo_symbol` in the runner (base
  minus `STOCK`; BRKB→BRK-B, COINBASE→COIN, ROBINHOOD→HOOD, TESLA→TSLA, NVIDIA→NVDA; indexes, commodities, metals,
  Hong Kong, Korean and Japanese underlyings dropped by name).
- **Kept** only where Yahoo's chart metadata says currency USD, exchange in {NMS, NGM, NCM, NYQ, ASE, PCX, BTS} and
  instrument type EQUITY or ETF. Leveraged and inverse ETFs stay in: their hedge is the ETF itself.
- **Count at the freeze (metadata only):** 381 contracts kept (324 EQUITY, 57 ETF), one contract per ticker; 21
  dropped by name, 78 without a Yahoo chart (all Asian listings, HTTP 404), 1 non-USD.
- **Survivorship:** current-survivor-only. Stock perps MEXC delisted before 2026-10-22 are absent, and Yahoo also keeps
  only live tickers. This is a venue-own-universe gate-0 screen: a PASS earns only a frozen forward paper lane (the
  valid forward path), never a real-money step.

## Data
| Input | Source | Coverage | Frozen as |
|---|---|---|---|
| Perp hourly klines (close, high, amount = USDT turnover) | MEXC public contract klines, fetched 2026-10-22 by `scripts/fetch_mexc_tradfi.py` | first bar 2025-07-23 for the oldest names, last bar opens 2026-10-22 11:00 UTC; 0 holes (provenance) | per-file sha256 in `inputs/mexc_files.json`, checked by the runner before any read |
| Settled funding (t, rate, cycle_h) | MEXC public funding history, same fetch | 8 h cycles for most prints (124,553); 4 h, 1 h and 24 h cycles also occur | same manifest |
| Contract snapshot (web taker/maker fee, contract size) | same fetch | 470 contracts at 2 bp taker / 0 maker, 9 at 0/0, 2 at 1 bp / 0 | sha256 below |
| Cash daily close and volume, dividends (ex-date, amount), splits | Yahoo chart endpoint, `events=div,split`, 2025-06-01..2026-10-24, fetched 2026-11-10 before the freeze, raw responses hashed in `inputs/cash_receipts.json` | per ticker | `inputs/cash_daily.parquet`, `inputs/cash_events.parquet`, `inputs/cash_meta.json` |
| 13-week T-bill (^IRX close, percent) | Yahoo, cached `data/markets/yahoo/_IRX.parquet` | to 2026-10-19 | sha256 below |

No price, funding level or return of the universe was summarized before this freeze. The coverage counts above
(cycles, listing months, turnover quantiles) were the only reads of the MEXC files. Prior exposure, disclosed:
- docs/MEXC_EDGES.md (2026-10-19 snapshot) noted two stock tokens (BMYSTOCK, PWRSTOCK) at about +0.77% per 8 h; the
  idea for M493 knew stock perps can carry high funding.
- M463's zero-trial audit counted dividend atoms in MEXC TradFi funding (51 of 67 ex-dates); R306 read MEXC TradFi
  prices for another question. Neither scored a carry.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Score = Σ settled rates in (t − L days, t] × 365 / L | funding.rate, funding.t | MEXC, perp, fraction per settlement | L = 7 or 14 days, settlements with t ≤ decision time | settled at t | yes (settled before the close) | current-survivor-only | none; missing prints count as zero (sum) |
| Perp price at the US close | klines_1h.close | MEXC, perp, USDT | close of the hourly bar that ends at 16:00 ET (13:00 on early closes) | bar close | yes | survivor-only | missing bar: no trade that week for that name |
| Perp turnover | klines_1h.amount | MEXC, USDT | trailing 7 days to the decision bar, mean per day | bar close | yes | survivor-only | NaN as 0 |
| Cash close, dollar volume | Yahoo close, volume | Yahoo, cash stock, USD | official close; 20-session mean of close × volume | after the close | yes (the order is MOC) | live tickers only | missing date: no trade |
| Price ratio | perp close / cash close | both | at the decision close | close | yes | — | outside [0.95, 1.05]: ineligible |
| Split ahead | Yahoo split events | Yahoo | split date in (decision, next rebalance] | announced in advance by the company | treated as known (announced corporate action) | — | — |
| Dividends | Yahoo dividends | Yahoo | ex-date in (mark date, next mark date] | announced in advance | used only for P&L, never for selection | — | — |

## Rule or search space
- **Rebalance:** the first NYSE session on or after each Wednesday (sessions = SPY's Yahoo dates), at the US close.
  Window: every such date from the first Yahoo session (2025-06) whose close lies inside the perp data, through
  2026-10-21. Weeks with no position count as zero return on the full capital.
- **Eligible at decision d (time t):** perp close and cash close present; first funding print at least L days before t;
  no split in (d, next rebalance]; perp/cash ratio in [0.95, 1.05]; perp turnover ≥ $100k a day; cash dollar volume ≥
  $5M a day.
- **Book:** keep a held name while eligible and its score ≥ τ_out = τ_in / 2; fill the remaining slots of K with
  eligible new names ranked by score that clear τ_in. A held name without both prices is carried to the next date.
- **Size:** capital C = $10,000; notional per leg N = C × L_lev/(L_lev + 1) (L_lev = 2: stock fully paid, perp margin
  N/2); each slot is N/K at entry; quantities stay fixed while held.
- **P&L per position and week:** funding (Σ rate × q × close of the hourly bar ending at each settlement) − q × Δperp +
  qs × Δcash + qs × dividends × (1 − 0.15); costs on entry and exit.
- **Grid (the decision family):** L ∈ {7, 14} days × K ∈ {3, 5, 10} × τ_in ∈ {10%, 20%}/yr = **12 cells, 12 trials**.
- **Primary cell (fixed now): L = 14, K = 5, τ_in = 20%/yr.** Ex-ante reasons: a 14-day window is the steadier carry
  signal; five names spread single-stock squeezes; 20%/yr clears a weekly round trip (about 30 bp at 1x).

## Splits and cost
No train/test split: one fixed rule on the whole window (gate 0). Costs per side at 1x:
- **Perp:** the contract's web taker fee (2 bp for almost all; the owner places weekly orders by hand) + a declared
  5 bp half-spread haircut (no measured MEXC stock-perp book exists in the lab).
- **Cash stock:** IBKR Fixed commission, $0.005 a share, minimum $1.00, maximum 1% of value
  (https://www.interactivebrokers.com/en/pricing/commissions-stocks.php), + a declared 5 bp half-spread haircut.
  Regulatory sell fees (under 0.5 bp) and the one-time EUR/USD conversion are left out and named as limits.
- **Dividends:** 15% US withholding (France-US treaty rate with a W-8BEN) on dividends the long stock receives; the
  perp side is whatever MEXC's funding and price did.
- **Sensitivity:** every cost item × 2 and × 3. Extra cost view (not a trial): the MEXC API taker fee, 8 bp.
- **Leverage views (not trials):** L_lev = 1 and 3 at 1x.

## Gates
Primary cell, L_lev = 2, $10k:
1. Annualized net on capital minus the mean T-bill (^IRX close, 2-day lag, over the rebalance dates) ≥ **+2.0 pts** at
   1x costs.
2. Excess over the T-bill **> 0** at 2x costs.
3. 4-week circular block bootstrap (10,000 reps, seed 436) of the mean weekly net at 1x: the 2.5% point **> 0**.
4. Sum of weekly net at 1x without its **5 best weeks > 0**.
5. No position-week whose perp hourly high rose ≥ **45%** above the week's opening mark (an L = 2 short would be
   liquidated before a weekly margin top-up).

**Verdict:** PASS if all five hold; PARTIAL if 1-4 hold and only 5 fails (the carry needs L_lev = 1 capital);
INCONCLUSIVE if fewer than **26** weeks hold a position; NULL otherwise. Reported, not gates: the 12-cell grid at
1x/2x/3x, the API-fee and leverage views, Newey-West t (lag 4), positive-week share, worst and best week,
funding/price/dividend/cost decomposition, names held, capacity (slot size versus turnover).

**Power (assumption, stated before data):** with a weekly net standard deviation of 0.3% of capital and about 65
weekly dates, the 80%-power detectable mean is 2.8 σ/√n ≈ 0.10% a week, about 5.4%/yr. A smaller true edge can fail
gate 3 by chance.

## Null
The T-bill hurdle and the block-bootstrap interval of the primary's weekly net; no permutation null. The verdict rule
is above.

## Multiplicity
12 cells in this family, all reported; the primary alone decides. Program trials before this lane: see the registry
row's notes (`registry.program_trials()` at registration). A PASS here is exploratory against a program of about
9.78 million trials and earns only a forward paper lane.

## Evidence lineage and admission (future lanes only)
Canonical method id: M493. Parents: none (new). Related scopes: M463 (ex-dividend atoms, zero-trial audit), R430 and
R391/R275 (crypto carry engines, design references only). Samples seen: see "Data" above. Fresh sample: none, gate 0.
GATES requirements unmet: no forward days, survivor-only universe, declared (not measured) spreads. Binance stock perps
(`data/fundingRate`) are not used: their fee page was not read, the held funding archive ends 2026-09-30, and
symbol collisions with crypto tokens would need a mapping audit; a robustness arm would be a new lane.

## Stop rules
One run. No new feature, cell, threshold, universe filter or cost after the run. A crash after the freeze abandons the
lane (frozen files are not edited); a fix is a new lane id.

```inputs
e0704cf5eea412b89a0e107ef176d6ad1052722e6a3a33646295690cf3a4c07d scripts/run_stock_carry.py
ab17450b0392adb9a66d39e4481f8412ae746921fb0c2f387970268880f3c9a4 tests/test_run_stock_carry.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba scripts/run_clockflow.py
651e59851fd224c050640c47e2f953b325eb860cd082ce844f26027349d048e6 data/mexc_tradfi/runs/1792671203016652636/contracts.json
1117940f59539e6f981ac20f21c5fd18ae5368e5f644a78cbe7c056220b1cbf9 experiments/stock_carry_v1/inputs/mexc_files.json
e225b288bbff38066ef0a7afd5efd24e5d4d0f5daa2cc5f8976287e42a96324e experiments/stock_carry_v1/inputs/cash_daily.parquet
2d422eb55bb503eee092f1fe8b63591ebb15a6b7d825e3583d16684db183b4cd experiments/stock_carry_v1/inputs/cash_events.parquet
76c3cba58284443a914b1ea23b8153da884462d99f51ee9a6112092b8ed31ff4 experiments/stock_carry_v1/inputs/cash_meta.json
d8ec3fe40797180b9a439b33b1550d49ddd42081c2a180b7849ed0d6f6d8f96a experiments/stock_carry_v1/inputs/cash_receipts.json
dadd94c7ba2d03826b8128a1876fa3e8cc6b3cd197377b2232b043fd6ea7b36e data/markets/yahoo/_IRX.parquet
```
