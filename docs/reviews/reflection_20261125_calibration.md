# Reflection 2026-11-25 (cycle 3 of the day): how good are my own probabilities, and why do my first drafts lean clean?

- **The lens:** "invert", turned on myself.
- **The subject:** register Q25 (are the lab's written forecasts calibrated?), widened to my first drafts.
- **Not options again.** This is a method question that every lane depends on.

## 0. What the lab already knows
- **Forecasts are scarce.** The first room counted "309 rounds; only 4 numeric forecasts, 1 scored"
  (`room_20261125/synthesis.md:36`).
  - Since then the register carries written predictions: O3b, O7b, Q26, Q16, Q01, O1-O7.
  - December's reads carry cycle 8's numbers (`december_decision_20261125.md` §4).
- **Today's scored predictions:**
  - O3b: 1 of 4 right;
  - O7b: 2 of 3;
  - Q26 and Q16: held.
- **Today's first drafts were corrected seven times,** each by a critic, an audit or my own second look, and every
  time toward a cleaner story than the data:
  - TSLA "15-45×" crypto; really about 2× gross with gross (L053);
  - an assumed $40bn TSLA volume; measured $13bn (L053);
  - a contradicting snapshot called a "fit" (L053);
  - SPX charm "closed at Fermi"; parked, since the window was not measured;
  - Saturday "priced right"; right for a straddle, cheap on variance, and rich over 2022-25 (L054);
  - "the makers priced it away", then "mostly the world": both sides moved (L055);
  - "makers chase last year": fits Sunday only.
- **The field.** Brier's score, (p − outcome)² averaged, is the standard. Murphy's decomposition splits it into
  reliability (calibration), resolution, and the base rate's uncertainty. Tetlock's forecasting tournaments found
  that well-calibrated forecasters update in small steps and keep wide bands early.
  - Tetlock's own text is not read: the Good Judgment page sat behind a Cloudflare challenge on 2026-11-24, and no
    bypass is used (`docs/METHOD_LIBRARY.md`).

## 1. The economic question
How far should my written probabilities be shrunk before they choose the next experiment (value × p ÷ cost) or size
a stake (Thorp)? If my p is 2× too high, the register's order is wrong and stakes are too large.

## 2. The mechanism: what produces the clean-story errors
- **I write the conclusion while the data is half in.** A snapshot or one season arrives, and I write a status word
  ("answered", "dead", "alive", "closed at Fermi"). The rest of the data then contradicts it.
  - O3a was "answered" from two snapshots.
  - O1 was "closed" without measuring the window that mattered.
- **I compare whatever numbers are at hand,** not like with like: gross against net, an assumed volume.
- **I explain a change with one cause** before measuring the other side (L055).
- **The common root:** the status word comes before the decisive observation that the page itself names.

## 3. The barrier
None outside me. Inside, it is the pleasure of a finished paragraph (Feynman: "you are the easiest person to fool").

## 4. Fermi
- **The cost of wrong status words.** Wasted cycles, or a dropped lead.
  - O1 would have been dropped.
  - O3a's "Saturday priced right" would have hidden a 4-year rent, had the history read not been registered.
- **The value of calibration.** With 30 scored forecasts, a Brier score shows whether my p carries information
  beyond the base rate. Until then, the honest prior for "my p" is the family base rate, shrunk.

## 5. What we have that others do not
Every forecast is timestamped in git before its outcome, so the score cannot be fooled after the fact.

## 6. The cheapest decisive observation
- **A ledger of every written forecast with its outcome,** scored mechanically, now. The room's extractor is building
  the first list (`room_20261125c/forecast_extract.md`). I verify it and write `registry/forecasts.csv` plus a
  scoring script.
- **A change in how I write, not a new check (rule 11).** A status word (answered, killed, alive, closed) may follow
  only the decisive observation that the page names. Before that, the word is "leaning", with the side and a
  probability that enters the ledger.
