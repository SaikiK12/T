# Public M090 content-proof trust material

Public root/intermediate certificates only; no private keys or account data.
`root.pem` is the OS trust store's self-signed DigiCert Trusted Root G4.
`chain.source.pem` preserves the official downloaded intermediate bytes;
`chain.pem` is the normalized PEM used by OpenSSL. Exact source URL/download
hash, fixed service, signer DER pin and two live CRL endpoints are in policy.json.
R374 freezes all these inputs before market capture and obtains fresh CRLs.

Primary-source review on 2026-10-29, retained as bounded engineering context:

- [RFC3161](https://datatracker.ietf.org/doc/html/rfc3161), sections 2.2,
  2.4.1/2.4.2 and security considerations: imprint, nonce, genTime, Accuracy
  and trust. Absence of Accuracy is not zero uncertainty.
- [DigiCert RFC3161 service](https://knowledge.digicert.com/general-information/rfc3161-compliant-time-stamp-authority-server),
  service endpoint and public certificate update dated 2026-09-03.
- [CP/CPS 7.09](https://www.digicert.com/content/dam/digicert/pdfs/legal/digicert-public-trust-cp-cps-v7-09.pdf),
  title/version and section 6.8 only. UTC(k) synchronization and auditable
  corrections do not supply the older indexed numerical one-second bound.
  No full CPS review is claimed. R374 accepts no CPS precision fallback.
- [FreeTSA](https://www.freetsa.org/index_en.php) and its
  [usage page](https://www.freetsa.org/freetsa.html), bounded service,
  certificate, verification and rate-limit reading; not R374's endpoint.
- [OpenSSL ts](https://docs.openssl.org/1.1.1/man1/ts/), query/verification
  semantics; actual current OpenSSL 3.x commands are tested with ephemeral
  offline certificate chains and signed responses, including revocation.

Invented-byte feasibility probes on Oct 29 verified both service signatures
and found no signed Accuracy. Their temporary bodies were lost at restart;
they are not independently replayable evidence here or market forecasts.
R374's later frozen source packet and native results are separate evidence.

R374 always returns no UTC interval and zero eligible forecasts. Signature
checks prove content under the authority's key, conditional on operator
security; they do not prove source truth, public availability, actual disk
survival or a truthful UTC clock. CRL checks apply at signed genTime; they are
not a later revocation audit. The immutable result head is needed to reject
deletion/substitution of a complete earlier archive. No order or clock change.
