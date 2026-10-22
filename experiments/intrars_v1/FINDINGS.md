# FINDINGS: intrars_v1 (R300). The day's leaders reverse early and keep leading after the US open, but not by enough to pay a daily round trip

**Verdict: NULL.** M318 is TESTED.
- **Trials:** 24, gate 0 on seen data.
- **Read:** frozen PREREG 47548a76, committed and pushed in b2fc3aa before the run. Run 2026-10-22 08:18 UTC with
  `scripts/run_intrars.py`.
  - All 10 inputs matched their frozen hashes.
  - It loaded 499 coins' bars (`bars_digest` 6be8ab9e…).
- **Program trials** after this round: see "Read against the program".
- **The pick fails.** The best discovery book is us10 n3 follow: at 10:00 New York, long the 3 strongest top-50
  perps since 00:00 UTC and short the 3 weakest, flat at 24:00 UTC.
  - Discovery t +1.88. Validation net +38.7 bp/day, t +1.28 against the 2.0 bar.
  - Without its 10 best days the validation mean is −3.3 bp/day.

## What was tested
Linda Raschke on stocks: the day's relative-strength leaders keep leading into the close. Here that means:
- **Universe:** the top 50 Binance perps by trailing 30-day volume at each decision.
- **Signal:** each coin's move since 00:00 UTC.
- **Decision hour:** 1, 2, 4, 8 or 12 h after 00:00 UTC, or 10:00 New York on NYSE days ("us10").
- **Books:** long the n strongest and short the n weakest (follow), or the reverse (fade), with n = 3 or 5. Flat at
  24:00 UTC.
- **Costs and funding:** API 8.5 bp per side at 1x. The book is entered and closed daily, so the cost is 34 bp/day at
  1x. Funding is paid and received.
- **Placebo clocks:** eight random clocks (the day starting at another hour), reported only.
- **Windows:** discovery 2021-01..2023-12, validation 2024-01..2026-09.

## Result

**The pick: us10 n3 follow (bp/day; t is Newey-West, lag 5)**

| Window | Gross (t) | Net 1x / 2x / 3x | t at 1x / 2x / 3x | Median day, gross | Without best 10 days (1x) | Best 10 days' share (1x) | Sharpe (1x) | Long leg | Short leg | Basket |
|---|---|---|---|---|---|---|---|---|---|---|
| Discovery | +68.6 (+3.73) | +34.6 / +0.6 / −33.4 | +1.88 / +0.03 / −1.81 | +32.3 | +8.7 | 75% | 1.21 | +62.6 | +6.1 | −2.0 |
| Validation | +72.7 (+2.41) | +38.7 / +4.7 / −29.3 | **+1.28** / +0.16 / −0.97 | +47.9 | **−3.3** | 108% | 1.00 | +33.5 | +39.2 | +1.2 |

- **The checks:**
  - t ≥ 2.0 at 1x: **fails** (+1.28);
  - a positive 2x mean: passes (+4.7);
  - a positive mean without the 10 best days: **fails** (−3.3).
- **The gross is steady.** It is positive in every calendar year: 64, 93, 49, 48, 58 and 126 bp/day in 2021-2026, on
  187-252 NYSE days a year. Net at 1x it is positive in every year too (+14 to +92).
- **But it is noisy.** The daily gross has a standard deviation of about 650 bp. A 5% trimmed mean keeps +61 bp/day,
  but at 1x the 10 best days carry most of the net.
- **The edge moved legs.** In 2021-23 it was in the leaders (long excess over the basket +64.5 bp/day). In 2024-26
  it was in both: the leaders +32.3 and the laggards +40.4.
- **Break-even** is 17.2 / 18.2 bp per side (discovery / validation), twice the API 1x cost. At 2x it is about zero;
  at 3x it loses.
- **Scale:** the Sharpe uses √365 per book day. us10 trades about 250 days a year, so √250 gives about 0.8 in
  validation. +38.7 bp per NYSE day is about +97%/yr on one unit per leg, at about 100% annual volatility.

**All 24 books (bp/day; t at net 1x)**

