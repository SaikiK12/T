# PREREG: levels_mexc0_v1 (R336). R333's level model on MEXC's zero-fee perps, at the measured MEXC spread

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R336
- **Method M412:** conditional support/resistance continuation versus rebound probabilities.
  - This lane re-prices R333's frozen out-of-sample trades at a zero-fee venue's cost.
  - It refits nothing.
- **Owner (single writer):** the Claude session that froze it. R336 was claimed on issue #7 (comment 6427816692)
  before the freeze.
- **Date registered (UTC):** 2026-10-26
- **Code:** `scripts/run_levels_mexc0.py`, tested by `tests/test_levels_mexc0.py`.

## Why
**The owner (2026-10-26):** an edge must be tradable as short-hold futures, "scalping futures to do quick money",
not as spot or long holds.

**R333** was NULL at the lab's API cost, but it holds the best short-horizon futures signal the lab has:
- hourly decisions, with exits at ± sigma12 or after 12 h;
- +29.7 bp gross per trade, and +18.1 bp/day gross day-weighted (t 4.84);
- a break-even of about 9 bp a side on the day-weighted series.

**MEXC** lists perps with zero maker and zero taker fees, where a trade's cost is the spread.

## Question
Take the coins whose MEXC perp had zero fees on every contract snapshot. Re-decide R333's V0 trades on them at MEXC's
measured spread. Does a constant-size book of those trades earn a positive net day-sum at 1x, with Newey-West t ≥ 2,
over 2022-01-01..2026-09-30?

## Data (all already held; nothing is downloaded)
- **Trades:** `experiments/level_probability_v2/results/v0_oos_events.csv.gz`, R333's frozen output. Its sha is in
  the inputs block. It holds every V0 out-of-sample event:
  - the decision bar t, on R333's hourly grid from 2021-01-01, and the exit row;
  - the class, and the through-direction return g on Binance closes, net of Binance funding;
  - sigma12, the model's three probabilities and E_sigma.

  R333's walk-forward fit the model only on events that ended at least 24 h before each quarter.
- **Zero-fee set:** the five MEXC contract snapshots `data/mexc/contracts/2026-10-{19,20,21,22,26}.json`.
  - A contract is in the set if it is trading (state 0) with takerFeeRate 0 and makerFeeRate 0 on all five.
  - That is 74 contracts on 67 base coins.
  - 55 coins have R333 events, where R333's symbol is the base plus USDT. The other 12 are TradFi or MEXC-only and
    drop out.
- **Spreads:** the 35 hourly MEXC ticker snapshots in `data/recorders/mexc_ticker/` at the freeze.
  - They run 2026-10-20 12:00..2026-10-26 21:00 and are listed in the inputs block. The runner reads only those,
    because the recorder keeps adding files.
  - Half-spread = (ask1 − bid1) / (ask1 + bid1).
  - Per contract: the median over the snapshots with a valid two-sided quote.

## Costs
- **One-way cost of a coin:** fee 0, plus the median half-spread of its cheapest zero-fee contract, with a floor of
  1 bp.
- It is charged at 1x, 2x and 3x on entry and exit.
- 2x and 3x stand in for what is not measured: slippage beyond the touch, latency, and spread changes since 2022.

The table was computed from the inputs before any outcome was read:

