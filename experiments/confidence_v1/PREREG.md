# PREREG: informative candle features, disjoint probability calibration and net costs

- **Registry id:** R331
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-26

## Question and unchanged authorities

Owner asks for the best useful breakout/rebound confidence model with primary
research alongside implementation. BEST here means the lowest selection-period
proper probability loss among a finite registered family, NOT a globally best
model, validated future confidence, net edge or private institutional strategy.
M412/OWN26-LEVEL-PROBABILITY is the single canonical method family. Source-only
OFI refinements map to existing M084/M264 aliases; no duplicate queue or panel.
R330's original null/inactive rule and old targets remain intact. R311 stays
INCONCLUSIVE224/273 with selected2x/3x losses; R321's failed inference controls
are not repaired/reclassified here. No validation winner/gap/cost/size rescue.

## Input and source contract before any new model outcome

- `config.json`: `0040bc752072b2f1ea40c395267a4aca6099e69e3d170a1625e3d023bd41968c`.
- `data_inputs.json`: `2f648c9bd5c8e44430461d00a6f7a18433e6fd1a2fbd45b0b1b6868611a61a87`.
- `code_inputs.json`: `97adc248383dad8cc820674087d6df4f45ed44c2c2e391542e63b8a107a2b237`.
- `sources.json`: `ff152cd483855d9ebd65fb840134657f33e9e1f8375f9ff47b192b19c3303e17`.

17-file local import/test closure, Python3.12.14 and pinned numeric/model package
versions verify before/after every stage. SharedCLI dispatch is intentionally
excluded. Existing lockedscikit-learn1.8.0 is used for OUR fixedlearners; no new
package/modelweights download or sourcepaperstrategy replication.

Four assets fixed before outcomes: BTCcontrol,ETH,SOL,WIF. Eight old MEXC
price/funding files are unchanged.28original public rawpages from the OLD R310
acquisition already contain APIopen/high/low; all50112rows reconcile exactly to
oldclose/vol/amount. Pin eachgzip/rawhash,URL,receipt andnativeinteger clock;
reject wrongscheme/query/asset/interval, fractional/bool clocks, nonhourly or
out-of-query rows, conflicts orclose/volume/amount mismatches. Source real*
fields are retained inoldcache but UNUSED anduninterpreted. No actual OFI,
absorption or signedtradeflow can be inferred from these bars.

Old R330 signal/label/outcome records and their independently audited source
identity are pinned. New rows must match those targets exactly. Theirreuse is
transitive proof, NOT a new independent sample. NO new market/history request.
All dates/prices/labels already seen by project: time-separated fitting, not
new market out-of-sample discovery. Original historicalbudget remains ONE
allowance7757/8000requests,reported229.85/250MiB spent,exactremainingbytesunknown.

One bounded reader completed2searches+3primaryPDFGETs/1945479bodybytes, within
2MiBcombined/1MiBperbody/120s, no retries/redirect/loginbypass.40received scopes
retain Guo temperature, Kull Dirichlet/calibration distinctions and Cont quote-
event OFI requirements; exactread/unread versions in sources.json. Main/selected
sections read; supplements/linkedcode/papers/datasets/weights remainunread.
Temperature cannot createinformation; maxclassconfidence calibration does not
imply eachclass/fullmulticlass reliability. PaperODIR is distinct from our
identity regularizer. Cont's contemporaneous equityimpact is not futureMEXCalpha.
No further acquisition/new source family budget is silently opened this pass.

## Finite causal features and unchanged target

Original R330 eligibility:00UTC, prior72CLOSE extrema excludingdecisionclose,
near within.25sigma12; validnonzerovolume, no missingfeatures imputed. Delay1h,
then original entry-relative +/-sigma12 HOURLYCLOSE barrier firsthit or12h
closingtimeout. Observedovershoots, gapunknown and(entry,exit]funding retained.
Not actual intrabar/freshness/firsttouch/fill labels; those scopes remainopen.

Ten fixed covariates, all available atdecision:
1. Signed logdistance tolevel/sigma.
2–4. Outside-direction1h/6h/24h logreturns/sigma.
5. log1p(last6hour meansquaredreturn / last72hour meansquaredreturn).
6. log(currentcontractvolume / prior72hour medianvolume), denominator excludes
   decisionbar; invariant to a fixed withinasset volumeunit rescaling.
7. Signed candlebody / currenthigh-low (zero for observedflatrange).
8. Signed(lowerwick-upperwick) / range (zero for observedflatrange).
9. Outside-direction(asset24h-BTC24h logreturn)/sigma.
10. Levelside(-1support,+1resistance).

