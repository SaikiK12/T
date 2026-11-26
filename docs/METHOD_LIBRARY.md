# Method library: the best advice on how to do research, read at the source, and the rules it gave

- **Why.** The owner, 2026-11-23: my best work came from reading precise passages of good books. My working rules
  must come from the best sources, not only from my own mistakes, and they must keep improving.
- **How it is used** (`CLAUDE.md`, chain step 5):
  - every fourth cycle I read the next unread source below;
  - I copy the passage that matters;
  - I change `CLAUDE.md` only if the passage improves a concrete decision.
  - "Read, no change" is a valid outcome.

## Read
### Richard Feynman, "Cargo Cult Science" (Caltech commencement, 1974)
Read 2026-11-23, in full, from a public HTML copy of the talk: https://sites.cs.ucsb.edu/~ravenben/cargocult.html.
The Caltech PDF is a scan without text.
- **The principle.** "The first principle is that you must not fool yourself--and you are the easiest person to fool."
- **Millikan.** Later measurements of the electron charge crept up slowly. "When they got a number that was too high
  above Millikan's, they thought something must be wrong--and they would look for and find a reason… When they got a
  number close to Millikan's value they didn't look so hard."
- **Leaning over backwards.** "You should report everything that you think might make it invalid--not only what you
  think is right about it."
- **The rats.** Repeat the other person's experiment under condition X first, then change to Y.
- **Rules it gave:**
  - hunt bugs as hard when a result pleases as when it fails;
  - every FINDINGS lists what could invalidate it;
  - reproduce the baseline before testing a variation.

### Richard Hamming, "You and Your Research" (Bell Labs talk, 1986)
Read 2026-11-23, in full (14,458 words), from the transcript at https://www.cs.virginia.edu/~robins/YouAndYourResearch.html.
- **Important problems.** "If you do not work on an important problem, it's unlikely you'll do important work."
  Important means having "a reasonable attack", not just a big prize.
  - "Great scientists have thought through… a number of important problems in their field, and they keep an eye on
    wondering how to attack them."
- **Great Thoughts Time.** On Friday afternoons, only great thoughts.
- **Classes, not instances.** "I would never again solve an isolated problem except as characteristic of a class."
- **Turn it around.** "What appears to be a fault, often, by a change of viewpoint, turns out to be one of the
  greatest assets you can have."
- **Ambiguity.** "Believe the theory enough to go ahead; they doubt it enough to notice the errors."
- **The open door.** Those who work with the door closed after ten years "don't quite know what problems are worth
  working on".
- **Rules it gave:**
  - keep a short list of the lab's important problems with their attacks, and reread it at each open step;
  - when a mechanism works, solve its class (R525 did);
  - turn a defect into an asset;
  - believe enough to act, doubt enough to audit.

### Marcos López de Prado, "The 10 Reasons Most Machine Learning Funds Fail" (2018)
Read 2026-11-23, pp. 4-5 (pitfalls 1-2 and their solutions) and the summary table on p. 18. Source: GARP's hosted PDF,
https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf. Pitfalls 3-10 are not read.
- **The Sisyphus paradigm.** "It takes almost as much effort to produce one true investment strategy as to produce a
  hundred."
- **The meta-strategy paradigm.** "Tasks of the assembly line are clearly divided into subtasks. Quality is
  independently measured and monitored for each subtask."
- **Research through backtesting.** "Take some data, run it through an ML algorithm, backtest the predictions, and
  repeat the sequence until a nice-looking backtest shows up… It typically takes about 20 such iterations to
  discover a (false) investment strategy." Also: "feature importance is a research tool, and backtesting is not."
- **Rules it gave:**
  - explain why an edge pays (decompose its PnL by source, coin, venue and regime) before running another backtest;
  - run the lab as stations (data, mechanism, test, costs, portfolio, money), each with a measured quality.