| Coin | Zero-fee contract | Median half-spread, bp | One-way cost, bp |
|---|---|---|---|
| ACE | ACE_USDT | 0.36 | 1.00 |
| ALLO | ALLO_USDT | 0.47 | 1.00 |
| APT | APT_USDT | 0.62 | 1.00 |
| ASTER | ASTER_USDT | 0.70 | 1.00 |
| BEAT | BEAT_USDT | 0.68 | 1.00 |
| DASH | DASH_USDT | 0.99 | 1.00 |
| LSK | LSK_USDT | 0.51 | 1.00 |
| ONE | ONE_USDT | 0.35 | 1.00 |
| POL | POL_USDT | 0.54 | 1.00 |
| VVV | VVV_USDT | 0.39 | 1.00 |
| WLFI | WLFI_USDT | 0.90 | 1.00 |
| JTO | JTO_USDT | 1.05 | 1.05 |
| JASMY | JASMY_USDT | 1.09 | 1.09 |
| ONDO | ONDO_USDT | 1.11 | 1.11 |
| MEGA | MEGA_USDT | 1.15 | 1.15 |
| AKE | AKE_USDT | 1.17 | 1.17 |
| BTR | BTR_USDT | 1.17 | 1.17 |
| LDO | LDO_USDT | 1.23 | 1.23 |
| BR | BR_USDT | 1.29 | 1.29 |
| RE | RE_USDT | 1.29 | 1.29 |
| ORDI | ORDI_USDT | 1.29 | 1.29 |
| SPX | SPX_USDT | 1.34 | 1.34 |
| STO | STO_USDT | 1.53 | 1.53 |
| BSB | BSB_USDT | 1.59 | 1.59 |
| 1000BONK | 1000BONK_USDT | 1.63 | 1.63 |
| VELVET | VELVET_USDT | 1.63 | 1.63 |
| ICP | ICP_USDT | 1.74 | 1.74 |
| KAITO | KAITO_USDT | 1.79 | 1.79 |
| EVAA | EVAA_USDT | 1.85 | 1.85 |
| PONS | PONS_USDT | 1.87 | 1.87 |
| BANK | BANK_USDT | 1.88 | 1.88 |
| POWER | POWER_USDT | 1.94 | 1.94 |
| FOLKS | FOLKS_USDT | 2.05 | 2.05 |
| SIREN | SIREN_USDT | 2.18 | 2.18 |
| LIGHT | LIGHT_USDT | 2.34 | 2.34 |
| HNT | HNT_USDT | 2.35 | 2.35 |
| MYX | MYX_USDT | 2.45 | 2.45 |
| BLESS | BLESS_USDT | 2.59 | 2.59 |
| TUT | TUT_USDT | 2.62 | 2.62 |
| DEXE | DEXE_USDT | 2.81 | 2.81 |
| SYN | SYN_USDT | 2.92 | 2.92 |
| SKYAI | SKYAI_USDT | 2.96 | 2.96 |
| BICO | BICO_USDT | 3.02 | 3.02 |
| PIPPIN | PIPPIN_USDT | 3.14 | 3.14 |
| RAVE | RAVE_USDT | 3.25 | 3.25 |
| LYN | LYN_USDT | 3.40 | 3.40 |
| CHZ | CHZ_USDT | 3.61 | 3.61 |
| CYS | CYS_USDT | 4.18 | 4.18 |
| HEI | HEI_USDT | 4.39 | 4.39 |
| RIVER | RIVER_USDT | 4.46 | 4.46 |
| AVAX | AVAX_USD | 5.19 | 5.19 |
| ESPORTS | ESPORTS_USDT | 5.89 | 5.89 |
| LAB | LAB_USDT | 7.86 | 7.86 |
| BILL | BILL_USDT | 8.78 | 8.78 |
| BCH | BCH_USD1 | 19.84 | 19.84 |

## Policy and books (6 trials)
- **PZ:** trade an event when |E_sigma × sigma12| > 4 × the coin's one-way cost, which is twice the round trip.
  - Through the level if the expected return is positive, away from it if negative.
  - This is the same form as R333's P1, at this lane's cost.
- **Books:**
  1. **PZ_SUM (primary):** a constant size per trade. The series is each calendar day's summed net return of the
     trades entered that day, in units of one trade's notional. A day with no trade is 0.
  2. **PZ_MEAN:** the same trades on R333's convention: each day's mean net per trade, with no-trade days missing.
     Reported beside the primary.
  3. **PZ_CAP7 (the manual book):** the first 7 PZ trades of each UTC day by decision time, summed per day. At equal
     times, the larger |expected| goes first.
  4. **P1_TRADES:** R333's P1 sides, whose threshold uses the lab's API tier cost and is stricter, charged this lane's
     cost and summed per day.
