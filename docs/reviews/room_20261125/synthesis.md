# Room 2026-11-25: what I verified, what I reject, what changes (lead researcher's synthesis)

The room had eight Haiku members: two auditors, framework, inventor, critic, x100, and two rules-matrix readers. Each
report is a lead. Below, each claim that would move a rule, a lane or money is marked:
- **verified** (checked on the source myself);
- **rejected** (checked and wrong);
- **open** (not yet checked).

## Framework (`framework.md`)
- **Verified: "€10k a year needs roughly €280-550k deployed at these rates."**
  - At +3.3% (design gap now) and +6.1% (weekend book, unproven), €10k a year needs €160-300k. With the decay and a
    prior of 0.35 on the weekend book, the room's range follows.
  - Allocation does not make a breakthrough; more independent rents do.
- **Rejected: "the weekend figures are not proportional"** (§5). Costs grow with size, so the net per trade is not
  constant.
  - At half the edge (21 bp): 13 bp net at $1k (6 bp book + 1.8 fee) and 9 bp at $5k (9.8 + 1.8). So 5 × 9/13 = 3.5×,
    as written.
  - The full-edge ratio follows the same way. The cycle-4 table is consistent.
- **G1 is answered from a primary source** (Hyperliquid docs, read in cycle 7, not recorded until now). "Unified
  account … USDC balance is the single source for validator-operated perps, XYZ perps, and spot". Isolated positions
  draw their margin from that balance. So one USDC balance backs the design gap's Hyperliquid leg and the weekend
  book. The map's margin row is updated.
- **G2, the euro-dollar exposure, is right and important. Open as a measurement.**
  - The owner's hurdle is in euros. A dollar principal of €50k swings by about €3.5-5k a year with EUR/USD.
  - A hedge costs about the rate gap (about 2%/yr), most of the design gap's +3.3%.
  - Mitigation from the rules: Kraken's multi-collateral takes euros, so its principal stays in euros and only the
    P&L is in dollars. Hyperliquid's USDC principal is the exposed part.
  - To measure: the euro P&L of the dollar legs.
- **G3 is right: the decay cannot be confirmed forward in useful time** (t ≈ 0.3 after a year). The suggested
  cross-sectional test by pair age is weakened by a fact the room did not know: a pair's "age" in R525 is the age of
  the lab's data (Kraken serves one year), not the venue's listing. Open.
- **Kept as a proposal, not adopted:** allocation rules R-A1..R-A6. They are sensible, but no money is allocated
  before a PASS, and the December table already fixes the first step.

## x100 (`x100.md`)
- **Diagnosis checked on the registry:** 309 rounds; only 4 numeric forecasts, 1 scored. The forecast discipline
  exists in the rule (step 4) but not yet in practice. Adopted: a forecast ledger, scored automatically.
- **Adopted:** "replay first" (a historical number within a day, before any forward lane) and a verdict split (in
  sample / out of sample / measurement / null), with a deflated Sharpe on every PASS. Both match Bailey et al. (read
  today).
- **Adopted:** fixed room roles with a checked sample of each role's claims. That is what this file does.

## Inventor (`inventions.md`)
- **Its own Fermi sizes are €10-100 a year each** (LST unbonding discount, bridge-delay premium, prediction-market
  disputes). Nothing to pursue now. It marked duplicates against the registry correctly. Spot-checked: M296 and M494
  exist as it says.

## Auditor, non-carry families (`audit_other.md`)
- **Verified: R304's PARTIAL is superseded.**
  - R332's FINDINGS line 1: "On a complete-metrics panel R304's +58.9 bp/day is −16.5, and a rule that only asks
    'does this row have metrics?' earns +50.3".
  - R304's own header ("the leak never carried it") is outdated. R299 is already marked "INVALIDATED BY AUDIT" in its
    notes.
