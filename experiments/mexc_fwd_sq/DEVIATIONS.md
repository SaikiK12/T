# Deviations: mexc_fwd_sq (R218)

Operational notes after the freeze. The PREREG, the frozen script and every rule are unchanged.

## 2026-11-11, MEXC requests paced on GitHub's runners (no ticket affected)
- Run 42990781696: MEXC refused five of R218's kline requests (PEPE, PUMPFUN, QNT, RLC, TAO) with code 510
  ("Endpoint rate limit exceeded ... scope: IP"), right after R215 used the same runner's IP. The script stops on any
  failed fetch ("no tickets this run"), so it wrote nothing that run and R221 was skipped.
- R218 fetches through `scripts/forward_mexc.py`'s client, so the workflow now runs it as R215 and R220 run:
  through `scripts/run_paced_mexc.py` (MEXC requests at most every 0.25 s, each 510 retried after 5, 15 and 45 s),
  with up to 3 attempts 180 s apart. `scripts/forward_mexc_sq.py` and `lab/mexc.py` are unchanged; a fetch that
  succeeds returns the same data, so the rule and every value are unchanged.
