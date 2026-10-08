# ancova

## Purpose and when not
Statsmodels OLS with additive common covariate slopes. Type III sum contrasts default, Type II optional. Factor interaction may be requested but factor-by-covariate slopes are not fitted. Check overlap and homogeneity of slopes separately; covariate adjustment does not establish causality.

## Required fields and measurement
outcome: scale; factors: categorical list; covariates: scale list; ss_type=2/3; contrast=sum; interaction=false by default. Action `ancova`.

## Assumptions: evidence versus diagnostics
User evidence establishes design, independence, units and measurement meaning. Helper checks finite inputs, complete cases, rank/count/variance constraints. Residual distributions and design assumptions are not declared passed.

## Computation status
Helper-supported in `scripts/advanced.py`. scipy/statsmodels/pingouin/sklearn compute all numeric results. No LLM arithmetic.

## Output contract
N, selected options, model-specific computed tables/diagnostics, audit, source, package versions, validity and notes. JSON addition is a new action, not a change to legacy fields. Reports display estimates from the helper.

## Validation
Noisy multi-factor/unbalanced fixtures, direct library comparisons, analytic eigenvalue/rotation identities and invalid-input tests. Published-SPSS parity is limited to fixtures named in `../tests/fixtures/parity.json`; none of these new advanced procedures currently has a licensed-SPSS comparison.

## SPSS convention notes
Statsmodels OLS with additive common covariate slopes. Type III sum contrasts default, Type II optional. Factor interaction may be requested but factor-by-covariate slopes are not fitted. Check overlap and homogeneity of slopes separately; covariate adjustment does not establish causality.
SPSS defaults and rotation normalization can differ. Do not claim whole-procedure parity from an omnibus-only fixture.

## Interpretation and alternatives
Explain SS/contrast or extraction/rotation policy, inspect assumptions and report uncertainty. Main effects with interactions, sphericity violations and component retention require judgment. Use mixed models/validated specialist workflows outside supported restrictions.
