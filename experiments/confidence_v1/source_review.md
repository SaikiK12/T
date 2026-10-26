# R331 bounded primary reading

Acquisition is closed: two search queries and three unauthenticated GETs,
1,945,479 body bytes, every PDF complete/HTTP200. Overall acquisition about36s
(120s maximum); request script itself1.742s. No retries/redirects/account/market/
history/modelweights requests. All raw/text fingerprints are in receipts.json.

## Concrete implementation implications

- Temperature: freeze the base model; fit one positiveT against calibrationNLL,
  then predict softmax(z/T). It cannot change argmax or create information.
  Guo explicitly assumes training/calibration/test share a distribution.
- Dirichlet: softmax(W*log(p)+b). Identity is in the family, but standardL2 toward
  zero is not identityshrinkage. PaperODIR penalizes only offdiagonalW andb,
  with MEAN-logloss scaling. A ||W-I||² penalty is ournewregularizedvariant.
- Source guarantees neither20/50sampleminimum nor financialedge. Mainexperiments
  use IID-like nested folds and muchlarger calibrationdata. Temporal/crossasset
  dependence anddistributiondrift remainours tohandle.
- Maxclassconfidencecalibration is weaker thanclasswise/fullmulticlasscalibration.
  Evaluate eachbreak/rebound/timeoutclass, properloss and economiccosts versus
  constantprior. GoodconstantpriorECE can contain no usefulinformation.
- Cont'sOFI requires successivebestbid/ask prices AND queuequantities. The
  equation aggregates quoteaddition/removal/pricechanges, including cancellations.
  OHLCV,wicks andunsignedvolume cannot reconstructit. Do notlabelthoseproxies
  orderflow/absorption. ItsR² is concurrentUS-equityprice-impactexplanation,
  notnextperiodcryptoprediction or executableprofit.

## Read/unread scope

Guo mainsections1–6 read; Kullmainsections1–5 read, equations/fitting/experimental
protocolstext checked. Figure/table entries are context, not independently
reproducedresults. Contselectedsections1,2.1–2.3,3.1,4.1 andparts4.2 read;
mostdetailtables/seasonality/appendixunread. Allsupplements,linkedpapers,code,
datasets andweightsunreceived/unexecuted. The search-only2026SMARTpaper is an
unread discovery, notanimplementedmethod. Source_methods.json enumerates every
receivedmethod/controlfamily withinthisactualscope, includingweak/referenceonly
alternatives; no newstrategy/marketresult isclaimed.
