# Inventions room, 2026-11-25 (inventor)

Scope: ten candidate venue-rule mechanisms (capacity rents), each checked against the lab's registry before proposal.
Read-only on the repo; no journal files opened; no runs; no orders. Labels: [R] repo path:line or registry id,
[W] web source read this session, [I] my inference, [U] unverified.

## 0. Method and what I read
- Read: `docs/reviews/approach_20261124.md`, `docs/reviews/mechanism_map.md` (both in full).
- Registry checks (run 2026-11-25):
  - `grep -i -E "<pattern>" registry/methods.csv registry/rounds.csv` for each candidate, with the output trimmed to ids and status.
  - Patterns used: unbond|unstak|LST|withdrawal queue|stETH; stablecoin|redeem|depeg|USDC|USDT; prediction market|polymarket|kalshi;
    index rebal|rebalanc|index fund; pre-market|pre-launch|pre-IPO|hyperp; tokenized|RWA (word-bounded; the unbounded
    "rwa" matched "forward", which I corrected); unlock|vesting|cliff; heartbeat|deviation threshold|Chainlink (0 hits);
    option expiry|max pain|expiry pin; Aave|Morpho|Compound|Euler|bridge|challenge period|UMA (see the results per candidate).
- Intake and data checks: `research/intake/venue_yield_20261120.md` (read lines 1-45), `research/intake/idea_wave6_20261111.md`
  (xStocks EEA line), `research/intake/oracle_frontiers_20261125.md` (line 27), `data/defillama/manifest.json` (perps mapping only).
- Primary-source web reads (WebSearch, standard mode, 2026-11-25):
  - Lido withdrawals help center and lido.fi/how-lido-works/withdrawals: normal wait 1-5 days, FIFO queue, wait depends on
    queue size, validator exit rate and buffer ETH; the stETH:ETH rate is fixed at finalization (help.lido.fi, 7858315; lido.fi).
  - Polymarket docs (docs.polymarket.com/concepts/resolution): anyone may propose an outcome and anyone may dispute it, through UMA's
    Optimistic Oracle. The bond (about $750) and a 2-hour challenge come only from third-party guides [U].
- A direct fetch of docs.lido.fi/contracts/withdrawal-queue returned HTTP 404; the contract-level rule is not yet read [U].

## 1. Registry verdict per candidate (grep results)

| # | Candidate | Registry hits (id, status) | Intake / data hits | Verdict |
|---|---|---|---|---|
| 1 | LST / restaking unbonding-queue discount | none for unbond, unstak, withdrawal queue, stETH, LST (the only hit is M505, a perp-DEX vault row) | none | **NEW** |
| 2 | Stablecoin primary-redemption gate (par redemption closed to retail) | M189 UNTESTED (USDT peg to next-day market), M192 BLOCKED (supply z-score), M535 / R488 (USDe flow) | `usde_flow_20261113.md` | **PARTIAL**: peg covered, the mint/redeem gate is new |
| 3 | Prediction-market resolution-dispute rent (UMA) | M291 BLOCKED (No-bias price band), M098 BLOCKED (archive not acquired) | none | **PARTIAL**: price band covered, the dispute mechanism is new |
| 4 | Lending utilisation kink (borrow APY jumps above 80%) | M478 (benchmark rate) | `venue_yield_20261120.md` already reads the kink formula and measures it (2.65% supply on Hyperliquid PM) | **DUPLICATE** (intake) |
| 5 | Aave-type liquidation bonus | none for Aave, Morpho, liquidation bonus | `research/intake/README.md:257` (aave_v3_liquidation_event_contract_20261023), SRC26-011 read | **PARTIAL** (intake) |
| 6 | Tokenized-equity premium over NAV (xStocks, Ondo GM, Backed) | M449 (cross-venue funding carry on tokenised RWA) and M491 BLOCKED (ETP premium to NAV) | `idea_wave6_20261111.md:111`: Kraken xStocks not available in the EEA [V] | **PARTIAL**: the spot-token premium is not in the registry; access is a barrier |
| 7 | Canonical L2 withdrawal-delay premium (fast bridge vs 7-day exit) | none for bridge, withdrawal delay, challenge period | none | **NEW** |
| 8 | Pre-launch token perps | M296 UNTESTED, M501, R271/R272 | `mechanism_map.md` pre-listing row | **DUPLICATE** |
| 9 | Option expiry pin / settlement window | M289, M303, M317, M440 (all present) | `data/option_expiry` | **DUPLICATE** |
| 10 | Crypto index reconstitution flow | M494 BLOCKED, M462, R389, R529 (NULL, roll front-run) | none | **DUPLICATE** |

