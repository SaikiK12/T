# Listing-clocks scout (room 20261126b)

Scope: pre-launch and pre-IPO perps, the switch to a spot or external oracle at listing, and funding during pre-launch.
Venues a French client can reach: Hyperliquid (core and xyz/trade.xyz HIP-3), Aevo. Binance is geo-blocked from this
environment (HTTP 451), so its numbers below are unverified.

## What the lab already holds (read, not re-estimated)
- `registry/methods.csv:268` (M296): "Hyperliquid's hyperp mark is capped at 3x the 8-hour mark EMA and 1.5x the median
  external perp when one exists; a 10x figure in a news summary is contradicted by the docs."
- `registry/methods.csv:268` (M296): "the conversion date is a dated rule-based event to study inside this row, not a new one."
- `registry/methods.csv:269` (M297): post-airdrop supply short, UNTESTED. Not a listing-clock payer.
- `registry/rounds.csv:90` (R271): Binance announcement families, "survivors none".
- `registry/rounds.csv:92` (R272): R271's "pre-listing short 168 h" forward on MEXC paper. Overlaps candidate 3.
- `registry/rounds.csv:296` (R516): "R275's engine cannot enter a pair in its first ~3 weeks". Cross-venue, not the switch.
- `registry/rounds.csv:297` (R517): "R516's supply dried up on Binance+Hyperliquid". Cross-venue, not the switch.
- `docs/reviews/december_decision_20261125.md:71`: trade.xyz lists "10 pre-IPO markets in 2026".
- `docs/reviews/december_decision_20261125.md:97`: "The prediction failed on size. The spread averaged 0.85%".
- `docs/reviews/december_decision_20261125.md:98`: "Cross-venue capital already aligns most pre-IPO pairs."
- `docs/reviews/december_decision_20261125.md:103`: "about **$0.5k a year**" (cross-venue pre-IPO, Fermi).
- `docs/reviews/december_decision_20261125.md:105`: "The recorder already captures every pre-IPO name on four venues."
- `registry/rounds.csv:257` (R470): cost "xyz 0.9/9 bp + Lighter 0 bp + 2 bp per fill" (used as fee reference only).
- Held HIP-3 universe, `data/hip3list/universe.csv`: 160 rows; the pre-IPO names CBRS and QNT are absent (only
  UNITREE appears among them). The held data does not cover the conversions below; the public API pulls are new.

## What the venues say (primary sources, fetched 2026-11-26)
- Hyperliquid hyperps, https://hyperliquid.gitbook.io/hyperliquid-docs/trading/hyperps:
  - oracle: "replaced with an 8 hour exponentially weighted moving average of the last day's minutely mark prices."
  - "The mark price of Hyperps are capped at 3x the 8-hour mark price EMA."
  - "Hyperps with external prelaunch perp listings have mark price capped to 1.5x the median external perp price"
  - "Funding rate premium samples are computed as 1% of the usual clamped interest rate and premium formula."
  - conversion: "shortly after when ABC/USDT is listed on Binance, OKX, or Bybit spot trading"; "ABC-USD will convert
    to a normal ABC-USD perp."
- Hyperliquid funding, https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding: "Funding on Hyperliquid is
  capped at 0.5%/hour." Interest: "predetermined at 0.01% every 8 hours."
- trade.xyz pre-IPO, https://docs.trade.xyz/llms-full.txt (section "Pre-IPO Perpetuals"):
  - "The oracle price is derived from a 30-minute exponentially-weighted moving average."
  - "premium samples are computed as 1% of the standard XYZ perpetual funding calculation." and "This is a funding
    multiplier of `0.005`."
  - conversion: "expected to convert into a normal equity perpetual with external pricing"; "the standard (`0.5`)
    funding multiplier"; "Conversion occurs after the underlying asset begins regular trading".
- Conflict to flag: The Block, 2025-08-27,
  https://www.theblock.co/amp/post/368486/hyperliquid-new-safeguards-following-whale-driven-xpl-pre-market-liquidations:
  "a new hard cap will limit hyperp mark prices to 10x the 8-hour exponential moving average". The current docs say 3x.
  The docs were fetched today; the date of the change is unknown. The lab's M296 already takes the docs as authority.
