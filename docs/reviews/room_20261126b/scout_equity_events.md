# Scout: equity index and earnings events seen on 24/7 perps (room 20261126b)

Scout: Haiku, 2026-11-26. Family: S&P 500 adds/deletes, Russell reconstitution, after-close earnings, on trade.xyz
(HIP-3) and Lighter US-stock perps. Nothing was traded, fetched with credentials, or committed.

## 0. Bottom line

- Academic index effect is small now. Greenwood and Sammon: the abnormal return of additions "has fallen from an
  average of 3.4% in the 1980s and 7.6% in the 1990s to 0.8% over the past decade" (NBER w30748 abstract,
  https://www.nber.org/papers/w30748, read via WebFetch summary). The body says the effective-day return was
  "close to zero by the late 2010s" (scratchpad eq/nber_gs.txt, around line 555).
- The sign has flipped for one class. Vijh and Wang (Financial Management 2022, DOI 10.1111/fima.12391): "The 74
  upward additions result in highly significant excess returns of –2.48% over a 3-day window centered on the
  announcement date" (2016-2020). Their sample is 2001-2020, 403 additions.
- Held data cannot test an announcement effect yet. No held ticker is a 2026 S&P 500 addition in the window that I
  checked. OKTA, SN and the Everpure name are not in the held perp list.
- Cost gate: the lab's unit is "30 bp per round trip of price" (experiments/earnperp_v1/FINDINGS.md, costs section).
  Any candidate must clear that net of funding.

## 1. What the lab already knows (read, not re-tested)

- methods.csv:223 (M222): index additions and post-earnings drift were "Skipped: data not free or effect decayed."
- methods.csv:426 (M519): "S&P 500 additions announced after the close, on 24/7 stock perps ... N time-stamped S&P DJI
  announcement archive, BLOCKED". The blocker is the archive. It is public (press.spglobal.com), so it is buildable.
- methods.csv:420 (M513) and rounds.csv:248 (R461, earnperp_v1): NULL. After-close filings: next close +22 bp
  (n 219, Holm p 1.0, MDE80 127 bp). Diagnostic: before-open filings held to the close +80 bp in A (raw p 0.03 of 32
  cells), +70 bp in B. Not decided.
- rounds.csv:251 (R464) and :249 (R462): weekend fades on xyz index/commodity perps and single stocks. R464 NULL,
  R462 PARTIAL (frozen verdict PASS on gate 0).
- rounds.csv:227 (R442, xperp_stock_v1): NULL at gate 0 for OKX stock X-Perp carry.
- rounds.csv:262 (R475, hip3stock_v1): PARTIAL, weekly funding carry on trade.xyz US-stock perps.
- No lab row or FINDINGS covers Russell reconstitution or S&P membership changes.

## 2. Primary-source facts (URL and exact quote)

- Announcement timing for S&P 500 (not verified from the methodology PDF). The S&P methodology PDF returned HTTP 403
  to WebFetch twice, so I did not fetch it. A search summary says announcements are "generally made shortly after
  market close" (https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-equity-indices-policies-practices.pdf).
  Label: assumed until the PDF is read.
