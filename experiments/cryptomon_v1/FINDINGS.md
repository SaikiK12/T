# FINDINGS: cryptomon_v1 (R471), Bitcoin's weekend move and the Monday session of Bitcoin-linked US stocks

**Verdict: NULL.** In A (2020-09 .. 2023-12, 173 sessions after a closure), the slope of the decision names' Monday
session move D_bar on Bitcoin's weekend return W is **+0.057 (HC1 t 0.48)**. The bar was |t| ≥ 2.0. The follow
trade on A's 61 events (|W| ≥ 3%) earns +39.1 bp gross with t 0.54, and in B (2024-01 .. 2026-11, 36 events) it
loses 30.0 bp (t -0.30).

**The open prices the weekend; the session adds nothing steady.** The gap Ḡ on W has slope +0.91 (t 19.6) in A and
+0.99 (t 27.7) in B. The decision names open with about all of Bitcoin's weekend move already in the price. After
the open, the session neither follows nor fades it in a way this sample can tell from zero.

Run: `python scripts/run_cryptomon.py`, 2026-11-12, after the freeze (PREREG sha256 `88459528`, commit `cef29a53`).
- The PREREG verified and its 4 inputs matched; the 15 data files matched their manifests (`results/run.log`).
- The data were fetched after the freeze by the frozen `scripts/fetch_cryptomon.py` (Bitcoin to 2026-11-11, stocks
  2020-06-01 .. 2026-11-12). Provenance is in `docs/provenance/cryptomon.json`.
- **Sessions:** 323 sessions after a closure of at least three days, 2020-09-08 .. 2026-11-09 (173 in A, 150 in B).
  - Rows per name: MSTR 323, MARA 305, RIOT 305, COIN 291; HOOD 276, IREN 260 and QQQ 323 are reported only.
  - The 50% gap guard dropped no row (checked after the read with the guard off).

## Decision samples (decision names MSTR, COIN, MARA, RIOT; direction follow, from A's slope sign)

| sample | sessions | slope D_bar on W | HC1 t | events | gross bp | 1x bp | 2x bp | 3x bp | event t |
|---|---|---|---|---|---|---|---|---|---|
| A | 173 | **+0.057** | **0.48** | 61 | +39.1 | +33.3 | +27.5 | +21.7 | 0.54 |
| B | 150 | -0.286 | -1.44 | 36 | -30.0 | -35.8 | -41.6 | -47.4 | -0.30 |

- **Frozen rule:** A passes only with |t| ≥ 2.0 on the slope and an event mean above 2 units (11.6 bp) gross. The
  slope fails, so the lane is NULL whatever B shows.
- **Cost sensitivity:** one unit is 5.8 bp a round trip (trade.xyz growth mode 2 × 0.9 bp + 4 bp slippage). Costs are
  not what decides here: the event sd is about 560 bp in A and 610 bp in B, a hundred times the unit.
- **Read against the program's 9,785,247 trials:** a NULL needs no deflation.
- **Power was weaker than stated before the read.** The PREREG put the slope's se near 0.065 and the detectable slope
  near 0.18. A's HC1 se is 0.120: the sd of D_bar is 4.9%, not 4%, and the big weekends carry the big session moves.
  So the detectable slope (t 2.0, 80% power) is about 0.34.
  - A's 95% interval is -0.18 to +0.29. A follow drift of 0.3 W or more, or a fade of 0.2 W or more, is unlikely.
  - A smaller drift is not excluded.

## Reported, not deciding

**Gap and session (decision names)**

| sample | slope Ḡ on W | t | slope D on W, W < 0 | t | slope D on W, W > 0 | t | event mean W ≤ -3% (n) | W ≥ +3% (n) |
|---|---|---|---|---|---|---|---|---|
| A | +0.913 | 19.6 | -0.346 | -1.95 | +0.452 | 2.49 | +81.6 bp (21) | +102.4 bp (40) |
| B | +0.985 | 27.7 | -0.802 | -4.32 | -0.338 | -0.91 | +216.0 bp (11) | +51.9 bp (25) |

