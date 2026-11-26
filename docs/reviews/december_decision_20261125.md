# What each December read will trigger, decided before any read (2026-11-25, reflection cycle 12)

- **Why now.** A decision made after seeing a result is made under its influence. Self-review 3 ranked this second
  among the unasked items.
- **What this file is:**
  - the dated forecasts of cycle 8;
  - the evidence since then: the decay of about 30% a year, the non-Kraken pairs at about zero in 2026, the stake
    rule checked on the real mixed account;
  - a fixed mapping from each read's outcome to the stake the lab will propose.
- **What it is not.** The frozen PREREGs are unchanged. Their "what a PASS earns" sets a ceiling (at most $2,000,
  leverage at most 2.5). This file chooses inside that ceiling and can only be stricter.
- **The owner places every order** (`AGENTS.md`).

## 1. What a stake can earn now (the money arithmetic, written first)
- **The base is the autumn 2026 level of the Kraken + Hyperliquid book,** not the whole year:
  - about 1% a month at 1x, gross of the halving (cycles 7-8);
  - halved for Thorp, 6% a year at 1x;
  - at the stake's leverage (Kraken 1.5x, Hyperliquid 1.5x), about 9%;
  - minus venue-failure cost (about 2% a year of the stake), 7%;
  - after the 31.4% flat tax, about 4.8%;
  - minus euro cash after tax (about 1.5%), **about +3.3% a year over cash.**
- **On €2,000 that is about €65 a year.**
  - **Corrected the same day** (room critic, verified on `experiments/xfund_eea_v1/FINDINGS.md:85`): R508's real costs are
    2-3x its 1x assumption, so the figure is about **€40-50 a year**. The decision is unchanged.
- **The first stake is a calibration, not an income.** It measures:
  - real fills against paper;
  - real funding against the recorded funding;
  - the transfer burden between the two accounts;
  - the tax paperwork.
- **The step to €10,000 needs a measured forward edge of at least about 5% a year after decay** (the stake note's
  bar). At the current trend, that bar may never be met. I state that now so a pass is not read as a promise.

## 2. The mapping (fixed; changing a row needs a written reason dated before the read)
| Read (date) | Its own rule | If it passes | If it fails or stays "not yet" |
|---|---|---|---|
| **R523** (about 12-13 / 12-23): Kraken+HL and Deribit+HL combined, fund_book | NW t ≥ 3.0, cumulative net > 0 | Propose a stake on **Kraken + Hyperliquid only**. Deribit + Hyperliquid's net was about 0 in 2026 (cycle 8), and a funding-only pass does not change that | No stake from this read; R510 still decides the Kraken sleeve |
| **R527** (about 12-15 / 12-25): three floorless venues combined | NW t ≥ 3.0, cumulative net > 0 | The same as R523, Kraken + Hyperliquid only. It adds no Bitfinex or Deribit leg | As R523 |
| **R510** (about 12-19 / 01-03): Kraken+HL, fund_book, fast | NW t ≥ 2.5 and cumulative net_book > 0; FAIL if mean ≤ 0 or R509's kill switch | **Stake 1:** €2,000 on Kraken + Hyperliquid (details below) | FAIL: no Kraken stake. The money case waits for R509's 90-day look (about February 2027). NOT YET: wait for its second look |
| **R521** (about 12-22 / 01-06): Deribit+HL, fund_book, fast | NW t ≥ 2.5, cumulative net > 0 | **No stake on this pass alone.** Funding-only reads exclude the price legs, which took the 2026 net to about 0. Wait for R520's 90-day look | Nothing changes |
| **R509, R512, R520, R524** full looks (90 and 180 scored days, February to May 2027) | per PREREG | Scale decisions, at the bar of §1 | A FAIL of R509 or its kill switch ends any Kraken stake |

- **If R523 or R527 passes before R510 decides,** the stake is proposed then, at the same size. R510 is not waited
  for; the three are correlated reads of the same Kraken book.

## 3. Stake 1, specified now
- **Size:** €2,000 in all, split by `scripts/stake_ticket.py` between Kraken (EEA derivatives) and Hyperliquid.
  - Euro collateral on Kraken where its multi-collateral accepts it (`answers_20261124.md` §3).
- **Leverage:**
  - Kraken account 1.5x only at the EEA 5% maintenance, otherwise 1x;
  - Hyperliquid account at most 1.5x.
  - Checked on the real mixed account (cycle 11): worst intraday loss 4.4% of notional, against 59% room.
- **Margin mode:** cross on both accounts, never isolated per leg (R280: isolated legs are liquidated by single-coin
  pumps even at 1x). Checked 2026-11-25: none of R508/R509's coins is isolated-only on Hyperliquid.
- **Daily checks:**
  - each account's net long share (above 60% of gross, apply the long-alt distance);
  - distance to liquidation on each venue's mark;
  - funding received against the recorded funding.
