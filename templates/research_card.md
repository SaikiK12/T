# Research card: SRC__-___ <short name>

Write a card only for a source that was actually read, and put it at `research/intake/cards/<SRC id>.md`. In the same
commit, update that source's `received_scope` in its catalog row to the exact pages, sections, version or commit read.
Reading a paper does not earn a strategy: this card earns one finite experiment only if section 3 is complete.

Label every statement in sections 1 and 2 as **published result**, **working-paper result**, **exchange rule** or
**new hypothesis**. Do not copy an effect size without its sample, horizon and cost assumption.

## 1. What the source says
- Mechanism:
- Market and venue:
- Data granularity and horizon:
- Observable features and target:
- Execution, fee and rebate assumptions:
- Latency assumptions:
- Queue and fill assumptions:
- Adverse-selection treatment:
- Statistical design and multiplicity handling:
- Effect size (with its sample and cost basis):
- Caveats the authors state:

## 2. What we can reproduce
- Data we hold or record that matches each input (path, venue, clock, since when):
- Inputs we cannot observe, and what that removes from the test:
- Costs and latency that apply from this container (round trip, fee tier):

## 3. The experiment it earns, or none
All four are required; if one is missing, write "none" and stop.
- Mechanism (one sentence):
- Observable inputs, all available to us:
- Causal decision timestamp (which clock orders the events):
- Falsification condition (the result that closes it):
- Queue id (`registry/methods.csv`) and lane id once a PREREG is frozen:
- Trials it adds to `registry.program_trials()`:
