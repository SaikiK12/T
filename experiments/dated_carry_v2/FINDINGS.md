# R328 — small conditional dated-carry margin; executable net return remains unknown

**PARTIAL.** On the same two committed R327 market snapshots, 162 of 216 registered
terminal scenarios are calculable. An independent Fraction oracle exactly checks
54 hypothetical coin paths, 108 journals and 324 chained rows. Three artifacts
reproduce byte for byte. The other 54 scenarios retain insufficient ETH top-book
depth. **No expected net return, executable edge or new prospective day is established.**

## Economic result

One current snapshot: **2026-10-26 09:00:25.802567–09:00:30.410372 UTC**. The fixed
contracts are BTC-25DEC26 and ETH-25DEC26, versus MEXC spot. Each independent model
account starts with **10,000 USDT**, shorts **250 USD face** and buys its own coins
without borrowing. BTC is the control. Do not add these separate accounts as one
10,000-USDT portfolio. Full/top views are capacity controls on the same two pairs.

The reference world assumes the future delivery index equals today's futures
midpoint, and that the eventual spot USDT sale price divided by that USD index is
one. Neither assumption is a forecast, observed exit or verified USD/USDT parity.
Public fee scenarios use 3.5 bp inverse entry, 2.5 bp dated delivery and the public
spot quote-commission fields. The captured instrument rate of 0.00035 agrees with
the public schedule; it does not prove the owner's fee, debit asset or rounding.

| Full-depth candidate | Model net USDT, 1x | 2x | 3x | Range across nine terminal worlds, 2x |
| --- | ---: | ---: | ---: | ---: |
| BTC control | +1.5221 | +1.1191 | +0.7163 | +0.4492 to +1.8350 |
| ETH altcoin | +0.7434 | +0.3289 | -0.0854 | -0.3557 to +1.0743 |

These are about 1.52/1.12/0.72 bp of the entire 10,000 capital for BTC and
0.74/0.33/-0.09 bp for ETH, over roughly 60 days to December 25. They are not daily
profits or observed returns. At 3x, the registered adverse BTC world leaves only
**0.0926 USDT** before unknown routing costs. ETH's nine-world 3x range is
**-0.7190 to +0.5582 USDT**, with its negative reference result retained.

At 2x, ETH breaks even at a terminal spot-USDT/delivery-USD ratio of 0.99868295:
about 13.17 bp of adverse conversion erases the reference margin. BTC's threshold
is 0.99551847, about 44.82 bp. These are conditional arithmetic thresholds, not
loss probabilities, calibrated bounds or activation rules.

**Transfer, network and withdrawal costs are an optimistic zero floor in these
numbers. Actual routing costs and the subsequent executable exit remain unknown.**
They can erase this small margin. The cash control assumes zero gross return;
alternative cash yield and opportunity cost are not estimated. The same initial
coins held passively use the same capital and spot-cost world, without claiming
matched realized risk or a forecast comparison.

Fixed coin purchases are 0.00309549 BTC and 0.10713 ETH across every cost tier,
fee control and exit world. Their modeled 1x purchase costs are 248.4732 and
249.2908 USDT; the rest of 10,000 remains idle. At 3x those costs are 248.7216 and
249.5431. BTC full/top and ETH full support the fixed quantities. ETH top does not:
its 54 scenarios stay unknown, with no smaller order, replacement coin or leverage-up.

## Accounting and source limits

For short fill faces A_i and prices F_i, the hedge is `a = sum(A_i / F_i)` coins,
not face divided by an arithmetic VWAP. Daily realization keeps the position and
coin cash, resetting its reciprocal checkpoint. Delivery adds only the final
interval and closes the face amount. The same purchased coins are earmarked as
inverse collateral and counted once. There is no fictitious USD principal credit
from shorting the future. Spot principal and quote fees spend cash; inverse entry
and delivery fees reduce coin balances once.

The conditional model is:

`terminalUSDT = [A * (1-d) + (C0-E-a) * X] * R * (1-f)`

Here A is total USD face, C0 initial coins, E entry coin fees, X the delivery USD
index, d the delivery rate, f the spot exit rate, and R the actual spot-USDT price
divided by X. R includes the difference between the 07:30–08:00 delivery TWAP and
subsequent exit, plus venue and USD/USDT effects. Residual reserve coins have price
delta. Unknown X or R leaves actual terminal cash and net return unknown.