- Aevo: https://www.aevo.xyz/docs/ returned "None found" for pre-launch, funding, mark or conversion rules. A
  third-party OKX page says Aevo caps pre-launch leverage at 2x; unverified.
- Binance pre-market (search summary only, not fetched): the SOMIUSDT announcement describes funding at "0.005% per
  funding interval since funding interval occurs every 4 hours, because the premium index is unavailable during the
  pre-market trading period." Public Binance futures API returned HTTP 451 "Service unavailable from a restricted
  location" from this environment. I did not attempt to get around it.

## Data I pulled (public Hyperliquid info API; scratch files under the session scratchpad)
- `metaAndAssetCtxs` (core and dex "xyz"): xyz:CBRS onlyIsolated=True, xyz:ANT onlyIsolated=None. The onlyIsolated flag
  is not a conversion marker: several converted names still show True. Do not use it to date conversions.
- `candleSnapshot` 1d and 1h, `xyz:QNT` and `xyz:CBRS`, May-June 2026.
- `fundingHistory`, `xyz:QNT` (500 rows, 2026-05-28 to 06-18) and `xyz:CBRS` (500 rows, 2026-04-30 to 05-21). This
  is hourly funding plus premium. Each call returns at most 500 rows.

## Candidate 1: conversion-hour sign (switch move)
- Hypothesis: the signed move in the conversion hour equals the sign of (hyperp mark minus external price at the
  switch). Opposite: the switch move is noise, unpredictable in sign.
- Payer: the oracle changes from an EMA of the venue's own mark to external pricing (trade.xyz, quotes above). Holders
  with positions into the switch are forced to re-mark at the new price.
- Measured (hourly candles, `h_xyz_QNT.json`, `h_xyz_CBRS.json`):
  - QNT, 2026-06-04: 13:00 UTC close 91.431; 14:00 bar open 91.459, low 70.329, close 82.093, volume 292,314;
    low 57.474 at 20:00. Daily open 97.2, close 59.638 (candleSnapshot 1d).
  - CBRS, 2026-05-14: 13:00 UTC close 298.13; 14:00 bar high 392.42, close 369.85, volume 238,777; 17:00 close
    304.09. Daily close 329.4.
  - Both spikes land in the 14:00 UTC bar. I did not verify the listing time, so the US cash open is an assumption.
- Not measured: the external price at the switch (not held; Binance is blocked here). Sign cannot be tested yet.
- Kill: sign of the switch move unpredictable (hit rate under 60% over at least 8 names), or median |move| under 2%.
- Cheapest decisive observation: 1h candles for the 10 pre-IPO names around each conversion (about 20 public calls),
  plus the first regular-session price of each underlying from a public quote history. About 2 hours of work, 0 EUR.
- Value for a €10k French client: large intraday moves (about 20-35% in the two cases), but the 14:00 bar's volume
  makes the hour's depth unknown to me. Assumed, not measured. About 10 events a year on one venue (line 71).
- Probability 0.2: two cases, and both reversed within 3 hours, so the sign is not visible in these two cases.

## Candidate 2: funding regime change at conversion (premium sign predicts funding sign?)
- Hypothesis: the pre-switch premium sign predicts the post-switch funding sign, because the 0.005 multiplier becomes
  0.5 (100x) at conversion. Opposite: post-switch funding sign is unrelated to the pre-switch premium.
- Payer: the side that was paying the pre-switch premium pays the post-switch funding (trade.xyz quote above).
- Measured (`fundingHistory`, `fund_hist.json`):

| Name | Switch (UTC) | Pre n | Pre mean abs funding %/h | Post n | Post mean abs funding %/h | Post max abs %/h | Pre signed mean premium % | Post hours with funding sign = pre-premium sign |
|---|---|---|---|---|---|---|---|---|
| xyz:QNT | 2026-06-04 14:00 | 163 | 0.00043 | 337 | 0.01347 | 0.1085 | -0.0009 | 0.507 |
| xyz:CBRS | 2026-05-14 14:00 | 324 | 0.00072 | 176 | 0.00522 | 0.0828 | +0.2809 | 0.625 |