### Edward O. Thorp, "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market" (2006)
- **Read 2026-11-24:** section 7 (7.1-7.4, pp. 405-415 of the *Handbook of Asset and Liability Management*,
  chapter 9). Source: the copy at https://www.gwern.net/doc/statistics/decision/2006-thorp.pdf. The 1997 conference
  version is also posted at https://sites.oxy.edu/lengyel/M330/thorp/paper.htm. Sections 1-6 and 8-10 are not read.
- **Taken ahead of the queue order.** The next decision is the stake's size, and Thorp bears on it directly.
- **The formulas** (checked against the page):
  - f* = (m − r)/s², and g(f*) = S²/2 + r: the best growth depends only on the Sharpe ratio;
  - g(c f*)/g(f*) = c(2 − c): half Kelly keeps 3/4 of the growth;
  - the chance of ever falling to a fraction x of the start is x^(2/c − 1): losing half is 1/2 at full Kelly and
    1/8 at half.
- **The passage that matters.** "To the extent me is an uncertain estimate of mt, it is wise to assume mt < me and
  to choose f < fe* by enough to prevent g ⩽ 0." With m_t = m_e/2, full Kelly grows at zero. Systems "may be partly
  or entirely based on data mining", and "systems that do work attract capital".
- **Jumps limit leverage below f*.** In October 1987 the index fell 23% in a day. For Berkshire, Kelly said 6.2x and
  Thorp chose 2.0, the maximum allowed.
- **Rules it gave:**
  - Size by the shrunk edge (at most half the in-sample level) and by the jump that can happen, never by the
    in-sample variance.
  - For the design gap the jump is a venue failing. `scripts/stake_kelly.py` gives the break-even failure rate,
    (L m − r)/(1 − recovery).
  - Stake at most half the growth-optimal fraction.

### John P. A. Ioannidis, "Why Most Published Research Findings Are False" (PLoS Medicine, 2005)
- **Read 2026-11-24:** pp. 1-3 of 6 (the framework, the bias model, the corollaries, Tables 1-3, Figure 1). Open
  access: https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.0020124.
- **Taken in place of Tetlock.** Good Judgment's commandments page sits behind a Cloudflare challenge, and no
  workaround is used. Ioannidis answers the same question with an equation.
- **The equation** (Table 1, checked against the page):
  - with prior odds R, power 1 − β and size α, PPV = (1 − β)R / (R − βR + α);
  - a finding is more likely true than false only if (1 − β)R > α;
  - with bias u, PPV = ([1 − β]R + uβR) / (R + α − βR + u − uα + uβR), which falls as u rises.
- **The passage that matters.** "Corollary 3: The greater the number and the lesser the selection of tested
  relationships in a scientific field, the less likely the research findings are to be true." Hypothesis-generating
  fields "should have extremely low PPV". At 9.8 million trials, this lab is one.
- **Measured here** (`scripts/base_rates.py`, 244 FINDINGS):
  - decided pass share: carry 64%, settle 43%, carry_tradfi 33%, cross-section 23%, calendar 23%, flow 17%,
    events 14%;
  - charts, options, micro, portfolio and vaults: 0%;
  - all families: 26%.
  - Past passes outside carry mostly failed their confirmations, so their share overstates the prior.
- **Rules it gave:**
  - Every PREREG writes a forecast: the family's pass share, the prior, the power, and P(PASS) (template section
    "Forecast").
  - A test under about 10% P(PASS) needs a written reason.
  - The self-review scores those forecasts.

### George Pólya, *How to Solve It* (1945; Penguin edition with a foreword by Ian Stewart)
- **Read 2026-11-25:** the publisher's official sample (Penguin, `9780140124996-sample.pdf`): Stewart's foreword in
  full and the book's table of contents, which lists the dictionary of heuristics. The book's own chapters were not
  read; there is no legal free copy, and course PDFs of the whole book were not used.
- **The four phases** (Stewart's summary of Pólya's opening list): understand the problem; "try to use experience
  from related problems to plan an attack"; carry out the attack; "ask yourself whether you really believe the
  answer you've got".
