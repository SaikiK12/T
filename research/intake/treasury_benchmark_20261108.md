# Treasury reference quotes are not cash-account returns

Source/mechanics qualification,2026-11-08; no new financial measurement,
trial, return estimate or frozen strategy change. DTB3's discount convention
was already named in R406's PREREG; this note makes its economic limitation
explicit instead of presenting a familiar definition as a new discovery.

## Primary source register and read scope

All accessed2026-11-08 through public reference-page reads. No market-history
CSV, auction API, archive or protected2020 rows were downloaded/parsed.
No authentication or source-denial workaround. These documentation reads
are not an extra grant for historical/market acquisition.

| Source and organization | Publication/version | Read scope and exact useful statement |
|---|---|---|
| [DTB3 series metadata, FRED / Federal Reserve Bank of St. Louis; underlying source Federal Reserve Board](https://fred.stlouisfed.org/series/DTB3) | Page undated; metadata update displayed2026-11-06; accessed2026-11-08 | Partial: series identity, percent/daily units, notes and revision disclaimer. Notes explicitly say “Discount Basis”. No displayed yield was compared or scored. |
| [Understanding Pricing and Interest Rates, US Treasury/Bureau of the Fiscal Service](https://www.treasurydirect.gov/marketable-securities/understanding-pricing/) | Publication date not found; accessed2026-11-08 | Partial: Bills section. Exact formula: “Price = Face value (1 – (discount rate x time)/360)”. Other security examples are outside this review. |
| [Marketable-securities glossary, US Treasury/Bureau of the Fiscal Service](https://www.treasurydirect.gov/help-center/glossary-for-marketable-securities/) | Publication date not found; accessed2026-11-08 | Partial: investment-rate and settlement definitions. “An annualized simple interest rate based on a 365-day year (366-day basis for a leap year), without compounding.” |
| [Daily Treasury Bill Rates, US Treasury](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_bill_rates) | Methodology undated; page displays2026-11-06; accessed2026-11-08 | Partial: definitions below table. Bank discount uses par and360days; coupon/investment yield uses purchase price and365/366days. No table or return series extracted. |
| [H.15 Selected Interest Rates, Federal Reserve Board](https://www.federalreserve.gov/releases/h15/) | Current release2026-11-06; accessed2026-11-08 | Partial: release identity/calendar paragraph. It is a published secondary-market reference, not the lab's investment receipt. No current rate table scored. |

## Cash algebra and the missing contract

For face value F, paid price P, discount quote d as a fraction and actual
days N to maturity, Treasury's bill-price formula gives

`P = F * (1 - d*N/360)`.

The held-to-maturity cash return is `(F-P)/P`, not the quoted discount
fraction. For the applicable short-bill simple-investment convention,
annualizing that cash return by `Y/N` gives `d*Y/(360-d*N)`, with Y the
applicable365/366-day year. This is algebra from the cited definitions,
not a fitted model, realized return or universal long-maturity yield rule.
Exact settlement/maturity and the applicable convention must be known.
A generic three-month series does not supply a held CUSIP or exact N.

For positive d and a positive purchase price, the different cash denominator
and year basis matter. Their impact on any existing strategy was NOT
measured here. Do not pick a91-day convention after seeing carry results,
replace the series to improve a verdict, or silently rescore old journals.

## Consequence for this lab

R406/R413 preserve their frozen DTB3 reference rules. Their code's labels
about a T-bill being paid are not proof of a purchased bill or a realized
cash account. Averaging later daily reference rates over a lock is also
different from holding a specified bill or a fully specified reinvestment
portfolio. R429's284-date source identity pass repairs data admission only;
it neither converts this benchmark nor supplies investable cash evidence.

Before economic/account admission, a new frozen comparison must specify
the investable instrument, receipt/decision/settlement/maturity clocks,
buy/sell or redemption cash, cash denominator, funding and reinvestment,
fees and FX treatment at comparable capital/risk. Missing instrument or
access evidence stays missing. No account, legal eligibility determination
or trade is made here. M244/M480 remain PARTIAL; existing results stay.

Costs1x/2x/3x: N/A (source/mechanics only), not zero. No new PnL or
prospective paper day is produced, and no high-return claim follows.
