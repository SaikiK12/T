# Session-split return persistence: primary-source intake, 2026-11-15

Source intake for **M541 / R493** (`experiments/sessionpersist_v1`). Read scopes below are exact.
No paywall or bot check was bypassed; blocked items stay unread and are labelled as such.

Search tooling: the Tavily MCP tool returned HTTP 432 (plan quota) on every call this session, so
all searching went through keyless primary APIs: **OpenAlex**, **Crossref**, **Semantic Scholar**.
The DuckDuckGo instant-answer API returned empty abstracts for the ticker questions. Binance's
HTML announcement pages served a CAPTCHA ("Let's confirm you are human") and were abandoned; the
public CMS JSON API answered, then rate-limited this IP (HTTP 429).

## 1. What was actually read

### WS-S01 — Lou, Polk, Skouras (2019), "A tug of war: Overnight versus intraday expected returns"
- *Journal of Financial Economics*, DOI `10.1016/j.jfineco.2019.03.011`. Crossref confirms authors
  (Lou, Polk, Skouras), container and 2019-10 date; Crossref carries **no abstract**.
- **Abstract read in full** from Semantic Scholar (`DOI:` lookup, `abstract` field). Verbatim opening:
  > "We link investor heterogeneity to the persistence of the overnight and intraday components of
  > returns. We document strong overnight and intraday firm-level return continuation along with an
  > offsetting cross-period reversal effect, all of which lasts for years. We look for a similar tug
  > of war in the returns of 14 trading strategies, finding in all cases that profits are either
  > earned entirely overnight (for reversal and a variety of momentum strategies) or entirely
  > intraday, typically with profits of opposite signs across these components."
- OpenAlex OA status `bronze`; S2 `openAccessPdf` points at the ScienceDirect article page
  (`S0304405X19300650`), licence `None`. **The full text was not fetched or read.**
- **Read scope: abstract only.** Mechanism taken from it: same-component continuation plus an
  offsetting cross-component reversal. This is the direct parent of the tested hypothesis.

### WS-S02 — Hendershott, Livdan, Rösch (2010), "Intraday Patterns in the Cross-section of Stock Returns"
- DOI `10.1111/j.1540-6261.2010.01573.x` (*Journal of Finance*). **Abstract read** from OpenAlex's
  reconstructed inverted index. Key claims: return continuation at half-hour intervals that are
  exact multiples of a trading day, lasting at least 40 trading days; volume, order imbalance,
  volatility and spreads show similar patterns but do not explain the returns; short-term reversal
  is driven by liquidity imbalances under an hour and bid-ask bounce.
- OA `bronze`, `pdfdirect` Wiley link present. **Full text not read.**
- **Read scope: abstract only.** Supports "same-clock-time continuation" as a cross-sectional
  mechanism, and warns that microstructure (bounce, imbalance) can manufacture part of it.

### WS-S03 — Bogousslavsky (2021), "The cross-section of intraday and overnight returns"
- DOI `10.1016/j.jfineco.2020.07.020`. Crossref confirms single author Bogousslavsky, *JFE*, 2021-07.
- **Abstract NOT obtained.** Crossref: none. OpenAlex: none. Semantic Scholar `DOI:` lookup: HTTP 404.
  Green OA is listed via SSRN `10.2139/ssrn.2869624`, but the SSRN page returned a "Just a moment…"
  bot check (5.6 KB), and a Hawaii ScholarSpace session-decomposition PDF returned a 5,898-byte
  Turnstile page. Author page unreachable. **No bypass attempted.**
- **Read scope: title, author, venue, year only.** The paper's actual decomposition, sample and
  magnitudes are **unknown to this lane**. It is cited as the named literature anchor, not as
  evidence for any number.

### WS-S04 — adjacent crypto session work (titles/metadata only)
OpenAlex search surfaced, among others: "Max effect in crypto market: Evidence from intraday and
overnight trading" (2026, green, no DOI), "Bitcoin intraday time series momentum" (2021,
`10.1111/fire.12290`, green), "Overnight cryptocurrency downside and opening versus intraday equity
returns in Southeast Asia" (2026, `10.21203/rs.3.rs-11503547/v1`). **None of these bodies or
abstracts were read this session.** They are recorded as leads only.

## 2. Dedupe against this repo's own record

Checked before registering (WEB_SEARCH protocol, `registry/methods.csv` + rounds):
- **M195** QQQ/NQ night effect; **M321** index-perp weekend/overnight gap — index instruments, not
  an altcoin cross-section.
- **M492 / R435** MEXC stock-perp overnight vs intraday — **NULL**, TradFi underlyings.
- **M539** crypto MAX intraday/overnight — **NULL**, an extreme-value factor, not cumulative
  session-return persistence.
- **R222 `xsalt_v1`** slow altcoin cross-sections (beta, residual momentum, MAX, premium) — supplies
  the cross-sectional conventions reused here (min 15 names, quintile books), and its MOM is a
  720-hour total-return momentum, not a session split.
No existing lane tests *cumulative same-session return persistence with an opposite-sign
cross-session comparison* in the altcoin-perp cross-section. M541 is new.

## 3. The experiment it earns

- **Mechanism transferred, not assumed.** Equity evidence (WS-S01, WS-S02) is driven by a trading
  day with a real close/open and by clienteles that trade at different times. **Crypto perps trade
  24/7 with no close and no opening auction.** So the transfer is a genuine question: does an
  *imposed* UTC boundary carry any of the same structure? A null is the expected outcome if the
  effect is an artifact of the equity session clock.
- **Testable inputs:** Vision hourly klines (frozen provenance manifests), session sums of hourly
  log returns over a fixed 00-14 / 14-24 UTC cut, next-day total return as the target.
- **Control that makes it interpretable:** `MOM24`, the same 7-day lookback with **no** session
  split. If the split factors do not beat the unsplit control, the session boundary adds nothing.
- **What it cannot show:** the equity mechanism (clienteles, auctions) is not observable here, so a
  hit would be a statistical pattern, not a verified mechanism.

## 4. Unread / unknown, explicitly

- WS-S03 abstract and full text; WS-S01 and WS-S02 full texts; every WS-S04 body.
- Whether any of these papers already report a crypto session-split cross-section (not checked
  beyond titles).
- No claim is made that any book, corpus or paywalled article was read.
- Binance contract-class metadata for post-2024 listings remains partially unresolved (CMS 429);
  the lane sidesteps it by using the frozen provenance manifests and a pre-2024 first-bar filter,
  which excludes the 2025-2026 TradFi waves by construction.
