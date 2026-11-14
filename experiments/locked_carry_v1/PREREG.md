# PREREG: locked_carry_v1 (R335). The guarantee engine: a coin-margined cash-and-carry locked to expiry on BTC and ETH

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R335
- **Method M244:** dated-futures cash-and-carry: buy spot, short the matched future, hold to expiry.
  - This lane measures the history of its BTC and ETH coin-margined form.
  - Altcoins, rolls before expiry and early exits stay open.
- **Owner (single writer):** the Claude session that froze it. R335 was claimed on issue #7 (comment 6427214528)
  before the freeze.
- **Date registered (UTC):** 2026-10-26
- **Code:** `scripts/run_locked_carry.py`.
  - `--run` calls `verify()` on this file first.
  - It then checks every input's sha256 against the block below, before it reads any price.
  - Tested in `tests/test_locked_carry.py` on invented numbers:
    - the locked-dollar identity, and the one-times equity that cannot be liquidated;
    - the 08:00 UTC expiry, and the T-bill's two-day lag;
    - the loader returning no row before 2021-01-01, and dropping untraded or thin bars;
    - the engine: lock, hold to expiry, re-lock, the 14-day minimum, the window cut and the hurdle;
    - each lock against the T-bill actually paid.
- **Execution mode:** manual web or API.
  - Two orders open a lock and the settlement closes the short; one order sells the coins afterwards.
  - That is a few orders a quarter.
- **Gate: 0, on seen data.** R301 (qbasis_v1) read these COIN-M hours in 2021-01..2026-09.

## Why this lane exists
**The owner's request (2026-10-26):** stop putting effort into what does not work, think outside the box, and try to
create an equation or a model that guarantees something.

**What can be guaranteed.** A forecast cannot guarantee a profit. Only a complete hedge can: a position whose payoff
is the same in every outcome, so that its price at entry fixes the result. The cleanest one a small account can hold
is the coin-margined cash-and-carry:
- Buy B coins at spot S0, then short Q = B·F0 dollars of the coin's inverse quarterly at F0.
- At expiry the short has earned Q·(1/F_T − 1/F0) coins. The account then holds B·F0/F_T coins, worth exactly B·F0
  dollars at the settlement price F_T, whatever F_T is.
- The equity always equals the short's notional (one times), so the short cannot be liquidated.
- The locked return is F0/S0 − 1 before costs, and it is known at entry.

**What earlier work measured, and what it left open**
- **R327/R328** (Codex) measured one day's offer: 250 USD face on 10,000 of capital earned BTC +1.52 USDT at 1x.
- **My own read of 2026-10-26** used OKX and Deribit public quotes (scratchpad only, not a lane). BTC's locked yields
  were about 0.1-0.8%/yr above the 3-month T-bill.
- **R301** reported the mean annualized basis by year across its coins:

  | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|
  | +12.6% | −2.8% | +2.8% | +9.8% | +4.6% | +2.0% |

None of these says how often the locked offer beat the T-bill after costs, or what a patient engine would have
earned.

## Question
On Binance's BTC and ETH coin-margined quarterlies in 2021-01..2026-09, consider a cash-and-carry that is held to
expiry and entered only when its locked yield beats the 3-month T-bill by a hurdle. Did it earn at least 1%/yr more
than the T-bill at 2x costs?

## Data (backtest venue = trade venue)
- **Futures:** `data/coinm_1h/{BTC,ETH}USD_YYMMDD.parquet`, the 24 quarterlies per coin expiring
  2021-03-26..2026-12-25.
  - Source: Binance COIN-M hourly klines from data.binance.vision (`docs/provenance/coinm_1h.json`).
  - Only rows with t ≥ 2021-01-01 are read: a pyarrow filter does it, and the loader raises if an earlier row comes
    back. The contracts that expired in 2020 are not opened.
- **Spot:** `data/binance_spot/{BTC,ETH}USDT.parquet`, hourly from 2021-01-01. USDT is taken at one dollar.
- **Robustness:**
  - `data/coinbase/{BTC,ETH}-USD.parquet` provides dollar spot.
  - `data/coinbase/USDT-USD.parquet` sizes the USDT assumption, as its 1st, 50th and 99th percentiles.
- **T-bill:** `data/macro/ust_3m.parquet`, which is FRED DGS3MO (3-month constant maturity, in percent).
  - An observation is used from two days after its date.
- **Bars:** a bar counts only if its volume is above 0.
  - A futures bar also needs at least 10 trades. Spot files carry no trade count.
  - Bars under 10 trades are below 6% of each contract's hours. This is a plumbing count of trades only, with no
    prices read.
  - The settlement bar at 08:00 has no trades and drops out.