- **The dictionary entries** that the table of contents names include "Have you seen it before?", "Do you know a
  related problem?", "Look at the unknown", "Working backwards", "Specialization", "Generalization" and "Auxiliary
  problem".
- **The passages that matter:**
  - "Pólya places a great deal of emphasis on the consideration of related problems whose solution is already known
    and on reasoning by analogy."
  - "Did you use all the data? Does the statement of the problem involve information that you haven't used?"
  - Schoenfeld, quoted by Stewart: competent problem-solving is largely "the ability to monitor and assess what one
    does while working problems", the "resource allocation during thinking".
  - Stewart: "someone has to have the two pieces of the puzzle… in his or her head at the same time, otherwise
    nobody will spot the possible connection."
- **The decision it changes.** It is the second time the same lesson has reached me (L040 was the first): in cycle 4
  I nearly re-derived a class the lab had studied in eleven rounds, and the LLP's inventory had been recorded for two
  weeks without a question.
  - The one-page approach in `CLAUDE.md` gains a step 0: what the lab already knows (its rounds on the mechanism)
    and which recorded data no question has used.
  - Promoted per the chain's rule.

### Bailey, Borwein, López de Prado & Zhu, "Pseudo-Mathematics and Financial Charlatanism" (Notices of the AMS, 2014)
- **Read 2026-11-25, in full:** sections 1-9 and the proofs in appendices 10.1-10.4; the Python listing in 10.5 was
  skimmed.
  - Legal copy: the authors' own `davidhbailey.com/dhbpapers/backtest-pseudo.pdf` (April 2014 version).
  - The AMS copy returned 403 and was not bypassed.
- **The equations, checked against the page:**
  - expected best in-sample Sharpe of N skill-less configurations:
    E[max_N] ≈ (1 − γ)Z⁻¹(1 − 1/N) + γZ⁻¹(1 − 1/(Ne)), with γ ≈ 0.5772 (Prop. 2.1);
  - minimum backtest length: MinBTL ≈ (that expression / E[max_N])² < 2 ln N / E[max_N]² years (Th. 3.1).
  - With 5 years of data, no more than about 45 independent trials before a Sharpe of 1 is expected from noise.
- **The passage that matters.** "A researcher that does not report the number of trials N used to identify the
  selected backtest configuration makes it impossible to assess the risk of overfitting."
  - Also, under compensation effects (a global constraint, or serial dependence, Props. 6.1-6.3), "good backtest
    performance is an indicator of negative future results".
- **Checked against this lab:**
  - **R530's balanced book.** The `rel` variant was picked from R462's 32 cells. SE of the A weekend mean is about
    27.7/√17 ≈ 6.7 bp, and E[max_32] ≈ 2.0, so the selection haircut is about 14 bp of +52. Thorp's halving (26 bp)
    is the larger haircut, and it is the one the power calculation used.
  - **Its SD reduction is a property of the design, not a selected statistic,** so it is not shrunk.
  - **Compensation effects bear on the carry family.** Cycles 7-8 found dispersion is regime-driven. A pair selected
    for its strong recent months (the Kraken pairs, +31%/yr in their first ten months) may have been selected at a
    peak, and so may do worse than the family's average. The dated forecasts (cycle 8) already lean that way.
- **Decision changed: none.** The lab already counts trials per round and across the program, halves in-sample
  edges, and forward-tests selected variants. Read, no change.

### Campbell R. Harvey, "Presidential Address: The Scientific Outlook in Financial Economics" (Journal of Finance 72(4), 2017)
- **Read 2026-11-26:** sections V-VI (the minimum Bayes factor, Tables II-III) and IX (recommendations). Author's copy:
  https://people.duke.edu/~charvey/Research/Published_Papers/P131_The_scientific_outlook.pdf.
