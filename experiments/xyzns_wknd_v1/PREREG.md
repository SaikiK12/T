# PREREG: xyzns_wknd_v1 (R464). Do trade.xyz index, commodity and FX perps overshoot over the weekend?

- **Registry id:** R464
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11)
- **Date registered (UTC):** 2026-11-11

Method M520, from idea wave 6 (2026-11-11, `research/intake/idea_wave6_20261111.md`). It moves R462's frozen
weekend fade (M515) from trade.xyz's US-stock perps to its US equity-index, commodity and FX perps. Parents: M515,
M447, M188, M321, R432, R459 and R462. This file is frozen by `lab.prereg.freeze()` before any price of these 14
markets is fetched or read for this question. After the freeze it is never edited; a changed idea is a new lane.

## Question
trade.xyz (Hyperliquid HIP-3) prices 14 non-stock markets from a reference: CME-style index futures, metals spot,
energy futures and spot FX. Each reference closes on Friday (17:00 New York; Brent 18:00) and reopens on Sunday
(18:00; FX 17:00). In between, the perp has no external price. The oracle "initializes from the last available
external price" and runs a 30-minute EMA of the perp's own book.

When the reference reopens, does the perp give back part of its weekend move? Does fading that move from one hour
before the reopen to two hours after it pay more than a round trip at the market's fee?

## Why this lane
- **R462 found the effect on the stock perps.** Its gate 0 passed: a fade from Sunday 19:00 to 22:00 earned +42.4 bp
  per market-weekend before costs in sample A (Holm p 0.004) and +36.2 bp in B. R463 now tests it forward.
- **Same venue, same mechanism, different markets.** The oracle rule above is trade.xyz's generic one
  (`llms-full.txt`, sha256 `7ac7ef34dec6e080…`, read by the author on 2026-11-11):
  - FX: "Internal pricing is used from Friday 5:00 PM to Sunday 5:00 PM ET, or at any time there is a gap of more
    than 30 seconds between external oracle datapoints."
  - Indices and commodities: external prices 23/5, "from Sunday 6:00 PM ET to Friday 5:00 PM ET". No separate
    weekend rule is written for them; the generic rule applies.
  - Brent's row in the Specification Index says "Friday 6PM ET". The commodities page says 5 PM. This lane uses the
    Specification Index row for each market.
- **Cost.** 13 of the 14 markets ran in growth mode on 2026-11-11: 0.9 bp per taker fill. GOLD is excluded from
  growth mode by trade.xyz's rule ("Perps tracking gold"), so it pays 9 bp.
