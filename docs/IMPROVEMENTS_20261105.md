# 100 improvements toward better edges (2026-11-05)

A dated proposal written by Claude at the owner's request ("100 improvements in any direction, research or other").
It is evidence, not a second queue: research items that are new get a row in `registry/methods.csv` (M477-M481) and
the rest point at existing rows. Ranked by the binding constraint each removes. ★ marks the ten picked to start.

**Where the lab stands.**
- **Confirmed net edges are small and few:** cross-venue carry (about +2.5 to +10 %/yr); locked carry when the basis is
  rich (absent in 2026, +0.29 %/yr over the T-bill today).
- **Many gross effects are real but sit below taker costs:** the atlas lifts replicate 50-71 % against 6-11 % for
  placebo (R185, R192, R195).
- **Forward evidence is slowed by host outages:** 11-02, 11-04 09:38-19:10 and 11-05 14:43-15:08.

**So the levers are:**
1. uptime;
2. cost (maker fills, zero-fee venues);
3. premia not yet tested (volatility);
4. better statistics for forward lanes.

## A. Uptime and forward evidence (the slowest constraint)
1. ★ An always-on host for daemons (the owner's computer via Remote Control, or a small server): every outage
   deletes forward days that cannot be replayed. Owner decision.
2. ★ Automatic restart on session start: `scripts/restart_all.sh` is idempotent, so a local SessionStart hook can run
   it. This needs the owner's permission (the auto-mode classifier refused the self-edit).
3. An outage ledger per lane: on-time coverage, and the power each lane still has at its planned read.
4. Replayable-forward design: lanes whose decisions use only first-seen-stamped public data can be reconstructed after
   an outage, flagged as replayed and never pooled with live days.
5. Backfill sources for critical feeds (data.binance.vision daily archives, venue REST history) with gap flags.
6. A disk-budget guard: 5.8 GB free today. Pack old recordings to the `data-archive` branch before 1 GB is left.
7. Keep heartbeat `status.json` files out of the commit path; commit journals once per hour from the forward loop.
8. One scheduler that knows every lane's decision windows and holds the container up only then (from
   `lab/operations.py`).
9. A daily health line per lane, posted to #7 only when something is broken.
10. A restore drill: rebuild from git and `data-archive` on a clean container (task 160 handover).

## B. Execution and costs (most gross edges die here)
11. ★ Maker-fill replay with queue position from recorded L2 and trades (M474): fill rate and adverse selection on
    Lighter (0/0 fees) and MEXC (0 maker).
12. Reprice the replicated "gross positive, net negative" atlas cells (R192 and R195 excess CCEs) at maker cost net
    of the adverse selection measured in item 11.
13. Venue incentives, rebates and collateral yield as P&L terms (M475).
14. Fee-tier ladder: what monthly volume reaches the next tier, and whether a combined book reaches it.
15. Cost by symbol and hour of day from R404 and `mexc_costs`: trade only cheap hours.
16. Paper smart routing: each leg to the cheapest venue at decision time.
17. Implementation shortfall on every forward lane: paper fill vs the next real trade, to calibrate the fill model.
18. A latency map: which HFT rules become executable at 50 ms instead of the measured 233-255 ms.
19. A square-root impact law fitted on R404 depth, used to size $10k+ legs and to cap capacity.
20. M469: long-tail carry re-test at the measured R404 costs (after 11-18, as frozen).

## C. Carry, funding and basis (the only confirmed family)
21. M476: per-candle sizing on the carry book (shrunk Kelly, Gârleanu-Pedersen trade rate, no-trade band, cushion,
    liquidation cap).
22. ★ M478: USDC and USDT borrow and lending rates (public DeFi and exchange earn rates) as the carry's financing
    benchmark. They say when leveraged carry pays.
23. A funding forecast (HAR with open interest, premium index and basis) to enter carry pairs earlier (M455).
24. Locked carry v2 on R407's exact mechanics (`lab/locked_carry.py`), on every dated-future venue reachable.
25. Calendar spreads: long near, short far dated futures when the term structure kinks.
26. The same perp across venues at settlement: continue R353-R364 with the funding drag R387 measured.
27. USDT vs USDC quote spreads on the same coin as a carry.
28. TradFi perp funding (MEXC, 481 contracts) vs the underlying's cost of carry: rates and dividends (M463).
29. Carry capacity: the dollars before costs eat the spread (R404 depth).
30. A carry-crash exit (funding sign flip) re-tested on hourly data (R207 was daily).

## D. Sizing and portfolio
31. The shrunk-Kelly factor max(0, 1 - 1/t^2) on every lane's allocation after its PASS (derived and simulated in
    `docs/SIZING_EVIDENCE.md`).
32. A cross-lane portfolio from forward-only covariances (M281 sleeve book).
33. A Grossman-Zhou drawdown cushion at the portfolio level.
34. A per-candle liquidation cap for each carry leg's venue (extend today's BTC tail measure).
35. Finish the volatility forecast race: HAR with funding vs EWMA by QLIKE (M018, M185, M455).
36. Lane correlations on named stress days (`lab/stress.py`).
37. A capacity-aware allocation: each lane's dollar cap from book depth.
38. A no-trade band on the flow books' rebalancing.
39. Pre-registered kill switches per lane, with their cost in expected return.
40. The go_real ladder: a tiny owner-placed R406 twin compared with paper to the bp.

## E. Volatility and options (a premium family the lab has not tested)
41. ★ M477: the crypto variance risk premium. DVOL vs later realized volatility on the held `data/deribit/dvol_*`,
    pre-registered before any read.