- Effective timing, primary press releases:
  - Okta, 2026-10-30 (https://press.spglobal.com/2026-10-30-Okta-Set-to-Join-S-P-500-Others-to-Join-S-P-MidCap-400-and-S-P-SmallCap-600):
    "effective prior to the opening of trading on Wednesday, November 4". No time of day is given.
  - Total-market change, 2026-06-04 (https://press.spglobal.com/2026-06-04-S-P-Dow-Jones-Indices-Consultation-on-Treatment-of-MegaCap-Companies-Results):
    "prior to the market open on Monday, June 8, 2026".
  - So the convention is effective before the next open. The trade day that carries the demand is the prior close.
- Announcement-to-effective gap: Greenwood and Sammon, nber_gs.txt around line 499: "For additions, the average period
  between the announcement and the effective date is 4.8 days; for deletions it is 5.8 days."
- Effective-day volume share: nber_gs.txt around line 243: "in the 2010s that number increased to almost 30%". The
  share is volume on the effective date within +/-22 trading days, from 15% in the 1990s.
- Old sample timing: Kasch and Sarkar (NY Fed SR484, nyfed.txt line 633): "Index inclusion announcements and effective
  inclusions take place after trading hours." Their CAR from announcement to the day after effective is 6.01%
  (t 12.43), 1989-2009, 403 additions. CAR40 reverses: "about two months after effective inclusion in the index there
  is a reversal of the initial increase in value."
- Front-running explanation (Greenwood and Sammon, nber_gs.txt around line 212): "sophisticated market participants who
  anticipate index changes purchase additions and sell deletions before the announcement day".
- Tesla 2020 example (Vijh, text around line 102): "announcement to effective date excess return of 66.7%". One
  case, and not an upward addition.
- Russell: LSEG, 2026-05-22 (https://www.lseg.com/en/media-centre/press-releases/ftse-russell/2026/ftse-russell-begins-june-2026-semi-annual-russell-us-indexes-reconstitution):
  "Changes from the June 2026 reconstitution will take effect after US equity markets close on Friday, June 26." Rank day:
  "as of the April 30 rank day". Schedule: "the reconstitution of the Russell US Indexes will again be held
  semi-annually in June and December".
- Lighter US-stock perps: Bankless, 2026-01-06 (https://www.bankless.com/read/news/lighter-expands-trading-hours-for-u-s-equity-perpetual-futures):
  "at anytime of day, from Monday to Friday." 24/7 is "coming soon". Secondary guides disagree on 24/7 vs 24/5.
  Label: not verified against Lighter's own docs.
- trade.xyz hours: search summaries (not primary) say US names are priced on 24/5 external prices and internal pricing on
  weekends. Hyperliquid docs HIP-3 page was not reachable. Label: assumed.

## 3. Held data (what I ran)

- data/xyz_wknd/manifest.json: kind "hyperliquid_xyz_1h_and_funding", window 2026-04-17 to 2026-11-10, 152 files
  (76 klines, 76 funding). Fetched 2026-11-25.
- Row counts I read from the manifest (python, no bars loaded):
  - AAPL 4,641 hourly bars and 4,968 funding prints; NVDA, MSFT, AMD, HOOD, SNDK, NFLX, PLTR, MU, LLY, ORCL, TSLA,
    GOOGL, META, AMZN, COST, MSTR, COIN, INTC, RIVN, HIMS, CRWV, BABA, TSM all about 4,641.
  - Shorter histories: AVGO 3,826; AMAT 3,202; LRCX 824; GLW 822; CRWD 1,994; NET 1,997.
  - 4,968 is every hour in the window, so near-full hourly coverage 24/7 for the large names (fewer bars for shorter
    histories).
  - Not held: OKTA, SN, PSTG.
- Public API used by the held pull (data/xyz_wknd/receipts.jsonl line 1): POST type "candleSnapshot", req coin
  "xyz:TSLA", interval "1h". Also "fundingHistory" with coin "xyz:TSLA". Test once before use.
- Membership of held names in the S&P 500 is from memory, not checked: AAPL, NVDA, MSFT, AMD, HOOD, SNDK, NFLX, PLTR,
  MU, DELL, LLY, ORCL, TSLA, GOOGL, META, AMZN, COST, IBM, QCOM, WDC, CVX, INTC, AVGO, AMAT, LRCX, GEV, COIN. Check
  each against the S&P constituent list before use.

## 4. Three candidate questions

### Q1. Do after-close S&P 500 announcements on held perp names drift to the effective-date close?

- Hypothesis: the perp drifts in the announced direction from the announcement hour to the effective-date close
  (index funds buy or sell at the prior close). Opposite: no drift, or a reversal by the effective close (NY Fed CAR40
  reversal; GS effective-day return near zero).
- Payer and rule: index funds must trade at the effective close (GS nber_gs.txt around line 243, effective-day volume
  near 30%). Rule: announcement "prior to the opening" (Okta release above).
- Why not known: M222 skipped; M519 BLOCKED for lack of an archive. The archive is public and can be built.
- Data: held xyz hourly bars cover 2026-04-17 to 2026-11-10 (section 3). Public archive: press.spglobal.com releases.
- Cheapest decisive observation (about 2 hours, EUR 0): list S&P 500 change releases dated 2026-04-17 to 2026-11-10 and
  match names to the held list. If zero match, kill: no in-window event exists. If any match, compute the perp return
  from the announcement-hour candle to the next close and to the effective-date close, minus 30 bp round trip.
- Kill result: fewer than 15 matched events, or mean net below 30 bp, or sign not stable across events.
- Value for a French owner with about EUR 10k: low. The window is about 4.8 days (GS), so funding and the 30 bp
  round trip take much of a small edge. The payer is in a cash closing auction, not on the perp.
- Probability: 4%. One line: GS say the effect is near zero in the 2010s, and held names rarely change membership.

### Q2. Does the Russell June 26, 2026 close move held perp names into the 16:00 ET print?

- Hypothesis: names with Russell index migration (buyers in Russell 2000 funds) drift up into the effective close.
  Opposite: no drift; the rebalance is already priced by the May 22 preliminary list.
- Payer and rule: Russell index funds trade at the close. LSEG: "will take effect after US equity markets close on
  Friday, June 26."
- Why not known: no lab row covers Russell. Note that the held list is mostly large caps. Most Russell 1000 to 2000
  migrations are not in it.
- Data: the held window covers June 26 (2026-04-17 to 2026-11-10). Needs the May 22 preliminary list (FTSE Russell,
  public) to match names. The June 26 16:00 ET print is 20:00 UTC on the hourly bar.
- Cheapest decisive observation (about 1 hour, EUR 0): intersect the preliminary add and delete lists with the held
  list. If fewer than 5 names overlap, kill by count. Otherwise read the 20:00 UTC bar change (effective close) for
  each overlapping name against a 5-day placebo window.
- Kill result: overlap under 5 names, or no difference from placebo days.
- Value for a French owner with about EUR 10k: low. Held perps are large caps; the Russell effect sits in small caps.
- Probability: 3%. One line: the held list has few migrating names, and the effect is a small-cap flow.

### Q3. After an after-close announcement, does the perp overshoot and revert before the next cash open?

- Hypothesis: the perp move on an announcement hour is an overreaction that reverts by the next open. Opposite: the move
  continues into the effective close. Vijh's -2.48% for upward additions (2016-2020) suggests sign and mix matter. Kasch
  and Sarkar show continuation to the effective date in 1989-2009.
- Payer and rule: the migration mix (Vijh, "upward additions" from the S&P 400) sets the sign. Rule: S&P effective
  "prior to the opening" (Okta release).
- Why not known: the lab has a related after-close test that is NULL (R461), but no S&P membership test. M519 is
  blocked on the archive. Q3 is the fade version of Q1 and uses the same archive.
- Data: same as Q1. Cheapest decisive observation: after Q1's archive, count events per year in the held list. If
  fewer than 15 in total, kill.
- Kill result: under 15 events, or the overshoot-then-revert pattern fails in both halves of the sample.
- Value for a French owner with about EUR 10k: low to none; perp-listed membership changes appear to be rare.
- Probability: 3%. One line: the perp-listed names in the archive are few, and the R461 after-close test was NULL.

## 5. Can a French retail client capture this?

- On a 24/7 perp, a trader can act on an after-close announcement before the next cash open. The held hourly bars show
  near-full hourly coverage for large names (section 3). Not verified: whether the overnight prices are live or
  internal on weekdays, and the Lighter hours conflict between sources.
- The payer trades at the cash close. The perp tracks that through its oracle. Whether the perp shows the flow
  is not verified.
- Cost: 30 bp round trip (experiments/earnperp_v1/FINDINGS.md). Funding applies on top (held funding rows).
- A leverage-free EUR 10k sizing is about 0.5 point of capital per trade, assumed. A 3-5 day hold pays funding over the
  hold; compute it from the held funding rows before any test.

## 6. Not checked

- The S&P methodology PDF (403) and the Hyperliquid HIP-3 docs (page not reached). Both are primary sources still to read.
- The Greenwood and Sammon PDF was read from a local text extraction (scratchpad eq/nber_gs.txt). Equations and tables
  were not checked against the paper.
- The Vijh explanation for the flipped sign was not read.
- Membership of held names in the S&P 500 is from memory.
- No recent (2025-2026) index-change archive has been assembled.