| Book | Gross disc / valid | Net 1x discovery (t) | Net 1x validation (t) | Validation 2x / 3x |
|---|---|---|---|---|
| k1 n3 follow | −43.5 / −33.0 | −77.5 (−3.48) | −67.0 (−1.67) | −101.0 / −135.0 |
| k1 n3 fade | +43.5 / +33.0 | +9.5 (+0.43) | −1.0 (−0.03) | −35.0 / −69.0 |
| k1 n5 follow | −50.1 / −4.3 | −84.1 (−5.20) | −38.3 (−1.28) | −72.3 / −106.3 |
| k1 n5 fade | +50.1 / +4.3 | +16.1 (+1.00) | −29.7 (−1.00) | −63.7 / −97.7 |
| k2 n3 follow | −35.8 / +25.3 | −69.8 (−2.92) | −8.7 (−0.25) | −42.7 / −76.7 |
| k2 n3 fade | +35.8 / −25.3 | +1.8 (+0.08) | −59.3 (−1.71) | −93.3 / −127.3 |
| k2 n5 follow | −39.0 / +11.0 | −73.0 (−3.85) | −23.0 (−0.88) | −57.0 / −91.0 |
| k2 n5 fade | +39.0 / −11.0 | +5.0 (+0.26) | −45.0 (−1.72) | −79.0 / −113.0 |
| k4 n3 follow | −3.9 / +27.0 | −37.9 (−1.54) | −7.0 (−0.20) | −41.0 / −75.0 |
| k4 n3 fade | +3.9 / −27.0 | −30.1 (−1.23) | −61.0 (−1.79) | −95.0 / −129.0 |
| k4 n5 follow | +13.8 / +31.0 | −20.2 (−1.21) | −3.0 (−0.11) | −37.0 / −71.0 |
| k4 n5 fade | −13.8 / −31.0 | −47.8 (−2.87) | −65.0 (−2.33) | −99.0 / −133.0 |
| k8 n3 follow | +49.9 / +37.5 | +15.9 (+0.76) | +3.5 (+0.11) | −30.5 / −64.5 |
| k8 n3 fade | −49.9 / −37.5 | −83.9 (−4.02) | −71.5 (−2.22) | −105.5 / −139.5 |
| k8 n5 follow | +29.9 / +34.2 | −4.1 (−0.28) | +0.2 (+0.01) | −33.8 / −67.8 |
| k8 n5 fade | −29.9 / −34.2 | −63.9 (−4.31) | −68.2 (−2.92) | −102.2 / −136.2 |
| k12 n3 follow | +47.3 / +35.5 | +13.3 (+0.78) | +1.5 (+0.06) | −32.5 / −66.5 |
| k12 n3 fade | −47.3 / −35.5 | −81.3 (−4.76) | −69.5 (−2.80) | −103.5 / −137.5 |
| k12 n5 follow | +36.2 / +23.6 | +2.2 (+0.18) | −10.4 (−0.48) | −44.4 / −78.4 |
| k12 n5 fade | −36.2 / −23.6 | −70.2 (−5.68) | −57.6 (−2.65) | −91.6 / −125.6 |
| **us10 n3 follow (pick)** | +68.6 / +72.7 | +34.6 (+1.88) | +38.7 (+1.28) | +4.7 / −29.3 |
| us10 n3 fade | −68.6 / −72.7 | −102.6 (−5.58) | −106.7 (−3.53) | −140.7 / −174.7 |
| us10 n5 follow | +43.0 / +30.6 | +9.0 (+0.65) | −3.4 (−0.12) | −37.4 / −71.4 |
| us10 n5 fade | −43.0 / −30.6 | −77.0 (−5.58) | −64.6 (−2.22) | −98.6 / −132.6 |

### The sign turns over the day
- **The first hour's leaders reverse.** In discovery k1 follow grosses −44 to −50 bp/day, so k1 fade grosses +44 to
  +50. That is the atlas's direction (R185). In validation the fade is worth +4 to +33 bp/day gross, under the 34 bp
  cost.
- **The 2 h and 4 h anchors are mixed:** they reverse in 2021-23 and lean to continuation in 2024-26.
- **From 8 h on, the leaders keep leading.** Every k8, k12 and us10 follow book grosses +24 to +73 bp/day in both
  windows. Only us10 n3 clears 34 bp/day in both.
- **Three names beat five** at every late anchor. The extreme names carry the effect.

### Placebo clocks: 00:00 UTC is not special; the US morning may be
Each clock runs the 20 k-anchored books with the day starting at o:00 UTC (us10 has no placebo).