Note on the registry: M494 and M291 were the closest hits, but both are blocked on data, not tested. Blocked is not
null. A registry verdict on a family is not a verdict on its mechanism.

## 2. The non-duplicate candidates (1, 2, 3, 6, 7, and 5 in part)

### Candidate 1. Unbonding-queue discount on liquid-staking tokens (NEW)
- **Economic question.** Does a rule that makes exit slow (a FIFO withdrawal queue) make holders pay a discount to sell
  early, and does that discount close when the queue clears?
- **Mechanism.** Holders who need ETH now must sell stETH on the secondary market instead of waiting in the queue.
  - Who must trade: holders forced by liquidity needs (collateral calls, fund redemptions). This is the Celsius case
    in the web results: "784m stETH in Lido's long withdrawal queue" (cointelegraph headline, undated in this session) [W].
  - Constraint: FIFO order, queue length, validator exit rate, buffer ETH [W, help.lido.fi/7858315].
  - Price set by: secondary market (stETH/ETH), with the redemption rate fixed at finalization [W].
- **Barrier.** Queue arbitrage needs capital that can sit in the queue for days, plus a way to claim. Large LST desks
  do this, so the rent should be thin unless the queue is very long.
- **Fermi, EUR 10k owner.**
  - Assumed discount when the queue is more than 3 days long: 0.5% [I, not measured].
  - Events a year: 3 to 6 [I].
  - Capture at 30% of the discount: 0.005 × 0.3 × 10,000 × 4 = about EUR 60 a year [I].
  - Capacity: the discount is set by the secondary market's depth, so it is large in principle; the owner's own size is the cap.
- **Our edge.** Only the reading of the queue state, and the owner's own small size. Weak.
- **Cheapest decisive observation.** Two series: (a) Lido withdrawal-queue backlog and claimable time, over time, from the
  Lido contracts or the stake.lido.fi interface (not in `data/`; to fetch, small); (b) the stETH/ETH secondary price, from
  DefiLlama coins API or a DEX pool (not in `data/`; `data/defillama/manifest.json` holds perps TVL only).
- **Kill.** The secondary discount stays under about 20 bp even when the queue is over 3 days long, or the discount
  does not correlate with queue length over six months.

### Candidate 2. Stablecoin primary-redemption gate (PARTIAL: peg covered, gate new)
- **Economic question.** When par redemption is closed to most holders (KYC-gated mint and redeem), does the secondary
  price fall below par, and is the gap paid by retail who cannot redeem?
- **Mechanism.** A stablecoin's par is enforced only by holders who can redeem. Retail cannot redeem, so retail sells at the
  market price; the discount is the price of the gate [I].