- **Controls:** THROUGH and AWAY on every event, summed per day at 0x and 1x.
- **Placebo (not a trial):** PZ's trades with random sides, 1,000 draws, seed 336. It reports the share of draws at
  or above PZ's 1x mean per trade.
- **Net per trade:** side × g − 2 × multiple × the coin's one-way cost.
- **A trade's day:** its decision bar's UTC day (t // 1 day), as in R333.
- **Window:** 2022-01-01..2026-09-30, 1,734 days.
- **t-stat:** Newey-West with lag 3 (`lab.stats.newey_west_t`).

## Decision
**The primary is PZ_SUM, fixed now.** It is PARTIAL (gate 0) only if all five hold; otherwise NULL:
1. the 1x day-sum Newey-West t ≥ 2.0;
2. the 2x day-sum mean is positive;
3. the 1x day-sum mean without its 10 best days is positive;
4. the 1x day-sum mean is positive in both halves (2022-01..2023-12 and 2024-01..2026-09);
5. the 1x day-sum mean is positive without the trades of the coin with the largest net sum.

**What a PARTIAL earns:** a frozen forward paper lane on MEXC's zero-fee perps, with a new id, frozen before its first
forward day.
- It uses live MEXC prices and quotes, checks the fee at each signal, and freezes tickets before entry.
- It is not a gate-1 pass. These hours and this model were seen in R333, and 9.48 million program trials stand behind
  any t of 2.

**What a NULL means:** R333's model does not pay on these coins even at MEXC's zero-fee cost. M412 stays NULL for
futures at this scope, and no retuning on these data follows.

## Reported (not decided on)
- **Per book, at gross, 1x, 2x and 3x:**
  - trades, and trades per day (mean, median, p90, max);
  - bp per day, t, bp per trade and the hit rate;
  - bp per day without the 10 best days, and in each half;
  - the best coin, its share of the net, and the book without it;
  - bp per trade by year;
  - the max drawdown and worst day of the day-sum series, in units of one trade's notional;
  - trade quantiles from 1% to 99%.
- **Also per book:** the break-even one-way cost, R333's day-mean convention at 1x/2x/3x, and the most trades open at
  any hour (max and p95).
- **Per coin, at 1x:** trades, bp per trade, and share of the net.
- **The cost table** and the zero-fee contract list.

## Power (from counts only; no outcome was read)
- **Counts:** 19,405 V0 events on the 55 coins. PZ takes 15,327 trades:
  - 8.8 a day on average (median 7, p90 18), on 1,708 of the 1,734 days;
  - by year: 2022 2,084, 2023 1,689, 2024 3,188, 2025 3,332, 2026 5,034.
- **A trade's spread:** about one sigma12, which is 2-5% on these coins; take 4%.
- **A day's sum:** with n trades and pairwise correlation ρ, its standard deviation is about 4% × sqrt(n (1 + (n − 1)
  ρ)). For n = 9 and ρ from 0.1 to 0.3, that is 15-22% of one trade's notional.
- **Expected t over 1,734 days:** about 2 at +10 bp net per trade (88 bp a day), and about 5 at +25 bp.

## Known limits
- **Seen data:** R333 read these hours and fit this model. This lane only re-prices and re-filters its saved trades,
  so it is gate 0.
- **Prices:** Binance closes and funding stand in for MEXC's. MEXC perps on thin coins can lag or deviate.
- **Coin selection:** the zero-fee set is October 2026's.
  - MEXC's fee groups change daily: 98 to 150 zero-fee contracts per snapshot.
  - A coin's past trades are priced as if it had been zero-fee throughout.
