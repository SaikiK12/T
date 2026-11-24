# PREREG: roll_frontrun_v1 (R529). Front-running the commodity index roll in CME calendar spreads

Freeze with `lab.prereg.freeze()` before any spread return is computed. Never edited afterwards.

- **Registry id:** R529
- **Owner (single writer):** the Claude session that froze it. `scripts/run_roll_frontrun.py` is the only writer of
  `experiments/roll_frontrun_v1/results/`.
- **Date registered (UTC):** 2026-11-24

**Methods:** a new method (front-running the index roll), queued with this round. Family: carry_tradfi.
- **Paper only.**

## Why
- **Wide means new payers** (`CLAUDE.md` rule 7, L031). This is a structural payer in another market.
- **Who pays, and why must they?** Commodity index funds (S&P GSCI, BCOM) hold long futures and must roll them from
  the nearby contract to the next on announced dates: business days 5-9 (GSCI) and 6-10 (BCOM).
  - CFTC economists (Brunetti & Reiffen, "Commodity index trading and hedging costs", read 2026-11-24, pp. 1-2, 7,
    17) find two things:
    - "One of our key findings is that the inter-maturity spread increases with the percentage of CIT holdings in
      the first deferred contract", consistent with Mou (2010);
    - "Most of this roll takes place between 30 and 40 days prior to contract expiration."
  - Their note 19 warns that some index traders now hold more distant contracts and roll less.
- **Sources not read:** Mou (2010/2011) is behind Cloudflare (SSRN) and an Anubis challenge (Columbia); S&P's
  methodology returned 403. None was bypassed. The design uses only the mechanism above.

## Data (held; R505's pulls, read-only)
- **Source:** `data/databento/cmeterm_v3` (Databento GLBX.MDP3 statistics, settlements) and R504's map in
  `data/databento/cmeterm_v2` (resolve.json and definitions), loaded by `scripts/run_cmeterm_v3.load()`.
- **Content:** the daily settlement of the three contracts with the most open interest, per root.
- **Roots:** 13 (CL HO RB NG GC SI HG PL ZC ZS ZW LE HE), 2010-06..2026-10.
- **No new download.** The data manifests are pinned below.

## Rule (`scripts/run_roll_frontrun.py`)
- **Per root and month m (2010-08..2026-10):**
  - BD0 = the root's last settlement day before month m; BD4 and BD9 = its 4th and 9th settlement days of month m.
  - A = the contract among the root's top three by open interest at BD0 that expires in calendar month m+1.
  - B = the next-expiring contract among them, at most 4 months after A.
  - No index table is used: for these roots, the next liquid contract is the index's next month.
- **Trade:** long B, short A, equal notional, from the BD0 settlement to the BD9 settlement:
  ret = r_B − r_A minus the cost.
- **Events:** an event counts only if both contracts settle on BD0, BD4 and BD9. Counted before the freeze (no return
  computed): 1,250 events in 195 months, about 6.4 roots a month. CL has only 63, because its m+2 contract is often
  not in the top three.
- **Costs:** 2/4/6 bp a round trip on one leg's notional. A CME calendar spread trades as one instrument at about one
  tick (CL 0.01 on about $70; grains a quarter cent), plus fees.
- **Decided series:** the monthly mean over the roots with an event.
  - **PASS** if NW t (lag 3) ≥ 2.8 at 2 bp, the 4 bp mean is > 0, and both halves are > 0.
- **Reported, not decided:**
  - the pre-roll window (BD0→BD4) and the roll window itself (BD4→BD9);
  - energy only;
  - by root;
  - by year;
  - 6 bp.

## Supply, break-even, power and forecast (`CLAUDE.md` step 4)
- **Supply:** about 78 root-events a year, in every month.
- **Break-even.** One roll month earning a 3.6%/yr index-level cost (Mou, abstract) is about 30 bp a month if all of
  it showed in a 9-day spread move, against 2 bp of cost. Post-2010 effects are likely far smaller.
- **Power.** The monthly mean over about 6 roots has an assumed standard deviation of about 0.6% (a 9-day calendar
  spread move, about 1.2-1.5% per root, partly diversified). Over 195 months, t ≈ edge/0.6% × 14:
  - 2.8 at 12 bp;
  - 4.7 at 20 bp;
  - 2.3 at 10 bp.
  So power is about 0.9 at 20 bp and 0.3 at 10 bp.
- **Forecast (Ioannidis):**
  - family carry_tradfi: 2 of 6 decided passed (`scripts/base_rates.py`);
  - prior π ≈ 0.25: a real, mandated payer, but well known since 2010, index money has shrunk relative to open
    interest, and some funds roll earlier or further out;
  - power about 0.6 over plausible sizes;
  - **P(PASS) ≈ 0.25 × 0.6 + 0.75 × 0.0026 ≈ 15%**, PPV ≈ 0.99.

## Pre-mortem: "it failed because…"
1. **The effect was arbitraged away after 2010.** Front-running became known, and the index roll is now absorbed by
   others ahead of time. The pre-roll and roll windows show where any move sits.
2. **The generic contract rule picks the wrong B for some roots** (a non-index month in the top three). That adds
   noise, not bias. By root shows it.
3. **Seasonal curve moves swamp the roll** (grain harvests, natural gas winter). They are not tied to BD0-BD9, so they
   add noise. By root and by year show it.
4. **Thin coverage on CL**, the largest index weight (63 events). Energy-only is reported.
5. **Costs above one tick for wider spreads** (livestock, platinum). 4 and 6 bp are reported, and the decision needs
   the 4 bp mean > 0.

## What the author has seen
- R505/R506 on the same settlements: term-structure carry, roll yields between contracts.
- The event counts above.
- No calendar-spread return over the roll window was computed.

## Trials
- **This round:** 1 (the decided series). Its windows and subsets are reported, not decided.
- **Program trials:** 9,785,790 before, 9,785,791 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_roll_frontrun.py` | 7eedd850f877cfc0230ea94cc6d233a83f448cf695ad5e00e895fbb9fe60ce0c |
| `tests/test_roll_frontrun.py` | 4756faf01b5c7ce180682e4d929dc81f3f0dc15e6ca0277feedc680b3a90e383 |
| `scripts/run_cmeterm_v3.py` | 98064ca0ee4ad11dfe610b9efcf4eddab64193c9c3a078385761bf38cd53c068 |
| `scripts/run_cmeterm.py` | 0d035322383ebac8df92922ed2edd214b17988e81cb5d1edb4aacfb0ae48e08a |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `lab/prereg.py` | 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 |
| `data/databento/cmeterm_v3/manifest.csv` | cb4368c1291b7e1c7512406451052b30b52e744b0d9b66da03622e32cc448d68 |
| `data/databento/cmeterm_v3/manifest_defs.csv` | 64d39386b1a6792aef895547010bd1f41c3730467992a2b5b84612c382b9ad90 |
| `data/databento/cmeterm_v2/resolve.json` | 8580ec72a4ecff16dd94ad0981fe26afc00c0f12f6b6d8b02288fe0417cc0a7e |
| `data/databento/cmeterm_v2/manifest_defs.csv` | af3855623279bcdba24dfc06969300e4c9670416ba0c803539ab3cae9c96e456 |