- **Barrier.** Primary redemption requires institutional KYC; the owner cannot take the arbitrage [I, to verify against
  the issuer's terms, not read this session].
- **Fermi.** A 5 bp dislocation on EUR 10k is EUR 5 an event [I]; events are rare for the major coins. Capacity is small for the owner.
- **Cheapest decisive observation.** The USDT-USD peg series that M189 already names (its data is `data/coinbase`, UNTESTED).
  Read it before any new data.
- **Kill.** Peg deviations under 5 bp in the last two years, or none outside the usual market-stress days.
- **Verdict.** Low capacity for the owner. Included because it is a rule, and because the registry has no mint-redeem row.

### Candidate 3. Prediction-market resolution-dispute rent (PARTIAL: price band covered, dispute new)
- **Economic question.** While a contested outcome is in dispute, do traders holding the disputed side pay a price for
  waiting, and is there a rent for those who can hold through the vote?
- **Mechanism.** [W, docs.polymarket.com/concepts/resolution] Anyone may propose an outcome and anyone may dispute it, through
  UMA's Optimistic Oracle. [U, third-party guides] The bond is about $750; a dispute reopens the request; disputes go to a
  UMA token-holder vote; a 2-hour challenge period.
- **Who must trade.** Holders of the disputed side who need the cash back early.
- **Barrier.** Access for a French retail client is not confirmed [U]; check `docs/reviews/venue_access_fr_20261110.md`
  (not read this session). Also the M291 HN point: the time value of money is the sure side's cost.
- **Fermi.** A dispute costs the bond ($750) and lasts hours to days [U]. A rent of 2% on a EUR 500 position over a
  week is EUR 10 an event [I]; the count of disputes a year is not measured.
- **Cheapest decisive observation.** Count disputed markets and their price moves inside the dispute window from the
  public Polymarket APIs (not held in `data/`; M098 is blocked on the archive, but resolved-market prices may be public).
- **Kill.** The price moves inside a dispute window are within the spread, or disputes are fewer than about 10 a year.

### Candidate 6. Tokenized-equity premium over NAV on spot tokens (PARTIAL)
- **Economic question.** Do tokenized stocks (Backed xStocks, Ondo GM) trade at a premium to the underlying's close on
  weekends, and who pays it?
- **Mechanism.** Holders buy tokens at a premium because they cannot buy the stock out of hours; the premium closes only
  through primary issuance (authorised minting), which needs institutional access [I].
- **Barrier.** Kraken xStocks are not available in the EEA (`research/intake/idea_wave6_20261111.md:111`) [V in that note].
  The owner's access to Backed or Ondo is not checked [U].
- **Fermi.** Premium of 0.3% on a weekend round trip on EUR 10k is EUR 30 a weekend at full capture [I]; realistic capture small.
- **Cheapest decisive observation.** The token's DEX price versus the US close, over weekends, from DEX pool data (not in `data/`).
- **Kill.** Premium under the round-trip cost; or the lab's R462 closed-market result already explains it (it does: the
  weekend fade is the same family, `mechanism_map.md`). This is a partial duplicate of the 24/7 perp family and should
  be read as a spot-token instance of it.

### Candidate 7. Canonical-bridge withdrawal-delay premium (NEW)
- **Economic question.** A rollup's standard exit waits a challenge period (commonly 7 days on Optimism and Arbitrum) [U,
  from background knowledge; not read this session]. Do fast third-party bridges charge a premium that holds only while
  the wait lasts?
- **Mechanism.** Users who need L1 ETH now pay the fast bridge's fee; the fee is set by its liquidity and the wait.
- **Barrier.** Bridge liquidity providers with capital that can wait; competition makes the premium thin [I].
- **Fermi.** Premium of 0.1% on EUR 10k, one or two trips a year: EUR 10 to 20 a year [I].
- **Cheapest decisive observation.** Fast-bridge quotes against the canonical wait, from a bridge's public quote API (not held).
- **Kill.** The fee is under the gas cost, or the quoted discount is below 5 bp.

### Candidate 5. Aave-type liquidation bonus (PARTIAL, intake)
- Covered in intake (`research/intake/README.md:257`, SRC26-011 read). Not a new registry row; the bonus is the rule.
  Speed is the barrier (MEV bots take it first) [I]. Not pursued here.

## 3. Ranking (top 3 by expected value per hour of work)

1. **Candidate 1 (LST unbonding discount).** New; the data is free and small to fetch; the rule is primary (Lido FAQ).
   Expected value: about EUR 50-100 a year for the owner [I], with an hour of data work. Unverified: the queue history and the discount.
2. **Candidate 7 (canonical-bridge withdrawal premium).** New; a quote-API read of one hour; expected value about EUR 10-20 a year [I].
3. **Candidate 3 (prediction-market resolution-dispute rent).** New mechanism, partly covered by blocked rows; access unconfirmed.
   Expected value unknown; the count of disputes is the first measurement.

All three are small for a EUR 10k account [I]. The honest reading: none is a breakthrough for the owner's size; each is a cheap
decisive test of whether a new rule creates a rent.

## 4. What I did not check (weakest links)
- The Lido contract-level rule (docs.lido.fi withdrawal-queue page returned 404); the figures are from help-center pages.
- The Polymarket bond and challenge period (third-party only).
- The owner's venue access for each candidate (`venue_access_fr_20261110.md` not read).
- Every Fermi figure is my assumption, labelled [I]; none is measured.
- No data pulled; no journal file opened; no run executed.