| Clock (day starts) | Highest discovery t | Its pick | Pick's validation net 1x (t) |
|---|---|---|---|
| **00:00 (real)** | 1.00 | k1 n5 fade | −29.7 (−1.00) |
| 01:00 | 2.41 | k12 n3 follow | +3.1 (+0.10) |
| 06:00 | 1.61 | k8 n3 follow | +9.9 (+0.26) |
| 08:00 | 2.46 | k8 n3 follow | +84.6 (+2.37) |
| 11:00 | 1.60 | k4 n3 follow | +78.5 (+1.93) |
| 12:00 | 1.56 | k4 n3 follow | +79.2 (+1.81) |
| 14:00 | 0.82 | k1 n3 follow | −17.6 (−0.38) |
| 15:00 | 0.70 | k1 n3 follow | +26.8 (+0.73) |
| 21:00 | 0.38 | k12 n3 follow | +25.3 (+0.91) |

- **The real clock ranks 6th of 9** on its highest discovery t, and **last** on its pick's validation. This is R290's
  answer again: the UTC day start carries no special structure.
- **Post hoc, not a test:** the three clocks whose pick decides at 15:00-16:00 UTC (08:00 + 8 h, 11:00 + 4 h,
  12:00 + 4 h) all earned +78 to +85 bp/day net in validation, t 1.8-2.4. The 08:00 clock's pick would have passed
  all three checks.
  - With us10 (14:00-15:00 UTC), that is four books deciding in the US morning, all continuation.
  - The placebo clocks are controls. Nothing here was picked from them, and they are not trials.
- **SPA over the 24 books against cash:**
  - discovery p 0.224, best book the pick;
  - validation p 0.593, best book the pick.

  Neither window rejects "no book beats cash".

## What this does and does not show
**It shows, for the top 50 Binance perps in 2021-2026:**
- Ranked from 00:00 UTC, the first hour's movers reverse and the late-day leaders continue. Neither pays 34 bp a day
  reliably.
- The best book (us10 n3 follow) grosses about +70 bp/day in both windows and in every year, with a heavy right tail.
  It fails the t bar and the tail check in validation.
- The 00:00 UTC clock is no better than random clocks for this rule.

**It does not test:**
- **Cheaper execution.** The break-even is about 17-18 bp per side. A maker entry or the zero-fee MEXC contracts
  would change the arithmetic; R193 found maker fills adversely selected on the atlas cells.
- **Anchors in the US morning** other than us10. The placebo pattern is a lead for unseen data, below.
- **The atlas's per-tier fade** (top 10, rank 11-25, 1-12 h holds). This lane ranked all 50 names and held to
  24:00 UTC.
- **MEXC prices,** and whether pumped coins could be shorted.

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side, which is 34 / 68 / 102 bp/day: the book turns over twice a day.
- **No book is positive at 2x except the pick** (+4.7 bp/day, t 0.16). None is positive at 3x.
- **The cost decides this family.** Every k8-us10 follow book is positive gross in both windows; only one clears 1x.

## Read against the program
- **Program trials:** 9,478,649 after R299 (12) and R300 (24) (`registry.program_trials()`).
- **24 trials, one pick, one validation read.** The pick's validation t of 1.28 is far from any bar.
- **SPA:** p 0.224 and 0.593 per window.
- **The gross t of 2.41 in validation is not evidence of a tradable edge.**
  - It is the gross of a book picked on discovery's net, among 24.
  - It sits below a 34 bp/day cost.
- **Power, written before the run:** a pick with a true annual Sharpe of 1.0 had 37% power. This pick's observed
  validation Sharpe is about 0.8-1.0, so a NULL here is the expected outcome even if the effect is real.

## Next
- **M318 is TESTED and NULL** in this form (00:00 UTC anchor, top 50, held to 24:00 UTC, API costs).
- **Queued as M319, for unseen data only:** relative strength into the US morning continues.
  - **Rule fixed now** (the 08:00 placebo clock's pick): at 16:00 UTC, long the 3 strongest top-50 perps by their
    move since 08:00 UTC and short the 3 weakest, held to 08:00 UTC the next day.
  - **Where it can be read:** the 2020 reserved sample (batch 2; batch 1 is frozen) or forward paper days. Never
    2021-26 again.
  - **Source:** the four US-morning books above, picked after seeing them. It must be judged at its own cost and
    with this lane's trial count disclosed.
- **The early-hour fade (the atlas's direction)** decayed from +40-50 to +4-33 bp/day gross between windows. No new
  lane.
