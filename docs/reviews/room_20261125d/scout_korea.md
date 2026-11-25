# Scout: Korean venues (Upbit, Bithumb), structural payers
Date: 2026-11-25. Scout only: no test run, no PREREG, no orders. Probabilities are my own judgments.

## 0. What the lab already holds (read, not re-tested)
- M268 (Korean premium per coin, relative to BTC, cross-section): TESTED, R282 NULL, rank IC -0.005 at 24 h (t -1.6). Registry path: `registry/methods.csv:243`. Because the premium is measured relative to BTC, the common Korean component (the level of the BTC premium) is removed by design. Candidate 2 uses that component.
- M060 / R267: Binance "Will Delist" short, NULL (primary +1 h -0.12%, t -0.06). Upbit delist is mentioned only as "Upbit delist X18" (`registry/methods.csv:61`), with no round row for it.
- M061 / M062 / M190 / M280: Upbit and Bithumb listing notices BLOCKED (no archive held; `registry/methods.csv:62-63`). M280 records that "Upbit, Bithumb and Bybit refuse this machine (HTTP 403)" (`registry/methods.csv:255`).
- M294 (wallet suspension premium) and M465 (caution-flag "cage-pump" fade): UNTESTED. M465 cites SRC1103-017 for the FSC line "up to 10x+ above other exchanges" (`registry/methods.csv:372`).
- M464 (Upbit 00:00 UTC reset "racehorse" reversal): UNTESTED (`registry/methods.csv:371`).
- R205, R219, R189: NULL, other venues or designs (`registry/rounds.csv:8,29,43`).
- A grep of registry/methods.csv and rounds.csv for the FX act, 외국환, 정리매매 or the Upbit delisting clock returned nothing. Those rules are not covered anywhere in the lab.

## 1. What is held (data/)
- `data/upbit_hist/open/candles_1d` 245 files; `reserved/candles_1d` holds the rest, including `KRW-USDT.parquet`. Columns: t (ms, 00:00 UTC), open, high, low, close, volume, turnover_krw.
- `data/bithumb_hist/open/candles_1d` 364 files; `reserved/candles_1d` also holds KRW-USDT.
- `data/klines_1h/BTCUSDT.parquet` (Binance hourly, 4.5 MB).
- Contracts: `data/upbit_hist/contracts.csv` has status "live" for all 300 rows (open 245, reserved 55). `data/bithumb_hist/contracts.csv` has "live" for all 482 rows (open 364, reserved 118). No delisted Korean market is in the held data. This is a survivorship gap for any delisting question.
- Note: `docs/DATA_SOURCES.md:29` says Upbit history runs to 2026-10-20, but the KRW-BTC file I read ends 2026-11-17. The file itself is the better record; check it before using the end date.
- No USD/KRW series is held. FRED (DEXKOUS) could not be fetched from this machine (connection reset). I used KRW-USDT on Upbit as the dollar rate instead.

Code run (scratchpad `kr_probe`, read-only):
- First-candle year of KRW markets: Upbit 2025: 78, 2026: 59; Bithumb 2025: 110, 2026: 57. The 2021 counts (63 Upbit, 75 Bithumb) are the start of the history, not listings. Listing supply is high: about 137 new Upbit KRW markets in 2025-26 by this proxy.

Code run, BTC premium (USDT-implied):
- premium = KRW-BTC open / (KRW-USDT open x BTCUSDT 1h open at 00:00 UTC) - 1, daily.
- KRW-USDT is held only from 2024-06-07, so the series covers 846 days, 2024-06-07 to 2026-09-30.
- By year, median and 5th/95th percentiles: 2024 median -0.00%, 5% -0.21%, 95% +0.15%. 2025 median +0.01%, 5% -0.11%, 95% +0.15%. 2026 median +0.03%, 5% -0.09%, 95% +0.13%.
- Monthly median, last 12 months: between -0.04% (Jul 2026) and +0.07% (Apr 2026).
- Days with |premium| > 3%: 0.1%. Max +7.69% on 2024-06-07, the first day of the series; I did not check it, so treat it as a possible start-up artifact.
- Weekend vs weekday medians: weekend +0.017% (n 242), weekday +0.013% (n 604). The 5th/95th percentiles are close as well.
- Reading: by this measure the BTC kimchi premium is near zero in 2024-26. The premium that M268 removed by normalising to BTC is small to begin with.

## 2. Rules found (primary text quoted)
- Upbit's Trading Support Termination Policy (Korean), URL: https://static.upbit.com/guide/market_policy_close.pdf (text extracted locally with pdftotext; the PDF's title is 업비트 거래지원 종료정책, revised 260721).
  - Steps (page 1 of the PDF): "거래지원 심의위원회는 거래 유의종목 지정 사유가 해소되지 않거나, 이용자 보호를 위해 필요하다고 판단되는 경우 거래지원 종료를 의결하고 업비트 공지사항을 통해 거래지원 종료사실을 안내"
  - Clock: "업비트는 거래지원 종료 공지일로부터 30일간 정리매매 기간을 부여" and "업비트는 특별한 사정이 없는 한 거래지원 종료일로부터 30일간 출금 서비스를 지원".
  - After that: "출금기간 종료 후에는 출금 수수료 외에 보관 수수료가 부과될 수 있으며".
  - One listed reason is quantitative in kind only: "일정 기간 동안 시가총액 또는 거래회전율이 현저히 낮게 유지되는 경우" (market cap or turnover kept markedly low for a period). No threshold is given.
