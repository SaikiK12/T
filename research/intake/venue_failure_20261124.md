# Venue failure: base rates of exchange closure and of customer loss (question Q3), read 2026-11-24

- **Question** (`research/intake/questions_20261120.md`, Q3): how often does a crypto venue fail, and what do its
  customers lose? It is the input that decides the stake's size in `scripts/stake_kelly.py`.
- **Read myself, legal copies on the authors' pages:**
  - Mukherjee & Moore (2022), in full (8 pages);
  - Moore, Christin & Szurdi (2018), p. 8 only (the closure and reimbursement passage, Tables II-III).

## Cards
### 1. Closure rate and its drivers (Mukherjee & Moore, "Cryptocurrency Exchange Closure Revisited (Again)", eCrime 2022)
- **Source:** https://tylermoore.utulsa.edu/ecrime22exchange.pdf, pp. 1-6 and Tables III-IV.
- **Claim.** Of 822 exchanges operating in 2010-2022, 327 (40%) closed (Cryptowisser's list). The Kaplan-Meier curve
  shows about 75% surviving 3 years, and a median life near 7 years, so about 10% a year on average.
- **Drivers** (Cox hazard ratios, Table IV):
  - each coin traded, 0.995;
  - accepting US customers, 1.52-1.59;
  - crypto only (no fiat), 1.38-1.39 (7.5 on data to May 2021);
  - OECD headquarters, not significant;
  - a security breach, not significant (1.06).
- **Limits:**
  - "closure" includes orderly shutdowns;
  - no variable for age, owner, size of open interest or regulation;
  - on-chain venues are left out.

### 2. What customers get back (Moore, Christin & Szurdi, "Revisiting the Risks of Bitcoin Currency Exchange Closure", ACM TOIT 2018)
- **Source:** https://jszurdi.github.io/content/academicpapers/toit18.pdf, p. 8.
- **Claim.** "Of the 38 exchanges that closed, we have found evidence on whether customers were reimbursed in 16
  cases. Six exchanges have not reimbursed affected customers, while five have fully refunded customers and five
  more have partially done so."
  - Counting a partial refund as half, the expected recovery is about 47% where the outcome is known.
  - In the same sample, 38 of 80 Bitcoin exchanges (2010-2015) closed.
- **Limits:** 16 known cases, all small Bitcoin exchanges of 2010-2015.

### 3. Deribit's owner (search summary, several outlets; not a primary read)
- **Claim.** Coinbase completed its acquisition of Deribit on 2025-08-14 (about $2.9 billion; Coinbase's release on
  Nasdaq, The Block, Cointelegraph).
- **Use:** the closure model knows no owner, so it puts Deribit (crypto only, about 100 coins) at about 9% a year.
  The adjusted set gives it Kraken's rate.

## Use in the lab (`scripts/stake_kelly.py`)
- **Closure rates a year** (`LAM_VENUE`), from card 1. They take the base of 10% at 16 coins and are scaled by the
  hazard ratios:

  | Venue | Coins (rough) | Crypto only | US customers | Rate from the models | Adjusted |
  |---|---|---|---|---|---|
  | Kraken | 350 | no | yes | 2.9% | 2.9% |
  | Binance | 400 | no | no | 1.5% | 1.5% |
  | Bitfinex | 200 | no | no | 4.0% | 4.0% |
  | Deribit | 100 | yes | no | 9.1% | 2.9% (Coinbase-owned) |
  | Hyperliquid | 200 | yes (on chain) | no | 5.5% | 5.5% (not modelled) |

- **Recovery:** 47% (card 2).
- **Weighted by the ticket's deposits:** 4.7% (models) or 3.8% (adjusted) closures a year. That is an expected loss of
  2.5% or 2.0% a year of the stake.
- **The stake at leverage 2, on the three forward pairs, adjusted rates, half Kelly.** It beats cash by:
  - +3.5%/yr at the in-sample edge (6.7%/yr at 1x);
  - +1.9%/yr at 5%/yr;
  - +0.2%/yr at half the edge.
  So venue risk takes about as much as half the edge.
- **Rule** (`docs/reviews/stake_dhl_20261123.md`): stake only if the passing read's forward fund_book supports at
  least about 5%/yr at 1x.

## Not read
- Moore & Christin (2013), the rest of the 2018 paper, Charoenwong & Bernardi's hack list, and the court and
  administrator records of FTX, Mt. Gox and QuadrigaCX.
- Hyperliquid's own failure modes (contract, validator, oracle).
