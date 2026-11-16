# settlelit_fwd (R364): Lighter settlement scalp forward on paper

**Writer lost (2026-11-16).** Last commit e5107fb9 (2026-11-06). `scripts/forward_settlelit.py` and `scripts/record_tape.py` ran as container daemons and stopped with the container on 2026-11-06: 13 decisions, 0 selected, 0 tickets (`journal/status.json`). The registry row stays RUNNING / PENDING. A restart needs an always-on host: its PREREG enters within 5 s of T-10 s on a live book, which no scheduled runner can do. Its final date is 2027-10-28.