- Amended Foreign Exchange Transactions Act (Korean law firm summary), URL: https://www.lawtimes.co.kr/news/articleView.html?idxno=220703
  - Scope: "가상자산사업자가 가상자산의 매도·매수·교환 및 그 밖에 대통령령으로 정하는 행위를 통하여 대한민국과 외국 간에 가상자산을 이전하는 것" (a crypto business moving virtual assets between Korea and a foreign country through sale, purchase, exchange or other acts set by decree).
  - Penalty: "등록을 하지 않거나, 거짓이나 그 밖의 부정한 방법으로 등록하고 가상자산이전업무를 한 자를 형사처벌 대상으로 규정" (operating without registration is subject to criminal penalty; up to 3 years or KRW 300 million).
  - Effective date: "개정안은 공포 후 6개월이 경과한 날부터 시행될 예정이며(부칙 제1조)". The same article states the transition clause (부칙 제3조) covers only 전문외국환업무취급업자 (specialised FX businesses), not virtual-asset transfer businesses. The same firm's note gives promulgation 2026-06-02 and effect 2026-12-03 (https://www.lawtimes.co.kr/news/articleView.html?idxno=228190 is the decree article; the 2026-12-03 date comes from a search summary of a law-firm newsletter, bkl.co.kr, and I could not open the statute itself). Official check: law.go.kr, law 제21714호.
- FSC registration rules for exchanges, URL: https://fsc.go.kr/eng/pr010101/87500, "will take effect from August 20, 2026" (registration and sanctions notice; other changes "six months after promulgation").
- Virtual Asset User Protection Act, effective 19 July 2024: https://fsc.go.kr/eng/pr010101/82683 (page title "The Act on the Protection of Virtual Asset Users to Take Effect from July 19"). Secondary: theblock.co reports the 80% cold-storage duty. This is a custody rule, not a trading clock.
- Bithumb caution notices are public, for example "[Bithumb] Polkadot (DOT) Designated as a Trading Caution Item", https://en.bloomingbit.io/reporters/exchange-announcement-bot?page=10 (an aggregator feed, not the exchange itself).
- Kimchi premium, academic: arXiv 2410.22443, "Bitcoin and Shadow Exchange Rates", https://arxiv.org/abs/2410.22443. Quote from the abstract: premiums "are larger in countries facing greater frictions in conventional cross-border payment channels". The abstract does not give the sample period, and it uses LocalBitcoins P2P data, not Upbit.
- Not verified: a $50,000 annual cap on overseas remittance. Sources conflict (a 2021 Asiae article gives $5,000 per remittance and $50,000 a year; another gives $3,000 per transaction). I do not use any cap as a rule here.

## 3. Candidate questions

### Candidate 1: the cross-border crypto registration clock (new rule, 2026-12-03)
- Hypothesis: the Korean premium on KRW markets (BTC and the top 30 by turnover) rises in the 4-6 weeks before 2026-12-03 as cross-border transfers are rushed, then falls after the effective date. Opposite: no pre-deadline move, because the rule is registration plus penalty, not a cap, and flows move offshore or to P2P.
- Payer and rule: any Korean crypto business moving assets abroad must be registered by 2026-12-03, with no transition for transfer businesses (quote above). Those that cannot register must stop or pay the penalty; the flow that must move before the date is the payer.
- Why not known: no registry row mentions the FX act (grep of methods.csv and rounds.csv returned nothing). M268 and R282 are cross-sectional and end in 2026-10; the rule itself is not a variable there.
- Data: held: KRW-BTC and KRW-USDT daily (2024-06 to 2026-09, the series in section 1); no prior event of this type is in the held data, so the event cannot be tested on history. The forward test needs hourly KRW-BTC and KRW-USDT from now to 2026-12-03, plus Binance BTCUSDT (held to 2026-11).
- Cheapest decisive observation: record hourly KRW-BTC, KRW-USDT and BTCUSDT from a machine the lab can reach (Upbit and Bithumb returned HTTP 403 from this machine per M280; do not work around it). Hours of work to write the recorder, cost zero, about 5 weeks of data before the date.
- Result that kills it: the USDT-implied premium over the 4 weeks before 2026-12-03 stays inside its 2024-26 90% band (about -0.13% to +0.16% on the daily measure above), with no rise in the last 3 weeks.
- Value if true, French retail with about EUR 10k: low. The owner cannot trade the KRW side (no Korean bank account, no KRW). The only trade is a directional bet on the global perp (Binance, or Hyperliquid/Kraken where listed), and the premium's effect on it is unknown. Honest: mostly unreachable.
- Probability it is true: 25%. The payer is real and dated, but a pre-deadline rush has no precedent in the held data, and the 2021 remittance rules did not obviously create a lasting premium.