- **Mourey et al.'s asymmetry is not here in the session.** Negative weekends do not lead to further Monday declines
  after the open. The negative-W slopes are negative: after a Bitcoin fall the names rose during the session on
  average.
- **That B slope (t -4.32) is three crash Mondays** (exploratory, after the read). 2024-08-05 (W -20.5%, D +18.9%),
  2025-04-07 (W -7.9%, D +7.9%) and 2025-02-03 (W -6.9%, D +8.1%) carry it. Without the three sessions with the largest
  |W|, the slope is +0.21 (t 0.59) in B and +0.09 (t 0.34) in A. It is a rebound after market-wide panics, not a
  rule about Bitcoin's weekend. It is one of 18 reported slope cells, and three sessions do not make a lane.
- **Monday gaps partly reverse in B, broadly** (exploratory). D on Ḡ over all sessions is +0.05 (t 0.37) in A and
  -0.28 (t -1.54) in B. For QQQ it is +0.13 (t 1.23) in A and -0.22 (t -2.21) in B. This looks like the known
  overnight-intraday reversal of the cash market more than a crypto effect.

**Each decision name, events signed in the follow direction (bp gross, t, n)**

| name | A | B |
|---|---|---|
| MSTR | +87.8 (1.20, 61) | +22.2 (0.18, 36) |
| COIN | +58.5 (0.93, 47) | +16.9 (0.19, 36) |
| MARA | -31.2 (-0.32, 56) | -78.1 (-0.57, 36) |
| RIOT | +18.6 (0.22, 56) | -80.9 (-0.79, 36) |

**HOOD, IREN and the QQQ placebo** (each on its own sessions)

| name | sample | slope Ḡ on W (t) | slope D on W (t) | follow events bp (t, n) |
|---|---|---|---|---|
| HOOD | A | +0.244 (5.43) | -0.063 (-0.91) | -23.5 (-0.50, 37) |
| HOOD | B | +0.667 (8.47) | -0.255 (-1.74) | -49.5 (-0.57, 36) |
| IREN | A | +0.455 (5.27) | +0.229 (1.47) | +140.1 (1.15, 32) |
| IREN | B | +1.026 (9.41) | -0.756 (-2.90) | -213.4 (-1.36, 36) |
| QQQ | A | +0.075 (4.82) | +0.013 (0.86) | +17.5 (1.43, 61) |
| QQQ | B | +0.170 (5.05) | -0.082 (-3.14) | -19.7 (-1.06, 36) |

- None of the trade.xyz names gives a follow trade with |t| above 1.5 in either sample, and the signs flip between A
  and B.
- QQQ's gap moves +0.08 to +0.17 per unit of W. Its B session slope (t -3.14) has the same sign as the decision
  names' B slope: the B reversal is market-wide, not a crypto-name effect.

## What is closed and what is not
- **Closed for this lane:** a steady drift after Monday's open in Bitcoin's weekend direction (or against it) of
  about 0.2 or more of W, for the four decision names, 2020-2026. Also the 3%-event trade at R462's cost unit.
- **Not tested:** the perps' own price at 09:30 New York (cash opens only), drifts below the detectable slope, the
  first minutes after the open (only open-to-close was read), other crypto names, and the Thursday-to-Friday or
  holiday sessions other than three-day closures.
- **No forward lane is earned.** The frozen rule gives one only to a PASS.
- **M521 stays TESTED (NULL).** Mourey et al.'s full text is still unread [U]. If their effect exists, this read
  says it is in the gap, which trade.xyz's weekend perps already price.

## Limits
- **Survivors:** the names were chosen in 2026, and MARA and RIOT are not on trade.xyz.
- **Yahoo daily bars:** an unofficial endpoint. The raw responses and their sha256 are kept. Opens are the
  consolidated official opens; a perp trader could not have filled at them exactly.
- **Bitcoin from the Binance perp's hourly opens:** W starts at P 16:00 New York. On early-close days (13:00) P's
  close is three hours earlier.
- **Exploratory reads** (the three crash Mondays, D on Ḡ) were made after the frozen read. They decide nothing.
