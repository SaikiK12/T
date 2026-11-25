# Reflection 2026-11-25: what I can create with the Greeks (gamma, charm, vanna, vomma) and what decides it

The owner, 2026-11-25: "Réfléchis à des choses que toi tu peux créer… le gamma, le vanna, le vomma et d'autres trucs à
mixer… pose-toi des questions sur les choses où tu ne peux pas savoir si c'est acquis… si c'est la vérif qui limite,
débloque-la."

The room for this cycle:
- `room_20261125b/options_literature.md`, the literature, 15 sources;
- `room_20261125b/options_archive.md`, the lab's 14 option rounds;
- `room_20261125b/weekend_vrp_reading.md`, the weekend reading, still running.

My verification is in section 1. The questions this page produced are O1-O6 in `open_questions.md`.

## 0. What the lab already knows (Pólya: "Have you seen it before?")
- **Fourteen option rounds, none passed** (archive, section 1):
  - gamma: R292 (dealer GEX from taker flow);
  - charm: R289 and R296 (the Friday 08:00 UTC expiry);
  - flow: R295 (blocks and net drift);
  - skew: R307;
  - the variance premium: R209, R385, R409, R410, R411;
  - an equity GEX filter on crypto vol: R416;
  - equity intraday momentum: R528, on ES; the room did not list it.
- **The number that explains them all is in R292.** Dealers are short gamma on 76-92% of days. But the median net
  GEX is −$20M per 1% move, which is **0.13% of BTC perp daily volume** (`registry/methods.csv`, M308 result).
  "The hedge is a rounding error next to perp volume" (`experiments/dealerflow_v1/FINDINGS.md:55`).
- **The variance premium is real gross and dies on costs and tails.**
  - DVOL exceeds the next 30 days' realized vol by +8.15 vol points (R411, t 5).
  - A weekly short straddle earns +44 bp a week gross (t 4.66). It nets −12 bp at 1x, and the hedge is 69% of the
    cost (R409).
  - A banded maker hedge cuts the hedge fee from 39 to 9 bp a week, but the best cell is +15.6 bp (t 1.30), and the
    worst week is −985 bp (R410).
- **Data held and never used for these questions:**
  - ES hourly bars 2010-2026 (`data/databento/es_1h`, bought for R528);
  - the minute Deribit chain with bid and ask (`data/option_expiry`, five days);
  - SqueezeMetrics GEX 2011-2026;
  - Binance hourly klines.

## 1. What holds in the room's reports (checked on the page)
- **Baltussen, Da, Lammers & Martens (JFE 2021), Table 7, in the PDF:**
  - "NGEt−1 < 0 … 6.63∗∗∗ … (4.78)", adjusted R² 3.58%;
  - "NGEt−1 ≥ 0 … 0.82 (1.03)";
  - the coefficients are ×100.
  - Footnote: "2930 days with a negative NGE and 3158 with a positive".
  - Table 8: "NGE ∗ rROD,t −123.04∗∗∗ (−3.42)".
  - The room's figures are right.
- **Baltussen, Terstegge & Whelan (2024):**
  - "the SOQ exceeds the index closing price by an average of 18 basis points … (t-statistic = 3.5)";
  - "The pre-2003 sample period displays no such effect";
  - an "overnight order imbalance of $306 million";
  - charm's predictive t is 2.99.
  - All hold.
- **Mechanical checks** (`scripts/verify_citations.py`, given `--corpus` this cycle for paper text):
  - literature: 20 of 27 quotes found in the papers' text. I read the other 7: paper titles of sources not
    downloaded, two Greek definitions, one paraphrase ("unwinding ∆hedges hypothesis"), and S8's abstract-only phrase.
  - archive: 63 verified, 33 located, 10 not matched word for word. The 10 are paraphrases of true lines, for
    example "Every entry used the 08:00 hour" (`experiments/vrpsell_v2/FINDINGS.md:10`) and "the same for maker and
    taker" (`FINDINGS.md:98`).
  - No room claim was wrong.
  - One gap: the literature member did not know R292's size figure, which decides most of the subject (section 2).
  - The folder for S8 (Golez & Jackwerth) holds a different paper (NBER w26773, Hazelkorn et al.). S8 is cited only
    from its abstract.

## 2. The one number that decides a Greek idea: forced hedge ÷ liquidity in the window where it must trade
- **The mechanism.** Every Greek channel is a payer of the kind this lab finds productive (L031): a dealer must
  trade the underlying because time passed (charm), the price moved (gamma) or implied vol moved (vanna).
  - The sign comes from the dealer's book.
  - Whether it moves the price depends on how large the forced trade is next to the liquidity **in the window when
    it has to happen**.
- **Fermi, with numbers I can stand behind:**

