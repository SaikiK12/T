# Scout: supply and index plumbing (room 20261125d)

Date: 2026-11-25. Scope: crypto supply and index plumbing. No orders, no accounts, no logins, no bypasses.
I did not open experiments/*/journal/, did not grep experiments/, and did not commit.

## 1. What the lab already did

- M057 (methods.csv:58) is the unlock short. Its rule is "insiders/privateSale >= 1% of max supply". R265 (rounds.csv:83)
  replicated it at gate 0 and recorded it as PARTIAL, in sample only. The rule names two cliff categories and leaves out
  "airdrop" by construction.
- M156 (methods.csv:157) is the unlock/ADV split, logged and not gated.
- M297 (methods.csv:269) is the post-airdrop supply short, UNTESTED. Its trigger is "more than a set share of supply was
  airdropped (recipients sell)". It is a listing-day share rule, not a cliff rule.
- M072 (methods.csv:73) is the 30-day pre-cliff short, BLOCKED, "N unlock calendar".
- M222 (methods.csv:223) skipped "index additions": "Skipped: data not free or effect decayed."
- R529 (rounds.csv:309) is the commodity index-roll front-run. Its status is RUNNING, PENDING and its P(PASS) was 15%.
  LESSONS.md:495 reports the same family as done: "a trader starting at the last month-end and holding to the 9th day
  earned about 3 bp gross a month, nothing, in 2010-2026." The two sources conflict. The room should settle R529's status.
- M015, M108, M235 and M281 are outside this family. M281 is a sleeve book that will include the unlock short.
- grep of methods.csv and rounds.csv for Bitwise, COIN50, CF Benchmarks, ETF, in-kind, creation, points and season:
  no hit for any of them. Crypto index rebalances, ETP creation rules and points clocks are not in the registry.

## 2. Data check

- data/defillama: mapping.csv (300 perps mapped to a protocol) and protocols.json (10 MB). The latest vintage, not
  point in time (docs/DATA_SOURCES.md:32). No unlock calendar.
- data/coinmetrics: open/ holds about 910 files; catalog.json lists supply and market-cap fields. Latest vintage.
- data/recorders/unlocks: 13 daily gzipped snapshots, 2026-10-20 to 2026-11-06. Each holds DefiLlama emissions per token.
  Run this session: 4,816 token rows, 428,935 unlock events. Allocation categories include "airdrop" (7,005 rows),
  "insiders", "privateSale", "farming", "ecosystem", "Uncategorized" and "community". Forward-only: no history before
  2026-10-20.
- data/unlocks/2026-10-20 is named in docs/DATA_SOURCES.md:21 but is NOT in this checkout (data/ has no unlocks folder).
  R265's calendar cannot be re-read from the named path here. This matters for candidate 1.
- data/hyperliquid/candles_1d: 235 files. None for BASED, ZEST or RE (checked by name).
- data/defillama/mapping.csv: BASEDUSDT has four candidate slugs, all "ambiguous" (lines 63-66). REUSDT maps to "re"
  with status "ok" (line 300). Zest is not mapped.

## 3. Public API and primary-source checks

- Test once: https://api.llama.fi/emission/based returned the body "Upgrade to the paid API plan at
  https://defillama.com/subscription". The probe https://api.llama.fi/emissions/ returned HTTP 402. Per-protocol
  emission history is paywalled. I did not work around it.
- COIN50 Index Guide, https://marketvector.com/rulebooks/download/COIN50_Index_Guide.pdf: HTTP 403, not read. Its
  quarterly schedule (Nov, Feb, May, Aug) comes only from a search summary. Treat it as unverified.
- Bitwise special meeting, July 14 2025, https://bitwiseinvestments.com/indexes/committee-meeting-notes/bitwise-crypto-asset-indexes/special-meeting-july-14-2025
  (returned by the fetch tool, not re-checked in a second read):
  - "At each monthly rebalance, the Bitwise 10 Large Cap Crypto Index will first weight Eligible Crypto Assets"
  - "based on free-float-adjusted market capitalization."
  - "at least 87.5% of the index is allocated to crypto assets"
  - "on each NYSE trading day, the index will evaluate its holdings as of 12 p.m. ET."
  - "If, on any such day, less than 86% of the index is allocated to Approved Components,"
  - "the index will effect a rebalance at 4 p.m. ET on the same day"
  - The page has no sentence on execution or notice period. The rule heading says "effective upon BITW's uplisting as an ETP".
  - Search summary only: the most recent notice is dated 2026-10-22 for the 2026-10-30 rebalance. Not verified on the page.
- CF Benchmarks, https://www.cfbenchmarks.com/blog/cf-institutional-digital-asset-index-postponement-of-the-q3-2026-reconstitution-and-rebalance
  - "its scheduled implementation date of September 1st, 2026"
  - "in due course, no less than 7 days prior to the new implementation date"
  - "This postponement will minimise any negative market impacts of the scheduled Reconstitution and Rebalance."
  - Search summary only: the postponed rebalance was later suspended on 2026-10-29.
- SEC press release, https://www.sec.gov/newsroom/press-releases/2025-101-sec-permits-kind-creations-redemptions-crypto-etps
  - "voted to approve orders to permit in-kind creations and redemptions by authorized participants"
  - "bitcoin and ether ETPs" are named. The vote was 2025-07-29 (the fetch result says "On July 29, 2025").
- arXiv 2312.02752, https://arxiv.org/abs/2312.02752 (abstract, fetch): "up to 66% in some cases--are rapidly sold, often
  in recipients' first post-claim transaction." The abstract says nothing on price impact.
- Lighter points: https://docs.lighter.xyz/points-program/retail returned "Page Not Found". Secondary search snippets
  conflict: one says points are distributed "every Friday", another "every Tuesday". Lighter's points rules are
  UNVERIFIED.
- Hyperliquid points: sources conflict on whether a program runs in 2026. Treat as unverified.

## 4. Candidate 1: airdrop-cliff short (the category M057 left out)

- Hypothesis: a dated cliff of airdrop-allocated tokens of at least 1% of max supply is followed by a fall in the perp from
  D-7 to D, net of cost.
- Opposite: airdrop recipients sold at claim ("rapidly sold, often in recipients' first post-claim transaction", arXiv
  2312.02752). A later cliff adds no fresh supply, so the net return is zero.
- Payer and rule: the airdrop cliff in the contract. Holders are not forced to sell, so this is a weaker payer than an
  insider cliff. Its strength depends on the sale at claim being incomplete.
- Why not known: M057 is limited to insiders/privateSale. R265 used only those categories. M297 is a listing-day share rule
  and UNTESTED. Airdrop cliffs have never been tested as a category.
- Data held: data/recorders/unlocks (forward only, 13 days). Historical calendar: data/unlocks/2026-10-20 is missing from
  this checkout. Counted here (dedup by token, time, type): 489 airdrop unlock rows across 162 tokens in history.
  Dated rows still ahead as of the 2026-11-06 snapshot: 50 rows across 4 tokens.
  - Zest: 9,000,000 on 2026-11-17 = 0.9% of max supply.
  - Re: 7,091,667 monthly, 2026-11-17 to 2027-07-18 = 0.71% each.
  - Based: 56,000,000 on 2027-03-30 = 5.6% of max supply (token mapping ambiguous, see section 2).
  - SpaceFi: a rate change on 2027-02-13 with amount 0.
  - Percentages are my computation from the snapshot's maxSupply field.
- Cheapest decisive observation: 1 hour and 0 euros if the R265 calendar can be found. Filter category == "airdrop", count
  events at or above 1% of max supply, price each D-7 to D on mapped Binance perps (data/markPriceKlines_1h or
  data/klines_1h), cost at 1x/2x/3x. Without that calendar, the test is blocked; the forward snapshot alone gives only 4
  tokens and no sample.
- Kill result: net mean at 2x cost at or below zero, or fewer than about 30 events.
- Value for the French owner: the R265 dose table says 1-2% cliffs gave +1.5% (rounds.csv:83). The in-window events are
  0.7-0.9%, below that band, and Based is one event at 5.6%. Hyperliquid does not hold BASED, ZEST or RE in data/. Deribit
  and Kraken were not checked live. Reachable only through a Binance-listed perp (RE). Value small.
- Probability it is true: 15%. The arXiv sell-at-claim finding suggests the cliff is already sold; only the 5.6% event
  could keep the dose effect alive.

## 5. Candidate 2: Bitwise 10 forced buy at the monthly rebalance

- Hypothesis: names with an approved single-asset ETP (the "Approved Components") gain in the days before the monthly
  rebalance and reverse after it, relative to other names.
- Opposite: the calendar is public (Bitwise posts notices), so arbitrageurs buy first and the move is gone; or the 86%
  intraday trigger seldom fires, so there is no forced flow.
- Payer and rule: "the index will reallocate weight from non-Approved Components to Approved Components" (special meeting
  page, July 14 2025). If the approved share is below 86% at the 12 p.m. ET check, the index rebalances at 4 p.m. ET the
  same day. That is a forced buy at the close.
- Why not known: M222 skipped index additions (methods.csv:223). No row covers Bitwise, COIN50 or CF Benchmarks. The closest
  test is R529 (commodity index roll), whose status conflicts with LESSONS.md:495 (section 1).
- Data held: data/klines_1h and data/spot_1h cover Binance-listed names, enough to measure the window. Not held: Bitwise
  weights, the list of Approved Components, the trigger history, and the notice dates (the notices page is HTML; its API
  was not tested).
- Cheapest decisive observation: 2 to 3 hours and 0 euros. Pull the monthly rebalance dates from the notices page (from
  the first uplisting-era rebalance, unknown date). For each date, compare the 5-day pre-window return of approved and
  non-approved names. Count how many monthly checks crossed the 86% line.
- Kill result: fewer than 12 trigger events, or pre-window abnormal return at or below zero at 2x cost. A trigger that never
  fired is itself the finding: the mechanism is dead.
- Value for the French owner: the forced trade sits in spot names. On perps (Hyperliquid, Kraken, Deribit) the owner can
  hedge only the large names. Expected effect is at most a few basis points per month. Value low.
- Probability it is true: 10%. The calendar is public and arbitrage is cheap; the 87.5% rule may rarely bind.

## 6. Candidate 3: points-period volume clock (a rule-timed volume payer)

- Hypothesis: perp volume on a points venue rises toward the end of each points period and drops after it. The effect is in
  volume and spread, not in price.
- Opposite: farmers trade a fixed size whatever the clock, so volume shows no weekly shape; or no published snapshot exists,
  so no clock can be tested.
- Payer and rule: the venue pays points for volume, and traders pay spread and fees for that volume. The clock is the
  distribution schedule. Lighter's schedule is unverified (section 3).
- Why not known: no methods.csv row on points or snapshots. Lighter's zero-fee work (rounds.csv:111, "Lighter (0/0 fees)";
  rounds.csv:155, R347) tested price and fee, not volume around a points period.
- Data held: data/lighter_trades (trade/, quote/, sessions.csv; listed, not opened), data/lighter_hist, data/aster_hist
  (candles_1d, funding, receipts). Not checked whether these span the season.
- Cheapest decisive observation: 2 hours and 0 euros. Daily Lighter volume by weekday over the held window, with a placebo
  on non-points weeks. Test whether the weekly position of the period end moves volume beyond noise.
- Kill result: no difference by week position (|t| below 2), or the same shape before and after the season ended.
- Value for the French owner: a volume clock is not a return by itself. It would tell the owner when liquidity is thin or
  thick. Lighter is not on the owner's list. Hyperliquid's points status is unclear. Value low.
- Probability it is true: 10%. Points rules are unverified, and volume shapes often disappear once the rule is public.

## 7. Rejected for now

- In-kind creations for spot BTC and ETH ETPs since 2025-07-29 (SEC quote, section 3). In-kind removes cash creation buys.
  The flow data is not held and no public API was tested. Keep for later.

## 8. What was not checked, and the weakest links

- COIN50 rulebook not read (403). Bitwise and CF notices read from fetch summaries, not re-read.
- DefiLlama emissions API is paywalled (402). The only calendar held is forward-only; the R265 folder is missing here.
- Lighter and Hyperliquid points rules: not verified.
- Deribit and Kraken listings: not checked live.
- Housekeeping: I wrote a curl output to /home/user/T/.scratch_none by mistake, then deleted it. Nothing else in the repo changed.
  The only file I created is this one.
