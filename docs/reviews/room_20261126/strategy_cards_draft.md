# Strategy cards (draft, extractor room, 2026-11-25)

Scope: 14 lanes (R508, R509, R510, R512, R520, R521, R523, R524, R525, R526, R527, R530, R463, R467). Read: each lane's PREREG.md; FINDINGS.md where it exists (xfund_eea_v1, gap_breadth_v1, risk_limits_v1); README.md for xyzbal_fwd, xyzwknd_fwd, ltwknd_fwd; the rounds.csv row of each. Not opened: any journal (sealed forward data), DEVIATIONS.md, calibration.py, spec.toml, results/ folders. Citations are absolute paths; `:N` is the line in that file. Forward lanes with no FINDINGS are marked "no FINDINGS (forward, sealed)".

Status is taken from rounds.csv (all 14 rows: RUNNING / PENDING). Where a FINDINGS file states a verdict, the card says so; see "Discrepancies" at the end.

---

## 1. R508 xfund_eea_v1 (folder experiments/xfund_eea_v1)
- **Family:** carry, funding spread across a design gap. Method M553, candidate C13. Gate 1 (paper).
- **Status:** rounds.csv RUNNING / PENDING. FINDINGS.md:3 says "Verdict: PASS (R391's rule, gate 1)".
- **Instruments / venues:** Kraken linear perps PF_* (offered to EEA clients) and Hyperliquid perps.
- **Signal / entry:** 14-day funding sums per venue; spread = (short venue − long venue) × 365 / 14. Book `L14d th5% K20`, "Entries widest-first" (/home/user/T/experiments/xfund_eea_v1/PREREG.md:82-84).
- **Exit:** spread under half the threshold, or a venue stops trading (PREREG.md:85).
- **Size / leverage:** 20 slots, 1x per leg. A slot is 1/20 = 5% of book capital (same engine: /home/user/T/experiments/risk_limits_v1/PREREG.md:45).
- **Universe:** 111 coins (`symbols.csv`; PREREG.md:52).
- **Costs at 1x:** 7 bp per leg-side; 2x = 14, 3x = 21 (PREREG.md:86). Flat, not measured in the book. One live snapshot of 2026-11-18 (FINDINGS.md:73-91): thin Kraken buckets cost 13.5-16.5 bp per side at $500-1,000, plus taker fees of 5 bp (Kraken) and 4.5 bp (Hyperliquid).
- **Evidence (in-sample, 2025-12-08..2026-11-15, 343 book days):** 1x +24.28 %/yr, 2x +22.50, 3x +20.73 (FINDINGS.md:19-21); NW t 7.39 (:23). Every month positive (:44). No by-year table: one year of Kraken funding exists. Secondary `th10%`: +24.84 at 1x (:59).
- **Decision:** one run, 2026-11-18 (FINDINGS.md:10). PASS needs all of: one-sided Newey-West p ≤ 0.05 (lag 10), 2x mean > 0, 10% trimmed mean > 0, mean without the two best coins > 0 (PREREG.md:92-96). UNREADABLE under 60 book days.
- **Capacity:** 97% of return from coins trading under $100k a day on Kraken (FINDINGS.md:12-13). A $1,000-2,500 leg fits the thin coins; 20 slots is roughly $40k-100k of two-leg capital (:94-96).
- **Weakest link (stated by the lane):** Kraken's funding formula not verified (PREREG.md:123); one year only (FINDINGS.md:98); survivorship (:100); fills at daily closes plus a flat cost (:102).

