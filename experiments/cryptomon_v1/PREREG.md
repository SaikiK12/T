# PREREG: cryptomon_v1 (R471). Bitcoin's weekend move and the Monday session of Bitcoin-linked US stocks

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R471
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M521, idea wave 8 (`research/intake/idea_wave8_20261112.md`). Owner request of 2026-11-12: no idea is shelved
without web research and a power check on the longest free history.

## Question
- After a weekend, a Bitcoin-linked US stock opens with a gap that prices part of Bitcoin's weekend move.
- Does the stock keep moving in Bitcoin's direction from Monday's open to Monday's close, or give the gap back?
- If either is large and steady, a 24/7 stock perp (trade.xyz lists COIN, MSTR, HOOD and IREN) could trade the US
  session that follows the weekend.

## Why now
- Mourey, Shahrour and Şoiman (Finance Research Letters 86, 2025), abstract only: negative weekend crypto returns
  predict Monday equity declines; positive ones do not. Whether this sits in the open gap or continues during the
  session is not stated, and their full text was not readable.
- Blockworks/Messari: trade.xyz weekend perp moves predict the reopening with slope 0.834 (614 market-weekends,
  2026-03 to 2026-07). Read by a helper through a fetch summary; not checked by the author.
- No study of the session after the open was found (wave 8, lens 3).
- The 2026-11-12 power note on M521 used only the 29 trade.xyz weekends. The cash stocks give about 320 weekends.

## What the author has seen
- **Bitcoin weekend returns** (BTCUSDT perp hourly opens held in `data/klines_1h`, to 2026-09-30), counted for power
  only:
  - A has 175 weekends, with an sd of W of 4.67% and 59 weekends at |W| >= 3%;
  - B has 143 weekends to 2026-09-25, with an sd of 3.37% and 35 weekends at |W| >= 3%.
- **R244 (M198):** Bitcoin's weekend return against QQQ's Monday gap, NULL. It covers the gap, not the session.
- **R462, R465 and R466:** trade.xyz and Lighter weekend prices of the six crypto-linked perps, in aggregate.
- **One vendor episode** (Binance Research, September 2026): crypto names ran on during the session after a
  Thursday-night move.
- **Two HTTP probes:** Yahoo's chart endpoint for SPY and MSTR (5 days, header fields only) and Binance's archive
  (status codes).
- **Not read:** no stock open or close of this lane's universe, and no statistic of D or G.

## Data (fetched after this freeze)
- **Bitcoin:** `scripts/fetch_cryptomon.py btc --end 2026-11-11`, through `lab/data.py`.
  - Binance's public archive (data.binance.vision), BTCUSDT USD-M perp, 1 h klines.
  - Every zip is checked against its published SHA-256.
  - Output: `data/cryptomon/binance/klines_1h/`.
- **Stocks:** `scripts/fetch_cryptomon.py stocks --start 2020-06-01 --end 2026-11-12`.
  - Yahoo's public chart endpoint, daily bars, raw JSON kept.
  - Output: `data/cryptomon/yahoo/`, with a per-file sha256 manifest.
  - MSTR, COIN, MARA, RIOT, HOOD, IREN and QQQ.
- **Provenance:** `docs/provenance/cryptomon.json`.

## Rule (constants in `scripts/run_cryptomon.py`)
- **Sessions:** QQQ's trading days. S is a session at least 3 calendar days after the previous session P: Mondays,
  and Tuesdays after a Monday holiday.
- **W:** Bitcoin's return from the hourly open at P 16:00 New York to the hourly open at S 09:00 New York. It is
  known 30 minutes before the open.
- **Per stock at S:**
  - G = open(S) / close(P) - 1, the gap;
  - D = close(S) / open(S) - 1, the session.
  - A gap with |G| > 50% is a data break (a split priced on one side only) and is dropped.
