# Kraken Derivatives tail risk, 2024-01 to 2026-11 (room reader, 2026-11-26)

Scope: Kraken Futures / Kraken Derivatives (PF_ linear perps). Public pages and public API only. Nothing was logged in,
no order or account was touched, and experiments/*/journal/ was not opened.

Limits up front: the status history page shows only about two weeks (Nov 17-25, 2026). The Atom feed shows 5 recent
entries. I could not read 2024-2025 Kraken status entries from the primary source. Where I cite 2025 outages, the only
source is a third-party aggregator (isdown.app), so they are not confirmed.

## 1. Delistings of perpetuals

- **Rule on notice.** Source: https://support.kraken.com/articles/7526425887508-Futures-contracts-trading-suspensions-delistings
  (page "Last updated: November 25, 2026"). Quote: "When possible, we will notify clients in advance via platform
  notification." Quote: "We reserve the right to take these actions without advance notice in extenuating
  circumstances." No hours or days are fixed anywhere on the page.
- **Rule on open positions.** Same page. Quote: "A fair and reasonable settlement price will be determined by Kraken at
  our sole discretion." Quote: "The settlement prices are calculated by applying a volume weighted, time segmented TWAP
  methodology" ... "operated on the constituent exchanges in a 60-minute observation period." The page has no separate
  sentence on what happens to an open position beyond settlement at that price.
- **Delisting batches on the page.**
  - Quote: "The following derivatives contracts will be delisted on Friday, November 27, 2026 at 10:00 UTC:" (PF_ACEUSD).
  - 23 Nov 2026 batch: 12 PF_ symbols (for example PF_SSVUSD, PF_BBUSD, PF_LQTYUSD).
  - 30 Oct 2026 batch: PI_XBTUSD, PI_ETHUSD, PI_LTCUSD, PI_XRPUSD (inverse "PI_" contracts, not PF_).
  - 1 Oct 2026 batch: a large set, including PF_NMRUSD, PF_GMXUSD, PF_DOGSUSD.
  - Count: a hand tally by a model found about 310 distinct PF_ symbols in the delisted table, from 12-May-2022 to
    23-Nov-2026. Treat this as approximate. I did not verify it row by row.
- **Status page, July 2026 batch.** Source: https://status.kraken.com/ (incident "July delisting batch liquidation
  period extended", Nov 16 16:00 to Nov 21 01:49 UTC, about 4d 10h). The title is shown on the status page; the
  full update text was not visible.
- **Instruments API.** Source: https://futures.kraken.com/derivatives/api/v3/instruments. The response is about 796k
  characters. I read about 200k characters in chunks (0-200,000). I found 0 "tradeable":false in the parts read. I
  could not finish the count, so I give no total of non-tradeable instruments. The read covered PF_ symbols
  including PF_MANAUSD, PF_CRVUSD, PF_AAVEUSD, PF_RUNEUSD. This number needs a full pass by a script (a `curl`
  of the endpoint, parsed with `jq`), not a model read.

## 2. Halts, outages, post-only and cancel-only periods

- **Post-only semantics.** Source: https://status.kraken.com/history (incident "Derivatives Platform Maintenance",
  Nov 17, 2026, 08:09 UTC). Quote: "Orders can be placed or cancelled, but no executions or liquidations can occur
  until post-only is removed." Completed 08:19: "The platform is back online and post-only has been removed." Duration
  about 18 minutes.
- **Nov 19, 2026 maintenance.** Source: same page. Quote: "There will be a period of 'post-only' once the platform is
  back online and checks are being completed." Duration about 16 minutes.
- **Nov 20-21, 2026, US derivatives.** Source: same page. Quote: "During the window, clients will not be able to
  place, modify, cancel, or close orders or positions, including via API." The window was about 1h33m. This affects
  US Futures only, per the Atom feed. It does not directly affect the EEA perps.
- **Nov 19-20, 2026, auto-cancel broken.** Source: same page. Quote: "While this issue continues, open futures orders
  will not be cancelled automatically when the timeout expires." Duration about 18h (Nov 19 20:06 to Nov 20 14:03).
- **Nov 26, 2026 (scheduled).** Source: https://status.kraken.com/history.atom. Quote: "The Derivatives platform will
  be unavailable for approximately 15 minutes", with post-only afterward. Also a spot "cancel-only mode, and then
  post-only mode" entry the same day.
- **Liquidation during post-only.** Source: https://support.kraken.com/articles/7526425887508-Futures-contracts-trading-suspensions-delistings.
  Quote: "During the post-only period, no executions or liquidations can occur until after the post-only mode is
  removed."
- **2025 (third-party only, not confirmed on Kraken status).** Source: https://isdown.app/status/kraken/incidents/437319-connectivity-issues-derivatives
  and https://isdown.app/status/kraken/incidents/451586-futures-connectivity-issues-web-mobile-api-rest-websockets.
  Aug 26, 2025 (about 1h), Aug 28, 2025 (about 3h, post-only lifted 16:42, resolved 19:04), Sep 26, 2025 (evening
  resolution). Each put the platform in post-only, with liquidations paused until it lifted. Treat as unverified.

## 3. Liquidation and margin rules (Kraken Derivatives, EEA/EU)

- **Trigger.** Source: https://support.kraken.com/articles/4402283092244-Liquidation-FAQ (last updated November 16,
  2026). Quote: "A liquidation is triggered when the portfolio value of a derivatives margin wallet falls below the
  maintenance margin." Quote: "Kraken Derivatives does not offer margin calls or any warnings."
- **Halt behavior.** The FAQ does not say what happens in a halt. The post-only quote above covers liquidations.
- **Multi-M partial and full liquidation.** Same FAQ. Quote: "a Partial Liquidation will be initiated in which a
  percentage of the position(s) will be liquidated" and "a full liquidation will be initiated in which the entire
  position will enter the liquidation process." A liquidation fee applies to Multi-M positions.
- **Margin schedule.** Source: https://support.kraken.com/articles/derivatives-margin-schedule-and-maximum-leverage-eea
  (last updated October 30, 2026). Quote: "Kraken Derivatives reserve the right to update the margin schedule at any
  time without warning." Quote: "if there is not sufficient margin in a trader's wallet to meet updated requirements,
  position(s) can be liquidated." Class A maintenance margin starts at 5% at Level I (rising to 25% at Level IV). Class
  G values are not in the table I read.
- **Equity protection / unwind (EPP).** Source: https://support.kraken.com/articles/360022835671-Equity-Protection-Process
  (last updated November 16, 2026). Quote: "On Kraken Derivatives, your account balance can never go below zero."
  Quote: "Kraken routes them to registered liquidity providers who have agreed to take on positions in these
  situations." Quote: "If covered liquidation also fails, the remaining contracts are unwound." Counterparties are
  ranked by position value, return on equity and effective leverage. This is the auto-deleveraging-type step.
  The page says: "Equity Protection is only available outside of the U.S. and Kraken Derivatives US customers are not
  eligible." It does not name the EEA entity.
- **Gap.** I found no EU-entity-specific ADL text. The EPP page applies outside the US, which is inferred to cover EEA
  clients. That is an inference, not a quote.

## 4. Mark or index divergence incidents

- None found. Search for Kraken-specific mark/index divergence incidents returned only general explainers. Kraken's
  learn page says the mark price sets margin and liquidations. Source: https://www.kraken.com/learn/last-price-mark-price-futures.
  The Coin-M liquidation FAQ quote: "the maximum premium or discount from the index for perpetual contracts is 1%."
  This is a cap statement from the Coin-M FAQ (last updated March 17, 2026), not an incident.
- This is not evidence that none happened. The status history I could read covers only about two weeks.

## Answers

(a) Events in about 3 years that would cost a hedged position more than 5% (long on one venue, short on the other,
same coin). Based on what I could read: **0 documented events**. The sources cover too little of 2024-2025 to prove a
zero. The mechanisms that could do it:
1. A Kraken halt (post-only or cancel-only for 1-3 hours, as the 2025 items show) while the other leg moves. The hedge
   is then one-sided. A 5% move in an hour on a thin coin would breach 5%.
2. A delisting settled at a 60-minute TWAP of the constituent spot venues (quote above) while the other leg trades on.
   The settlement price could differ from the hedge's exit price by more than 5% on a thin coin. This is a design
   risk, not a documented event.
3. Forced liquidation with IOC on a thin book, or an EPP unwind to liquidity providers. Both are paid at a price set by
   Kraken, not the market.

(b) Advance notice before a delisting. The rule gives **no minimum**: "When possible, we will notify clients in advance
via platform notification." Plan for zero notice. The one batch I could date (PF_ACEUSD, Nov 27, 2026, 10:00 UTC)
does not show the date it was announced, so I cannot give a measured notice period from these sources.

## Not checked, and what could be wrong
- Status history for 2024-2025 was not readable. The 2025 items come from a third party.
- The 310-symbol delisting count was tallied by a model, not checked row by row.
- The instruments endpoint was only partly read (0 to 200k of about 796k characters). A script over the full response is the cheap check.
- EEA-specific margin percentages (Class G, the EU fee table) were not found.
- Rule quotes are from model-processed page text. Each quote should be checked against the live page before any money move.