- **Outside evidence (vendor-side).** Blockworks for the Hyperliquid Policy Center (2026-08-03; "commissioned by
  Hyperliquid Policy Center"; read by the author on 2026-11-11):
  - 614 market-weekends across 68 TradeXYZ markets, 2026-03-13 to 2026-07-03, each with at least $1M of weekend
    volume. The report does not say which markets; some of the 14 here may be among them.
  - The reopening move (dependent variable: the median external print 5-10 minutes after the reopen) regressed on
    the final internal weekend move has slope 0.834 (interval 0.73-0.93), intercept -15 bp.
  - A slope below 1 means the reopen moves less than the perp did: the perp gives back about a sixth of its weekend
    move. The report is gross of fees.
- **The lab's own prior is mixed.** R432 (Binance TradFi perps on QQQ, SPY, gold, silver, WTI, Brent and gas) found
  fade slopes of -0.12 / -0.18 / -0.26 at the CME reopen + 15 min, + 60 min and the cash open. Its primary cell was
  NULL at a 12 bp cost unit. Binance's weekend pricing differs from trade.xyz's.

## What the author has seen
- **xyz market names, growth flags and fee scales** (`meta`, dex xyz, 2026-11-11).
- **The trade.xyz Specification Index**, sessions, holiday closures and fee rules (`llms-full.txt`).
- **R451** held xyz hourly closes for GOLD, SILVER, CL, BRENTOIL and SP500 for 2026-09-30 .. 2026-11-11 (sample B's
  period) and computed flow-book returns from them. The author never computed a weekend move, a Sunday price or a
  reopen move from those files.
- **The commodity-perp recorder** (`scripts/record_commodity_perps.py`, M447) has held xyz oracle, mark and mid for
  some of these markets since 2026-10-28. It was never read for this question.
- **R432's results** on Binance's perps of the same underlyings over overlapping weekends (above). This lane is
  therefore a venue transfer, not independent of the underlying weekends' news.
- **R462's result** on the xyz stock perps and the wave 6 helper reports.
- **No xyz price, weekend move or return of these 14 markets has been computed or looked at.**
- The rule and runner were run only on synthetic worlds (`tests/test_xyzns.py`), including a planted overshoot and a
  world without one.

## Universe (`experiments/xyzns_wknd_v1/universe.csv`, frozen)
Built by `python scripts/fetch_xyz_ns.py universe` on 2026-11-11 from names and sessions only.

| class | markets (API coin) | Friday close | Sunday reopen |
|---|---|---|---|
| index | SP500, XYZ100 | 17:00 | 18:00 |
| metal | GOLD, SILVER, PLATINUM, PALLADIUM, COPPER | 17:00 | 18:00 |
| energy | CL (WTIOIL), NATGAS, HO (DIESEL) | 17:00 | 18:00 |
| energy | BRENTOIL | 18:00 | 18:00 |
| fx | EUR, GBP, JPY | 17:00 | 17:00 |

- **`growth`:** growthMode on 2026-11-11: "enabled" for 13 markets, blank for GOLD.
- **Excluded:** the Asian and Indian index perps (JP225, KR200, NIFTY) and the Asian stocks, which follow other
  sessions; and the US stocks and funds, which are R462's.
- **Survivorship:** markets delisted before 2026-11-11 are absent.

## Samples
- **A, decides.** Weekends with a Friday from 2026-05-01 to 2026-09-25: 18 weekends (R462's span).
- **B, confirms.** Fridays from 2026-10-02 to 2026-11-06: 6 weekends.
- **Skipped weekends:** R462's rule (`xyzwknd_rule.weekend`):
  - a Friday that is not an NYSE trading day, or is an early close;
  - a Monday that is not a trading day.
  - In these spans it drops 2026-05-22, 2026-06-19, 2026-07-03 and 2026-09-04. These are also the trade.xyz futures
    holiday weekends in the spans.
- **Bars:**
  - Hyperliquid `candleSnapshot` 1 h and `fundingHistory` for each `xyz:<coin>`, over 2026-04-01 to 2026-11-10
    00:00 UTC.
  - Fetched **after this freeze** by the frozen `scripts/fetch_xyz_ns.py bars` into `data/xyz_ns`, with a per-file
    sha256 manifest and a provenance record.
  - The API serves only the most recent 5,000 candles, so the earliest bars are from mid-April 2026.
- **Eligibility:** a market-weekend counts when the market's first candle is at least 7 days before R and both P(R)
  and P(E) exist.

## The rule (`scripts/xyzns_rule.py`)
All times New York.
- **Instants per market:**
  - R = Friday close of the reference (the last external print);
  - O = Sunday reopen of the reference;
  - E = O - 1 h (entry);
  - X1 = O + 2 h;
  - X2 = Monday 10:00 (diagnostic).
- **P(T), W, s, c_k, f_k and g_k exactly as R462** (`xyzwknd_rule.event_row`):
  - P(T) is the close of the last hourly candle that opens in [T - 3 h, T - 1 h], else missing;
  - W = 1e4 ln(P(E)/P(R)); s = -sign(W), the fade side; W = 0 is dropped;
  - c_k = s × 1e4 ln(P(X_k)/P(E));
  - f_k = -s × 1e4 × (hourly funding settled in (E, X_k]);
  - g_k = c_k + f_k, the return before trading costs.
- **Groups:** `all`, `index`, `metal`, `energy`, `fx`.
- **Thresholds:** |W| ≥ θ, with θ in {0, 25, 50, 100} bp. These markets move less than single stocks; the Blockworks
  report found direction poorly predicted below 25 bp.
- **Test:** R462's two-sided sign-flip randomization test of mean g = 0.
  - Signs are flipped together within each weekend.
  - 200,000 draws, seed 464. `cluster_flip_p`, `holm` and `mde80` come from `scripts/earnperp_rule.py`.
- **Decision cells** (sample A, X1 only, Holm over the two p values):
  - D1: `all`, θ = 25 bp;
  - D2: `all`, θ = 50 bp.
  - X1 only, because R462's Monday exit was noise (sd 381 bp), and Monday 10:00 is not a reopen for these markets.

## Trials
- Cells: 5 groups × 4 thresholds × 2 exits = **40**, each read in A and in B. B adds no hypothesis.
- Registry trials: 40.
- Program trials: 9,785,102 before this lane, 9,785,142 after.

## Decision
The trade direction is the sign of the cell's sample-A mean: fade if positive, follow if negative.
- **PASS:** a decision cell meets all of these:
  - at least 60 events over at least 10 weekends in A;
  - a Holm p of at most 0.05;
  - |mean| above 2 cost units, so the 2x net is positive;
  - in B: at least 20 events over at least 4 weekends, the same sign, and |mean| above 1 unit.
- **PARTIAL:** the same cell has the A sample sizes, a Holm p of at most 0.05, |mean| above 1 unit, and the same sign
  in B with B's sample sizes.
- **INCONCLUSIVE:** neither decision cell has the A sample sizes.
- **NULL:** otherwise. The best state of the two cells is the lane's verdict.
- Read against 9.8 million program trials, any hit is weak. A PASS or PARTIAL earns a forward paper lane on xyz with
  measured book costs, never a trade.

## Costs (1x, 2x, 3x)
- **One cost unit is a round trip (R462's unit):**
  - growth-mode markets: 2 × 0.9 bp + 4 bp of slippage = **5.8 bp**;
  - GOLD: 2 × 9 + 4 = **22 bp**.
  - The 4 bp slippage is an assumption: these books were not recorded before 2026-11-11.
- Funding is charged inside g from the recorded hourly rates.
- The 1x, 2x and 3x nets subtract 1, 2 and 3 units from |mean|.

## Power (stated before the run)
- MDE80 = 2.8 sd / sqrt(n), reported for every cell; the cluster test is wider.
- At most 14 × 18 = 252 market-weekends in A, fewer above θ.
- Assumption: a weekend-level mean fade return with an sd of about 25 bp across weekends. With 18 weekends, the
  lane detects about 17 bp, against a 2x cost of about 12-16 bp.
- R462's effect size (+42 bp) would be seen. An effect the size of R432's slopes (a sixth of a 60 bp median |W|,
  about 10 bp) would likely be missed. A NULL here does not rule that out.

## Code
```inputs
ae8a014b5d1ae4456c5cce21bfe707f0f862a4fe80fe2c9ec40bdaaeefb3f488  experiments/xyzns_wknd_v1/universe.csv
5134509d43290d4ea32138c8cff52f610aeda6495b1f4fd5cc4633638b91e998  scripts/xyzns_rule.py
dfd43da9c687aa8ec99a07c1f73a579a3ba58226a49a94b42294faa8012f86e1  scripts/run_xyzns.py
55c83ef7d872d213b43519d1e34d52b1e1f8e30521b4341388f2ffa4e8369dd0  scripts/fetch_xyz_ns.py
af9ddf4ee7a95a806a1457a3c75edf399da05258f95697771cb23c0ebb6b9642  tests/test_xyzns.py
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a  scripts/xyzwknd_rule.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
374365de7ca4b1fe9e527b3a4fab5feef1b3d447ee2905f5a51d2b2341e191d4  scripts/fetch_xyz_wknd.py
6a9c4286ac1a12a391c0ebaca022510fb40d59affff9eb56ce71d44246a64ca1  scripts/earnperp_rule.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
```
The runner also re-hashes every bar and funding file against `data/xyz_ns/manifest.json`.

## Feature lineage and point-in-time availability
- **W and s.** Source: xyz trades before R and E (candle closes). Available at E. Point-in-time. Missing data: the
  event is dropped and counted.
- **Growth mode (the cost unit).** Source: `meta` on 2026-11-11. Not point-in-time for earlier weekends; a market
  charged 5.8 bp may have paid more then.
- **Sessions (R, O).** Source: the Specification Index on 2026-11-11. No dated change to commodity or FX closed
  hours was found in the changelog; a change before 2026-11-11 would misplace R or O for earlier weekends.
- **c_k and f_k.** Source: candle closes before X_k and funding settled in (E, X_k]. Outcome only.

## Evidence lineage and admission
- **Method:** M520. **Parents:** M515 and R462 (the stock-perp fade), M447 (re-anchoring at the CME reopen), M188 and
  M321, R432 (Binance, NULL primary) and R459 (oil on Lighter, forward).
- **Decision group:** M520 on xyz prices; one verdict from the two pre-named cells.
- **Samples:** no xyz weekend price of these markets was ever read. B's period overlaps R451's closes for 5 markets.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: pre-named cells; Holm over 2; 40 cells counted; costs at 1x/2x/3x; power stated; a later confirmation sample.
  - Not met: gate 1 (a forward, on-time sample on the trade venue with measured costs) and gate 3 (account risk). The
    result stays exploratory.

## Stop rules
- The lane ends with its first complete run on A and B. Nothing is retuned afterwards: no other instant, threshold,
  group, cost or sample. A changed idea is a new lane.
- **A PASS or PARTIAL earns** a forward paper lane under a new id, with tickets frozen at E, xyz book costs and its
  own PREREG with at least 15 weekends before any verdict. R463's pinned files are not edited for it.
- **A NULL closes M520 in this form.** The class and other-θ cells are diagnostics and do not reopen it.
- No orders, no money, no credentials. The run reads files and writes `experiments/xyzns_wknd_v1/results/`.