- **Decision names and start dates (P on or after):**
  - MSTR 2020-09-01, after its first Bitcoin purchase;
  - COIN 2021-04-15;
  - MARA 2021-01-01;
  - RIOT 2021-01-01.
- **Decision series:** D_bar(S), the mean D of the decision names trading at S.
- **Direction:** the sign of A's slope of D_bar on W.
  - Follow means buy at the open when W > 0 and sell when W < 0.
  - Fade is the opposite.
- **Events:** sessions with |W| >= 3%. The trade return of an event is direction × sign(W) × D_bar(S).
- **Cost:** one unit of 5.8 bp a round trip, R462's trade.xyz growth-mode unit (2 × 0.9 bp + 4 bp slippage). The
  2x and 3x reads subtract two and three units.

## Samples and decision (gate 0)
- **A** (S 2020-09-01 .. 2023-12-31) decides and fixes the direction. **B** (S 2024-01-01 .. 2026-11-11) confirms.
- **INCONCLUSIVE:** fewer than 30 events in A or 15 in B.
- **A passes** when both hold:
  - the slope of D_bar on W, over all of A's sessions, has |t| >= 2.0 (HC1 standard error);
  - A's mean event trade return is above 2 units (11.6 bp) gross.
- **Verdicts:**
  - **PASS:** A passes and B's mean event trade return, in A's direction, is above 1 unit (5.8 bp).
  - **PARTIAL:** A passes and B's is at or below 1 unit.
  - **NULL:** A fails.
- **A PASS earns a forward lane** under a new id. It would trade trade.xyz's crypto-linked perps on fresh weekends,
  with tickets frozen before each Monday open and costs measured on `claude/xyz-books-data`.

## Power (stated before the read)
- The sd of D_bar is assumed at about 4% (four names that move together). It is not measured.
- **Slope in A:** se ≈ 4% / (4.67% × sqrt(175)) ≈ 0.065, so the detectable slope (t 2.0, 80% power) is about 0.18.
  That is 18% of Bitcoin's weekend move continuing or reversing after the open.
- **Event mean:** se is about 52 bp in A (59 events) and about 65 bp in B (about 38 events).
- **So only a large drift passes.** For example, after a -5% weekend, about -0.9% more during the session. A small
  drift would read NULL here and would not be excluded.

## Reported, not deciding
- For A and B:
  - the slope of the gap (Ḡ on W);
  - the slopes on negative-W and positive-W sessions separately (Mourey et al.'s asymmetry);
  - the event means for W <= -3% and W >= +3%;
  - the 1x/2x/3x event returns;
  - each decision name's event mean.
- **The same reads on HOOD and IREN** (listed on trade.xyz) **and on QQQ** (a placebo: a broad index should show
  little).

## Trials and reading
- Two trials: one rule, read in either direction. Program trials: 9,785,245 before this lane, 9,785,247 after.
- Read against `registry.program_trials()`.

## Limits
- **Survivors:** the names were chosen in 2026. MARA and RIOT are not on trade.xyz; they add power to the mechanism
  test only.
- **Cash prices, not perp fills:** a forward lane would trade the perp at 09:30 New York, whose price can differ from
  the cash open.
- **Early closes:** on early-close days (13:00 New York) P's close is three hours before W's start.
- **Yahoo's terms:** the endpoint is unofficial. The raw responses and their hashes are kept so the read can be
  reproduced.
- **MSTR's 2024 split:** handled by Yahoo's split-adjusted daily bars and the 50% gap guard.

## Code
```inputs
358165eb94413105d273ab8da2a9067247cd73c1d21de2e8e0360ab60c44a381  scripts/run_cryptomon.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
60de3167ab5a229e5a0bc19526b857655784952a0c21fa978a1a88bd4d6538b9  tests/test_cryptomon.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
```

## Stop rules
- One run after the fetch. Nothing is retuned afterwards; a changed idea is a new lane.
- No orders, no money, no credentials. The run writes only `experiments/cryptomon_v1/results/`.
