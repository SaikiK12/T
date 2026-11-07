# Atomic route source qualification, 2026-11-07

Owner objective: substantial repeatable net returns and frequent opportunities,
with evidence of reliability. Atomic rollback protects the specified token
balance condition if a correctly implemented transaction executes. It does
not guarantee inclusion, recurring opportunities, net gas profit, stablecoin
value, contract safety or a high return on total capital. No transaction or
wallet was created or sent. No flash loan, relay or mempool action.

Sources read on2026-11-07:
- PublicNode, https://ethereum.publicnode.com/ (undated, public endpoint
  listing only): https://ethereum-rpc.publicnode.com.
- Uniswap Developers, https://developers.uniswap.org/docs/protocols/v2/deployments
  (undated, partial mainnet row): Ethereum factory
  0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f.
- Uniswap Developers, https://developers.uniswap.org/docs/protocols/v2/concepts/flash-swap
  (undated, partial definition): withdrawn tokens must be paid for or returned
  with a fee by the transaction's end. No deployed custom profit guard tested.
- Uniswap, https://docs.uniswap.org/whitepaper.pdf (2020, indexed fee section
  only):0.3%swap input adjustment. No full whitepaper/corpus read claimed.
- SushiSwap, https://github.com/sushiswap/v2-core and
  https://raw.githubusercontent.com/sushiswap/v2-core/master/contracts/UniswapV2Pair.sol
  (undated current tree, partial repository layout/contract read). The proposed
  Ethereum Sushi factory address was found in secondary Bitquery material,
  https://docs.bitquery.io/docs/blockchain/Ethereum/dextrades/uniswap-api/;
  on-chain/primary deployment identity remains UNQUALIFIED.
- Circle, https://developers.circle.com/stablecoins/usdc-contract-addresses
  (undated, partial Ethereum row):
  0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48. No token/owner entitlement.

One ordinary metadata-only `eth_chainId` POST to PublicNode at16:07UTC returned
**HTTP403,17bytes**. The exact request-body hash, UTC access/receipt, response
body/hash and normal Python urllib UA are in chain_id.receipt.json. No market
reserve, price, route quote, gas profit or frequency was read. The status was
known during allowed plumbing before R425's freeze; R425 records its integrity
and qualification, not a blinded economic experiment. No denied-resource
retry, alternative provider/region/header, credential or access workaround.

**Source blocked, economics untested**, not a zero-profit result. A successor
needs properly permitted market data before any frozen economic test.