- **Spreads:** 35 hourly snapshots from October 2026 stand in for 2022-2026. Depth at the owner's size is not measured
  on these contracts.
- **Fills:** at the hourly close (V0), which means an order right at the decision close, so API execution. Barriers
  are read on closes. There is no queue or latency model.
- **Funding:** g carries Binance's funding, not MEXC's.

## Inputs (sha256, checked by the runner before it reads anything)
```inputs
63cfe3f52046d33036b798da26710f27a2677175da79e87fa3c11f04d5aef232  experiments/level_probability_v2/results/v0_oos_events.csv.gz
9653e68f1b04fb36eba14741181002ca917933bf93a03645b44f2dd9e9e5b4e7  data/mexc/contracts/2026-10-19.json
40b47d7815b5a2ebf6bdea9a40fec8a62d48bfc98eb2bb66842cd288a9cc13b3  data/mexc/contracts/2026-10-20.json
180753aabdd434f83ad5e792f8347c7359bb3dec2a8351e33e46841791fa078b  data/mexc/contracts/2026-10-21.json
ec25ba7aa4134f3adf75be5b110842255d5f55a87df6e41f56df0d8d4f79ce9a  data/mexc/contracts/2026-10-22.json
61d596565a7596d41ad3063cf9d65f1b0997f9b817c33117ae68b557e40bf26e  data/mexc/contracts/2026-10-26.json
e55943d9c30f554a9948cbbeb23e2abc341f32c27b8595b7710b98bc83fbbbd4  data/recorders/mexc_ticker/2026-10-20/12.parquet
0ffe68d5e0f9cf0857f18a8d2ae8ae350b990bf98728dc198b647782ddf725ae  data/recorders/mexc_ticker/2026-10-20/13.parquet
cac2b419c1a74b8328ca7189f8450a909c4eea76dd4c0030b4ff70d5cc7c1cf7  data/recorders/mexc_ticker/2026-10-20/16.parquet
4e618264c865764f64cfd41cbb21f889022ac1708b6732b3af936e2c302490fe  data/recorders/mexc_ticker/2026-10-20/17.parquet
9433c0a357d93334821946193aeb84100b895b1590d3c3a5eed48523e06be94e  data/recorders/mexc_ticker/2026-10-20/18.parquet
0b041dd063492d995350255dbaa408ab52fa3eeb54a62a796bf73f4a0ab48055  data/recorders/mexc_ticker/2026-10-20/21.parquet
68e5c061e6bd3b09938e3161e789a94aaea3337985a86b63df882462915f1430  data/recorders/mexc_ticker/2026-10-20/22.parquet
81b94609cc04a0135cdd12eab91ad6b14c8b70bb51efb5027e493203467975af  data/recorders/mexc_ticker/2026-10-20/23.parquet
f4b43a06ada12c7fcc217abf16eabe223c4e6398e67772cbed97180cd4a31ebf  data/recorders/mexc_ticker/2026-10-21/03.parquet
37558c746049e4769effcec2bda2fe28e60ae28eac4ad2b8201cb760fcdf42cb  data/recorders/mexc_ticker/2026-10-21/05.parquet
4fa318f19c6820b15109d244b413cae52e98ae72241149b77266719d05cd9d38  data/recorders/mexc_ticker/2026-10-21/06.parquet
a7dce5a87ad46a6ef78d43862c43c13ec20657e7c6225a298b7fa26f7638efda  data/recorders/mexc_ticker/2026-10-21/09.parquet
36d337767ecae7519937f64741e567dba4835f24de64a4dd2eb14209d4684efa  data/recorders/mexc_ticker/2026-10-21/10.parquet
4adbc2a9258ff6b71174d98beee922683e82535c6160fa3a235db6bd0452713d  data/recorders/mexc_ticker/2026-10-21/11.parquet
626a0f0572637b9d28444e1de9802c14b1bad1533998295c2e3605bb2b213fba  data/recorders/mexc_ticker/2026-10-21/15.parquet
3c4b630d40f685837a2742d208a1834ad51406ebad899440e081c9ebbe824faf  data/recorders/mexc_ticker/2026-10-21/16.parquet
08c41b166c8a6416d952a13f814fb0acb225205f8419fe934d00ca2faaff950c  data/recorders/mexc_ticker/2026-10-21/17.parquet
9f1a7008d6e23f29880274a17e6e1f5b342ff12fcd9bf1680a0be37faa9eaf33  data/recorders/mexc_ticker/2026-10-21/20.parquet
57bf4da5d465b79865027edc7d1c07f7d2ce4825e868784116aeb609a4b18382  data/recorders/mexc_ticker/2026-10-21/21.parquet
7ecc15dda5b4961303e9d8578e7fa9c0299894fe2171773a97ee0f194ce77d51  data/recorders/mexc_ticker/2026-10-21/22.parquet
5aa7b469b5033c2e513e47eb7f7fb5a155c32d449e148f73ad8847dd56f05b3a  data/recorders/mexc_ticker/2026-10-22/01.parquet
98792c1154a6a39e82479edfcda90a1307501f9857735a14f17c3e4b6a0093bd  data/recorders/mexc_ticker/2026-10-22/02.parquet
c3349757fa935ed692cc56a956ed0fba2a5dfccb32bdf0527288f9dcc360d7e2  data/recorders/mexc_ticker/2026-10-22/03.parquet
1a95d46829f9fc4e1178d75b769f2e7e7f6215915575db0d0adb111f6f3915f1  data/recorders/mexc_ticker/2026-10-22/04.parquet
0686bbe318c855a8452d75acc10466979e23f9e15164668ce18500c09c9a8979  data/recorders/mexc_ticker/2026-10-22/06.parquet
b760ecc8e3f0fc89a7b6656cadfa685fb1c16e52b9d799ad295b5db77780389d  data/recorders/mexc_ticker/2026-10-22/07.parquet
56525788606297bd268885c711de6ada3856c6ad81bab5f2f7ca27891a50ccf9  data/recorders/mexc_ticker/2026-10-22/08.parquet
25c9b5bf21e7a68d372f94a8a4c82ff659161b58e51a046f4056d35d681a9f73  data/recorders/mexc_ticker/2026-10-22/09.parquet
e67f5250cf571a03053820b1bff7d629b4207bb33f9807812c5851e3298d948c  data/recorders/mexc_ticker/2026-10-22/12.parquet
6d9e66266cd821ea2d00f6d5aa30258312fb502b2ae368cfcc462a34bdd79148  data/recorders/mexc_ticker/2026-10-22/16.parquet
e6e5d2eecdbcb64e06a19e4de042b6c4ae00b6cc4e663174874fbdb312499546  data/recorders/mexc_ticker/2026-10-22/17.parquet
bb59b1ac25a5f67a747858d3911f0873905bc14e4b9873d0fa4cbfc8f087b87f  data/recorders/mexc_ticker/2026-10-26/15.parquet
26d11c3d470a9a81a63283fa44d86ff8b6d228455f53390ca2723f5ec9261059  data/recorders/mexc_ticker/2026-10-26/16.parquet
988509b4be5e32ec314a947bffde23f37a1d3cc1be7785b91d701a48de65ffec  data/recorders/mexc_ticker/2026-10-26/17.parquet
26a52d0870353422a8a7e75e358c0ec277a9678b3269ffe4615dde0e1108353a  data/recorders/mexc_ticker/2026-10-26/21.parquet
da09f3a1f5b6c0441bd17ab8eb6a105259f59042d78db2c48b869bc598c47efc  scripts/run_levels_mexc0.py
47716aeb8249a627f127dba9bd29e4a5d936bbdc646b3532b50e89a38badcf99  tests/test_levels_mexc0.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
```