## 2. R509 xfund_eea_fwd (experiments/xfund_eea_fwd)
- **Family:** carry, forward paper of R508's book. Method M553. Gate 2. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** Kraken PF_* and Hyperliquid, 111 coins (PREREG.md:38).
- **Signal / entry:** spread ≥ 5%/yr, widest first, into free slots (/home/user/T/experiments/xfund_eea_fwd/PREREG.md:35). Guard: 30-day correlation of daily log returns ≥ 0.9, at least 20 observations (:34).
- **Exit:** below 2.5%/yr, stale leg (3 days), undefined window, or contract leaves the venue's live list (:37).
- **Size / leverage:** long the venue that paid less, short the other, 1x each leg (:36); 20 slots.
- **Costs:** the decided series charges each leg-side its measured $1,000 walk plus taker fee (Kraken 5 bp, Hyperliquid 4.5 bp); a leg-side with no book record costs 21 bp (:52-56). Book walks at $1,000 and $2,500 (:49).
- **Evidence:** none decided. Its basis is R508 in-sample, +24.28 %/yr at 1x (PREREG.md:8). Dry run 2026-11-18: 111 coins per venue, 0 failures; live books walked at 6-29 bp per side for $1,000 (:124-128).
- **Decision:** scored days start 2026-11-19 (:60-61). Look 1 at 90 scored days (about 2027-02-17): PASS if NW t (lag 10) of net_book ≥ 2.5, doubled-cost sum > 0 and max drawdown > −3%; FAIL if the mean ≤ 0 (:66). Look 2 at 180 days (about 2027-05-18), same PASS conditions (:67). Kill switch: cumulative net_book below −3% fails at once (:69).
- **Capacity:** per-coin capacity reported, not decided (:72-73).
- **Weakest link:** Kraken delistings forcing exits; depth over time; access not checked (:105-110). A day count above 20% late sets "degraded timing" (:71).

## 3. R510 xfund_eea_fast (experiments/xfund_eea_fast)
- **Family:** carry, early read of R509's journal. Method M553. Gate 2 read; trades nothing. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** none traded; reads R509's `decisions.csv`, `tickets.csv`, `days.csv`, `book_fills.csv` (PREREG.md:27-28).
- **Statistic:** fund_book = funding − measured cost / 40 per scored day; net_book is R509's decided series (:33-37).
- **Looks:** 30 scored days (about 2026-12-19): PASS if NW t (lag 5) of fund_book ≥ 2.5 and cumulative net_book > 0; FAIL if mean fund_book ≤ 0; otherwise NOT YET (:42). 45 days (about 2027-01-03): PASS on the same two conditions; otherwise NO EARLY PASS (:43). R509's −3% kill switch applies (:45).
- **Earns (if PASS):** a stake of at most $2,000 two-leg via `lab.gate.go_real()`, after the owner confirms Kraken EEA access (:47-48).
- **Costs:** R509's measured costs; first 42 leg-sides had median 16.7 bp on Kraken and 7.9 bp on Hyperliquid, fees excluded (:73-76).
- **Evidence:** none decided. Power for 30-day windows from R508's days: 92% at 1x, 84% at 2.4x, 78% at 3x (:58-61).
- **Weakest link:** the statistic ignores the price legs; a basis drifting against the book can pass 30 days and fail R509 later (:80-81).

## 4. R512 xfund_eea3_fwd (experiments/xfund_eea3_fwd)
- **Family:** carry, three venues, sequential monitor. Method M554 (source R511, `xfund_kaster_v1`, not in this set). Gate 2. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** Kraken + Hyperliquid + Aster; 132 coins (PREREG.md:24, :28). Per coin the engine takes the widest eligible pair among the three venues (:26).
- **Signal / entry:** 14-day lookback, entry 5%/yr, 20 slots (:24).
- **Exit:** the R509 engine's exits (:26 cites `lab.carrylane`); not restated in the file.
- **Size / leverage:** 1x per leg; 20 slots.
- **Costs:** measured $1,000 cost per leg-side plus taker fee: Kraken 5 bp, Hyperliquid 4.5 bp, Aster 4 bp; no record 21 bp (:40-43).
- **Decision (anytime monitor, `lab.anytime`):** E_n checked every scored day from day 30. PASS on the first day n in [30, 180] with E_n ≥ 40 (:51). FAIL at once if cumulative net_book < −3%; at 90 days if the mean ≤ 0; at 180 days without a crossing (:52-55).
- **Evidence:** none decided. Source R511 (reported, in-sample): 1x +25.04 %/yr, 2x +23.43, 3x +21.81, NW t 6.23 (:9-10). Simulated size 2.2-4.2%; median crossing day 38-47 at R508's level (:59-64). Dry run 2026-11-19: 132 / 101 / 132 files, 0 failures; books walked at 7-24 bp per side (:110-111).
- **Weakest link:** persistent autocorrelation can push the monitor's size above 4.2% (:91-92). Aster access from France is "authorised nowhere" (:88).