- **Stops:**
  - the stake is closed at a 25% loss of the stake (gate 4 proposal);
  - or at R509's kill switch (cumulative net_book below −3%);
  - or if the realized net is below +0.5% a month for two months running (the regime-adjusted decay made visible).
- **Review:** monthly, against the regime-adjusted trend (`scripts/check_gap_trend.py`). Not quarterly: at −30% a
  year, a quarter is a tenth of the rent's life.

## 4. What I will score afterwards
- **The forecasts of cycle 8:** R510 0.60, R509 0.45, R512 0.40, R523 0.45, R527 0.40, R521 0.30, R520 0.10,
  R524 0.10.
- **Whether the mapping above was followed** without a later rewrite.

## Addendum, the same cycle: pre-listing perps, counted (cycle 9's next step)
- **trade.xyz's Pre-IPO Specification Index** (`llms-full.txt`, fetched 2026-11-24) lists 10 pre-IPO markets in
  2026:
  - eight already converted at their listing: CBRS 05-14, QNT 06-04, SPCX 06-12, SKHY 07-10, CXMT 07-27, UNITREE 08-14,
    SHEIN 09-01, JIO 10-02 (anticipated dates);
  - two live: OURA (anticipated 10-28) and ANT, Anthropic (anticipated 11-20, grace to 2027-01-19).
  - That is about 10 conversion events a year on one venue.
- **The same names trade on other venues.** Anthropic is on xyz (ANT), Lighter (ANTHROPIC, a 1-billion-share unit
  that "uses the scaled ANT share price (× 17.615235684)" after the IPO), and two other HIP-3 dexes (io:ANTH,
  para:ANTH). The lab's book recorder holds all four, hourly, since 2026-11-11. No question has used them.
- **Prediction, written before looking:**
  - The xyz/Lighter spread for Anthropic, after the 17.615 scaling, averages more than 2% and moves by several %.
  - The reason: before the IPO nothing converges the venues except cross-venue capital, which faces split margin
    and an uncertain listing date. At the listing both reference the same share price, so the spread must close.
  - Below about 0.5%, the cross-venue variant is already arbitraged, and the class is a curiosity.
- **Observed** (recorded hourly books on `claude/xyz-books-data`, 2026-11-11 .. 11-25; 346 common hours):

  | Name | Venues | Ratio, median (min .. max) | Mean \|spread\| | Path |
  |---|---|---|---|---|
  | Anthropic | Lighter / (xyz × 17.615) | 0.9912 (0.9719 .. 1.0202) | 0.85% | daily median −1.41% to −1.49% through 11-16, −0.96% on 11-18, **−0.31% on 11-19, about 0 from 11-20** |
  | Anthropic | para:ANTH / xyz:ANT | 0.9988 (0.9906 .. 1.0296) | — | — |
  | Oura (not yet listed) | Lighter / xyz | 1.0001 (0.9929 .. 1.0033) | 0.08% | flat |

- **Anthropic listed on Nasdaq on 2026-11-19** (priced $83, opened $111.50, first close about $97.17; news reports,
  e.g. Al Jazeera, Fox Business, TechRepublic). The cross-venue spread closed that day.
  - That is the mechanism in one clean event: at the oracle switch both venues reference the same share price.
  - A pair long Lighter and short xyz through the pre-IPO week would have earned about 1.4% before costs.
- **The prediction failed on size.** The spread averaged 0.85%, not over 2%, and Oura's venues sat within ±0.1%.
  Cross-venue capital already aligns most pre-IPO pairs. Anthropic's 1.4% was the exception and closed at the
  listing.
- **Fermi** (step 4: capacity, the owner's capital, decay):
  - about 10 conversions a year on xyz; a spread worth trading on perhaps a third of them; about 1% gross a pair; a
    pre-IPO book of maybe $5k a side;
  - about **$0.5k a year**.
  - A curiosity for now, by the criterion written first.
- **Kept as a watch, not a lane.** The recorder already captures every pre-IPO name on four venues. A cross-venue
  spread above about 2% on a name with a dated listing is the trigger to look again. The next names are OURA and,
  on Lighter, OPENAI.

## Addendum 2026-11-26 (written before any December read): tail rules for stake 1
From `docs/reviews/reflection_20261126_tail.md` (strand 2).
- **Venue failure is the binding risk.** Keep on Hyperliquid only the margin its legs need at 1.5x, plus 25%.
- **Leverage:** Hyperliquid at 1.5x or less (ADL priority).
- **On any ADL, forced settlement or Kraken delisting of one leg,** close the other leg within the same hour.
- **Before the stake goes live, build the watch script (T1).** It reads the public Hyperliquid fills and Kraken's
  instrument list hourly.
- The mapping in §2 is unchanged.