### Candidate 2: the BTC level of the Korean premium as a capital-control signal (time series, the part M268 removed)
- Hypothesis: when the USDT-implied BTC premium is high (for example above +0.5% at the daily close), Binance BTC perp returns over the next 1-7 days are positive (Korean demand leads). Opposite: high premium is followed by a fall in the premium, with no effect on the global price (the premium closes on the Korean side).
- Payer and rule: capital controls on fiat remittance (Foreign Exchange Transactions Act). They cap how much arbitrage capital can move, so the premium persists when it arises. The rule is quoted in section 2 only in its 2026 form; the 2021 remittance limits are not verified.
- Why not known: M268 (`registry/methods.csv:243`) is normalised to BTC, so BTC's own premium is zero by construction. R282 (`registry/rounds.csv:101`) tests only the cross-section. The BTC-level series has not been tested.
- Data: held (section 1). The series is short (846 days from 2024-06) and daily; the 2024-06-07 value (+7.69%) must be checked for an artifact before use.
- Cheapest decisive observation: already built from held data (code in section 1, under 10 minutes). Next step: regress the next 1, 3, 7 day Binance BTCUSDT return on the premium bins, with HAC standard errors. Cost zero.
- Result that kills it: no monotone relation between premium bins and forward returns (t below 2 on every horizon, both halves of 2024-06 to 2026-09 same sign or both null). With about 110 independent weeks, power is low; this is a limit, not a pass.
- Value if true: small. The premium is near zero now (2025-26 median +0.01% to +0.03%), so the rule is not binding in this window; a French owner gains only if the global perp moves with the premium.
- Probability it is true: 10%. The premium is near zero, M268 is NULL, and the rule is not visibly binding in the sample.

### Candidate 3: the Upbit/Bithumb delisting clock on coins with a global perp (caution, then 30-day clearing, then 30-day withdrawal)
- Hypothesis: for coins that Upbit or Bithumb delists, the global perp (Binance, MEXC, Hyperliquid where listed) falls over the 30 days after the delisting notice, when holders must exit on the exchange. Opposite: the caution flag (유의종목) and the committee vote are already priced, and the 30-day clearing period is anticipated, so the perp shows no drift after the notice.
- Payer and rule: after the committee resolves to end trading support, "업비트는 거래지원 종료 공지일로부터 30일간 정리매매 기간을 부여" (30 days of clearing trade), then "거래지원 종료일로부터 30일간 출금 서비스를 지원" (30 days of withdrawal). After that, storage fees may apply. The payer is the Korean holder who must sell or withdraw by a known date.
- Why not known: M060 and R267 are the Binance delisting notice (NULL). The Upbit clock (30-day clearing, 30-day withdrawal) is not in the registry (grep returned nothing). M061 (Upbit listing notices) and M465 (caution flags, untested) are adjacent but not this clock.
- Data: NOT held. Held contracts are all "live" (section 1), so delisted Korean markets are absent. Upbit notices are not held (M061). Upbit and Bithumb return HTTP 403 from this machine (M280).
- Cheapest decisive observation: scrape a public aggregator feed of exchange notices (for example the bloomingbit exchange-announcement feed, URL above) for caution and delisting notices in 2021-2026. Target 100-300 notices. Check its terms first. Then match each notice to the global perp (Binance klines_1h, held) and compare returns from notice to 30 days later against coins with no Korean listing. Hours of work, cost zero.
- Result that kills it: among notices with a global perp (expect n of 30-60), the mean return from notice day to clearing end is at or above the matched control, or the t is below 2 on the event study with the 2x cost band.
- Value if true: low to medium for a French owner. Only coins that have a global perp are reachable, and most Korean-delisted coins are small. Expect a few trades a year at most, and the M060 precedent (Binance delisting notices, NULL) suggests the effect is small.
- Probability it is true: 20%. The payer is strong and dated, but the same family (delisting shorts, M060, R267) was NULL, and the 30-day window is long enough to be anticipated.

## 4. Other items checked, not candidates
- Settlement clock: Upbit's 00:00 UTC daily reset is M464 (untested). Not repeated here.
- Holidays: Korean bank wires (K Bank, Upbit's KRW partner) show planned maintenance windows, including a weekend, but I found no official Upbit weekend or holiday KRW schedule (search results were secondary). The weekend premium check in section 1 (weekend median +0.017% vs weekday +0.013%) gave no difference. Dropped.
- Wallet status: M294 and M465 already cover it. The Upbit market status is current state only, so no history is held.

## 5. What was not checked
- Upbit's listing criteria and KRW-market admission rules are only partly sourced (the policy PDF covers caution and termination, not listing).
- FRED FX could not be fetched; the premium uses KRW-USDT, which is itself a Korean-side price under the same controls.
- The 2026-12-03 effective date comes from a secondary summary; the statute was not opened.
- Data end dates disagree (section 1, DATA_SOURCES.md:29 vs the file).
- The 7.69% premium on 2024-06-07 is unexplained.
- No Upbit or Bithumb endpoint was called in this scout (the lab's history was read from disk).

Files written: this page only. No other file edited, nothing committed.