OHLC/rangeconsistency,finitepositiveprices/volume/amount and simultaneousBTC
past24hcloses required; unavailablefeature staysNone. Old targets remain even
when newfeaturematrix missing. No feature/rank/threshold/asset selection.
Globaltraining mean/populationSD only; constantscale1; standardizedfeatures
clipped[-5,5]. Learnedforecasts stillscored beyond5trainSD, but learnedmodel
entries abstainthere. Priors/originalreference needno newfeaturegate.

## Four chronological committed stages

Commit finite code/spec/input/sourceidentities BEFORE models/statistics.
Hashing reads entireinputbytes; returned datarows are filtered BEFORE eachstage.
Sourcepage bytes may containlaterrows; no laterrow is returned orlearned.
Require HEADbytes equal eachsealedphase manifest and itsartifacts beforeusingit.
Pickles are OUR owncommittedhashverifiedlocalmodel artifacts, never untrusted
remote/uploaded inputs. Modelmetadata alsoexports explicitlogits/numericHGBtrees.

A. TRAIN: May1..August31,2025 (123decisiondays). Priceclose/funding timestamp
   rowsbeforeSeptember1 only, with causalhistory fromApril27. Fit on feature-
   complete financial-known targets; >=50total and>=5eachclass required. Same
   classpayoffmeans separately estimated from normalizedrealizedprice+funding.
   Save/COMMIT bases/scaler/prior/payoffs/trainingrows/export beforeB.
B. CALIBRATION FIT: September1..October31 (61days), no November/2026rows.
   Fit calibrators only on out-of-training baseprobabilities; >=30events and
   >=3eachclass, otherwise preserve unavailability. Save/COMMIT beforeC.
C. SELECTION: November1..December31 (61days), no2026rows. Select lowest MEAN
   deliveredmulticlass NLL among sixfixedlearnedvariants plus prior; common
   feature/price-label identities and >=30selectionlabels. Missingcalibrator
   isunavailable, notzero/equivalent winner. Simplerwins within1e-6 loss:
   prior,ridgeraw,ridgetemperature,ridgeDirichlet,treeraw,treetemperature,treeDirichlet.
   Save allranks,missingcandidates,selectionrows and COMMIT beforeD.
D. Evaluate ALL registeredvariants on2026January1..September30 (273days) once
   afterchosenmodel committed. Also reportCselection economics forcomparison,
   WITHOUTusingits PnL toalterthe NLL criterion. No refit/feature/tuning/winner
   changeafterD. Deterministic reproduction isnot a new independentlook/sample.

If a phase fails, retain itsfailure anddo notinventparameters/labels orresample
untilitpasses. These finite stages are the reusable loop; no endlessvalidation
search, permanentprocess or scheduledexecution/delivery guarantee.

## Models, calibration equations and optimizer scope

Two BASE models, fixed before outcomes; no classbalancing/reweighting:
- Multinomial LogisticRegression,C=.1,lbfgs,maxiter2000,tol1e-9,seed331.
- HistGradientBoostingClassifier,32iterations,3maxleaves,20minleaf,learningrate.05,
  L2=10,earlystoppingFalse,seed331; no validationfraction/earlystop labels.

Three probabilityforms PERbase:
- raw;
- temperature:softmax(log(p)/T),fitheldCfit meanNLL on logT in[-log10,log10],
  boundedscalaroptimizer maxiter1000,xatol1e-10. PositiveT preservesargmax.
- OUR identity-L2 Dirichlet:softmax(Wlogp+b),meanNLL+||W-I||²/6+||b||²/6;
  analyticgradient,initialW=I/b0,all12rawparameters bounded[-5,5],L-BFGS-B,
  maxiter1000,ftol1e-12,gtol1e-8. This isNOTKullODIR, whichpenalizesoffdiagonals
  andintercepts differently. Failedoptimizer remainsunavailable.

Probabilityfloor1e-12 andrenormalization arefixed. Optimizers useunflooredoutput
NLL whereapplicable; delivered/scoredforecasts usefloor, so no identicalextreme
objective claim. Globalfrequency prior usestraining(count+1)/(n+3). >=50/5,
30/3 and30selection thresholds are OURpracticalchoices, not sourcetheorems.
No neuralweights,benchmarkhyperparametergrid orpaperresults arereplicated.

## Economics, controls and multiplicity

Reuse frozen R330 financialengine WITHOUTmonkeypatch/edit. One adapter per
probabilityrecipe maps registeredpointpredictions to uniqueeventcells; labels
andcashmath unchanged. ExportouterR331protocol withengineR330sourceprovenance.
SAME10000USDTaccount acrossfourcoins peralternative,500entrynotional/coin,
maximum2000INITIALgross,causal3xshadow admissionsharedalltiers. No leverage-up,
shortprincipalcash,orcombining four10000accounts. Markedgross,margin/liquidation
andintrahorizonfunding-equity/riskmatching remainunverified.

