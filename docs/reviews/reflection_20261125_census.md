# Reflection, 2026-11-25 (cycle 9 of rule 11): can the design-gap class grow? A census of funding designs

## How I approached the last subject, and what I would change
- **Cycle 8 concluded "the product is the pipeline":** each rent decays about 30% a year, so the lab must find new
  ones early. I named "new venues, new listings, new margin regimes" without checking that new floorless venues
  exist.
- **What I would change:** before searching for new members of a class, ask whether the class can have new members.
  That means asking who sets the rule, and why they would set it differently. This cycle does that.
- **Why the funding family is on the table a third session:** the money case rests on it, and the question is
  whether its pipeline exists. If the answer is no, the lab leaves the family for its pipeline work.

## 0. What the lab already knows
- **Mapped:**
  - floorless: Kraken (premium only), Deribit (±0.025% dead zone), Bitfinex (±0.05% dead zone), dYdX (cross markets
    default 0);
  - floor: Binance, Gate, KuCoin, Hyperliquid, Aster.
  - HIP-3 dexes differ per deployer: xyz 0.5, Felix 0, Dreamcash about 0. R518 found that gap thin against costs.
- **Not mapped:** the new perp venues of 2025-26.
- Lighter's and Paradex's fees were in `docs/VENUE_STRUCTURE.md`; their funding rules were not.

## 1. The census (primary sources: each venue's documentation, fetched 2026-11-25)
| Venue | Crypto funding rule | Interest term | Interval | TradFi / RWA |
|---|---|---|---|---|
| Extended | (P + clamp(0.01% − P, ±0.05%)) / 8, paid hourly | 0.01% / 8 h | 1 h | interest 0.0035% / 8 h (about 3.8%/yr) |
| edgeX | P + clamp(I − P, ±0.05%) | I from quote and base borrow indices | 1 h settlement, 4 h window | — |
| Paradex | clip(mult · (Prem + clip(0.01% − Prem, ±0.05%)), ±max), EWMA. Prem is a **weighted median of impact premia across Paradex, Binance, Bybit, OKX, Hyperliquid and Lighter** | 0.01% / 8 h | continuous | multiplier 0.5 |
| Drift (docs now at velocity.exchange) | (dead-zoned, ramped premium + an always-on offset) / 24; 5 bp dead zone | offset **raised from 7.3% to 10.95%/yr** | 1 h | — |
| Variational | P + clamp(I_8h − P, ±0.05%), within a floor and cap | I_8h | 1-8 h | **interest 0%** for RWA perps |
| Lighter | premium · multiplier + clamped interest | 0.01% crypto | 1 h | about 0.0032% (many RWA); 0 for FX, US10Y, STRC |
| Hyperliquid (validator perps) | P + clamp(0.01% − P, ±0.05%) | 0.01% / 8 h | 1 h | xyz ×0.5 |

- **Every new venue copies the floor.** That covers Extended, edgeX, Paradex, Drift, Variational, Lighter, Aster and
  Hyperliquid. Drift even raised its floor in 2026, to the industry's 10.95%.
- **Floorless designs survive only at legacy venues:** Kraken, Deribit, Bitfinex and dYdX v4's cross markets.
- **Lower or zero interest terms exist only for TradFi/RWA perps,** where the venues aim at SOFR-like carry:
  Variational 0%, Lighter about 0-3.5%, Extended 3.8%, xyz and Paradex half the floor.
- **One new design: Paradex sets its funding premium from other venues' books** (a weighted median).
  - Its own book's premium moves its funding only when Paradex sits in the middle of the venues.
  - So a local Paradex premium is corrected by price convergence, not by funding.
  - Not a rent by itself, but a row for the map.

## 2. Why every new venue copies the floor (the mechanism, as a hypothesis)
- **The floor is a subsidy from directional longs to whoever is short by default:** market makers carrying
  inventory, and basis traders who are long spot and short the perp.
- **A new venue needs those liquidity providers before it has users.** A floor that pays shorts about 11% a year in
  calm markets attracts them, so new venues keep it.
- **A floorless venue's customers are different:** hedgers, regulated retail (Kraken's EU offer), options-driven flow
  (Deribit). Those venues have no reason to add the subsidy.
- **What this predicts:**
  - the design-gap class has a fixed membership;
  - its rent decays as cross-venue capital grows (cycle 8);
  - no new floorless crypto venue is coming to replace it.
- **Assumption:** the LP-subsidy motive is my reading, not a venue's statement. The census itself is the observed
  fact.

## 3. What it changes
- **The design-gap family is a decaying asset with no pipeline.** Its remaining money is the Kraken thin-coin sleeve
  plus whatever Kraken and Deribit list next. Each new thin listing on a floorless venue is a small fresh rent.
- **The lab's pipeline must come from other classes:** markets where demand is new and arbitrage capital has not yet
  arrived, so He et al.'s θ grows faster than W.
  - **24/7 equity perps** (the closed-market family, R530). Hyperliquid's HIP-3 open interest reached an all-time
    high of $3.1B in June 2026: demand growing.
  - **Pre-listing perps: pre-IPO stocks and pre-launch tokens.** The oracle switches from internal to external at
    the listing. The lab holds four 2026 IPO transitions on xyz (CBRS 05-14, QNT 06-05, SPCX 06-12, SKHY 07-10)
    and M296 (pre-launch crypto perps, untested; R271/R272 on Binance pre-market notices). A cross-venue variant (the
    same pre-IPO name on xyz, Lighter and Variational, converging at the IPO) has not been looked at.
  - **Outcome markets** (Hyperliquid HIP-4, live 2026) carry new demand. They are not mapped.
- **The map gains two rows:** the funding census (in the funding row) and pre-listing perps.

## 4. The cheapest decisive observation, for the next cycle
- **Pre-listing perps: count the events before anything else** (the "count the chances" lens).
  - Pre-IPO perps across xyz, Lighter, Variational and Paradex since 2025.
  - Pre-launch token perps (Hyperliquid hyperps, Lighter prelaunch, Binance pre-market) since 2025.
  - For each event: the last internal price, the first external price, and the cross-venue spread before the
    switch.
- **If fewer than about 20 events a year,** the class is a curiosity, not a sleeve.
