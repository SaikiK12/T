# M488: official dashboard units and European funding processing clarified

Codex, **2026-11-07 UTC**. Source-code/document qualification only: no new
funding-history request, rate statistic, trading rule or PnL. Earlier frozen
source notes and R419's raw collector remain exact. The
[receipt](coinbase_unit_qualification_20261107/receipt.json) records source URLs,
body sizes, SHA256 and read scope.

## The public MDA field has a primary-source display convention

The ordinary [Coinbase public dashboard](https://www.coinbase.com/market-data/derivatives)
(Coinbase, undated, accessed **2026-11-07**, partial route/component read)
loads [app e_DUioEnG0.js](https://www.coinbase.com/assets/sw-cache/e_DUioEnG0.js),
which assigns its derivatives route to
[c_CXQJLpmP.js](https://www.coinbase.com/assets/sw-cache/c_CXQJLpmP.js).
These deployed primary scripts are undated and content-hashed in the receipt;
only the route, CDE funding adapter, formatter and export were examined.

The CDE adapter parses `funding_rate` directly as its value, multiplies that
value by **8,760** for its annualized display, and retains `event_time` as the
timestamp. Its percentage export multiplies the value by **100**; its ordinary
display uses the same percentage convention. Thus the dashboard treats the
**MDA CDE field as an hourly decimal fraction**. These numbers describe the
deployed program, not an observed return or a forecast. The website's constant
annualization is not evidence of 8,760 payable observations: maintenance and
missing/closed hours must stay explicit.

This resolves the MDA display-scale uncertainty more directly than the Help
page's contradictory arithmetic examples. It **does not** establish the
distinct Advanced REST field's scale/fixing, historical mark prices, exact
client cash postings or an audited clearing record. No historical funding
value was evaluated to infer the unit.

## CFSE itself describes hourly accrual and twice-daily cash processing

[CBFSE Trade and Order Execution Policy](https://www.coinbase.com/legal/cbfse_tradeandexecutionorder)
(Coinbase Financial Services Europe Ltd, updated **2026-09-11**, accessed
**2026-11-07**, partial: sections7.1 and11.5, with related12.3) confirms the
**20** three-minute premium observations, **1/24** scale and **75%/25%**
smoothing. Section7.1(c) states:

> "The resulting Funding Payments are processed twice daily through clearing house cash adjustments"

The policy separates these adjustments from variation margin, uses the venue
or clearing mark, and says CFSE retains no funding portion as revenue. Accrued
debits can reduce available margin before a favorable price move. This is an
EEA primary policy, rather than an inference from U.S. Prime's client posting
schedule. Exact CFSE booking times, accessible collateral and the client's
statement remain unverified. A model must keep accrual and spendable cash
separate and must not assume instant transfers between venues.

## A newer exchange rule contradicts the old maturity interpretation

Coinbase Derivatives' [Form1-N filed with the SEC](https://www.sec.gov/files/coinbase-derivatives-form-1-n.pdf)
(submitted **2026-09-01**, embedded rulebook **August2026**, accessed
**2026-11-07**, **partial**: BIP Rule1129 on PDF pages167-168, plus cover/version)
says:

> "The Contract has no expiration date and no final settlement date."

The inspected BIP rule specifies the **0.01BTC** multiplier and hourly funding
aggregated at midday/end-day clearing runs. This conflicts with the
**2089** reference maturity in the August24 European SID and current Advanced
metadata, and supersedes the April rulebook's old five-year description for
the inspected exchange rule. No filing-effectiveness or broker product
reconciliation is inferred merely from dates. ETH's full contract chapter was
not extracted in this pass. Preserve the source disagreement: neither the
legacy2030 code nor the2089 reference field alone proves an economic expiry.

## What the next economic lane can now specify

Use the qualified **MDA** decimal convention for an explicitly named historical
series; do not silently transfer it to Advanced. The saved history has no mark
base, and the funding timestamps still need a fixing/position-eligibility
interpretation. Any historical mark proxy needs explicit bounds and a label
that it is a scenario, not exact paid carry. Paired R419 books now arrive in
the canonical state branch, but do not establish fills or funding settlements.
Freeze a separate economic lane before matching rates, computing differences,
walking books or scoring any return. Include both venues' real regular fees,
contract granularity, separate cash/margin accounts, one-leg failure and costs
1x/2x/3x. M488 remains **PARTIAL**.

Additional source read: Coinbase's [Get Public Product Candles](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/public/get-public-product-candles)
(undated, accessed **2026-11-07**, partial endpoint/query/schema) documents
public product OHLC buckets, not historical funding marks. No candle request
was sent and no candle was substituted for the funding cash base. The guessed
regulations page and the web reader's CDE OpenAPI rendering were inaccessible;
the previously captured OpenAPI extract was read locally. No denied FairX
resource, source budget or rate-limit stop was retried or reset.