- Post-switch signed mean funding: QNT -0.00046 %/h (longs pay 49.3% of hours); CBRS -0.00085 %/h (longs pay 62.5%).
- The mean absolute funding rises 7x to 31x, but the sign is not one-sided and the spikes are large. The premium falls
  (pre mean abs premium 0.72% to 0.28% for QNT; 1.18% to 0.18% for CBRS).
- Check code (run in the session; the inline Python is reproduced here so it can be rerun):

```python
import json, datetime as dt, statistics as st
R = json.load(open(S + '/fund_hist.json'))  # S = scratchpad path
sw = {"xyz:QNT": dt.datetime(2026,6,4,14,tzinfo=dt.timezone.utc),
      "xyz:CBRS": dt.datetime(2026,5,14,14,tzinfo=dt.timezone.utc)}
for c, rows in R.items():
    t0 = sw[c].timestamp()*1000
    pre  = [r for r in rows if r['time'] < t0]
    post = [r for r in rows if r['time'] >= t0]
    pm = st.mean(float(r['premium']) for r in pre)
    pf = st.mean(float(r['fundingRate']) for r in post)
    hit = sum((float(r['fundingRate']) > 0) == (pm > 0) for r in post) / len(post)
    print(c, round(pm*100,4), round(pf*100,5), round(hit,3), len(pre), len(post))
```

- Result: n = 2 names (337 post hours for QNT, 176 for CBRS). Hit rate 0.507 and 0.625. Not established. With two
  names no test of this claim has power; the 0.625 is inside noise for n = 2.
- Kill: hit rate at or below 0.55 on 10 or more names with a sample of 1,000 or more post-switch hours.
- Cheapest decisive observation: `fundingHistory` (public) for the 10 pre-IPO names, paged in 500-row windows around each
  conversion. About 1 hour, 0 EUR.
- Value for €10k: the funding bill for the crowded side can be large in one hour (0.108%/h max, QNT), but the signed
  mean is small (about -4% to -7% a year). Value is in avoiding a crowded book across conversion, not in a carry.
- Probability 0.15: two names and a 0.5 to 0.6 hit rate; funding sign after conversion looks mostly noise.

## Candidate 3: fixed pre-market funding as a payer (Binance; blocked here, overlaps R272)
- Hypothesis: a fixed funding rate of +0.005% per 4 h during pre-market makes longs pay a steady carry, so a short
  collects it while the premium index is unavailable. Opposite: pre-market drift upward (longs buying) exceeds the
  carry, so the short loses.
- Payer: longs, by the fixed rate (search summary, Binance SOMIUSDT, unverified; see above).
- Why not already known: R271 and R272 test the pre-listing short at 168 h on MEXC paper (`registry/rounds.csv:92`).
  The fixed-funding leg is not tested in any round.
- Data: none held. Binance public API is blocked here (HTTP 451). The announcement page is the only other source.
- Cheapest decisive observation: read the announcement history for a list of pre-market perps (public page, not the
  API), and count how many carried the +0.005% template. About 2 hours, 0 EUR.
- Kill: fewer than 10 pre-market listings with the fixed template, or the pre-market price drift exceeds the carry in
  most cases.
- Value for €10k: 0.005% per 4 h is about 0.03% a day, about 0.2% over a 7-day pre-market. Small against costs.
- Probability 0.1: the carry is too small to clear fees; the venue may not be reachable for the client (owner to check).

## Scouting notes
- The brief's framing of a forced convergence to a known price at a known time does not hold on Hyperliquid. The hyperp
  oracle is an EMA of its own mark, and conversion is tied to a CEX spot listing, not to a date.
- The Hyperliquid pre-IPO funding multiplier change (0.005 to 0.5 per trade.xyz) is the one documented regime change
  at conversion, and Candidate 2 tests it.
- Not checked: Hyperliquid's `perpDexs` `assetToStreamingOiCap` (open-interest caps on xyz) as a forced-flow lever.
  Retrieved, not analysed.
