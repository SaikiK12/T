# PREREG: levels_lighter_v1 (R337). R333's level trades on Lighter's own prices, at Lighter's measured book cost

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R337
- **Method M412:** conditional support/resistance continuation versus rebound probabilities.
  - This lane re-prices R333's frozen out-of-sample trades on another venue's prices and cost.
  - It refits nothing.
- **Owner (single writer):** the Claude session that froze it. R337 was claimed on issue #7 (comment 6428171638)
  before the freeze.
- **Date registered (UTC):** 2026-10-26
- **Code:** `scripts/run_levels_lighter.py`, tested by `tests/test_levels_lighter.py`. It reuses R336's book functions
  from `scripts/run_levels_mexc0.py`.

## Why
**The owner (2026-10-26):** an edge must be tradable as short-hold futures, "scalping futures to do quick money".

**R336** (PARTIAL, gate 0) priced R333's trades on MEXC's zero-fee perps at the quoted spread: +16.7 bp a trade at
1x, t 2.85, break-even 10.5 bp a side. But:
- MEXC's zero fees hold for web orders only. API orders pay 6 bp maker and 8 bp taker since 2026-06-01, and the
  notice says API fees override promotions (`docs/MEXC_EDGES.md`). With the spread added, that is about R336's
  break-even.
- R336's full book places about 9 orders at each hourly close, which is API work. The manual 7-a-day book keeps
  about half (t 2.02).

**Lighter's default (Standard) account** pays 0 maker and 0 taker fees, API orders included. Taker orders wait
300 ms (`docs/VENUE_STRUCTURE.md`). Its books are thinner than MEXC's, so the cost is the book walk.

## Question
Take R333's V0 events on the coins Lighter lists on its open route. Price them on Lighter's own hourly closes and
funding, at Lighter's measured cost of a $1k order. Does a constant-size book of the policy's trades earn a positive
net day-sum at 1x, with Newey-West t ≥ 2, over 2025-02-01..2026-09-30?

## Data (all already held; nothing is downloaded)
- **Events:** `experiments/level_probability_v2/results/v0_oos_events.csv.gz`, R333's frozen output.
  - Per event: the decision bar t on R333's hourly grid, the exit row, the level side, the class, sigma12, the
    model's E_sigma, R333's P1 side, and g on Binance closes net of Binance funding.
  - R333's walk-forward fit the model only on events that ended at least 24 h before each quarter.
- **Venue map:** `data/lighter_hist/contracts.csv`, open route only (each such market maps to a Binance perp).
  - The reserved route (no Binance perp) is never read.
  - Two markets are quoted per 1,000 tokens (1000TOSHI, 1000NOT). Returns are ratios, so this does not matter.
- **Prices and funding:** `data/lighter_hist/open/candles_1h/` and `data/lighter_hist/open/funding/`, fetched
  2026-10-21.
  - Bars are keyed by their open time. In zero-volume hours, Lighter repeats the last close.
  - Funding settles hourly. The rate is signed so that a positive value is paid by longs.
- **Book cost:** the 20 hourly snapshots of `scripts/record_lighter_book.py` in `data/recorders/lighter_book/` at
  the freeze (2026-10-21 16:00 .. 2026-10-26 21:00, with gaps).
  - Each row gives, for one market, the cost in bp from the mid of a $1k market buy and a $1k market sell walked
    through the shown book.
  - The runner reads only the snapshot files listed in the inputs block. Rows of symbols outside the open-route map
    are dropped before anything is computed.
  - Every snapshot row shows 0 maker and 0 taker fees.

