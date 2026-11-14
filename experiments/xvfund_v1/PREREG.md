# PREREG: xvfund_v1 (R470). Cross-venue funding carry on the same US stock perp, trade.xyz against Lighter

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R470
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

Method M527 (new). Family: cross-venue funding carry (R275, R288, R443).

## Question
- trade.xyz (Hyperliquid HIP-3) and Lighter list the same 50 US stock perps. Both are open to French residents
  (`docs/reviews/venue_access_fr_20261110.md`), and neither is authorised anywhere.
- Does shorting the venue that pays more trailing funding, and buying the other, earn more than cash after costs?

## Why now
- **The two venues fund differently.** The 2026-11-11 baseline check (docs/loop/STATE.md) put xyz's stock-perp
  funding near 5.5%/yr and Lighter's TradFi funding near 3.5%/yr. That baseline gap is too small to trade.
  This lane asks whether the dispersion around it is large and lasting enough to pay a taker round trip.
- **Costs are lower than R443's.**
  - R443 (OKX X-Perps against Hyperliquid) lost to costs: 39 bp a round trip and short-lived spreads.
  - Here a round trip costs 9.8 bp at 1x on growth-mode xyz markets: xyz charges 0.9 bp a fill in growth mode and
    Lighter charges nothing.
- **A forward lane could use measured costs.** Both venues' books have been recorded hourly on
  `claude/xyz-books-data` since 2026-11-10.

## What the author has seen
- **Funding and price files that R462, R465 and R466 fetched:**
  - xyz from 2026-08-18 and Lighter from 2026-06-24, both to 2026-11-09;
  - used only inside weekend-fade returns, as the funding paid over a weekend hold.
- **The 2026-11-11 baseline check** of each venue's median funding level. So the sign of the average spread
  (xyz pays more) is expected.
- **One Lighter candle's field names** (AAPL, 2026-11-11), to confirm that `v` is base volume. No statistic.
- **Not computed:** no spread series, no spread dispersion, no carry book and no statistic of this lane.

## Data (fetched after this freeze)
- **Fetcher:** `scripts/fetch_xvfund.py bars --start 2025-11-01T00:00:00Z --end 2026-11-11T00:00:00Z`, writing
  `data/xvfund/` with a per-file sha256 manifest. Provenance goes in `docs/provenance/xvfund.json`.
  - **xyz** (via `lab/carrylane.py`): Hyperliquid `fundingHistory` of `xyz:<COIN>`, every hourly print, and the 1d
    candles.
  - **Lighter:** hourly funding (signed + when longs pay) and 1 h candles, through the paced client.
- **Pairs:** R465's frozen `experiments/ltwknd_v1/universe.csv`: the 50 of R462's US-stock xyz markets that Lighter
  lists under the same symbol. This is today's survivors.
- **Fee tier:** R462's frozen `experiments/xyzwknd_v1/universe.csv` gives each market's xyz growth flag.
  47 of the 50 are in growth mode.

## Rule (constants in `scripts/run_xvfund.py`)
- **Daily axis:** 00:00 UTC.
  - xyz's close at D is the 1d candle opened at D − 1 day.
  - Lighter's close at D is the close of the last traded 1 h bar opened in [D − 3 h, D − 1 h].
  - Quote volume is base volume × close, over the day ending at D.
- **Spread at D:** xyz's funding minus Lighter's, each summed over prints in (D − 7 days, D] and annualized
  (× 365 / 7). Each venue needs its first print at or before D − 7 days.
- **Direction:**
  - A spread of at least +10%/yr shorts xyz and buys Lighter.
  - A spread of at most −10%/yr shorts Lighter and buys xyz.
- **Exits at D, first:**
  - the held direction's spread is below 5%/yr, or missing;
  - a close is missing on either leg for the interval just booked (forced);
  - the two legs' one-day returns differ by more than 20 points (split guard, forced). That interval is booked at
    zero price P&L. A split adjusted on one venue only would otherwise book a fake gain or loss.
- **Entries at D:**
  - Pairs not held and not exited at D, with an absolute spread of at least 10%/yr, both closes at D, and quote
    volume of at least $100k on each venue on the day ending at D.
  - Highest absolute spread first, into free slots. There are 10 slots and no rank exit.
- **Position:**
  - Each slot is short N/10 on one venue and long N/10 on the other. Each leg is margined at 2x, so capital is N.
  - Free slots hold cash earning nothing.
  - Notional is constant. Rebalancing and transfers between venues are not costed.
