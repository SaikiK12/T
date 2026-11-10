# Cboe delayed option chains: QQQ, SPY and SPX (data branch)

Written only by `.github/workflows/claude-cboe-recorder.yml`, which runs `scripts/record_cboe_chain.py` from the
default branch once in each New York window on weekdays: pre (08:00-09:29) and post (16:20-18:59). Public delayed
quotes (cdn-api.cboe.com), no key. Cboe serves only the current day's chain, so a day not recorded is lost.

Layout: `YYYY-MM-DD/{pre,post}_{QQQ,SPY,SPX}.parquet` (New York date), columns as in the script's COLS.
Used by M486 (dealer gamma levels as a risk filter; needs about 120 sessions). 2026-11-10 pre was recorded in the
Claude container and copied here.
