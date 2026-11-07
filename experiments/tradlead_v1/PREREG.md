# PREREG: tradlead_v1 (R261). Does the last hour of TradFi perps lead crypto?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R261 (claimed on issue #7)
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_tradlead.py`
- **Queue:** M004 (TradFi commodity/equity perps' 1 h return leads the crypto cross-section, next 1-24 h). It is a
  proxy for the "news moves TradFi first" claim (rDbW, World Monitor), not the claim itself.
- **Gate:** 0 (screen). **All data used here lies inside the program's spent holdout** (2025-07 onward), because
  Binance's TradFi perps start in 2025-12. So the result is exploratory at program level. A pass can only queue a
  forward paper lane under a new id.

## What the author has seen
- **R216 (venue_gap_v1):** TradFi perps exist in the archive from 2025-12. They carried 49% of book A's gross on an
  18-day forward replay, and about 0 on the archive. That was about the flow books, not about a lead.
- **Before writing this:** the archive's coverage of the leaders, their hours of finite returns, and that no
  eligible crypto coin has a missing return in 2026-01..09. No return, correlation or book on this question has been
  computed.
- The general fact that crypto co-moves with the NASDAQ on some days. Nothing on lead-lag at 1 h in 2026.

## Leaders (fixed by category, before any statistic)
- **CMD:** XAUUSDT, XAGUSDT, CLUSDT, BZUSDT.
- **EQ:** QQQUSDT, NVDAUSDT, TSLAUSDT, INTCUSDT, MUUSDT, MRVLUSDT, SNDKUSDT, NBISUSDT. These are unlevered US
  stocks or ETFs that are not crypto-linked.
- **Excluded:**
  - DEFIUSDT and BTCDOMUSDT: crypto indices.
  - MSTRUSDT and CRCLUSDT: crypto-linked.
  - KORU, MUU, SOXL, SOXS and SNXX: leveraged or inverse.
  - SAMSUNG, SKHYNIX, SKHY, EWY and DRAM: Asian hours or unclear underlying.
  - SPCX: unclear underlying.

## Signal (row t is known at the close of row t; `u.ret[t]` is the return over the next bar)
- **Leader return:** L[t] = the mean of `u.ret[t]` over the leader's members with a finite value. Lk[t] = L[t-1] is
  the leader's return over the bar that ends at row t's close.
- **z[t]** = Lk[t] / the standard deviation of Lk over rows t-719..t (at least 240 finite values).
- **Trigger:** |z[t]| >= 1.
- **Crypto universe:** `u.elig` coins that are not in R216's `tradfi_symbols.json`.

## Books
Each trigger at row t opens a slice held for rows t..t+H-1, with H in {1, 4, 24}. Positions are the sum of open
slices times 1/H.
- **TS (market timing):** each slice is d x sign(z[t]) units of the equal-weight crypto market, weighted 1/n over
  the coins eligible at each row.
- **XS (beta cross-section):**
  - beta[t, s] is the OLS slope of coin s's return over the bar ending at row k on Lk[k], for k in t-719..t. It
    needs at least 240 pairs.
  - e[t, s] = beta[t, s] x Lk[t], computed over eligible crypto coins with a finite beta. A trigger row needs at
    least 10 such coins.
  - The slice is d x (long the top quintile by e, short the bottom quintile). That is floor(n / 5) coins a side,
    1/q each, so the book is dollar-neutral.
- **d:** +1 follows the leader, -1 fades it.
- **Accounting:** `slices.run`, `hedge=False`, tier costs at 1x/2x/3x, and `missing="raise"`. A raise invalidates
  the run; it is reported, not patched.
- **Warm-up:** each book starts 24 rows before its window.

## Windows
- **Discovery:** 2026-01-01..2026-05-31.
- **Validation:** 2026-06-01..2026-09-29. The archive ends 2026-09-30, and that last day is left out.

## Variants (24 trials)
2 leaders x 2 books x 3 holds x 2 signs. In discovery, each (leader, book, H) keeps the sign with the larger 1x mean,
which gives 12 selected books. Both signs count as trials.

## Decision (per selected book)
- **Discovery:** 1x NW t (lag 10) >= 2, and the 2x mean > 0.
- **Validation:** computed only for discovery passers. A pass needs all of:
  - 1x mean > 0 with NW t >= 1.5;
  - 2x mean > 0.
- **A validation pass** queues a forward paper lane (a new id). Nothing more, because both windows are spent.

## Reported (not decided on)
- Trigger counts per leader and window.
- Discovery correlations of Lk[t] with:
  - the crypto market's next-bar return (the lead);
  - the bar ending at t (contemporaneous).

  Each is reported for all hours, 13-20 UTC, and other hours.
- **Per selected book and cost level:** mean, NW t, Sharpe, max DD, per month, gross and cost, plus beta and
  residual against the crypto market.

## Multiplicity
- Trials = 24.
- Program trials before: 9,472,037 (after R260).

## Expectations
- If the lead exists, it is in EQ during US cash hours. CMD's link to crypto is weak and of unknown sign.
- **At H = 1 the TS book turns over every trigger hour, so costs will dominate.** H = 24 is the fairest test.
- **Most likely:** NULL. Five months of discovery give little power. A true 1 h lead would mostly show in the
  contemporaneous correlation, which cannot be traded.