Decision remains FIXED2x16bp roundtripcost plus.25sigma reserve. Reserve is
heuristic,not calibrateduncertainty. Globaltrainingclasspayoffs are not assumed
feature-conditionallyvalidated. Stress1x/2x/3x SINGLE8bp-per-side lumpedcost on
actualentry/exitnotional, no spread doublecount. Historicalclose fills and
tradedclosefundingnotional areproxies; fair/index/ownerfee/quote/fill unknown.
Retain no-trade/feature/OOD/funding/gap/failure cases and everycalendaridle day.
No admittedunknown exposure/cash isclosed/zeroed; useoldpersistentnewrisk stops.

THIRTEEN fixed semantic accountpolicies: sixlearnedforms; newtrainingfrequency;
originalR330conditional andoriginalR330frequency; alwaysbreak,alwaysrebound,
alwayslong onSAMEevents,cash. NLL-selecting procedure isconservatively14thtested
variant. Count14newtrials; programbefore9478976,after9478990. Twoeconomicwindows
x13policiesx3costs=78uniquecells, not78independentstrategytrials. Eightadaptercalls
perwindow repeatcontrols; exactcash/ticket/day equivalence mustpass BEFORE
storage deduplication. Preserve allunique negative/null/unknownresults; report
actualreplaycounts/deduplicatedrepetitions. Do notdiscarddistinctcontrols.

All threecosttiers keep identicalsignals/quantities andcommon3xadmission. Fixed
oldreferences arecomparison recipes, notpost-hoc winners; no index/coinremoval.
Actualexecutable expectednet/activation remainunknown/False regardlessofproxygain.
Selected2xaccount incomplete=>INCONCLUSIVE; zeroclosedtrades=>NULL_INACTIVE;
nonpositive2xnet=>NULL_COST_PROXY; otherwise nonimprovedpairedprobabilityNLL=>
NULL_PROBABILITY_GAIN; otherwisePARTIAL_PROXY_ONLY, neverconfirmed/activated.
Alwaysreport3x losses aswell; PARTIAL isnot approvalofastressednegativebook.

## Reliability, dependence and independent verification

Reportperclass fixed5bin reliability withcounts/days/14dayblocks; meanNLL and
Brier versus prior on SAME labels, not incomparableavailablecaseaverages.
Emptybins andmissingcandidates stayvisible. Joint14daycalendar labelshifts
retaincrossassetstructure butareONLYdescriptive, notexchangeablepvalues.

100FIXED syntheticno-information paths,seed33101:105days/fourobservationsperday,
10independentAR(.7)features withgroup/individualnoise; labelsconstantacrossfour
same-day observations,Markovpersistence.6 and redrawprior(.15,.25,.6). Split
120/60/60/180rows fortrain/Cfit/Cselect/heldtest. RunSAMEfixedmodel/calibration/
selectionpipeline; preserve sparse/optimizerfailures withoutredrawing. Report
nonpriorselections andheldlossdiff, not a marketfalsepositive/significance claim.
This doesnotvalidateR321intervals, marketcalibration, universalconfidencebounds
orprogram-wideFWER. Calibrateduncertainty/validpvalue remainnull.

Independentchecker must compareoldtargetidentities, manuallyreconstructOHLC
features/trainingscaler,exportedridge/numericHGBbaseprobabilities,temperature/
Dirichletmaps andCselectionwinner WITHOUTproductionfunctions; alluniqueaccount
cash/fees/sourcefunding byFraction. Full constructed four-stage protocol plus
WHOLEindependentoracle runsbeforefreeze, includingbothlongandshort anddelivered
predictiontampering counterexample; oldR330 auditfailure remainspreserved.

Seven newmeaningful unittestmethods cover source/clock/cutoff/covariatecausality,
unitinvariance,calibrationidentity/argmax/gradient,allHGBbranches,exports/sparse/
selectioncontrols,andcompletefourstage/oracle. Fullunittestdiscovery required
beforelabcommit. Narrowindependent36literal reviewpinsfeature/modelhashes;
sourceclocktruncation fixedbeforefreeze. Wholeactualdriver/profitability not
peer-certified. Byte-reproducecompactresultartifacts in afreshfolder andleave
concise canonicalqueue/intake/result inissue7/existingdraft49.

No actualorders/money/secrets,largedataset/weights,merge/closure,newqueue/panel,
posthocmarketwinner or newprospectiveday. Newprospectiveforecast/strategy scoring
needsseparatefrozenprotocol/on-timeinputs; historicalresultalone doesnotactivate.