- **Daily P&L for the interval D − 1 → D, booked at D:**
  - funding: the short leg receives its venue's prints in (D − 1, D] and the long leg pays its own;
  - price: −(short leg's return) + (long leg's return).
- **Costs per entry or exit, both legs, at 1x:**
  - xyz taker 0.9 bp (growth mode) or 9 bp, and Lighter taker 0 bp;
  - plus 2 bp slippage on each fill (R462's 4 bp round trip per market).
  - So growth-mode markets cost 4.9 bp a side and 9.8 bp a round trip, and standard ones 13 and 26.
  - The 2x and 3x reads multiply the total.
- **Hurdle:** 4.0%/yr on capital, flat.
- **Statistic:** daily net on capital minus hurdle / 365. Reported as its annualized mean (points) and its
  Newey-West t at lag 10 (`lab.stats.newey_west_t`).

## Samples and decision (gate 0)
- **A** (days from the first day any pair has a spread to 2026-08-31) decides. **B** (2026-09-01 .. 2026-11-10)
  confirms. The book runs continuously across both, and each day is scored in its sample.
- **INCONCLUSIVE:** A has fewer than 60 days.
- **A passes** when all of these hold:
  - the 1x annualized excess is at least +3.0 points;
  - the NW t is at least 2.0;
  - the 2x excess is above 0;
  - the 1x drawdown is above −5% of capital.
- **Verdicts:**
  - **PASS:** A passes and B's 1x excess is above 0.
  - **PARTIAL:** A passes and B's 1x excess is at or below 0.
  - **NULL:** A fails.
- **A PASS earns a forward lane** under a new id. It would use measured book costs from `claude/xyz-books-data`
  and point-in-time tickets. A NULL closes M527 on this venue pair.

## Power (stated before the read)
- **Yardstick:** R443's long-run daily sd of the excess, 0.138% (crypto, OKX against Hyperliquid). Two perps on the
  same stock should diverge less than that, so this is conservative.
- **If A has about 270 days** (pairs from December 2025): the se of the annualized excess is about
  0.138% × 365 / sqrt(270) ≈ 3.1 points. The MDE (t 2.0, 80% power) is then about 8.7 points.
- **If most pairs list later** and A has 120 days: se ≈ 4.6 points and MDE ≈ 13 points.
- **So A passes only if the carry is large.** An excess of a few points would read NULL here, and that would not
  exclude it.

## Reported, not deciding
- For each sample at 1x, 2x and 3x: annualized net and excess, NW t and drawdown.
- The funding, price and cost parts; the average number of slots held; the daily sd.
- Top-10-day share; exit reasons (spread, missing price, split guard); entries by direction.
- For a forward lane: the detectable excess at 90 and 180 days, from A's sd.

## Trials and reading
- One rule, one trial. Program trials: 9,785,244 before this lane, 9,785,245 after.
- Read against `registry.program_trials()`.

## Limits
- **Survivor universe:** pairs listed on 2026-11-10. Delisted pairs and the order of listings are not modelled
  beyond each venue's first funding print.
- **Assumed costs:** both venues' books were recorded only from 2026-11-10.
- **Fee tier:** growth flags as of 2026-11-10. The dates xyz switched growth mode on are not modelled.
- **Fills:** daily closes on last trades, not marks or fills.
- **Margin:** two venues hold margin separately, and a leg can be liquidated while the other gains. At 2x that takes
  about a 50% move against one leg. Transfers are not costed.
- **Seen windows:** A and B overlap the windows of R462, R465 and R466, whose prices and funding were used in
  weekend returns.

## Code
```inputs
dfba790b96e3945da9c0dec04fd2275ad569114aa89951baf55634eef7408835  scripts/run_xvfund.py
78a3857511f236a4c7380b7a45faf916df808c7d2189338bbecd8d8fc68e3e1c  scripts/fetch_xvfund.py
cfce0ad27202036a69f2557e299d7ed7795e6b6cf2afbd02892047a4e4d818b5  tests/test_xvfund.py
a4d7d0f4dcca6a857c69ca620ce374f118fa70423f236de5b6fedff9bb42bc28  experiments/ltwknd_v1/universe.csv
746d69923e55a68a5fefad555afba4647eac8b41d355b460edaaa73c1f611373  experiments/xyzwknd_v1/universe.csv
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
```

## Stop rules
- One run after the fetch. Nothing is retuned afterwards; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/xvfund_v1/results/`.