| Channel | Forced trade | Liquidity in the window | Ratio | Lab result |
|---|---|---|---|---|
| Crypto gamma (BTC, 2024-26) | −$20M per 1% (R292) | BTC perp daily volume | 0.13% | R292 NULL |
| Crypto charm at Deribit 08:00 UTC | gamma expiring within 2% of spot | 07:30-08:00 perp volume | small; R289 saw a 15-20 bp reversal, too small | R296 NULL |
| SPX charm into the 3rd-Friday SOQ | $280-306M overnight (paper) | ES overnight notional, measured here (16:00-09:00 New York, median): $29bn (2018), $45bn (2021), $53bn (2024), $82bn (2026) | 0.4-1.0% | never tested |
| SPX gamma (dealers short) | billions per 1% | ES day session $150-420bn (measured here) | about 1% | R528 NULL on the simple form |

- **What the table says:**
  - Crypto option hedging is an order of magnitude too small to move crypto prices. Every crypto Greek-flow round was
    NULL, and this is why. A crypto vanna round (M310) would face the same ratio. I do not test it (O4).
  - SPX charm has the larger ratio. The square-root impact law (impact ≈ σ_window × √(Q/V), σ overnight ≈ 70 bp)
    predicts 4-6 bp now, not the paper's 18 bp. Overnight ES volume has nearly tripled since 2018.
    - At 12 chances a year and about 1.5 bp of MES cost, a 5 bp effect is worth about 0.4%/yr on notional.
    - The full 18 bp would be worth about 2%/yr.
    - The 2022-26 holdout has about 59 events with an SD near 70 bp, so its standard error is about 9 bp. It cannot
      tell 5 bp from zero.
    - Killed at Fermi: worth less than its cycle (O1). The prediction is written in the register in case it is ever
      measured.
  - **Where the ratio is large is single stocks with heavy short-dated option open interest** (TSLA, NVDA and other
    0DTE and weekly names). There, dealer gamma per 1% can be several percent of the stock's daily volume, by
    order-of-magnitude reasoning not yet measured. That is where Ni-Pearson-Poteshman pinning and gamma squeezes live.
    The owner can reach those names on trade.xyz single-stock perps. This is O2.
    - **Measured the same day for $0.077** (Databento OPRA, TSLA open interest 2026-11-13 and the series
      definitions):
      - $2.3-2.5bn of gamma per 1% move, gross; $0.8-0.9bn calls-minus-puts.
      - That is about 6% gross and 2% net of an assumed $40bn of daily stock volume.
      - **TSLA's ratio is 15-45 times crypto's.**
      - The dealer's sign is the open part. Retail buys TSLA calls, which would make dealers short calls, the
        opposite of the GEX convention.
