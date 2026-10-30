# Forex and US indices: data we can reach, known edges, first tests

A subagent researched this on 2026-10-20. It made only small probes (under 1 MB) and ran no edge test. Paper facts come
from search summaries, not full texts. Citations marked "memory" were not re-checked. This file widens the program to
the owner's forex and NASDAQ request (queue M193-M198, M212-M222).

## Data (probed 2026-10-20)

| Source | What | Reachable here |
|---|---|---|
| Yahoo chart API (`lab/markets.py`) | Daily bars for indices, ETFs, `=F` futures, `=X` FX and VIX. EURUSD from 2003-12, ^NDX from 2000. Intraday is short-lived: 1m about 8 days, 5m 60 days, 1h 730 days. | yes |
| Dukascopy datafeed | FX and index-CFD ticks and 1m/daily candles (`.bi5`, LZMA). About 90 MB per EURUSD tick-year; 1m is 2-15 KB per day. Connections reset often. | yes |
| Cboe | VIX, VIX3M, VIX9D, VVIX, SKEW history CSVs (about 1.2 MB); VX futures per expiry from 2013 (about 16 KB each) | yes |
| Kenneth French, AQR | daily and monthly factors | yes |
| CFTC COT | weekly positioning, yearly history zips | yes |
| Treasury, ECB, BIS policy rates | yield curve, EUR crosses, policy rates | yes |
| FRED | `fredgraph.csv` fails here (HTTP/2 errors); the API needs a key, which only the owner can create | no |
| Stooq | bot-check page since about 2026-03 | no |
| OANDA, TrueFX | need a token or registration | no |

## Traps
- **`=F` futures on Yahoo are continuous and unadjusted.** NQ=F jumps at quarterly rolls. Use ^NDX, ETFs or Dukascopy,
  or drop roll days.
- **FX daily bars are stamped at London midnight.**
  - 703 of 5,971 EURUSD bars carry a Sunday date. Convert with `tz_convert('Europe/London')` before using weekdays.
  - FX bars end at 19:00 New York (London midnight), after the 16:00 equity close, so same-date FX and equity returns are not synchronous.
- **Survivorship and revisions.** Yahoo keeps only symbols trading today. XIV is gone, which hides the -96% day of
  2018. `adjclose` is revised retroactively. A PREREG must record a checksum of each parquet file it reads.
- **Quote conventions.** ^TNX is the yield x 10. ^IRX is a percent yield. Policy-rate carry understates real forward
  points.
- **Constituent lists are current only.** Single-stock cross-sections are survivorship-biased. Use indices, ETFs,
  futures and FX only.

## Edges, ranked by evidence, feasibility and testability

**Protocol for every row:**
- Windows: discovery 2000-2012, validation 2013-2019, holdout 2020-2026-10 (read once), then forward paper. Most of
  these papers end before 2013, so only 2013 onward is out of sample.
- Costs: 1 bp one-way for index ETFs, futures and FX majors; 2 bp for crosses; 10 bp for TRY, ZAR and MXN. Report 1x,
  2x and 3x.
- FX carry also pays a 0.5-1%/yr swap markup.

| # | Edge | Evidence | Data | First test | Queue |
|---|---|---|---|---|---|
| 1 | Cross-asset time-series momentum | Moskowitz-Ooi-Pedersen; Hurst-Ooi-Pedersen 1880-2016. Weak in 2009-13 | Yahoo daily | sign of the 12-month return, vol-targeted to 10%, monthly, about 25 series | M194 |
| 2 | Overnight vs intraday drift | Lou-Polk-Skouras 2019; Cliff-Cooper-Gulen | Yahoo OHLC ^NDX, SPY, QQQ | close-to-open vs open-to-close, then buy close, sell open, with costs both ways | M195 |
| 3 | Turn-of-month | McConnell-Xu 2008; Etula et al. RFS 2020 | Yahoo daily | long SPY/QQQ from close T-1 to close T+3, against random-day control | M196 |
| 4 | G10 FX carry | Lustig-Roussanov-Verdelhan (Sharpe about 0.6 in 1983-2007); crash risk (Jurek) | Yahoo spot + BIS rates | top 3 vs bottom 3 of 9 G10 pairs by policy-rate gap, monthly; no TRY/ZAR/MXN | M193 |
| 5 | FX momentum | Menkhoff et al. 2012 | Yahoo FX | rank 14 pairs on 1- and 12-month return, 3 long / 3 short | M193 |
| 6 | Intraday momentum, last half hour | Gao-Han-Li-Zhou; Zarattini et al. 2024 | Dukascopy 1m (US500, USATECH) | sign of prior close to 10:00 ET, then trade 15:30-16:00 | M212 |
| 7 | Opening-range breakout on NQ/ES | Zarattini-Aziz (QQQ); a blog finds net about zero | Dukascopy 1m | 5-minute ORB, exit at close | M213 |
| 8 | VIX term-structure carry | static short-vol Sharpe under 0.5; Volmageddon 2018 | Cboe + SVXY/VXX | short vol only in contango and VIX under its 1-year median, with a hard loss cap | M214 |
| 9 | Volatility risk premium (measure only) | Bakshi-Kapadia; Carr-Wu (memory) | Cboe VIX, ^GSPC | VIX²/252 minus next 21-day realised variance | M215 |
| 10 | Dollar-cycle trend | Lustig et al. dollar factor | Yahoo FX + DX-Y.NYB | 12-month sign of the USD basket | M216 |
| 11 | FX value | Asness-Moskowitz-Pedersen 2013 | BIS real effective rates | 5-year real-rate change rank, monthly | M217 |
| 12 | Index short-term reversal in high VIX | Nagel 2012 (memory) | Yahoo + ^VIX | long after a 1-day drop > 1% when VIX > 25 | M218 |
| 13 | Halloween / sell-in-May | Bouman-Jacobsen 2002 (memory) | Yahoo | Nov-Apr vs May-Oct | M219 |
| 14 | Day-of-week and holiday effects | French 1980; Ariel 1990 (memory); likely gone | Yahoo | weekday means (London time for FX) | M219 |
| 15 | Pre-FOMC drift | gone after 2015 except press-conference meetings (Kurov et al.; NY Fed) | calendar + daily | SPY on press-conference FOMC days, 2013 on | M191 |
| 16 | COT positioning extremes | (none cited) | CFTC | speculator net z > 2 -> next 4 weeks, entered after Friday release | M220 |
| 17 | Month-end London 4 pm fix | Melvin-Prins; Evans (memory) | Dukascopy 1m | 15:30-16:00 London return, last 3 business days | M221 |
| 18-22 | Close-auction pressure, index additions, post-earnings drift, 0DTE flows, option-hedged carry | data paid, decayed, or survivorship-biased | - | skipped; carry with a VIX filter is a cheap proxy for 22 | M222 |

Prop-firm fit:
- Rules on overnight holds and news trading kill rows 2 and 15.
- Rows 6 and 7 fit them.
- See `docs/PROP_FIRMS.md`.

## Data pull
- **Phase 1:**
  - Yahoo daily for `lab/markets.UNIVERSE` (fetched 2026-10-20, a few MB);
  - Cboe indices and VX files (about 4 MB);
  - French factors;
  - BIS, Treasury and ECB rates (about 3 MB).
- **Phase 2**, only if phase 1 shows something: Dukascopy 1m for US500, USATECH and EURUSD, 2019-2026 (about 5,700
  requests, about 50 MB). Ask the owner first.
- **Order of lanes:** rows 3, 2, 1, 5, then 4.
