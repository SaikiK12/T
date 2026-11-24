# PREREG: closing_momentum_v1 (R528). Intraday momentum into the US cash close on E-mini S&P 500 futures

Freeze with `lab.prereg.freeze()` before the data is downloaded. Never edited afterwards.

- **Registry id:** R528
- **Owner (single writer):** the Claude session that froze it. `scripts/run_closing_momentum.py` is the only writer of
  `experiments/closing_momentum_v1/results/`.
- **Date registered (UTC):** 2026-11-24

**Methods:** M523 (end-of-day momentum from leveraged-ETF rebalancing), on CME futures instead of 24/7 perps.
- **Paper only.**

## Why
- **Wide, not stuck** (`CLAUDE.md` standing rule 7). Six cycles in a row served the funding-design gap. This round is a
  different family, a different market and a different payer, with no tie to crypto carry.
- **Who pays, and why must they?** Leveraged and inverse ETFs must rebalance near the close in the direction of the
  day's move. Option dealers who are short gamma hedge the same way. The flow is mechanical: it does not depend on
  anyone's view (Baltussen, Da, Lammers & Martens, JFE 2021, "Hedging demand and market intraday momentum").
- **The literature's rule.** Gao, Han, Li & Zhou (JFE 2018, "Market intraday momentum"): on SPY, the first half
  hour's return (previous close to 10:00 ET) predicts the last half hour's.
- **Out of sample.** 2018-2026 is after publication. A decay there is the main risk and the main question.
- **The owner's reach.** CME micro E-mini futures (MES) through a regulated broker, a product a French retail client
  can trade. It holds money for one hour a day.

## Data (named before the search; fetched after this freeze)
- **Source:** Databento GLBX.MDP3, schema ohlcv-1h, symbol ES.v.0 (the volume-leading contract), stype continuous,
  2010-06-06..2026-11-20.
- **Pulls:** `scripts/fetch_databento.py get`, quoted first by the free `metadata.get_cost` (the full range was
  quoted at $0.97 on 2026-11-24). Half-year pulls of at most 5 cents each, into `data/databento/es_1h/` with its
  `manifest.csv` (sha256 per file). The lane cap of $2 holds.
- **Why hourly bars, not minutes.** Minute bars cost $21 (ES) or $9.7 (MES, from 2019), beyond the lab's spending
  so far ($2.78). With hourly bars:
  - the predictor is exactly the literature's (previous 16:00 to 10:00 New York);
  - the target is the last hour (15:00-16:00) rather than the last half hour, which dilutes the effect.

## Rule (`scripts/run_closing_momentum.py`)
- **Inputs per New York trading day:** closes at 10:00, 15:00 and 16:00 New York time (bars labelled by open time in
  UTC; New York hours are whole UTC hours across daylight saving), and the previous trading day's 16:00 close.
- **A (Gao):** position s = sign(ln C10/C16_prev), held from the 15:00 close to the 16:00 close.
- **B (Baltussen):** s = sign(ln C15/C16_prev), same hold.
- **Days counted:** a day counts only if the four bars exist and carry one instrument_id (no roll inside the signal
  or the hold). Early-close days have no 15:00/16:00 bars and drop out.
- **Costs:** 1/2/3 bp a round trip on notional. On MES that is about $1.2 of fees and one 0.25-point tick, against
  about $30k of notional.
- **Decision (each rule separately), on 2018-01-01..2026-11-20 at 1 bp:** PASS if NW t (lag 5) ≥ 2.8, the 2 bp mean is
  > 0, and both halves are > 0.
- **Reported, not decided:**
  - 2010-06..2017-12, the in-sample period of the literature;
  - by year;
  - the signal-target correlation;
  - 3 bp.

## Supply, break-even and power (`CLAUDE.md` step 4)
- **Supply:** about 250 trades a year, every one a single hour.
- **Break-even.** If the literature's predictability held (a correlation of 0.10-0.14 between the sign and the next
  move), a sign rule earns about ρ·σ·√(2/π). With σ ≈ 25-30 bp for the last hour, that is 2-3 bp a trade gross,
  against 1 bp of cost. Thin but positive.
- **Power.** On about 2,200 decided days, the expected t is (edge − cost)/σ·√n:
  - about 2.5-3.5 at full effect;
  - under 1 at half the effect.

  So power at the 2.8 bar is roughly 40-60% if the effect is intact, and near zero if it halved. The round is mainly
  a decay test. A FAIL with a positive gross mean says "decayed or too thin", not "never there".

## Pre-mortem: "it failed because…"
1. **The effect decayed after publication.** This is likely, and it is the question. The by-year table shows when.
2. **0DTE options (2022+) left dealers long gamma at the close,** so the end of the day reverts. That gives negative
   years from 2022: a finding, not a bug.
3. **The last hour dilutes the last half hour.** That lowers t. The literature also reports predictability for
   15:00-15:30, so the dilution is partial.
4. **Rolls or bad bars give outliers.** Roll days are excluded by instrument_id. The by-year table and the hit rate
   show whether one day drives the mean.
5. **Costs at the close are higher than one tick.** ES depth is greatest at the close, so one tick is a fair price
   for MES. 2 and 3 bp are reported.

## Trials
- **This round:** 2 (rules A and B).
- **Program trials:** 9,785,788 before, 9,785,790 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_closing_momentum.py` | 5b1633b0fe2922c0afd6717c0e0624f29f55f571d3f00f0f18618c28a6d7db37 |
| `tests/test_closing_momentum.py` | fb5324423137bb00fd8108ecf57423c6b4a31252a13ba0b92d326f58a01398ce |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `scripts/fetch_databento.py` | b2a03bdcbcd64412c83eec66751ccbbecc3ab3b3bd34a273f1847a0aebea95b2 |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `lab/prereg.py` | 3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 |
