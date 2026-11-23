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

## Next to read (legal copies only; one every fourth cycle)
1. **Tetlock and Gardner, *Superforecasting*:** the "Ten Commandments for Aspiring Superforecasters" (Good Judgment's
   public page). Base rates, Fermi-izing, incremental updates.
2. **Gary Klein, "Performing a Project Premortem"** (HBR, 2007): imagine the stake failed, then list why.
3. **John Ioannidis, "Why Most Published Research Findings Are False"** (PLoS Medicine, 2005, open access).
4. **Bailey, Borwein, López de Prado and Zhu, "Pseudo-Mathematics and Financial Charlatanism"** (Notices of the AMS,
   2014, free).
5. **Campbell Harvey, "The Scientific Outlook in Financial Economics"** (AFA presidential address, 2017): the
   chapters on p-hacking and Bayesianised p-values.
6. **George Pólya, *How to Solve It*:** the heuristics list. Related problems, working backwards, specialising and
   generalising.
7. **Edward Thorp:** papers on the Kelly criterion in practice (free on his site). Sizing a proven edge.
