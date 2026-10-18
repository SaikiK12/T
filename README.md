# T

A structured foundation for a crypto-perps research program. The goal is positive PnL, and the rule is that nothing counts as an edge until it survives pre-registration, a null, held-out data and a forward paper test.

**Status:** a scaffold. It was built from reading an earlier Claude Code session, not from the original code and data, which stay on the owner's machine. Start with [`docs/FOUNDATION.md`](docs/FOUNDATION.md) for the conventions and [`docs/AUDIT.md`](docs/AUDIT.md) for the weak points found.

## Use

```
python3 -m unittest discover -s tests -t .     # needs numpy
```

```python
from lab import prereg, registry, gate
prereg.freeze("experiments/<lane>/PREREG.md")                  # once, before any statistic
registry.append("registry/rounds.csv", lane="<lane>", title="...", status="REGISTERED", verdict="PENDING")
gate.go_real(scored_returns, entry_days=entry_days)            # forward tickets, unlevered
```

Rules for contributors: [`AGENTS.md`](AGENTS.md). New lane: copy `templates/lane/`.