## Events kept
- **Window:** decision day (t // 1 day, UTC) in 2025-02-01..2026-09-30, 607 days.
- **Coverage:**
  - The coin's Lighter market has a bar in each of the 72 hours ending with the decision hour, each with positive
    quote volume. This is R333's own candidate rule, on Lighter.
  - It has a close at every hour from the decision bar to the exit bar.
- **Cost:** the coin has a measured book cost.

## Pricing
- **Entry and exit:** R333's hours. The entry is at the decision bar's close and the exit at the exit row's close.
  The exit was decided by Binance closes against ± sigma12 barriers or the 12-hour timeout.
- **g on Lighter:** the level side × the sum, over the bars held, of Lighter's next-bar simple return less the
  funding a long pays at a settlement inside that bar. This is `engine.forward_returns`' convention, as in R333.

## Costs
- **One-way cost of a coin:** fee 0, plus the median over the snapshots of the mean of its $1k buy and sell walk
  costs, with a floor of 1 bp.
- It is charged at 1x, 2x and 3x on entry and exit.
- 2x and 3x stand in for what is not measured:
  - Lighter's books before October 2026, which were thinner while the venue was young;
  - the 300 ms taker delay, and the seconds between the hourly close and the order;
  - orders above $1k.

Computed from the inputs before any outcome was read (97 coins; Lighter's symbol, one-way bp):

| Coin, bp | | | | | |
|---|---|---|---|---|---|
| BTC 1.00 | XRP 1.00 | SOL 1.00 | ETH 1.00 | BNB 1.00 | HYPE 1.00 |
| ZEC 1.00 | NEAR 1.04 | PAXG 1.18 | LIT 1.22 | CC 1.48 | TRX 1.59 |
| AVAX 1.63 | LINK 1.65 | WLD 1.69 | XPL 1.72 | ENA 1.73 | VVV 1.76 |
| AAVE 1.79 | DOGE 1.95 | ONDO 1.97 | SUI 2.00 | ARB 2.02 | XMR 2.33 |
| ETHFI 2.40 | UNI 2.42 | TAO 2.47 | ADA 2.72 | CRV 2.91 | PUMP 3.06 |
| JUP 3.30 | PENGU 3.38 | PONS 3.42 | 1000PEPE 3.42 | BCH 3.55 | 1000SHIB 3.63 |
| DOT 3.65 | HBAR 3.73 | SEI 3.86 | LDO 4.08 | LTC 4.10 | POL 4.13 |
| STRK 4.19 | TRUMP 4.44 | ZRO 4.71 | ASTER 4.75 | FARTCOIN 4.89 | OP 4.91 |
| WLFI 5.35 | PYTH 5.37 | AERO 5.53 | ICP 5.57 | VIRTUAL 5.72 | CHIP 5.91 |
| USELESS 5.92 | 1000BONK 6.32 | TIA 6.43 | GRASS 6.60 | WIF 7.26 | APT 7.35 |
| MON 7.59 | DYDX 7.84 | PENDLE 7.88 | DASH 8.14 | JTO 8.31 | MEGA 8.87 |
| FIL 9.30 | SPX 9.47 | SKR 9.67 | EIGEN 11.04 | ZK 11.66 | XLM 11.70 |
| 1000FLOKI 11.86 | 0G 12.05 | BERA 12.46 | S 12.99 | SYRUP 17.06 | AZTEC 17.73 |
| ROBO 18.61 | AXS 19.15 | POPCAT 24.72 | NMR 25.58 | ARC 27.34 | CAP 27.99 |
| MET 28.49 | EDGE 30.00 | RIVER 36.10 | KAITO 37.25 | BIO 39.06 | FF 44.09 |
| PROVE 47.29 | ZORA 55.14 | STABLE 55.35 | STBL 57.17 | LINEA 58.35 | 2Z 66.88 |
| AVNT 102.10 |  |  |  |  |  |

## Policy and books (6 trials)
- **LZ:** trade an event when |E_sigma × sigma12| > 4 × the coin's one-way cost, which is twice the round trip.
  Through the level if the expected return is positive, away from it if negative. This is R336's PZ at this lane's
  cost.
- **Books:**
  1. **LZ_SUM (primary):** a constant size per trade. The series is each calendar day's summed net return of the
     trades entered that day, in units of one trade's notional. A day with no trade is 0.
  2. **LZ_MEAN:** the same trades on R333's convention: each day's mean net per trade, with no-trade days missing.
     Reported with the primary.
  3. **LP1_TRADES:** R333's P1 sides, whose threshold uses the lab's API tier cost and is stricter, charged this
     lane's cost and summed per day.
  4. **LZ_BINANCE:** LZ's trades on R333's Binance g, at this lane's cost. The gap to LZ_SUM is the venue's price
     effect.
- **Controls:** THROUGH and AWAY on every kept event, summed per day at 0x and 1x, on Lighter prices.
- **Placebo (not a trial):** LZ's trades with random sides, 1,000 draws, seed 337. It reports the share of draws at
  or above LZ's 1x mean per trade.
- **Net per trade:** side × g − 2 × multiple × the coin's one-way cost.
- **A trade's day:** its decision bar's UTC day.
- **t-stat:** Newey-West with lag 3 (`lab.stats.newey_west_t`).

## Decision
**The primary is LZ_SUM, fixed now.** It is PARTIAL (gate 0) only if all five hold; otherwise NULL:
1. the 1x day-sum Newey-West t ≥ 2.0;
2. the 2x day-sum mean is positive;
3. the 1x day-sum mean without its 10 best days is positive;
4. the 1x day-sum mean is positive in both halves (2025-02-01..2025-11-30 and 2025-12-01..2026-09-30);
5. the 1x day-sum mean is positive without the trades of the coin with the largest net sum.

**What a PARTIAL earns:** a frozen forward paper lane on Lighter, with a new id, frozen before its first forward day.
- R333's model is refit once on all events that ended before the freeze, and frozen with its sha.
- Each hour it uses live Binance features and Lighter's book at each signal, freezes tickets before entry, and
  prices exits on Lighter.
- It is not a gate-1 pass. These hours and this model were seen in R333.

**What a NULL means:** on Lighter's prices at Lighter's measured cost, R333's book does not pay over this window.
- The automated route for M412 is closed at this scope.
- MEXC's manual web book (R336's PZ_CAP7) is the only route left, and no retuning on these data follows.

## Reported (not decided on)
- **Per book, at gross, 1x, 2x and 3x:**
  - trades, and trades per day (mean, median, p90, max);
  - bp per day, t, bp per trade and the hit rate;
  - bp per day without the 10 best days, and in each half;
  - the best coin, its share of the net, and the book without it;
  - bp per trade by quarter;
  - the max drawdown and worst day of the day-sum series, in units of one trade's notional;
  - trade quantiles from 1% to 99%.
- **Also per book:** the break-even one-way cost, R333's day-mean convention at 1x/2x/3x, and the most trades open at
  any hour (max and p95).
- **The venue gap:** the correlation of g on Lighter and on Binance over the kept events, and LZ's mean and median
  absolute side-signed gap.
- **Per coin, at 1x:** trades, bp per trade, share of the net and the cost.
- **Coverage counts:** events on mapped coins, each drop reason, and the events on coins without a measured cost.

## Power (from counts only; no outcome was read)
- **Coverage:**
  - 34,966 events fall in the window on mapped coins.
  - Of these, 3,702 fail the 72-hour rule and 4,549 come before the coin's Lighter bars start. None have a missing
    close.
  - 777 events on 10 coins have no measured cost: AI16Z, BIRB, DOLO, DUSK, EDEN, FOGO, MKR, MYX, PIPPIN and RESOLV,
    all inactive on Lighter now.
  - That leaves 25,938 events on 97 coins.
- **LZ:** 17,322 trades. That is 28.5 a day (median 26, p90 50, max 123), with a trade on 603 of the 607 days.
  - By half: 8,214 and 9,108.
  - By quarter from 2025Q1 to 2026Q3: 991, 2,115, 2,837, 3,376, 3,143, 2,636 and 2,224.
  - LP1 takes 9,586 trades.
- **A day's sum:** take a trade's standard deviation as 4.5% (R336's interquartile range). With 28.5 trades a day and
  pairwise correlation ρ from 0.1 to 0.3, the day sum's standard deviation is 47-73% of one trade's notional.
- **Expected t over 607 days:**
  - about 1.0-1.5 at +10 bp net a trade;
  - about 1.6-2.6 at R336's +17 bp;
  - about 1.9-3.0 at +20 bp.
  So a NULL is weak evidence against the book. A PARTIAL needs the effect at least as large as R336's.

## Known limits
- **Seen data:** R333 read these hours on Binance and fit this model. Lighter's prices track Binance's: their hourly
  returns correlate 0.98-0.995 on APT, AVAX and DOGE, and closes differ by about 5 bp at the median. So this lane is
  gate 0.
- **Exits:** decided on Binance closes, not on Lighter's.
- **Costs:** from 20 snapshots taken in October 2026. Lighter's 2025 books were thinner.
- **Survivorship:** the 10 coins without a cost are coins Lighter has since delisted, so their 777 events are left
  out.
- **Fills:** at the hourly close. There is no queue or latency model, beyond 2x and 3x.
- **Not measured:** Lighter's mark-price liquidations and its auto-deleveraging.

## Inputs (sha256, checked by the runner before it reads anything)
```inputs
63cfe3f52046d33036b798da26710f27a2677175da79e87fa3c11f04d5aef232  experiments/level_probability_v2/results/v0_oos_events.csv.gz
bd040f363ec869ffc6aeacd58f66bece070471b56b7fcf122269319a6df2e398  data/lighter_hist/contracts.csv
94e0b41aa48eadcdc04bbe88cc1d84dabad7561ef8f4a9fbfc4d69377b4b82cd  data/lighter_hist/open/candles_1h/0G.parquet
b68de42863bf9cdafb534796e49f4476f276a416704eb81821f0a46c269b333f  data/lighter_hist/open/candles_1h/1000BONK.parquet
8e59dcb81a38bce60e974042cc1ded296ed0b0a3f92cf1418b41aaccdb61945f  data/lighter_hist/open/candles_1h/1000FLOKI.parquet
b5e21f3f70c7c8b1f20b167601f1db4d4cc53109c80db951e2e60e02c6ea5675  data/lighter_hist/open/candles_1h/1000NOT.parquet
ee8c50dfec2e6f30e7301e567bfc68112795ff7e333bb53c3c077c8e303b1a1c  data/lighter_hist/open/candles_1h/1000PEPE.parquet
4dcff2b068d00bd35bdfbeb942d282a88667e273117bd4bd38808afdf1d50e4a  data/lighter_hist/open/candles_1h/1000SHIB.parquet
4d716dbb3b72fb459d8de778b16cf66c8ebb3d011cca2102266d4421557fe4a6  data/lighter_hist/open/candles_1h/2Z.parquet
139fb812a8c84b60061106b07d4deda8af30358e2f0c0d67bb545431fac257d6  data/lighter_hist/open/candles_1h/AAVE.parquet
e7bb98be3b4936e44a947f5ac27b80aeb2c497f4db213ab605d6e151fe50c10c  data/lighter_hist/open/candles_1h/ADA.parquet
0b22e231fa1e7d1c1220126475fd21ff4d98b478a6287b63f9515534d7ec61f5  data/lighter_hist/open/candles_1h/AERO.parquet
3825d88e46e79f8e97946547dcd24e007df0b6f9c234a97ae26ec9cb87060c1a  data/lighter_hist/open/candles_1h/AI.parquet
0ce94352d50f50e7d1d3d52d0db01c91902ab6b42ee048be6d4b1ce0e460c654  data/lighter_hist/open/candles_1h/AI16Z.parquet
cba3e50c5e1af1e919b320c6f576db14f830dfe087aec93582f4bdf4306cdd80  data/lighter_hist/open/candles_1h/APT.parquet
aed3ae51e53b1ef96621196849d3cc0bdbad3e8cf8e7e2aeaf70cf4aa753a52a  data/lighter_hist/open/candles_1h/ARB.parquet
6dbfb1747d8145cc22d78ac4b291f0acfcd379a7a8dc5e0486a0156135c741c5  data/lighter_hist/open/candles_1h/ARC.parquet
77028fbd5fb61cf3c831bb3f64c73a010bbfa105e37acbd381382f7b7900a310  data/lighter_hist/open/candles_1h/ASTER.parquet
6bb0dc529263a6ebe0328d12620bdce136ac4c3fc3cf7cb542c27a4080226fbb  data/lighter_hist/open/candles_1h/AVAX.parquet
b0a2adf8be3387f67a1870b15cf6097706e93342dbe7194ce7c0233bff7bc47a  data/lighter_hist/open/candles_1h/AVNT.parquet
2997d7b402a7bab60da9417385bb448829361858fc36cbf3608ba27055508d6a  data/lighter_hist/open/candles_1h/AXS.parquet
b10c203e7882f0960e1f5c824dff8921722c0401c2628b9412feb94daf0ae3e7  data/lighter_hist/open/candles_1h/AZTEC.parquet
192d941b345e303fa4b740788d0361db93f7223148025d6da27773df77077e3a  data/lighter_hist/open/candles_1h/BCH.parquet
b3fba80c977e304241bc905f40633d12d0234bab15eeb1bb15a64048c183e078  data/lighter_hist/open/candles_1h/BERA.parquet
67df1147759e0a996c5d22c5393e08036dcc7e688ec1be0f00996e7b42f6c461  data/lighter_hist/open/candles_1h/BIO.parquet
50c4f8e49caacc513d322a0d35275cf4bfd5818d1fb7b2b10d0403f5f31ed7ee  data/lighter_hist/open/candles_1h/BIRB.parquet
6751a89901e0f0215d715eb5766323e2a06e9cc8706438f57a36dcfc937a0d89  data/lighter_hist/open/candles_1h/BNB.parquet
e400c4aa687bdcf7be9d4c8ab2d2697c5f72f361d545eb9eee49e12720bb647c  data/lighter_hist/open/candles_1h/BTC.parquet
3b7ae0dd3895a6437a395f436289a93837cc5979761a55c88340a0ba422b798b  data/lighter_hist/open/candles_1h/CAP.parquet
304809ba9c06328d611c8cd7ab08ab5adce933e3bdba4e473e533c4f9ef0310c  data/lighter_hist/open/candles_1h/CC.parquet
27ed3aad0540dff3887d50640532061048aaa9e4a2cc46690bdb3100a44d2802  data/lighter_hist/open/candles_1h/CHIP.parquet
aea26582839d0b22ebcb003c2cb1ad7d1f1f8d7f11e9c311914032f86e624343  data/lighter_hist/open/candles_1h/CRV.parquet
f1469b9190f6b60345292cdc909f78dfaa45da305a5092f742b3154dba4c8507  data/lighter_hist/open/candles_1h/DASH.parquet
031fddb017bb54e989a70118ceb0a1de1a9054b0d8dd48fa8c208a9c5b6102b2  data/lighter_hist/open/candles_1h/DIA.parquet
e0a00aa424e48a37bf37e4bb670a368eaf97ded03828f0893a58af92af28b817  data/lighter_hist/open/candles_1h/DOGE.parquet
9bb82b8abc47a636a18cc1248f59d5b46f38ca77fb4a4f5702b55a6ac25870cb  data/lighter_hist/open/candles_1h/DOLO.parquet
fe700a99aee6d05e224e3bd115f5f9cab416a3d8a5ba14ace2e8b7f3f709c6b2  data/lighter_hist/open/candles_1h/DOT.parquet
b88180762e962713c06e87575f85ddbcf5afc48ac3c69549b19648ffe0ca991c  data/lighter_hist/open/candles_1h/DUSK.parquet
dfeac80a4314490c53a8cb3a88b232598a9148cffbe30ec7c7d90b10e98c9618  data/lighter_hist/open/candles_1h/DYDX.parquet
51d4af24bc79ffe99f5289910d4f9df68aae87d40db610a1a8f8c4b59c231618  data/lighter_hist/open/candles_1h/EDEN.parquet
206daa51e7f5d30c0c5ab3089da10518521a2df8ffea64b1bbbbbafefe6f7866  data/lighter_hist/open/candles_1h/EDGE.parquet
aa7c697b878b06b1eaa56f3ed8ae6d4e4aa5bdf9cd5a169489513fe1860592b8  data/lighter_hist/open/candles_1h/EIGEN.parquet
c3fae9309c96d034145672c9cf13a1f668532bd23fb01500270ab009fae04dde  data/lighter_hist/open/candles_1h/ENA.parquet
4fdd5651d05148f0d25f48abc489b1ac52aa27f540355fbcea07fa1d84ae3ae4  data/lighter_hist/open/candles_1h/ETH.parquet
66c16b84529f3ed499b498a102d5aebf82426c8a719ee0c0229c74b959afb4a3  data/lighter_hist/open/candles_1h/ETHFI.parquet
87c0f5c365eb0cb4fda8fe4ce3d6796bb5acc450d66c65817095f4bf1087f668  data/lighter_hist/open/candles_1h/FARTCOIN.parquet
00377f39acbe4570150c67ec9a213b24397066dd7450fe7a70241a91582bbba1  data/lighter_hist/open/candles_1h/FF.parquet
51d9381721384e3b6e2215ba1708e9c67ba28f57229d2ce13c88789cc6f4cc81  data/lighter_hist/open/candles_1h/FIL.parquet
1a58dd76035b4e2e84a17702d3997924d792a87953d03ccd25bc2f56f936483b  data/lighter_hist/open/candles_1h/FOGO.parquet
8a9fccfcc6289c6ae7f463acd9ba4fdc0a4de53e20a3326f115c0850b12ed9ac  data/lighter_hist/open/candles_1h/FOLKS.parquet
3043d1d8a818b71d055af9f2e94b9f59160f84c2f37d90fbdc69f7f9ac5e9ebf  data/lighter_hist/open/candles_1h/GRASS.parquet
71d8550b3406bea82f949216312cba6517bb6224f5e9b40457b8162b7e974564  data/lighter_hist/open/candles_1h/HBAR.parquet
ada33fe480d41835f28f37e979a1c9fdd2d5e65f20c114a29a138123f2912f61  data/lighter_hist/open/candles_1h/HYPE.parquet
b2c52d31276972f212f1cdc0bd6ebf32c9cf0f807cc1d76b69ae92af13ecc0bb  data/lighter_hist/open/candles_1h/ICP.parquet
363f857661b1b4bfa766be846dbe763fab4ff2af39a73697da0e80a4ff009301  data/lighter_hist/open/candles_1h/JTO.parquet
cafe969f5612ce31374ced80bf5a5ac974e5c3c3f1c341a52c3365548c811c69  data/lighter_hist/open/candles_1h/JUP.parquet
847b1bb91ba453adf211329846605c27eb0d37e1f54e489a845b3d793c7227b2  data/lighter_hist/open/candles_1h/KAITO.parquet
207fd5408d77a58c308decd7b5a8e12a2f484c7cdcdb7296e7b595a11fc7d4ef  data/lighter_hist/open/candles_1h/LDO.parquet
fead167047603764c58b98e04b68a6888c96b63074f3555c80130261e5daaa06  data/lighter_hist/open/candles_1h/LINEA.parquet
ee794517a070a52efd456652e78ce2ae74a1a4fc429c8dbacd1cd6ff0ed159ff  data/lighter_hist/open/candles_1h/LINK.parquet
2c2f5335d9d03a5cd0c690729a761c40c1a1540775f4d1ee8d2291ec85182e65  data/lighter_hist/open/candles_1h/LIT.parquet
8962a54fed99be299246e71302b27cae1bc69d9799ddabf36cca0ee0d58fecbe  data/lighter_hist/open/candles_1h/LTC.parquet
b3b8708b9a66870bb2fdd94b6147b2621d114c65cf58aaa4c73bdcb9d73edf80  data/lighter_hist/open/candles_1h/MEGA.parquet
dfd90ec0b6dc58be451f72c47ad1519dc3b98f45e9fde2918208783834434aa3  data/lighter_hist/open/candles_1h/MET.parquet
74b302705b6b6c02617a699fd007a71a3ab38bec8ffbb970fb6e9f1ae2bad491  data/lighter_hist/open/candles_1h/MKR.parquet
97cf472672b9d17cea1a668a51bf03acafaf2c4dbe86cc7d7d8ba80fd74d9b49  data/lighter_hist/open/candles_1h/MON.parquet
e6cc8b85bbc2237c7a8ae3c9c005324a1261b99322ef391ebc16c8c24fd7f84f  data/lighter_hist/open/candles_1h/MORPHO.parquet
f71754d6c45db847ab55cc2bfe72d207935ef1c94f7e245ccd6ed1ec07f11939  data/lighter_hist/open/candles_1h/MYX.parquet
e1efb9caabcd4188e8ca7a4f043a63d4629f54ed3d145a207fbdb53c025148fe  data/lighter_hist/open/candles_1h/NEAR.parquet
215f189ef7ba9c66ede9ec6d7d1fb06a5410affd4ccf073e53196e1fc2de15b3  data/lighter_hist/open/candles_1h/NMR.parquet
e3c256749d7848e0a472fe5042ec812d0abeb611f12a235f17d4a6c126dac457  data/lighter_hist/open/candles_1h/ONDO.parquet
48cac6bb2e391d60229e031334c49035440604557a620e7e91257c8d795280c3  data/lighter_hist/open/candles_1h/OP.parquet
2852e1f7afeceafec9c411b1675cff9f23c8c7db575406841b52d0eebda36c5c  data/lighter_hist/open/candles_1h/PAXG.parquet
aa9021169b29b775aa230167f7b2b1eaed9e5374b40e28209360c37db56cee4e  data/lighter_hist/open/candles_1h/PENDLE.parquet
c6326c21c131553b7974e91b45a8c928b8f2df2c73c5fbc72694e89ba8278d4b  data/lighter_hist/open/candles_1h/PENGU.parquet
6166497a7248e259964ce377c5aadb38a18a328172964d747410e8e864d66dc8  data/lighter_hist/open/candles_1h/PIPPIN.parquet
7bbe6b202ce161bc72d4daec939ce5809608bfe75ea16c4f5b9416441580d3e0  data/lighter_hist/open/candles_1h/POL.parquet
bda7590f6236e76349bac49fc902ad3180b6f6443711f9f67da4526f3e48cdc5  data/lighter_hist/open/candles_1h/PONS.parquet
b7e6a1c6db9010acdf3ec0d1aec1145ae58d421337d7035452649f13df358b01  data/lighter_hist/open/candles_1h/POPCAT.parquet
c4cd9c1b02dbecbec91d66438bea01d39214901e046c4ed1f55329f144ea3002  data/lighter_hist/open/candles_1h/PRL.parquet
9e1bc3101c75886cc48e64f5d297bffcce7b11fe9403e53ce63d0e7b635f1eda  data/lighter_hist/open/candles_1h/PROVE.parquet
c2f8e442a2a954fe157aec3ad874465612da5d3a482d8d5a5d973999f63b166a  data/lighter_hist/open/candles_1h/PUMP.parquet
1d9281036ab072a94c53c57d38c1ba15d464c7da4f4b4cd0fb518909d7b669c7  data/lighter_hist/open/candles_1h/PYTH.parquet
f68a95cb7075fa865c7c0fb0cd47a65bf08fe60bdd995302fb18cd7a49ba3be6  data/lighter_hist/open/candles_1h/QNT.parquet
94871f55eb3ce596192f219eba0408ef83970e2c85d63f3a6679476fb225ff9e  data/lighter_hist/open/candles_1h/RESOLV.parquet
2f61494b975d2e6f999153d87edf08664d327aba7ea2dc7fe0e9c058e2a97171  data/lighter_hist/open/candles_1h/RIVER.parquet
52e0bc78f5724ac58f989e28d3fa77d2e5db9ce304a09027a28191799ae711cc  data/lighter_hist/open/candles_1h/ROBO.parquet
5edac5b762289c734ae5e32b3210991548b6310beba5220f41e3a0a861d31591  data/lighter_hist/open/candles_1h/S.parquet
94005d214207bb6a124c9579bd42c43a81ec4dceb6610ed0638af2e841ba54cc  data/lighter_hist/open/candles_1h/SEI.parquet
d5b48486e7db22bbd0f7536b4e530f21edfca421d9dd02a28d5ff33ba19beaf2  data/lighter_hist/open/candles_1h/SKR.parquet
8cb72cad3889efce1d5faa4074e02198b19ad98fa8e482a569921145d0efb4a9  data/lighter_hist/open/candles_1h/SOL.parquet
d62df020e9c72c786bc06c09525e28e3ece1ed69fd6104e2bb54433a59d8f483  data/lighter_hist/open/candles_1h/SPX.parquet
2eb880b2757c649c6ef40785b02f0081567a65a85ded43dfaed9da7ecdd5e17f  data/lighter_hist/open/candles_1h/STABLE.parquet
a00978b874382f88829185f994db8e2fe307c9183e60b09a3738189d56cd057f  data/lighter_hist/open/candles_1h/STBL.parquet
677868eec79602261fb00f56db59a73e79d1cafd151fad3567f9d40a7f3718c1  data/lighter_hist/open/candles_1h/STRK.parquet
9deb421e4c11a2faf856c15503f498cab1b4edcc4b78bbdc6bbcb26b748bc3a5  data/lighter_hist/open/candles_1h/SUI.parquet
502209e473461944508c029e1cbb0e46b40bd3101e3288a0d5f5cbfa27b7a391  data/lighter_hist/open/candles_1h/SYRUP.parquet
112b516d78739122ff0ea5c71721146b6dd7385feae232324e3d30b5e67fcfbe  data/lighter_hist/open/candles_1h/TAO.parquet
a1c47902be28c8e9b2c7ed1873235bcc141748baf70e6da14bc9c365d8fe7bd3  data/lighter_hist/open/candles_1h/TIA.parquet
fa99e16bed1729636347a33ba0dd05690ec3c31eb8af3e43a0d69d55f9f470ba  data/lighter_hist/open/candles_1h/TRUMP.parquet
cd117f00a4d5921b18b3ba0a26c2348b8dfc40c02f5af146ac76660ac029220d  data/lighter_hist/open/candles_1h/TRX.parquet
fda70fde2ae08f251593ff7db5663dcc059be05b95a1a999e4657df270650cd9  data/lighter_hist/open/candles_1h/UNI.parquet
38575b9927f9d87cf08c6aab70ece996e9b2eb0bae6ec1f9c3c85807b771be4a  data/lighter_hist/open/candles_1h/USELESS.parquet
f5f39c4e0717474390b505998d252d3c9b6ced4c902b212d6308427a606b04b1  data/lighter_hist/open/candles_1h/VIRTUAL.parquet
b9501cd6bde2912872d0d469459e9d8e2ba5a2993ff122c8e1761998e2ed3966  data/lighter_hist/open/candles_1h/VVV.parquet
3e97b11ab22431141e450d3de58308d94d2d25d824c1b2575a8d4c35aa044418  data/lighter_hist/open/candles_1h/WIF.parquet
18e19be2f7a641012452bffd9e706b7f939918969d3ba749221db0a695f9e3c1  data/lighter_hist/open/candles_1h/WLD.parquet
cecd98bcaae59777b5ca1ac2e7c5712800859436c3700c5b165064f83c01bb3e  data/lighter_hist/open/candles_1h/WLFI.parquet
40462f301edec0573490b7eb83997dcd924fc84201c7bcff30e3523a7dcf04e3  data/lighter_hist/open/candles_1h/XLM.parquet
7253a9e604b70c328bb4acd237650648f1a27078ba4ad9dac2bd1589bdd721cc  data/lighter_hist/open/candles_1h/XMR.parquet
194c4c1319dd8967a4bc149d4ee0f9fd3524732a9cb184c5e5cccc2952ce2200  data/lighter_hist/open/candles_1h/XPL.parquet
dd63cb034762b811e35e48fd6be8a8a1cc5ba6366f88329caec45eaa1c853768  data/lighter_hist/open/candles_1h/XRP.parquet
a1fb1a46eff6b00231fc450e458e47888f9b1c507875fbd7cb28741a68f97f6e  data/lighter_hist/open/candles_1h/ZEC.parquet
a08ff7b93891220da5437d6c68769d4499d62c9980d84f598c56969fcbd9f909  data/lighter_hist/open/candles_1h/ZK.parquet
1816f700b5034ef16f795fda9e80e27cfedca23ad2e03452583a774560c1f572  data/lighter_hist/open/candles_1h/ZORA.parquet
0c9079a880619edd2e1da06bc4a90520af6d125741cb7b57d76fc71129d7a6c7  data/lighter_hist/open/candles_1h/ZRO.parquet
25fe27cccf16938f5a9855b8cf9d2e7a82a32752e2eaef8e7ee27fe86b16bb7e  data/lighter_hist/open/funding/0G.parquet
650155d9101eac677698cf2607c18fe4e11c67da101880af2445e22c2e817e39  data/lighter_hist/open/funding/1000BONK.parquet
a67e382b8d50cbed4e7976f3f03f58ecb9a7528a166021caebe95e6aae17a13b  data/lighter_hist/open/funding/1000FLOKI.parquet
26bd125f5ca13fdc7178f0ec8abd544eb664cb2c40466e0ae5931fff1d794abd  data/lighter_hist/open/funding/1000NOT.parquet
55e9ef7ce76057b27bce394e59d29616a87320162c82daf8d4d932521dd68dc6  data/lighter_hist/open/funding/1000PEPE.parquet
d132d1603dcb04844b63aa283bbd7aa1be4036d0e53a827e5350b5625dc320d1  data/lighter_hist/open/funding/1000SHIB.parquet
c0ad9905360e4ae48b00ba67d52d80ed05a543b0c23e85c3d1fd4d5e9ec0c765  data/lighter_hist/open/funding/2Z.parquet
52d5c219944211e21fa468f2a9bd99e792b65c4eeb344da1719f484bf3c6d78d  data/lighter_hist/open/funding/AAVE.parquet
1c0fc051302047701616ec66361bca177519a756f1e22c356a4c0bea5848a3d4  data/lighter_hist/open/funding/ADA.parquet
ad4f66310a4ca9764377186956c1d49e75b8a4e5594f0b7b007003eda14a74ac  data/lighter_hist/open/funding/AERO.parquet
9e0f57465ef02a70376e29329075583d221d5668352cfab1165f920fb142c8a2  data/lighter_hist/open/funding/AI.parquet
bc7aa0760cd025f47139083f6ff1ebe1e760698ee90d147ccc7588d9e2c2185f  data/lighter_hist/open/funding/AI16Z.parquet
27ba7bacf469461ae068ca13c086cb07b6dc3bc9db21e7b80fad6751ab1aff2e  data/lighter_hist/open/funding/APT.parquet
747ac0b023644dafaa3d3e635927fea68c60ceea47e7fef5029e06d95d9bbe60  data/lighter_hist/open/funding/ARB.parquet
b8af9cd59f53633c9cbc6fa28d7c7a54e10f21bef6e59ce7807c08413e53d944  data/lighter_hist/open/funding/ARC.parquet
d29c7a3185994ae140764af5c21748eb40ce652b3035f9cf30b4934c94f12efb  data/lighter_hist/open/funding/ASTER.parquet
c8628b217d15692af58f17977db4a226e25a02f882cc6c0b00c42f68120e5c56  data/lighter_hist/open/funding/AVAX.parquet
9fcbcf97a218c1fae64cb24816aad1f9b30def141276ef5f3cba746397802277  data/lighter_hist/open/funding/AVNT.parquet
0a37a807d5332f1bbcbecd1efbc2a07bb87370abb0cebc93c3e176b9f88f7341  data/lighter_hist/open/funding/AXS.parquet
a60cb0e76568b4cb53b8be34a2c8a73affc199fe296c7f66829e26fcda8c5990  data/lighter_hist/open/funding/AZTEC.parquet
10e24bf52911ebf6a782e9365a63abbefe92bc99fae43167d2ebd0281f541a3f  data/lighter_hist/open/funding/BCH.parquet
1775502a8d788d91a02cea436ff3b356b936cef2960d6cdf0072cbaa4496aa6f  data/lighter_hist/open/funding/BERA.parquet
7025f19cb743eefd246a38cdcf4aacc225d7ef35c50dd7a51a32ae61be069114  data/lighter_hist/open/funding/BIO.parquet
6b39759ac744e3866b27598542bb7045032a0f0a5e88f6416d196985e099a762  data/lighter_hist/open/funding/BIRB.parquet
42070e7e158809c6c3b57a3fb5298564c1167c8530c099c14f1ceacb949450b0  data/lighter_hist/open/funding/BNB.parquet
9676ff7fdffb8fa1d5fc3a7850f53dec4080e505e14de6c55fddc73079cd947d  data/lighter_hist/open/funding/BTC.parquet
f5ee1a1b5095942b4eb74577722c20cb9291d7edb109d356ee45d83f18da6f78  data/lighter_hist/open/funding/CAP.parquet
8827055d4754122ddf6084c2bf486c8c80a2f2e889cce2c08ce4150630aae783  data/lighter_hist/open/funding/CC.parquet
f3223d5d2a5c5c546d8dc35980118560bb331c437f2b7c8e1e6767c658697293  data/lighter_hist/open/funding/CHIP.parquet
7473eddb83250f45c704c3772c5d0f2a8bde77ed95e6922fb02ed167d21cbd49  data/lighter_hist/open/funding/CRV.parquet
80724c01c0651ea80d4b65ebc1ad6752222b89f4f9a4fedd6e4f25fc0c136a1e  data/lighter_hist/open/funding/DASH.parquet
0eec79fbc6df049002406e0647a2a0ccc946fa307ba0bed98d9bee5902329378  data/lighter_hist/open/funding/DIA.parquet
a730f78c88cb5b1b946dd339714fdf7fe528e5def28958fb539dd7ccad9fc096  data/lighter_hist/open/funding/DOGE.parquet
b02c9e801090844842b633226f0be0c5a7f0e5d26052863b92a72347105e75de  data/lighter_hist/open/funding/DOLO.parquet
248e2f3cdb4ae63e911ca1d851823c27d9975df997323adf34c82fdb9facf2e8  data/lighter_hist/open/funding/DOT.parquet
554248e484af9dfc39be339869afcf23dafcab8388ef319a37c04c8b4df03525  data/lighter_hist/open/funding/DUSK.parquet
bdc7d1226325cb3df09569a29e4ed07ab31e0c0ced2ffd018857f86292317849  data/lighter_hist/open/funding/DYDX.parquet
b02c9e801090844842b633226f0be0c5a7f0e5d26052863b92a72347105e75de  data/lighter_hist/open/funding/EDEN.parquet
18bb52475d5928723d1a2f9e453bff93639c62f9688f4232253165c683fe508c  data/lighter_hist/open/funding/EDGE.parquet
6ee8b805d7f77cb92d42f87eafdc59055badd1c4388023ed55a97c4be2c7e7b6  data/lighter_hist/open/funding/EIGEN.parquet
0501ffa1126a14f9c39bd0baed982853b323e1a10da9f68583966704fe85f432  data/lighter_hist/open/funding/ENA.parquet
e77b0ec5e48ff42afd15b588a6897ed75f4ff8a9369bfb87097b88b6ff743f37  data/lighter_hist/open/funding/ETH.parquet
50c341d0372cf64dd916e8f5524e1d9111ccc4306354a459ba3605273976d29a  data/lighter_hist/open/funding/ETHFI.parquet
830a413503d4c00a59c5037d58d4dd24546a553f528e8c816022cbd09887d39a  data/lighter_hist/open/funding/FARTCOIN.parquet
e2288fc0b081a9d8a9e7a2e41cfa84592b20d40b03d140adcc4464108786ae75  data/lighter_hist/open/funding/FF.parquet
b56cef91b6ed656f4f4bce06ca9b99399d9a0518158f55cf45185fcb62c9e103  data/lighter_hist/open/funding/FIL.parquet
94203c00a7ef7ee616d4c089edbe5c676683c9948a9984fdd5e3bbbe9bd54c05  data/lighter_hist/open/funding/FOGO.parquet
c2e9707b3307b01b2fa1b895b3581da8ff6e6630357a17e043dc3e532be833da  data/lighter_hist/open/funding/FOLKS.parquet
b3565f70467561c02eced403a1d13bb3d067f7d658bc551224512c7a1243bcf9  data/lighter_hist/open/funding/GRASS.parquet
dd4d3b32059e351fd40197796601c29a0e26ff60c2a3d60319217f5374bfd4b6  data/lighter_hist/open/funding/HBAR.parquet
5a9fdaa83a1dc1ed3a1e9ae51c1130f681a8bae8b992b4b1798257cbdc66f44f  data/lighter_hist/open/funding/HYPE.parquet
121b2f5ed5e4f349f10ee8d87dffb8c8fbfdf39130904754a12f77d86388aab0  data/lighter_hist/open/funding/ICP.parquet
784dfa441bb3c37d517b505de1bc9f376c2e1f6f54c5c6a96fb19e7d50a321ee  data/lighter_hist/open/funding/JTO.parquet
4e94d5796ca161bb5a795175541e0b2e31079df38277556b66806697d0b8870e  data/lighter_hist/open/funding/JUP.parquet
241c5b6cb4ed4f33f1c29843ee730b9d955d2cfced99847817ed0626d9c3b63f  data/lighter_hist/open/funding/KAITO.parquet
25e968ebcf1f0dcfea1fd47796cd4cb90aeee383b9a9a70ec860c674ba827049  data/lighter_hist/open/funding/LDO.parquet
8dbf34e5f6bb359a60ecb8f446f70e082196d0c008f7bef839f11d6b8d674fe0  data/lighter_hist/open/funding/LINEA.parquet
57cef5b69e729a81cb60c8a9b400d74d447ba1c7a36f628b524f91c4a8bee197  data/lighter_hist/open/funding/LINK.parquet
b3cde7fca465ff09cfe52e1485ccfdd3cab7d23d91a88b84ea48ed34f3b4de49  data/lighter_hist/open/funding/LIT.parquet
b3d78a428f1bffdc2ff3658c2c2ec3b15759c22bff7a12381bd242e4364f28a1  data/lighter_hist/open/funding/LTC.parquet
c4f4d0d9ecf3fb52284f3a3b2ea69e750137339cdc46e856a06b53a9603e9a98  data/lighter_hist/open/funding/MEGA.parquet
60ae8dfe3f1a4eb5c1ebc14f8e57e9db945f8b50c5b6046b5fc10e7552742961  data/lighter_hist/open/funding/MET.parquet
b02c9e801090844842b633226f0be0c5a7f0e5d26052863b92a72347105e75de  data/lighter_hist/open/funding/MKR.parquet
cbd8e3436489ebdd12ecd6f6454275dc1bf9019fdbb62d41c521f8b9a813bbdc  data/lighter_hist/open/funding/MON.parquet
d6c69a45df41910f3eaab00ee47c600abb85042da9f840c95166ee56f1863a24  data/lighter_hist/open/funding/MORPHO.parquet
b02c9e801090844842b633226f0be0c5a7f0e5d26052863b92a72347105e75de  data/lighter_hist/open/funding/MYX.parquet
2038a298f1d154d493313193aa5bebec559e17baa21a0bedc17ff48d12a61de2  data/lighter_hist/open/funding/NEAR.parquet
c6fdbe44a048f888daa9d1b2e3a3df2256edba862adb9419ede3cba8c4f0cdef  data/lighter_hist/open/funding/NMR.parquet
9d88c230dbf391977b1c0d345e66312b61197681878d5726f666aaa12c0d6ec6  data/lighter_hist/open/funding/ONDO.parquet
967c4a13ecddf1d7996a341dffb2cc627fafd3c7e1f20c7c8c30025bc74137b6  data/lighter_hist/open/funding/OP.parquet
4f38fdb57222d610b2c660aaf4049e04dcbc9aac019f5eb0d6de17b3c2219c8d  data/lighter_hist/open/funding/PAXG.parquet
2f23a3068f4542fd161943431d0dffd60774a1d3bfe065ccd1b3666e15e67354  data/lighter_hist/open/funding/PENDLE.parquet
4921a7b0ed20ef7183aca969626f46537ac551f67843aa037e65483ea090bb45  data/lighter_hist/open/funding/PENGU.parquet
a5b43238afed81da6b51a468b353312b2ddc81721eb053c0204c1415823f69e2  data/lighter_hist/open/funding/PIPPIN.parquet
f22fb5d4e67b4ba109e7a56efd6ea4beca910ff9885802fe575b5d82ec15d1a9  data/lighter_hist/open/funding/POL.parquet
bff575b0db242f599ff7be70396df487237cce58c6842d5d4936c44a3b004ec0  data/lighter_hist/open/funding/PONS.parquet
e8dee5e8b4911ed45eb8d71ebf90fc009152ffb189d953b18f6defed3cb304c1  data/lighter_hist/open/funding/POPCAT.parquet
aced16490dea59d468fd89ba919b894aede977ed830646280561eab97812b499  data/lighter_hist/open/funding/PRL.parquet
be7620b0883e753573683b36e717776175a6f18918c78fd1f1f3bc84b2e6ec8b  data/lighter_hist/open/funding/PROVE.parquet
46cb1c682a19e038caabfef92b784c93d118c4339275a1a2958b6af4ed3d960b  data/lighter_hist/open/funding/PUMP.parquet
7beb2b9f193d48a94b1f4e9fd442b74dafd2f7045e91211f164e9ee132206566  data/lighter_hist/open/funding/PYTH.parquet
0ed869594e9908fcd531963ec09413dd5bdc7a8e00d57c5af3d3c431b11ff6b2  data/lighter_hist/open/funding/QNT.parquet
b02c9e801090844842b633226f0be0c5a7f0e5d26052863b92a72347105e75de  data/lighter_hist/open/funding/RESOLV.parquet
00b4992aa52de70c43cf2762cde271a820c4750daa319699e5f6b4a198c604ba  data/lighter_hist/open/funding/RIVER.parquet
d000c4d91ae067f80c13589d19b1bc7f756ae89f41a33eb9a4fb4278f54249e7  data/lighter_hist/open/funding/ROBO.parquet
9a81da6094ea323315dd10c7d8b346944ef213c64f0b23fdf78e82818c5f5aca  data/lighter_hist/open/funding/S.parquet
99a8c2d4ad3a236720d8f00cd17bb50afd9864d4ef49e0d3799c64d610185947  data/lighter_hist/open/funding/SEI.parquet
edee3e7bf20a991718d1d0a4240dc1e7e0a811452cbe7deaf14e011e45586210  data/lighter_hist/open/funding/SKR.parquet
76be19706df57db54e9074763e0665dc11596d9487b837f87f2ebe48f5f74eb4  data/lighter_hist/open/funding/SOL.parquet
743c0c735d534e51e47ec37652e4370cf1b027c8ce825a8079b7152966670c73  data/lighter_hist/open/funding/SPX.parquet
17b9da977e2ec8251446b538afba01f820831e08ab8ca627e2132074aa2b2a06  data/lighter_hist/open/funding/STABLE.parquet
3e5e7c5c5b49bba7b478b9a4d78f009f5bad157990262a5f4aaeadb27ad2336e  data/lighter_hist/open/funding/STBL.parquet
9c02829119a4dcae146c74f3c08f7d705c3efdd9e16ed1173e3a88367576a2cc  data/lighter_hist/open/funding/STRK.parquet
54de3302c341d4153822dff427af9a4d372d0d21f3c199a135710b78d91e4643  data/lighter_hist/open/funding/SUI.parquet
8d905274c0bf62f4058a6f1a37fc5e850477661efa6711ce526eaa5c0bc8aa36  data/lighter_hist/open/funding/SYRUP.parquet
5376b20f39abc1f00ef16f0537c0b051158c1802a7c2b73ba0bdf1268af41a07  data/lighter_hist/open/funding/TAO.parquet
19a0592ffa614187616d3069e92dd46df1932c75092dbbec877071475d10903c  data/lighter_hist/open/funding/TIA.parquet
17082a4cc838716b0e13d8705793d035b2bc2ed631213a75e734e3426a848c3a  data/lighter_hist/open/funding/TRUMP.parquet
77302cf345b0cf13136fb5324bceba8f3d7fbb1c5ea5b3403771df2118a5e755  data/lighter_hist/open/funding/TRX.parquet
4c3af90e02805a1c9bc7e9d69889d6028a7de52f3203c2b1f1840a824d8ea620  data/lighter_hist/open/funding/UNI.parquet
99e7dae7599b5384e42de77483a7dbf47532c25fafe193182723e4334511a767  data/lighter_hist/open/funding/USELESS.parquet
70a6fa71434ac9674b24bdc4eee395771ba87a952a4b29cc45122f4c86a2270c  data/lighter_hist/open/funding/VIRTUAL.parquet
90740f406313cbccaddde2e1467db49c2b8a7f27f73588c754d6d04856521b69  data/lighter_hist/open/funding/VVV.parquet
740e2daf1cecb86119c668e2f716918bf527b268ca0a8b8ee53bde5276016c12  data/lighter_hist/open/funding/WIF.parquet
7d512c7a3661cefd40902641ccd3f677e0e7702b2ab5b475494d7b4eaf3208c8  data/lighter_hist/open/funding/WLD.parquet
bd4462a4cc59fa380c1ea1dda053e599c9ec55b4d2a37fd5b0d0c79387cc17e2  data/lighter_hist/open/funding/WLFI.parquet
257c32ea735bf7b045a6ab0d38b0e2a9d01cd2535d0e8d1cf12171eefbf95beb  data/lighter_hist/open/funding/XLM.parquet
647f50fe68a2e12565d74b00ab5bc75c1e13f7bdfea81fa57bb1e12c958a972e  data/lighter_hist/open/funding/XMR.parquet
17159c7b2dee6696fdde49a893ac66168f8c67e2e19ab909590dbdcd939fa0c5  data/lighter_hist/open/funding/XPL.parquet
cd73bb881a15162996a0b079d6bf5a9df35b3cc876d61b9e423488825d05148f  data/lighter_hist/open/funding/XRP.parquet
ae40ad4d0fe9368ba29516d0bb67b6d57f20749e0cce78cd9e69e01c3e0a8960  data/lighter_hist/open/funding/ZEC.parquet
3db78f1d5c577663cbcb05453ca5d2ad6ca64c78d3ff7f3635917db734696627  data/lighter_hist/open/funding/ZK.parquet
c6dd9ec9814813b110f6510eb6a6094f9a808999179649f9a0657eadb06da15f  data/lighter_hist/open/funding/ZORA.parquet
a115df85077b0b7d70c25ed92478e099d31f99843b839cb859fba249b6149da4  data/lighter_hist/open/funding/ZRO.parquet
018b8828832002e964e233b31ccd8ae9272af87c47171fc3e43732722b952767  data/recorders/lighter_book/2026-10-21/16.parquet
1284f3672e174920b4f6af25dc1095d5bea0cbd39efe7ec5b6aae5111487a10e  data/recorders/lighter_book/2026-10-21/17.parquet
ba4a0c875759cd9d5db59594d85969722c4ac857b06f5b0c20b446a0b014a44b  data/recorders/lighter_book/2026-10-21/20.parquet
6514c2eb6a4ecc064b14fe228b1d83ee01a60760e37038f6c1b4d1c377a03423  data/recorders/lighter_book/2026-10-21/21.parquet
576842018e81c3c93682c0432acd4cc88777dfe2ea2391c5ba9f641f5f847a85  data/recorders/lighter_book/2026-10-21/22.parquet
eddcd4702e7cf637315c501b7d37c38c998608cdfaa96ff1aab72df702a135c3  data/recorders/lighter_book/2026-10-22/01.parquet
083d9cd01d429c7c7c31ae7c0efe46709979ebf56af7b01f7ac9b98a8b46e662  data/recorders/lighter_book/2026-10-22/02.parquet
20f4a1f4ff48915b44628342c84a305bb330140f5c86360791413a136d55f42e  data/recorders/lighter_book/2026-10-22/03.parquet
9f96bde04596e8651160a2864bb503775f4e8e6d3cc14e47af883af7a7a26015  data/recorders/lighter_book/2026-10-22/04.parquet
268e67eadcb1ff0142a9f8193032aa4b252831d88cd87bd53a8f6dd82f5478ad  data/recorders/lighter_book/2026-10-22/06.parquet
836ba014871b3c96cd8de513b736656b501183b278d05ab3d4d1d9a666ad2799  data/recorders/lighter_book/2026-10-22/07.parquet
efa5ac591926382a48b5408c3808624de0cf18a1a7449e8f7c8cd588cb44d2e3  data/recorders/lighter_book/2026-10-22/08.parquet
2a083da836c53d81bf1ba49d8bf5d0560ac455b57719afa13b201d247e62ebd0  data/recorders/lighter_book/2026-10-22/09.parquet
5b62a82119e4c0d0f673c28caad36d6c1051ab187dec7b2b29e02049f64509af  data/recorders/lighter_book/2026-10-22/12.parquet
f3e234bd8a0a60e16805c2c53871df45320a0ac2342814839c8dbef423331377  data/recorders/lighter_book/2026-10-22/16.parquet
eee352fd1121da860e79813e818a3525a57071691c0420e77da81bf71ba61cc3  data/recorders/lighter_book/2026-10-22/17.parquet
c613bfc07d7538bf9c84ddfd80d1cc08628aa1ba64f23eaa65844efdf1460f7e  data/recorders/lighter_book/2026-10-26/15.parquet
902bef3fbe372f28ebae617632a49d5594fdc886acf3963498b301579ba4fc1c  data/recorders/lighter_book/2026-10-26/16.parquet
c0e66e6682af7c153ee16f6b2ef9902e0cfbe34bdc4e6627af8b9cc99b2c2951  data/recorders/lighter_book/2026-10-26/17.parquet
0730b033bf2fcbaa82c31662f26cc1b72aae2387f58f4aa78e3e06128f454512  data/recorders/lighter_book/2026-10-26/21.parquet
ca8705906d077149e5e41b0d176a79723119f437f6792e534506218b04027e7d  scripts/run_levels_lighter.py
df5467d5a3b17e6ad26e8d4d3c2ca84af01403ddf70c173df3b827a4a4ce4a38  tests/test_levels_lighter.py
da09f3a1f5b6c0441bd17ab8eb6a105259f59042d78db2c48b869bc598c47efc  scripts/run_levels_mexc0.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
```
