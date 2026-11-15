# prop (qwen3.8-flash)

Verdict: as listed, no edge passes a typical funded-account challenge.

Carry: ~1%/yr with 0.07% max DD is too slow for a 10% target and is already flagged not prop-usable (R202). Daily loss/DD are not the binding constraints; profit target/horizon are.

Unlock short: +3.24% mean per event is attractive, but the tail is fatal under prop rules. The 5% daily loss limit binds first. At 2% equity notional per event, the worst single event hit is -3.55% equity; two such events same day breach 5%. At 3.8% cap, worst event -6.75% breaches daily. At 5% cap, worst event -8.85% breaches daily, and sequential max DD -9.85% leaves no room for concurrency. The reported worst concurrent cluster and max 9 open positions mean simultaneous squeezes can exceed daily loss even with small per-event caps.

The 10% profit target binds the other way. At a rules-compliant 2% cap, expected gain is ~0.065% equity per event. A 10% target needs ~154 events. Recent event flow is ~168/yr, so ~11 months; average flow is much lower. Typical challenge windows are incompatible. Raising size to hit target violates daily/DD because of -132% gross events and extreme funding.

Execution/validation also bind. R265 is gate-0 PARTIAL, not confirmed forward; calendar is today’s snapshot, not point-in-time; events are Binance perps, not MEXC; execution is manual-web; measured costs are only around $10k API size. Do not assume these returns are tradable at prop size.

A rules-compliant variant is conceivable only as a survivable low-return book, not a challenge-passing one: per-event cap ≤2%, portfolio gross cap ≤10–15%, daily new notional ≤2%, max concurrent positions ≤2–3, trailing-funding veto where available, no stop-loss because intrabar path is unknown. This likely keeps max DD under 10%, but expected target completion is too slow.

Min trading days is probably not the main blocker if recent event frequency persists, but cannot be guaranteed on-time.

Cannot know from the pack: intrabar MFE/MAE, trailing funding at entry, true point-in-time calendar, MEXC executable fills/impact at size, forward replication, exact prop daily-loss measurement, and whether R266 tickets will pass.
