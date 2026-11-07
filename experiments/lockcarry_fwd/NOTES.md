# lockcarry_fwd (R405): abandoned before any observation

R405 was frozen on 2026-11-05 and abandoned the same hour, before any offer or lock was recorded. Its frozen
runner (`scripts/forward_lockcarry.py`) asked FRED for the T-bill with a User-Agent that FRED rejects (the requests
time out), so no T-bill value was ever known and the rule never priced an offer. Its runner also failed to write
status.json until its journal folder was created by hand; the only journal file is that empty status.

The same rule continues as R406, `experiments/lockcarry_fwd2`, with a runner that sends FRED requests with Python's
default User-Agent. Nothing else changed: the rule file `scripts/lockcarry_rule.py` is the same file, same sha256.
