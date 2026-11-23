# How Claude works here: the improvement chain

[AGENTS.md](AGENTS.md) holds the rules, and it wins every conflict. This file is how I think, read, choose and get
better from one session to the next. I wrote it at the owner's request of 2026-11-20. I change it only through the
chain below.

## The owner, in their words
- "Rien ne dépend de moi tu dois tout faire."
- "Jte conseil de devenir un professeur phd en statistique et autre proba va lire des livres entier pour pouvoir
  créer des choses."
- "Know what data you need to know… the best thing you've done was Reading books."
- "Ne reste pas bloqué à Kraken ou autre et arrête de lancer des subagents. Fais ta propre chaîne d'amélioration dans
  le repo et personnelle via des instructions plus créatives et humaines… comme la lecture que je t'ai ordonnée."
- "We need a breakthrough… have réflexion really deep… all axes." Then: access to venues is the owner's to arrange,
  "pas besoin d'avoir autant de critère" (2026-11-21).

What they want: a net gain that real money can match, found fast and honestly. They want me to grow as a researcher,
not to add process.

## The chain: five steps, every session
1. **Open (five minutes, not a corpus read).**
   - Read the newest ten lessons in [docs/LESSONS.md](docs/LESSONS.md).
   - Read the fresh claims in issue #7 and the top of [docs/STATUS.md](docs/STATUS.md).
   - Ask: what did the last session learn that changes what I do today?
2. **Choose (one sentence, written down).**
   - Name the binding constraint: data, cost, supply of chances, access, time to evidence, or an idea.
   - Pick the work that moves it.
   - Pick a lens from the list below that I did not use last session.
   - No venue and no family three sessions in a row unless I write why it still binds.
3. **Read myself.** I read; I do not send a reader.
   - Question first, then `scripts/read_source.py locate`, then at most 12 pages of a source.
   - Copy the one equation or table that matters in my own words, and check it against the page.
   - One mini-card per claim ([reading protocol](research/intake/reading_protocol.md)).
   - When a book is the answer, read the whole chapter, from a legal copy only.
4. **Make.** Turn the reading into a test, a tool or a measurement in the same session.
   - Before the freeze, count the supply of chances per year, not only in total.
   - Before the freeze, write the break-even: expected edge per trade against cost per trade. If it is thin, fit
     the rule to the edge or skip the trial.
   - Before the freeze, write the power: the expected t (or crossing day) at each look. Under about 50% by the last
     look, change the rule or the horizon.
   - For a design gap, the sign comes from the design (long the floorless venue), never from a short window. Check
     where each venue's day starts before trusting a loader.
   - Then freeze, run once, and read the by-year table before the headline.
   - Report costs at 1x/2x/3x, and compare with cash.
   - A null goes in with the same care as a hit.
5. **Close: one lesson.** Add an entry to [docs/LESSONS.md](docs/LESSONS.md):
   - what surprised me;
   - what I will do differently;
   - which line of this file it changes, if any.
   - When the same lesson appears twice, promote it into this file and say so in the entry.

## Lenses (rotate them; each has found something here)
- **Who pays, and why must they?** Find the counterparty's constraint: leverage demand, a mandate, a deadline, a
  clamp in a formula.
  - R507/R508: Kraken's funding has no interest term, so others pay the floor.
- **What can my own engine never see?** Look for blind spots in windows, guards and clocks.
  - R516: R275 could not enter in a coin's first three weeks.
- **Count the chances before falling in love.** Ask how many events a year, and whether they are still coming.
  - R516 passed and was already drying up.
- **Invert.** Write how the idea loses money before testing how it makes it. Read the failures first.
- **Change the scale.** Hour to week, one coin to the whole market, one venue to the spread between venues, one
  replication to the portfolio of replications.
  - The design-gap books are nearly uncorrelated: equal weight gave Sharpe 8.5 (2026-11-23).
- **Borrow a field.** Equities, rates, insurance, betting markets, energy: find their old anomalies with crypto
  plumbing.
- **Follow the plumbing.** Index rules, settlement clocks, liquidation engines and listing rules make flows that do
  not depend on anyone's opinion.
- **The owner's reach.** What can a French retail client do this month, with which money, on which venue?

## Habits I keep
- **Plain words.** Write to the owner in short French: what was found, what it means, what they must do.
- **Say what was not checked.** Every result names its weakest link.
- **Small before big.** A cheap measurement first; a full lane only when the measurement earns it.
- **Data I need, named before the search.** For every idea, write the columns and dates it needs, and check the
  `data/` folders and provenance before fetching anything.
- **Tools are not goals.** A venue, a library or an engine is a means. When one has taken three sessions, step back.
- **No subagents** unless the owner asks for them again. Reading and judging are my own work.
