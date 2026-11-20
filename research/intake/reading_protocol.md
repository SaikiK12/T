# Reading protocol: question first, locate, then read

- **Asked by the owner (2026-11-20).** Reading was the most useful work. Make it cheaper in tokens and richer in what
  it yields, and know what we need to know before reading.
- **The 2026-11-19 baseline.** Five Haiku readers spent 167k-251k tokens each for 11-26 sources, mostly in targeted
  parts.

## The rules
1. **Start from a question in the bank** (`questions_20261120.md` or later). It names the decision it serves, what an
   answer looks like, and where to scout. Reading with no question is browsing; do it only when scouting zones.
2. **Locate before reading.** Use `scripts/read_source.py`:
   - `fetch URL` extracts a PDF once into plain text per page, cached;
   - `locate ID term ...` ranks pages by how many of the question's terms they contain;
   - `pages ID 12-14 --max-chars 6000` prints only those pages.
   - Never read a PDF page-image by page-image when the text extracts: plain text costs a fraction of the tokens.
   - **Budget:** at most 12 pages a source and 6 sources a question, unless a source is the answer.
3. **Write mini-cards, not summaries.** One card per usable claim, at most about 120 words:
   - `claim`: one sentence;
   - `kind`: published result, working-paper result, exchange rule, regulation or new hypothesis;
   - `formula`: if any, with its symbols defined;
   - `conditions`: sample, venue, horizon, cost basis;
   - `source`: title, legal URL, pages read;
   - `use`: the test or tool it earns here, or "none".
4. **Answer the question in five lines,** then say what is still unknown.
5. **Verify before acting.** A cheap reader (Haiku) locates and extracts. The session re-reads the few pages behind
   any claim that will change a frozen lane, a sizing rule or money, and marks them checked.
6. **Legal sources only:** author-hosted, open-licence or publisher-free texts, arXiv, regulators, and venue docs.
   Never use piracy sites, a paywall bypass or a login. Record what could not be read.
7. **Record exact scopes.** Pages actually read go on the card. A book read in part is never called read.