42. M477: delta-hedged short straddles and strangles on Deribit paper from the held option trades
    (`data/deribit_trades`, 223 MB), at real spreads and fees.
43. Weekly (Friday 08:00) vs monthly expiry premium.
44. A put-skew premium: short 25-delta puts, delta-hedged (R307 read the risk reversal as a predictor, not a premium).
45. DVOL term-structure carry, if the term points are public.
46. Long gamma around scheduled macro releases when implied is below the realized volatility those releases bring.
47. Option-implied skew as a regime gate for existing books.
48. A cross-venue implied-volatility gap: Binance options (held) vs Deribit.
49. Volatility forecast quality as the sizing input of the premium (item 35).
50. A forward paper lane for the premium if gate 0 passes (public Deribit books, no account).

## F. Microstructure within our latency
51. Re-scope the HFT family to horizons of 500 ms or more (R367: 200 ms rules are not executable from here).
52. Order-book imbalance to the next 1-5 s mid move, at maker cost on Lighter (`record_raw`).
53. Toxicity (VPIN-style) as a filter for when to quote.
54. A liquidation-cascade fade at maker on Hyperliquid and Lighter trades (M325 extension).
55. Hourly-funding settlement microstructure net of the funding drag (R387 continuation).
56. A 1 s lead-lag between Hyperliquid and Lighter outside the EIA events (`record_tape`).
57. ★ R336 (MEXC zero-fee level scalp, +16.7 bp a trade, t 2.85, PARTIAL): reconsider its dropped MEXC forward lane at
    measured spreads.
58. Spread capture on newly listed perps in their first hours.
59. Lighter index steps (R389, M462): continue the forward event study.
60. A single-asset US-open effect on TradFi perps (R371 is cross-sectional).

## G. Events and flows
61. Unlock short (R266) with a pre-unlock entry variant, as a new lane.
62. Upbit listing pumps (M464, M465): needs the owner's yes for the Upbit hourly download.
63. Delisting and monitoring-tag shorts: keep running (R268, R270).
64. CPI, FOMC and NFP crypto responses on 1 s data at maker cost.
65. Daily ETF flow data to next-day BTC returns.
66. Stablecoin mint and burn (public chain data) to flows.
67. Exchange wallet flows (M294 recorder) to short-horizon returns.
68. Funding-interval switches as a natural experiment (M461).
69. Weekly-expiry pinning at maker (R296 tested the Friday fade).
70. News event study from `record_news`, timestamps first, pre-registered.

## H. Cross-section, ML and data
71. A clean point-in-time ML ranker with purged cross-validation, metrics-leak excluded (the R332 lesson).
72. A feature store with first-seen timestamps on every recorded field, so leaks are caught by construction.
73. The long-tail carry second read (R392, 11-17).
74. A survivorship-free universe that keeps delisted coins (R404 band costs).
75. A regime gate fitted forward-only (R233's gate was NULL on seen data).
76. ★ Resume the Hyperliquid vault download (5,609 of 9,478 done) and the leaderboard history (M466, M467).
77. Vault-copy test: follow top vaults chosen only from past windows, survivorship-free.
78. Overnight cross-asset signals into crypto (rates, dollar index, NQ; M198 tested the reverse).
79. Slow on-chain factors from the held Coinmetrics data.
80. The KRW premium on Upbit as a signal (only if `upbit_hist` covers it).

## I. Statistics and methodology
81. ★ M479: anytime-valid monitoring (e-values) for forward lanes, so they can be read every day without inflating error,
    instead of a few fixed looks.
82. A power plan before every registration: the minimum detectable effect at the planned N, and dropping lanes that
    cannot reach it.
83. Partial pooling across coins instead of per-coin t-tests.
84. Program-level error accounting that weights prospective lanes above in-sample families (9.78 M program trials).
85. A shifted-time placebo by default for every event lane.
86. The break-even cost printed by every runner next to 1x/2x/3x.
87. Decision memos generated from the PREREG text (no hand-typed verdict names).
88. Cross-venue replication as a standard gate before any forward lane.
89. A simulated false-PASS rate across all running lanes under the null.
90. An independent adversarial review of every PREREG before freezing (R407 caught R406's sizing defect after the
    fact).

## J. New venues, instruments and sources
91. A reachability check of more public perp venues, without working around any block.
92. Coinbase International perp funding as an extra carry leg.
93. Hyperliquid HIP-3 equity perps: funding vs dividends (M463).
94. Fee and data audit of other low-fee venues before any lane.
95. CME micro BTC futures basis vs perp funding (Databento, within the $2 cap).
96. Deribit linear (USDC) vs inverse futures: the convexity difference.
97. ★ M480: funding-rate swap markets (for example Pendle's Boros), which let a carry lock the funding itself. Check
    existence, access and public data first.
98. M481: Ethena-style basis yield (sUSDe) as the benchmark a carry book must beat.
99. DEX pool fees vs impermanent loss from the M288 recorder.
100. The owner checks whether a Deribit account is possible from their country, for the tiny real lock.

## The ten to start (★), in order
1. Item 2 (automatic restart; needs permission) and item 1 (always-on host; owner decision).
2. Item 41/42 (crypto variance risk premium, held data, gate 0 on unread questions).
3. Item 11 (maker queue replay).
4. Item 22 (financing benchmark).
5. Item 81 (anytime-valid forward reads).
6. Item 57 (R336 forward lane).
7. Item 76 (vault data).
8. Item 97 (funding swaps).