- **Window:** the bars opening 2021-01-01 00:00 .. 2026-09-30 23:00 UTC.

## Rule
At each bar close t (the end of a UTC hour), for each coin:

**Measures**
- **Eligible contracts:** τ, the days from t to expiry (08:00 UTC on the contract's date), lies in [14, 200], and both
  closes exist at t.
- **Gross locked return:** g = F/S − 1.
- **Net:** n_m = g − m·c, for m = 1, 2, 3.
  - At 1x, c = 25 bp for the round trip: spot taker 10 bp to buy and 10 bp to sell after settlement, and futures taker
    5 bp.
- **Locked yield:** y = n_1 · 365/τ. **Excess:** e = y − r_t, where r_t is the T-bill.

**Engine** (per coin, per hurdle h ∈ {0, 3, 6}%/yr)
- In cash, lock the eligible contract with the highest e once e ≥ h.
- Hold it to expiry, then stay in cash until the next lock.
- Decisions use 1x costs. The books are reported at 1x, 2x and 3x.

**Accounting**
- Cash earns log(1 + r)/8760 an hour.
- A lock's log(1 + n_m) is spread evenly over its hours from entry to expiry. A lock still running at 2026-09-30
  counts pro rata.
- Reported over the window: the engine's annualized return, the T-bill-only return, and their difference (the excess).
- Per calendar year: the engine's return minus the T-bill's.

**Descriptive outputs**
- Per coin and year, from the best excess on offer at each bar close:
  - the mean gross annualized basis;
  - its 10th, 50th and 90th percentiles;
  - the share of hours with e ≥ 0, 3, 6 and 10%.
- Each lock's return against the T-bill actually paid over its hours, since rates can rise after entry.
- The same computations with Coinbase dollar spot, as robustness. These are not trials and not part of the decision.

## Decision (primary: BTC, h = 3%, Binance spot)
**USEFUL** needs both of these. Otherwise the result is **NOT USEFUL**.
1. The excess over the T-bill is at least +1.0%/yr at 2x costs over the window.
2. The excess at 2x is above 0 in at least 3 of the 6 calendar years 2021..2026 (2026 to September).

The registry verdict is DATA_PASS for USEFUL and NULL for NOT USEFUL.

The other rules (ETH, and h = 0 and 6%) are reported with the same two checks. They do not change the primary's
verdict.

USEFUL means only that the result is worth an alert on the live offer and a forward paper design. It does not say the
offer will be rich again, and it authorizes no order.

## Null
There is no null distribution: each lock's return is fixed at entry by g and the costs. The uncertainty is whether the
offer will be rich again. That is history, reported year by year, not a statistic tested against noise. Cost
sensitivity is 1x, 2x and 3x.

## Multiplicity
- **This lane:** 6 trials (2 coins × 3 hurdles).
- **Program trials before R335:** 9,478,976 on this branch (`registry.program_trials`). Codex's branch shows 9,478,990,
  which includes R334's.

## Evidence lineage and admission
- **Canonical method:** M244.
- **Related methods:**
  - M170: R301 tested the basis as a perp signal, NULL.
  - M047: perp premium arbitrage, BLOCKED.
- **Parent rounds:**
  - R301 (qbasis_v1) read the 2021-01..2026-09 COIN-M closes and reported the mean basis by year.
  - R327/R328 (Codex) read the current quote only.
- **Samples already seen:** every hour in this window was seen by R301. No fresh sample, so gate 0.
- **docs/GATES.md sha256:** e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926.
- **Gate admission:** not sought. A forward lane would need its own PREREG and the owner's go.

## Not measured here
- Venue default, or a withdrawal freeze.
- USDT against the dollar: only its percentiles are reported.
- The settlement index against the spot sale: the coins are sold at spot after settlement.
- Fees above the taker assumption, or the account's real tier.
- Account access by country.
- Rolls and early exits.

## Stop rules
- One run. New hurdles, contracts, cost levels, early exits or rolls after seeing the results are a new lane.
- If an input hash fails, nothing is computed.

## Outputs
`results/summary.json`, `results/locks.csv`, `results/calendar.csv` and `run.log`.

## Inputs
```inputs
4ff05cf70d2075c4c578265a66319048fcd185b2354896722e3b6408d69768a0  data/coinm_1h/BTCUSD_210326.parquet
d699036ea7de35291a8f27cf7ea6fb98dbab7996c9dd2c6db813a72ba8a90ec1  data/coinm_1h/BTCUSD_210625.parquet
061cd93ac3b0c2ecd0aadb2e1c9d43e090fe0436164e9573f73dcb9d048c0db3  data/coinm_1h/BTCUSD_210924.parquet
801aff5f8c0bec7fc68655e2da77a236e865e11447397ce748ca89d6be6903b7  data/coinm_1h/BTCUSD_211231.parquet
771f6026de4b0b61e7e1e8fefb03c25826f2bb9a5aa13af57e5f7874b43d4269  data/coinm_1h/BTCUSD_220325.parquet
e9f74605fbe5b92d57ab37efd74b097b7c3f005d00a573664e2a689caf673e70  data/coinm_1h/BTCUSD_220624.parquet
6a088abf43e61e2f9ec196df769fd89217c3ebaf3f72de169703799b96c643ca  data/coinm_1h/BTCUSD_220930.parquet
e22ed28226b144936fb77ca65a7d33e9769f9186671025946efde2c17c75f7bf  data/coinm_1h/BTCUSD_221230.parquet
8df8d89ba8582d198b163103488681552cc5fa810dc021651de2615b76476d97  data/coinm_1h/BTCUSD_230331.parquet
3bf62df29ba0bc565bf9903086639889a2951ff0c86cb3915cb08a8c1108a875  data/coinm_1h/BTCUSD_230630.parquet
27c630153c8ea0e12140bcecee56ed282b45fce031419dd44967a7afb50c9495  data/coinm_1h/BTCUSD_230929.parquet
ea2a71b020cdfdc2214be1c9fd595b107b81456cc23af0d0ed4698cfe89dfca5  data/coinm_1h/BTCUSD_231229.parquet
b16c89a47bd91429410d5754a728501078f60d2ff78a700dec1649881c57ee94  data/coinm_1h/BTCUSD_240329.parquet
6ab6d1d96888b6f755c74ed5e26f449feecceb335687961162e9cb510628bce0  data/coinm_1h/BTCUSD_240628.parquet
71cb75305804de69b6e89105c5c8f67275bd6e1845517b224fb6d10372f6d9d2  data/coinm_1h/BTCUSD_240927.parquet
30ac79646b848a395f413fa034d15f08800cdf808c61b364d4fcc5a3783501ca  data/coinm_1h/BTCUSD_241227.parquet
237802fbdf23472fdcfae722f07f210984b30176540d7b479c06d8e54afd1c72  data/coinm_1h/BTCUSD_250328.parquet
9eb794f81f4dbd65df7dbd3100c7c6bba94cfdbc2961c273d766fdbce8ed9f2a  data/coinm_1h/BTCUSD_250627.parquet
78ab847f225a5b9f5193e2cfe1e0df1eda399b154ecd2659deb739b675a1491c  data/coinm_1h/BTCUSD_250926.parquet
a107df4fb96bb4e3f996299556bbb0ec73ad9446e6c639f1e95f366c1e91a27e  data/coinm_1h/BTCUSD_251226.parquet
10fe3d697a71e034ae35f04f5e70a37cf27f824b1a9ea87c346d9b4ce3b44f95  data/coinm_1h/BTCUSD_260327.parquet
59ddc949288f2b8f4b87abf50f5855cc487ceeb285f20dd863ee12ca1d251e4c  data/coinm_1h/BTCUSD_260626.parquet
8d995a142774c69256d7959b8545bbbe2b5868d2b5a35b618127c4f9631e2ae6  data/coinm_1h/BTCUSD_260925.parquet
bb9313a2afa779c9553c9fd2145b4fbbea3c9595782ab5beb427ae63d2c5a2f8  data/coinm_1h/BTCUSD_261225.parquet
3f25fe43fd6b48e617e9875af438bc85ee9d8206fa94d3201edf56e41f83a8d8  data/coinm_1h/ETHUSD_210326.parquet
d44efa592676a0d808b0e4219aa09d62ffd742859d5c6a281ef1994a6be510a8  data/coinm_1h/ETHUSD_210625.parquet
da0d185342fc93f0d5f26aab636de6f4d69514bc75373393035a80b8b9d21e06  data/coinm_1h/ETHUSD_210924.parquet
399f31baca5e5a42377dabd6d237331f0246fc59a52a34418e5869dc4f98d4d0  data/coinm_1h/ETHUSD_211231.parquet
4ebb45acd95f1d6a83cbbe38df3dbc47f4bd9dbb0c2102c0bbd8a3d1c05894fb  data/coinm_1h/ETHUSD_220325.parquet
25a9451877a2f79dbcddbe77c33910d58785398ccb45309c516f0d8cfaab3710  data/coinm_1h/ETHUSD_220624.parquet
5142187acd463db8f16bf5d2a62e892fb61e39be1310bd453321c43b1c6e7e59  data/coinm_1h/ETHUSD_220930.parquet
7def64c2172cc3b54355a2012e079e9317f6b4608a583a951564b9cb06b5333d  data/coinm_1h/ETHUSD_221230.parquet
47de96717e759abcd838c6cc06e1680fcef59f93a6e63db3ae16e9ffd92d97f6  data/coinm_1h/ETHUSD_230331.parquet
e941cd57afc807ccc1ec94812024620df878903c227ef485de57debd5d76ffd4  data/coinm_1h/ETHUSD_230630.parquet
91f26d3ee0b3660b3b5aacd4d0738188e18433bb5c2eebfa6d5d03ff1eb1f970  data/coinm_1h/ETHUSD_230929.parquet
fb1e1408c2c656471e678afbb31e46d5d102b9431f424983aa25ceb249a29a24  data/coinm_1h/ETHUSD_231229.parquet
47645d3c867bb1e48bd9acc92ce90c076ead73daac9772682e0ecf3125957768  data/coinm_1h/ETHUSD_240329.parquet
a421b244c6c70a6bfcf589e2b70350216ff678e25402ada5c05db1c7cf47883d  data/coinm_1h/ETHUSD_240628.parquet
3f4ea307fab8e2ce53fa5b7e30a6521ab6d86fa9572a1fa7f074295c182d4b48  data/coinm_1h/ETHUSD_240927.parquet
b0dc1b0e96de8ad779d58f37e31ade4b909fe6031af23205c9fcdc2d6e8d7fd9  data/coinm_1h/ETHUSD_241227.parquet
f0532d608f8ceb524b8f7579d7d93772e7f8e4a200e22b4f7e9c0ed4032b3733  data/coinm_1h/ETHUSD_250328.parquet
c015fc0fc2b1329aaaf8c1f6fb6b31fb25a374993b59b68da62635ff890fd077  data/coinm_1h/ETHUSD_250627.parquet
a505ce249d684041640d09589b15f719aee119fa8b581aa40030263db2e15c78  data/coinm_1h/ETHUSD_250926.parquet
fef1b5114390852dc4a935666abcb3d3f65690ac3ea3c0b34cd3a25fe5273f2e  data/coinm_1h/ETHUSD_251226.parquet
aca3bf25efb39dea899112ce20f41fd4d8702a5543cd489c5014dbd47b842124  data/coinm_1h/ETHUSD_260327.parquet
575957ca067a40cab5c40938458d5a3e3096ae46b37ddf94497a893b9661ca9c  data/coinm_1h/ETHUSD_260626.parquet
f71941070e1b1b394e29f07699894621e6c2be378e2ea38a78ca6bbe539a987d  data/coinm_1h/ETHUSD_260925.parquet
10c1492995a50ae290ecd9823babc91df917c39f9ca0933f0e5e51758e5b0205  data/coinm_1h/ETHUSD_261225.parquet
b885c835e6ccedf309d8f3a146fd9ac542e16b2ae84aa71438da2711c8f6aba6  data/binance_spot/BTCUSDT.parquet
89e4bd0d1402c521589badab3ca823157e99fa2485f78527038b9700fd320d9d  data/binance_spot/ETHUSDT.parquet
237247afd7c98bb7cd7f6d86c999ef4e4b2c662ff57554cad2097c6b5d4dd4ad  data/coinbase/BTC-USD.parquet
88700555cd2d43cf877ae7aeb97b0d6765fce1080a090650df1cb92971c956f3  data/coinbase/ETH-USD.parquet
3dc007f31ab4502e47d0581696fb4455907f068264f9eac2cfa0f248e430e4e0  data/coinbase/USDT-USD.parquet
bd9fc2ab8a3bb35d1b669f135083e679dc9cebfbbe46544531446af66f108bdd  data/macro/ust_3m.parquet
32753f108addabfc193580db81da783324254c3d06dea907b7b7bf75d3194cbf  docs/provenance/coinm_1h.json
e6f54ecd12d340bac83a13240dbe6c97d49d4e84751462a25cc37bf2c2abcde0  docs/provenance/macro.json
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
760bd29c4f22c9f8d6a78e3cb137baebd7f0b97f3f7ac7bada1eacfd7ddb240b  scripts/run_locked_carry.py
c450dd3aac0b475f724beb3e110e7345ed7b4d4c148e099fb2f04e92f3b1bf6b  tests/test_locked_carry.py
```