- **Verified: labels that overstate.**
  - R197 is labelled CONFIRMED, but its notes say "In-sample PASS", and its holdout R198 is NULL (t 1.22).
  - R185 is labelled CONFIRMED with notes "In-sample, gross".
  - The registry is append-only, so the rows are not edited. The caveats go in `label_caveats.md` (this folder), and
    the x100 verdict split applies from now on.
- **Checked, and the claim stands as context:** R465's hourly table shows the give-back falls between Sunday 20:00
  and 22:00, when Blue Ocean resumes (20:05).
  - The auditor's suggestion to enter at 20:30 would enter after the reversal starts. I reject it as a design for
    the fade.
  - Its point that the depth table skipped 19:30-21:30 is right but does not change R530 (entry 19:00, exit 22:00).
- **Open:** R435's open instant and R432's energy exit at the Monday cash open (both grid picks; low prior).

## Auditor, carry families (`audit_carry.md`)
- **Verified: isolated margin per leg is the wrong setup at any leverage** (R280,
  `experiments/levcarry_v1/FINDINGS.md:4-9`). 155 days with a short leg's coin up about 95% or more within the day.
  One cross-margin account per venue never liquidates at 1x.
  - **The stake must use cross margin on both accounts.**
  - **Checked today on Hyperliquid's `meta`** (235 assets): 9 are isolated-only (FRIEND, HPOS, NFTI, OX, PANDORA,
    RLB, SHIA, UNIBOT, XTEN), and **none of R508/R509's coins is among them.** Kraken's multi-collateral account is
    cross.
  - Added to the December stake specification.
- **Open, important for any KuCoin citation:** R384 shows KuCoin's funding scaling changed on 2026-07-25. Books cited
  at +20-24%/yr earn about +10% after it. Not in the December stake (Kraken + Hyperliquid), so not urgent.
- **Context, consistent with the lab's access notes:** most carry books are not holdable from France. The December
  stake was chosen on venues the owner can reach.

## Rules-matrix reader, margin and liquidation (`matrix_margin_liquidation.md`)
- **Spot-checked:** Hyperliquid's backstop at 2/3 of maintenance (seen in the trade.xyz / Hyperliquid text in
  cycle 6). Kraken EEA maintenance is 5% (repo answer, 2026-11-24).
- **New leads, open:**
  - Velocity's (Drift's) insurance fund is staker-owned and open to retail, with a $1M lifetime cap;
  - Paradex's insurance fund takes 70% of the liquidation penalty.
  - Vault yields were measured small in R446 (HLP, LLP). The new ones are noted, not pursued.

## Rules-matrix reader, closed-market pricing (`matrix_closed_market.md`)
- **Verified on the source:** Variational's equity perps freeze their index on weekends and holidays.
  - Quote: "Fixed Mode (Daily Maintenance, Holidays and Weekends): Fixed Mode is applied on Equity-based RWA Perps.
    No recalculation occurs, the Price Index remains fixed at the last available value" (`docs.variational.io`
    `llms-full.txt`, Index Smoothing).
  - trade.xyz and Lighter instead run a book-driven EMA (cycles 4-5).
- **Verified: Variational has a public read-only API** (`/metadata/v2/stats`, 10 requests per 10 s). It gives each
  listing's mark and indicative quotes at $1k, $100k and $1m.
  - On 2026-11-25 it listed 597 markets, including US stock perps with real volume: NVDA about $15.9M a day, QQQ
    $9.8M, AMD $3.1M. Base spreads were 4-9 bp (MSTR 31 bp).
