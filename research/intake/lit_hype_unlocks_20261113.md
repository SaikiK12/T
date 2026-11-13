# LIT and HYPE unlocks against R265's rule, and what a LIT unlock means for R447 (2026-11-13)

Follow-up to the [HLP/LLP/LIT intake](hlp_llp_lit_20261113.md) (FEAT-004, 2026-11-13 09:03 UTC). That note is a
frozen input of R484 ([`llphouse_v1/PREREG.md`](../../experiments/llphouse_v1/PREREG.md), sha256 `637797de...`), so
it stays at its intake bytes and this note carries the later work. Where the two differ, this note is newer:
- Factor 2 there labels DefiLlama's LIT schedule UNVERIFIED. DefiLlama's copy is now VERIFIED by re-fetch (WS0020);
  the schedule itself still has no primary source.
- Factor 2 there leaves the R265 question to FEAT-004. The answer is below: it is a linear start and does not fall
  under R265's rule (M057, M538).
- Its Routing section lists M536 as UNTESTED. M536 was tested by R484 and came out NULL
  ([FINDINGS](../../experiments/llphouse_v1/FINDINGS.md)).

Ledger rows WS0020 and WS0021 in [`registry/web_searches.csv`](../../registry/web_searches.csv); catalog rows
SRC1113-009 and SRC1113-012 in [`source_catalog_websearch_20261113.csv`](source_catalog_websearch_20261113.csv);
the HYPE body is saved in [`hlp_llp_lit_20261113/`](hlp_llp_lit_20261113/) (`SHA256SUMS`).

## LIT and HYPE unlocks against R265's rule

**Rule read from the frozen files.** R265 ([`unlocks_v1/PREREG.md`](../../experiments/unlocks_v1/PREREG.md)) and R266
([`unlocks_fwd/PREREG.md`](../../experiments/unlocks_fwd/PREREG.md)) both use `cliff_days` in
[`scripts/unlock_events.py`](../../scripts/unlock_events.py): it sums only `cliffAllocations` whose category is
`insiders` or `privateSale`, per UTC day D, and keeps D when the sum is at least 1% of max supply (14-day spacing).
`linearAllocations` are never read. R266 applies the same function to each token's `unlockEvents` in the daily
emissionsIndex snapshot (`scripts/forward_unlocks.py`, `snapshot_events`).

