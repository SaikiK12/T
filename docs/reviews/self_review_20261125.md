# Self-review 3, 2026-11-25: the first ten cycles under rule 11 ("reflect more than I produce")

- **What this is.** Ten cycles of my own choices as data (L036-L045), from the owner's correction of 2026-11-24 to
  today.
- **Previous review:** `self_review_20261124.md`.

## The ten cycles
| # | Subject | Lens | Kind | Outcome | Changed a money decision? |
|---|---|---|---|---|---|
| 1 | Why the design gap persists | Who pays | reflection + one measurement | Gap = risk premium (liquid) + capacity rent (thin). Kraken's mark low on 2025-10-10: −43.8% | yes: Kraken lane 1.5x only at 5% MM |
| 2 | He, Manela, Ross & von Wachter, read in full | Borrow a field (theory) | reading | Funding above cash = price of leverage, bounded by W/m; decay is the default | framework only |
| 3 | Our book's price legs | What my engine cannot see | reflection + measurement | Entry-gap convergence is real but small on executable prices (+1%/yr); Kraken spot-perp dropped on fees | no (small) |
| 4 | The closed-market class | Pólya: have I seen it before? | reflection + measurement | The lab held 11 rounds on it; capacity about $5k a trade | sized a family |
| 5 | Speed of proof for the weekend fade | Derive the design from the noise | reflection + reading (Nagel) + measurement | Balanced book: SD per weekend at 34-56%, power at half the edge 92% against 32%; one of my two predictions failed | speed of proof |
| 6 | R530 frozen; margin rule read | The owner's reach | lane + reading | Isolated margin: size is capital-bound (about $1k a trade at €10k) | yes: sizing |
| 7 | Why R508 fell in 2026 | Decompose by source (López de Prado) | reflection + measurement | The book earns dispersion both ways; dispersion fell threefold. "Pays in sell-offs" (**wrong**) | yes: expectation cut 2-3x |
| 8 | Trend or regime, on R525's 5.7 years | Longest series | reflection + measurement | −30% of the mean level a year (t −5.2); pays after rallies; non-Kraken ≈ 0 in 2026; dated forecasts | yes: money case narrowed to Kraken |
| 9 | Can the class grow? Census of 7 venues | Follow the plumbing | reading (venue docs) | Every new venue copies the floor; the class has no pipeline | strategy: pipeline elsewhere |
| 10 | This review | — | review | — | — |

## Outcomes by kind
- **Tests run: 0.** One lane frozen (R530). Every measurement was descriptive, on seen data or recorded books, and
  named by a reflection first. Rule 11 was followed.
- **What changed the money plan (5 of 9 cycles):**
  - deep reads of the lab's own data: cycles 4, 7 and 8;
  - primary venue rules: cycles 1, 6 and 9.
- **Theory readings (He et al., Nagel)** changed no money decision directly. They made every later analysis sharper:
  the W/m barrier, decay as the default, the reversal as a liquidity payment, and the balanced book.
- **The largest single change came from the cheapest work:** cycle 8 regressed returns the lab already had on disk.
  It reversed a claim made to the owner the cycle before, and cut the money case to one sleeve.

## Claims I made to the owner, scored
| Claim (date) | Status now |
|---|---|
| Kraken thin coins: €3-8k a year after tax (11-24) | cut 2-3x (cycles 7-8) |
| Weekend fade: $7-23k a year (11-24) | cut to about $2k at the €10k stage (cycle 6) |
| "The sleeve pays most in sell-offs" (11-25, cycle 7) | **reversed** by cycle 8: it pays after rallies |
| Executable-price convergence worth about +1%/yr (11-24) | stands, small |
| The balanced weekend book has about half the noise (11-25) | stands, structural; its mean is in-sample |
- **Pattern:** my first Fermi sizes were optimistic every time, cut by a factor of 2-10 within two days. Each first
  estimate used the measurement I had just made (depth, in-sample average) and left out the binding constraint
  (capital, margin) and the decay.

## Failure modes in these ten cycles
1. **A claim left the lab before it met the longest series** (cycle 7). Corrected the next cycle (L044).
2. **The story that found a book replaced the measurement of what it earns** (L043). For about ten days I described
   R508 as "the floor" when it earns two-way dispersion.
3. **Sizing by the last measurement, not the binding constraint** (L042), and sizing without the decay (cycle 8).
4. **The lab's own record forgotten** (cycle 4, L040). Promoted into step 0.
5. **Overdue routine:** the method reading due at cycle 9 was missed. It is done this cycle.

## What a better researcher would have done
- **Run the 5.7-year decomposition (cycle 8) before writing the capital plan** (`answers_20261124.md`). The plan's
  expectations were set from whole-sample averages of a decaying family.
- **Asked "can the class grow?" at cycle 2,** when He et al. showed decay. Cycle 9's census was a few hours of
  reading.
- **Kept a scoreboard of claims made to the owner** (the table above), updated every cycle, so reversals are visible
  at once.

## Unasked work worth more than the plan (ranked for real money)
1. **Check the stake rule against the sign the book actually takes.**
   - The wick work (11-24) and the "Kraken 1.5x" rule were reasoned for long-alt Kraken accounts. Cycle 7 shows the
     book is often **short** Kraken alts.
   - A short account dies on an up-spike, not a down-spike. The decisive number is Kraken's mark **high** on squeeze
     days for the coins the book shorts.
   - `stake_ticket.py`'s `worst_move` handles mixed accounts, but the leverage rule's evidence did not.
2. **Pre-commit the December decision.** Write now what each read's outcome triggers: which stake, which venues,
   what size. The forecasts are dated (cycle 8); the actions should be too, so the decision is not improvised under
   the result's influence.
3. **Pre-listing perps: count the events** (cycle 9's next step).
4. **The method reading** (Bailey et al., minimum backtest length). It bears on R530, whose design was selected on
   23 weekends.

## Rules
- **Promoted** (the same lesson twice: L042 capacity, then L043/L044 decay): step 4 of the one-page approach in
  `CLAUDE.md` now reads "a Fermi size and the capacity: the smaller of the market's and the owner's under the
  venue's margin rule, net of the measured decay".
- **Flagged for review, not pruned:** "for a design gap, the sign comes from the design (long the floorless venue),
  never from a short window" (`CLAUDE.md`, step 4).
  - Cycle 7 found the design-signed gap was negative in four of five winter months on Kraken + Hyperliquid, while
    the sign-agnostic book earned.
  - The rule guards against short-window sign flips, which is still right. Its premise, that the design fixes the
    sign, is not.
  - Decide when R527 (design-signed) and R509 (sign-agnostic) are read in December.