- **Why this disagreement could matter (the one-page approach, short):**
  - **Mechanism.** If Variational's OLP (its only market maker) quotes around a frozen index over a weekend, while
    xyz moves by W, then at the reopen both venues reference the same cash price.
  - **The pair:** long the venue that is cheaper on Sunday, short the dearer. Its P&L is the whole cross-venue spread,
    whatever the open does. With Variational frozen at Friday's close, that spread is about W.
  - **Barrier:** the OLP's last look and risk limits, weekend sizes, split margin across two venues, and access
    (Variational's restricted persons).
  - **Fermi, if it held:** tens of bp to several % a market-weekend on the names with large W. Capacity is set by the
    OLP's quotes ($100k size quoted).
- **Prediction, written before any weekend is recorded:**
  - P(the OLP's weekend quotes stay within 20 bp of Friday's index while xyz moves by more than 100 bp) ≈ 0.25.
  - A professional sole maker with last look is more likely to move or widen its quotes.
  - If they do stay, the gap is a rule-forced convergence with weekly supply. If not, the row is closed.
- **The cheapest decisive observation is now recording.** `scripts/record_variational.py` runs hourly in
  `claude-xyz-books.yml` (folder `variational/` on `claude/xyz-books-data`) from 2026-11-25.
  - The first chances are Thanksgiving (Thursday 11-26, a US market holiday) and the 11-28/29 weekend.
  - A read of those weekends is registered before it is looked at.
- **Open (reported, not verified):**
  - Paradex's closing-hours index is about 79% peer weight;
  - Lighter removed caps for NVDA on 2026-07-10;
  - Felix's funding multiplier is 0.0 for NVDA/TSLA;
  - xyz's funding cap text conflicts (4%/h against 0.5%/h).

## Critic (`critic.md`)
- **Verified, and it changes a number: the December stake's base used R508's 1x cost** (7 bp a leg).
  - R508's own FINDINGS (`experiments/xfund_eea_v1/FINDINGS.md:85`): "costs about 15-20 bp on average, about 2-3x the
    test's 7 bp".
  - At 2-3x costs the stake's excess falls from about €65 to about €40-50 a year on €2,000. The decision is unchanged
    (a calibration stake), and the memo is corrected.
- **Accepted: the forecast prior for R530 was too high.**
  - The family's "3 of 5" are gate-0 screens, not confirmed passes; the registry holds no closed-market PASS.
  - The R530 PREREG is frozen, so its forecast stays as written. A dated revision is recorded here: π ≈ 0.20, so
    P(PASS) ≈ 0.20 × 0.92 + 0.80 × 0.06 ≈ 0.23. R530's read will be scored against both.
- **Accepted as known limits** (already in R530's "Known limits", now weighted more heavily):
  - last-trade returns may carry bid-ask bounce (Nagel: about 40% of a closing-price reversal);
  - the balanced design was selected after R462's `rel` cell.
  - What R463's B tickets show on executable mids will be read beside R530.
- **Accepted: the Kraken short-leg risk is 8.7% cumulative,** not 4.4% (the script resets legs daily; legs are held
  about 19 days). It is still far inside 59%. The rule holds. The short-leg note is corrected.
- **Not reproduced: the lag correlation of 0.45.** With returns December to October against the previous month's
  dispersion, I get 0.27 (same-month 0.915, which the critic reproduces). The difference is the month alignment. I
  keep 0.27 with the alignment stated.
- **Reproduced by the critic:**
  - the −30%/yr trend, which survives dropping 2021 (−32%) and 2022 (−32%);
  - the 0.91 correlation;
  - the weekend capacity table;
  - R530's input hashes.
- **Disclosure from the critic:** one recursive grep may have read journal files; nothing was quoted. Noted. Future
  room prompts forbid recursive greps over `experiments/`.

## Mechanical citation check (`scripts/verify_citations.py`, new today)
- **Over the first room's reports, 129 citations:** 11 verified verbatim, 87 located (the file and lines exist, no
  quote), 21 failed (16 quotes not found at the cited place, 5 found elsewhere), and 8 unresolvable paths to scratch
  files.
- **The failures are where my attention goes.** For example, the carry auditor's "+20-24%/yr in 2025-26" for KuCoin
  is not in the files it cites, so that claim stays open.