**Sources and labels.**
- SRC1113-009, DefiLlama [emissions/lighter](https://defillama-datasets.llama.fi/emissions/lighter): re-fetched by a
  second agent at 09:03 UTC, 384,204 bytes, sha256 `605f1fb9...`, byte-identical to the 08:2x copy. **VERIFIED as
  DefiLlama's published schedule** (WS0020). It is still a secondary source with no cited document, and Lighter
  publishes no tokenomics page (SRC1113-011, WS0017, NOT_FOUND), so the schedule itself rests on DefiLlama alone.
- SRC1113-012, DefiLlama [emissions/hyperliquid](https://defillama-datasets.llama.fi/emissions/hyperliquid): 383,701
  bytes, sha256 `f834c1eb...`, saved in [`hlp_llp_lit_20261113/`](hlp_llp_lit_20261113/). Secondary, UNVERIFIED (one
  fetch, WS0021). Not queue-changing: it has no event in the window under any reading.
- Not read: the 23.5 MB emissionsIndex that R266 snapshots (HEAD request only). That the index rows carry the same
  `unlockEvents` as the per-protocol bodies is assumed, not checked.

**Events dated 2026-11-13 to 2027-03-31.**

| Token | Event (DefiLlama) | Type and category | Size | R265 rule | R266 ticket |
|---|---|---|---|---|---|
| LIT | Team 1,661,000 + Investors 1,533,000 LIT a week from 2026-12-29 05:48 UTC to 2029-12-28 | `linear_start`, insiders; `cliffAllocations` empty | 3,194,000 LIT a week = 0.319% of the 1bn max supply a week (0.046% a day); first week 0.32%; first year about 166.7m (16.7%) | **Does not qualify**: no cliff, so `cliff_days` returns no day | No (no event) |
| LIT | Ecosystem 250m | TBD, not scheduled | n/a | No event | No |
| HYPE | none dated in the window. Last dated event 2026-11-06 (179,706 HYPE). Core Contributors cliffs 2026-01-06 to 2026-11-06 are observed HyperLabs transfers, category `Uncategorized`, largest 3,750,000 (0.375%) on 2026-10-07 | cliff, Uncategorized | below 1% even if relabelled insiders | **Does not qualify** | No |
| HYPE | 609.3m TBD (Core Contributors TBD and others) | not scheduled | n/a | No event | No |

The other check items in the plan:
- **First-week tranche:** 0.32% of max supply, under 1%. No single day reaches 1% at 0.046% a day; adding weeks
  together to cross 1% would be a different rule, so it is not done.
- **Size against volume:** at the 2026-11-10 perp close of 3.4753, a week of the LIT stream is about $11.10m. That
  is 0.56 days of the perp's mean daily quote volume over 2026-10-12..2026-11-10 ($19.73m; spot $4.27m), or 8.0% of
  perp volume each day (6.6% of perp plus spot). R181's 0.82-day cut applies to one cliff day's tokens and is not
  applied here. HYPE: N/A (no event).
- **R266's venue:** moot, since R266's rule yields no LIT or HYPE event. Whether MEXC lists a LIT perp was not checked.

**Decision: no lane.** No LIT or HYPE event in 2026-11-13..2027-03-31 falls under R265's rule, so nothing exists that
R266 could miss, and FEAT-004 step 3 (`experiments/litunlock_fwd`) does not apply. Calling a linear stream an unlock
event would change R265's rule, so it is a new idea: **M538** (UNTESTED) in `registry/methods.csv`, the short from
the close of D-7 to the close of D+14 around a first insider `linear_start` of at least 0.25% of max supply a week,
with its kill test written there (archive cross-section on the R265 snapshot first; LIT's own 2026-12-29 start is
one forward instance and decides nothing alone). It would need its own frozen PREREG and round before any return is
read. Notes added on M057, M506 and M537.

## What a large LIT unlock means for R447 (llpstake_v1)

No return, funding sum or price after 2026-11-10 was computed for this section. It reads R447's frozen book
([PREREG](../../experiments/llpstake_v1/PREREG.md)): per 1 LIT staked, 10 USDC in LLP, the LIT held and staked, and a
short of 1 LIT on Lighter's LIT perp margined at 1x. The stream starts on 2026-12-29, inside gate 1's first 90 scored
days (look on 2027-02-08), and runs past the 180-day look (2027-05-09).
- **Stake value against the short.** The stake and the short are the same size in LIT, so a fall in LIT from new
  supply moves both legs by the same amount; only the spot-to-perp basis stays in the book. The unhedged line (R447
  "stake held without the short") carries the full move and decides nothing.
- **Funding sign.** The short earns funding only while longs pay. Longs paid in every month to 2026-11-10 (intake
  note, moves section, LIT funding by month). If holders of newly unlocked LIT, or traders front-running it, short the perp, funding can
  turn negative and the short pays. This is the R447 leg most exposed to the unlock, and its PREREG already names a
  funding regime shift on LIT as the lane's main unknown.
- **Liquidation.** R447's check fires on a daily high of 2/1.2 times the previous close (+66.7%). Selling pressure
  from an unlock moves price the other way; the risk stays a short squeeze, as before. A 5x short would be closer.
- **LLP access demand.** LLP needs 0.1 LIT staked per USDC. Unlocked LIT that is staked for LLP access adds deposits,
  which spread LLP's liquidation income over more capital; unlocked LIT that is sold adds supply. Which one dominates
  is not known, and no staked-LIT total is available (unread list below).
- **Lock-up timing.** Unstaking takes 3 days and LLP withdrawal 5 minutes, while the perp short can be closed at once.
  An exit around the unlock would leave the stake unhedged for those 3 days if the short were closed first.
- **Buyback against supply.** The buyback bought 20,000 to 41,000 LIT a day in September and October; the stream adds
  about 456,000 a day, 11 to 23 times more. This matters for M537's flow and the unhedged line, not for the hedged book.

### Addendum 2026-11-13 ~10:00 UTC: R447 watch note
- DefiLlama's team and investor `linear_start` stream (3.194m LIT/week) starts on 2026-12-29, six weeks before R447's
  first gate look on 2027-02-08, so about six weeks of the stream fall inside the scored window of that look.
- R447 holds a short of 1 LIT on Lighter's LIT perp per LIT staked. The short receives funding while longs pay. To
  2026-11-10 longs paid at a plain annualised mean of about 13.7%/yr over 7,485 hours (R484 intake note, funding
  paragraph; R447's FINDINGS report about 12.3%/yr on notional with its own day convention). If unlock selling or
  hedging makes shorts pay instead, the same leg becomes a cost to the book.
- This is a watch item, not a test and not a prediction. No LIT, HLP or LLP return, price or funding after
  2026-11-10 was read for it. R447's PREREG is unchanged; its 2027-02-08 look decides.

## What stays unread or unverified
- LIT's vesting from a Lighter primary source (NOT_FOUND, SRC1113-011); DefiLlama's schedule cites no source.
- The emissionsIndex body R266 snapshots (23.5 MB, not downloaded); whether MEXC lists a LIT perp.
- The staked LIT total (no keyless endpoint found).

## Routing
- Ledger WS0020 (SRC1113-009 re-fetch, VERIFIED) and WS0021 (SRC1113-012, HYPE); new **M538** (insider linear-start
  short, UNTESTED, no lane); notes on M057, M506 and M537. `WS1113-LIT-INSIDER-UNLOCK` stays an alias of M057: the
  decision is no R265 event.
- No frozen file, lane, workflow, round row or earlier ledger row was changed. The FEAT-004 commit (`2cd9b32a`) had
  first put these sections into the intake note, which R484 had frozen; the follow-up restored that note to its
  `45a4f263` bytes and moved the sections here.