## 5. R520 xfund_dhl_fwd (experiments/xfund_dhl_fwd)
- **Family:** carry, Deribit + Hyperliquid, forward paper. Method M560. Gate 2. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** Deribit (hourly bars, daily closes at 00:00 UTC, funding `interest_1h`) and Hyperliquid; 89 coins (PREREG.md:28-32).
- **Signal / entry:** R275's book unchanged: "lookback 14 days, entry 5%/yr, exit below half, 20 slots" (:26); correlation guard 30 days ≥ 0.9 on 20 observations (:27).
- **Size / leverage:** 20 slots, 1x per leg (same engine as R509).
- **Costs:** every on-time ticket walks both books at $1,000 and $2,500; the read charges Deribit 3.5 bp and Hyperliquid 4.5 bp; no record 21 bp (:35-38).
- **Decision:** scored from 2026-11-22 (:33). Kill switch: cumulative net_book below −3% (:44). Look 1 at 90 scored days: PASS if NW t (lag 10) ≥ 2.5 and cumulative net_book > 0; FAIL if the mean ≤ 0 (:45-48). Look 2 at 180 days: PASS if NW t ≥ 2.0, else FAIL (:49). No calendar date stated.
- **Evidence:** none decided. Basis (R519's history, not opened here, quoted in the PREREG): 1x +4.52 %/yr, 2x +3.43, 3x +2.35, NW t 7.02, 2023-06..2026-11 (:16-18). Power about 30% at look 1 and about 75% by look 2 at that level (:51-52).
- **Weakest link:** the basis is a reported secondary on data already seen (:22); at half the level the lane likely FAILs (:52).

## 6. R521 xfund_dhl_fast (experiments/xfund_dhl_fast)
- **Family:** carry, fast read of R520's journal. Method M560. Gate 2. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING. Writes nothing.
- **Instruments / venues:** reads R520's book A (Deribit + Hyperliquid); Deribit fee 3.5 bp (PREREG.md:24).
- **Statistic:** fund_book = funding − measured cost / 40 per scored day; net_book from R520 (:24-26).
- **Looks:** 30 scored days (about 2026-12-22) and 45 (about 2027-01-06) (:27). PASS if NW t (lag 5) of fund_book ≥ 2.5 and cumulative net_book > 0. FAIL if the mean fund_book ≤ 0, or R520's kill switch fired within 45 days (:28-30). Otherwise NOT YET at look 1 and NO EARLY PASS at look 2; R520 decides (:31).
- **Calibration (R519's history, descriptive):** power 0.67 at 30 days, 0.73 at 45; size 0.03 and 0.04 on the demeaned series (:37-40).
- **Earns (if PASS):** at most $2,000 two-leg, cross margin at most 2x, alerts above each venue's liquidation line (:47-49).
- **Evidence:** none decided. R520 had 30 replay days and no scored day at freeze (:55).
- **Weakest link:** the statistic is funding net of costs; the whole net is only a guard, and R520's own looks decide (:51).

## 7. R523 gap_combo_fast (experiments/gap_combo_fast)
- **Family:** framework; a combined read of two independent design-gap lanes. Method M560 + M553. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING. Writes nothing.
- **Instruments / venues:** R509 (Kraken + Hyperliquid) and R520 (Deribit + Hyperliquid), equal weight on common scored days (:22-25).
- **Entry / size:** no own entry; inherits each lane's book. Combined day = mean of the two lanes (:25).
- **Looks:** 20 common scored days (about 2026-12-13) and 30 (about 2026-12-23) (:26). PASS if NW t (lag 5) of the combined fund_book ≥ 3.0 and combined cumulative net_book > 0 (:27). FAIL if the mean ≤ 0 or either lane's cumulative net_book is below −3% (:28).
- **Calibration (in-sample, 343 common days):** threshold 3.0 gives power 0.78 at 20 days and 0.92 at 30; size 0.046 and 0.038 (:36-37).
- **Correlation:** −0.04 between R508's and R519's funding-net series over 343 days (:15-16).
- **Earns (if PASS):** at most $2,000 total across both pairs, leverage at most 2.5 under `lab/margin.py` (:43-46).
- **Evidence:** none decided.
- **Weakest link:** the two pairs share Hyperliquid's floor (:17-18); one common scored day existed at freeze (:3).

## 8. R524 xfund_bfx_fwd (experiments/xfund_bfx_fwd)
- **Family:** carry, Binance + Bitfinex, forward paper. Method M552. Gate 2. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** Binance perps (`lab.carrylane`) and Bitfinex (`lab/bitfinex.py`); 69 coins (PREREG.md:26-31).
- **Signal / entry:** "binance+bitfinex, lookback 14 days, entry 5%/yr, exit below half, 20 slots" (:24); guard as R509.
- **Size / leverage:** 20 slots, 1x per leg.
- **Costs:** walked $1,000 / $2,500 books at each on-time ticket; the read adds taker fees of Binance 5 bp and Bitfinex 6.5 bp; no record 21 bp (:32-34).
- **Decision:** scored from 2026-11-25 (:31). Looks at 90 and 180 scored days (:37): PASS if NW t (lag 5) of fund_book ≥ 2.5 and cumulative net_book > 0; FAIL if the mean fund_book ≤ 0 or cumulative net_book < −3%. Otherwise CONTINUE after look 1, and FAIL at look 2 if the same test does not pass (:38-40).
- **Evidence:** none decided. Basis (R507's history, in-sample, quoted): +5.21 %/yr at 1x over 2,078 days, NW t 11.94; 2025-26 about +3.1 %/yr (:16-17). Power 0.77 at 90 days, 1.0 at 180; size 0.0 (:41-42).
- **Weakest link:** the Bitfinex numbers are "the least trustworthy of the three floorless venues" (gap_breadth FINDINGS.md:96-97).

## 9. R525 gap_breadth_v1 (experiments/gap_breadth_v1)
- **Family:** carry, design gap widened to 12 pairs; equal-weight portfolio. Method M552. Paper.
- **Status:** rounds.csv RUNNING / PENDING. FINDINGS.md:3 says "Verdict: PASS".
- **Instruments / venues:** floorless (Kraken, Bitfinex, Deribit) × floor (Binance, Gate, Hyperliquid, KuCoin): 12 pairs (PREREG.md:18-19; FINDINGS.md:25-39). 9 are new, 3 are known (R507, R508, R519).
- **Signal / entry:** each pair is R275's book unchanged on `lab.xfund_v2` (PREREG.md:40). The PREREG does not restate its thresholds; R508's are L14d th5% K20.
- **Portfolio rule:** each day the mean 1x net over pairs live that day, equal weight, no selection (:41-43). PASS if NW t (lag 10) ≥ 3.0, 2x mean > 0, both halves > 0 (:42).
- **Costs:** the PREREG does not state them; the same book uses 7 / 14 / 21 bp per leg (/home/user/T/experiments/risk_limits_v1/PREREG.md:44).
- **Evidence (in-sample, 2021-01-22..2026-09-30, 2,078 days):** portfolio +7.77 %/yr at 1x, +6.70 at 2x, Sharpe 5.5, NW t 11.96, max drawdown −0.73% (FINDINGS.md:14-15). By year (1x): 2021 +13.7, 2022 +4.1, 2023 +9.4, 2024 +8.6, 2025 +2.2, 2026 to Sep +9.5 (:19-22). Kraken+Binance +32.4 %/yr at 1x (:28).
- **Audit:** with a one-day decision delay, bitfinex+gate falls to −11.4 %/yr; LUNA (May 2022) lost −3,449% of a leg's notional; worst day −85.9% of book capital (:81-84).
- **Decision:** run once on 2026-11-23 (FINDINGS.md:10).
- **Capacity:** Kraken pairs about +31 %/yr each but small capacity (FINDINGS.md:53); Deribit is the broadest (+6-7 %/yr).
- **Weakest link:** all in-sample; only forward days confirm (:57-58); Kraken window is 10 months (:58); pairs that share a floorless venue are near-duplicates (:62-63).

## 10. R526 risk_limits_v1 (experiments/risk_limits_v1)
- **Family:** risk overlay on R525's book. Method M552. Paper.
- **Status:** rounds.csv RUNNING / PENDING. FINDINGS.md:3 says "PASS by the frozen rule".
- **Limits tested:** `agree` (no entry if the legs' prices differ by more than 2% at entry, PREREG.md:47); `active` (each leg printed in at least 20 of the 24 hourly bars before entry, :51); `stop` (close both legs at the first hourly close where the ratio moved more than 10% from entry, with both legs printing, 7-day bar, :52-56); `all` = all three (:57).
- **Portfolios:** P12 (all 12 pairs) for `agree`; P4 (the 4 hourly pairs) for the others (:60, :68-69).
- **Size:** a slot is 1/K = 5% of book capital (:45).
- **Costs:** 7 / 14 / 21 bp per leg (:44); sensitivity at agree 5%, stop 20%, 1% extra slippage on stopped trades (:58).
- **Decision rule:** a limit is ADOPTED if at base timing its 1x keeps ≥ 80% of the base and, with a one-day delay, its worst day and 1x are no worse than the base (:68-71). PASS if "all" is adopted and its delay-1 worst day is above −5% (:72).
- **Evidence (in-sample, same days as R525):** P12 base 1x +7.77, delay-1 +4.57 with worst day −14.33%; P12 `agree` delay-1 +7.17 with worst day −0.41% (FINDINGS.md:21-24). P4 `active` Sharpe 4.59 / 4.30 at delay 0 / 1, max drawdown −0.69% (:29). P4 `stop` max drawdown −5.83% against −2.75% base (:30). `all` at delay-1: 1x +4.96, worst day −1.57% (:32).
- **Caveat:** the stop passes the rule but doubles drawdowns; FINDINGS says do not add it on last-trade prices (FINDINGS.md:5-6, :64-66).
- **Decision:** run once on 2026-11-23 (FINDINGS.md:10).
- **Weakest link:** limits chosen after seeing LUNA (:73-74); last-trade data on thin venues drives the stop and agree's Kraken cost (:75-76); coverage is 4 pairs for the hourly tests (:77-78).

## 11. R527 gap_combo3_fast (experiments/gap_combo3_fast)
- **Family:** framework; combined read of the three floorless venues' lanes. Method M553 + M560 + M552. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING. Writes nothing.
- **Instruments / venues:** R509 (Kraken + HL), R520 (Deribit + HL), R524 (Bitfinex + Binance), equal weight on common days (:16-19, :27-31).
- **Entry / size:** no own entry; inherits each lane.
- **Looks:** 20 common scored days (about 2026-12-15) and 30 (about 2026-12-25) (:32). PASS if NW t (lag 5) of the combined fund_book ≥ 3.0 and cumulative net_book > 0. FAIL if the mean ≤ 0 or any lane's cumulative net_book < −3% (:33-34).
- **Calibration (in-sample, 304 days 2025-12-01..2026-09-30):** three lanes equal weight: power 0.86 at 20 days, 0.95 at 30; size 0.032 / 0.000 (:42, :47).
- **Costs:** fund_book is already net of measured costs (:57).
- **Earns (if PASS):** at most $2,000 total, leverage at most 2.5, with R526's entry filters (:73-76).
- **Evidence:** none decided; R524 had 0 scored days at freeze (:81).
- **Weakest link:** Bitfinex's thin books may cost more than 7 bp and dilute the third lane (:63-64); Kraken's variance dominates the equal-weight mean (:67).

## 12. R463 xyzwknd_fwd (experiments/xyzwknd_fwd)
- **Family:** weekend reversal (fade of the Fri 20:00 → Sun 19:00 NY move), trade.xyz US-stock perps. Method M515. Paper. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** Hyperliquid HIP-3 perps `xyz:<coin>`, 76 markets (R462's universe) (PREREG.md:51-52).
- **Signal:** W = 10,000 × ln(P(E) / P(R)); R = Friday 20:00 NY, E = Sunday 19:00 NY (:60, :63-64).
- **Entry:** "A trade: |W| ≥ 50 bp. Fade: short when W > 0, long when W < 0" (PREREG.md:65).
- **Exit:** X1 = Sunday 22:00 NY (:60).
- **Size / leverage:** one trade per market with |W| ≥ 50; $1k per fill; weekend net = mean over traded markets (:93).
- **Costs at 1x:** one taker fee per fill (growth mode 0.1 × 4.5 bp × deployer scale factor) plus the recorded $1k walked cost from the nearest book snapshot within 90 min; else 10 bp, counted (:70-76). 2x and 3x double and triple it.
- **Evidence:** none decided. In-sample R462 (not forward): +42.4 bp per market-weekend before costs in sample A (Holm p 0.004), +36.2 bp in B (:19-20). Resampled power: A passes 87% of the time, 51% at the 20th traded weekend (:126).
- **Decision:** futility NULL at 15 traded weekends if the mean ≤ 0 (:98-99). PASS at 20 weekends (p < 0.01) or 30 (p < 0.04), with 1x > 0, 2x > 0 and the mean without the best 3 > 0; tickets (B) must cover two thirds of weekends with mean > 0 (:100-106). Read dates: futility about March 2027, interim about April, final about June (Power section).
- **Weakest link:** last-trade prices, costs assumed in R462 (:19-20); GitHub scheduler can drop B tickets (Known limits).

## 13. R467 ltwknd_fwd (experiments/ltwknd_fwd)
- **Family:** weekend reversal on Lighter's US-stock perps. Method M515. Paper. No FINDINGS (forward, sealed).
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** Lighter perps, 50 markets (`ltwknd_v1/universe.csv`, PREREG.md:62-63). Standard account, 0 maker and 0 taker (:32-34).
- **Signal:** as R463, on traded hourly candles (volume > 0, close > 0) (:72-76).
- **Entry:** "A trade: |W| ≥ 50 bp" (PREREG.md:77). **Exit:** X1 = Sunday 22:00 NY (:71).
- **Size:** one trade per market; $1k per fill (Known limits section).
- **Costs at 1x:** Lighter's listed taker fee (0 for all 50 markets on 2026-11-11, :82-83) plus the recorded $1k walked cost; fallback 10 bp, counted (:84-86).
- **Evidence:** none decided. In-sample R465 (not forward): +45.3 bp per market-weekend in A (p 0.005), +35.6 bp in B, and −1.3 bp in the unseen sample C, Feb-Apr 2026 (:20-22). The weekend moves correlate 0.96 with R463's (:31-32).
- **Decision:** same schedule and rules as R463: futility at 15 traded weekends; PASS at 20 or 30 with tickets agreeing; PARTIAL if A passes but tickets cover under two thirds (:113-124).
- **Weakest link:** sample C shows the effect can vanish for whole months (Power section); a Pyth oracle change on 2026-06-15 moved the overnight session (:42-44); corporate actions (Known limits).

## 14. R530 xyzbal_fwd (experiments/xyzbal_fwd)
- **Family:** market-neutral weekend reversal (balanced version of R463). Method M563. Paper. No FINDINGS (forward, sealed). README.md:1-17.
- **Status:** rounds.csv RUNNING / PENDING.
- **Instruments / venues:** trade.xyz US-stock perps on Hyperliquid, R462's 76 markets (PREREG.md:12-13, :80-82).
- **Signal:** "rel W = W − the weekend's median W" (PREREG.md:85). Median over all priced markets; at least 5 needed (:84).
- **Entry:** "buy every market with rel W ≤ −50 bp and sell every market with rel W ≥ +50 bp, from E to X1" (PREREG.md:86); E = Sunday 19:00 NY.
- **Exit:** X1 = Sunday 22:00 NY (PREREG.md:16-17).
- **Size / leverage:** equal notional on each side; a weekend with no market on one side does not trade (:87-88). Weekend net = mean of the long side and mean of the short side (:95).
- **Costs at 1x:** two taker fees (from `markets/`) plus the walked $1k cost at E and at X1; 10 bp fallback, counted (:90-94). 2x and 3x per weekend (:96).
- **Evidence:** none decided. In-sample R462 weekends to 2026-11-09: balanced A +52.0 bp per weekend, SD 27.7; B +22.2, SD 35.9 (:30-33). The code reproduces gross A +59.9 bp and B +30.1 bp (:43). Forecast P(PASS) ≈ 0.36 (:149).
- **Decision:** futility NULL at 15 traded weekends if the mean ≤ 0 (:106-107). PASS at 20 weekends (p < 0.01) or 30 (p < 0.04), with 2x mean > 0 and the mean without the best 3 > 0 (:108-112). Schedule: first weekend 2026-12-04; 20th about late April 2027; 30th about early July 2027 (Supply section).
- **Weakest link (pre-mortem):** the in-sample edge may be bid-ask bounce in last-trade closes; dollar-neutral is not beta-neutral (:152-157). The design was chosen after R462's `rel` cell looked strong (:170-171).

---

## Summary

| id | one-line strategy | status (rounds.csv; FINDINGS) | best evidence number | decision date |
|---|---|---|---|---|
| R508 | Kraken + Hyperliquid funding carry, L14d th5% K20 | RUNNING; FINDINGS PASS | +24.28 %/yr at 1x, NW t 7.39 (in-sample, 2025-12..2026-11) | one run 2026-11-18 (done) |
| R509 | Forward paper of R508's book, measured costs | RUNNING | none (no FINDINGS) | look 1 about 2027-02-17; look 2 about 2027-05-18 |
| R510 | Early read of R509's funding net of costs | RUNNING | none | about 2026-12-19; about 2027-01-03 |
| R512 | Kraken + Hyperliquid + Aster carry, anytime monitor | RUNNING | none; source R511 +25.04 %/yr at 1x | crossing from day 30 to 180; no date |
| R520 | Deribit + Hyperliquid carry, forward | RUNNING | none; basis R519 +4.52 %/yr at 1x | 90 and 180 scored days; no date |
| R521 | Fast read of R520 (funding net of costs) | RUNNING | none | about 2026-12-22; about 2027-01-06 |
| R523 | R509 + R520 equal-weight combined read | RUNNING | none; calibration power 0.78 / 0.92 | about 2026-12-13; about 2026-12-23 |
| R524 | Binance + Bitfinex carry, forward | RUNNING | none; basis R507 +5.21 %/yr at 1x over 2,078 days | 90 and 180 scored days from 2026-11-25 |
| R525 | 12-pair design-gap portfolio (floorless x floor) | RUNNING; FINDINGS PASS | +7.77 %/yr at 1x, NW t 11.96 (in-sample 2021-2026-09) | run 2026-11-23 (done) |
| R526 | Live risk limits on R525's book | RUNNING; FINDINGS PASS by rule | P12 agree delay-1 worst day −0.41%; stop doubles drawdown | run 2026-11-23 (done) |
| R527 | Three-lane combined read (R509, R520, R524) | RUNNING | calibration power 0.86 / 0.95 | about 2026-12-15; about 2026-12-25 |
| R463 | trade.xyz weekend fade, forward, ticketed fills | RUNNING | none; R462 in-sample +42.4 bp gross per market-weekend | futility at 15 traded weekends; looks at 20 and 30 |
| R467 | Lighter weekend fade, forward, ticketed fills | RUNNING | none; R465 A +45.3 bp, C −1.3 bp | same schedule as R463 |
| R530 | Balanced (market-neutral) trade.xyz weekend fade | RUNNING | none; R462 balanced A +52.0 bp, SD 27.7 | futility at 15; first weekend 2026-12-04 |

## Discrepancies and open points
1. Status: rounds.csv shows RUNNING / PENDING for R508, R525 and R526, while their FINDINGS say PASS. This draft does not change the registry; whoever owns it should reconcile.
2. R526: the frozen rule ADOPTS the stop, but its FINDINGS (:64-66) advise against the hourly stop on last-trade prices. The two statements conflict for a live book.
3. Not in this set but cited: R511 (`xfund_kaster_v1`) and R519 (`deribitgap_v1`). Their numbers are quoted from the lane PREREGs that cite them, not checked against those folders.
4. Not opened per the brief: DEVIATIONS.md (xfund_eea_fwd, xfund_eea3_fwd, xfund_dhl_fwd), calibration.py (gap_combo3_fast), spec.toml and results/ (gap_breadth_v1, risk_limits_v1), all journals.
5. The weekend lanes' 1x cost lines are described from the PREREG text only; no measured cost value was read.
