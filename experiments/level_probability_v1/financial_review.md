# R330 independent bounded math/causality/account review

Reviewed exact `lab/level_probability.py` SHA-256 **aed8c36a6defd0c70143e42930e1be881d26367483aef3d4269c4bc54a8cbdc2**. No tracked file edited, no network call, no historical market outcome/data file read. Runtime cases compiled the exact bytes after a hash guard and used invented literal arrays/records only. This is a narrow component review, not a runner/source-data/whole-system/profitability certification.

## Checks executed on this final candidate

- prior72extrema excludes decisionclose.
- features invariant to futurecloses.
- onehour delayedentry.
- close-grid barrier uses observed overshoot.
- funding excludesentry includesexit.
- pricelabel survives unknownfunding without zero payoff.
- firstpricegap stops beforelaterresolution.
- timeout exactly12postentryhours.
- Dirichletcounts.
- payoffmagnitudes separatefromprobabilities.
- cell shrink20 global.
- noearnedcalibration.
- literal500notional net 1x.
- literal500notional net 2x.
- literal500notional net 3x.
- samequantityalltiers.
- no fictitiousopeningprincipal.
- 3xshadow boundary sharescapitalstop ALLtiers.
- blockedmissingcandidate cannotpoisonknownaccount.
- admittedmissingexit preservesexposure andunknownidledays.
- admittedunknownfunding preservesclose andpendingcash.
- strictadjacentcycle certifiesinterioronly.
- conflictingcycle doesnotassumezero.
- actualzerorate distinctfromunknown.
- highhitprobability notpositiveEV.
- actualactivation alwaysfalse.

**26 literal checks passed.** Earlier17checks were rerun on this final hash after code changes; reruns are not additional independent trials. Intermediate counterexamples are retained below rather than upgraded to passes.

## Material defects found and pre-freeze corrections observed

At originalSHA0dd0e6a6f0177339a48898a968cdb8af3831341d1e53b9e28c8397d9c2d6f388, constructed four500-notional shorts from1to100 left negativecash yet the nextday still openedfourpositions. A reportedmaximumgrossfraction.2also incorrectly implied a bound on markedgross (literalmarkedgross200000beforeexit). Currentcandidate stopsnewrisk against a100%-entry-notionalcashreservation and calls.2anENTRYgrosscap; markedgross/margin/liquidationverification remainfalse. Existingadverse closes are retained, not replacedbyfictitiousliquidation.

A firstcapitalguard ranseparatelypercosttier, allowing differententries nearcapitalboundaries. Currentcandidate useschronological3xshadowadmission forALLtiers. The literalshort500at100to1998leaves501.608/493.216/484.824cash andblocks thenextentryatALLtiers. Futureexitsarenotcreditedbeforetheirchronologicalevent.

Prebuilding persistentunknown fromanunadmittedcandidatecouldpoisoncashcompleteness aftercapitalrejection. Currentcandidate schedulesamissing-exitmarker and appliesitonlywhenitsticketwasadmitted; blockedfutureevents are skipped. A bankruptaccount plusunenteredmissingexit nowpreservesknownnegativecash,zeroseconddayP&L,noopenposition/nopendingfunding/nounknownmarker. Admittedgapandfundingunknowncases stillkeepunknowncash/exposureandstopnewrisk; knownclosesremain.

## Scope and remaining limitations

These labels are **entry-relative hourly-close continuation/reversal afteraonehourdelay**, conditionalonproximitytoprior72hourcloseextrema. They are notactualintrabarfirsttouch/freshsupport/MSNRlevelbreaks orfillprobabilities. Repeatednear-leveldaysarepossible; nofirst-touchfreshnessclaimisreviewed.

Trainingfit usesfinancial-knownoutcomes; scoring canincludeprice-known/funding-unknownlabels. Differentcoverage/censoringmustbedisclosed. Themoduledoesnotenforceexternaltrain/calibration/validationdatefilteritself: runnercutoffs,trainingartifactcommit,inputhashesandnoleakageacrossthosestageswereNOTreviewedhere. Noactualreturndatasetortrainedmarketcoefficientswasread.

Classprobabilitiesareseparatefrompayoffmagnitudes. Constructed90%breakprobabilitywithrarelargeoppositelossesyieldednegativeexpectedbreakpayoff; rawconfidenceisnotanedge. The.25sigmadecisionreserveisaregisteredheuristic,notacalibrateduncertaintybound. Brier/logloss/reliabilitydefinitionsandjoint14day-shiftsarecomponentdiagnostics,notvalidatedcoverage,pvaluesorprogram-wideselectioncontrol.

PaperAccountchecksestablishconditionallinearP&L/funding/feesandshared10000USDTcapital,notactualvenuecollateral,liquidation,maintenancehaircuts,lotrounding,fair/indexfundingnotional,executablequotes,sourcefirst-seenclocks,capacityoraccountentitlement. Cost16bproundtripthresholdusesentrynotionalwhileactualexitfeeusesexitnotional; itisafixedresearchdecisionrule,notaguaranteedbreak-evenbound. Cumulativefundingispostedatmodelexit; intrahorizonmargin/equityisnotvalidated. Negative-equityadverseworldsremainliteralmodelresults,notexecutablemarginpaths.

Onlythefinancialkernelandboundedcausal/missing-stateinvariantslistedabovewereexecuted. Wholecollector/runner/independentoracle/panel/intake/prospectivepaperprotocol,realizedriskcomparabilityandpositiveexpectedreturnwerenotindependentlycertified. Noorderoractivationallowed.
