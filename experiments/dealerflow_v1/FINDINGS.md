# FINDINGS: dealerflow_v1 (R292). Dealer gamma from Deribit taker flow says nothing about the next day's volatility or autocorrelation; the hedge it implies is too small next to perp volume

**Verdict: NULL.** M308 is TESTED.
- **Trials:** 4, gate 0.
- **Read:** frozen PREREG 94c1d1c6 (committed in 246efd0 before the run), run 2026-10-22 02:47 UTC,
  `scripts/run_dealerflow.py`.
  - 9 inputs, and all 258 Deribit flow files, matched their frozen hashes.
- **Program trials** after this round: 9,478,572 (`registry.program_trials()`).
- **No trades:** a mechanism check only.

## What was tested
**The claim** (the owner's term list; options-flow tools such as QuantData's GEX):
- dealers long gamma damp the market: lower volatility, mean-reverting returns;
- dealers short gamma amplify it: higher volatility, trending returns.

**The estimate:**
- **Positions:** every Deribit BTC and ETH option trade since 2016 (41M trades) carries the taker's side. An
  option's net taker buying since its first trade is the takers' position, and the makers ("dealers") hold the
  opposite.
- **Dealer GEX** at each UTC close = Σ (−taker position) × gamma × F² × 0.01, in USD per 1% move.
  - Gamma is Black-76 at the option's last traded IV.
  - **g** = GEX / the perp's 30-day mean daily volume.
  - **short** = 1 when GEX < 0.
- **Targets on the next UTC day,** Binance BTC and ETH perps:
  - log realized variance (5-minute path), against a HAR base;
  - the hourly return autocorrelation.
- **Windows:** fit on 2021-04..2023, read on 2024..2026-09.

## Result

| Test | Discovery | Validation | Bar | Pass |
|---|---|---|---|---|
| Volatility, g | coef +40.4 (BTC), +3.7 (ETH): the wrong sign | DM t **−1.23**, MSE −0.84% | DM t ≥ 2.5, MSE cut ≥ 1%, coef < 0 | no |
| Volatility, short | coef −0.063 (BTC), +0.010 (ETH) | DM t −0.52, MSE −0.07% | the same, coef > 0 | no |
| Autocorrelation, g | t **+2.67** (the wrong sign) | t −0.06 | validation t ≤ −2.5, same sign | no |
| Autocorrelation, short | t +0.87 | t −0.82 | validation t ≥ +2.5, same sign | no |

- **Out of sample, adding dealer gamma to the HAR makes the volatility forecast slightly worse** in both forms.
  - The HAR alone explains 52% (BTC) and 45% (ETH) of next-day log variance in 2024-26.
  - Gamma adds nothing to that.
- **In discovery, both gamma coefficients point the wrong way:** more dealer long gamma came with more volatility
  and more trending hours the next day. Neither held up in validation.

### Why: the hedge is small
- **Dealers are short gamma almost all the time.**

  | | Share of short-gamma days | Median GEX per 1% move | Median g (share of a day's perp volume per 1% move) |
  |---|---|---|---|
  | BTC 2021-23 | 87% | −$6.8M | −0.05% |
  | BTC 2024-26 | 82% | −$20.1M | −0.13% |
  | ETH 2021-23 | 76% | −$2.4M | −0.03% |
  | ETH 2024-26 | 92% | −$5.7M | −0.05% |

  Customers on Deribit buy options on net, so the makers who sell to them carry negative gamma.
- **The hedge is a rounding error next to perp volume.**
  - At the median for BTC in 2024-26, a 5% move asks for about 0.65% of a day's Binance perp volume in hedges. On
    the 10% most-short days it is 1.7%.
  - The implied volume is about $15B a day. The equity story rests on dealers' hedges being
  large next to stock volume. In crypto they are not, at least on this venue and with this estimate.
- **Netting makes the estimate far smaller than the gamma dashboards show.** On 2026-10-21 the lab's chain recorder
  read about $630M of BTC gamma notional per 1% from open interest (calls plus puts, gross). The net taker
  position's gamma is a few percent of that. Open-interest GEX treats every open option as dealer-held, while most
  of it nets out between buyers and sellers. This is an order-of-magnitude comparison across different dates.
- **The gamma state barely moves.** With dealers short on 76-92% of days, the "short gamma" flag carries little
  information.

### By tercile of g (cuts from discovery, pooled over coins)

| Tercile | Next-day HAR residual, discovery | Validation | Next-day hourly autocorrelation, discovery | Validation |
|---|---|---|---|---|
| Low (dealers most short) | −0.037 | −0.035 | −0.044 | −0.038 |
| Mid | −0.015 | +0.000 | −0.021 | −0.015 |
| High (least short or long) | +0.052 | −0.039 | −0.014 | −0.029 |

- **Nothing monotone survives** into validation.
- **Hourly returns mean-revert a little on every kind of day** (mean ac −0.01 to −0.04), whatever the gamma state.

### Variants (reported, not decided on)

| Variant | Vol DM t | Vol MSE cut | ac t, discovery | ac t, validation |
|---|---|---|---|---|
| g without block trades | +1.12 | +0.47% | +3.19 | +0.58 |
| short without block trades | +0.79 | +0.29% | **−2.53** | **−2.62** |
| g without options expiring within 24 h | −1.12 | −0.82% | +2.70 | +0.08 |
| short without options expiring within 24 h | −0.96 | −0.14% | +0.55 | −1.23 |

- **Leaving out block trades** brings the volatility forecast closer to zero, but still below every bar.
- **Post hoc, against the story:** without block trades, days when screen makers are short gamma are followed by
  more mean-reverting hours, at t −2.5 in both windows.
  - The story predicts the opposite sign.
  - It is one of 8 reported variant looks, picked after reading them all.
  - It is logged as a seed for unseen data, not as a finding.

## What this does and does not show
**It shows,** for 2021-2026, that net taker flow on Deribit's BTC and ETH options, read as dealer gamma:
- does not improve a HAR forecast of the next UTC day's perp volatility;
- does not sign the next day's hourly autocorrelation out of sample;
- implies hedge flows of a fraction of a percent of perp volume per 1% move.

**It does not test:**
- **The open-interest GEX that public dashboards show** (equity convention: dealers long calls, short puts). The
  lab's chain recorder holds that from 2026-10-21 only.
- **Other venues:** OKX, Bybit, Binance and CME options, and Deribit's USDC options.
- **Intraday horizons:** hedging around 08:00 UTC expiries, or a pin at large strikes. R289's Friday settlement
  reversal is the intraday lead, and `charm_expiry_v1` is queued for it.
- **Whether makers are dealers.** That is the assumption, and a NULL cannot tell a wrong assumption from a missing
  effect.

## Costs
No trades, so no costs. A pass would have earned a trading lane with API costs.

## Read against the program
- 4 trials, each against t 2.5 (Bonferroni over 4).
- No test came within reach of the bar out of sample (best validation |t| 1.23).
- The program's 9.48M trials do not change a NULL.

## Next
- **M308 is TESTED (NULL).** Dealer gamma from taker flow does not enter the queue as a regime input.
- **Still open from the same data:**
  - **M311:** Deribit block prints leading the perp (`blocks_v1`);
  - **M313:** signed option premium ("net drift") leading the perp;
  - `charm_expiry_v1` (R289's Friday reversal against expiring gamma).

  Each needs its own frozen PREREG.
- **Post hoc seed** (screen-only short gamma and more mean-reverting hours): read only on data after 2026-09, in a
  frozen forward lane, if it is ever wanted.