- **The general rule (already step 4's Fermi, made concrete for this class).** Before any Greek idea:
  - write the forced notional and the window's volume;
  - below about 0.5%, stop;
  - then ask whether the professionals' own quotes already price it (section 3).

## 3. The weekend clock: a convention gap that the incumbents already price
- **The question.** Deribit quotes implied vol in calendar time. Crypto realized vol is lower at weekends (CME:
  weekend vol is about 75% of weekdays). If market makers priced a Saturday like a Tuesday, buying Tuesday variance
  and selling Saturday's would be a design gap: a rule others had not compared (approach, 4c).
- **The cheapest decisive observation was in our own files.** The minute chain (`data/option_expiry`) holds full
  term structures with bid and ask. Implied forward vols from the mark IVs of the dailies:

| Snapshot (UTC) | Next day | Day after | Following day |
|---|---|---|---|
| Thu 2026-10-29 08:09 | Thu→Fri 29.4% | Fri→Sat 29.8% | **Sat→Sun 18.0%** |
| Fri 2026-10-30 08:09 | Fri→Sat 42.4% | **Sat→Sun 20.7%** | Sun→Mon 32.4% |

- **Realized, Binance BTCUSDT hourly, 08:00→08:00 UTC windows:**

| Window | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| Mean \|r\| 2023-24, bp | 199 | 177 | 199 | 204 | 170 | **77** | 169 |
| Mean \|r\| 2025-26, bp | 187 | 146 | 166 | 191 | 150 | **81** | 176 |
| Close-to-close vol 2025-26, % | 49.4 | 38.5 | 43.7 | 52.2 | 41.5 | **24.9** | 45.7 |

- **Reading:**
  - A one-day ATM straddle at 18-21% costs 75-88 bp. A Saturday's mean absolute move is 77-81 bp.
  - **Market makers already price Saturday at about half a weekday's vol, and they are about right.** There is no
    gross gap left to harvest, and costs are about 16 bp a straddle:
    - a measured half-spread of 7.5-10 bp on the dailies;
    - fees of about 6 bp.
  - The strong form of the idea is dead, settled in ten minutes with held data and no download.
- **What remains (O3b).** On the Friday snapshot, Sun→Mon forward vol is 32.4%, which costs about 134 bp. The
  Sunday-window mean move was 169-176 bp in 2023-26, though only 120 bp in the last 13 weeks.
  - That is one snapshot, so it is a question, not a finding.
  - The Sunday window holds the CME reopen and Asia's Monday, a closed-market clock like our xyz class.
  - The decisive history is the daily options' trade IVs (`data/deribit_trades`, public). I started refetching BTC
    2022-01.. on 2026-11-25. The prediction is written in the register before the data arrives.
- **The field's best evidence** (Deribit Insights, "Option Backtest – Selling Weekend Vol, Revisited", read on the
  page by me after the Haiku reader's report `room_20261125b/weekend_vrp_reading.md`):
  - **The rule.** "At 16:00 UTC every Friday, sell a 0.35 delta strangle that expires on Sunday at 08:00 UTC, and
    hold the options to expiry."
  - **Results.** "Number of trades: 212 (169 wins, 43 losses) Net profit: 1.2485 BTC (+124.85%) … APR: 27.4%"
    (2020-01..2024-08). The strangle is unhedged and its returns are negatively skewed. The sample ends 2025-04, so it
    does not hold the 2025-10-10 Friday-night crash, which falls inside its window.
  - **"Bloody Sunday."** Selling the 2-day strangle on Sundays: "Number of trades: 251 (153 wins, 98 losses) Net
    profit: -0.9224 BTC (-92.24%) … APR: -17.7%". The author: "every other day generated at least a small profit".
    - Buying it instead: "after fees and slippage, the APR was only 2.1%, and the results included a 0.45 BTC
      drawdown".
    - So the Sunday-to-Tuesday window is underpriced gross and roughly fair net. That fits my O3b prediction (no
      underpricing beyond costs), which was committed (428def4e) before I read this page.
  - **The reader's quotes, checked mechanically** (`verify_citations.py --corpus` on the page text I fetched):
  - 31 found and 27 not.
  - Most of the 27 come from pages outside my corpus (CME, arXiv HTML).
  - Two are attributed to the Deribit pages but are not on them: "hedging will be covered in future pieces" and
    "drawdowns may be underestimated because only hourly data was used". The reader's fetch tool summarized pages,
    so these two are not to be cited.
  - Every Deribit figure used above I read on the page myself.
- **Checked and not a lever:** "Zero Fees On Hedge Legs" (Deribit, 2025-12-16, until the end of 2026). The fee is
    waived only on a futures leg "added to an option structure in a block trade", so it does not apply to
    R409/R410's hourly rebalancing, which was the binding cost.
- **The registered read for O3b** (written and committed before the refetched data is opened; a measurement, no
  money, 0 trials):
  - **Days:** every date D from 2022-01-01 to 2026-10-31.
  - **Option set:** BTC options expiring D+1 08:00 UTC, trades in `data/deribit_trades/BTC/flow` with hour t in
    [D 08:00, D 10:00).
  - **Implied:** the amount-weighted IV of the calls and puts whose strike is within ±2% of the hour's index price,
    pooled over the two hours. Skip the day if fewer than 5 BTC traded in that set.
  - **Premium:** 0.7979 × IV × √(23/8760), in bp of spot. This is the at-the-money straddle from 09:00 to 08:00.
  - **Realized:** |ln P(D+1 08:00) / P(D 09:00)|, from Binance BTCUSDT hourly closes (P(h) = the close of the bar
    that opens at h − 1).
  - **Read:** by weekday of D, the mean premium, the mean move, their ratio, and the mean of (move − premium) with a
    plain t across days.
  - **Underpriced** means the mean of (move − premium) is above 16 bp, with t ≥ 2.
  - **Reported:** by year, and the same read with the Monday 08:00 exit replaced by 00:00, to isolate Sunday evening.
- **Lesson.** A convention gap shows up first in the incumbents' quotes, not in realized data. I read their term
  structure before measuring the world.

## 4. Mixes the owner asked about, and where each stands
- **Gamma × time of day (Baltussen):** the simple form is dead on ES (R528). The NGE-conditioned form holds in-sample,
  and the effect halved after publication. Not worth a new round on hourly bars.
- **Charm × expiry clock:** crypto NULL (R296). SPX killed at Fermi (O1).
- **Vanna × vol events:** no empirical dealer-flow test exists anywhere (room S7: theory only). In crypto, the R292
  ratio rules it out (O4).
- **Vomma × vol of vol:** a forecasting question, not a flow (the room's Q10). It is useful only for sizing, so it
  stays low in the register (O5).
- **Gamma × closed market (new, O6):** pinned single stocks close Friday at a strike, and the pin releases over the
  weekend while xyz perps trade. This is a mix of O2 and R530's class. It is an idea only, until O2's ratio is
  measured.
- **Variance premium × clock (O3):** Saturday is fairly priced. Sunday→Monday is open.

## 5. How I approached this subject, and what I would change
- **What went right:**
  - I verified the room's central numbers in the PDFs before using them.
  - I extended the checker so the next paper report verifies itself.
  - I let a Fermi ratio kill two ideas (O1, O4) instead of running them.
  - I found the weekend answer in data we already had.
- **What I would change:**
  - I spent the first part of the cycle verifying figures before asking which figure decides the subject. R292's
    0.13% was in the archive all along, and it decides most of the Greek class.
  - Next time, the open step asks: "what single ratio decides this class?", and I look for it in the lab's own
    results first.
