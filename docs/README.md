# Documentation

[Repository home](../README.md) · [Document index, grouped by role](../README.md#docs)

**Open these first:**

| Need | Start here |
|---|---|
| What is true now | [STATUS](STATUS.md), rewritten in place |
| Understand the project without running code | [Guide en français](guides/START_HERE.fr.md) |
| Install, inspect, test or run the software | [Operator guide](guides/OPERATIONS.md) |
| The research rules | [GATES](GATES.md), [FOUNDATION](FOUNDATION.md) and [AGENTS.md](../AGENTS.md) |
| Get everything back without Claude | [HANDOVER](HANDOVER.md) |
| Any other note, audit or review | [The grouped index](../README.md#docs) |

**How this folder is laid out:**
- **The top level is flat on purpose.** Frozen PREREGs, pinned inputs and the source intake link to these paths, so
  files here are not moved or renamed. The [root index](../README.md#docs) groups them by role instead:
  - live rules;
  - venues and costs;
  - data;
  - evidence;
  - methods;
  - what the owner sent;
  - audits;
  - history.
- **Subfolders, for new writing:**
  - `guides/`: how-tos for people;
  - `reviews/`: dated reviews and audits, named `<topic>_<yyyymmdd>.md`;
  - `provenance/`: dataset identities;
  - `handover/`: operational handoffs;
  - `loop/`: the edge loop, paused since 2026-11-13.
- **Authorities:**
  - [`registry/methods.csv`](../registry/methods.csv) for current methods;
  - [`registry/rounds.csv`](../registry/rounds.csv) for registered rounds;
  - each lane's own PREREG and FINDINGS for its exact result.
  - This guide does not copy their status.