- **The passage that matters** (p. 1424): "If a test is based on a normal approximation and the z-score is given by
  Z, then the MBF is simply exp(–Z2/2)… a z-score of 2.0, which has a p-value of 5%, corresponds to an MBF of 0.14."
  - With prior odds PO (null : alternative), P(null | data) ≥ MBF·PO / (1 + MBF·PO).
  - The "symmetric-descending" version, SD-MBF = −e·p·ln(p), is the less generous one.
  - Table III: for a 5% chance that the null is true, t must reach 2.43 at even odds and 2.94 at 4:1. I reproduced
    both.
- **Decision changed** (written before any December read; `docs/reviews/december_decision_20261125.md`, addendum
  2026-11-26b, corrected the same night after the room's critic, `docs/reviews/room_20261126/critic_harvey.md`).
  - **The prior is π, the probability that the effect is real,** not the ledger's P(PASS). It is recovered as
    π = (P(PASS) − α)/(power − α), with each lane's stated power and size.
  - **The reference is Student's t** with the look's days − 1, because the lanes' NW t on 20-90 overlapping days is
    not normal. P(null) floors at a pass exactly at the bar:

| Read (bar, df) | P(PASS) | power | π | MBF (normal) | SD-MBF (normal) | **SD-MBF (Student-t)** |
|---|---|---|---|---|---|---|
| R510, 30 days (t 2.5, 29) | 0.60 | 0.84 | 0.71 | 1.7% | 5.6% | **7.4%** |
| R523, 20 days (t 3.0, 19) | 0.45 | 0.78 | 0.55 | 0.9% | 3.4% | **7.4%** |
| R527, 20 days (t 3.0, 19) | 0.40 | 0.86 | 0.44 | 1.4% | 5.1% | **10.9%** |
| R509 look 1 (t 2.5, 89) | 0.45 | 0.60 (assumed) | 0.75 | 1.5% | 4.8% | **5.3%** |
| R521, 30 days (t 2.5, 29) | 0.30 | 0.67 | 0.42 | 5.7% | 16.9% | **21.4%** |
| R520 look 1 (t 2.5, 89) | 0.10 | 0.30 | 0.31 | 8.9% | 24.8% | **26.8%** |
| R520 look 2 (t 2.0, 179) | 0.10 | 0.75 | 0.10 | 55.7% | 78.0% | **78.4%** |
| R524 look 1 (t 2.5, 89) | 0.10 | 0.77 | 0.12 | 23.7% | 51.1% | **53.7%** |
| R530, 20 weekends (p < 0.01 one-sided) | — | — | 0.20 | 21.1% | 46.0% | (bootstrap) |
| R530, 30 weekends (p < 0.04) | — | — | 0.20 | 46.4% | 68.7% | (bootstrap) |

  - **The rule is a block only.** If the SD-MBF floor (Student-t) is above 10%, a pass buys a second forward
    period of the same length, not money. Below 10% the floor licenses nothing; the lane's own mapping decides.
  - **Harvey's own example is inconsistent.** His t 2.6 with p 0.014 (p. 1424) does not match the normal two-sided
    p of 0.0093. Do not copy it.

## Next to read (legal copies only; one every fourth cycle)
1. **Tetlock and Gardner, *Superforecasting*:** the "Ten Commandments for Aspiring Superforecasters". Good Judgment's
   page was behind a Cloudflare challenge on 2026-11-24; a library or publisher copy is needed. Base rates,
   Fermi-izing, incremental updates.
2. **Gary Klein, "Performing a Project Premortem"** (HBR, 2007): imagine the stake failed, then list why.
5. ~~Campbell Harvey~~ (read 2026-11-26, above). Was: **Campbell Harvey, "The Scientific Outlook in Financial Economics"** (AFA presidential address, 2017): the
   chapters on p-hacking and Bayesianised p-values.
6. **George Pólya, *How to Solve It*, the book's own chapters:** read the foreword and the table of contents on
   2026-11-25 (above); the chapters need a library copy.