Cost tiers stress **entry** spot/inverse crossing and modeled commissions at the
same explicit exit-ratio world. They are not a complete future-exit impact or
latency stress. Index scales 1/2, 1, 2 and conversion ratios 399/400, 1, 401/400
are hypothetical worlds, not a fitted probability distribution. All failures,
negative results and unknowns remain in the artifacts.

The parent source intake used eight bounded static GETs, 1,339,810 accepted bytes
and one search. Its 46 enumerated mechanical scopes are not 46 new strategies.
The formal inverse/fee/settlement and instrument contracts were read; the capped
book-document tail, original 301 and legacy formula-page 404 remain explicit.
The bounded reading did **not** establish full deployed reciprocal-payoff or
coin-fee serialization. This is an independently checked conditional model,
not an exchange cash decoder. Spot units/grid, source effective age, owner fees,
permissions, fills, transfers, margin, liquidation, insurance/socialized loss and
actual delivery/exit remain unverified. Raw copyrighted pages stay in ignored
cache; compact notes, hashes and read/unread scopes are tracked.

## Frozen lineage and verification

- R327 code froze at `eec39c3d5005ad622ee393f8707b9fe72af1e0e5`; raw inputs were
  committed at `cc7c4bf` before reporting. Its ratio-string failure at `f835f0b`
  remains intact: no terminal scenario, journal or result file persisted. This
  was not zero economic cost or a passed numeric oracle.
- R328 froze at `a746d105a9fd2670b2e9241f818a05f17fd057a1`, PREREG SHA
  `39da5b84ee60e5983d2f2a7440922492c9c45f0dc6f2b50a276474da476c543a`, before
  corrected outcomes. Only the registered ratio literal becomes an exact
  Fraction. Original source, code, inputs, clocks, sizes, costs and guards stay intact.
- Full discovery passed **1,394 tests, two skips, 201.426 seconds** before freeze.
  Two new tests cover exact ratio types and the complete finite driver on
  constructed sources. Its 216 invented worlds form one unit check, not new
  market observations. Parent peer reviews retain their limited exact-hash
  scopes: 19 kernel checks, 11 adapter checks and five guard regressions. Reruns
  are not additional independent cases. Whole collector/driver/oracle/physical
  routing and actual payouts were not independently peer certified.
- The separate standard-library oracle consumes raw depth and reconstructs
  inverse **lots**, spot cash, fees, ownership links and every journal chain
  without importing production payoff/account modules. All 162 numeric worlds
  agree exactly; no actual payment or expected return was validated.

```sh
python -m lab account --dated-v2 --out /fresh/output
python scripts/check_dated_carry_v2.py /fresh/output/results.json
```

`results.json` (452,706 bytes), `journals.json.gz` (13,631 bytes) and `audit.json`
reproduce byte for byte with zero network requests. Native journals remain
append-only, with a compact immutable pack tracked. The original `--dated`
retains the R327 failure.

R327/R328 share one compatibility group: 432 planned attempt slots on the **same
two raw market pairs**, not 432 independent chances or four fresh pairs. This
version retains four entry slots, 24 fee/cost cells and 216 terminal slots:
162 computed, 54 uncomputed, 54 constructed coin paths. No predictive or
optimization strategy trial was added; program trials remain **9,478,970**.
M244's full strategy, roll and matched altcoin history remain open/blocked.
M170/R301 NULL, R311 INCONCLUSIVE on 224/273 common days with preselected 2x/3x
losses, R321 NOT_ACCEPTED and frozen owner-100 coverage remain unchanged.

The original current capture used seven HTTP-200 GETs, 5,945 accepted body bytes
and 4.608 seconds. Its durable reservations remain 458,752 bytes and 49 cumulative
seconds, with zero violations or pending requests; no refund, reset or second
collection. Transport/header/proxy bytes are unknown. The historical allowance
remains 7,757/8,000 requests and reported 229.85/250 MiB spent; exact remaining
bytes are unknown. There were no orders, money movements, secret reads, large
downloads, activation, merge/closure or permanent-execution claim. Prospective
strategy scoring still requires its own frozen protocol and on-time evidence.
